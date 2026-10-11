import hashlib
import secrets
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.institution import Institution
from app.models.role import Role
from app.models.user import User
from app.models.student import Student
from app.models.admission import AdmissionApplication, AdmissionStatusHistory
from app.models.tnea_allotment import TNEAAllotment, TNEAImportBatch
from app.models.activation_token import StudentActivationToken
from app.adapters.tnea_adapter import MockTNEAAdapter
from app.adapters.notification_adapter import mock_notification_service
from app.core.config import settings
from app.core.security import get_password_hash
from app.schemas.tnea import (
    TNEARecordPayload,
    TNEARecordResult,
    TNEAImportResponse,
)

tnea_adapter = MockTNEAAdapter()


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of an activation token."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


async def process_tnea_import(
    db: AsyncSession,
    records: List[TNEARecordPayload],
    source: str,
    filename_or_reference: Optional[str],
    imported_by: str,
) -> TNEAImportResponse:
    """
    Ingests synthetic TNEA allotment records deterministically and idempotently.
    Creates Student, Inactive User, AdmissionApplication (ACTIVATION_PENDING), 
    Allotment, and Activation Token records.
    """
    batch = TNEAImportBatch(
        source=source,
        filename_or_reference=filename_or_reference,
        record_count=len(records),
        imported_by=imported_by,
        status="STARTED",
        errors_summary={},
    )
    db.add(batch)
    await db.flush()

    # Verify target institution
    inst_query = select(Institution).where(Institution.code == settings.INSTITUTION_CODE)
    inst_res = await db.execute(inst_query)
    institution = inst_res.scalar_one_or_none()
    if not institution:
        institution = Institution(
            code=settings.INSTITUTION_CODE,
            name=settings.INSTITUTION_NAME,
            academic_year=settings.ACADEMIC_YEAR,
            environment=settings.ENVIRONMENT,
            config={"branches": []}
        )
        db.add(institution)
        await db.flush()

    # Get STUDENT role
    role_query = select(Role).where(Role.name == "STUDENT")
    role_res = await db.execute(role_query)
    student_role = role_res.scalar_one_or_none()
    if not student_role:
        student_role = Role(name="STUDENT", description="Enrolled candidate")
        db.add(student_role)
        await db.flush()

    results: List[TNEARecordResult] = []
    successful_count = 0
    duplicate_count = 0
    skipped_count = 0
    failed_count = 0
    dispatched_count = 0
    errors_log: Dict[str, Any] = {}

    for item in records:
        record_dict = item.model_dump(mode="json")
        app_no = item.tnea_application_number.strip()
        allot_no = item.allotment_number.strip()

        # 1. Deterministic validation
        is_valid, validation_errors = tnea_adapter.validate_record(
            record_dict, target_institution_code=settings.INSTITUTION_CODE
        )

        if not is_valid:
            # Check if reason is wrong institution
            if any("Institution mismatch" in err for err in validation_errors):
                skipped_count += 1
                results.append(
                    TNEARecordResult(
                        tnea_application_number=app_no,
                        student_name=item.student_name,
                        branch_name=item.branch_name,
                        allotment_number=allot_no,
                        status="REJECTED_WRONG_INSTITUTION",
                        message=f"Rejected: Allotment is for college '{item.college_code}', not '{settings.INSTITUTION_CODE}'",
                    )
                )
                errors_log[app_no] = validation_errors
                continue
            else:
                failed_count += 1
                results.append(
                    TNEARecordResult(
                        tnea_application_number=app_no,
                        student_name=item.student_name,
                        branch_name=item.branch_name,
                        allotment_number=allot_no,
                        status="FAILED_VALIDATION",
                        message=f"Validation failed: {'; '.join(validation_errors)}",
                    )
                )
                errors_log[app_no] = validation_errors
                continue

        # 2. Check for duplicate/existing allotment or student (Idempotency)
        existing_allot_query = select(TNEAAllotment).where(
            or_(
                TNEAAllotment.tnea_application_number == app_no,
                TNEAAllotment.allotment_number == allot_no,
            )
        )
        existing_allot_res = await db.execute(existing_allot_query)
        existing_allotment = existing_allot_res.scalar_one_or_none()

        existing_student_query = select(Student).where(
            Student.tnea_application_number == app_no
        ).options(selectinload(Student.activation_token), selectinload(Student.user))
        existing_student_res = await db.execute(existing_student_query)
        existing_student = existing_student_res.scalar_one_or_none()

        if existing_allotment or existing_student:
            duplicate_count += 1
            # If student exists, reuse or retrieve existing demo activation token if available
            existing_token_raw = None
            results.append(
                TNEARecordResult(
                    tnea_application_number=app_no,
                    student_name=item.student_name,
                    branch_name=item.branch_name,
                    allotment_number=allot_no,
                    status="SKIPPED_DUPLICATE",
                    message="Allotment already exists in database. Skipped duplicate creation.",
                    raw_activation_token=existing_token_raw,
                )
            )
            continue

        # 3. Create new Student and Inactive User
        student_email = (
            item.email.strip()
            if item.email and item.email.strip()
            else f"{app_no.lower()}@demo.admissionai.local"
        )
        student_dob = item.date_of_birth or date(2008, 1, 1)
        student_mobile = item.mobile.strip() if item.mobile else "9876543210"

        # Check if user with this email already exists
        user_query = select(User).where(User.email == student_email)
        user_res = await db.execute(user_query)
        user = user_res.scalar_one_or_none()
        if not user:
            # Temporary placeholder password hash until student completes /auth/activate
            temp_hash = get_password_hash(secrets.token_urlsafe(24))
            user = User(
                email=student_email,
                hashed_password=temp_hash,
                role_id=student_role.id,
                is_active=False,  # Inactive until account activation
            )
            db.add(user)
            await db.flush()

        student = Student(
            user_id=user.id,
            institution_id=institution.id,
            tnea_application_number=app_no,
            full_name=item.student_name.strip(),
            date_of_birth=student_dob,
            email=student_email,
            mobile=student_mobile,
            community=item.community,
            allotted_branch=item.branch_name.strip(),
            quota=item.quota,
            status="ACTIVATION_PENDING",
        )
        db.add(student)
        await db.flush()

        # 4. Create Admission Application in ACTIVATION_PENDING state
        app = AdmissionApplication(
            student_id=student.id,
            status="ACTIVATION_PENDING",
            completion_percentage=0,
            personal_data={
                "candidate_name": item.student_name,
                "dob": student_dob.isoformat(),
                "mobile": student_mobile,
                "email": student_email,
                "community": item.community,
            },
            academic_data={
                "allotted_branch": item.branch_name,
                "quota": item.quota,
                "tnea_app_no": app_no,
                "cutoff_mark": item.cutoff_mark,
            },
        )
        db.add(app)
        await db.flush()

        # 5. Record initial state history: ALLOTTED -> ACTIVATION_PENDING
        history = AdmissionStatusHistory(
            admission_application_id=app.id,
            previous_status="ALLOTTED",
            new_status="ACTIVATION_PENDING",
            changed_by=imported_by,
            actor_role="ADMIN_VERIFIER",
            reason="TNEA Allotment imported. Student record initialized in ACTIVATION_PENDING.",
            metadata_info={"source": source, "allotment_number": allot_no},
        )
        db.add(history)

        # 6. Create TNEA Allotment Record
        allotment = TNEAAllotment(
            student_id=student.id,
            tnea_application_number=app_no,
            allotment_number=allot_no,
            college_code=item.college_code.strip(),
            college_name=item.college_name.strip(),
            branch_code=item.branch_code,
            branch_name=item.branch_name.strip(),
            community=item.community,
            quota=item.quota,
            cutoff_mark=item.cutoff_mark,
            allotment_date=item.allotment_date,
            joining_deadline=item.joining_deadline,
            allotment_status=item.allotment_status,
            source=source,
            raw_data=record_dict,
        )
        db.add(allotment)

        # 7. Generate Secure Activation Token (48h expiry)
        raw_token = f"ACT-{app_no}-{secrets.token_urlsafe(24)}"
        t_hash = hash_token(raw_token)
        expiry = datetime.now(timezone.utc) + timedelta(hours=48)

        token_record = StudentActivationToken(
            student_id=student.id,
            token_hash=t_hash,
            expires_at=expiry,
            is_used=False,
        )
        db.add(token_record)

        # 8. Dispatch Mock Notification
        mock_notification_service.send_activation_invite(
            recipient_email=student_email,
            recipient_mobile=student_mobile,
            student_name=item.student_name,
            raw_token=raw_token,
            tnea_app_no=app_no,
        )
        dispatched_count += 1
        successful_count += 1

        results.append(
            TNEARecordResult(
                tnea_application_number=app_no,
                student_name=item.student_name,
                branch_name=item.branch_name,
                allotment_number=allot_no,
                status="CREATED",
                message="Successfully imported allotment and initialized candidate in ACTIVATION_PENDING",
                raw_activation_token=raw_token,
            )
        )

    # Finalize batch
    batch.successful_count = successful_count
    batch.duplicate_count = duplicate_count
    batch.skipped_count = skipped_count
    batch.failed_count = failed_count
    batch.errors_summary = errors_log

    if failed_count == 0 and successful_count > 0:
        batch.status = "COMPLETED"
    elif successful_count > 0 and (failed_count > 0 or skipped_count > 0):
        batch.status = "PARTIAL"
    elif successful_count == 0 and failed_count > 0:
        batch.status = "FAILED"
    else:
        batch.status = "COMPLETED"

    await db.commit()

    return TNEAImportResponse(
        batch_id=batch.id,
        source=source,
        total_records=len(records),
        successful_records=successful_count,
        duplicate_records=duplicate_count,
        skipped_records=skipped_count,
        failed_records=failed_count,
        status=batch.status,
        results=results,
        dispatched_notifications_count=dispatched_count,
    )


async def list_tnea_import_batches(db: AsyncSession) -> List[TNEAImportBatch]:
    query = select(TNEAImportBatch).order_by(TNEAImportBatch.created_at.desc())
    res = await db.execute(query)
    return list(res.scalars().all())


async def get_tnea_import_batch_by_id(
    db: AsyncSession, batch_id: str
) -> Optional[TNEAImportBatch]:
    query = select(TNEAImportBatch).where(TNEAImportBatch.id == batch_id)
    res = await db.execute(query)
    return res.scalar_one_or_none()


async def list_tnea_allotments(
    db: AsyncSession,
    branch_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = (
        select(TNEAAllotment, Student, AdmissionApplication)
        .outerjoin(Student, TNEAAllotment.student_id == Student.id)
        .outerjoin(AdmissionApplication, Student.id == AdmissionApplication.student_id)
        .order_by(TNEAAllotment.imported_at.desc())
    )

    if branch_filter:
        query = query.where(TNEAAllotment.branch_name == branch_filter)
    if status_filter:
        query = query.where(AdmissionApplication.status == status_filter)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                TNEAAllotment.tnea_application_number.ilike(pattern),
                TNEAAllotment.allotment_number.ilike(pattern),
                Student.full_name.ilike(pattern),
                Student.email.ilike(pattern),
            )
        )

    res = await db.execute(query)
    rows = res.all()

    items = []
    for allot, student, app in rows:
        items.append({
            "id": allot.id,
            "student_id": allot.student_id,
            "tnea_application_number": allot.tnea_application_number,
            "allotment_number": allot.allotment_number,
            "college_code": allot.college_code,
            "college_name": allot.college_name,
            "branch_code": allot.branch_code,
            "branch_name": allot.branch_name,
            "community": allot.community,
            "quota": allot.quota,
            "cutoff_mark": allot.cutoff_mark,
            "allotment_date": allot.allotment_date,
            "joining_deadline": allot.joining_deadline,
            "allotment_status": allot.allotment_status,
            "source": allot.source,
            "imported_at": allot.imported_at,
            "student_name": student.full_name if student else None,
            "admission_status": app.status if app else (student.status if student else "ALLOTTED"),
        })
    return items


async def get_tnea_allotment_by_id(
    db: AsyncSession, allotment_id: str
) -> Optional[Dict[str, Any]]:
    query = (
        select(TNEAAllotment, Student, AdmissionApplication)
        .outerjoin(Student, TNEAAllotment.student_id == Student.id)
        .outerjoin(AdmissionApplication, Student.id == AdmissionApplication.student_id)
        .where(TNEAAllotment.id == allotment_id)
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        return None
    allot, student, app = row
    return {
        "id": allot.id,
        "student_id": allot.student_id,
        "tnea_application_number": allot.tnea_application_number,
        "allotment_number": allot.allotment_number,
        "college_code": allot.college_code,
        "college_name": allot.college_name,
        "branch_code": allot.branch_code,
        "branch_name": allot.branch_name,
        "community": allot.community,
        "quota": allot.quota,
        "cutoff_mark": allot.cutoff_mark,
        "allotment_date": allot.allotment_date,
        "joining_deadline": allot.joining_deadline,
        "allotment_status": allot.allotment_status,
        "source": allot.source,
        "imported_at": allot.imported_at,
        "student_name": student.full_name if student else None,
        "admission_status": app.status if app else (student.status if student else "ALLOTTED"),
    }


async def get_tnea_allotment_by_student_id(
    db: AsyncSession, student_id: str
) -> Optional[Dict[str, Any]]:
    query = (
        select(TNEAAllotment, Student, AdmissionApplication)
        .outerjoin(Student, TNEAAllotment.student_id == Student.id)
        .outerjoin(AdmissionApplication, Student.id == AdmissionApplication.student_id)
        .where(TNEAAllotment.student_id == student_id)
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        return None
    allot, student, app = row
    return {
        "id": allot.id,
        "student_id": allot.student_id,
        "tnea_application_number": allot.tnea_application_number,
        "allotment_number": allot.allotment_number,
        "college_code": allot.college_code,
        "college_name": allot.college_name,
        "branch_code": allot.branch_code,
        "branch_name": allot.branch_name,
        "community": allot.community,
        "quota": allot.quota,
        "cutoff_mark": allot.cutoff_mark,
        "allotment_date": allot.allotment_date,
        "joining_deadline": allot.joining_deadline,
        "allotment_status": allot.allotment_status,
        "source": allot.source,
        "imported_at": allot.imported_at,
        "student_name": student.full_name if student else None,
        "admission_status": app.status if app else (student.status if student else "ALLOTTED"),
    }

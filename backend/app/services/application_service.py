from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.admission import AdmissionApplication, AdmissionStatusHistory
from app.models.student import Student
from app.models.tnea_allotment import TNEAAllotment
from app.schemas.application import (
    ApplicationDraftUpdate,
    ApplicationCompletionResponse,
    SectionCompletion,
    ApplicationDetailResponse,
)
from app.services.checklist_service import ChecklistService
from app.core.state_machine import (
    AdmissionState,
    UserRole,
    validate_and_transition,
    InvalidStateTransitionError,
    UnauthorizedTransitionError,
)


class ApplicationService:
    @staticmethod
    async def generate_application_number(db: AsyncSession) -> str:
        """
        Generates a standardized admission application number: XYZADM202600001
        """
        stmt = select(func.count(AdmissionApplication.id))
        res = await db.execute(stmt)
        count = res.scalar() or 0
        return f"XYZADM2026{count + 1:05d}"

    @classmethod
    async def get_or_initialize_application(
        cls, db: AsyncSession, student: Student
    ) -> AdmissionApplication:
        """
        Retrieves the admission application for a student, or initializes it
        with prefilled read-only allotment metadata.
        """
        stmt = select(AdmissionApplication).where(AdmissionApplication.student_id == student.id)
        res = await db.execute(stmt)
        app = res.scalar_one_or_none()

        if not app:
            # Fetch TNEA allotment info if available
            allotment_stmt = select(TNEAAllotment).where(TNEAAllotment.student_id == student.id)
            allotment_res = await db.execute(allotment_stmt)
            allotment = allotment_res.scalar_one_or_none()

            app_number = await cls.generate_application_number(db)
            is_fg = (student.quota or "").upper() == "FIRST GRADUATE"
            is_75 = "7.5" in (student.quota or "")

            app = AdmissionApplication(
                student_id=student.id,
                application_number=app_number,
                status="ACTIVATED",
                completion_percentage=20,
                gender=None,
                nationality="Indian",
                state="Tamil Nadu",
                caste=student.community,
                allotment_order_number=allotment.allotment_number if allotment else f"ALT-{student.tnea_application_number}",
                allotment_quota=student.quota or (allotment.quota if allotment else "General"),
                allotted_category=student.community or (allotment.community if allotment else "OC"),
                allotted_college_code=allotment.college_code if allotment else "XYZ",
                allotted_branch_name=student.allotted_branch or (allotment.branch_name if allotment else None),
                is_first_graduate=is_fg,
                is_7_5_govt_quota=is_75,
                personal_data={
                    "candidate_name": student.full_name,
                    "dob": student.date_of_birth.isoformat() if student.date_of_birth else None,
                    "mobile": student.mobile,
                    "email": student.email,
                    "community": student.community,
                },
                academic_data={
                    "allotted_branch": student.allotted_branch,
                    "quota": student.quota,
                    "tnea_app_no": student.tnea_application_number
                }
            )
            db.add(app)
            await db.commit()
            await db.refresh(app)

        elif not app.application_number:
            app.application_number = await cls.generate_application_number(db)
            await db.commit()
            await db.refresh(app)

        return app

    @classmethod
    async def evaluate_completion(
        cls, db: AsyncSession, app: AdmissionApplication, student: Optional[Student] = None
    ) -> ApplicationCompletionResponse:
        """
        Calculates field-level section completion, uploaded mandatory document status,
        and submission readiness.
        """
        sections: Dict[str, SectionCompletion] = {}
        blockers: List[str] = []

        # 1. Personal & Identity Details
        personal_fields = {
            "Gender": app.gender,
            "Blood Group": app.blood_group,
            "Nationality": app.nationality,
            "Religion": app.religion,
            "Caste / Community": app.caste,
            "Mother Tongue": app.mother_tongue,
            "Aadhaar Number": app.aadhaar_number,
        }
        missing_personal = [k for k, v in personal_fields.items() if not v]
        sections["personal"] = SectionCompletion(
            completed=len(missing_personal) == 0,
            fields_filled=len(personal_fields) - len(missing_personal),
            fields_total=len(personal_fields),
            missing_fields=missing_personal,
        )
        if missing_personal:
            blockers.append(f"Personal Details incomplete: missing {', '.join(missing_personal)}")

        # 2. Contact & Address
        contact_fields = {
            "Address Line 1": app.address_line1,
            "City": app.city,
            "District": app.district,
            "State": app.state,
            "Pincode": app.pincode,
            "Emergency Contact Name": app.emergency_contact_name,
            "Emergency Contact Phone": app.emergency_contact_phone,
            "Emergency Contact Relation": app.emergency_contact_relation,
        }
        missing_contact = [k for k, v in contact_fields.items() if not v]
        sections["contact"] = SectionCompletion(
            completed=len(missing_contact) == 0,
            fields_filled=len(contact_fields) - len(missing_contact),
            fields_total=len(contact_fields),
            missing_fields=missing_contact,
        )
        if missing_contact:
            blockers.append(f"Address & Emergency Contact incomplete: missing {', '.join(missing_contact)}")

        # 3. Parents / Guardian
        has_father = bool(app.father_name and app.father_mobile)
        has_mother = bool(app.mother_name and app.mother_mobile)
        has_guardian = bool(app.guardian_name and app.guardian_mobile)
        has_income = bool(app.annual_family_income and app.annual_family_income > 0)

        missing_parent = []
        if not (has_father or has_mother or has_guardian):
            missing_parent.append("At least one Parent/Guardian details (Name & Mobile)")
        if not has_income:
            missing_parent.append("Annual Family Income")

        sections["parent"] = SectionCompletion(
            completed=len(missing_parent) == 0,
            fields_filled=2 - len(missing_parent),
            fields_total=2,
            missing_fields=missing_parent,
        )
        if missing_parent:
            blockers.append(f"Parent/Guardian details incomplete: {', '.join(missing_parent)}")

        # 4. Academic Marks (10th & 12th)
        academic_fields = {
            "10th School Name": app.tenth_school_name,
            "10th Board": app.tenth_board,
            "10th Year": app.tenth_year_of_passing,
            "10th Reg No": app.tenth_registration_number,
            "10th Marks": app.tenth_total_marks,
            "12th School Name": app.twelfth_school_name,
            "12th Board": app.twelfth_board,
            "12th Year": app.twelfth_year_of_passing,
            "12th Reg No": app.twelfth_registration_number,
            "12th Total Marks": app.twelfth_total_marks,
            "12th Maths Marks": app.twelfth_maths_marks,
            "12th Physics Marks": app.twelfth_physics_marks,
            "12th Chemistry Marks": app.twelfth_chemistry_marks,
            "12th Cutoff Marks": app.twelfth_cutoff_marks,
        }
        missing_academic = [k for k, v in academic_fields.items() if v is None or v == ""]
        sections["academic"] = SectionCompletion(
            completed=len(missing_academic) == 0,
            fields_filled=len(academic_fields) - len(missing_academic),
            fields_total=len(academic_fields),
            missing_fields=missing_academic,
        )
        if missing_academic:
            blockers.append(f"Academic Details incomplete: missing {', '.join(missing_academic[:4])}...")

        # 5. Documents
        checklist = await ChecklistService.get_checklist_for_application(db, app, student)
        mandatory_docs = [item for item in checklist if item.is_mandatory]
        mandatory_uploaded = [item for item in mandatory_docs if item.document_status != "NOT_UPLOADED"]
        all_uploaded = [item for item in checklist if item.document_status != "NOT_UPLOADED"]

        missing_docs = [item.name for item in mandatory_docs if item.document_status == "NOT_UPLOADED"]
        sections["documents"] = SectionCompletion(
            completed=len(missing_docs) == 0,
            fields_filled=len(mandatory_uploaded),
            fields_total=len(mandatory_docs),
            missing_fields=missing_docs,
        )
        if missing_docs:
            blockers.append(f"Mandatory documents pending upload: {', '.join(missing_docs)}")

        # 6. Declaration
        if not app.declaration_accepted:
            blockers.append("Declaration not accepted by candidate")

        # Calculate weighted overall percentage
        sec_weights = {
            "personal": 0.20,
            "contact": 0.15,
            "parent": 0.15,
            "academic": 0.25,
            "documents": 0.25,
        }
        overall = 0.0
        for sec_name, weight in sec_weights.items():
            sec = sections.get(sec_name)
            if sec and sec.fields_total > 0:
                ratio = min(1.0, sec.fields_filled / sec.fields_total)
                overall += ratio * weight * 100.0

        overall_percentage = int(min(100.0, max(0.0, overall)))

        can_submit = (len(blockers) == 0 and app.status in ["ACTIVATED", "APPLICATION_IN_PROGRESS"])

        return ApplicationCompletionResponse(
            overall_percentage=overall_percentage,
            sections=sections,
            documents_uploaded=len(all_uploaded),
            mandatory_documents_total=len(mandatory_docs),
            mandatory_documents_uploaded=len(mandatory_uploaded),
            can_submit=can_submit,
            blockers=blockers,
        )

    @classmethod
    async def update_draft(
        cls,
        db: AsyncSession,
        app: AdmissionApplication,
        draft: ApplicationDraftUpdate,
        student: Student
    ) -> AdmissionApplication:
        """
        Saves application form draft values and recalculates completion progress.
        """
        if app.status in ["APPLICATION_SUBMITTED", "DOCUMENT_REVIEW", "DOCUMENTS_VERIFIED", "ADMISSION_CONFIRMED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify application in status '{app.status}'. Application is already submitted."
            )

        # Update non-null draft fields
        update_data = draft.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if hasattr(app, key):
                setattr(app, key, val)

        # Update status from ACTIVATED to APPLICATION_IN_PROGRESS if user started filling
        if app.status == "ACTIVATED":
            app.status = "APPLICATION_IN_PROGRESS"
            student.status = "APPLICATION_IN_PROGRESS"

        # Calculate new completion %
        completion_info = await cls.evaluate_completion(db, app, student)
        app.completion_percentage = completion_info.overall_percentage
        app.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(app)
        return app

    @classmethod
    async def submit_application(
        cls,
        db: AsyncSession,
        app: AdmissionApplication,
        student: Student,
        declaration_accepted: bool
    ) -> AdmissionApplication:
        """
        Validates all mandatory fields and documents, records declaration acceptance,
        and transitions application to APPLICATION_SUBMITTED.
        """
        if not declaration_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must accept the final declaration before submitting your application."
            )

        app.declaration_accepted = True
        app.declaration_accepted_at = datetime.now(timezone.utc)

        completion = await cls.evaluate_completion(db, app, student)
        if not completion.can_submit and len(completion.blockers) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit application. Unresolved items: {'; '.join(completion.blockers)}"
            )

        # Validate State Transition
        try:
            current_st = AdmissionState(app.status)
            target_st = AdmissionState.APPLICATION_SUBMITTED
            actor_role = UserRole.STUDENT
            validate_and_transition(current_st, target_st, actor_role)
        except (InvalidStateTransitionError, UnauthorizedTransitionError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        prev_status = app.status
        now = datetime.now(timezone.utc)

        app.status = "APPLICATION_SUBMITTED"
        app.submitted_at = now
        app.completion_percentage = 100
        app.updated_at = now
        student.status = "APPLICATION_SUBMITTED"
        student.updated_at = now

        # Record History
        history = AdmissionStatusHistory(
            admission_application_id=app.id,
            previous_status=prev_status,
            new_status="APPLICATION_SUBMITTED",
            changed_by=student.email,
            actor_role="STUDENT",
            reason="Candidate successfully completed application form and submitted required documents with signed digital declaration.",
            metadata_info={
                "application_number": app.application_number,
                "mandatory_documents_verified_count": completion.mandatory_documents_uploaded
            }
        )
        db.add(history)

        await db.commit()
        await db.refresh(app)
        await db.refresh(student)

        return app

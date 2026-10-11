import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from fastapi import HTTPException, status

from app.core.state_machine import AdmissionState
from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.user import User
from app.models.onboarding import (
    StudentType,
    StudentTypeStatus,
    OnboardingStatus,
    ParentLinkStatus,
    ChecklistCategory,
    StudentTypeScope,
    GuidanceCategory,
    EventStatus,
    OnboardingProfile,
    ParentGuardian,
    StudentGuardianLink,
    OnboardingChecklistItem,
    OnboardingGuidanceConfiguration,
    InaugurationEvent,
    TransportConfiguration,
    OnboardingAuditLog,
)


def is_admission_confirmed(application: Optional[AdmissionApplication]) -> bool:
    """Centralized authoritative predicate checking whether admission is confirmed."""
    if not application:
        return False
    # Authoritative confirmed states in AdmissionAI lifecycle
    return application.status in [
        AdmissionState.ADMISSION_CONFIRMED,
        AdmissionState.ERP_SYNC_PENDING,
        AdmissionState.ERP_SYNCED,
        AdmissionState.ONBOARDING,
        AdmissionState.INDUCTION_READY,
        AdmissionState.ACTIVE_STUDENT,
    ]


class OnboardingEligibilityService:
    @staticmethod
    async def check_eligibility(db: AsyncSession, student_id: str) -> Tuple[bool, str, Optional[AdmissionApplication]]:
        """Authoritative onboarding eligibility check for a student."""
        stmt = select(AdmissionApplication).where(AdmissionApplication.student_id == student_id)
        res = await db.execute(stmt)
        application = res.scalars().first()

        if not application:
            return False, "Admission application not found.", None

        if not is_admission_confirmed(application):
            return False, "Onboarding will become available after admission confirmation.", application

        return True, "Candidate is eligible for onboarding.", application

    @staticmethod
    async def require_eligible(db: AsyncSession, student_id: str) -> AdmissionApplication:
        """Enforces eligibility, raising 403 HTTP error if not eligible."""
        eligible, reason, application = await OnboardingEligibilityService.check_eligibility(db, student_id)
        if not eligible or not application:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=reason or "Onboarding will become available after admission confirmation.",
            )
        return application


DEFAULT_CHECKLIST_TEMPLATE = [
    # Scope: ALL
    {
        "item_key": "CAMPUS_ID_CARD",
        "title": "Upload photo & details for College ID Card & Smart Card",
        "category": "GENERAL",
        "student_type_scope": "ALL",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 1",
        "sort_order": 1,
    },
    {
        "item_key": "LAPTOP_GUIDANCE",
        "title": "Review First-Year Recommended Laptop Specifications (Core i5/Ryzen 5, 16GB RAM)",
        "category": "ACADEMIC",
        "student_type_scope": "ALL",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 2",
        "sort_order": 2,
    },
    {
        "item_key": "FACULTY_MEMBER_INFO",
        "title": "Note details of assigned Faculty Member & contact information",
        "category": "ACADEMIC",
        "student_type_scope": "ALL",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 3",
        "sort_order": 3,
    },
    {
        "item_key": "COUNSELLOR_INFO",
        "title": "Review assigned Counsellor, HoD, and Branch Coordinator details",
        "category": "ACADEMIC",
        "student_type_scope": "ALL",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 4",
        "sort_order": 4,
    },
    {
        "item_key": "ACADEMIC_COMMUNICATION",
        "title": "Acknowledge Official Academic Communication Channel (Parents' WhatsApp group)",
        "category": "PARENT",
        "student_type_scope": "ALL",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 5",
        "sort_order": 5,
    },
    {
        "item_key": "INAUGURATION_DETAILS",
        "title": "Review First-Year Inauguration Ceremony schedule (31.08.2026) & guidelines",
        "category": "GENERAL",
        "student_type_scope": "ALL",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 6",
        "sort_order": 6,
    },
    {
        "item_key": "DRESS_CODE",
        "title": "Acknowledge Campus Dress Code Policy (Formal attire for Boys & Girls)",
        "category": "GENERAL",
        "student_type_scope": "ALL",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 7",
        "sort_order": 7,
    },
    # Scope: DAY_SCHOLAR
    {
        "item_key": "DAY_SCHOLAR_TRANSPORT",
        "title": "Review College Bus Routes, Timings & Boarding Point instructions",
        "category": "DAY_SCHOLAR",
        "student_type_scope": "DAY_SCHOLAR",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 8",
        "sort_order": 8,
    },
    {
        "item_key": "DAY_SCHOLAR_MOBILE",
        "title": "Acknowledge Day-Scholar Mobile Phone Campus Usage Policy",
        "category": "DAY_SCHOLAR",
        "student_type_scope": "DAY_SCHOLAR",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 9",
        "sort_order": 9,
    },
    # Scope: HOSTELLER
    {
        "item_key": "HOSTEL_RULES",
        "title": "Acknowledge Hostel Code of Conduct & Dining Guidelines",
        "category": "HOSTELLER",
        "student_type_scope": "HOSTELLER",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 10",
        "sort_order": 8,
    },
    {
        "item_key": "HOSTEL_MOBILE_GUIDANCE",
        "title": "Acknowledge Hosteller mobile-phone guidance",
        "category": "HOSTELLER",
        "student_type_scope": "HOSTELLER",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 11",
        "sort_order": 9,
    },
    {
        "item_key": "HOSTEL_PERSONAL_ITEMS",
        "title": "Prepare personal items and necessities checklist for hostel stay",
        "category": "HOSTELLER",
        "student_type_scope": "HOSTELLER",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 12",
        "sort_order": 10,
    },
    {
        "item_key": "HOSTEL_VISITORS_FORM",
        "title": "Submit Authorized Visitors' Form with Parent/Guardian signatures",
        "category": "HOSTELLER",
        "student_type_scope": "HOSTELLER",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 13",
        "sort_order": 11,
    },
    {
        "item_key": "HOSTEL_GATE_PASS",
        "title": "Review Hostel Gate-Pass, Outing and Leave permissions protocol",
        "category": "HOSTELLER",
        "student_type_scope": "HOSTELLER",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 14",
        "sort_order": 12,
    },
    {
        "item_key": "HOSTEL_FOOD_POLICY",
        "title": "Acknowledge prohibition of outside cooked food deliveries in hostel rooms",
        "category": "HOSTELLER",
        "student_type_scope": "HOSTELLER",
        "is_mandatory": True,
        "source_reference": "General Instructions to be informed to all students - Section 15",
        "sort_order": 13,
    },
]


class OnboardingService:
    @staticmethod
    async def log_audit(
        db: AsyncSession,
        actor_id: str,
        actor_role: str,
        action: str,
        profile_id: Optional[str] = None,
        student_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> OnboardingAuditLog:
        """Helper to append an entry to OnboardingAuditLog."""
        log = OnboardingAuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            profile_id=profile_id,
            student_id=student_id,
            details_json=details or {},
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def get_or_create_profile(db: AsyncSession, student_id: str) -> OnboardingProfile:
        """Fetches or creates the OnboardingProfile for an eligible student."""
        application = await OnboardingEligibilityService.require_eligible(db, student_id)

        stmt = select(OnboardingProfile).where(OnboardingProfile.student_id == student_id)
        res = await db.execute(stmt)
        profile = res.scalars().first()

        if not profile:
            profile = OnboardingProfile(
                student_id=student_id,
                application_id=application.id,
                academic_year="2026-27",
                student_type=StudentType.UNSPECIFIED,
                student_type_status=StudentTypeStatus.UNSPECIFIED,
                onboarding_status=OnboardingStatus.ONBOARDING_PROFILE_PENDING,
                overall_completion_percentage=0,
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

            # Sync initial checklist
            await OnboardingService.sync_checklist_items(db, profile)

            await OnboardingService.log_audit(
                db=db,
                actor_id=student_id,
                actor_role="STUDENT",
                action="ONBOARDING_PROFILE_CREATED",
                profile_id=profile.id,
                student_id=student_id,
                details={"status": profile.onboarding_status.value},
            )
        else:
            await OnboardingService.sync_checklist_items(db, profile)

        return profile

    @staticmethod
    async def sync_checklist_items(db: AsyncSession, profile: OnboardingProfile) -> List[OnboardingChecklistItem]:
        """Dynamically synchronizes checklist items based on student type."""
        stmt = select(OnboardingChecklistItem).where(OnboardingChecklistItem.profile_id == profile.id)
        res = await db.execute(stmt)
        existing_items = res.scalars().all()
        existing_keys = {item.item_key: item for item in existing_items}

        student_type_val = profile.student_type.value if hasattr(profile.student_type, "value") else str(profile.student_type)

        applicable_templates = []
        for tmpl in DEFAULT_CHECKLIST_TEMPLATE:
            scope = tmpl["student_type_scope"]
            if scope == "ALL":
                applicable_templates.append(tmpl)
            elif scope == "DAY_SCHOLAR" and student_type_val == "DAY_SCHOLAR":
                applicable_templates.append(tmpl)
            elif scope == "HOSTELLER" and student_type_val == "HOSTELLER":
                applicable_templates.append(tmpl)

        new_items = []
        for tmpl in applicable_templates:
            key = tmpl["item_key"]
            if key not in existing_keys:
                item = OnboardingChecklistItem(
                    profile_id=profile.id,
                    item_key=key,
                    title=tmpl["title"],
                    category=tmpl["category"],
                    student_type_scope=tmpl["student_type_scope"],
                    is_mandatory=tmpl["is_mandatory"],
                    is_acknowledged=False,
                    source_reference=tmpl["source_reference"],
                    sort_order=tmpl["sort_order"],
                )
                db.add(item)
                new_items.append(item)

        if new_items:
            await db.commit()

        await OnboardingService.recalculate_progress(db, profile)

        stmt_all = (
            select(OnboardingChecklistItem)
            .where(OnboardingChecklistItem.profile_id == profile.id)
            .order_by(OnboardingChecklistItem.sort_order.asc())
        )
        res_all = await db.execute(stmt_all)
        return list(res_all.scalars().all())

    @staticmethod
    async def recalculate_progress(db: AsyncSession, profile: OnboardingProfile) -> None:
        """Recalculates completion percentage and updates lifecycle status."""
        stmt = select(OnboardingChecklistItem).where(OnboardingChecklistItem.profile_id == profile.id)
        res = await db.execute(stmt)
        items = res.scalars().all()

        student_type_val = profile.student_type.value if hasattr(profile.student_type, "value") else str(profile.student_type)

        # Filter applicable items
        applicable_items = [
            i for i in items
            if i.student_type_scope == "ALL" or i.student_type_scope == student_type_val
        ]

        total = len(applicable_items)
        acknowledged = sum(1 for i in applicable_items if i.is_acknowledged)

        percentage = int((acknowledged / total) * 100) if total > 0 else 0
        profile.overall_completion_percentage = percentage

        if profile.student_type_status == StudentTypeStatus.UNSPECIFIED:
            profile.onboarding_status = OnboardingStatus.ONBOARDING_PROFILE_PENDING
        elif percentage == 100:
            profile.onboarding_status = OnboardingStatus.INDUCTION_READY
        elif percentage > 0:
            profile.onboarding_status = OnboardingStatus.ONBOARDING_CHECKLIST_ACTIVE
        else:
            profile.onboarding_status = OnboardingStatus.ONBOARDING_IN_PROGRESS

        await db.commit()
        await db.refresh(profile)

    @staticmethod
    async def request_student_type(
        db: AsyncSession,
        student_id: str,
        student_type: StudentType,
        actor_id: str,
        actor_role: str,
    ) -> OnboardingProfile:
        """Controlled student type selection requested by student."""
        profile = await OnboardingService.get_or_create_profile(db, student_id)

        old_type = profile.student_type
        profile.student_type = student_type
        profile.student_type_status = StudentTypeStatus.STUDENT_REQUESTED

        await db.commit()
        await db.refresh(profile)

        await OnboardingService.sync_checklist_items(db, profile)

        await OnboardingService.log_audit(
            db=db,
            actor_id=actor_id,
            actor_role=actor_role,
            action="STUDENT_TYPE_REQUESTED",
            profile_id=profile.id,
            student_id=student_id,
            details={
                "old_student_type": old_type.value if hasattr(old_type, "value") else str(old_type),
                "new_student_type": student_type.value if hasattr(student_type, "value") else str(student_type),
                "status": profile.student_type_status.value,
            },
        )
        return profile

    @staticmethod
    async def confirm_student_type(
        db: AsyncSession,
        student_id: str,
        student_type: StudentType,
        actor_id: str,
        actor_role: str,
    ) -> OnboardingProfile:
        """Controlled student type confirmation by admin."""
        profile = await OnboardingService.get_or_create_profile(db, student_id)

        old_type = profile.student_type
        profile.student_type = student_type
        profile.student_type_status = StudentTypeStatus.ADMIN_CONFIRMED

        await db.commit()
        await db.refresh(profile)

        await OnboardingService.sync_checklist_items(db, profile)

        await OnboardingService.log_audit(
            db=db,
            actor_id=actor_id,
            actor_role=actor_role,
            action="STUDENT_TYPE_CONFIRMED",
            profile_id=profile.id,
            student_id=student_id,
            details={
                "old_student_type": old_type.value if hasattr(old_type, "value") else str(old_type),
                "new_student_type": student_type.value if hasattr(student_type, "value") else str(student_type),
                "confirmed_by": actor_id,
            },
        )
        return profile

    @staticmethod
    async def acknowledge_checklist_item(
        db: AsyncSession,
        profile_id: str,
        item_key: str,
        student_id: str,
    ) -> OnboardingChecklistItem:
        """Acknowledges a checklist item as the single source of truth."""
        stmt = select(OnboardingProfile).where(OnboardingProfile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalars().first()
        if not profile:
            raise HTTPException(status_code=404, detail="Onboarding profile not found.")

        if profile.student_id != student_id:
            raise HTTPException(status_code=403, detail="Forbidden: You cannot modify another student's checklist.")

        stmt_item = select(OnboardingChecklistItem).where(
            and_(
                OnboardingChecklistItem.profile_id == profile.id,
                OnboardingChecklistItem.item_key == item_key,
            )
        )
        res_item = await db.execute(stmt_item)
        item = res_item.scalars().first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Checklist item '{item_key}' not found.")

        item.is_acknowledged = True
        item.acknowledged_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(item)

        await OnboardingService.recalculate_progress(db, profile)

        await OnboardingService.log_audit(
            db=db,
            actor_id=student_id,
            actor_role="STUDENT",
            action="CHECKLIST_ACKNOWLEDGED",
            profile_id=profile.id,
            student_id=student_id,
            details={
                "item_key": item_key,
                "overall_completion_percentage": profile.overall_completion_percentage,
                "onboarding_status": profile.onboarding_status.value,
            },
        )
        return item

    @staticmethod
    async def create_parent_invitation(
        db: AsyncSession,
        student_id: str,
        name: str,
        phone: str,
        email: Optional[str],
        relationship: str,
    ) -> Dict[str, Any]:
        """Creates a secure parent invitation with hashed token storage."""
        await OnboardingEligibilityService.require_eligible(db, student_id)
        profile = await OnboardingService.get_or_create_profile(db, student_id)

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        link = StudentGuardianLink(
            student_id=student_id,
            guardian_id=None,
            invite_token_hash=token_hash,
            token_expires_at=expires_at,
            relationship=relationship.upper(),
            status=ParentLinkStatus.PENDING,
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)

        await OnboardingService.log_audit(
            db=db,
            actor_id=student_id,
            actor_role="STUDENT",
            action="PARENT_INVITE_CREATED",
            profile_id=profile.id,
            student_id=student_id,
            details={
                "link_id": link.id,
                "relationship": link.relationship,
                "expires_at": expires_at.isoformat(),
            },
        )

        return {
            "link_id": link.id,
            "invite_token": raw_token,  # Raw token returned only in immediate response
            "relationship": link.relationship,
            "expires_at": expires_at.isoformat(),
            "status": link.status.value,
        }

    @staticmethod
    async def redeem_parent_invitation(
        db: AsyncSession,
        raw_token: str,
        parent_user_id: str,
        parent_name: str,
        parent_phone: str,
        parent_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Redeems an invitation token via SHA-256 hash lookup."""
        token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()

        stmt = select(StudentGuardianLink).where(StudentGuardianLink.invite_token_hash == token_hash)
        res = await db.execute(stmt)
        link = res.scalars().first()

        if not link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or unrecognized invitation token.",
            )

        if link.status != ParentLinkStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation token is already {link.status.value.lower()}.",
            )

        now = datetime.now(timezone.utc)
        expires = link.token_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if expires < now:
            link.status = ParentLinkStatus.EXPIRED
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation token has expired.",
            )

        # Create or update ParentGuardian
        stmt_g = select(ParentGuardian).where(ParentGuardian.user_id == parent_user_id)
        res_g = await db.execute(stmt_g)
        guardian = res_g.scalars().first()

        if not guardian:
            guardian = ParentGuardian(
                user_id=parent_user_id,
                name=parent_name,
                phone=parent_phone,
                email=parent_email,
                relationship=link.relationship,
            )
            db.add(guardian)
            await db.commit()
            await db.refresh(guardian)
        else:
            guardian.name = parent_name
            guardian.phone = parent_phone
            if parent_email:
                guardian.email = parent_email
            await db.commit()

        link.guardian_id = guardian.id
        link.status = ParentLinkStatus.ACTIVE
        link.token_used_at = now
        await db.commit()
        await db.refresh(link)

        await OnboardingService.log_audit(
            db=db,
            actor_id=parent_user_id,
            actor_role="PARENT",
            action="PARENT_LINK_ACTIVATED",
            student_id=link.student_id,
            details={
                "link_id": link.id,
                "guardian_id": guardian.id,
                "relationship": link.relationship,
            },
        )

        return {
            "success": True,
            "message": "Parent account successfully linked to student.",
            "link_id": link.id,
            "student_id": link.student_id,
            "relationship": link.relationship,
            "status": link.status.value,
        }

    @staticmethod
    async def get_inauguration_info(db: AsyncSession, academic_year: str = "2026-27") -> Dict[str, Any]:
        """Calculates dynamic inauguration event status (UPCOMING / TODAY / PAST)."""
        stmt = select(InaugurationEvent).where(
            and_(
                InaugurationEvent.academic_year == academic_year,
                InaugurationEvent.is_active.is_(True),
            )
        )
        res = await db.execute(stmt)
        event = res.scalars().first()

        if not event:
            event = InaugurationEvent(
                academic_year=academic_year,
                event_name="First-Year Inauguration Ceremony",
                event_date="2026-08-31",
                reporting_time="08:30 AM",
                ceremony_time="09:30 AM",
                venue="Main College Auditorium, Campus Block A",
                instructions_student="Formal dress code strictly required. Please arrive on time with your admission confirmation slip.",
                instructions_parent="Parents and guardians are cordially invited. Refreshments and lunch will be provided.",
                is_active=True,
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        event_date_str = event.event_date

        if event_date_str == today_str:
            calculated_status = EventStatus.TODAY.value
        elif event_date_str > today_str:
            calculated_status = EventStatus.UPCOMING.value
        else:
            calculated_status = EventStatus.PAST.value

        return {
            "id": event.id,
            "academic_year": event.academic_year,
            "event_name": event.event_name,
            "event_date": event.event_date,
            "reporting_time": event.reporting_time,
            "ceremony_time": event.ceremony_time,
            "venue": event.venue,
            "instructions_student": event.instructions_student,
            "instructions_parent": event.instructions_parent,
            "event_status": calculated_status,
        }

    @staticmethod
    async def get_transport_info(db: AsyncSession, college_code: str = "XYZ") -> Dict[str, Any]:
        """Returns transport information without hardcoding external URLs."""
        stmt = select(TransportConfiguration).where(TransportConfiguration.college_code == college_code)
        res = await db.execute(stmt)
        config = res.scalars().first()

        if not config or not config.is_configured:
            return {
                "is_configured": False,
                "college_code": college_code,
                "message": "Information not configured for this prototype.",
                "routes": [],
                "general_instructions": "College bus routes and timings will be communicated before inauguration.",
            }
        return {
            "is_configured": True,
            "college_code": config.college_code,
            "routes": config.routes_json or [],
            "general_instructions": config.general_instructions,
        }

    @staticmethod
    def get_guidance_cards(student_type: StudentType = StudentType.UNSPECIFIED) -> List[Dict[str, Any]]:
        """Returns institutional guidance cards with accurate terminology."""
        student_type_str = student_type.value if hasattr(student_type, "value") else str(student_type)

        cards = [
            {
                "category": "CONTACTS",
                "title": "Faculty Member & Academic Leadership Directory",
                "source_reference": "General Instructions to be informed to all students",
                "data": {
                    "faculty_member_role": "Faculty Member",
                    "description": "Each student is assigned a dedicated Faculty Member for academic guidance and mentorship.",
                    "counsellor_role": "Department Counsellor",
                    "hod_role": "Head of Department (HoD)",
                    "branch_coordinator_role": "First-Year Branch Coordinator",
                },
            },
            {
                "category": "COMMUNICATION",
                "title": "Academic Communication Channel",
                "source_reference": "General Instructions to be informed to all students",
                "data": {
                    "primary_channel": "Official Parents' WhatsApp Group",
                    "description": "Attendance alerts, internal test marks, circulars, and semester schedules are shared directly with parents via the official group.",
                },
            },
            {
                "category": "DRESS_CODE",
                "title": "Campus Dress Code Policy",
                "source_reference": "General Instructions to be informed to all students",
                "data": {
                    "boys": "Formal shirts tucked in with formal trousers and leather shoes. T-shirts and jeans are strictly prohibited during academic hours.",
                    "girls": "Formal churidar with dupatta pinned on both sides or formal salwar kameez. Loose hair and casual footwear are prohibited.",
                },
            },
            {
                "category": "LAPTOP",
                "title": "First-Year Laptop Specification Guidance",
                "source_reference": "General Instructions to be informed to all students",
                "data": {
                    "processor": "Intel Core i5 (12th Gen+) or AMD Ryzen 5 (5000 series+)",
                    "ram": "16 GB DDR4/DDR5 recommended (Minimum 8 GB)",
                    "storage": "512 GB NVMe SSD",
                    "operating_system": "Windows 11 / Linux dual-boot supported",
                },
            },
            {
                "category": "GENERAL",
                "title": "Placement & Career Development Disclosure",
                "source_reference": "General Instructions to be informed to all students",
                "attribution": "Institution-Provided Information (Not independently verified by AdmissionAI)",
                "data": {
                    "placement_highlight": "The institution reports an 85% placement record for eligible students across leading engineering recruiters.",
                    "training_programs": "Value-added industry skills training commences from Semester 2 onwards.",
                },
            },
        ]

        if student_type_str == "DAY_SCHOLAR":
            cards.append({
                "category": "DAY_SCHOLAR_RULES",
                "title": "Day-Scholar Campus & Transportation Guidelines",
                "source_reference": "General Instructions to be informed to all students",
                "data": {
                    "bus_instructions": "Day-scholars using college transport must board at designated stops with valid bus passes.",
                    "mobile_policy": "Mobile phones must remain switched off and kept inside bags during class hours.",
                },
            })
        elif student_type_str == "HOSTELLER":
            cards.append({
                "category": "HOSTELLER_RULES",
                "title": "Hostel Life, Necessities & Mobile-Phone Guidance",
                "source_reference": "General Instructions to be informed to all students",
                "data": {
                    "mobile_guidance": "Hosteller mobile-phone guidance: Mobile usage is permitted only in hostel rooms during non-study hours; strictly forbidden during study hours (08:30 PM - 10:30 PM).",
                    "food_delivery_policy": "Outside cooked food delivery is strictly prohibited in hostel premises.",
                    "visitors_form": "Parents must submit the Authorized Visitors' Form along with authorized photos at check-in.",
                    "gate_pass": "Hostel outpass must be approved by the Resident Warden and verified by parent SMS/phone.",
                    "personal_items": "Students should bring their own mattress, pillow, bedsheets, bucket, mug, lock & keys, and study lamp.",
                },
            })

        return cards

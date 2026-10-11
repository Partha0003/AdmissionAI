from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database.session import get_db
from app.models.user import User
from app.models.student import Student
from app.models.onboarding import (
    StudentType,
    StudentTypeStatus,
    OnboardingProfile,
    OnboardingChecklistItem,
    OnboardingAuditLog,
    InaugurationEvent,
    TransportConfiguration,
)
from app.api.deps import get_current_user, get_current_student, require_roles
from app.services.onboarding_service import (
    OnboardingService,
    OnboardingEligibilityService,
)
from app.schemas.onboarding import (
    StudentTypeRequest,
    StudentTypeConfirmRequest,
    OnboardingProfileResponse,
    ChecklistItemResponse,
    ParentInvitationCreate,
    ParentInvitationResponse,
    GuidanceCardResponse,
    InaugurationEventResponse,
    TransportConfigResponse,
    OnboardingAuditLogResponse,
)

router = APIRouter(tags=["Onboarding & Student Induction"])


def build_profile_response(profile: OnboardingProfile, checklist_items: List[OnboardingChecklistItem]) -> OnboardingProfileResponse:
    """Builds a serializable OnboardingProfileResponse from profile and checklist items."""
    return OnboardingProfileResponse(
        id=str(profile.id),
        student_id=str(profile.student_id),
        application_id=str(profile.application_id),
        academic_year=str(profile.academic_year),
        student_type=profile.student_type,
        student_type_status=profile.student_type_status,
        onboarding_status=profile.onboarding_status,
        overall_completion_percentage=profile.overall_completion_percentage,
        checklist_items=checklist_items,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# ==============================================================================
# STUDENT ONBOARDING ENDPOINTS
# ==============================================================================

@router.get("/onboarding/me", response_model=OnboardingProfileResponse)
async def get_my_onboarding_profile(
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Retrieve the current student's onboarding profile and checklist."""
    profile = await OnboardingService.get_or_create_profile(db, current_student.id)
    items = await OnboardingService.sync_checklist_items(db, profile)
    return build_profile_response(profile, items)


@router.post("/onboarding/me/student-type", response_model=OnboardingProfileResponse)
async def request_student_type(
    payload: StudentTypeRequest,
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student),
    current_user: User = Depends(get_current_user),
):
    """Request/select student type (DAY_SCHOLAR or HOSTELLER) via controlled workflow."""
    profile = await OnboardingService.request_student_type(
        db=db,
        student_id=current_student.id,
        student_type=payload.student_type,
        actor_id=current_user.id,
        actor_role="STUDENT",
    )
    items = await OnboardingService.sync_checklist_items(db, profile)
    return build_profile_response(profile, items)


@router.get("/onboarding/me/checklist", response_model=List[ChecklistItemResponse])
async def get_my_checklist(
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Get all applicable onboarding checklist items for the student."""
    profile = await OnboardingService.get_or_create_profile(db, current_student.id)
    items = await OnboardingService.sync_checklist_items(db, profile)
    return items


@router.post("/onboarding/me/checklist/{item_key}/acknowledge", response_model=ChecklistItemResponse)
async def acknowledge_checklist_item(
    item_key: str,
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Acknowledge a specific onboarding checklist item."""
    profile = await OnboardingService.get_or_create_profile(db, current_student.id)
    item = await OnboardingService.acknowledge_checklist_item(
        db=db,
        profile_id=profile.id,
        item_key=item_key,
        student_id=current_student.id,
    )
    return item


@router.post("/onboarding/me/parent-invitation", response_model=ParentInvitationResponse)
async def create_parent_invitation(
    payload: ParentInvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Generate a cryptographically secure, single-use parent invitation token."""
    res = await OnboardingService.create_parent_invitation(
        db=db,
        student_id=current_student.id,
        name=payload.parent_name,
        phone=payload.phone,
        email=payload.email,
        relationship=payload.relationship,
    )
    return res


@router.get("/onboarding/me/guidance", response_model=List[GuidanceCardResponse])
async def get_student_guidance(
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Retrieve personalized guidance cards based on student type."""
    profile = await OnboardingService.get_or_create_profile(db, current_student.id)
    cards = OnboardingService.get_guidance_cards(profile.student_type)
    return cards


@router.get("/onboarding/me/inauguration", response_model=InaugurationEventResponse)
async def get_student_inauguration(
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Retrieve first-year inauguration details with dynamically computed status."""
    await OnboardingEligibilityService.require_eligible(db, current_student.id)
    info = await OnboardingService.get_inauguration_info(db)
    return info


@router.get("/onboarding/me/transport", response_model=TransportConfigResponse)
async def get_student_transport(
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Retrieve transport information without hardcoded external links."""
    await OnboardingEligibilityService.require_eligible(db, current_student.id)
    info = await OnboardingService.get_transport_info(db)
    return info


# ==============================================================================
# ADMIN ONBOARDING DESK ENDPOINTS
# ==============================================================================

@router.get("/admin/onboarding/profiles", response_model=List[OnboardingProfileResponse])
async def list_onboarding_profiles(
    student_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """List all onboarding profiles with optional filtering."""
    stmt = select(OnboardingProfile).order_by(desc(OnboardingProfile.created_at))
    if student_type:
        stmt = stmt.where(OnboardingProfile.student_type == student_type)
    if status_filter:
        stmt = stmt.where(OnboardingProfile.onboarding_status == status_filter)

    res = await db.execute(stmt)
    profiles = list(res.scalars().all())

    result = []
    for p in profiles:
        items = await OnboardingService.sync_checklist_items(db, p)
        result.append(build_profile_response(p, items))

    return result


@router.post("/admin/onboarding/students/{student_id}/confirm-type", response_model=OnboardingProfileResponse)
async def confirm_student_type(
    student_id: str,
    payload: StudentTypeConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """Admin confirms or overrides the student type."""
    profile = await OnboardingService.confirm_student_type(
        db=db,
        student_id=student_id,
        student_type=payload.student_type,
        actor_id=current_user.id,
        actor_role=current_user.role.name if current_user.role else "ADMIN",
    )
    items = await OnboardingService.sync_checklist_items(db, profile)
    return build_profile_response(profile, items)


@router.post("/admin/onboarding/inauguration", response_model=InaugurationEventResponse)
async def update_inauguration_event(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """Configure or update inauguration ceremony details."""
    stmt = select(InaugurationEvent).where(InaugurationEvent.academic_year == payload.get("academic_year", "2026-27"))
    res = await db.execute(stmt)
    event = res.scalars().first()

    if not event:
        event = InaugurationEvent(
            academic_year=payload.get("academic_year", "2026-27"),
            event_name=payload.get("event_name", "First-Year Inauguration Ceremony"),
            event_date=payload.get("event_date", "2026-08-31"),
            reporting_time=payload.get("reporting_time", "08:30 AM"),
            ceremony_time=payload.get("ceremony_time", "09:30 AM"),
            venue=payload.get("venue", "Main College Auditorium, Campus Block A"),
            instructions_student=payload.get("instructions_student", "Formal dress code strictly required."),
            instructions_parent=payload.get("instructions_parent", "Parents and guardians are cordially invited."),
            is_active=True,
        )
        db.add(event)
    else:
        for k, v in payload.items():
            if hasattr(event, k) and v is not None:
                setattr(event, k, v)

    await db.commit()
    await db.refresh(event)

    info = await OnboardingService.get_inauguration_info(db, event.academic_year)
    return info


@router.post("/admin/onboarding/transport", response_model=TransportConfigResponse)
async def update_transport_config(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """Configure institutional transport routes without copying third-party URLs."""
    stmt = select(TransportConfiguration).where(TransportConfiguration.college_code == payload.get("college_code", "XYZ"))
    res = await db.execute(stmt)
    config = res.scalars().first()

    if not config:
        config = TransportConfiguration(
            college_code=payload.get("college_code", "XYZ"),
            routes_json=payload.get("routes", []),
            general_instructions=payload.get("general_instructions", "College bus routes and timings."),
            is_configured=payload.get("is_configured", True),
        )
        db.add(config)
    else:
        if "routes" in payload:
            config.routes_json = payload["routes"]
        if "general_instructions" in payload:
            config.general_instructions = payload["general_instructions"]
        if "is_configured" in payload:
            config.is_configured = payload["is_configured"]

    await db.commit()
    await db.refresh(config)

    return {
        "is_configured": config.is_configured,
        "college_code": config.college_code,
        "routes": config.routes_json or [],
        "general_instructions": config.general_instructions,
    }


@router.get("/admin/onboarding/audit-logs", response_model=List[OnboardingAuditLogResponse])
async def list_onboarding_audit_logs(
    student_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN_VERIFIER", "ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """Retrieve append-only audit trail for onboarding activities."""
    stmt = select(OnboardingAuditLog).order_by(desc(OnboardingAuditLog.created_at)).limit(limit)
    if student_id:
        stmt = stmt.where(OnboardingAuditLog.student_id == student_id)
    if action:
        stmt = stmt.where(OnboardingAuditLog.action == action)

    res = await db.execute(stmt)
    return list(res.scalars().all())

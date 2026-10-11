from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.database.session import get_db
from app.models.user import User
from app.models.student import Student
from app.models.admission import AdmissionApplication
from app.models.onboarding import (
    ParentGuardian,
    StudentGuardianLink,
    ParentLinkStatus,
    OnboardingProfile,
)
from app.api.deps import get_current_user
from app.services.onboarding_service import OnboardingService
from app.schemas.onboarding import (
    ParentRedeemRequest,
    ParentRedeemResponse,
    OnboardingProfileResponse,
    GuidanceCardResponse,
    InaugurationEventResponse,
)
from app.api.v1.onboarding import build_profile_response

router = APIRouter(prefix="/parent", tags=["Parent Portal"])


@router.post("/redeem-invitation", response_model=ParentRedeemResponse)
async def redeem_parent_invitation(
    payload: ParentRedeemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Redeems an invitation token via SHA-256 hash matching and links parent account."""
    res = await OnboardingService.redeem_parent_invitation(
        db=db,
        raw_token=payload.invite_token,
        parent_user_id=current_user.id,
        parent_name=payload.parent_name,
        parent_phone=payload.phone,
        parent_email=payload.email,
    )
    return res


@router.get("/student", response_model=Dict[str, Any])
async def get_linked_student_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Anti-IDOR Protected: Retrieve basic summary of the linked student."""
    # Find guardian
    stmt_g = select(ParentGuardian).where(ParentGuardian.user_id == current_user.id)
    res_g = await db.execute(stmt_g)
    guardian = res_g.scalars().first()
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No parent profile found. Please redeem your invitation token first.",
        )

    # Find active link
    stmt_l = select(StudentGuardianLink).where(
        and_(
            StudentGuardianLink.guardian_id == guardian.id,
            StudentGuardianLink.status == ParentLinkStatus.ACTIVE,
        )
    )
    res_l = await db.execute(stmt_l)
    link = res_l.scalars().first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active student link found. Please redeem your invitation token.",
        )

    stmt_s = select(Student).where(Student.id == link.student_id)
    res_s = await db.execute(stmt_s)
    student = res_s.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Linked student record not found.")

    stmt_app = select(AdmissionApplication).where(AdmissionApplication.student_id == student.id)
    res_app = await db.execute(stmt_app)
    app = res_app.scalars().first()

    return {
        "student_id": student.id,
        "full_name": student.full_name,
        "allotted_branch": student.allotted_branch,
        "relationship": link.relationship,
        "application_status": app.status if app else "UNKNOWN",
        "academic_year": "2026-27",
    }


@router.get("/onboarding", response_model=OnboardingProfileResponse)
async def get_linked_student_onboarding(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Anti-IDOR Protected: Retrieve linked student's onboarding progress and checklist."""
    stmt_g = select(ParentGuardian).where(ParentGuardian.user_id == current_user.id)
    res_g = await db.execute(stmt_g)
    guardian = res_g.scalars().first()
    if not guardian:
        raise HTTPException(status_code=403, detail="No active parent profile found.")

    stmt_l = select(StudentGuardianLink).where(
        and_(
            StudentGuardianLink.guardian_id == guardian.id,
            StudentGuardianLink.status == ParentLinkStatus.ACTIVE,
        )
    )
    res_l = await db.execute(stmt_l)
    link = res_l.scalars().first()
    if not link:
        raise HTTPException(status_code=403, detail="No active student link found.")

    profile = await OnboardingService.get_or_create_profile(db, link.student_id)
    items = await OnboardingService.sync_checklist_items(db, profile)
    return build_profile_response(profile, items)


@router.get("/guidance", response_model=List[GuidanceCardResponse])
async def get_parent_guidance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve parent guidance cards and official communication channel information."""
    stmt_g = select(ParentGuardian).where(ParentGuardian.user_id == current_user.id)
    res_g = await db.execute(stmt_g)
    guardian = res_g.scalars().first()

    student_type = None
    if guardian:
        stmt_l = select(StudentGuardianLink).where(
            and_(
                StudentGuardianLink.guardian_id == guardian.id,
                StudentGuardianLink.status == ParentLinkStatus.ACTIVE,
            )
        )
        res_l = await db.execute(stmt_l)
        link = res_l.scalars().first()
        if link:
            stmt_p = select(OnboardingProfile).where(OnboardingProfile.student_id == link.student_id)
            res_p = await db.execute(stmt_p)
            prof = res_p.scalars().first()
            if prof:
                student_type = prof.student_type

    cards = OnboardingService.get_guidance_cards(student_type or "UNSPECIFIED")
    return cards

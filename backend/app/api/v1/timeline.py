from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.analytics import StudentJourneyTimelineResponse
from app.services.unified_timeline_service import UnifiedTimelineService

router = APIRouter(prefix="/timeline", tags=["Phase 8 - Unified Operational Timeline"])


@router.get("/me", response_model=StudentJourneyTimelineResponse)
async def get_my_journey_timeline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the unified 8-stage operational journey for the authenticated student.
    """
    return await UnifiedTimelineService.get_student_journey_timeline(db, current_user)


@router.get("/admin/{application_id}", response_model=StudentJourneyTimelineResponse)
async def get_admin_application_timeline(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN_VERIFIER", "FINANCE_OFFICER", "ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """
    Returns the chronological operational timeline for an application across all domains.
    """
    return await UnifiedTimelineService.get_application_timeline(db, application_id)

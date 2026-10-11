from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.analytics import AnalyticsOverviewResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/admin/analytics", tags=["Phase 8 - Operational Analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    date_filter: str = Query("all_time", pattern="^(today|last_7_days|last_30_days|all_time|custom)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN", "FINANCE_OFFICER", "ADMIN_VERIFIER"])),
):
    """
    Returns operational descriptive metrics and conversion bottlenecks from actual database records.
    Strictly READ-ONLY.
    """
    return await AnalyticsService.get_overview_metrics(
        db=db,
        date_filter=date_filter,
        start_date_str=start_date,
        end_date_str=end_date,
    )

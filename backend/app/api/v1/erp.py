from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.erp import (
    ERPReadinessValidationResponse,
    ERPAdmissionRecordResponse,
    ERPSyncRequest,
    ERPIntegrationEventResponse,
)
from app.services.erp_service import ERPService

router = APIRouter(prefix="/admin/erp", tags=["Phase 7 - ERP Staging & Integration"])


@router.get("/records", response_model=List[ERPAdmissionRecordResponse])
async def list_erp_records(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN", "ADMIN_VERIFIER"])),
):
    """
    Lists ERP staged records with status and search filters.
    """
    return await ERPService.list_erp_records(db, status_filter=status, search=search)


@router.get("/records/{record_id}", response_model=ERPAdmissionRecordResponse)
async def get_erp_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN", "ADMIN_VERIFIER"])),
):
    """
    Retrieves ERP staged record with sanitized JSON payload preview.
    """
    return await ERPService.get_erp_record_by_id(db, record_id)


@router.post("/validate/{application_id}", response_model=ERPReadinessValidationResponse)
async def validate_erp_readiness(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN", "ADMIN_VERIFIER"])),
):
    """
    Validates institutional ERP readiness policy for an application.
    """
    return await ERPService.validate_erp_readiness(db, application_id)


@router.post("/stage/{application_id}", response_model=ERPAdmissionRecordResponse)
async def stage_admission_record(
    application_id: str,
    force_stage: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """
    Assembles normalized payload and stages record for ERP synchronization.
    """
    return await ERPService.stage_admission_record(db, application_id, force_stage=force_stage)


@router.post("/records/{record_id}/sync", response_model=ERPAdmissionRecordResponse)
async def sync_erp_record(
    record_id: str,
    payload: ERPSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """
    Dispatches staged admission record to MockERPAdapter.
    """
    return await ERPService.sync_record(
        db,
        record_id=record_id,
        simulate_failure=payload.simulate_failure,
        failure_reason=payload.failure_reason,
    )


@router.post("/records/{record_id}/retry", response_model=ERPAdmissionRecordResponse)
async def retry_erp_sync(
    record_id: str,
    payload: ERPSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN"])),
):
    """
    Safely retries failed ERP synchronization on the same record.
    """
    return await ERPService.retry_sync(
        db,
        record_id=record_id,
        simulate_failure=payload.simulate_failure,
        failure_reason=payload.failure_reason,
    )


@router.get("/records/{record_id}/events", response_model=List[ERPIntegrationEventResponse])
async def get_erp_integration_events(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMISSION_HEAD", "SUPER_ADMIN", "ADMIN_VERIFIER"])),
):
    """
    Returns integration event history for an ERP record.
    """
    return await ERPService.get_record_events(db, record_id)

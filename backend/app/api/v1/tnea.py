from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.tnea import (
    TNEAImportRequest,
    TNEAImportResponse,
    TNEAImportBatchListItem,
    TNEAAllotmentResponse,
)
from app.models.user import User
from app.api.deps import require_roles
from app.services.tnea_service import (
    process_tnea_import,
    list_tnea_import_batches,
    get_tnea_import_batch_by_id,
    list_tnea_allotments,
    get_tnea_allotment_by_id,
)

router = APIRouter(tags=["TNEA Allotments & Ingestion"])

admin_role_check = require_roles([
    "ADMIN_VERIFIER",
    "ADMISSION_HEAD",
    "FINANCE_OFFICER",
    "SUPER_ADMIN"
])


@router.post("/admin/tnea/import", response_model=TNEAImportResponse)
async def import_tnea_allotments(
    payload: TNEAImportRequest,
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only endpoint to import synthetic TNEA allotment records.
    Deterministically validates allotments, creates student & application records in ACTIVATION_PENDING,
    generates secure activation tokens, and logs audit events.
    """
    if not payload.records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No allotment records provided in import payload."
        )

    response = await process_tnea_import(
        db=db,
        records=payload.records,
        source=payload.source,
        filename_or_reference=payload.filename_or_reference,
        imported_by=current_user.email,
    )
    return response


@router.get("/admin/tnea/imports", response_model=List[TNEAImportBatchListItem])
async def get_tnea_import_batches(
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns audit history of all TNEA allotment import batches.
    """
    batches = await list_tnea_import_batches(db)
    return batches


@router.get("/admin/tnea/imports/{batch_id}", response_model=TNEAImportBatchListItem)
async def get_tnea_import_batch_detail(
    batch_id: str,
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves details and audit summary for a specific import batch.
    """
    batch = await get_tnea_import_batch_by_id(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TNEA import batch '{batch_id}' not found."
        )
    return batch


@router.get("/admin/allotments", response_model=List[TNEAAllotmentResponse])
async def get_allotments_registry(
    branch: Optional[str] = Query(None, description="Filter by allotted branch"),
    status: Optional[str] = Query(None, description="Filter by admission lifecycle status"),
    search: Optional[str] = Query(None, description="Search by student name, TNEA app no, allotment no"),
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns all imported synthetic allotments with filtering and search capabilities.
    """
    allotments = await list_tnea_allotments(
        db=db,
        branch_filter=branch,
        status_filter=status,
        search=search
    )
    return allotments


@router.get("/admin/allotments/{allotment_id}", response_model=TNEAAllotmentResponse)
async def get_allotment_detail(
    allotment_id: str,
    current_user: User = Depends(admin_role_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves details for a single TNEA allotment.
    """
    allotment = await get_tnea_allotment_by_id(db, allotment_id)
    if not allotment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Allotment with ID '{allotment_id}' not found."
        )
    return allotment

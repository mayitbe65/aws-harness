"""Export API endpoints for PDF/HTML generation from snapshots.

Rule R1: All queries filter by user_id for user isolation
Rule R5: Snapshot creation uses transactions for consistency
Rule R9: Export uses frozen snapshot data to prevent mid-export modifications
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timezone
from uuid import UUID

from src.database.db import get_db
from src.routers.auth import get_current_user_from_token
from src.services.export_service import ExportService
from src.schemas.export import (
    ExportRequest,
    ExportResponse,
    SnapshotStatusResponse,
    ExportHistoryResponse,
)
from src.models.snapshot import Snapshot
from src.models.question import Question

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/pdf", response_model=ExportResponse, status_code=202)
async def request_pdf_export(
    request: ExportRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """Request PDF/HTML export of questions (Rule R5: transaction, Rule R9: snapshot).

    Creates a snapshot at export time to freeze question data, preventing
    modifications that occur after snapshot creation from affecting the export.

    Args:
        request: Export request with question IDs and options
        current_user: Current authenticated user
        db: Database session

    Returns:
        ExportResponse with snapshot_id and pending status

    Raises:
        HTTPException: 400 if no valid questions provided, 401 if unauthorized,
                      500 if export creation fails
    """
    user_id = current_user["user_id"]

    try:
        # Validate question IDs format
        # Keep as strings for SQLAlchemy GUID type compatibility
        validated_ids = []
        for q_id in request.question_ids:
            try:
                # Validate it's a valid UUID format
                UUID(q_id)
                validated_ids.append(q_id)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid question ID format. Must be valid UUIDs.",
                )

        # Create snapshot (Rule R5 - transaction, Rule R9 - data frozen)
        # The service handles question validation and existence check
        snapshot = await ExportService.create_snapshot(
            db,
            user_id,
            request.question_ids,
            format=request.format,
            group_by=request.group_by,
            include_answers=request.include_answers,
        )

        logger.info(
            f"Created export request {snapshot.snapshot_id} for user {user_id} "
            f"with {len(request.question_ids)} questions"
        )

        # In production: dispatch to Celery task for async PDF generation
        # For now: status is pending, can be polled for completion

        return ExportResponse(
            snapshot_id=str(snapshot.snapshot_id),
            status="pending",
            message="Export queued successfully. Check status using the snapshot_id.",
            estimated_time=5,  # seconds
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error requesting export: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error requesting export: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create export request. Please try again.",
        )


@router.get("/{snapshot_id}", response_model=SnapshotStatusResponse, status_code=200)
async def get_export_status(
    snapshot_id: str,
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> SnapshotStatusResponse:
    """Get export status (Rule R1: user isolation).

    Retrieves the current status of an export snapshot. Only the user who
    created the export can view its status.

    Args:
        snapshot_id: Snapshot ID to check
        current_user: Current authenticated user
        db: Database session

    Returns:
        SnapshotStatusResponse with current status and details

    Raises:
        HTTPException: 401 if unauthorized, 404 if snapshot not found,
                      500 if database error
    """
    user_id = current_user["user_id"]

    try:
        # Get snapshot (Rule R1: filter by user_id for isolation)
        snapshot = await ExportService.get_snapshot_status(db, snapshot_id, user_id)

        if not snapshot:
            logger.warning(
                f"User {user_id} attempted to access snapshot {snapshot_id} "
                "that does not exist or belongs to another user"
            )
            raise HTTPException(
                status_code=404,
                detail="Snapshot not found. It may have been deleted or belong to another user.",
            )

        return SnapshotStatusResponse(
            snapshot_id=str(snapshot.snapshot_id),
            status=snapshot.status,
            created_at=snapshot.created_at,
            completed_at=snapshot.completed_at,
            file_url=snapshot.file_url,
            error_message=snapshot.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting snapshot status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve export status.",
        )


@router.get("/{snapshot_id}/download", status_code=200)
async def download_export(
    snapshot_id: str,
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Download export file (Rule R1: user isolation, Rule R9: use frozen data).

    Generates and downloads the PDF/HTML file from frozen snapshot data.
    The file is generated on-demand from the frozen data to ensure it
    contains the exact questions at export time.

    Args:
        snapshot_id: Snapshot ID to download
        current_user: Current authenticated user
        db: Database session

    Returns:
        StreamingResponse with PDF/HTML file

    Raises:
        HTTPException: 400 if export not completed, 401 if unauthorized,
                      404 if snapshot not found, 500 if generation fails
    """
    user_id = current_user["user_id"]

    try:
        # Get snapshot (Rule R1: filter by user_id for isolation)
        snapshot = await ExportService.get_snapshot_status(db, snapshot_id, user_id)

        if not snapshot:
            logger.warning(
                f"User {user_id} attempted to download snapshot {snapshot_id} "
                "that does not exist or belongs to another user"
            )
            raise HTTPException(
                status_code=404,
                detail="Snapshot not found.",
            )

        if snapshot.status != "completed":
            logger.info(
                f"User {user_id} attempted to download snapshot {snapshot_id} "
                f"with status {snapshot.status}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Export is {snapshot.status}. Please wait for it to complete.",
            )

        # Generate from frozen snapshot (Rule R9: use frozen data)
        pdf_content = await ExportService.generate_pdf_content(snapshot)

        # Determine media type and filename
        if snapshot.format == "pdf":
            media_type = "application/pdf"
            filename = f"export_{snapshot_id}.pdf"
        else:  # html
            media_type = "text/html"
            filename = f"export_{snapshot_id}.html"

        logger.info(
            f"User {user_id} downloading export {snapshot_id} as {snapshot.format}"
        )

        # Return as downloadable file
        return StreamingResponse(
            iter([pdf_content.encode("utf-8")]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading export: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate or download export.",
        )


@router.get("", response_model=ExportHistoryResponse, status_code=200)
async def get_export_history(
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        10, ge=1, le=50, description="Items per page (1-50)"
    ),
) -> ExportHistoryResponse:
    """Get export history (Rule R1: user isolation).

    Lists all past exports for the current user with pagination.
    Sorted by creation time (newest first).

    Args:
        current_user: Current authenticated user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        ExportHistoryResponse with list of snapshots and total count

    Raises:
        HTTPException: 401 if unauthorized, 500 if database error
    """
    user_id = current_user["user_id"]

    try:
        # Get total count
        count_stmt = select(func.count()).select_from(Snapshot).where(
            Snapshot.user_id == user_id  # Rule R1: user isolation
        )
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get paginated list
        snapshots, _ = await ExportService.list_snapshots(
            db,
            user_id,
            page=page,
            page_size=page_size,
        )

        logger.info(
            f"User {user_id} retrieved export history page {page} "
            f"(size {page_size}, total {total})"
        )

        return ExportHistoryResponse(
            snapshots=[
                SnapshotStatusResponse(
                    snapshot_id=str(s.snapshot_id),
                    status=s.status,
                    created_at=s.created_at,
                    completed_at=s.completed_at,
                    file_url=s.file_url,
                    error_message=s.error_message,
                )
                for s in snapshots
            ],
            total=total,
        )

    except Exception as e:
        logger.error(f"Error getting export history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve export history.",
        )


@router.post("/cleanup", status_code=200)
async def cleanup_exports(
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Cleanup expired snapshots (internal/admin use only).

    Removes snapshots that have expired (default: 30 days after creation).
    This endpoint is typically called by a background job, not by regular users.

    Args:
        current_user: Current authenticated user (should be admin in production)
        db: Database session

    Returns:
        Dictionary with cleanup status and count

    Raises:
        HTTPException: 401 if unauthorized, 500 if cleanup fails
    """
    # In production: verify user is admin
    # For now: just run cleanup
    user_id = current_user["user_id"]

    try:
        logger.info(f"Cleanup requested by user {user_id}")

        cleaned = await ExportService.cleanup_expired_snapshots(db)

        logger.info(f"Successfully cleaned up {cleaned} expired snapshots")

        return {
            "status": "success",
            "cleaned_count": cleaned,
            "message": f"Cleaned up {cleaned} expired snapshots.",
        }

    except Exception as e:
        logger.error(f"Error during export cleanup: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to cleanup expired snapshots.",
        )

"""Photo recognition router with Vision API integration."""
import logging
import tempfile
import shutil
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.db import get_db
from src.routers.auth import get_current_user_from_token
from src.services.recognition_service import RecognitionService
from src.schemas.recognition import RecognitionResponse, RecognitionQuality

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/recognition", tags=["recognition"])


def _upload_to_s3(file_bytes: bytes, user_id: str, content_type: str) -> str:
    """Upload photo to S3 and return the public URL."""
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(content_type, "jpg")
    key = f"{settings.S3_PHOTO_PREFIX}/{user_id}/{uuid.uuid4()}.{ext}"
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    s3.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


@router.post("/upload", response_model=RecognitionResponse, status_code=200)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> RecognitionResponse:
    """
    Upload photo and recognize text using Vision API (Rule R4: quality check, Rule R8: retry).

    Quality levels:
    - HIGH (confidence >= 0.7): Auto-save ready
    - MEDIUM (0.5 <= confidence < 0.7): Mark needs_review=true, prompt user
    - LOW (confidence < 0.5): Recognition failed, suggest retry

    Args:
        file: Photo file (JPEG, PNG, WebP)
        current_user: Current user from JWT token
        db: Database session

    Returns:
        RecognitionResponse with status, quality, result, message

    Raises:
        HTTPException: 400 (bad file type/size), 401 (auth), 500 (server error)
    """
    user_id = current_user["user_id"]

    try:
        # Validate file type
        if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Accepted: JPEG, PNG, WebP",
            )

        # Validate file size (< 10MB)
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large (max 10MB)",
            )

        # Upload to S3 first (regardless of recognition result)
        try:
            photo_url = _upload_to_s3(contents, user_id, file.content_type)
            print(f"[S3] Uploaded photo: {photo_url}", flush=True)
        except Exception as e:
            logger.error(f"S3 upload failed for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="图片上传失败")

        # Save file temporarily for recognition
        temp_dir = tempfile.mkdtemp()
        file_path = Path(temp_dir) / (file.filename or "temp_photo")

        try:
            with open(file_path, "wb") as f:
                f.write(contents)

            # Call Vision API with retry logic (Rule R8: 3 retries)
            logger.info(
                f"Calling Vision API for user {user_id} with file {file.filename}"
            )
            result = await RecognitionService.call_vision_api(
                str(file_path), max_retries=3
            )

            if result is None:
                logger.warning(
                    f"Vision API failed for user {user_id} after all retries"
                )
                return RecognitionResponse(
                    status="failed",
                    quality=RecognitionQuality.LOW,
                    result=None,
                    message="Recognition failed after 3 retries. Please try again or upload a clearer photo.",
                    needs_manual_review=True,
                    photo_url=photo_url,
                )

            # Validate quality (Rule R4: three-level check)
            quality_check = RecognitionService.validate_recognition_result(result)

            logger.info(
                f"Quality check result for user {user_id}: quality={quality_check.quality}, "
                f"is_valid={quality_check.is_valid}, reason={quality_check.reason}"
            )

            # Determine response based on quality level
            if quality_check.quality == RecognitionQuality.HIGH:
                return RecognitionResponse(
                    status="success",
                    quality=RecognitionQuality.HIGH,
                    result=result,
                    message="Recognition successful! Question is ready to save.",
                    needs_manual_review=False,
                    photo_url=photo_url,
                )
            elif quality_check.quality == RecognitionQuality.MEDIUM:
                return RecognitionResponse(
                    status="success",
                    quality=RecognitionQuality.MEDIUM,
                    result=result,
                    message="Recognition result has medium confidence. Please review and correct before saving.",
                    needs_manual_review=True,
                    photo_url=photo_url,
                )
            else:  # LOW
                return RecognitionResponse(
                    status="failed",
                    quality=RecognitionQuality.LOW,
                    result=None,
                    message=f"Recognition failed: {quality_check.reason}. Please retry with a clearer photo.",
                    needs_manual_review=True,
                    photo_url=photo_url,
                )

        finally:
            # Clean up temporary files
            shutil.rmtree(temp_dir, ignore_errors=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_photo for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recognition service error",
        )

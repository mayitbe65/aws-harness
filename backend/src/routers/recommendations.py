"""Recommendation endpoints for spaced repetition review."""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.models.question import Question
from src.models.review_plan import ReviewPlan
from src.routers.auth import get_current_user_from_token
from src.schemas.recommendation import (
    MarkReviewedRequest,
    MarkReviewedResponse,
    RecommendationListResponse,
    ReviewItemResponse,
)
from src.services.recommend_service import RecommendationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

# Redis client helper
def get_redis_client():
    """Get Redis client for caching.

    Returns:
        Redis client or None if Redis is unavailable
    """
    try:
        import redis
        from src.config import settings
        redis_url = settings.REDIS_URL
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis client initialization failed: {e}")
        return None


def get_cache_key(user_id: str, resource: str = "plan") -> str:
    """Generate cache key with user isolation (Rule R6).

    Args:
        user_id: User ID
        resource: Resource type (e.g., "plan", "stats")

    Returns:
        Cache key in format: recommend:{user_id}:{resource}
    """
    return f"recommend:{user_id}:{resource}"


@router.get("/plan", response_model=RecommendationListResponse, status_code=200)
async def get_recommendations(
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
    use_cache: bool = Query(True),
):
    """Get recommendation plan with spaced repetition priority (Rule R6: Redis cache).

    Returns a list of recommended questions sorted by priority score.
    Results are cached per user for 1 hour.

    Args:
        current_user: Current authenticated user (from JWT token)
        db: Database session
        limit: Maximum number of recommendations (1-50, default 10)
        use_cache: Whether to use Redis cache (default True)

    Returns:
        RecommendationListResponse with items, stats, and cache metadata

    Raises:
        HTTPException: 401 if unauthorized, 500 on server error
    """
    user_id = current_user["user_id"]
    cache_key = get_cache_key(user_id, "plan")

    try:
        # Try cache first (Rule R6: Redis cache with user isolation)
        if use_cache:
            try:
                import json
                redis_client = get_redis_client()
                if redis_client:
                    cached = redis_client.get(cache_key)
                    if cached:
                        logger.info(f"Cache hit for {cache_key}")
                        data = json.loads(cached)
                        return RecommendationListResponse(**data)
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")
                # Fall through to DB if cache fails

        # Get recommendations from service
        now = datetime.now(timezone.utc)
        recommendations = await RecommendationService.get_recommendations(
            db, user_id, limit=limit, current_time=now
        )

        # Get statistics
        async with db.begin():
            # Count mastered questions
            mastered_stmt = select(func.count(ReviewPlan.plan_id)).where(
                and_(
                    ReviewPlan.user_id == user_id,
                    ReviewPlan.is_mastered == True,
                )
            )
            mastered_result = await db.execute(mastered_stmt)
            mastered_count = mastered_result.scalar() or 0

            # Count by subject
            subject_stmt = select(
                Question.subject,
                func.count(Question.question_id).label("count")
            ).where(
                Question.user_id == user_id
            ).group_by(Question.subject)

            subject_result = await db.execute(subject_stmt)
            total_by_subject = {
                row[0]: row[1] for row in subject_result.all()
            }

        # Helper to ensure timezone-aware datetime
        def ensure_aware_datetime(dt: Optional[datetime]) -> datetime:
            if dt is None:
                return now
            if dt.tzinfo is None:
                # Make naive datetime timezone-aware (assume UTC)
                return dt.replace(tzinfo=timezone.utc)
            return dt

        # Build response
        response = RecommendationListResponse(
            items=[
                ReviewItemResponse(
                    question_id=str(rec["question"].question_id),
                    photo_url=rec["question"].photo_url,
                    recognized_text=rec["question"].recognized_text,
                    subject=rec["question"].subject,
                    difficulty=rec["question"].difficulty,
                    error_count=rec["plan"].error_count or 0,
                    reviewed_count=rec["plan"].reviewed_count or 0,
                    last_error_time=ensure_aware_datetime(rec["plan"].last_error_time),
                    last_reviewed_time=ensure_aware_datetime(rec["plan"].last_reviewed_time) if rec["plan"].last_reviewed_time else None,
                    next_review_time=ensure_aware_datetime(rec["plan"].next_review_time),
                    priority=rec["priority"],
                )
                for rec in recommendations
            ],
            total_questions=len(recommendations),
            mastered_count=mastered_count,
            total_by_subject=total_by_subject,
            generated_at=now,
            cache_ttl_seconds=3600,
        )

        # Store in cache (Rule R6: key includes user_id for isolation)
        try:
            import json
            redis_client = get_redis_client()
            if redis_client:
                redis_client.setex(
                    cache_key,
                    3600,  # 1 hour TTL
                    response.model_dump_json(),
                )
                logger.info(f"Cached recommendations for {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache: {e}")

        return response

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommendations"
        )


@router.post("/mark-reviewed/{plan_id}", response_model=MarkReviewedResponse, status_code=200)
async def mark_reviewed(
    plan_id: str,
    request: MarkReviewedRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Mark a question as reviewed (Rule R5: transaction protection).

    Updates ReviewPlan with new review count or error count based on correctness.
    Clears user's recommendation cache after update.

    Args:
        plan_id: ID of ReviewPlan to mark (UUID format with or without hyphens)
        request: MarkReviewedRequest with reviewed boolean
        current_user: Current authenticated user
        db: Database session

    Returns:
        MarkReviewedResponse with updated plan info and next review time

    Raises:
        HTTPException: 401 if unauthorized, 404 if plan not found, 500 on error
    """
    from uuid import UUID as PyUUID

    user_id = current_user["user_id"]

    try:
        # Convert plan_id to UUID hex format (GUID storage format)
        try:
            # Parse UUID from string (handles both with/without hyphens)
            parsed_uuid = PyUUID(plan_id)
            plan_id_hex = parsed_uuid.hex
        except ValueError:
            # If not valid UUID, try treating as hex already
            plan_id_hex = plan_id.replace("-", "")

        # Call service (includes transaction protection - Rule R5)
        updated_plan = await RecommendationService.mark_reviewed(
            db,
            user_id,
            plan_id_hex,
            was_correct=request.reviewed,
        )

        # Clear user's recommendation cache (Rule R6)
        try:
            cache_key = get_cache_key(user_id, "plan")
            redis_client = get_redis_client()
            if redis_client:
                redis_client.delete(cache_key)
                logger.info(f"Cleared cache for {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")

        # Determine message
        if request.reviewed:
            days_until = (updated_plan.next_review_time - datetime.now(timezone.utc)).days
            message = f"Great! Next review in {days_until} days"
        else:
            message = "Keep practicing! Next review in 1 day"

        return MarkReviewedResponse(
            plan_id=str(updated_plan.plan_id),
            next_review_time=updated_plan.next_review_time,
            reviewed_count=updated_plan.reviewed_count or 0,
            is_mastered=updated_plan.is_mastered,
            message=message,
        )

    except ValueError as e:
        logger.error(f"Invalid plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error marking reviewed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark review"
        )


@router.get("/stats", status_code=200)
async def get_study_stats(
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Get learning statistics for the user.

    Returns overview of total questions, mastery rate, today's reviews, and errors.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with learning statistics

    Raises:
        HTTPException: 401 if unauthorized, 500 on error
    """
    user_id = current_user["user_id"]

    try:
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        async with db.begin():
            # Total questions
            total_stmt = select(func.count(Question.question_id)).where(
                Question.user_id == user_id
            )
            total_result = await db.execute(total_stmt)
            total_questions = total_result.scalar() or 0

            # Mastered
            mastered_stmt = select(func.count(ReviewPlan.plan_id)).where(
                and_(
                    ReviewPlan.user_id == user_id,
                    ReviewPlan.is_mastered == True,
                )
            )
            mastered_result = await db.execute(mastered_stmt)
            mastered_count = mastered_result.scalar() or 0

            # Reviewed today
            today_reviewed_stmt = select(func.count(ReviewPlan.plan_id)).where(
                and_(
                    ReviewPlan.user_id == user_id,
                    ReviewPlan.last_reviewed_time >= today,
                )
            )
            today_reviewed_result = await db.execute(today_reviewed_stmt)
            today_reviewed_count = today_reviewed_result.scalar() or 0

            # Average errors
            avg_errors_stmt = select(func.avg(ReviewPlan.error_count)).where(
                ReviewPlan.user_id == user_id
            )
            avg_errors_result = await db.execute(avg_errors_stmt)
            avg_errors = avg_errors_result.scalar() or 0.0

        mastery_rate = ((mastered_count / max(total_questions, 1)) * 100) if total_questions > 0 else 0.0

        return {
            "total_questions": total_questions,
            "mastered_count": mastered_count,
            "mastery_rate": mastery_rate,
            "reviewed_today": today_reviewed_count,
            "average_errors_per_question": float(avg_errors),
            "stats_generated_at": now.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )

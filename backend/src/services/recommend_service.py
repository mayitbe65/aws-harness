"""Spaced repetition algorithm based on Ebbinghaus forgetting curve."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from src.models.question import Question
from src.models.review_plan import ReviewPlan
import logging

logger = logging.getLogger(__name__)


class RecommendationService:
    """Spaced repetition algorithm based on Ebbinghaus forgetting curve.

    实现规则 R5（事务保护）：所有计算在数据库事务中进行
    实现规则 R7（单元测试）：目标覆盖率 > 80%，优先达到 100%
    """

    # Review schedule (days between reviews)
    REVIEW_SCHEDULE = {
        0: 1,      # First review: 1 day after error
        1: 3,      # Second: 3 days
        2: 7,      # Third: 7 days
        3: 15,     # Fourth: 15 days
        4: 30,     # Fifth: 30 days
    }

    # Algorithm weights
    WEIGHT_ERROR_FREQUENCY = 0.4
    WEIGHT_FORGETTING = 0.4
    WEIGHT_DIFFICULTY = 0.2

    # Difficulty scale
    MAX_DIFFICULTY = 5

    @staticmethod
    def get_next_review_days(reviewed_count: int) -> int:
        """Get review interval for next review based on review count.

        Args:
            reviewed_count: Number of times question has been successfully reviewed

        Returns:
            Number of days until next review
        """
        return RecommendationService.REVIEW_SCHEDULE.get(reviewed_count, 30)

    @staticmethod
    def calculate_error_frequency_score(error_count: int) -> float:
        """Calculate error frequency score [0, 1].

        Higher error count = higher score.
        Uses sigmoid-like curve: 1 error = 0.5, 2 = 0.67, 5 = 0.83, 10 = 0.91

        Args:
            error_count: Total number of errors for the question

        Returns:
            Score [0, 1] representing error frequency
        """
        if error_count <= 0:
            return 0.0

        # Sigmoid-like curve
        return min(1.0, error_count / (error_count + 1.0))

    @staticmethod
    def calculate_forgetting_score(
        last_reviewed_time: Optional[datetime],
        reviewed_count: int,
        current_time: Optional[datetime] = None,
    ) -> float:
        """Calculate forgetting score based on Ebbinghaus curve [0, 1].

        If never reviewed, return 0.0 (no forgetting curve yet).
        If reviewed, use distance from last_reviewed_time vs expected review cycle.

        Args:
            last_reviewed_time: Timestamp of last review (or None)
            reviewed_count: Number of successful reviews so far
            current_time: Reference time (defaults to now)

        Returns:
            Score [0, 1] representing forgetting factor
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        if last_reviewed_time is None:
            # Question just added, not reviewed yet
            return 0.0

        # Days since last review
        days_since_review = (current_time - last_reviewed_time).days

        # Expected review cycle for this question
        review_cycle = RecommendationService.REVIEW_SCHEDULE.get(reviewed_count, 30)

        # Forgetting factor: 0 at start of cycle, 1.0 after cycle ends
        forgetting_factor = min(1.0, max(0.0, days_since_review / review_cycle))

        # Damping factor: older questions (many reviews) are less urgent
        # After 5+ reviews, reduce priority to prevent reviewing already-mastered items
        repetition_damping = max(0.1, 1.0 - (reviewed_count * 0.15))

        return forgetting_factor * repetition_damping

    @staticmethod
    def calculate_difficulty_score(difficulty: int) -> float:
        """Calculate difficulty score [0, 1].

        Harder questions get higher priority. Difficulty scale: 1-5 → normalized to 0-1

        Args:
            difficulty: Difficulty level 1-5

        Returns:
            Score [0, 1] representing difficulty
        """
        return min(1.0, max(0.0, difficulty / RecommendationService.MAX_DIFFICULTY))

    @staticmethod
    def calculate_priority(
        error_count: int,
        reviewed_count: int,
        last_error_time: datetime,
        last_reviewed_time: Optional[datetime],
        difficulty: int,
        is_mastered: bool,
        current_time: Optional[datetime] = None,
    ) -> float:
        """Calculate priority score [0, 1].

        Priority = 0.4 * error_frequency + 0.4 * forgetting + 0.2 * difficulty

        Args:
            error_count: Total errors
            reviewed_count: Successful reviews
            last_error_time: When last error occurred
            last_reviewed_time: When last reviewed
            difficulty: Difficulty 1-5
            is_mastered: Whether already mastered
            current_time: Reference time (defaults to now)

        Returns:
            Priority score [0, 1]
        """
        if is_mastered:
            return 0.0  # Already mastered, no priority

        error_score = RecommendationService.calculate_error_frequency_score(error_count)
        forgetting_score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time, reviewed_count, current_time
        )
        difficulty_score = RecommendationService.calculate_difficulty_score(difficulty)

        priority = (
            RecommendationService.WEIGHT_ERROR_FREQUENCY * error_score +
            RecommendationService.WEIGHT_FORGETTING * forgetting_score +
            RecommendationService.WEIGHT_DIFFICULTY * difficulty_score
        )

        return min(1.0, max(0.0, priority))

    @staticmethod
    async def get_recommendations(
        db: AsyncSession,
        user_id: str,
        limit: int = 10,
        current_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get recommended questions for user.

        Rule R5: Transaction protection - all operations in db.begin() block

        Args:
            db: AsyncSession database connection
            user_id: User ID
            limit: Maximum number of recommendations (default 10)
            current_time: Reference time (defaults to now)

        Returns:
            List of dicts with question, plan, and priority, sorted by priority DESC
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        try:
            # Rule R5: Transaction protection
            async with db.begin():
                # Join Question and ReviewPlan
                stmt = select(Question, ReviewPlan).join(
                    ReviewPlan,
                    Question.question_id == ReviewPlan.question_id,
                ).where(
                    and_(
                        ReviewPlan.user_id == user_id,
                        Question.user_id == user_id,
                        ReviewPlan.is_mastered == False,  # Only non-mastered questions
                        Question.needs_review == False,   # Only high-quality questions (Rule R4)
                    )
                )

                result = await db.execute(stmt)
                items = result.all()

            # Calculate priority for each item
            recommendations = []
            for question, plan in items:
                # Ensure datetimes are timezone-aware
                last_error_time = plan.last_error_time or current_time
                if last_error_time.tzinfo is None:
                    last_error_time = last_error_time.replace(tzinfo=timezone.utc)

                last_reviewed_time = plan.last_reviewed_time
                if last_reviewed_time and last_reviewed_time.tzinfo is None:
                    last_reviewed_time = last_reviewed_time.replace(tzinfo=timezone.utc)

                priority = RecommendationService.calculate_priority(
                    error_count=plan.error_count or 0,
                    reviewed_count=plan.reviewed_count or 0,
                    last_error_time=last_error_time,
                    last_reviewed_time=last_reviewed_time,
                    difficulty=question.difficulty or 3,
                    is_mastered=plan.is_mastered,
                    current_time=current_time,
                )

                recommendations.append({
                    "question": question,
                    "plan": plan,
                    "priority": priority,
                })

            # Sort by priority descending
            recommendations.sort(key=lambda x: x["priority"], reverse=True)

            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            raise

    @staticmethod
    async def get_recommendation_stats(
        db: AsyncSession,
        user_id: str,
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get recommendation statistics for user.

        Args:
            db: AsyncSession database connection
            user_id: User ID
            current_time: Reference time (defaults to now)

        Returns:
            Dict with counts by subject, mastered count, etc.
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        try:
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

                # Count total questions
                total_stmt = select(func.count(Question.question_id)).where(
                    Question.user_id == user_id
                )
                total_result = await db.execute(total_stmt)
                total_count = total_result.scalar() or 0

                # Count by subject
                subject_stmt = select(
                    Question.subject,
                    func.count(Question.question_id)
                ).where(
                    Question.user_id == user_id
                ).group_by(Question.subject)

                subject_result = await db.execute(subject_stmt)
                total_by_subject = {subject: count for subject, count in subject_result.all()}

            return {
                "total_questions": total_count,
                "mastered_count": mastered_count,
                "total_by_subject": total_by_subject,
            }

        except Exception as e:
            logger.error(f"Error fetching recommendation stats: {e}")
            raise

    @staticmethod
    async def mark_reviewed(
        db: AsyncSession,
        user_id: str,
        plan_id: str,
        was_correct: bool,
        current_time: Optional[datetime] = None,
    ) -> ReviewPlan:
        """Mark question as reviewed and update next review time.

        If correct: advance to next cycle (reviewed_count += 1, check if mastered)
        If wrong: reset cycle but increment error count

        Rule R5: Transaction protection for update

        Args:
            db: AsyncSession database connection
            user_id: User ID
            plan_id: ReviewPlan ID
            was_correct: Whether the question was answered correctly
            current_time: Reference time (defaults to now)

        Returns:
            Updated ReviewPlan

        Raises:
            ValueError: If plan not found
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        try:
            async with db.begin():
                # Fetch plan
                stmt = select(ReviewPlan).where(
                    and_(
                        ReviewPlan.plan_id == plan_id,
                        ReviewPlan.user_id == user_id,
                    )
                )

                result = await db.execute(stmt)
                plan = result.scalars().first()

                if not plan:
                    raise ValueError(f"ReviewPlan {plan_id} not found")

                if was_correct:
                    # Correct: advance to next review cycle
                    plan.reviewed_count = (plan.reviewed_count or 0) + 1
                    next_days = RecommendationService.get_next_review_days(plan.reviewed_count)

                    # Check if mastered (after 5+ reviews with no errors)
                    if plan.reviewed_count >= 5:
                        plan.is_mastered = True

                    logger.info(
                        f"Question {plan.question_id} reviewed correctly, "
                        f"next in {next_days} days, reviewed_count={plan.reviewed_count}"
                    )
                else:
                    # Wrong: reset review count, increment error count
                    plan.reviewed_count = 0
                    plan.error_count = (plan.error_count or 0) + 1
                    next_days = RecommendationService.get_next_review_days(0)  # Restart from 1 day

                    logger.info(
                        f"Question {plan.question_id} reviewed incorrectly, "
                        f"retry in {next_days} days, error_count={plan.error_count}"
                    )

                # Update timestamps
                plan.last_reviewed_time = current_time
                plan.next_review_time = current_time + timedelta(days=next_days)
                plan.updated_at = current_time

                await db.flush()

            return plan

        except Exception as e:
            logger.error(f"Error marking reviewed: {e}")
            raise

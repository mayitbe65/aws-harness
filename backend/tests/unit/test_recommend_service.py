"""Unit tests for spaced repetition recommendation service.

Rule R7: Target coverage > 80%, aim for 100%
Rule R5: Transaction protection in async context
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.recommend_service import RecommendationService
from src.models.question import Question
from src.models.review_plan import ReviewPlan


class TestErrorFrequencyScore:
    """Test error frequency score calculation."""

    def test_error_frequency_zero_errors(self):
        """0 errors → 0 score"""
        score = RecommendationService.calculate_error_frequency_score(0)
        assert score == 0.0

    def test_error_frequency_negative_errors(self):
        """Negative errors clamped to 0"""
        score = RecommendationService.calculate_error_frequency_score(-5)
        assert score == 0.0

    def test_error_frequency_one_error(self):
        """1 error → 0.5 score"""
        score = RecommendationService.calculate_error_frequency_score(1)
        assert score == 0.5

    def test_error_frequency_two_errors(self):
        """2 errors → 0.67 score"""
        score = RecommendationService.calculate_error_frequency_score(2)
        assert abs(score - 2/3) < 0.01

    def test_error_frequency_five_errors(self):
        """5 errors → 0.83 score"""
        score = RecommendationService.calculate_error_frequency_score(5)
        assert abs(score - 5/6) < 0.01

    def test_error_frequency_ten_errors(self):
        """10 errors → 0.91 score"""
        score = RecommendationService.calculate_error_frequency_score(10)
        assert abs(score - 10/11) < 0.01

    def test_error_frequency_many_errors_approaches_one(self):
        """Many errors approach 1.0"""
        score = RecommendationService.calculate_error_frequency_score(1000)
        assert 0.9 < score < 1.0

    def test_error_frequency_clamped_to_one(self):
        """Score never exceeds 1.0"""
        score = RecommendationService.calculate_error_frequency_score(10000)
        assert score <= 1.0


class TestForgettingScore:
    """Test forgetting curve score calculation."""

    def test_forgetting_never_reviewed(self):
        """Never reviewed → 0 score"""
        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=None,
            reviewed_count=0,
        )
        assert score == 0.0

    def test_forgetting_never_reviewed_with_count(self):
        """Never reviewed regardless of count → 0 score"""
        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=None,
            reviewed_count=5,
        )
        assert score == 0.0

    def test_forgetting_just_reviewed_zero_count(self):
        """Just reviewed (0 days ago), reviewed_count=0 → ~0 score"""
        now = datetime.now(timezone.utc)
        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=now,
            reviewed_count=0,
            current_time=now,
        )
        assert score == 0.0

    def test_forgetting_one_day_into_one_day_cycle(self):
        """1 day into 1-day cycle (reviewed_count=0) → ~1.0 * damping(0) = 1.0"""
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)

        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=one_day_ago,
            reviewed_count=0,
            current_time=now,
        )

        # Should be 1.0 * 1.0 damping = 1.0
        assert score >= 0.95

    def test_forgetting_half_cycle_elapsed(self):
        """Half of review cycle elapsed → 0 score (days_since_review uses .days which floors)"""
        now = datetime.now(timezone.utc)
        # timedelta().days is an integer, so 0.5 days becomes 0 days
        half_day = now - timedelta(hours=12)

        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=half_day,
            reviewed_count=0,
            current_time=now,
        )

        # Since .days floors, this is 0 days into a 1-day cycle = 0.0
        assert score == 0.0

    def test_forgetting_full_cycle_elapsed_first_review(self):
        """Full review cycle elapsed (reviewed_count=0, 1-day cycle)"""
        now = datetime.now(timezone.utc)
        full_cycle = now - timedelta(days=1)

        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=full_cycle,
            reviewed_count=0,
            current_time=now,
        )

        # Should be 1.0 * 1.0 = 1.0 (clamped)
        assert score >= 0.95

    def test_forgetting_beyond_cycle_clamped(self):
        """Days beyond cycle clamped to 1.0 * damping"""
        now = datetime.now(timezone.utc)
        far_past = now - timedelta(days=100)

        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=far_past,
            reviewed_count=0,
            current_time=now,
        )

        # Should be 1.0 * 1.0 (clamped) = 1.0
        assert score >= 0.95

    def test_forgetting_damping_after_one_review(self):
        """After 1 review, damping = 1.0 - 0.15 = 0.85"""
        now = datetime.now(timezone.utc)
        three_days_ago = now - timedelta(days=3)  # 3-day cycle for reviewed_count=1

        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=three_days_ago,
            reviewed_count=1,
            current_time=now,
        )

        # Should be 1.0 * 0.85 = 0.85 (at end of 3-day cycle)
        assert 0.8 < score < 0.9

    def test_forgetting_damping_after_four_reviews(self):
        """After 4 reviews, damping = 1.0 - 4*0.15 = 0.4"""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=thirty_days_ago,
            reviewed_count=4,
            current_time=now,
        )

        # Should be 1.0 * 0.4 = 0.4
        assert 0.35 < score < 0.45

    def test_forgetting_damping_floor_at_zero_one(self):
        """Damping never goes below 0.1"""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=thirty_days_ago,
            reviewed_count=10,  # Damping would be 1.0 - 10*0.15 = -0.5, floored to 0.1
            current_time=now,
        )

        # Should be 1.0 * 0.1 = 0.1
        assert score >= 0.08

    def test_forgetting_none_current_time(self):
        """None current_time defaults to now"""
        past = datetime.now(timezone.utc) - timedelta(days=1)

        # Should not raise
        score = RecommendationService.calculate_forgetting_score(
            last_reviewed_time=past,
            reviewed_count=0,
            current_time=None,
        )

        assert score >= 0.0


class TestDifficultyScore:
    """Test difficulty score calculation."""

    def test_difficulty_level_1(self):
        """Difficulty 1 → 0.2 score"""
        score = RecommendationService.calculate_difficulty_score(1)
        assert abs(score - 0.2) < 0.01

    def test_difficulty_level_2(self):
        """Difficulty 2 → 0.4 score"""
        score = RecommendationService.calculate_difficulty_score(2)
        assert abs(score - 0.4) < 0.01

    def test_difficulty_level_3(self):
        """Difficulty 3 → 0.6 score"""
        score = RecommendationService.calculate_difficulty_score(3)
        assert abs(score - 0.6) < 0.01

    def test_difficulty_level_4(self):
        """Difficulty 4 → 0.8 score"""
        score = RecommendationService.calculate_difficulty_score(4)
        assert abs(score - 0.8) < 0.01

    def test_difficulty_level_5(self):
        """Difficulty 5 → 1.0 score"""
        score = RecommendationService.calculate_difficulty_score(5)
        assert abs(score - 1.0) < 0.01

    def test_difficulty_zero(self):
        """Difficulty 0 → 0 score (clamped)"""
        score = RecommendationService.calculate_difficulty_score(0)
        assert score == 0.0

    def test_difficulty_negative_clamped(self):
        """Negative difficulty clamped to 0"""
        score = RecommendationService.calculate_difficulty_score(-5)
        assert score == 0.0

    def test_difficulty_above_max_clamped(self):
        """Difficulty > 5 clamped to 1.0"""
        score = RecommendationService.calculate_difficulty_score(10)
        assert score == 1.0


class TestPriorityCalculation:
    """Test overall priority calculation."""

    def test_priority_mastered_question_always_zero(self):
        """Mastered question always has priority 0"""
        now = datetime.now(timezone.utc)

        priority = RecommendationService.calculate_priority(
            error_count=10,
            reviewed_count=10,
            last_error_time=now,
            last_reviewed_time=now,
            difficulty=5,
            is_mastered=True,
            current_time=now,
        )

        assert priority == 0.0

    def test_priority_new_question_high_error_high_difficulty(self):
        """New question with error → moderate-high priority"""
        now = datetime.now(timezone.utc)

        priority = RecommendationService.calculate_priority(
            error_count=1,
            reviewed_count=0,
            last_error_time=now,
            last_reviewed_time=None,
            difficulty=5,
            is_mastered=False,
            current_time=now,
        )

        # 0.4 * 0.5 (1 error) + 0.4 * 0 (never reviewed) + 0.2 * 1.0 (high difficulty)
        # = 0.2 + 0 + 0.2 = 0.4
        assert 0.35 < priority < 0.45

    def test_priority_new_question_no_error_easy(self):
        """New question, no error, low difficulty → very low priority"""
        now = datetime.now(timezone.utc)

        priority = RecommendationService.calculate_priority(
            error_count=0,
            reviewed_count=0,
            last_error_time=now,
            last_reviewed_time=None,
            difficulty=1,
            is_mastered=False,
            current_time=now,
        )

        # 0.4 * 0 + 0.4 * 0 + 0.2 * 0.2 = 0.04
        assert priority < 0.05

    def test_priority_multiple_errors_high_difficulty(self):
        """Multiple errors, high difficulty → high priority"""
        now = datetime.now(timezone.utc)

        priority = RecommendationService.calculate_priority(
            error_count=5,
            reviewed_count=0,
            last_error_time=now,
            last_reviewed_time=None,
            difficulty=5,
            is_mastered=False,
            current_time=now,
        )

        # 0.4 * (5/6) + 0.4 * 0 + 0.2 * 1.0 = 0.4*0.833 + 0.2 = 0.333 + 0.2 = 0.533
        assert 0.5 < priority < 0.6

    def test_priority_overdue_review_high_difficulty(self):
        """Overdue for review (1 day past 1-day cycle) → high priority"""
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)

        priority = RecommendationService.calculate_priority(
            error_count=2,
            reviewed_count=0,
            last_error_time=one_day_ago,
            last_reviewed_time=one_day_ago,
            difficulty=5,
            is_mastered=False,
            current_time=now,
        )

        # 0.4 * (2/3) + 0.4 * 1.0 * 1.0 + 0.2 * 1.0
        # = 0.267 + 0.4 + 0.2 = 0.867
        assert 0.8 < priority < 0.95

    def test_priority_none_current_time_defaults(self):
        """None current_time defaults to now"""
        past = datetime.now(timezone.utc) - timedelta(days=1)

        # Should not raise
        priority = RecommendationService.calculate_priority(
            error_count=1,
            reviewed_count=0,
            last_error_time=past,
            last_reviewed_time=None,
            difficulty=3,
            is_mastered=False,
            current_time=None,
        )

        assert 0.0 <= priority <= 1.0

    def test_priority_clamped_to_one(self):
        """Priority never exceeds 1.0"""
        now = datetime.now(timezone.utc)
        far_past = now - timedelta(days=100)

        priority = RecommendationService.calculate_priority(
            error_count=100,
            reviewed_count=0,
            last_error_time=far_past,
            last_reviewed_time=far_past,
            difficulty=5,
            is_mastered=False,
            current_time=now,
        )

        assert priority <= 1.0

    def test_priority_clamped_to_zero(self):
        """Priority never goes below 0"""
        now = datetime.now(timezone.utc)

        priority = RecommendationService.calculate_priority(
            error_count=0,
            reviewed_count=100,
            last_error_time=now,
            last_reviewed_time=now,
            difficulty=0,
            is_mastered=False,
            current_time=now,
        )

        assert priority >= 0.0


class TestReviewSchedule:
    """Test review schedule progression."""

    def test_schedule_first_review(self):
        """First review (reviewed_count=0) → 1 day"""
        days = RecommendationService.get_next_review_days(0)
        assert days == 1

    def test_schedule_second_review(self):
        """Second review (reviewed_count=1) → 3 days"""
        days = RecommendationService.get_next_review_days(1)
        assert days == 3

    def test_schedule_third_review(self):
        """Third review (reviewed_count=2) → 7 days"""
        days = RecommendationService.get_next_review_days(2)
        assert days == 7

    def test_schedule_fourth_review(self):
        """Fourth review (reviewed_count=3) → 15 days"""
        days = RecommendationService.get_next_review_days(3)
        assert days == 15

    def test_schedule_fifth_review(self):
        """Fifth review (reviewed_count=4) → 30 days"""
        days = RecommendationService.get_next_review_days(4)
        assert days == 30

    def test_schedule_beyond_fifth_review(self):
        """Beyond 5 reviews → caps at 30 days"""
        days_6 = RecommendationService.get_next_review_days(5)
        days_10 = RecommendationService.get_next_review_days(10)

        assert days_6 == 30
        assert days_10 == 30

    def test_schedule_progression_all(self):
        """Full schedule: 1 → 3 → 7 → 15 → 30"""
        expected = [1, 3, 7, 15, 30]
        for count, expected_days in enumerate(expected):
            assert RecommendationService.get_next_review_days(count) == expected_days


@pytest.mark.asyncio
async def test_get_recommendations_empty():
    """get_recommendations with no questions returns empty list"""
    db = AsyncMock(spec=AsyncSession)
    db.begin.return_value.__aenter__.return_value = None
    db.begin.return_value.__aexit__.return_value = None

    # Mock execute to return empty result
    db.execute = AsyncMock(return_value=MagicMock(all=lambda: []))

    recommendations = await RecommendationService.get_recommendations(
        db=db,
        user_id="test-user",
        limit=10,
    )

    assert recommendations == []
    db.begin.assert_called_once()


@pytest.mark.asyncio
async def test_get_recommendations_sorted_by_priority():
    """get_recommendations returns items sorted by priority DESC"""
    db = AsyncMock(spec=AsyncSession)

    # Create mock questions and plans
    q1 = MagicMock(spec=Question)
    q1.question_id = "q1"
    q1.difficulty = 3
    q1.needs_review = False

    p1 = MagicMock(spec=ReviewPlan)
    p1.error_count = 1
    p1.reviewed_count = 0
    p1.last_error_time = datetime.now(timezone.utc)
    p1.last_reviewed_time = None
    p1.is_mastered = False

    q2 = MagicMock(spec=Question)
    q2.question_id = "q2"
    q2.difficulty = 5
    q2.needs_review = False

    p2 = MagicMock(spec=ReviewPlan)
    p2.error_count = 5
    p2.reviewed_count = 0
    p2.last_error_time = datetime.now(timezone.utc)
    p2.last_reviewed_time = None
    p2.is_mastered = False

    # Mock execute
    db.begin.return_value.__aenter__.return_value = None
    db.begin.return_value.__aexit__.return_value = None
    db.execute = AsyncMock(return_value=MagicMock(all=lambda: [(q1, p1), (q2, p2)]))

    recommendations = await RecommendationService.get_recommendations(
        db=db,
        user_id="test-user",
        limit=10,
    )

    # q2 should be first (higher difficulty + more errors = higher priority)
    assert len(recommendations) == 2
    assert recommendations[0]["question"].question_id == "q2"
    assert recommendations[0]["priority"] > recommendations[1]["priority"]


@pytest.mark.asyncio
async def test_get_recommendations_respects_limit():
    """get_recommendations respects limit parameter"""
    db = AsyncMock(spec=AsyncSession)

    # Create 5 questions
    items = []
    for i in range(5):
        q = MagicMock(spec=Question)
        q.question_id = f"q{i}"
        q.difficulty = 3
        q.needs_review = False

        p = MagicMock(spec=ReviewPlan)
        p.error_count = i + 1
        p.reviewed_count = 0
        p.last_error_time = datetime.now(timezone.utc)
        p.last_reviewed_time = None
        p.is_mastered = False

        items.append((q, p))

    db.begin.return_value.__aenter__.return_value = None
    db.begin.return_value.__aexit__.return_value = None
    db.execute = AsyncMock(return_value=MagicMock(all=lambda: items))

    recommendations = await RecommendationService.get_recommendations(
        db=db,
        user_id="test-user",
        limit=3,
    )

    assert len(recommendations) == 3


@pytest.mark.asyncio
async def test_get_recommendations_db_error():
    """get_recommendations raises on database error"""
    db = AsyncMock(spec=AsyncSession)

    db.begin.side_effect = Exception("Database connection failed")

    with pytest.raises(Exception, match="Database connection failed"):
        await RecommendationService.get_recommendations(
            db=db,
            user_id="test-user",
        )


@pytest.mark.asyncio
async def test_get_recommendation_stats():
    """get_recommendation_stats returns correct counts"""
    db = AsyncMock(spec=AsyncSession)

    # Mock the execute context manager
    db.begin.return_value.__aenter__.return_value = None
    db.begin.return_value.__aexit__.return_value = None

    # Create mocks for the three queries - simulate actual sequence
    mastered_result = MagicMock()
    mastered_result.scalar.return_value = 5

    total_result = MagicMock()
    total_result.scalar.return_value = 15

    subject_result = MagicMock()
    subject_result.all.return_value = [("math", 10), ("physics", 5)]

    # Track call count to return different results
    call_count = [0]

    async def mock_execute(stmt):
        call_count[0] += 1
        if call_count[0] == 1:
            return mastered_result
        elif call_count[0] == 2:
            return total_result
        else:
            return subject_result

    db.execute = mock_execute

    stats = await RecommendationService.get_recommendation_stats(
        db=db,
        user_id="test-user",
    )

    assert stats["mastered_count"] == 5
    assert stats["total_questions"] == 15
    assert stats["total_by_subject"]["math"] == 10
    assert stats["total_by_subject"]["physics"] == 5


@pytest.mark.asyncio
async def test_get_recommendation_stats_db_error():
    """get_recommendation_stats raises on database error"""
    db = AsyncMock(spec=AsyncSession)

    db.begin.side_effect = Exception("Database connection failed")

    with pytest.raises(Exception, match="Database connection failed"):
        await RecommendationService.get_recommendation_stats(
            db=db,
            user_id="test-user",
        )


@pytest.mark.asyncio
async def test_mark_reviewed_correct():
    """mark_reviewed with was_correct=True advances reviewed_count"""
    db = AsyncMock(spec=AsyncSession)

    plan = MagicMock(spec=ReviewPlan)
    plan.plan_id = "plan-1"
    plan.question_id = "q-1"
    plan.error_count = 1
    plan.reviewed_count = 0
    plan.is_mastered = False
    plan.last_reviewed_time = None

    # Mock execute
    db.begin.return_value.__aenter__.return_value = None
    db.begin.return_value.__aexit__.return_value = None
    db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(first=lambda: plan)))

    result = await RecommendationService.mark_reviewed(
        db=db,
        user_id="test-user",
        plan_id="plan-1",
        was_correct=True,
    )

    assert result.reviewed_count == 1
    assert result.is_mastered is False
    assert result.last_reviewed_time is not None
    assert result.next_review_time is not None


@pytest.mark.asyncio
async def test_mark_reviewed_mastered_after_five_reviews():
    """mark_reviewed marks mastered after 5 successful reviews"""
    db = AsyncMock(spec=AsyncSession)

    plan = MagicMock(spec=ReviewPlan)
    plan.plan_id = "plan-1"
    plan.question_id = "q-1"
    plan.error_count = 0
    plan.reviewed_count = 4
    plan.is_mastered = False

    db.begin.return_value.__aenter__.return_value = None
    db.begin.return_value.__aexit__.return_value = None
    db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(first=lambda: plan)))

    result = await RecommendationService.mark_reviewed(
        db=db,
        user_id="test-user",
        plan_id="plan-1",
        was_correct=True,
    )

    assert result.reviewed_count == 5
    assert result.is_mastered is True


@pytest.mark.asyncio
async def test_mark_reviewed_incorrect():
    """mark_reviewed with was_correct=False resets reviewed_count and increments error"""
    db = AsyncMock(spec=AsyncSession)

    plan = MagicMock(spec=ReviewPlan)
    plan.plan_id = "plan-1"
    plan.question_id = "q-1"
    plan.error_count = 1
    plan.reviewed_count = 2
    plan.is_mastered = False

    db.begin.return_value.__aenter__.return_value = None
    db.begin.return_value.__aexit__.return_value = None
    db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(first=lambda: plan)))

    result = await RecommendationService.mark_reviewed(
        db=db,
        user_id="test-user",
        plan_id="plan-1",
        was_correct=False,
    )

    assert result.reviewed_count == 0
    assert result.error_count == 2
    assert result.is_mastered is False


@pytest.mark.asyncio
async def test_mark_reviewed_plan_not_found():
    """mark_reviewed raises ValueError if plan not found"""
    db = AsyncMock(spec=AsyncSession)

    db.begin.return_value.__aenter__.return_value = None
    db.begin.return_value.__aexit__.return_value = None
    db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(first=lambda: None)))

    with pytest.raises(ValueError, match="ReviewPlan .* not found"):
        await RecommendationService.mark_reviewed(
            db=db,
            user_id="test-user",
            plan_id="nonexistent",
            was_correct=True,
        )


@pytest.mark.asyncio
async def test_mark_reviewed_db_error():
    """mark_reviewed raises on database error"""
    db = AsyncMock(spec=AsyncSession)

    db.begin.side_effect = Exception("Database transaction failed")

    with pytest.raises(Exception, match="Database transaction failed"):
        await RecommendationService.mark_reviewed(
            db=db,
            user_id="test-user",
            plan_id="plan-1",
            was_correct=True,
        )


class TestAlgorithmWeights:
    """Test algorithm weight distribution."""

    def test_weights_sum_to_one(self):
        """Algorithm weights sum to 1.0"""
        total = (
            RecommendationService.WEIGHT_ERROR_FREQUENCY +
            RecommendationService.WEIGHT_FORGETTING +
            RecommendationService.WEIGHT_DIFFICULTY
        )
        assert abs(total - 1.0) < 0.01

    def test_error_frequency_weight(self):
        """Error frequency weight is 0.4"""
        assert RecommendationService.WEIGHT_ERROR_FREQUENCY == 0.4

    def test_forgetting_weight(self):
        """Forgetting weight is 0.4"""
        assert RecommendationService.WEIGHT_FORGETTING == 0.4

    def test_difficulty_weight(self):
        """Difficulty weight is 0.2"""
        assert RecommendationService.WEIGHT_DIFFICULTY == 0.2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_priority_with_none_last_error_time_uses_default(self):
        """priority calculation with None fields handles defaults"""
        now = datetime.now(timezone.utc)

        # Should not raise
        priority = RecommendationService.calculate_priority(
            error_count=0,
            reviewed_count=0,
            last_error_time=now,
            last_reviewed_time=None,
            difficulty=3,
            is_mastered=False,
            current_time=now,
        )

        assert 0.0 <= priority <= 1.0

    def test_all_zero_values_priority(self):
        """All zero values in priority calculation → low priority"""
        now = datetime.now(timezone.utc)

        priority = RecommendationService.calculate_priority(
            error_count=0,
            reviewed_count=0,
            last_error_time=now,
            last_reviewed_time=None,
            difficulty=0,
            is_mastered=False,
            current_time=now,
        )

        assert priority == 0.0

    def test_all_max_values_priority(self):
        """All max values in priority calculation → high priority"""
        now = datetime.now(timezone.utc)

        priority = RecommendationService.calculate_priority(
            error_count=100,
            reviewed_count=0,
            last_error_time=now - timedelta(days=1000),
            last_reviewed_time=now - timedelta(days=1000),
            difficulty=5,
            is_mastered=False,
            current_time=now,
        )

        assert priority > 0.5


class TestConstants:
    """Test algorithm constants."""

    def test_review_schedule_dict_exists(self):
        """REVIEW_SCHEDULE dict exists and has correct values"""
        schedule = RecommendationService.REVIEW_SCHEDULE
        assert schedule[0] == 1
        assert schedule[1] == 3
        assert schedule[2] == 7
        assert schedule[3] == 15
        assert schedule[4] == 30

    def test_max_difficulty_is_five(self):
        """MAX_DIFFICULTY constant is 5"""
        assert RecommendationService.MAX_DIFFICULTY == 5

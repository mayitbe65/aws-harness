"""Unit tests for recommendation API endpoints."""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from uuid import uuid4

from src.main import app
from src.models.question import Question
from src.models.review_plan import ReviewPlan
from src.models.user import User, UserRole
from src.utils.security import create_access_token, hash_password
from src.database.db import async_session_maker


@pytest_asyncio.fixture
async def test_user():
    """Create a test user in the database."""
    user_id = str(uuid4())
    async with async_session_maker() as session:
        user = User(
            user_id=user_id,
            email=f"test{uuid4()}@test.edu",
            password_hash=hash_password("Password123"),
            role=UserRole.STUDENT,
            name="Test Student",
        )
        session.add(user)
        await session.commit()
    return user_id


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Create authentication headers with a valid JWT token."""
    token = create_access_token(test_user, "STUDENT")
    return {"Authorization": f"Bearer {token}"}, test_user


@pytest_asyncio.fixture
async def test_questions_with_plans(test_user):
    """Create test questions and review plans for a user."""
    async with async_session_maker() as session:
        questions = []
        now = datetime.now(timezone.utc)
        for i in range(5):
            q = Question(
                question_id=uuid4(),
                user_id=test_user,
                photo_url=f"s3://bucket/photo{i}.jpg",
                recognized_text=f"Problem {i}: x^{i+2} = 0",
                confidence=0.9,
                subject="math" if i % 2 == 0 else "physics",
                difficulty=i + 1,
                tags="test",
                error_count=i + 1,
                last_error_time=now,
            )
            session.add(q)
            await session.flush()

            # Create review plan
            plan = ReviewPlan(
                plan_id=uuid4(),
                user_id=test_user,
                question_id=q.question_id,
                error_count=i + 1,
                reviewed_count=i,
                last_error_time=now - timedelta(days=i),
                last_reviewed_time=now - timedelta(hours=i * 12) if i > 0 else None,
                next_review_time=now + timedelta(days=i + 1),
                priority=0.5 + (i * 0.1),
                is_mastered=False,
            )
            session.add(plan)
            questions.append(q)

        await session.commit()

    return questions, test_user


# Test GET /api/recommendations/plan
@pytest.mark.asyncio
async def test_get_recommendations_success(test_questions_with_plans, auth_headers):
    """Test successful retrieval of recommendations."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/plan?limit=10",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total_questions" in data
    assert "mastered_count" in data
    assert "total_by_subject" in data
    assert "generated_at" in data
    assert data["cache_ttl_seconds"] == 3600
    assert len(data["items"]) <= 5  # We created 5 questions


@pytest.mark.asyncio
async def test_get_recommendations_default_limit(test_questions_with_plans, auth_headers):
    """Test default limit parameter (should be 10)."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/plan",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 5  # Only 5 questions created


@pytest.mark.asyncio
async def test_get_recommendations_pagination(test_questions_with_plans, auth_headers):
    """Test limit parameter for pagination."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/plan?limit=2",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_get_recommendations_limit_validation(test_questions_with_plans, auth_headers):
    """Test limit parameter validation (1-50)."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    # Test too low
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/plan?limit=0",
            headers=headers,
        )
    assert response.status_code == 422

    # Test too high
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/plan?limit=100",
            headers=headers,
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_recommendations_by_subject(test_questions_with_plans, auth_headers):
    """Test that total_by_subject counts are correct."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/plan?limit=10",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "total_by_subject" in data
    # We created 3 math (indices 0, 2, 4) and 2 physics (indices 1, 3)
    assert data["total_by_subject"]["math"] == 3
    assert data["total_by_subject"]["physics"] == 2


@pytest.mark.asyncio
async def test_get_recommendations_without_auth(test_questions_with_plans):
    """Test that endpoint requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/plan",
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_recommendations_invalid_token(test_questions_with_plans):
    """Test that invalid token is rejected."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/plan",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_recommendations_priority_sorting(test_questions_with_plans, auth_headers):
    """Test that recommendations are sorted by priority (highest first)."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/plan?limit=10",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    items = data["items"]

    # Check that items are sorted by priority descending
    if len(items) > 1:
        for i in range(len(items) - 1):
            assert items[i]["priority"] >= items[i + 1]["priority"]


# Test POST /api/recommendations/mark-reviewed/{plan_id}
@pytest.mark.asyncio
async def test_mark_reviewed_correct(test_questions_with_plans, auth_headers):
    """Test marking a question as reviewed correctly."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    # Get first plan_id
    async with async_session_maker() as session:
        from sqlalchemy import select
        stmt = select(ReviewPlan).where(ReviewPlan.user_id == user_id).limit(1)
        result = await session.execute(stmt)
        plan = result.scalars().first()
        plan_id = str(plan.plan_id)

    # Mark as reviewed (correct)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/api/recommendations/mark-reviewed/{plan_id}",
            json={"reviewed": True},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == plan_id
    assert "next_review_time" in data
    assert data["message"] is not None
    assert "Great" in data["message"]
    assert data["reviewed_count"] > 0
    assert isinstance(data["is_mastered"], bool)


@pytest.mark.asyncio
async def test_mark_reviewed_incorrect(test_questions_with_plans, auth_headers):
    """Test marking a question as reviewed incorrectly."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    # Get first plan_id
    async with async_session_maker() as session:
        from sqlalchemy import select
        stmt = select(ReviewPlan).where(ReviewPlan.user_id == user_id).limit(1)
        result = await session.execute(stmt)
        plan = result.scalars().first()
        plan_id = str(plan.plan_id)
        original_error_count = plan.error_count

    # Mark as reviewed (incorrect)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/api/recommendations/mark-reviewed/{plan_id}",
            json={"reviewed": False},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "Keep practicing" in data["message"]
    # After marking incorrect, reviewed_count should reset to 0
    assert data["reviewed_count"] == 0


@pytest.mark.asyncio
async def test_mark_reviewed_nonexistent_plan(auth_headers):
    """Test marking a non-existent plan."""
    headers, _ = auth_headers
    fake_plan_id = str(uuid4())

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/api/recommendations/mark-reviewed/{fake_plan_id}",
            json={"reviewed": True},
            headers=headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mark_reviewed_without_auth(test_questions_with_plans):
    """Test that endpoint requires authentication."""
    plan_id = str(uuid4())

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/api/recommendations/mark-reviewed/{plan_id}",
            json={"reviewed": True},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mark_reviewed_invalid_body(test_questions_with_plans, auth_headers):
    """Test with invalid request body."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    # Get first plan_id
    async with async_session_maker() as session:
        from sqlalchemy import select
        stmt = select(ReviewPlan).where(ReviewPlan.user_id == user_id).limit(1)
        result = await session.execute(stmt)
        plan = result.scalars().first()
        plan_id = str(plan.plan_id)

    # Send invalid body (missing "reviewed" field)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/api/recommendations/mark-reviewed/{plan_id}",
            json={},
            headers=headers,
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mark_reviewed_clears_cache(test_questions_with_plans, auth_headers):
    """Test that marking reviewed clears the recommendation cache."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    # Get first plan_id
    async with async_session_maker() as session:
        from sqlalchemy import select
        stmt = select(ReviewPlan).where(ReviewPlan.user_id == user_id).limit(1)
        result = await session.execute(stmt)
        plan = result.scalars().first()
        plan_id = str(plan.plan_id)

    # First, get recommendations (should populate cache if Redis is available)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.get(
            "/api/recommendations/plan?limit=10",
            headers=headers,
        )
    assert response1.status_code == 200

    # Mark reviewed (should clear cache)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response2 = await client.post(
            f"/api/recommendations/mark-reviewed/{plan_id}",
            json={"reviewed": True},
            headers=headers,
        )
    assert response2.status_code == 200

    # Get recommendations again (should regenerate from DB, not cache)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response3 = await client.get(
            "/api/recommendations/plan?limit=10",
            headers=headers,
        )
    assert response3.status_code == 200


# Test GET /api/recommendations/stats
@pytest.mark.asyncio
async def test_get_stats_success(test_questions_with_plans, auth_headers):
    """Test successful retrieval of learning statistics."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/stats",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "total_questions" in data
    assert "mastered_count" in data
    assert "mastery_rate" in data
    assert "reviewed_today" in data
    assert "average_errors_per_question" in data
    assert "stats_generated_at" in data
    assert 0 <= data["mastery_rate"] <= 100
    assert data["total_questions"] == 5


@pytest.mark.asyncio
async def test_get_stats_empty_user(auth_headers):
    """Test stats for user with no questions."""
    headers, user_id = auth_headers

    # User has no questions
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/stats",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_questions"] == 0
    assert data["mastered_count"] == 0
    assert data["mastery_rate"] == 0.0
    assert data["reviewed_today"] == 0
    assert data["average_errors_per_question"] == 0.0


@pytest.mark.asyncio
async def test_get_stats_without_auth(test_questions_with_plans):
    """Test that stats endpoint requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/stats",
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_stats_mastery_rate_calculation(test_questions_with_plans, auth_headers):
    """Test mastery rate calculation."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    # Mark one question as mastered
    async with async_session_maker() as session:
        from sqlalchemy import select
        stmt = select(ReviewPlan).where(ReviewPlan.user_id == user_id).limit(1)
        result = await session.execute(stmt)
        plan = result.scalars().first()
        plan.is_mastered = True
        await session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/stats",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    # 1 out of 5 questions mastered = 20%
    assert abs(data["mastery_rate"] - 20.0) < 0.01


@pytest.mark.asyncio
async def test_get_stats_reviewed_today_count(test_questions_with_plans, auth_headers):
    """Test that reviewed_today counts questions reviewed since midnight."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Update some questions to have been reviewed today
    async with async_session_maker() as session:
        from sqlalchemy import select
        stmt = select(ReviewPlan).where(ReviewPlan.user_id == user_id).limit(2)
        result = await session.execute(stmt)
        plans = result.scalars().all()
        for plan in plans:
            plan.last_reviewed_time = today + timedelta(hours=1)
        await session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/stats",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reviewed_today"] == 2


@pytest.mark.asyncio
async def test_get_stats_average_errors(test_questions_with_plans, auth_headers):
    """Test average errors calculation."""
    questions, user_id = test_questions_with_plans
    headers, _ = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/recommendations/stats",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    # We created questions with error_count 1, 2, 3, 4, 5
    # Average should be 3
    assert abs(data["average_errors_per_question"] - 3.0) < 0.01

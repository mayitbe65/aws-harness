"""Unit tests for question endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
from sqlalchemy import select

from src.main import app
from src.utils.security import create_access_token, hash_password
from src.models.user import User, UserRole
from src.models.question import Question
from src.database.db import async_session_maker
from datetime import datetime, timezone


@pytest_asyncio.fixture
async def test_user():
    """Create a test user in the database."""
    user_id = str(uuid4())
    unique_email = f"student-{uuid4()}@test.edu"
    async with async_session_maker() as session:
        user = User(
            user_id=user_id,
            email=unique_email,
            password_hash=hash_password("Password123"),
            role=UserRole.STUDENT,
            name="Test Student",
        )
        session.add(user)
        await session.commit()
    return user_id


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Create authorization headers for test user."""
    token = create_access_token(test_user, "STUDENT")
    return {"Authorization": f"Bearer {token}"}, test_user


@pytest.mark.asyncio
async def test_create_question(auth_headers):
    """Test creating a question."""
    headers, user_id = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "x^2 + 2x + 1 = 0",
                "confidence": 0.95,
                "subject": "math",
                "difficulty": 3,
                "tags": "algebra,quadratic",
            },
            headers=headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["recognized_text"] == "x^2 + 2x + 1 = 0"
    assert data["confidence"] == 0.95
    assert data["needs_review"] is False
    assert data["subject"] == "math"
    assert data["difficulty"] == 3
    assert data["tags"] == "algebra,quadratic"
    assert data["error_count"] == 1


@pytest.mark.asyncio
async def test_create_question_low_confidence(auth_headers):
    """Test creating low confidence question (should mark needs_review per Rule R4)."""
    headers, user_id = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "[无法识别]",
                "confidence": 0.5,  # < 0.7
                "subject": "math",
                "difficulty": 1,
            },
            headers=headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["needs_review"] is True


@pytest.mark.asyncio
async def test_create_question_default_values(auth_headers):
    """Test creating question with default values."""
    headers, user_id = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "Problem text",
            },
            headers=headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["confidence"] == 0.0
    assert data["subject"] == "math"
    assert data["difficulty"] == 3
    assert data["tags"] == ""


@pytest.mark.asyncio
async def test_create_question_validation_errors(auth_headers):
    """Test validation errors in create request."""
    headers, user_id = auth_headers

    # Missing photo_url
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/questions/create",
            json={
                "recognized_text": "Problem text",
            },
            headers=headers,
        )
    assert response.status_code == 422

    # Invalid confidence (> 1.0)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "Problem text",
                "confidence": 1.5,
            },
            headers=headers,
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_questions(auth_headers):
    """Test listing questions with pagination."""
    headers, user_id = auth_headers

    # Create 3 questions
    for i in range(3):
        async with AsyncClient(app=app, base_url="http://test") as client:
            await client.post(
                "/api/questions/create",
                json={
                    "photo_url": f"s3://bucket/photo{i}.jpg",
                    "recognized_text": f"Problem {i}",
                    "confidence": 0.9,
                },
                headers=headers,
            )

    # List all
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/questions?page=1&page_size=20",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_list_questions_pagination(auth_headers):
    """Test pagination in list questions."""
    headers, user_id = auth_headers

    # Create 5 questions
    for i in range(5):
        async with AsyncClient(app=app, base_url="http://test") as client:
            await client.post(
                "/api/questions/create",
                json={
                    "photo_url": f"s3://bucket/photo{i}.jpg",
                    "recognized_text": f"Problem {i}",
                    "confidence": 0.9,
                },
                headers=headers,
            )

    # First page (2 items)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/questions?page=1&page_size=2",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["has_more"] is True

    # Second page
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/questions?page=2&page_size=2",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["has_more"] is True

    # Third page
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/questions?page=3&page_size=2",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_list_questions_needs_review_filter(auth_headers):
    """Test filtering questions by needs_review status."""
    headers, user_id = auth_headers

    # Create 2 high confidence, 2 low confidence
    async with AsyncClient(app=app, base_url="http://test") as client:
        for i in range(2):
            await client.post(
                "/api/questions/create",
                json={
                    "photo_url": f"s3://bucket/high{i}.jpg",
                    "recognized_text": f"High confidence {i}",
                    "confidence": 0.95,
                },
                headers=headers,
            )
        for i in range(2):
            await client.post(
                "/api/questions/create",
                json={
                    "photo_url": f"s3://bucket/low{i}.jpg",
                    "recognized_text": f"Low confidence {i}",
                    "confidence": 0.5,
                },
                headers=headers,
            )

    # Filter: needs_review_only=true
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/questions?needs_review_only=true",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["needs_review"] is True for item in data["items"])


@pytest.mark.asyncio
async def test_get_question(auth_headers):
    """Test getting question details."""
    headers, user_id = auth_headers

    # Create a question
    async with AsyncClient(app=app, base_url="http://test") as client:
        create_response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "Test problem",
                "confidence": 0.9,
            },
            headers=headers,
        )

    question_id = create_response.json()["question_id"]

    # Get details
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/questions/{question_id}",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["question_id"] == question_id
    assert data["recognized_text"] == "Test problem"
    assert data["confidence"] == 0.9


@pytest.mark.asyncio
async def test_get_question_not_found(auth_headers):
    """Test getting non-existent question."""
    headers, user_id = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/questions/{str(uuid4())}",
            headers=headers,
        )

    assert response.status_code == 404
    assert "题目不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_question(auth_headers):
    """Test updating question (manual correction)."""
    headers, user_id = auth_headers

    # Create a question
    async with AsyncClient(app=app, base_url="http://test") as client:
        create_response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "Original text",
                "confidence": 0.5,
            },
            headers=headers,
        )

    question_id = create_response.json()["question_id"]

    # Update
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            f"/api/questions/{question_id}",
            json={
                "recognized_text": "Corrected text",
                "needs_review": False,
                "subject": "physics",
                "difficulty": 4,
                "tags": "mechanics",
            },
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["recognized_text"] == "Corrected text"
    assert data["needs_review"] is False
    assert data["subject"] == "physics"
    assert data["difficulty"] == 4
    assert data["tags"] == "mechanics"


@pytest.mark.asyncio
async def test_update_question_partial(auth_headers):
    """Test partial update (only update some fields)."""
    headers, user_id = auth_headers

    # Create a question
    async with AsyncClient(app=app, base_url="http://test") as client:
        create_response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "Original",
                "subject": "math",
                "difficulty": 2,
            },
            headers=headers,
        )

    question_id = create_response.json()["question_id"]

    # Update only text
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            f"/api/questions/{question_id}",
            json={"recognized_text": "Updated text"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["recognized_text"] == "Updated text"
    assert data["subject"] == "math"  # unchanged
    assert data["difficulty"] == 2  # unchanged


@pytest.mark.asyncio
async def test_update_question_not_found(auth_headers):
    """Test updating non-existent question."""
    headers, user_id = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            f"/api/questions/{str(uuid4())}",
            json={"recognized_text": "New text"},
            headers=headers,
        )

    assert response.status_code == 404
    assert "题目不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_question(auth_headers):
    """Test deleting a question."""
    headers, user_id = auth_headers

    # Create a question
    async with AsyncClient(app=app, base_url="http://test") as client:
        create_response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "To delete",
                "confidence": 0.9,
            },
            headers=headers,
        )

    question_id = create_response.json()["question_id"]

    # Delete
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(
            f"/api/questions/{question_id}",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["deleted_question_id"] == question_id
    assert "已删除" in data["message"]

    # Verify it's deleted
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/questions/{question_id}",
            headers=headers,
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_question_not_found(auth_headers):
    """Test deleting non-existent question."""
    headers, user_id = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(
            f"/api/questions/{str(uuid4())}",
            headers=headers,
        )

    assert response.status_code == 404
    assert "题目不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_data_isolation_rule_r1():
    """Test Rule R1: users can only access their own questions."""
    # Create two users
    user1_id = str(uuid4())
    user2_id = str(uuid4())

    async with async_session_maker() as session:
        user1 = User(
            user_id=user1_id,
            email="user1@test.edu",
            password_hash=hash_password("Password123"),
            role=UserRole.STUDENT,
            name="User 1",
        )
        user2 = User(
            user_id=user2_id,
            email="user2@test.edu",
            password_hash=hash_password("Password123"),
            role=UserRole.STUDENT,
            name="User 2",
        )
        session.add(user1)
        session.add(user2)
        await session.commit()

    token1 = create_access_token(user1_id, "STUDENT")
    token2 = create_access_token(user2_id, "STUDENT")

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 1 creates a question
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "User 1 problem",
                "confidence": 0.9,
            },
            headers=headers1,
        )

    question_id = response.json()["question_id"]

    # User 2 tries to GET — should be 404 (not 403 to avoid leaking info)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/questions/{question_id}",
            headers=headers2,
        )
    assert response.status_code == 404

    # User 2 tries to UPDATE — should be 404
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            f"/api/questions/{question_id}",
            json={"recognized_text": "Hacked"},
            headers=headers2,
        )
    assert response.status_code == 404

    # User 2 tries to DELETE — should be 404
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(
            f"/api/questions/{question_id}",
            headers=headers2,
        )
    assert response.status_code == 404

    # User 2 lists questions — should be empty
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/questions",
            headers=headers2,
        )
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_auth_required():
    """Test that endpoints require authentication."""
    # No Authorization header
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "Problem",
            },
        )
    assert response.status_code == 401
    assert "缺少 Authorization header" in response.json()["detail"]

    # Invalid token
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/questions",
            headers={"Authorization": "Bearer invalid_token"},
        )
    assert response.status_code == 401
    assert "无效或过期的 token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_transaction_protection_rule_r5(auth_headers):
    """Test Rule R5: transaction protection on create (question + review_plan)."""
    headers, user_id = auth_headers

    # Create a question
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/questions/create",
            json={
                "photo_url": "s3://bucket/photo.jpg",
                "recognized_text": "Problem",
                "confidence": 0.9,
            },
            headers=headers,
        )

    assert response.status_code == 201
    question_id = response.json()["question_id"]

    # Verify both question and review_plan were created atomically
    async with async_session_maker() as session:
        stmt = select(Question).where(Question.question_id == question_id)
        result = await session.execute(stmt)
        question = result.scalars().first()
        assert question is not None

        # Check that review_plan was created too
        from src.models.review_plan import ReviewPlan
        stmt = select(ReviewPlan).where(ReviewPlan.question_id == question_id)
        result = await session.execute(stmt)
        review_plan = result.scalars().first()
        assert review_plan is not None
        assert review_plan.priority == 0.9

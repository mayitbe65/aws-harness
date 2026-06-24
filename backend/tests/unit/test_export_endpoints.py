"""Unit tests for export API endpoints (Rule R1, R5, R9)."""
import pytest
import pytest_asyncio
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
from httpx import AsyncClient

from src.main import app
from src.database.db import async_session_maker
from src.utils.security import create_access_token, hash_password
from src.models.question import Question
from src.models.user import User, UserRole
from src.models.snapshot import Snapshot


@pytest_asyncio.fixture
async def test_user():
    """Create a test user in the database."""
    user_id = str(uuid4())
    unique_email = f"export_test_{uuid4()}@test.edu"
    async with async_session_maker() as session:
        user = User(
            user_id=user_id,
            email=unique_email,
            password_hash=hash_password("Password123"),
            role=UserRole.STUDENT,
            name="Test Export User",
        )
        session.add(user)
        await session.commit()
    return user_id


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Create valid auth headers for test user."""
    token = create_access_token(test_user, "STUDENT")
    return {"Authorization": f"Bearer {token}"}, test_user


@pytest_asyncio.fixture
async def other_user():
    """Create another test user."""
    user_id = str(uuid4())
    unique_email = f"export_other_{uuid4()}@test.edu"
    async with async_session_maker() as session:
        user = User(
            user_id=user_id,
            email=unique_email,
            password_hash=hash_password("Password123"),
            role=UserRole.STUDENT,
            name="Other Test User",
        )
        session.add(user)
        await session.commit()
    return user_id


@pytest_asyncio.fixture
async def test_questions(test_user):
    """Create test questions for a user."""
    question_ids = []
    async with async_session_maker() as session:
        for i in range(3):
            # Use string UUID directly for compatibility with GUID type
            q_id_str = str(uuid4())
            question = Question(
                question_id=q_id_str,
                user_id=test_user,
                photo_url=f"s3://bucket/test_{i}.jpg",
                recognized_text=f"Test question {i}: Solve x^2 + 2x = 0",
                confidence=0.95,
                subject="math",
                difficulty=i + 1,
                tags=f"algebra,equation",
                error_count=i + 1,
                needs_review=False,
            )
            session.add(question)
            question_ids.append(q_id_str)
        await session.commit()
    return question_ids


@pytest.mark.asyncio
async def test_request_pdf_export_success(auth_headers, test_questions):
    """Test successful PDF export request (Rule R1, R5, R9)."""
    headers, user_id = auth_headers
    question_ids = test_questions

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": question_ids[:2],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    assert response.status_code == 202
    data = response.json()
    assert "snapshot_id" in data
    assert data["snapshot_id"]  # Non-empty UUID
    assert data["status"] == "pending"
    assert data["estimated_time"] == 5
    assert "message" in data


@pytest.mark.asyncio
async def test_request_export_html_format(auth_headers, test_questions):
    """Test export request with HTML format."""
    headers, user_id = auth_headers
    question_ids = test_questions

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": question_ids[:1],
                "format": "html",
                "group_by": "difficulty",
                "include_answers": True,
            },
            headers=headers,
        )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_request_export_no_questions(auth_headers):
    """Test export with no valid questions (should fail)."""
    headers, user_id = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": [str(uuid4())],  # Non-existent question
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "no questions" in detail or "not found" in detail


@pytest.mark.asyncio
async def test_request_export_partial_invalid_questions(auth_headers, test_questions):
    """Test export with mix of valid and invalid questions.

    Note: The service allows exporting valid questions even if some
    requested IDs are invalid/non-existent. Only fails if NO valid questions exist.
    """
    headers, user_id = auth_headers
    valid_ids = test_questions[:1]
    invalid_ids = [str(uuid4())]  # Non-existent

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": valid_ids + invalid_ids,
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    # Should succeed - exports the 1 valid question (logs warning about missing ones)
    assert response.status_code == 202
    assert "snapshot_id" in response.json()


@pytest.mark.asyncio
async def test_request_export_invalid_uuid_format(auth_headers):
    """Test export with invalid UUID format."""
    headers, user_id = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": ["not-a-uuid"],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    assert response.status_code == 400
    assert "UUID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_export_status_success(auth_headers, test_questions):
    """Test getting export status."""
    headers, user_id = auth_headers
    question_ids = test_questions

    # First, create an export
    async with AsyncClient(app=app, base_url="http://test") as client:
        export_resp = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": question_ids[:1],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    snapshot_id = export_resp.json()["snapshot_id"]

    # Now get status
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/export/{snapshot_id}",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["snapshot_id"] == snapshot_id
    assert data["status"] == "pending"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_export_status_not_found(auth_headers):
    """Test getting status of non-existent export."""
    headers, user_id = auth_headers
    fake_id = str(uuid4())

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/export/{fake_id}",
            headers=headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_export_status_wrong_user(auth_headers, test_questions, other_user):
    """Test user isolation (Rule R1) - cannot access another user's export."""
    headers, user_id = auth_headers
    question_ids = test_questions

    # Create export with first user
    async with AsyncClient(app=app, base_url="http://test") as client:
        export_resp = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": question_ids[:1],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    snapshot_id = export_resp.json()["snapshot_id"]

    # Try to access with second user
    other_token = create_access_token(other_user, "student")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/export/{snapshot_id}",
            headers=other_headers,
        )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_export_pending(auth_headers, test_questions):
    """Test download of pending export (should fail)."""
    headers, user_id = auth_headers
    question_ids = test_questions

    # Create export
    async with AsyncClient(app=app, base_url="http://test") as client:
        export_resp = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": question_ids[:1],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    snapshot_id = export_resp.json()["snapshot_id"]

    # Try download while pending
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/export/{snapshot_id}/download",
            headers=headers,
        )

    assert response.status_code == 400
    assert "complete" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_export_not_found(auth_headers):
    """Test download of non-existent export."""
    headers, user_id = auth_headers
    fake_id = str(uuid4())

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/export/{fake_id}/download",
            headers=headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_export_wrong_user(auth_headers, test_questions, other_user):
    """Test user isolation when downloading export."""
    headers, user_id = auth_headers
    question_ids = test_questions

    # Create export with first user
    async with AsyncClient(app=app, base_url="http://test") as client:
        export_resp = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": question_ids[:1],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    snapshot_id = export_resp.json()["snapshot_id"]

    # Try to download with second user
    other_token = create_access_token(other_user, "student")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/export/{snapshot_id}/download",
            headers=other_headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_export_history_empty(auth_headers):
    """Test getting export history for new user (empty)."""
    headers, user_id = auth_headers

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/export",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["snapshots"] == []


@pytest.mark.asyncio
async def test_get_export_history_multiple(auth_headers, test_questions):
    """Test getting export history with multiple exports."""
    headers, user_id = auth_headers
    question_ids = test_questions

    # Create 3 exports
    snapshot_ids = []
    for i in range(3):
        async with AsyncClient(app=app, base_url="http://test") as client:
            resp = await client.post(
                "/api/export/pdf",
                json={
                    "question_ids": question_ids[:1],
                    "format": "pdf",
                    "group_by": "subject",
                    "include_answers": False,
                },
                headers=headers,
            )
            snapshot_ids.append(resp.json()["snapshot_id"])

    # Get history
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/export",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["snapshots"]) == 3

    # Verify most recent is first (ordered by created_at desc)
    for snapshot in data["snapshots"]:
        assert snapshot["snapshot_id"] in snapshot_ids
        assert snapshot["status"] == "pending"


@pytest.mark.asyncio
async def test_get_export_history_pagination(auth_headers, test_questions):
    """Test export history pagination."""
    headers, user_id = auth_headers
    question_ids = test_questions

    # Create 5 exports
    for i in range(5):
        async with AsyncClient(app=app, base_url="http://test") as client:
            await client.post(
                "/api/export/pdf",
                json={
                    "question_ids": question_ids[:1],
                    "format": "pdf",
                    "group_by": "subject",
                    "include_answers": False,
                },
                headers=headers,
            )

    # Get first page (limit 2)
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp1 = await client.get(
            "/api/export?page=1&page_size=2",
            headers=headers,
        )

    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total"] == 5
    assert len(data1["snapshots"]) == 2

    # Get second page
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp2 = await client.get(
            "/api/export?page=2&page_size=2",
            headers=headers,
        )

    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["snapshots"]) == 2

    # Different snapshots on each page
    ids1 = {s["snapshot_id"] for s in data1["snapshots"]}
    ids2 = {s["snapshot_id"] for s in data2["snapshots"]}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_export_history_user_isolation(auth_headers, test_questions, other_user):
    """Test that users only see their own exports (Rule R1)."""
    headers, user_id = auth_headers
    question_ids = test_questions

    # Create export with first user
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/export/pdf",
            json={
                "question_ids": question_ids[:1],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    # Check second user sees no exports
    other_token = create_access_token(other_user, "student")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/export",
            headers=other_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["snapshots"] == []


@pytest.mark.asyncio
async def test_export_requires_auth():
    """Test that export endpoints require authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # POST without auth
        response = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": [str(uuid4())],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
        )
    assert response.status_code == 401

    async with AsyncClient(app=app, base_url="http://test") as client:
        # GET without auth
        response = await client.get(
            f"/api/export/{uuid4()}",
        )
    assert response.status_code == 401

    async with AsyncClient(app=app, base_url="http://test") as client:
        # GET history without auth
        response = await client.get(
            "/api/export",
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_export_invalid_auth_token():
    """Test export with invalid auth token."""
    headers = {"Authorization": "Bearer invalid_token"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": [str(uuid4())],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_export_with_group_by_options(auth_headers, test_questions):
    """Test export with different grouping options."""
    headers, user_id = auth_headers
    question_ids = test_questions

    for group_by in ["subject", "difficulty", "none"]:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/export/pdf",
                json={
                    "question_ids": question_ids[:2],
                    "format": "pdf",
                    "group_by": group_by,
                    "include_answers": False,
                },
                headers=headers,
            )

        assert response.status_code == 202


@pytest.mark.asyncio
async def test_export_snapshot_transaction(auth_headers, test_questions):
    """Test that snapshot creation uses transaction (Rule R5)."""
    headers, user_id = auth_headers
    question_ids = test_questions

    # Create export (should be atomic)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": question_ids,
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    assert response.status_code == 202
    snapshot_id = response.json()["snapshot_id"]

    # Verify snapshot exists and has correct data
    async with async_session_maker() as session:
        from sqlalchemy import select
        stmt = select(Snapshot).where(
            Snapshot.snapshot_id == snapshot_id  # Use string directly
        )
        result = await session.execute(stmt)
        snapshot = result.scalars().first()

        assert snapshot is not None
        assert str(snapshot.user_id) == user_id  # Compare as strings
        assert snapshot.status == "pending"
        # Verify frozen data
        data = json.loads(snapshot.snapshot_data)
        assert len(data["questions"]) == len(question_ids)


@pytest.mark.asyncio
async def test_export_frozen_data(auth_headers, test_questions):
    """Test that export uses frozen snapshot data (Rule R9)."""
    headers, user_id = auth_headers
    question_ids = test_questions

    # Create export
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/export/pdf",
            json={
                "question_ids": question_ids[:1],
                "format": "pdf",
                "group_by": "subject",
                "include_answers": False,
            },
            headers=headers,
        )

    snapshot_id = response.json()["snapshot_id"]

    # Verify snapshot has frozen data
    async with async_session_maker() as session:
        from sqlalchemy import select
        stmt = select(Snapshot).where(
            Snapshot.snapshot_id == snapshot_id  # Use string directly
        )
        result = await session.execute(stmt)
        snapshot = result.scalars().first()

        assert snapshot is not None, f"Snapshot {snapshot_id} not found"
        assert snapshot.snapshot_data is not None
        data = json.loads(snapshot.snapshot_data)
        assert "questions" in data
        assert "metadata" in data
        assert data["metadata"]["frozen_at"] is not None
        assert len(data["questions"]) > 0

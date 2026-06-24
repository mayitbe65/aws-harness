"""Unit tests for authentication endpoints."""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.main import app
from src.utils.security import hash_password, create_access_token
from src.models.user import User, UserRole
from src.database.db import async_session_maker


@pytest.fixture
async def test_user():
    """Create a test user in the database."""
    user_id = str(uuid4())
    async with async_session_maker() as session:
        user = User(
            user_id=user_id,
            email="student@test.edu",
            password_hash=hash_password("Password123"),
            role=UserRole.STUDENT,
            name="Test Student",
        )
        session.add(user)
        await session.commit()
    return user_id, "student@test.edu", "Password123"


@pytest.mark.asyncio
async def test_login_success(test_user):
    """Test successful login with valid credentials."""
    user_id, email, password = test_user

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["user_id"] == user_id
    assert data["role"] == "STUDENT"
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


@pytest.mark.asyncio
async def test_login_invalid_email():
    """Test login with non-existent email."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": "nonexistent@test.edu", "password": "anypassword"},
        )

    assert response.status_code == 401
    assert "邮箱或密码错误" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_wrong_password(test_user):
    """Test login with wrong password."""
    user_id, email, password = test_user

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "WrongPassword123"},
        )

    assert response.status_code == 401
    assert "邮箱或密码错误" in response.json()["detail"]


@pytest.mark.asyncio
async def test_verify_password_success(test_user):
    """Test successful password verification."""
    user_id, email, password = test_user

    # Get a valid token
    token = create_access_token(user_id, "STUDENT")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/verify-password",
            json={"password": password},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["valid"] is True


@pytest.mark.asyncio
async def test_verify_password_wrong(test_user):
    """Test password verification with wrong password."""
    user_id, email, password = test_user

    token = create_access_token(user_id, "STUDENT")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/verify-password",
            json={"password": "WrongPassword123"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["valid"] is False


@pytest.mark.asyncio
async def test_verify_password_no_token():
    """Test password verification without Authorization header."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/verify-password",
            json={"password": "anypassword"},
        )

    assert response.status_code == 401
    assert "缺少 Authorization header" in response.json()["detail"]


@pytest.mark.asyncio
async def test_verify_password_invalid_token():
    """Test password verification with invalid token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/verify-password",
            json={"password": "anypassword"},
            headers={"Authorization": "Bearer invalid_token"},
        )

    assert response.status_code == 401
    assert "无效或过期的 token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_verify_password_malformed_auth_header():
    """Test password verification with malformed Authorization header."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/verify-password",
            json={"password": "anypassword"},
            headers={"Authorization": "InvalidFormat"},
        )

    assert response.status_code == 401
    assert "无效的 Authorization header 格式" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_invalid_email_format():
    """Test login with invalid email format."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": "not-an-email", "password": "password"},
        )

    assert response.status_code == 422  # Validation error

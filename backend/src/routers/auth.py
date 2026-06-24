"""Authentication routes and endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.db import get_db
from src.models.user import User
from src.schemas.auth import LoginRequest, LoginResponse, PasswordVerifyRequest
from src.utils.security import verify_password, create_access_token, decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


async def get_current_user_from_token(
    authorization: str = Header(None),
) -> dict:
    """
    Extract current user information from JWT token in Authorization header.

    Args:
        authorization: Authorization header value (Bearer token)

    Returns:
        Dictionary with user_id and role

    Raises:
        HTTPException: 401 if token is missing, malformed, or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Authorization header 格式",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的 token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


@router.post("/login", response_model=LoginResponse, status_code=200)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    """
    User login endpoint.

    Verifies email and password, returns JWT token on success.

    Args:
        request: Login request with email and password
        db: Database session

    Returns:
        LoginResponse with access token and user info

    Raises:
        HTTPException: 401 if email or password is incorrect
    """
    # Query user by email (Rule R1: email is unique, query doesn't involve user_id isolation)
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    # Verify user exists and password is correct
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token
    token = create_access_token(str(user.user_id), user.role.value)

    logger.info(f"User {user.email} logged in successfully")

    return LoginResponse(
        access_token=token,
        user_id=str(user.user_id),
        role=user.role.value,
        expires_in=3600,
    )


@router.post("/verify-password", status_code=200)
async def verify_password_endpoint(
    request: PasswordVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token),
) -> dict:
    """
    Verify current user's password.

    Used for sensitive operations that require password confirmation.

    Args:
        request: Password to verify
        db: Database session
        current_user: Current user from JWT token

    Returns:
        Dictionary with 'valid' boolean

    Raises:
        HTTPException: 404 if user not found, 401 if token is invalid
    """
    current_user_id = current_user["user_id"]

    # Query user by user_id (Rule R1: user_id isolation)
    stmt = select(User).where(User.user_id == current_user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # Verify password
    valid = verify_password(request.password, user.password_hash)

    logger.info(f"Password verification for user {user.email}: {valid}")

    return {"valid": valid}

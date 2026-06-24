"""Security utilities for password hashing and JWT token management."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import bcrypt
from jose import jwt, JWTError

from src.config import settings


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Previously hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(user_id: str, role: str) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to include in token
        role: User role to include in token

    Returns:
        JWT token string
    """
    # Calculate expiry time based on configured hours
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=settings.JWT_EXPIRY_HOURS)

    # Create payload
    payload = {
        'sub': user_id,
        'role': role,
        'iat': now,
        'exp': expiry,
    }

    # Encode token
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return token


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary with user_id and role on success, None on failure
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Extract user_id from 'sub' claim
        user_id = payload.get('sub')
        role = payload.get('role')

        if user_id is None or role is None:
            return None

        return {
            'user_id': user_id,
            'role': role,
        }
    except JWTError:
        return None

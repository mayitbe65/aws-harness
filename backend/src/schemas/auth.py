"""Pydantic schemas for authentication endpoints."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class LoginRequest(BaseModel):
    """Request body for login endpoint."""
    email: EmailStr
    password: str = Field(..., min_length=1, description="Plain text password")


class LoginResponse(BaseModel):
    """Response body for login endpoint."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    expires_in: int


class PasswordVerifyRequest(BaseModel):
    """Request body for password verification endpoint."""
    password: str = Field(..., min_length=1, description="Plain text password to verify")


class ErrorResponse(BaseModel):
    """Standard error response."""
    status: str = "error"
    code: str
    message: str
    details: Optional[dict] = None

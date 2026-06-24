"""User model with role-based access control."""
from enum import Enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Index, Enum as SQLEnum
from sqlalchemy.types import TypeDecorator, CHAR
from uuid import UUID as PyUUID

from src.database.db import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type that uses CHAR(32) with SQLite."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, PyUUID):
            return value.hex
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return PyUUID(value)


class UserRole(str, Enum):
    """Enum for user roles in the system."""
    ADMIN = "ADMIN"
    STUDENT = "STUDENT"


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    # Primary key
    user_id = Column(
        GUID(),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    # Email (unique, indexed)
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Password hash (never store plaintext)
    password_hash = Column(
        String(255),
        nullable=False,
    )

    # User role (indexed for permission queries)
    role = Column(
        SQLEnum(UserRole),
        nullable=False,
        default=UserRole.STUDENT,
        index=True,
    )

    # User display name
    name = Column(
        String(255),
        nullable=False,
    )

    # Timestamps for audit trail
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Explicit indices
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_role', 'role'),
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, email={self.email}, role={self.role})>"

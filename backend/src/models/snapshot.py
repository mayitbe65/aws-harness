"""Snapshot model for exporting frozen question data.

Rule R9: Snapshot mechanism freezes question data at export time to prevent
mid-export modifications. Snapshots auto-expire after 30 days.
"""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import relationship

from src.database.db import Base
from src.models.user import GUID


class Snapshot(Base):
    """导出快照模型 — 冻结题目数据以防止导出中间修改（规则 R9）。

    在导出时刻冻结题目数据，生成 PDF/HTML 文档。
    快照在创建后 30 天自动过期并被清理。
    """
    __tablename__ = "snapshots"

    # Primary key
    snapshot_id = Column(
        GUID(),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    # Foreign key to users table (with CASCADE delete per R1)
    user_id = Column(
        GUID(),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Export options
    question_ids = Column(
        Text,
        nullable=False,
    )  # Comma-separated question IDs

    format = Column(
        String(20),
        default="pdf",
        nullable=False,
    )  # "pdf" or "html"

    group_by = Column(
        String(20),
        default="subject",
        nullable=False,
    )  # "subject", "difficulty", or "none"

    include_answers = Column(
        String(10),
        default="false",
        nullable=False,
    )  # "true" or "false"

    # Frozen data (Rule R9: snapshot at export time prevents modifications)
    snapshot_data = Column(
        Text,
        nullable=False,
    )  # JSON string: {questions: [...], metadata: {...}}

    # File and status
    file_url = Column(
        String(512),
        nullable=True,
    )  # S3 URL or local path where PDF is stored

    status = Column(
        String(20),
        default="pending",
        nullable=False,
    )  # "pending", "generating", "completed", "failed"

    error_message = Column(
        Text,
        nullable=True,
    )  # Error details if status is "failed"

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )  # Time when PDF generation completed

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )  # Auto-delete after this time (default: 30 days)

    # Relationships
    user = relationship("User", backref="snapshots")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_snapshots_user_created", "user_id", "created_at"),
        Index("ix_snapshots_expires", "expires_at"),
        Index("ix_snapshots_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Snapshot(snapshot_id={self.snapshot_id}, "
            f"user_id={self.user_id}, format={self.format}, status={self.status})>"
        )

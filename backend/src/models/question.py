"""Question model for storing recognized questions from photos."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import relationship

from src.database.db import Base
from src.models.user import GUID


class Question(Base):
    """题目模型 — 存储拍照识别的数学题或作业题。

    存储用户上传照片经过 Vision API 识别后的题目信息。
    每条记录关联一个用户和多个复习计划。
    """
    __tablename__ = "questions"

    # Primary key
    question_id = Column(
        GUID(),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    # Foreign key to users table (with CASCADE delete per R1, R4)
    user_id = Column(
        GUID(),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 题目来源和内容
    photo_url = Column(
        String(512),
        nullable=True,
    )  # S3 URL or local path

    recognized_text = Column(
        Text,
        nullable=False,
    )  # OCR 识别结果

    confidence = Column(
        Float,
        default=0.0,
        nullable=False,
    )  # Vision API 可信度 [0, 1]

    # 质量标记（规则 R4 - 质量检查）
    needs_review = Column(
        Boolean,
        default=False,
        nullable=False,
    )  # True: 识别质量低，需人工审核

    review_notes = Column(
        Text,
        nullable=True,
    )  # 人工审核备注

    # 题目属性
    subject = Column(
        String(50),
        default="math",
        nullable=False,
    )  # 学科：math, physics, chemistry...

    difficulty = Column(
        Integer,
        default=3,
        nullable=False,
    )  # 难度级别：1-5，5 最难

    tags = Column(
        String(256),
        default="",
        nullable=False,
    )  # 标签：逗号分隔，如 "algebra,quadratic"

    # 错误次数和最后错误时间
    error_count = Column(
        Integer,
        default=1,
        nullable=False,
    )

    last_error_time = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    review_plans = relationship(
        "ReviewPlan",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    user = relationship("User", backref="questions")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_questions_user_created", "user_id", "created_at"),
        Index("ix_questions_needs_review", "needs_review"),
    )

    def __repr__(self) -> str:
        return (
            f"<Question(question_id={self.question_id}, "
            f"user_id={self.user_id}, subject={self.subject})>"
        )

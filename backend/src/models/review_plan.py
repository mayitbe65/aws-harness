"""ReviewPlan model for managing question review scheduling."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship

from src.database.db import Base
from src.models.user import GUID


class ReviewPlan(Base):
    """复习计划模型 — 基于艾宾浩斯遗忘曲线的复习安排。

    为每个题目跟踪复习进度和下次复习时间。
    实现规则 R5（事务保护）：所有更新必须在事务中进行。
    """
    __tablename__ = "review_plans"

    # Primary key
    plan_id = Column(
        GUID(),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    # Foreign keys (with CASCADE delete per R1)
    user_id = Column(
        GUID(),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question_id = Column(
        GUID(),
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 复习统计
    error_count = Column(
        Integer,
        default=0,
        nullable=False,
    )  # 总错误次数

    reviewed_count = Column(
        Integer,
        default=0,
        nullable=False,
    )  # 复习过的次数

    # 复习进度
    last_error_time = Column(
        DateTime(timezone=True),
        nullable=True,
    )  # 最后出错时间

    last_reviewed_time = Column(
        DateTime(timezone=True),
        nullable=True,
    )  # 最后复习时间

    next_review_time = Column(
        DateTime(timezone=True),
        nullable=True,
    )  # 下次复习推荐时间

    # 优先级和状态
    priority = Column(
        Float,
        default=0.0,
        nullable=False,
    )  # [0, 1] 优先级分数

    is_mastered = Column(
        Boolean,
        default=False,
        nullable=False,
    )  # True: 已掌握，不再推荐

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    question = relationship("Question", back_populates="review_plans")
    user = relationship("User", backref="review_plans")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_review_plans_user_next_review", "user_id", "next_review_time"),
        Index("ix_review_plans_is_mastered", "is_mastered"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReviewPlan(plan_id={self.plan_id}, "
            f"question_id={self.question_id}, priority={self.priority})>"
        )

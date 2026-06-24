"""Pydantic schemas for recommendation endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ReviewItemResponse(BaseModel):
    """Single item in recommendation list"""
    question_id: str
    photo_url: str
    recognized_text: str
    subject: str
    difficulty: int
    error_count: int
    reviewed_count: int
    last_error_time: datetime
    last_reviewed_time: Optional[datetime]
    next_review_time: datetime
    priority: float = Field(..., ge=0.0, le=1.0, description="Priority score [0, 1]")

    model_config = {"from_attributes": True}


class RecommendationListResponse(BaseModel):
    """API response: list of recommended questions"""
    items: List[ReviewItemResponse]
    total_questions: int
    mastered_count: int
    total_by_subject: dict = Field(default_factory=dict, description="Question count by subject")
    generated_at: datetime
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")


class MarkReviewedRequest(BaseModel):
    """Mark question as reviewed"""
    reviewed: bool = Field(..., description="true: 做对了, false: 做错了")


class MarkReviewedResponse(BaseModel):
    """Response after marking reviewed"""
    plan_id: str
    next_review_time: datetime
    reviewed_count: int
    is_mastered: bool
    message: str

"""Pydantic schemas for question endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateQuestionRequest(BaseModel):
    """创建题目请求 — 从拍照识别结果存储题目"""
    photo_url: str = Field(..., min_length=5, description="Photo S3 URL or local path")
    recognized_text: str = Field(..., min_length=5, max_length=10000, description="OCR 识别结果")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Vision API 可信度")
    subject: str = Field(default="math", description="Subject: math, physics, chemistry...")
    difficulty: int = Field(default=3, ge=1, le=5, description="Difficulty level: 1-5")
    tags: str = Field(default="", description="Comma-separated tags")


class UpdateQuestionRequest(BaseModel):
    """更新题目请求 — 人工纠正识别结果"""
    recognized_text: Optional[str] = Field(None, min_length=5, max_length=10000)
    subject: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    tags: Optional[str] = None
    needs_review: Optional[bool] = None
    review_notes: Optional[str] = None


class QuestionResponse(BaseModel):
    """题目响应模型"""
    question_id: str
    user_id: str
    photo_url: str
    recognized_text: str
    confidence: float
    subject: str
    difficulty: int
    tags: str
    error_count: int
    needs_review: bool
    review_notes: Optional[str]
    last_error_time: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionListResponse(BaseModel):
    """题目列表响应 — 分页"""
    items: List[QuestionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class DeleteQuestionResponse(BaseModel):
    """删除题目响应"""
    status: str
    message: str
    deleted_question_id: str

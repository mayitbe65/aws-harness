"""Pydantic schemas for export endpoints (Rule R9 - Snapshot mechanism)."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ExportRequest(BaseModel):
    """请求导出题目 — Rule R9 快照机制"""
    question_ids: List[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of question IDs to export (1-100 questions)"
    )
    format: str = Field(
        default="pdf",
        pattern="^(pdf|html)$",
        description="Export format: 'pdf' or 'html'"
    )
    group_by: str = Field(
        default="subject",
        pattern="^(subject|difficulty|none)$",
        description="Group questions by: 'subject', 'difficulty', or 'none'"
    )
    include_answers: bool = Field(
        default=False,
        description="Whether to include answer explanations"
    )


class ExportResponse(BaseModel):
    """导出请求响应 — 返回快照 ID 和初始状态"""
    snapshot_id: str = Field(..., description="Snapshot ID for tracking")
    status: str = Field(..., description="Status: 'pending' or 'generating'")
    message: str = Field(..., description="Human-readable status message")
    estimated_time: int = Field(
        default=5,
        description="Estimated time to generate PDF in seconds"
    )


class SnapshotStatusResponse(BaseModel):
    """快照状态响应 — 检查导出进度"""
    snapshot_id: str
    status: str  # "pending", "generating", "completed", "failed"
    created_at: datetime
    completed_at: Optional[datetime] = None
    file_url: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class ExportHistoryResponse(BaseModel):
    """导出历史列表 — 分页"""
    snapshots: List[SnapshotStatusResponse]
    total: int


class SnapshotHistoryResponse(BaseModel):
    """导出历史列表 — 分页（旧名称，保持兼容）"""
    snapshots: List[SnapshotStatusResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class SnapshotDeleteResponse(BaseModel):
    """删除快照响应"""
    status: str
    message: str
    deleted_snapshot_id: str

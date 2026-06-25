"""Schemas for photo recognition and Vision API integration."""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RecognitionQuality(str, Enum):
    """Quality levels for recognition results (Rule R4: three-level validation)."""
    HIGH = "high"       # confidence >= 0.7 → auto-save
    MEDIUM = "medium"   # 0.5 <= confidence < 0.7 → mark needs_review=true
    LOW = "low"         # confidence < 0.5 → recognition failed


class RecognitionResult(BaseModel):
    """Recognition result from Vision API."""
    recognized_text: str = Field(..., description="Recognized text from the photo")
    confidence: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score [0, 1] (Rule R2: default to 0 if missing)"
    )
    has_formulas: bool = Field(default=False, description="Contains math formulas")
    has_diagrams: bool = Field(default=False, description="Contains diagrams")
    raw_blocks: list = Field(default_factory=list, description="Raw text blocks from Vision API")


class QualityCheckResult(BaseModel):
    """Result of quality validation (Rule R4)."""
    is_valid: bool = Field(..., description="Whether the recognition passed quality checks")
    reason: Optional[str] = Field(
        default=None,
        description="Why invalid: low_confidence, invalid_length, garbage_data, etc."
    )
    quality: RecognitionQuality = Field(..., description="Quality level: HIGH, MEDIUM, or LOW")


class RecognitionResponse(BaseModel):
    """API response for photo recognition."""
    status: str = Field(..., description="success or failed")
    quality: RecognitionQuality = Field(..., description="Quality level: HIGH, MEDIUM, or LOW")
    result: Optional[RecognitionResult] = Field(default=None, description="Recognition result if successful")
    message: str = Field(..., description="User-friendly message")
    needs_manual_review: bool = Field(
        ...,
        description="Whether user should manually review before saving"
    )
    photo_url: Optional[str] = Field(default=None, description="S3 URL of uploaded photo")

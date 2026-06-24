"""Vision API integration with quality checks and retry logic."""
from typing import Optional
import logging
import asyncio
import re
from src.schemas.recognition import (
    RecognitionQuality,
    QualityCheckResult,
    RecognitionResult,
)
from google.cloud import vision

logger = logging.getLogger(__name__)


class RecognitionService:
    """Service for photo recognition using Google Vision API."""

    # Confidence thresholds (Rule R4: three-level quality checks)
    CONFIDENCE_HIGH_THRESHOLD = 0.7
    CONFIDENCE_MEDIUM_THRESHOLD = 0.5

    # Text length constraints
    MIN_TEXT_LENGTH = 5
    MAX_TEXT_LENGTH = 10000

    # Garbage data patterns (regex)
    GARBAGE_PATTERNS = [
        r"^\[.*无法.*识别.*\]$",  # "[无法识别]"
        r"^\.+$",  # "......"
        r"^·+$",  # "······"
        r"^\s*$",  # Empty/whitespace
    ]

    # Garbage data keywords
    GARBAGE_KEYWORDS = [
        "无法识别",
        "[image]",
        "[chart]",
        "模糊",
    ]

    @staticmethod
    def validate_recognition_result(result: RecognitionResult) -> QualityCheckResult:
        """
        Validate recognition result (Rule R4: three-level quality check).

        Quality levels:
        - HIGH: confidence >= 0.7 → auto-save
        - MEDIUM: 0.5 <= confidence < 0.7 → mark needs_review=true
        - LOW: confidence < 0.5 → recognition failed

        Args:
            result: RecognitionResult from Vision API

        Returns:
            QualityCheckResult with is_valid, reason, and quality level
        """
        # 1. Check confidence range (Rule R2: if missing, use 0)
        confidence = float(result.confidence) if result.confidence is not None else 0.0

        if confidence < 0 or confidence > 1:
            return QualityCheckResult(
                is_valid=False,
                reason="invalid_confidence_range",
                quality=RecognitionQuality.LOW,
            )

        # 2. Check text length
        text = result.recognized_text.strip()

        if len(text) < RecognitionService.MIN_TEXT_LENGTH:
            return QualityCheckResult(
                is_valid=False,
                reason="invalid_length",
                quality=RecognitionQuality.LOW,
            )

        if len(text) > RecognitionService.MAX_TEXT_LENGTH:
            return QualityCheckResult(
                is_valid=False,
                reason="invalid_length",
                quality=RecognitionQuality.LOW,
            )

        # 3. Check for garbage data patterns
        for pattern in RecognitionService.GARBAGE_PATTERNS:
            if re.match(pattern, text):
                return QualityCheckResult(
                    is_valid=False,
                    reason="garbage_data",
                    quality=RecognitionQuality.LOW,
                )

        # 4. Check for garbage data keywords
        for keyword in RecognitionService.GARBAGE_KEYWORDS:
            if keyword in text:
                return QualityCheckResult(
                    is_valid=False,
                    reason="garbage_data",
                    quality=RecognitionQuality.LOW,
                )

        # 5. Determine quality level based on confidence
        if confidence >= RecognitionService.CONFIDENCE_HIGH_THRESHOLD:
            quality = RecognitionQuality.HIGH
            is_valid = True
        elif confidence >= RecognitionService.CONFIDENCE_MEDIUM_THRESHOLD:
            quality = RecognitionQuality.MEDIUM
            is_valid = True
        else:
            quality = RecognitionQuality.LOW
            is_valid = False
            reason = "low_confidence"

        return QualityCheckResult(
            is_valid=is_valid,
            reason=None if is_valid else reason,
            quality=quality,
        )

    @staticmethod
    async def call_vision_api(
        image_path: str, max_retries: int = 3
    ) -> Optional[RecognitionResult]:
        """
        Call Google Vision API with retry logic (Rule R8: 3 retries with exponential backoff).

        Retry intervals: 1s, 2s, 4s

        Args:
            image_path: Path to image file
            max_retries: Number of retry attempts (default 3)

        Returns:
            RecognitionResult if successful, None otherwise
        """
        client = vision.ImageAnnotatorClient()

        for attempt in range(max_retries):
            try:
                # Load image
                with open(image_path, "rb") as image_file:
                    content = image_file.read()

                image = vision.Image(content=content)

                # Call Vision API with document text detection
                response = client.document_text_detection(image=image)

                # Check for API errors
                if response.error.message:
                    logger.error(
                        f"Vision API error on attempt {attempt + 1}: {response.error.message}"
                    )
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt  # 1s, 2s, 4s
                        logger.info(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    return None

                # Check if text was detected
                texts = response.text_annotations

                if not texts:
                    logger.warning(
                        f"Vision API returned no text on attempt {attempt + 1}/{max_retries}"
                    )
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt
                        logger.info(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    return None

                # Extract full text (first annotation is the full page text)
                full_text = texts[0].description

                # Get confidence from text blocks
                confidence = 0.0
                if (
                    response.full_text_annotation
                    and response.full_text_annotation.pages
                ):
                    page = response.full_text_annotation.pages[0]
                    if page.blocks:
                        block = page.blocks[0]
                        if block.paragraphs:
                            para = block.paragraphs[0]
                            if para.words:
                                word = para.words[0]
                                if word.confidence:
                                    confidence = float(word.confidence)

                # Check for formulas and diagrams (basic heuristics)
                has_formulas = bool(
                    re.search(r"[∑∫∂∇Σ∏]|[\^_]", full_text)
                )
                has_diagrams = (
                    len(response.text_annotations) > 5
                )  # Multiple text blocks suggest diagrams

                result = RecognitionResult(
                    recognized_text=full_text,
                    confidence=confidence,
                    has_formulas=has_formulas,
                    has_diagrams=has_diagrams,
                    raw_blocks=[t.description for t in texts],
                )

                logger.info(
                    f"Vision API succeeded on attempt {attempt + 1}: confidence={confidence}"
                )
                return result

            except Exception as e:
                logger.error(
                    f"Vision API call failed on attempt {attempt + 1}/{max_retries}: {e}"
                )

                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"All {max_retries} retries exhausted for Vision API"
                    )
                    return None

        return None

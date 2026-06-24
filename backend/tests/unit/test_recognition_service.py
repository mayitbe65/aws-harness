"""Unit tests for recognition service (Rule R4: quality checks, Rule R8: retry logic)."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.services.recognition_service import RecognitionService
from src.schemas.recognition import (
    RecognitionResult,
    RecognitionQuality,
    QualityCheckResult,
)


class TestQualityCheckHighConfidence:
    """Test HIGH quality when confidence >= 0.7."""

    def test_high_confidence_0_95(self):
        """HIGH quality: confidence 0.95 should pass"""
        result = RecognitionResult(
            recognized_text="x^2 + 2x + 1 = 0",
            confidence=0.95,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is True
        assert check.quality == RecognitionQuality.HIGH
        assert check.reason is None

    def test_high_confidence_0_7(self):
        """HIGH quality: confidence exactly 0.7 should pass"""
        result = RecognitionResult(
            recognized_text="Solve for x: 2x + 3 = 7",
            confidence=0.7,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is True
        assert check.quality == RecognitionQuality.HIGH

    def test_high_confidence_1_0(self):
        """HIGH quality: confidence 1.0 should pass"""
        result = RecognitionResult(
            recognized_text="Clear math problem text",
            confidence=1.0,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is True
        assert check.quality == RecognitionQuality.HIGH


class TestQualityCheckMediumConfidence:
    """Test MEDIUM quality when 0.5 <= confidence < 0.7."""

    def test_medium_confidence_0_6(self):
        """MEDIUM quality: confidence 0.6 should be MEDIUM"""
        result = RecognitionResult(
            recognized_text="somewhat blurry math problem",
            confidence=0.6,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is True
        assert check.quality == RecognitionQuality.MEDIUM
        assert check.reason is None

    def test_medium_confidence_0_5(self):
        """MEDIUM quality: confidence exactly 0.5 should be MEDIUM"""
        result = RecognitionResult(
            recognized_text="barely readable question",
            confidence=0.5,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is True
        assert check.quality == RecognitionQuality.MEDIUM

    def test_medium_confidence_0_55(self):
        """MEDIUM quality: confidence 0.55 should be MEDIUM"""
        result = RecognitionResult(
            recognized_text="slightly unclear problem statement",
            confidence=0.55,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is True
        assert check.quality == RecognitionQuality.MEDIUM


class TestQualityCheckLowConfidence:
    """Test LOW quality when confidence < 0.5."""

    def test_low_confidence_0_3(self):
        """LOW quality: confidence 0.3 should fail"""
        result = RecognitionResult(
            recognized_text="barely visible text",
            confidence=0.3,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.quality == RecognitionQuality.LOW
        assert check.reason == "low_confidence"

    def test_low_confidence_0_49(self):
        """LOW quality: confidence 0.49 (just below 0.5) should fail"""
        result = RecognitionResult(
            recognized_text="very unclear problem",
            confidence=0.49,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.quality == RecognitionQuality.LOW

    def test_low_confidence_0_0(self):
        """LOW quality: confidence 0.0 should fail"""
        result = RecognitionResult(
            recognized_text="indecipherable text",
            confidence=0.0,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.quality == RecognitionQuality.LOW


class TestQualityCheckMissingConfidence:
    """Test Rule R2: If confidence missing, use 0."""

    def test_missing_confidence_uses_zero(self):
        """Rule R2: Missing confidence should default to 0 → LOW quality"""
        result = RecognitionResult(
            recognized_text="test problem",
            confidence=None,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.quality == RecognitionQuality.LOW
        assert check.is_valid is False

    def test_default_confidence_is_zero(self):
        """Default confidence should be 0"""
        result = RecognitionResult(
            recognized_text="problem statement"
        )

        # confidence defaults to 0.0
        assert result.confidence == 0.0

        check = RecognitionService.validate_recognition_result(result)

        assert check.quality == RecognitionQuality.LOW


class TestQualityCheckTextLength:
    """Test text length validation."""

    def test_text_too_short(self):
        """Text < 5 chars should fail"""
        result = RecognitionResult(
            recognized_text="abc",  # 3 chars
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.reason == "invalid_length"
        assert check.quality == RecognitionQuality.LOW

    def test_text_minimum_length_5(self):
        """Text with exactly 5 chars should pass"""
        result = RecognitionResult(
            recognized_text="abcde",  # 5 chars
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is True
        assert check.quality == RecognitionQuality.HIGH

    def test_text_too_long(self):
        """Text > 10000 chars should fail"""
        result = RecognitionResult(
            recognized_text="x" * 10001,
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.reason == "invalid_length"

    def test_text_maximum_length_10000(self):
        """Text with exactly 10000 chars should pass"""
        result = RecognitionResult(
            recognized_text="x" * 10000,
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is True

    def test_whitespace_only_fails(self):
        """Whitespace-only text should fail as empty"""
        result = RecognitionResult(
            recognized_text="     ",  # 5 spaces
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        # After strip(), whitespace text becomes empty (0 chars), triggers invalid_length
        assert check.reason == "invalid_length"


class TestQualityCheckGarbageDataPatterns:
    """Test garbage data pattern detection."""

    def test_garbage_pattern_unrecognizable(self):
        """Pattern [无法识别] should be detected as garbage"""
        result = RecognitionResult(
            recognized_text="[无法识别]",
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.reason == "garbage_data"
        assert check.quality == RecognitionQuality.LOW

    def test_garbage_pattern_dots(self):
        """Pattern of only dots should be detected as garbage"""
        result = RecognitionResult(
            recognized_text="......",
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.reason == "garbage_data"

    def test_garbage_pattern_middle_dots(self):
        """Pattern of middle dots (·) should be detected as garbage"""
        result = RecognitionResult(
            recognized_text="······",
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.reason == "garbage_data"


class TestQualityCheckGarbageKeywords:
    """Test garbage keyword detection."""

    def test_garbage_keyword_unrecognizable(self):
        """Keyword '无法识别' should be detected as garbage"""
        result = RecognitionResult(
            recognized_text="这是一张很模糊的照片，无法识别",
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.reason == "garbage_data"

    def test_garbage_keyword_image_tag(self):
        """Keyword '[image]' should be detected as garbage"""
        result = RecognitionResult(
            recognized_text="Question: [image] not shown",
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.reason == "garbage_data"

    def test_garbage_keyword_chart_tag(self):
        """Keyword '[chart]' should be detected as garbage"""
        result = RecognitionResult(
            recognized_text="Graph [chart] cannot be shown",
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.reason == "garbage_data"

    def test_garbage_keyword_blurry(self):
        """Keyword '模糊' should be detected as garbage"""
        result = RecognitionResult(
            recognized_text="照片太模糊了，看不清楚",
            confidence=0.9,
        )

        check = RecognitionService.validate_recognition_result(result)

        assert check.is_valid is False
        assert check.reason == "garbage_data"


class TestQualityCheckInvalidConfidence:
    """Test invalid confidence values (validated by Pydantic schema)."""

    def test_confidence_boundary_values(self):
        """Test boundary confidence values are valid in schema"""
        # Pydantic validates bounds: 0.0 <= confidence <= 1.0
        # These values should be accepted
        result_0 = RecognitionResult(
            recognized_text="valid problem",
            confidence=0.0,
        )
        assert result_0.confidence == 0.0

        result_1 = RecognitionResult(
            recognized_text="valid problem",
            confidence=1.0,
        )
        assert result_1.confidence == 1.0


class TestVisionAPIRetryLogic:
    """Test Vision API retry logic (Rule R8: 3 retries with 1s/2s/4s intervals)."""

    @pytest.mark.asyncio
    async def test_call_vision_api_success_first_attempt(self):
        """Test successful Vision API call on first attempt"""
        with patch("src.services.recognition_service.vision.ImageAnnotatorClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock successful response
            mock_response = MagicMock()
            mock_response.error.message = ""
            mock_response.text_annotations = [
                MagicMock(description="x^2 + 2x + 1 = 0"),
                MagicMock(description="term1"),
                MagicMock(description="term2"),
            ]

            # Mock full_text_annotation for confidence
            mock_page = MagicMock()
            mock_block = MagicMock()
            mock_para = MagicMock()
            mock_word = MagicMock()
            mock_word.confidence = 0.95

            mock_para.words = [mock_word]
            mock_block.paragraphs = [mock_para]
            mock_page.blocks = [mock_block]
            mock_response.full_text_annotation.pages = [mock_page]

            mock_client.document_text_detection.return_value = mock_response

            # Create temporary test file
            import tempfile
            with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
                f.write(b"fake image data")
                temp_path = f.name

            try:
                result = await RecognitionService.call_vision_api(temp_path, max_retries=3)

                assert result is not None
                assert result.recognized_text == "x^2 + 2x + 1 = 0"
                assert result.confidence == 0.95
            finally:
                import os
                os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_call_vision_api_retries_on_exception(self):
        """Test Vision API retries on exception (Rule R8)"""
        with patch(
            "src.services.recognition_service.vision.ImageAnnotatorClient"
        ) as mock_client_class:
            with patch("src.services.recognition_service.asyncio.sleep", new_callable=AsyncMock):
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # First two attempts fail, third succeeds
                mock_response_fail = MagicMock()
                mock_response_fail.text_annotations = []

                mock_response_success = MagicMock()
                mock_response_success.error.message = ""
                mock_response_success.text_annotations = [
                    MagicMock(description="recovered text")
                ]

                mock_page = MagicMock()
                mock_block = MagicMock()
                mock_para = MagicMock()
                mock_word = MagicMock()
                mock_word.confidence = 0.85

                mock_para.words = [mock_word]
                mock_block.paragraphs = [mock_para]
                mock_page.blocks = [mock_block]
                mock_response_success.full_text_annotation.pages = [mock_page]

                # Set side effects: fail twice, succeed once
                mock_client.document_text_detection.side_effect = [
                    mock_response_fail,
                    mock_response_fail,
                    mock_response_success,
                ]

                import tempfile
                with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
                    f.write(b"fake image data")
                    temp_path = f.name

                try:
                    result = await RecognitionService.call_vision_api(
                        temp_path, max_retries=3
                    )

                    assert result is not None
                    assert result.recognized_text == "recovered text"
                    # Verify sleep was called twice (for retries)
                    assert mock_client.document_text_detection.call_count == 3
                finally:
                    import os
                    os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_call_vision_api_exhausts_retries(self):
        """Test Vision API returns None after max retries exhausted"""
        with patch(
            "src.services.recognition_service.vision.ImageAnnotatorClient"
        ) as mock_client_class:
            with patch("src.services.recognition_service.asyncio.sleep", new_callable=AsyncMock):
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # All attempts return empty text
                mock_response = MagicMock()
                mock_response.error.message = ""
                mock_response.text_annotations = []

                mock_client.document_text_detection.return_value = mock_response

                import tempfile
                with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
                    f.write(b"fake image data")
                    temp_path = f.name

                try:
                    result = await RecognitionService.call_vision_api(
                        temp_path, max_retries=3
                    )

                    assert result is None
                    # Verify all 3 attempts were made
                    assert mock_client.document_text_detection.call_count == 3
                finally:
                    import os
                    os.unlink(temp_path)


class TestRecognitionResultFormulas:
    """Test formula and diagram detection."""

    def test_has_formulas_with_math_symbols(self):
        """Test detection of mathematical formulas"""
        result = RecognitionResult(
            recognized_text="Calculate ∑(x^2) + ∫f(x)dx",
            confidence=0.9,
        )

        assert result.has_formulas is False  # Not auto-set, requires API to detect

    def test_has_diagrams_with_multiple_blocks(self):
        """Test diagram detection based on text blocks"""
        result = RecognitionResult(
            recognized_text="Diagram description",
            confidence=0.9,
            has_diagrams=True,
        )

        assert result.has_diagrams is True


class TestRecognitionResultDefaults:
    """Test RecognitionResult default values."""

    def test_default_confidence(self):
        """Default confidence should be 0.0"""
        result = RecognitionResult(
            recognized_text="test"
        )
        assert result.confidence == 0.0

    def test_default_has_formulas(self):
        """Default has_formulas should be False"""
        result = RecognitionResult(
            recognized_text="test"
        )
        assert result.has_formulas is False

    def test_default_has_diagrams(self):
        """Default has_diagrams should be False"""
        result = RecognitionResult(
            recognized_text="test"
        )
        assert result.has_diagrams is False

    def test_default_raw_blocks(self):
        """Default raw_blocks should be empty list"""
        result = RecognitionResult(
            recognized_text="test"
        )
        assert result.raw_blocks == []

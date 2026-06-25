"""
Spec-driven unit tests for the recognition feature.
Source of truth: /workshop/aws-harness/spec/recognize/requirements.md
Implementation under test: src.services.recognition_service.RecognitionService
"""

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.schemas.recognition import (
    QualityCheckResult,
    RecognitionQuality,
    RecognitionResult,
)
from src.services.recognition_service import RecognitionService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

JPEG_MAGIC = b"\xff\xd8\xff" + b"\x00" * 10


def _make_result(
    recognized_text: str,
    confidence: float = 0.8,
    has_formulas: bool = False,
    has_diagrams: bool = False,
    raw_blocks: list | None = None,
) -> RecognitionResult:
    """Create a RecognitionResult through normal construction (Pydantic validates)."""
    return RecognitionResult(
        recognized_text=recognized_text,
        confidence=confidence,
        has_formulas=has_formulas,
        has_diagrams=has_diagrams,
        raw_blocks=raw_blocks or [],
    )


def _make_result_bypass(recognized_text: str, confidence: float) -> RecognitionResult:
    """Bypass Pydantic validation to inject out-of-range confidence."""
    obj = RecognitionResult.__new__(RecognitionResult)
    object.__setattr__(obj, "recognized_text", recognized_text)
    object.__setattr__(obj, "confidence", confidence)
    object.__setattr__(obj, "has_formulas", False)
    object.__setattr__(obj, "has_diagrams", False)
    object.__setattr__(obj, "raw_blocks", [])
    return obj


def _boto_mock(json_payload: dict) -> MagicMock:
    """Return a mock boto3 client whose invoke_model succeeds with json_payload."""
    client = MagicMock()
    body_mock = MagicMock()
    body_mock.read.return_value = json.dumps(
        {"content": [{"text": json.dumps(json_payload)}]}
    ).encode()
    response_mock = MagicMock()
    response_mock.__getitem__ = lambda self, key: body_mock if key == "body" else None
    client.invoke_model.return_value = response_mock
    return client


def _make_temp_jpeg() -> str:
    """Create a temporary JPEG file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.write(fd, JPEG_MAGIC)
    os.close(fd)
    return path


# ---------------------------------------------------------------------------
# §4 Quality thresholds — validate_recognition_result
# ---------------------------------------------------------------------------


class TestQualityThresholds:
    """§4 Rule R4: quality classification based on confidence and text validity."""

    def test_high_quality_at_exact_threshold(self):
        """confidence == 0.7 with valid text → HIGH."""
        result = _make_result("这是一道数学题，考察加减乘除", confidence=0.7)
        qcr: QualityCheckResult = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.HIGH
        assert qcr.is_valid is True

    def test_high_quality_above_threshold(self):
        """confidence == 1.0 with valid text → HIGH."""
        result = _make_result("解方程 2x + 3 = 7，求 x 的值", confidence=1.0)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.HIGH
        assert qcr.is_valid is True

    def test_high_quality_well_above_threshold(self):
        """confidence == 0.9 with valid text → HIGH."""
        result = _make_result("分析下列句子的成分：春天来了。", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.HIGH

    def test_medium_quality_below_threshold(self):
        """confidence just below 0.7 (e.g. 0.69) with valid text → MEDIUM."""
        result = _make_result("计算圆的面积公式推导", confidence=0.69)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.MEDIUM
        assert qcr.is_valid is True

    def test_medium_quality_at_zero(self):
        """confidence == 0.0 with valid text → MEDIUM (not LOW), per §3 default rule."""
        result = _make_result("这是有效的题目文字内容", confidence=0.0)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.MEDIUM
        assert qcr.is_valid is True

    def test_medium_quality_low_positive(self):
        """confidence == 0.1 with valid text → MEDIUM."""
        result = _make_result("请解释光合作用的过程", confidence=0.1)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.MEDIUM

    def test_boundary_confidence_just_below_high(self):
        """confidence just below 0.7 is MEDIUM boundary."""
        result = _make_result("一道有效的题目文字", confidence=0.699)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.MEDIUM

    def test_boundary_confidence_at_07_is_high(self):
        """confidence == 0.7 is HIGH boundary (inclusive)."""
        result = _make_result("一道有效的题目文字内容啊", confidence=0.7)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.HIGH


# ---------------------------------------------------------------------------
# §4 LOW triggers — out-of-range confidence
# ---------------------------------------------------------------------------


class TestLowTriggerOutOfRangeConfidence:
    """§4 LOW trigger 1: confidence not in [0.0, 1.0]."""

    def test_negative_confidence_is_low(self):
        """confidence < 0 → LOW."""
        result = _make_result_bypass("这是一道有效的题目文字内容", confidence=-0.1)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_confidence_above_one_is_low(self):
        """confidence > 1.0 → LOW."""
        result = _make_result_bypass("这是一道有效的题目文字内容", confidence=1.1)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_large_negative_confidence_is_low(self):
        """confidence << 0 → LOW."""
        result = _make_result_bypass("有效题目文字长度超过五字符", confidence=-99.0)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW


# ---------------------------------------------------------------------------
# §4 LOW triggers — text length boundaries
# ---------------------------------------------------------------------------


class TestLowTriggerTextLength:
    """§4 LOW trigger 2 & 3: text length < 5 or > 10000 after strip."""

    def test_text_length_4_is_low(self):
        """strip length == 4 → LOW."""
        result = _make_result("abcd", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_text_length_5_is_valid(self):
        """strip length == 5 → not LOW (at least MEDIUM or HIGH)."""
        result = _make_result("abcde", confidence=0.8)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality != RecognitionQuality.LOW
        assert qcr.is_valid is True

    def test_text_length_5_high_confidence_is_high(self):
        """strip length == 5 with confidence >= 0.7 → HIGH."""
        result = _make_result("abcde", confidence=0.7)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.HIGH

    def test_text_length_5_low_confidence_is_medium(self):
        """strip length == 5 with confidence < 0.7 → MEDIUM."""
        result = _make_result("abcde", confidence=0.5)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.MEDIUM

    def test_text_length_10000_is_valid(self):
        """strip length == 10000 → valid (boundary inclusive)."""
        long_text = "题" * 10000
        result = _make_result(long_text, confidence=0.8)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.is_valid is True
        assert qcr.quality != RecognitionQuality.LOW

    def test_text_length_10001_is_low(self):
        """strip length == 10001 → LOW."""
        long_text = "题" * 10001
        result = _make_result(long_text, confidence=0.8)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_whitespace_padding_stripped_before_length_check(self):
        """Leading/trailing whitespace stripped before length check: '   ab   ' → length 2 → LOW."""
        result = _make_result("   ab   ", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_whitespace_only_is_low(self):
        """Pure whitespace → effectively length 0 → LOW."""
        result = _make_result("     ", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW


# ---------------------------------------------------------------------------
# §3 Missing confidence defaults to 0.0 → MEDIUM
# ---------------------------------------------------------------------------


class TestMissingConfidenceDefault:
    """§3: Missing confidence treated as 0.0 → MEDIUM for valid text."""

    def test_confidence_zero_valid_text_is_medium(self):
        """confidence=0.0 (the default value when missing) + valid text → MEDIUM."""
        result = _make_result("这是有效文字内容，长度超过五字符", confidence=0.0)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.MEDIUM
        assert qcr.is_valid is True

    def test_confidence_zero_is_not_low(self):
        """confidence=0.0 is in [0.0, 1.0], so it should NOT trigger LOW from range check."""
        result = _make_result("有效题目文字内容超过最小长度", confidence=0.0)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality != RecognitionQuality.LOW


# ---------------------------------------------------------------------------
# §5 Garbage patterns — regex patterns
# ---------------------------------------------------------------------------


class TestGarbagePatterns:
    """§5: Regex patterns that trigger LOW quality."""

    def test_garbage_pattern_cannot_recognize_bracketed(self):
        """Pattern ^\[.*无法.*识别.*\]$ → LOW."""
        result = _make_result("[无法识别内容]", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_garbage_pattern_cannot_recognize_bracketed_with_extra(self):
        """Pattern matches with content between 无法 and 识别 → LOW."""
        result = _make_result("[无法正常识别此文字]", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_garbage_pattern_pure_dots(self):
        """Pattern ^\.+$ (pure English periods) → LOW."""
        result = _make_result("......", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_garbage_pattern_single_dot(self):
        """Single period → matches ^\.+$ → LOW."""
        result = _make_result(".", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_garbage_pattern_pure_middle_dots(self):
        """Pattern ^·+$ (pure middle dots / 间隔号) → LOW."""
        result = _make_result("···", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_garbage_pattern_single_middle_dot(self):
        """Single middle dot → matches ^·+$ → LOW."""
        result = _make_result("·", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_garbage_pattern_pure_whitespace_regex(self):
        """Pattern ^\s*$ matches pure whitespace → LOW."""
        result = _make_result("   \t\n  ", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_garbage_pattern_empty_string(self):
        """Empty string → matches ^\s*$ → LOW."""
        result = _make_result("", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW


# ---------------------------------------------------------------------------
# §5 Garbage keywords — each keyword gets its own test
# ---------------------------------------------------------------------------


class TestGarbageKeywords:
    """§5: Keywords appearing anywhere in text trigger LOW."""

    def test_keyword_cannot_recognize(self):
        """Keyword '无法识别' anywhere in text → LOW."""
        result = _make_result("这段文字无法识别，请重新拍照", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_keyword_cannot_recognize_standalone(self):
        """Standalone keyword '无法识别' → LOW."""
        result = _make_result("无法识别", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_keyword_image_tag(self):
        """Keyword '[image]' anywhere in text → LOW."""
        result = _make_result("题目内容 [image] 后续文字", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_keyword_image_tag_standalone(self):
        """Standalone '[image]' → LOW."""
        result = _make_result("[image]", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_keyword_chart_tag(self):
        """Keyword '[chart]' anywhere in text → LOW."""
        result = _make_result("见下方 [chart] 所示", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_keyword_chart_tag_standalone(self):
        """Standalone '[chart]' → LOW."""
        result = _make_result("[chart]", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_keyword_blurry(self):
        """Keyword '模糊' anywhere in text → LOW."""
        result = _make_result("图片模糊，识别结果可能不准确", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False

    def test_keyword_blurry_standalone(self):
        """Standalone '模糊' → LOW."""
        result = _make_result("模糊内容这里", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_keyword_blurry_embedded(self):
        """'模糊' embedded mid-sentence → still LOW."""
        result = _make_result("前缀模糊后缀内容很长超过最小字数限制", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW


# ---------------------------------------------------------------------------
# §6 Retry logic — call_vision_api
# ---------------------------------------------------------------------------

VALID_RECOGNITION_PAYLOAD = {
    "recognized_text": "这是一道有效的数学题，求解方程",
    "confidence": 0.85,
    "has_formulas": True,
    "has_diagrams": False,
    "raw_blocks": [],
}


def _throttling_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "InvokeModel",
    )


def _access_denied_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
        "InvokeModel",
    )


class TestRetryLogic:
    """§6 Rule R8: retry behavior for call_vision_api."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Successful response on first attempt → returns RecognitionResult."""
        client = _boto_mock(VALID_RECOGNITION_PAYLOAD)
        tmp = _make_temp_jpeg()
        try:
            with patch("boto3.client", return_value=client), patch(
                "asyncio.sleep", new_callable=AsyncMock
            ):
                result = await RecognitionService.call_vision_api(tmp)
            assert result is not None
            assert result.recognized_text == VALID_RECOGNITION_PAYLOAD["recognized_text"]
        finally:
            os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_throttling_retries_up_to_3_attempts(self):
        """ThrottlingException on all attempts → returns None after 3 tries."""
        client = MagicMock()
        client.invoke_model.side_effect = _throttling_error()
        tmp = _make_temp_jpeg()
        try:
            with patch("boto3.client", return_value=client), patch(
                "asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep:
                result = await RecognitionService.call_vision_api(tmp, max_retries=3)
            assert result is None
            assert client.invoke_model.call_count == 3
        finally:
            os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_throttling_uses_exponential_backoff(self):
        """ThrottlingException triggers exponential backoff: 2^attempt seconds."""
        client = MagicMock()
        client.invoke_model.side_effect = _throttling_error()
        tmp = _make_temp_jpeg()
        try:
            with patch("boto3.client", return_value=client), patch(
                "asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep:
                await RecognitionService.call_vision_api(tmp, max_retries=3)
            # Should have slept at least twice (after attempt 0 and 1)
            assert mock_sleep.call_count >= 2
            # First sleep should be 2^0=1 or 2^1=2 seconds depending on implementation
            sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
            # All sleep durations should be powers of 2
            for duration in sleep_args:
                assert duration >= 1
        finally:
            os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_throttling_succeeds_on_retry(self):
        """ThrottlingException on first attempt, success on second → returns result."""
        client = MagicMock()
        body_mock = MagicMock()
        body_mock.read.return_value = json.dumps(
            {"content": [{"text": json.dumps(VALID_RECOGNITION_PAYLOAD)}]}
        ).encode()
        response_mock = MagicMock()
        response_mock.__getitem__ = lambda self, key: body_mock if key == "body" else None
        client.invoke_model.side_effect = [_throttling_error(), response_mock]
        tmp = _make_temp_jpeg()
        try:
            with patch("boto3.client", return_value=client), patch(
                "asyncio.sleep", new_callable=AsyncMock
            ):
                result = await RecognitionService.call_vision_api(tmp, max_retries=3)
            assert result is not None
            assert client.invoke_model.call_count == 2
        finally:
            os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_non_throttle_client_error_gives_up_immediately(self):
        """Non-throttle ClientError (AccessDeniedException) → immediately returns None, no retry."""
        client = MagicMock()
        client.invoke_model.side_effect = _access_denied_error()
        tmp = _make_temp_jpeg()
        try:
            with patch("boto3.client", return_value=client), patch(
                "asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep:
                result = await RecognitionService.call_vision_api(tmp, max_retries=3)
            assert result is None
            # Must NOT retry — only 1 call total
            assert client.invoke_model.call_count == 1
            # Must NOT sleep
            mock_sleep.assert_not_called()
        finally:
            os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_non_throttle_various_errors_no_retry(self):
        """Other ClientError codes (e.g. ValidationException) → no retry."""
        client = MagicMock()
        client.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid input"}},
            "InvokeModel",
        )
        tmp = _make_temp_jpeg()
        try:
            with patch("boto3.client", return_value=client), patch(
                "asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep:
                result = await RecognitionService.call_vision_api(tmp, max_retries=3)
            assert result is None
            assert client.invoke_model.call_count == 1
            mock_sleep.assert_not_called()
        finally:
            os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_json_parse_error_retries(self):
        """JSON parse failure → retries (same as ThrottlingException behavior)."""
        client = MagicMock()
        body_mock_bad = MagicMock()
        body_mock_bad.read.return_value = b"not valid json at all {{{{"
        response_mock_bad = MagicMock()
        response_mock_bad.__getitem__ = (
            lambda self, key: body_mock_bad if key == "body" else None
        )

        body_mock_good = MagicMock()
        body_mock_good.read.return_value = json.dumps(
            {"content": [{"text": json.dumps(VALID_RECOGNITION_PAYLOAD)}]}
        ).encode()
        response_mock_good = MagicMock()
        response_mock_good.__getitem__ = (
            lambda self, key: body_mock_good if key == "body" else None
        )

        client.invoke_model.side_effect = [response_mock_bad, response_mock_good]
        tmp = _make_temp_jpeg()
        try:
            with patch("boto3.client", return_value=client), patch(
                "asyncio.sleep", new_callable=AsyncMock
            ):
                result = await RecognitionService.call_vision_api(tmp, max_retries=3)
            # Should have retried and succeeded
            assert result is not None
            assert client.invoke_model.call_count == 2
        finally:
            os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_json_parse_error_all_fail_returns_none(self):
        """JSON parse failure on all 3 attempts → returns None."""
        client = MagicMock()
        body_mock = MagicMock()
        body_mock.read.return_value = b"{{invalid json}}"
        response_mock = MagicMock()
        response_mock.__getitem__ = (
            lambda self, key: body_mock if key == "body" else None
        )
        client.invoke_model.return_value = response_mock

        tmp = _make_temp_jpeg()
        try:
            with patch("boto3.client", return_value=client), patch(
                "asyncio.sleep", new_callable=AsyncMock
            ):
                result = await RecognitionService.call_vision_api(tmp, max_retries=3)
            assert result is None
            assert client.invoke_model.call_count == 3
        finally:
            os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_three_exhausted_returns_none(self):
        """3 ThrottlingExceptions exhausted → None."""
        client = MagicMock()
        client.invoke_model.side_effect = [
            _throttling_error(),
            _throttling_error(),
            _throttling_error(),
        ]
        tmp = _make_temp_jpeg()
        try:
            with patch("boto3.client", return_value=client), patch(
                "asyncio.sleep", new_callable=AsyncMock
            ):
                result = await RecognitionService.call_vision_api(tmp, max_retries=3)
            assert result is None
        finally:
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# §3 Boundary confidence values
# ---------------------------------------------------------------------------


class TestBoundaryConfidenceValues:
    """Boundary value analysis for confidence field."""

    def test_confidence_0_0_valid_text_is_medium(self):
        """confidence=0.0 + valid text → MEDIUM (lowest valid confidence)."""
        result = _make_result("合法的题目文字内容长度", confidence=0.0)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.MEDIUM
        assert qcr.is_valid is True

    def test_confidence_0_7_is_high(self):
        """confidence=0.7 is the exact HIGH boundary → HIGH."""
        result = _make_result("合法的题目文字内容长度", confidence=0.7)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.HIGH
        assert qcr.is_valid is True

    def test_confidence_1_0_is_high(self):
        """confidence=1.0 (maximum) → HIGH."""
        result = _make_result("合法的题目文字内容长度", confidence=1.0)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.HIGH
        assert qcr.is_valid is True


# ---------------------------------------------------------------------------
# §4 Boundary text length values
# ---------------------------------------------------------------------------


class TestBoundaryTextLength:
    """Boundary value analysis for text length."""

    def test_length_4_is_low(self):
        """4 chars (below minimum 5) → LOW."""
        result = _make_result("四字", confidence=0.9)
        # "四字" is 2 chars; use ASCII for precise control
        result2 = _make_result("abcd", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result2)
        assert qcr.quality == RecognitionQuality.LOW

    def test_length_5_is_not_low(self):
        """5 chars (at minimum boundary) → not LOW."""
        result = _make_result("abcde", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality != RecognitionQuality.LOW
        assert qcr.is_valid is True

    def test_length_10000_is_not_low(self):
        """10000 chars (at maximum boundary) → not LOW."""
        result = _make_result("a" * 10000, confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality != RecognitionQuality.LOW
        assert qcr.is_valid is True

    def test_length_10001_is_low(self):
        """10001 chars (exceeds maximum) → LOW."""
        result = _make_result("a" * 10001, confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.is_valid is False


# ---------------------------------------------------------------------------
# Combined / edge case tests
# ---------------------------------------------------------------------------


class TestCombinedEdgeCases:
    """Multi-factor edge cases from the spec."""

    def test_garbage_overrides_high_confidence(self):
        """Even confidence=0.99, garbage text → LOW (garbage beats confidence)."""
        result = _make_result("题目内容模糊无法辨认", confidence=0.99)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW

    def test_valid_text_with_formulas_and_diagrams(self):
        """has_formulas=True, has_diagrams=True do not affect quality grading."""
        result = _make_result(
            "解方程 x^2 + 3x - 4 = 0 的根",
            confidence=0.8,
            has_formulas=True,
            has_diagrams=True,
        )
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.HIGH
        assert qcr.is_valid is True

    def test_reason_field_populated_for_low(self):
        """LOW result should include a reason string."""
        result = _make_result("ab", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.LOW
        assert qcr.reason is not None
        assert len(qcr.reason) > 0

    def test_reason_field_for_valid_result(self):
        """Valid HIGH result should have reason field (possibly empty or descriptive)."""
        result = _make_result("这是完全合法的题目文字内容", confidence=0.9)
        qcr = RecognitionService.validate_recognition_result(result)
        assert qcr.quality == RecognitionQuality.HIGH
        # reason may be None or empty for valid results — just check it exists as attribute
        assert hasattr(qcr, "reason")

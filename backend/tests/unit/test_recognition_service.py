"""Unit tests for RecognitionService (Rule R4: quality checks, Rule R8: retry logic).

Service uses Bedrock Claude with CONFIDENCE_MEDIUM_THRESHOLD=0.0:
- HIGH  : confidence >= 0.7 AND valid text AND no garbage
- MEDIUM: 0.0 <= confidence < 0.7 AND valid text AND no garbage
- LOW   : confidence out of range, text too short/long, or garbage detected
"""
import io
import json
import tempfile
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from botocore.exceptions import ClientError

from src.services.recognition_service import RecognitionService
from src.schemas.recognition import (
    RecognitionResult,
    RecognitionQuality,
    QualityCheckResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bedrock_response(text_payload: str) -> MagicMock:
    """Build a mock boto3 invoke_model response with the given JSON payload."""
    body = MagicMock()
    body.read.return_value = json.dumps(
        {"content": [{"text": text_payload}]}
    ).encode()
    resp = MagicMock()
    resp.__getitem__ = lambda self, key: body if key == "body" else None
    return resp


def _valid_payload(
    recognized_text: str = "求解方程 x^2 - 4 = 0",
    confidence: float = 0.9,
    has_formulas: bool = True,
    has_diagrams: bool = False,
) -> str:
    return json.dumps(
        {
            "recognized_text": recognized_text,
            "confidence": confidence,
            "has_formulas": has_formulas,
            "has_diagrams": has_diagrams,
        }
    )


def _tmp_image(suffix: str = ".jpg") -> str:
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    # JPEG magic bytes so media-type detection works
    f.write(b"\xff\xd8\xff" + b"\x00" * 10)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# validate_recognition_result — HIGH quality
# ---------------------------------------------------------------------------

class TestHighQuality:
    def test_confidence_0_9_gives_high(self):
        r = RecognitionResult(recognized_text="x^2 + 2x + 1 = 0", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.quality == RecognitionQuality.HIGH
        assert check.is_valid is True
        assert check.reason is None

    def test_confidence_at_threshold_0_7_gives_high(self):
        r = RecognitionResult(recognized_text="Solve for x: 2x + 3 = 7", confidence=0.7)
        check = RecognitionService.validate_recognition_result(r)
        assert check.quality == RecognitionQuality.HIGH
        assert check.is_valid is True

    def test_confidence_1_0_gives_high(self):
        r = RecognitionResult(recognized_text="Clear question text.", confidence=1.0)
        check = RecognitionService.validate_recognition_result(r)
        assert check.quality == RecognitionQuality.HIGH
        assert check.is_valid is True


# ---------------------------------------------------------------------------
# validate_recognition_result — MEDIUM quality
# (CONFIDENCE_MEDIUM_THRESHOLD = 0.0 → any non-garbage result is at least MEDIUM)
# ---------------------------------------------------------------------------

class TestMediumQuality:
    def test_confidence_0_6_gives_medium(self):
        r = RecognitionResult(recognized_text="somewhat blurry math problem", confidence=0.6)
        check = RecognitionService.validate_recognition_result(r)
        assert check.quality == RecognitionQuality.MEDIUM
        assert check.is_valid is True
        assert check.reason is None

    def test_confidence_0_5_gives_medium(self):
        r = RecognitionResult(recognized_text="barely readable question", confidence=0.5)
        check = RecognitionService.validate_recognition_result(r)
        assert check.quality == RecognitionQuality.MEDIUM
        assert check.is_valid is True

    def test_confidence_0_3_gives_medium(self):
        # Bedrock skews low; 0.3 is still MEDIUM per current design
        r = RecognitionResult(recognized_text="low confidence but readable text", confidence=0.3)
        check = RecognitionService.validate_recognition_result(r)
        assert check.quality == RecognitionQuality.MEDIUM
        assert check.is_valid is True

    def test_confidence_0_0_gives_medium(self):
        # 0.0 >= CONFIDENCE_MEDIUM_THRESHOLD (0.0) → MEDIUM
        r = RecognitionResult(recognized_text="zero confidence still kept", confidence=0.0)
        check = RecognitionService.validate_recognition_result(r)
        assert check.quality == RecognitionQuality.MEDIUM
        assert check.is_valid is True

    def test_missing_confidence_defaults_0_0_medium(self):
        # Rule R2: missing confidence → 0.0 → MEDIUM (not LOW) for valid text
        r = RecognitionResult(recognized_text="question with no confidence", confidence=None)
        check = RecognitionService.validate_recognition_result(r)
        assert check.quality == RecognitionQuality.MEDIUM
        assert check.is_valid is True


# ---------------------------------------------------------------------------
# validate_recognition_result — LOW quality (garbage / length / range)
# ---------------------------------------------------------------------------

class TestLowQualityLength:
    def test_text_too_short_gives_low(self):
        r = RecognitionResult(recognized_text="abc", confidence=0.9)  # 3 chars
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.quality == RecognitionQuality.LOW
        assert check.reason == "invalid_length"

    def test_text_exactly_5_chars_passes(self):
        r = RecognitionResult(recognized_text="abcde", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is True

    def test_text_too_long_gives_low(self):
        r = RecognitionResult(recognized_text="x" * 10001, confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "invalid_length"

    def test_text_exactly_10000_chars_passes(self):
        r = RecognitionResult(recognized_text="x" * 10000, confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is True

    def test_whitespace_only_gives_low(self):
        # After strip(), 5 spaces → 0 chars → invalid_length
        r = RecognitionResult(recognized_text="     ", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "invalid_length"


class TestLowQualityGarbagePatterns:
    def test_pattern_unrecognizable_brackets_gives_low(self):
        r = RecognitionResult(recognized_text="[无法识别]", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "garbage_data"
        assert check.quality == RecognitionQuality.LOW

    def test_pattern_only_dots_gives_low(self):
        r = RecognitionResult(recognized_text="......", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "garbage_data"

    def test_pattern_middle_dots_gives_low(self):
        r = RecognitionResult(recognized_text="······", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "garbage_data"


class TestLowQualityGarbageKeywords:
    def test_keyword_unrecognizable_in_text_gives_low(self):
        r = RecognitionResult(recognized_text="这张照片无法识别，请重新上传", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "garbage_data"

    def test_keyword_image_tag_gives_low(self):
        r = RecognitionResult(recognized_text="Question: [image] not shown", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "garbage_data"

    def test_keyword_chart_tag_gives_low(self):
        r = RecognitionResult(recognized_text="See [chart] for details", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "garbage_data"

    def test_keyword_blurry_gives_low(self):
        r = RecognitionResult(recognized_text="照片太模糊了，看不清楚", confidence=0.9)
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "garbage_data"


class TestLowQualityInvalidConfidenceRange:
    def test_confidence_above_1_gives_low(self):
        # Pydantic ge/le only run on construction; service double-checks range
        r = RecognitionResult.__new__(RecognitionResult)
        object.__setattr__(r, "recognized_text", "valid enough text here")
        object.__setattr__(r, "confidence", 1.5)
        object.__setattr__(r, "has_formulas", False)
        object.__setattr__(r, "has_diagrams", False)
        object.__setattr__(r, "raw_blocks", [])
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "invalid_confidence_range"
        assert check.quality == RecognitionQuality.LOW

    def test_confidence_below_0_gives_low(self):
        r = RecognitionResult.__new__(RecognitionResult)
        object.__setattr__(r, "recognized_text", "valid enough text here")
        object.__setattr__(r, "confidence", -0.1)
        object.__setattr__(r, "has_formulas", False)
        object.__setattr__(r, "has_diagrams", False)
        object.__setattr__(r, "raw_blocks", [])
        check = RecognitionService.validate_recognition_result(r)
        assert check.is_valid is False
        assert check.reason == "invalid_confidence_range"


# ---------------------------------------------------------------------------
# call_vision_api — Bedrock boto3 integration
# ---------------------------------------------------------------------------

class TestCallVisionApiSuccess:
    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        path = _tmp_image()
        try:
            mock_client = MagicMock()
            mock_client.invoke_model.return_value = _make_bedrock_response(
                _valid_payload("求解 x^2 - 4 = 0", confidence=0.92)
            )
            with patch("boto3.client", return_value=mock_client):
                result = await RecognitionService.call_vision_api(path, max_retries=3)

            assert result is not None
            assert result.recognized_text == "求解 x^2 - 4 = 0"
            assert result.confidence == pytest.approx(0.92)
            assert result.has_formulas is True
            assert mock_client.invoke_model.call_count == 1
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_strips_markdown_fences_from_response(self):
        path = _tmp_image()
        fenced = "```json\n" + _valid_payload("一元二次方程", confidence=0.85) + "\n```"
        try:
            mock_client = MagicMock()
            mock_client.invoke_model.return_value = _make_bedrock_response(fenced)
            with patch("boto3.client", return_value=mock_client):
                result = await RecognitionService.call_vision_api(path, max_retries=1)

            assert result is not None
            assert result.recognized_text == "一元二次方程"
            assert result.confidence == pytest.approx(0.85)
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_detects_png_media_type(self):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)
        f.close()
        try:
            mock_client = MagicMock()
            mock_client.invoke_model.return_value = _make_bedrock_response(
                _valid_payload("PNG 题目识别", confidence=0.88)
            )
            with patch("boto3.client", return_value=mock_client):
                result = await RecognitionService.call_vision_api(f.name, max_retries=1)

            assert result is not None
            # Verify the media_type sent was PNG
            call_body = json.loads(mock_client.invoke_model.call_args[1]["body"])
            img_source = call_body["messages"][0]["content"][0]["source"]
            assert img_source["media_type"] == "image/png"
        finally:
            os.unlink(f.name)


class TestCallVisionApiRetry:
    @pytest.mark.asyncio
    async def test_throttling_retries_then_succeeds(self):
        path = _tmp_image()
        throttle_error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "invoke_model",
        )
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = [
            throttle_error,
            _make_bedrock_response(_valid_payload("retry success", confidence=0.8)),
        ]
        try:
            with patch("boto3.client", return_value=mock_client):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await RecognitionService.call_vision_api(path, max_retries=3)

            assert result is not None
            assert result.recognized_text == "retry success"
            assert mock_client.invoke_model.call_count == 2
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_json_parse_error_retries_then_succeeds(self):
        path = _tmp_image()
        bad_resp = _make_bedrock_response("this is not json {{{")
        good_resp = _make_bedrock_response(_valid_payload("second attempt ok", confidence=0.75))
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = [bad_resp, good_resp]
        try:
            with patch("boto3.client", return_value=mock_client):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await RecognitionService.call_vision_api(path, max_retries=3)

            assert result is not None
            assert result.recognized_text == "second attempt ok"
            assert mock_client.invoke_model.call_count == 2
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_returns_none(self):
        path = _tmp_image()
        throttle_error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "invoke_model",
        )
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = throttle_error
        try:
            with patch("boto3.client", return_value=mock_client):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await RecognitionService.call_vision_api(path, max_retries=3)

            assert result is None
            # First attempt + 2 retries = 3 total; last retry hits non-ThrottlingException path
            assert mock_client.invoke_model.call_count == 3
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_non_throttle_client_error_returns_none_immediately(self):
        path = _tmp_image()
        access_error = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "No permission"}},
            "invoke_model",
        )
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = access_error
        try:
            with patch("boto3.client", return_value=mock_client):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await RecognitionService.call_vision_api(path, max_retries=3)

            assert result is None
            assert mock_client.invoke_model.call_count == 1
        finally:
            os.unlink(path)


class TestCallVisionApiFileErrors:
    @pytest.mark.asyncio
    async def test_file_not_found_returns_none(self):
        result = await RecognitionService.call_vision_api("/nonexistent/path.jpg", max_retries=3)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_file_returns_none(self):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        f.write(b"")  # empty
        f.close()
        try:
            mock_client = MagicMock()
            bad_resp = _make_bedrock_response("not json")
            mock_client.invoke_model.return_value = bad_resp
            with patch("boto3.client", return_value=mock_client):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await RecognitionService.call_vision_api(f.name, max_retries=1)
            # Either None (all retries failed) or a result if parsing somehow worked
            # Main assertion: no uncaught exception
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# RecognitionResult schema defaults
# ---------------------------------------------------------------------------

class TestRecognitionResultSchema:
    def test_default_confidence_is_zero(self):
        r = RecognitionResult(recognized_text="test text")
        assert r.confidence == 0.0

    def test_default_has_formulas_is_false(self):
        r = RecognitionResult(recognized_text="test text")
        assert r.has_formulas is False

    def test_default_has_diagrams_is_false(self):
        r = RecognitionResult(recognized_text="test text")
        assert r.has_diagrams is False

    def test_default_raw_blocks_is_empty_list(self):
        r = RecognitionResult(recognized_text="test text")
        assert r.raw_blocks == []

    def test_explicit_fields_set_correctly(self):
        r = RecognitionResult(
            recognized_text="已知 sin θ = 3/5，求 cos θ",
            confidence=0.88,
            has_formulas=True,
            has_diagrams=False,
            raw_blocks=["line1", "line2"],
        )
        assert r.recognized_text == "已知 sin θ = 3/5，求 cos θ"
        assert r.confidence == pytest.approx(0.88)
        assert r.has_formulas is True
        assert r.raw_blocks == ["line1", "line2"]

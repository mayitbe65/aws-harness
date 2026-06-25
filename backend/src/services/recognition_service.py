"""Vision recognition via AWS Bedrock Claude (replaces Google Vision API)."""
import base64
import json
import logging
import asyncio
import re
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from src.config import settings
from src.schemas.recognition import (
    RecognitionQuality,
    QualityCheckResult,
    RecognitionResult,
)

logger = logging.getLogger(__name__)

RECOGNITION_PROMPT = """请识别这张图片中的题目内容。

要求：
1. 提取完整的题目文字，包括题干、选项、已有的答案或解析
2. 保留数学公式的原始格式（如分数、根号、上下标等）
3. 如果有图表或示意图，描述其内容
4. 返回 JSON 格式：
{
  "recognized_text": "完整题目文字",
  "has_formulas": true/false,
  "has_diagrams": true/false,
  "confidence": 0.0-1.0
}

confidence 评估标准：
- 0.9+：图片清晰，文字完整可读
- 0.7-0.9：图片基本清晰，少量文字模糊
- 0.5-0.7：图片较模糊，部分内容需推断
- <0.5：图片严重模糊或内容无法识别

只返回 JSON，不要其他说明文字。"""


class RecognitionService:
    CONFIDENCE_HIGH_THRESHOLD = 0.7
    # Bedrock LLM self-reported confidence skews low for Chinese math images;
    # any non-garbage result is treated as at least MEDIUM (needs_review=True).
    CONFIDENCE_MEDIUM_THRESHOLD = 0.0
    MIN_TEXT_LENGTH = 5
    MAX_TEXT_LENGTH = 10000

    GARBAGE_PATTERNS = [
        r"^\[.*无法.*识别.*\]$",
        r"^\.+$",
        r"^·+$",
        r"^\s*$",
    ]
    GARBAGE_KEYWORDS = ["无法识别", "[image]", "[chart]", "模糊"]

    @staticmethod
    def validate_recognition_result(result: RecognitionResult) -> QualityCheckResult:
        confidence = float(result.confidence) if result.confidence is not None else 0.0

        if confidence < 0 or confidence > 1:
            return QualityCheckResult(
                is_valid=False,
                reason="invalid_confidence_range",
                quality=RecognitionQuality.LOW,
            )

        text = result.recognized_text.strip()

        if len(text) < RecognitionService.MIN_TEXT_LENGTH:
            return QualityCheckResult(
                is_valid=False, reason="invalid_length", quality=RecognitionQuality.LOW
            )

        if len(text) > RecognitionService.MAX_TEXT_LENGTH:
            return QualityCheckResult(
                is_valid=False, reason="invalid_length", quality=RecognitionQuality.LOW
            )

        for pattern in RecognitionService.GARBAGE_PATTERNS:
            if re.match(pattern, text):
                return QualityCheckResult(
                    is_valid=False,
                    reason="garbage_data",
                    quality=RecognitionQuality.LOW,
                )

        for keyword in RecognitionService.GARBAGE_KEYWORDS:
            if keyword in text:
                return QualityCheckResult(
                    is_valid=False,
                    reason="garbage_data",
                    quality=RecognitionQuality.LOW,
                )

        if confidence >= RecognitionService.CONFIDENCE_HIGH_THRESHOLD:
            quality = RecognitionQuality.HIGH
            is_valid = True
            reason = None
        elif confidence >= RecognitionService.CONFIDENCE_MEDIUM_THRESHOLD:
            quality = RecognitionQuality.MEDIUM
            is_valid = True
            reason = None
        else:
            quality = RecognitionQuality.LOW
            is_valid = False
            reason = "low_confidence"

        return QualityCheckResult(is_valid=is_valid, reason=reason, quality=quality)

    @staticmethod
    async def call_vision_api(
        image_path: str, max_retries: int = 3
    ) -> Optional[RecognitionResult]:
        """Call Bedrock Claude to recognize question image."""
        # Read and encode image
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
        except OSError as e:
            logger.error(f"Failed to read image file {image_path}: {e}")
            return None

        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        # Detect media type from file header
        if image_bytes[:3] == b"\xff\xd8\xff":
            media_type = "image/jpeg"
        elif image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            media_type = "image/png"
        elif image_bytes[:4] == b"GIF8":
            media_type = "image/gif"
        else:
            media_type = "image/jpeg"  # fallback

        client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": RECOGNITION_PROMPT},
                    ],
                }
            ],
        }

        for attempt in range(max_retries):
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.invoke_model(
                        modelId=settings.BEDROCK_MODEL_ID,
                        body=json.dumps(request_body),
                    ),
                )

                response_body = json.loads(response["body"].read())
                raw_text = response_body["content"][0]["text"].strip()

                # Strip markdown code fences if present
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
                    raw_text = re.sub(r"\n?```$", "", raw_text)

                parsed = json.loads(raw_text)

                result = RecognitionResult(
                    recognized_text=parsed.get("recognized_text", ""),
                    confidence=float(parsed.get("confidence", 0.0)),
                    has_formulas=bool(parsed.get("has_formulas", False)),
                    has_diagrams=bool(parsed.get("has_diagrams", False)),
                    raw_blocks=[parsed.get("recognized_text", "")],
                )

                logger.info(
                    f"Bedrock recognition succeeded on attempt {attempt + 1}: "
                    f"confidence={result.confidence}"
                )
                return result

            except ClientError as e:
                code = e.response["Error"]["Code"]
                logger.error(f"Bedrock API error on attempt {attempt + 1}: {code} - {e}")
                if code == "ThrottlingException" and attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Throttled, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    return None

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse Bedrock response on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    return None

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    return None

        return None

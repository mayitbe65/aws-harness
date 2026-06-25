"""Export service for generating PDF/HTML from question snapshots.

Rule R9: Snapshot mechanism freezes question data at export time.
Rule R5: Transaction protection for snapshot creation and PDF generation.
Rule R1: User isolation enforced in all queries.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.models.question import Question
from src.models.snapshot import Snapshot
from src.models.user import GUID
from uuid import uuid4, UUID
import json
import logging

logger = logging.getLogger(__name__)


class ExportService:
    """PDF/HTML export service with snapshot mechanism (Rule R9, R5)."""

    @staticmethod
    async def create_snapshot(
        db: AsyncSession,
        user_id: str,
        question_ids: List[str],
        format: str,
        group_by: str,
        include_answers: bool,
    ) -> Snapshot:
        """Create snapshot with frozen question data (Rule R9, R5).

        Creates a snapshot at export time that freezes question data,
        preventing mid-export modifications. Uses transaction to ensure
        consistency (Rule R5).

        Args:
            db: Database session
            user_id: User ID (Rule R1 - isolation)
            question_ids: List of question IDs to export
            format: Export format ("pdf" or "html")
            group_by: Grouping strategy ("subject", "difficulty", or "none")
            include_answers: Whether to include answer explanations

        Returns:
            Snapshot object with frozen data

        Raises:
            ValueError: If no questions found
        """
        try:
            async with db.begin():
                # Validate question_ids - keep as strings for SQLAlchemy GUID compatibility
                validated_ids = []
                try:
                    for q_id in question_ids:
                        # Validate it's a valid UUID format
                        UUID(q_id)
                        validated_ids.append(q_id.replace("-", ""))
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid question ID format: {e}")

                # Fetch questions (Rule R5: in transaction, Rule R1: user isolation)
                stmt = select(Question).where(
                    and_(
                        Question.question_id.in_(validated_ids),
                        Question.user_id == user_id,  # Rule R1: isolation
                    )
                )

                result = await db.execute(stmt)
                questions = result.scalars().all()

                if not questions:
                    raise ValueError(
                        f"No questions found for user {user_id}"
                    )

                # Validate all requested questions were found
                found_ids = {str(q.question_id) for q in questions}
                requested_ids = set(question_ids)

                missing_ids = requested_ids - found_ids
                if missing_ids:
                    logger.warning(
                        f"Missing questions for snapshot: {missing_ids}"
                    )

                # Freeze data at snapshot time (Rule R9)
                frozen_data = {
                    "questions": [
                        ExportService._serialize_question(q)
                        for q in questions
                    ],
                    "metadata": {
                        "user_id": str(user_id),
                        "frozen_at": datetime.now(timezone.utc).isoformat(),
                        "total_questions": len(questions),
                        "format": format,
                        "group_by": group_by,
                        "include_answers": include_answers,
                    }
                }

                # Create snapshot (Rule R9: data is frozen here)
                snapshot = Snapshot(
                    snapshot_id=str(uuid4()),
                    user_id=user_id,
                    question_ids=",".join([str(q.question_id) for q in questions]),
                    format=format,
                    group_by=group_by,
                    include_answers="true" if include_answers else "false",
                    snapshot_data=json.dumps(frozen_data, default=str),
                    status="pending",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                )

                db.add(snapshot)
                await db.flush()

                snapshot.snapshot_id = UUID(snapshot.snapshot_id)

                logger.info(
                    f"Created snapshot {snapshot.snapshot_id} with "
                    f"{len(questions)} frozen questions for user {user_id}"
                )
                return snapshot

        except ValueError as e:
            logger.warning(f"Snapshot creation validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating snapshot: {e}")
            raise

    @staticmethod
    async def generate_pdf_content(
        snapshot: Snapshot,
    ) -> str:
        """Generate HTML/PDF content from snapshot (Rule R9).

        Uses frozen data from snapshot to generate document content.
        The frozen data prevents modifications that occurred after
        snapshot creation from affecting the export.

        Args:
            snapshot: Snapshot object with frozen data

        Returns:
            HTML string that can be rendered or converted to PDF

        Raises:
            ValueError: If snapshot data is malformed
        """
        try:
            # Parse frozen data (Rule R9: this is the authoritative data)
            data = json.loads(snapshot.snapshot_data)
            questions = data["questions"]
            metadata = data["metadata"]

            # Generate HTML content
            html_content = ExportService._generate_html(
                questions=questions,
                metadata=metadata,
                group_by=snapshot.group_by,
                include_answers=snapshot.include_answers == "true",
            )

            logger.info(
                f"Generated {snapshot.format} content for snapshot "
                f"{snapshot.snapshot_id} from frozen data"
            )
            return html_content

        except json.JSONDecodeError as e:
            logger.error(f"Malformed snapshot data JSON: {e}")
            raise ValueError(f"Malformed snapshot data: {e}")
        except Exception as e:
            logger.error(f"Error generating PDF content: {e}")
            raise

    @staticmethod
    async def get_snapshot_status(
        db: AsyncSession,
        snapshot_id: str,
        user_id: str,
    ) -> Optional[Snapshot]:
        """Get snapshot status (Rule R1 - user isolation).

        Args:
            db: Database session
            snapshot_id: Snapshot ID
            user_id: User ID (for isolation)

        Returns:
            Snapshot object or None if not found
        """
        stmt = select(Snapshot).where(
            and_(
                Snapshot.snapshot_id == snapshot_id,
                Snapshot.user_id == user_id,  # Rule R1: isolation
            )
        )

        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def list_snapshots(
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[Snapshot], int]:
        """List user's past exports (Rule R1 - user isolation).

        Args:
            db: Database session
            user_id: User ID (for isolation)
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (snapshots list, total count)
        """
        # Get total count
        count_stmt = select(Snapshot).where(
            Snapshot.user_id == user_id  # Rule R1: isolation
        )
        count_result = await db.execute(count_stmt)
        total = len(count_result.scalars().all())

        # Get paginated results
        offset = (page - 1) * page_size
        stmt = (
            select(Snapshot)
            .where(Snapshot.user_id == user_id)  # Rule R1: isolation
            .order_by(Snapshot.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        snapshots = result.scalars().all()

        return snapshots, total

    @staticmethod
    async def cleanup_expired_snapshots(
        db: AsyncSession,
    ) -> int:
        """Delete expired snapshots (called periodically).

        Rule R5: Cleanup uses transaction for consistency.

        Args:
            db: Database session

        Returns:
            Number of snapshots deleted
        """
        try:
            async with db.begin():
                # Get expired snapshots
                stmt = select(Snapshot).where(
                    Snapshot.expires_at <= datetime.now(timezone.utc)
                )

                result = await db.execute(stmt)
                expired = result.scalars().all()

                # Delete each one
                for snapshot in expired:
                    await db.delete(snapshot)

                logger.info(
                    f"Cleaned up {len(expired)} expired snapshots"
                )
                return len(expired)

        except Exception as e:
            logger.error(f"Error cleaning up snapshots: {e}")
            raise

    @staticmethod
    async def mark_snapshot_completed(
        db: AsyncSession,
        snapshot_id: str,
        file_url: str,
    ) -> None:
        """Mark snapshot as completed and store file URL.

        Args:
            db: Database session
            snapshot_id: Snapshot ID
            file_url: URL where PDF was stored

        Raises:
            ValueError: If snapshot not found
        """
        try:
            async with db.begin():
                stmt = select(Snapshot).where(
                    Snapshot.snapshot_id == snapshot_id
                )
                result = await db.execute(stmt)
                snapshot = result.scalars().first()

                if not snapshot:
                    raise ValueError(f"Snapshot {snapshot_id} not found")

                snapshot.status = "completed"
                snapshot.file_url = file_url
                snapshot.completed_at = datetime.now(timezone.utc)

                await db.flush()

                logger.info(
                    f"Marked snapshot {snapshot_id} as completed"
                )

        except ValueError as e:
            logger.warning(str(e))
            raise
        except Exception as e:
            logger.error(f"Error marking snapshot completed: {e}")
            raise

    @staticmethod
    async def mark_snapshot_failed(
        db: AsyncSession,
        snapshot_id: str,
        error_message: str,
    ) -> None:
        """Mark snapshot as failed with error details.

        Args:
            db: Database session
            snapshot_id: Snapshot ID
            error_message: Error description

        Raises:
            ValueError: If snapshot not found
        """
        try:
            async with db.begin():
                stmt = select(Snapshot).where(
                    Snapshot.snapshot_id == snapshot_id
                )
                result = await db.execute(stmt)
                snapshot = result.scalars().first()

                if not snapshot:
                    raise ValueError(f"Snapshot {snapshot_id} not found")

                snapshot.status = "failed"
                snapshot.error_message = error_message

                await db.flush()

                logger.warning(
                    f"Marked snapshot {snapshot_id} as failed: {error_message}"
                )

        except ValueError as e:
            logger.warning(str(e))
            raise
        except Exception as e:
            logger.error(f"Error marking snapshot failed: {e}")
            raise

    @staticmethod
    def _serialize_question(question: Question) -> Dict[str, Any]:
        """Serialize question for frozen data storage.

        Args:
            question: Question object

        Returns:
            Dictionary representation of question
        """
        return {
            "question_id": str(question.question_id),
            "photo_url": question.photo_url,
            "recognized_text": question.recognized_text,
            "confidence": question.confidence,
            "subject": question.subject,
            "difficulty": question.difficulty,
            "tags": question.tags,
            "error_count": question.error_count,
            "created_at": question.created_at.isoformat(),
        }

    @staticmethod
    def _generate_html(
        questions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        group_by: str,
        include_answers: bool,
    ) -> str:
        """Generate HTML document from frozen question data.

        Args:
            questions: List of serialized question data
            metadata: Metadata about the export
            group_by: Grouping strategy
            include_answers: Whether to include answers

        Returns:
            HTML string
        """
        # Start HTML document
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>错题宝 - 题目汇总</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
        }

        .header {
            text-align: center;
            border-bottom: 2px solid #0066cc;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        .header h1 {
            color: #0066cc;
            font-size: 28px;
            margin-bottom: 10px;
        }

        .metadata {
            font-size: 14px;
            color: #666;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 10px;
        }

        .metadata-item {
            display: flex;
            flex-direction: column;
        }

        .metadata-label {
            font-weight: bold;
            color: #0066cc;
        }

        .section {
            margin: 30px 0;
            page-break-inside: avoid;
        }

        .section-title {
            background-color: #0066cc;
            color: white;
            padding: 12px 15px;
            margin-bottom: 20px;
            border-radius: 4px;
            font-size: 18px;
            font-weight: bold;
        }

        .question {
            margin: 20px 0;
            padding: 15px;
            border-left: 4px solid #0066cc;
            background-color: #f9f9f9;
            page-break-inside: avoid;
        }

        .question-text {
            font-size: 16px;
            font-weight: 500;
            margin-bottom: 10px;
            color: #333;
        }

        .question-meta {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            font-size: 14px;
            color: #666;
        }

        .meta-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            background-color: #e0e0e0;
        }

        .difficulty-1 { background-color: #c8e6c9; }
        .difficulty-2 { background-color: #a5d6a7; }
        .difficulty-3 { background-color: #fff9c4; }
        .difficulty-4 { background-color: #ffcc80; }
        .difficulty-5 { background-color: #ef9a9a; }

        .tags {
            margin-top: 8px;
            font-size: 13px;
        }

        .tag {
            display: inline-block;
            padding: 3px 6px;
            background-color: #e3f2fd;
            color: #0066cc;
            border-radius: 3px;
            margin-right: 5px;
            margin-bottom: 5px;
        }

        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ccc;
            font-size: 12px;
            color: #999;
        }

        @media print {
            body { background-color: white; }
            .container { box-shadow: none; }
            .section { page-break-inside: avoid; }
            .question { page-break-inside: avoid; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>错题宝 - 题目汇总</h1>
            <div class="metadata">
                <div class="metadata-item">
                    <span class="metadata-label">导出时间</span>
                    <span>""" + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + """</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">总题数</span>
                    <span>""" + str(len(questions)) + """</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">分组方式</span>
                    <span>""" + ExportService._translate_group_by(group_by) + """</span>
                </div>
            </div>
        </div>
"""

        # Group and display questions
        if group_by == "subject":
            grouped = {}
            for q in questions:
                subject = q.get("subject", "未分类")
                if subject not in grouped:
                    grouped[subject] = []
                grouped[subject].append(q)

            for subject, qs in grouped.items():
                html += f"""        <div class="section">
            <div class="section-title">📚 {subject.upper()}</div>
"""
                for q in qs:
                    html += ExportService._generate_question_html(
                        q, include_answers
                    )
                html += """        </div>
"""

        elif group_by == "difficulty":
            grouped = {}
            for q in questions:
                difficulty = q.get("difficulty", 3)
                if difficulty not in grouped:
                    grouped[difficulty] = []
                grouped[difficulty].append(q)

            difficulty_labels = {
                1: "⭐ 简单",
                2: "⭐⭐ 较简单",
                3: "⭐⭐⭐ 中等",
                4: "⭐⭐⭐⭐ 较难",
                5: "⭐⭐⭐⭐⭐ 很难",
            }

            for difficulty in sorted(grouped.keys()):
                qs = grouped[difficulty]
                label = difficulty_labels.get(difficulty, f"难度 {difficulty}")
                html += f"""        <div class="section">
            <div class="section-title">{label}</div>
"""
                for q in qs:
                    html += ExportService._generate_question_html(
                        q, include_answers
                    )
                html += """        </div>
"""

        else:  # group_by == "none"
            for q in questions:
                html += ExportService._generate_question_html(
                    q, include_answers
                )

        # Footer
        html += f"""        <div class="footer">
            <p>本文档由错题宝自动生成 | 冻结时间：{metadata['frozen_at']}</p>
            <p>此文档中的题目数据已在导出时刻冻结，不会随后续修改而变化。</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    @staticmethod
    def _generate_question_html(
        question: Dict[str, Any],
        include_answers: bool,
    ) -> str:
        """Generate HTML for a single question.

        Args:
            question: Question data dictionary
            include_answers: Whether to include answers

        Returns:
            HTML string for the question
        """
        difficulty = question.get("difficulty", 3)
        difficulty_class = f"difficulty-{difficulty}"

        html = f"""            <div class="question">
                <div class="question-text">{question.get('recognized_text', '')[:200]}</div>
                <div class="question-meta">
                    <span class="meta-badge {difficulty_class}">
                        难度: {difficulty}/5
                    </span>
                    <span class="meta-badge">错误: {question.get('error_count', 0)}次</span>
                    <span class="meta-badge">置信度: {question.get('confidence', 0):.1%}</span>
                </div>
"""

        if question.get("tags"):
            html += f"""                <div class="tags">
"""
            for tag in question["tags"].split(","):
                tag = tag.strip()
                if tag:
                    html += f"""                    <span class="tag">{tag}</span>
"""
            html += f"""                </div>
"""

        html += f"""            </div>
"""
        return html

    @staticmethod
    def _translate_group_by(group_by: str) -> str:
        """Translate group_by value to Chinese.

        Args:
            group_by: Grouping strategy

        Returns:
            Chinese translation
        """
        translations = {
            "subject": "按学科",
            "difficulty": "按难度",
            "none": "不分组",
        }
        return translations.get(group_by, group_by)

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Check if value is a valid UUID.

        Args:
            value: String to check

        Returns:
            True if valid UUID, False otherwise
        """
        try:
            uuid4(value)
            return True
        except (ValueError, AttributeError):
            return False

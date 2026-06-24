"""Unit tests for export service with snapshot mechanism.

Rule R9: Snapshot mechanism - freezes question data at export time
Rule R5: Transaction protection for snapshot creation
Rule R1: User isolation in all queries
"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import json

from sqlalchemy import select
from src.services.export_service import ExportService
from src.models.snapshot import Snapshot
from src.models.question import Question
from src.models.user import User, UserRole
from src.database.db import async_session_maker
from src.utils.security import hash_password


class TestSnapshotCreation:
    """Test snapshot creation (Rule R9)."""

    @pytest.mark.asyncio
    async def test_create_snapshot_success(self):
        """Test successful snapshot creation."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create test question
        async with async_session_maker() as session:
            question = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/test.jpg",
                recognized_text="Solve: x^2 + 2x + 1 = 0",
                confidence=0.95,
                subject="math",
                difficulty=3,
                tags="algebra,quadratic",
            )
            session.add(question)
            await session.commit()
            question_id = question.question_id

        # Create snapshot
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(question_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )

            assert snapshot.snapshot_id
            assert snapshot.user_id == user_id
            assert snapshot.status == "pending"
            assert snapshot.format == "pdf"
            assert snapshot.group_by == "subject"

            # Verify frozen data
            data = json.loads(snapshot.snapshot_data)
            assert len(data["questions"]) == 1
            assert data["questions"][0]["recognized_text"] == "Solve: x^2 + 2x + 1 = 0"
            assert data["metadata"]["frozen_at"]

    @pytest.mark.asyncio
    async def test_snapshot_data_frozen_at_creation(self):
        """Rule R9: Snapshot freezes data at creation time, not affected by later changes."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_frozen@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create question
        async with async_session_maker() as session:
            question = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/test.jpg",
                recognized_text="Original text",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            session.add(question)
            await session.commit()
            question_id = question.question_id

        # Create snapshot (freezes data at this moment)
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(question_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )
            original_data = json.loads(snapshot.snapshot_data)

        # Modify question in database
        async with async_session_maker() as session:
            stmt = select(Question).where(Question.question_id == question_id)
            result = await session.execute(stmt)
            q = result.scalars().first()
            q.recognized_text = "Modified text"
            await session.commit()

        # Verify snapshot still has original text (frozen, not affected by modification)
        modified_data = json.loads(snapshot.snapshot_data)
        assert modified_data["questions"][0]["recognized_text"] == "Original text"
        assert modified_data == original_data  # Unchanged

    @pytest.mark.asyncio
    async def test_snapshot_expires_30_days(self):
        """Test snapshot expiration after 30 days."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_expire@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create test question
        async with async_session_maker() as session:
            question = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/test.jpg",
                recognized_text="test",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            session.add(question)
            await session.commit()
            question_id = question.question_id

        # Create snapshot
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(question_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )

        # Check expiration
        now = datetime.now(timezone.utc)
        assert snapshot.expires_at > now
        # Should be approximately 30 days from now
        days_until_expiry = (snapshot.expires_at - now).days
        assert days_until_expiry >= 29 and days_until_expiry <= 30

    @pytest.mark.asyncio
    async def test_snapshot_with_multiple_questions(self):
        """Test snapshot with multiple questions."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_multi@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create multiple questions
        async with async_session_maker() as session:
            q1 = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/q1.jpg",
                recognized_text="Math problem 1",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            q2 = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/q2.jpg",
                recognized_text="Physics problem 1",
                confidence=0.90,
                subject="physics",
                difficulty=4,
            )
            q3 = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/q3.jpg",
                recognized_text="Chemistry problem 1",
                confidence=0.92,
                subject="chemistry",
                difficulty=2,
            )
            session.add_all([q1, q2, q3])
            await session.commit()
            q_ids = [str(q1.question_id), str(q2.question_id), str(q3.question_id)]

        # Create snapshot with all questions
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                q_ids,
                format="pdf",
                group_by="subject",
                include_answers=False,
            )

            data = json.loads(snapshot.snapshot_data)
            assert len(data["questions"]) == 3
            assert len(snapshot.question_ids.split(",")) == 3

    @pytest.mark.asyncio
    async def test_snapshot_user_isolation(self):
        """Rule R1: Snapshot only includes questions from specified user."""
        # Create two users
        async with async_session_maker() as session:
            user1 = User(
                user_id=uuid4(),
                email="user1@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="User 1",
            )
            user2 = User(
                user_id=uuid4(),
                email="user2@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="User 2",
            )
            session.add_all([user1, user2])
            await session.commit()
            user1_id = user1.user_id
            user2_id = user2.user_id

        # Create questions for both users
        async with async_session_maker() as session:
            q1 = Question(
                question_id=uuid4(),
                user_id=user1_id,
                photo_url="s3://bucket/q1.jpg",
                recognized_text="User 1 question",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            q2 = Question(
                question_id=uuid4(),
                user_id=user2_id,
                photo_url="s3://bucket/q2.jpg",
                recognized_text="User 2 question",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            session.add_all([q1, q2])
            await session.commit()
            q1_id = q1.question_id
            q2_id = q2.question_id

        # User 1 creates snapshot with only their question
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user1_id,
                [str(q1_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )

            data = json.loads(snapshot.snapshot_data)
            assert len(data["questions"]) == 1
            assert data["questions"][0]["recognized_text"] == "User 1 question"

        # Try to create snapshot with user2's question as user1 (should fail)
        async with async_session_maker() as session:
            with pytest.raises(ValueError):
                await ExportService.create_snapshot(
                    session,
                    user1_id,
                    [str(q2_id)],  # User2's question
                    format="pdf",
                    group_by="subject",
                    include_answers=False,
                )


class TestPDFGeneration:
    """Test PDF content generation."""

    @pytest.mark.asyncio
    async def test_generate_pdf_with_grouping_by_subject(self):
        """Test PDF generation with subject grouping."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_pdf@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create questions from different subjects
        async with async_session_maker() as session:
            q1 = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/q1.jpg",
                recognized_text="Math problem",
                confidence=0.95,
                subject="math",
                difficulty=3,
                tags="algebra,quadratic",
            )
            q2 = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/q2.jpg",
                recognized_text="Physics problem",
                confidence=0.90,
                subject="physics",
                difficulty=4,
                tags="mechanics",
            )
            session.add_all([q1, q2])
            await session.commit()
            q1_id, q2_id = q1.question_id, q2.question_id

        # Create snapshot
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(q1_id), str(q2_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )

        # Generate PDF content
        html = await ExportService.generate_pdf_content(snapshot)

        assert "错题宝" in html
        assert "Math problem" in html
        assert "Physics problem" in html
        assert "math" in html.lower() or "MATH" in html
        assert "physics" in html.lower() or "PHYSICS" in html
        assert "algebra" in html
        assert "mechanics" in html

    @pytest.mark.asyncio
    async def test_generate_pdf_with_grouping_by_difficulty(self):
        """Test PDF generation with difficulty grouping."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_diff@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create questions with different difficulties
        async with async_session_maker() as session:
            q1 = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/q1.jpg",
                recognized_text="Easy problem",
                confidence=0.95,
                subject="math",
                difficulty=1,
            )
            q2 = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/q2.jpg",
                recognized_text="Hard problem",
                confidence=0.90,
                subject="math",
                difficulty=5,
            )
            session.add_all([q1, q2])
            await session.commit()
            q1_id, q2_id = q1.question_id, q2.question_id

        # Create snapshot with difficulty grouping
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(q1_id), str(q2_id)],
                format="pdf",
                group_by="difficulty",
                include_answers=False,
            )

        # Generate PDF content
        html = await ExportService.generate_pdf_content(snapshot)

        assert "Easy problem" in html
        assert "Hard problem" in html
        assert "简单" in html or "⭐" in html

    @pytest.mark.asyncio
    async def test_generate_pdf_no_grouping(self):
        """Test PDF generation with no grouping."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_no_group@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create questions
        async with async_session_maker() as session:
            q1 = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/q1.jpg",
                recognized_text="Question 1",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            session.add(q1)
            await session.commit()
            q1_id = q1.question_id

        # Create snapshot with no grouping
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(q1_id)],
                format="pdf",
                group_by="none",
                include_answers=False,
            )

        # Generate PDF content
        html = await ExportService.generate_pdf_content(snapshot)

        assert "Question 1" in html
        assert "错题宝" in html


class TestSnapshotStatus:
    """Test snapshot status queries."""

    @pytest.mark.asyncio
    async def test_get_snapshot_status(self):
        """Test retrieving snapshot status."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_status@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create question and snapshot
        async with async_session_maker() as session:
            question = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/test.jpg",
                recognized_text="test",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            session.add(question)
            await session.commit()
            question_id = question.question_id

        # Create snapshot
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(question_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )
            snapshot_id = snapshot.snapshot_id

        # Get snapshot status
        async with async_session_maker() as session:
            status = await ExportService.get_snapshot_status(
                session,
                snapshot_id,
                user_id,
            )

            assert status is not None
            assert status.snapshot_id == snapshot_id
            assert status.user_id == user_id
            assert status.status == "pending"

    @pytest.mark.asyncio
    async def test_get_snapshot_status_wrong_user(self):
        """Rule R1: User cannot access other user's snapshot."""
        # Create two users
        async with async_session_maker() as session:
            user1 = User(
                user_id=uuid4(),
                email="user1_status@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="User 1",
            )
            user2 = User(
                user_id=uuid4(),
                email="user2_status@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="User 2",
            )
            session.add_all([user1, user2])
            await session.commit()
            user1_id = user1.user_id
            user2_id = user2.user_id

        # Create question and snapshot for user1
        async with async_session_maker() as session:
            question = Question(
                question_id=uuid4(),
                user_id=user1_id,
                photo_url="s3://bucket/test.jpg",
                recognized_text="test",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            session.add(question)
            await session.commit()
            question_id = question.question_id

        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user1_id,
                [str(question_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )
            snapshot_id = snapshot.snapshot_id

        # Try to access with different user (should return None)
        async with async_session_maker() as session:
            status = await ExportService.get_snapshot_status(
                session,
                snapshot_id,
                user2_id,  # Different user
            )

            assert status is None

    @pytest.mark.asyncio
    async def test_list_snapshots(self):
        """Test listing user's snapshots."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_list@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create multiple questions
        async with async_session_maker() as session:
            questions = []
            for i in range(3):
                q = Question(
                    question_id=uuid4(),
                    user_id=user_id,
                    photo_url=f"s3://bucket/q{i}.jpg",
                    recognized_text=f"Question {i}",
                    confidence=0.95,
                    subject="math",
                    difficulty=3,
                )
                questions.append(q)
            session.add_all(questions)
            await session.commit()
            q_ids = [str(q.question_id) for q in questions]

        # Create snapshots
        async with async_session_maker() as session:
            for q_id in q_ids:
                await ExportService.create_snapshot(
                    session,
                    user_id,
                    [q_id],
                    format="pdf",
                    group_by="subject",
                    include_answers=False,
                )

        # List snapshots
        async with async_session_maker() as session:
            snapshots, total = await ExportService.list_snapshots(
                session,
                user_id,
                page=1,
                page_size=10,
            )

            assert len(snapshots) == 3
            assert total == 3


class TestSnapshotCleanup:
    """Test snapshot cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_snapshots(self):
        """Test deletion of expired snapshots."""
        # Create test user
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_cleanup@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        # Create question
        async with async_session_maker() as session:
            question = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/test.jpg",
                recognized_text="test",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            session.add(question)
            await session.commit()
            question_id = question.question_id

        # Create snapshot
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(question_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )
            snapshot_id = snapshot.snapshot_id

        # Manually set expiration to past
        async with async_session_maker() as session:
            stmt = select(Snapshot).where(
                Snapshot.snapshot_id == snapshot_id
            )
            result = await session.execute(stmt)
            snap = result.scalars().first()
            snap.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        # Verify it exists before cleanup
        async with async_session_maker() as session:
            stmt = select(Snapshot).where(
                Snapshot.snapshot_id == snapshot_id
            )
            result = await session.execute(stmt)
            snap = result.scalars().first()
            assert snap is not None

        # Run cleanup
        async with async_session_maker() as session:
            deleted_count = await ExportService.cleanup_expired_snapshots(session)
            assert deleted_count >= 1

        # Verify it's deleted
        async with async_session_maker() as session:
            stmt = select(Snapshot).where(
                Snapshot.snapshot_id == snapshot_id
            )
            result = await session.execute(stmt)
            snap = result.scalars().first()
            assert snap is None

    @pytest.mark.asyncio
    async def test_mark_snapshot_completed(self):
        """Test marking snapshot as completed."""
        # Create test user and question
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_complete@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        async with async_session_maker() as session:
            question = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/test.jpg",
                recognized_text="test",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            session.add(question)
            await session.commit()
            question_id = question.question_id

        # Create snapshot
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(question_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )
            snapshot_id = snapshot.snapshot_id

        # Mark as completed
        async with async_session_maker() as session:
            await ExportService.mark_snapshot_completed(
                session,
                snapshot_id,
                "s3://bucket/export_123.pdf",
            )

        # Verify status
        async with async_session_maker() as session:
            stmt = select(Snapshot).where(
                Snapshot.snapshot_id == snapshot_id
            )
            result = await session.execute(stmt)
            snap = result.scalars().first()
            assert snap.status == "completed"
            assert snap.file_url == "s3://bucket/export_123.pdf"
            assert snap.completed_at is not None

    @pytest.mark.asyncio
    async def test_mark_snapshot_failed(self):
        """Test marking snapshot as failed."""
        # Create test user and question
        async with async_session_maker() as session:
            user = User(
                user_id=uuid4(),
                email="test_failed@example.com",
                password_hash=hash_password("password123"),
                role=UserRole.STUDENT,
                name="Test User",
            )
            session.add(user)
            await session.commit()
            user_id = user.user_id

        async with async_session_maker() as session:
            question = Question(
                question_id=uuid4(),
                user_id=user_id,
                photo_url="s3://bucket/test.jpg",
                recognized_text="test",
                confidence=0.95,
                subject="math",
                difficulty=3,
            )
            session.add(question)
            await session.commit()
            question_id = question.question_id

        # Create snapshot
        async with async_session_maker() as session:
            snapshot = await ExportService.create_snapshot(
                session,
                user_id,
                [str(question_id)],
                format="pdf",
                group_by="subject",
                include_answers=False,
            )
            snapshot_id = snapshot.snapshot_id

        # Mark as failed
        async with async_session_maker() as session:
            await ExportService.mark_snapshot_failed(
                session,
                snapshot_id,
                "PDF generation timeout after 30 seconds",
            )

        # Verify status
        async with async_session_maker() as session:
            stmt = select(Snapshot).where(
                Snapshot.snapshot_id == snapshot_id
            )
            result = await session.execute(stmt)
            snap = result.scalars().first()
            assert snap.status == "failed"
            assert "timeout" in snap.error_message

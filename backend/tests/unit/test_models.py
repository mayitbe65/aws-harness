"""Unit tests for Question and ReviewPlan models."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.models import Question, ReviewPlan, User, Base, GUID, UserRole


class TestQuestionModel:
    """Test cases for Question model."""

    def test_question_model_creation(self):
        """Test basic Question model creation with required fields."""
        user_id = uuid4()
        question_id = uuid4()

        question = Question(
            question_id=question_id,
            user_id=user_id,
            photo_url="https://s3.example.com/photo.jpg",
            recognized_text="x^2 + 2x + 1 = 0",
            confidence=0.95,
            subject="math",
            difficulty=3,
        )

        assert question.question_id == question_id
        assert question.user_id == user_id
        assert question.photo_url == "https://s3.example.com/photo.jpg"
        assert question.recognized_text == "x^2 + 2x + 1 = 0"
        assert question.confidence == 0.95
        assert question.subject == "math"
        assert question.difficulty == 3

    def test_question_model_defaults(self):
        """Test Question model default values through column defaults."""
        # SQLAlchemy defaults are set at SQL level, not Python instantiation
        # We verify they exist as column definitions
        needs_review_col = Question.__table__.columns["needs_review"]
        subject_col = Question.__table__.columns["subject"]
        difficulty_col = Question.__table__.columns["difficulty"]
        tags_col = Question.__table__.columns["tags"]
        error_count_col = Question.__table__.columns["error_count"]
        confidence_col = Question.__table__.columns["confidence"]

        assert needs_review_col.default.arg is False
        assert subject_col.default.arg == "math"
        assert difficulty_col.default.arg == 3
        assert tags_col.default.arg == ""
        assert error_count_col.default.arg == 1
        assert confidence_col.default.arg == 0.0

    def test_question_model_timestamps(self):
        """Test Question model has timestamp columns with defaults."""
        # Verify timestamp columns exist and have defaults configured
        created_at_col = Question.__table__.columns["created_at"]
        updated_at_col = Question.__table__.columns["updated_at"]

        assert created_at_col is not None
        assert updated_at_col is not None
        assert created_at_col.default is not None
        assert updated_at_col.default is not None

    def test_question_model_columns_count(self):
        """Test that Question model has expected number of columns."""
        columns = Question.__table__.columns
        column_names = [col.name for col in columns]

        # Verify key columns exist
        expected_columns = [
            "question_id",
            "user_id",
            "photo_url",
            "recognized_text",
            "confidence",
            "needs_review",
            "review_notes",
            "subject",
            "difficulty",
            "tags",
            "error_count",
            "last_error_time",
            "created_at",
            "updated_at",
        ]

        for expected_col in expected_columns:
            assert expected_col in column_names, f"Missing column: {expected_col}"

        # Should have at least 14 columns
        assert len(column_names) >= 14

    def test_question_model_foreign_key_to_user(self):
        """Test Question model has foreign key to User."""
        # Check that user_id column exists and is a foreign key
        user_id_col = Question.__table__.columns["user_id"]
        assert len(user_id_col.foreign_keys) > 0

        # Get the foreign key constraint
        fk = list(user_id_col.foreign_keys)[0]
        assert fk.column.table.name == "users"
        assert fk.ondelete.lower() == "cascade"

    def test_question_cascade_to_review_plans(self):
        """Test that Question cascade delete is configured for review_plans."""
        # Verify the relationship has cascade delete and delete-orphan
        review_plans_rel = Question.review_plans.property
        assert review_plans_rel.cascade.delete
        assert review_plans_rel.cascade.delete_orphan

    def test_question_indexes(self):
        """Test that Question model has proper indexes."""
        index_names = [idx.name for idx in Question.__table__.indexes]

        expected_indexes = [
            "ix_questions_user_created",
            "ix_questions_needs_review",
        ]

        for expected_idx in expected_indexes:
            assert expected_idx in index_names, f"Missing index: {expected_idx}"

    def test_question_repr(self):
        """Test Question __repr__ method."""
        user_id = uuid4()
        question_id = uuid4()

        question = Question(
            question_id=question_id,
            user_id=user_id,
            photo_url="test.jpg",
            recognized_text="test",
            subject="physics",
        )

        repr_str = repr(question)
        assert "Question" in repr_str
        assert "subject=physics" in repr_str


class TestReviewPlanModel:
    """Test cases for ReviewPlan model."""

    def test_review_plan_model_creation(self):
        """Test basic ReviewPlan model creation."""
        plan_id = uuid4()
        user_id = uuid4()
        question_id = uuid4()

        plan = ReviewPlan(
            plan_id=plan_id,
            user_id=user_id,
            question_id=question_id,
            error_count=2,
            reviewed_count=1,
            priority=0.85,
        )

        assert plan.plan_id == plan_id
        assert plan.user_id == user_id
        assert plan.question_id == question_id
        assert plan.error_count == 2
        assert plan.reviewed_count == 1
        assert plan.priority == 0.85

    def test_review_plan_model_defaults(self):
        """Test ReviewPlan model default values through column definitions."""
        # Verify column defaults at schema level
        error_count_col = ReviewPlan.__table__.columns["error_count"]
        reviewed_count_col = ReviewPlan.__table__.columns["reviewed_count"]
        priority_col = ReviewPlan.__table__.columns["priority"]
        is_mastered_col = ReviewPlan.__table__.columns["is_mastered"]

        assert error_count_col.default.arg == 0
        assert reviewed_count_col.default.arg == 0
        assert priority_col.default.arg == 0.0
        assert is_mastered_col.default.arg is False

        # Optional fields should allow NULL
        assert ReviewPlan.__table__.columns["last_error_time"].nullable
        assert ReviewPlan.__table__.columns["last_reviewed_time"].nullable
        assert ReviewPlan.__table__.columns["next_review_time"].nullable

    def test_review_plan_model_timestamps(self):
        """Test ReviewPlan model has timestamp columns with defaults."""
        # Verify timestamp columns exist and have defaults
        created_at_col = ReviewPlan.__table__.columns["created_at"]
        updated_at_col = ReviewPlan.__table__.columns["updated_at"]

        assert created_at_col is not None
        assert updated_at_col is not None
        assert created_at_col.default is not None
        assert updated_at_col.default is not None

    def test_review_plan_model_columns_count(self):
        """Test that ReviewPlan model has expected number of columns."""
        columns = ReviewPlan.__table__.columns
        column_names = [col.name for col in columns]

        # Verify key columns exist
        expected_columns = [
            "plan_id",
            "user_id",
            "question_id",
            "error_count",
            "reviewed_count",
            "last_error_time",
            "last_reviewed_time",
            "next_review_time",
            "priority",
            "is_mastered",
            "created_at",
            "updated_at",
        ]

        for expected_col in expected_columns:
            assert expected_col in column_names, f"Missing column: {expected_col}"

        # Should have at least 12 columns
        assert len(column_names) >= 12

    def test_review_plan_foreign_key_to_user(self):
        """Test ReviewPlan model has foreign key to User."""
        user_id_col = ReviewPlan.__table__.columns["user_id"]
        assert len(user_id_col.foreign_keys) > 0

        fk = list(user_id_col.foreign_keys)[0]
        assert fk.column.table.name == "users"
        assert fk.ondelete.lower() == "cascade"

    def test_review_plan_foreign_key_to_question(self):
        """Test ReviewPlan model has foreign key to Question."""
        question_id_col = ReviewPlan.__table__.columns["question_id"]
        assert len(question_id_col.foreign_keys) > 0

        fk = list(question_id_col.foreign_keys)[0]
        assert fk.column.table.name == "questions"
        assert fk.ondelete.lower() == "cascade"

    def test_review_plan_indexes(self):
        """Test that ReviewPlan model has proper indexes."""
        index_names = [idx.name for idx in ReviewPlan.__table__.indexes]

        expected_indexes = [
            "ix_review_plans_user_next_review",
            "ix_review_plans_is_mastered",
        ]

        for expected_idx in expected_indexes:
            assert expected_idx in index_names, f"Missing index: {expected_idx}"

    def test_review_plan_repr(self):
        """Test ReviewPlan __repr__ method."""
        plan_id = uuid4()
        question_id = uuid4()

        plan = ReviewPlan(
            plan_id=plan_id,
            user_id=uuid4(),
            question_id=question_id,
            priority=0.75,
        )

        repr_str = repr(plan)
        assert "ReviewPlan" in repr_str
        assert "priority=0.75" in repr_str


class TestModelRelationships:
    """Test model relationships and cascade behavior."""

    def test_question_to_review_plans_relationship(self):
        """Test bidirectional relationship between Question and ReviewPlan."""
        question = Question(
            question_id=uuid4(),
            user_id=uuid4(),
            photo_url="test.jpg",
            recognized_text="test",
        )

        # Verify relationship is defined
        assert hasattr(Question, "review_plans")
        assert hasattr(ReviewPlan, "question")

    def test_question_to_user_relationship(self):
        """Test relationship between Question and User."""
        assert hasattr(Question, "user")
        assert hasattr(User, "questions")

    def test_review_plan_to_user_relationship(self):
        """Test relationship between ReviewPlan and User."""
        assert hasattr(ReviewPlan, "user")
        assert hasattr(User, "review_plans")

    def test_cascade_delete_configuration(self):
        """Test cascade delete is properly configured."""
        # Question to ReviewPlan cascade
        question_rel = Question.review_plans.property
        assert question_rel.cascade.delete
        assert question_rel.cascade.delete_orphan

        # User to Question cascade (via foreign key)
        user_id_col = Question.__table__.columns["user_id"]
        user_fk = list(user_id_col.foreign_keys)[0]
        assert user_fk.ondelete.lower() == "cascade"

        # User to ReviewPlan cascade (via foreign key)
        user_id_col_plan = ReviewPlan.__table__.columns["user_id"]
        user_fk_plan = list(user_id_col_plan.foreign_keys)[0]
        assert user_fk_plan.ondelete.lower() == "cascade"

        # Question to ReviewPlan cascade (via foreign key)
        question_id_col = ReviewPlan.__table__.columns["question_id"]
        question_fk = list(question_id_col.foreign_keys)[0]
        assert question_fk.ondelete.lower() == "cascade"


class TestModelExports:
    """Test that models are properly exported from __init__.py."""

    def test_models_imported_from_package(self):
        """Test all models can be imported from src.models package."""
        from src.models import Question, ReviewPlan, User, Base, GUID, UserRole

        assert Question is not None
        assert ReviewPlan is not None
        assert User is not None
        assert Base is not None
        assert GUID is not None
        assert UserRole is not None

    def test_models_have_correct_tablenames(self):
        """Test models have correct table names."""
        assert Question.__tablename__ == "questions"
        assert ReviewPlan.__tablename__ == "review_plans"
        assert User.__tablename__ == "users"

    def test_models_inherit_from_base(self):
        """Test all models are SQLAlchemy ORM models."""
        # Models inherit from declarative base, checking via registry
        from sqlalchemy.orm import class_mapper

        # If a class can be mapped, it's a valid ORM model
        try:
            class_mapper(Question)
            class_mapper(ReviewPlan)
            class_mapper(User)
            assert True
        except Exception:
            assert False, "Models are not properly mapped to SQLAlchemy"

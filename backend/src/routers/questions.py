"""Question storage and management endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update, delete
from uuid import uuid4
from datetime import datetime, timezone

from src.database.db import get_db
from src.models.question import Question
from src.models.review_plan import ReviewPlan
from src.schemas.question import (
    CreateQuestionRequest,
    UpdateQuestionRequest,
    QuestionResponse,
    QuestionListResponse,
    DeleteQuestionResponse,
)
from src.routers.auth import get_current_user_from_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/questions", tags=["questions"])




def _question_to_response(question: Question) -> QuestionResponse:
    """Convert Question model to QuestionResponse schema."""
    return QuestionResponse(
        question_id=str(question.question_id),
        user_id=str(question.user_id),
        photo_url=question.photo_url,
        recognized_text=question.recognized_text,
        confidence=question.confidence,
        subject=question.subject,
        difficulty=question.difficulty,
        tags=question.tags,
        error_count=question.error_count,
        needs_review=question.needs_review,
        review_notes=question.review_notes,
        last_error_time=question.last_error_time,
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


@router.post("/create", response_model=QuestionResponse, status_code=201)
async def create_question(
    request: CreateQuestionRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """创建题目记录（从拍照识别结果）

    - Rule R1: 所有题目关联当前用户
    - Rule R4: confidence < 0.7 自动标记 needs_review=true
    - Rule R5: 事务保护 create_question + review_plan
    """
    user_id = current_user["user_id"]

    try:
        async with db.begin():
            # 创建题目
            question_id = str(uuid4())
            question = Question(
                question_id=question_id,
                user_id=user_id,
                photo_url=request.photo_url,
                recognized_text=request.recognized_text,
                confidence=request.confidence,
                subject=request.subject,
                difficulty=request.difficulty,
                tags=request.tags,
                needs_review=request.confidence < 0.7,  # Rule R4
                error_count=1,
                last_error_time=datetime.now(timezone.utc),
            )

            db.add(question)

            # 同时创建初始复习计划
            review_plan = ReviewPlan(
                plan_id=str(uuid4()),
                user_id=user_id,
                question_id=question_id,
                error_count=1,
                reviewed_count=0,
                last_error_time=datetime.now(timezone.utc),
                next_review_time=datetime.now(timezone.utc),
                priority=0.9,  # 新题目优先级高
            )

            db.add(review_plan)
            await db.flush()

        await db.refresh(question)
        logger.info(f"Created question {question_id} for user {user_id}")
        return QuestionResponse(
            question_id=str(question.question_id),
            user_id=str(question.user_id),
            photo_url=question.photo_url,
            recognized_text=question.recognized_text,
            confidence=question.confidence,
            subject=question.subject,
            difficulty=question.difficulty,
            tags=question.tags,
            error_count=question.error_count,
            needs_review=question.needs_review,
            review_notes=question.review_notes,
            last_error_time=question.last_error_time,
            created_at=question.created_at,
            updated_at=question.updated_at,
        )

    except Exception as e:
        logger.error(f"Error creating question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建题目失败")


@router.get("", response_model=QuestionListResponse)
async def list_questions(
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    needs_review_only: bool = Query(False, description="Filter: only items needing review"),
) -> QuestionListResponse:
    """获取题目列表 — 分页

    - Rule R1: 查询结果仅包含当前用户的题目
    - 支持按 needs_review 筛选
    """
    user_id = current_user["user_id"]

    try:
        # 构建查询条件
        filters = [Question.user_id == user_id]
        if needs_review_only:
            filters.append(Question.needs_review == True)

        # 计算总数
        count_stmt = select(func.count()).select_from(Question).where(and_(*filters))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 构建分页查询
        offset = (page - 1) * page_size
        stmt = (
            select(Question)
            .where(and_(*filters))
            .order_by(Question.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        questions = result.scalars().all()

        return QuestionListResponse(
            items=[_question_to_response(q) for q in questions],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    except Exception as e:
        logger.error(f"Error listing questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取题目列表失败")


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: str,
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """获取题目详情

    - Rule R1: 验证题目所有者为当前用户，否则返回 404
    """
    user_id = current_user["user_id"]

    try:
        stmt = select(Question).where(
            and_(
                Question.question_id == question_id,
                Question.user_id == user_id,  # Rule R1: 所有权验证
            )
        )

        result = await db.execute(stmt)
        question = result.scalars().first()

        if not question:
            raise HTTPException(
                status_code=404,
                detail="题目不存在",
            )

        return _question_to_response(question)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取题目失败")


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str,
    request: UpdateQuestionRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """更新题目（人工纠正识别结果）

    - Rule R1: 所有权验证
    - Rule R5: 事务保护所有更新
    """
    user_id = current_user["user_id"]

    try:
        async with db.begin():
            # First, check if question exists and belongs to user
            stmt = select(Question).where(
                and_(
                    Question.question_id == question_id,
                    Question.user_id == user_id,  # Rule R1
                )
            )

            result = await db.execute(stmt)
            question = result.scalars().first()

            if not question:
                raise HTTPException(
                    status_code=404,
                    detail="题目不存在",
                )

            # Build update values dict
            update_data = {"updated_at": datetime.now(timezone.utc)}
            if request.recognized_text is not None:
                update_data["recognized_text"] = request.recognized_text
            if request.subject is not None:
                update_data["subject"] = request.subject
            if request.difficulty is not None:
                update_data["difficulty"] = request.difficulty
            if request.tags is not None:
                update_data["tags"] = request.tags
            if request.needs_review is not None:
                update_data["needs_review"] = request.needs_review
            if request.review_notes is not None:
                update_data["review_notes"] = request.review_notes

            # Execute UPDATE with all values at once
            stmt = update(Question).where(
                Question.question_id == question_id
            ).values(**update_data)
            await db.execute(stmt)

        # Re-fetch the updated question after transaction
        # Clear the session cache to ensure we get fresh data
        db.expunge_all()
        stmt = select(Question).where(Question.question_id == question_id)
        result = await db.execute(stmt)
        updated_question = result.scalars().first()

        logger.info(f"Updated question {question_id} for user {user_id}")
        return _question_to_response(updated_question)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新题目失败")


@router.delete("/{question_id}", response_model=DeleteQuestionResponse)
async def delete_question(
    question_id: str,
    current_user: dict = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> DeleteQuestionResponse:
    """删除题目及其关联复习计划

    - Rule R1: 所有权验证
    - Rule R5: 事务保护
    - 级联删除由模型关系定义（cascade="all, delete-orphan"）
    """
    user_id = current_user["user_id"]

    try:
        async with db.begin():
            # 验证所有权
            stmt = select(Question).where(
                and_(
                    Question.question_id == question_id,
                    Question.user_id == user_id,  # Rule R1
                )
            )

            result = await db.execute(stmt)
            question = result.scalars().first()

            if not question:
                raise HTTPException(
                    status_code=404,
                    detail="题目不存在",
                )

            # 删除题目（级联删除 ReviewPlan）
            stmt = delete(Question).where(
                Question.question_id == question_id
            )
            await db.execute(stmt)

        logger.info(f"Deleted question {question_id} for user {user_id}")

        return DeleteQuestionResponse(
            status="success",
            message="题目已删除",
            deleted_question_id=question_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除题目失败")

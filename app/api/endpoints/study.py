from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.word import Word
from app.models.user_progress import UserProgress
from app.models.user_study_plan import UserStudyPlan
from app.schemas.study import (
    StudySessionResponse,
    StudySubmitRequest,
    StudySubmitResponse,
    StudyStatsResponse,
)
from app.services.sm2_algorithm import SM2Algorithm

router = APIRouter(prefix="/study", tags=["Study"])


@router.get("/session", response_model=StudySessionResponse)
async def get_study_session(
    limit: int = Query(20, ge=1, le=100),
    include_new: bool = Query(True),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取学习会话

    返回待复习的单词 + 新单词
    """
    session_id = str(uuid4())
    words_data = []

    # 1. 获取待复习的单词
    review_query = select(UserProgress, Word).join(
        Word, UserProgress.word_id == Word.id
    ).where(
        and_(
            UserProgress.user_id == current_user.id,
            UserProgress.next_review_at <= datetime.utcnow(),
            UserProgress.status < 3  # 未掌握的单词
        )
    ).order_by(UserProgress.next_review_at.asc()).limit(limit)

    review_result = await db.execute(review_query)
    review_items = review_result.all()

    for progress, word in review_items:
        words_data.append({
            "word_id": word.id,
            "spelling": word.spelling,
            "phonetic": word.phonetic,
            "definitions": word.definitions,
            "sentences": word.sentences,
            "mnemonic": word.mnemonic,
            "audio_url": word.audio_url,
            "progress": {
                "status": progress.status,
                "ease_factor": progress.ease_factor,
                "interval": progress.interval,
                "total_reviews": progress.total_reviews,
                "correct_count": progress.correct_count,
            }
        })

    # 2. 如果需要新单词且数量不足
    if include_new and len(words_data) < limit:
        remaining = limit - len(words_data)

        # 获取用户激活的学习计划
        active_plan_query = select(UserStudyPlan).where(
            and_(
                UserStudyPlan.user_id == current_user.id,
                UserStudyPlan.is_active == True
            )
        ).limit(1)

        active_plan_result = await db.execute(active_plan_query)
        active_plan = active_plan_result.scalar_one_or_none()

        if active_plan:
            # 获取该词书中用户未学习的单词
            learned_word_ids_query = select(UserProgress.word_id).where(
                UserProgress.user_id == current_user.id
            )
            learned_word_ids_result = await db.execute(learned_word_ids_query)
            learned_word_ids = [row[0] for row in learned_word_ids_result.all()]

            new_words_query = select(Word).where(
                and_(
                    Word.book_id == active_plan.book_id,
                    Word.id.notin_(learned_word_ids) if learned_word_ids else True
                )
            ).limit(remaining)

            new_words_result = await db.execute(new_words_query)
            new_words = new_words_result.scalars().all()

            for word in new_words:
                words_data.append({
                    "word_id": word.id,
                    "spelling": word.spelling,
                    "phonetic": word.phonetic,
                    "definitions": word.definitions,
                    "sentences": word.sentences,
                    "mnemonic": word.mnemonic,
                    "audio_url": word.audio_url,
                    "progress": {
                        "status": 0,
                        "ease_factor": 2.5,
                        "interval": 0,
                        "total_reviews": 0,
                        "correct_count": 0,
                    }
                })

    # 3. 统计信息
    total_due_query = select(func.count(UserProgress.id)).where(
        and_(
            UserProgress.user_id == current_user.id,
            UserProgress.next_review_at <= datetime.utcnow(),
            UserProgress.status < 3
        )
    )
    total_due_result = await db.execute(total_due_query)
    total_due = total_due_result.scalar()

    review_words = len([w for w in words_data if w["progress"]["status"] > 0])
    new_words = len([w for w in words_data if w["progress"]["status"] == 0])

    return StudySessionResponse(
        session_id=session_id,
        words=words_data,
        stats={
            "total_due": total_due,
            "new_words": new_words,
            "review_words": review_words,
        }
    )


@router.post("/submit", response_model=StudySubmitResponse)
async def submit_study_result(
    submit_data: StudySubmitRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    提交学习结果

    使用 SM-2 算法计算下次复习时间
    """
    # 查找或创建用户进度记录
    progress_query = select(UserProgress).where(
        and_(
            UserProgress.user_id == current_user.id,
            UserProgress.word_id == submit_data.word_id
        )
    )
    progress_result = await db.execute(progress_query)
    progress = progress_result.scalar_one_or_none()

    if progress is None:
        # 创建新的进度记录
        progress = UserProgress(
            user_id=current_user.id,
            word_id=submit_data.word_id,
            status=0,
            ease_factor=2.5,
            interval=0,
            repetitions=0,
            total_reviews=0,
            correct_count=0,
            history=[]
        )
        db.add(progress)

    # 使用 SM-2 算法计算新参数
    new_interval, new_ease_factor, new_repetitions, next_review_at = SM2Algorithm.calculate_next_review(
        quality=submit_data.quality,
        prev_interval=progress.interval,
        prev_ease_factor=progress.ease_factor,
        prev_repetitions=progress.repetitions
    )

    # 更新状态
    new_status = SM2Algorithm.get_status_from_quality(submit_data.quality, progress.status)

    # 更新进度记录
    progress.status = new_status
    progress.next_review_at = next_review_at
    progress.ease_factor = new_ease_factor
    progress.interval = new_interval
    progress.repetitions = new_repetitions
    progress.last_review_at = datetime.utcnow()
    progress.total_reviews += 1

    if submit_data.quality >= 3:
        progress.correct_count += 1

    # 记录历史
    history_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "quality": submit_data.quality,
        "time_spent": submit_data.time_spent,
        "interval": new_interval,
        "ease_factor": new_ease_factor,
    }

    if progress.history is None:
        progress.history = []
    progress.history.append(history_entry)

    await db.commit()
    await db.refresh(progress)

    return StudySubmitResponse(
        next_review_at=progress.next_review_at,
        interval=progress.interval,
        ease_factor=progress.ease_factor,
        status=progress.status
    )


@router.get("/stats", response_model=StudyStatsResponse)
async def get_study_stats(
    period: str = Query("week", regex="^(day|week|month|all)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取学习统计
    """
    # 统计各状态的单词数量
    total_query = select(func.count(UserProgress.id)).where(
        UserProgress.user_id == current_user.id
    )
    total_result = await db.execute(total_query)
    total_words = total_result.scalar() or 0

    mastered_query = select(func.count(UserProgress.id)).where(
        and_(
            UserProgress.user_id == current_user.id,
            UserProgress.status == 3
        )
    )
    mastered_result = await db.execute(mastered_query)
    mastered = mastered_result.scalar() or 0

    learning_query = select(func.count(UserProgress.id)).where(
        and_(
            UserProgress.user_id == current_user.id,
            UserProgress.status.in_([1, 2])
        )
    )
    learning_result = await db.execute(learning_query)
    learning = learning_result.scalar() or 0

    new_query = select(func.count(UserProgress.id)).where(
        and_(
            UserProgress.user_id == current_user.id,
            UserProgress.status == 0
        )
    )
    new_result = await db.execute(new_query)
    new = new_result.scalar() or 0

    # 计算准确率
    accuracy_rate = 0.0
    if total_words > 0:
        accuracy_query = select(
            func.sum(UserProgress.correct_count),
            func.sum(UserProgress.total_reviews)
        ).where(UserProgress.user_id == current_user.id)
        accuracy_result = await db.execute(accuracy_query)
        correct_total, review_total = accuracy_result.one()

        if review_total and review_total > 0:
            accuracy_rate = correct_total / review_total

    return StudyStatsResponse(
        total_words=total_words,
        mastered=mastered,
        learning=learning,
        new=new,
        daily_streak=0,  # TODO: 实现连续学习天数统计
        accuracy_rate=accuracy_rate,
        time_spent_minutes=0,  # TODO: 实现学习时长统计
        chart_data={
            "dates": [],
            "reviews": [],
            "accuracy": [],
        }
    )

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class WordProgressInfo(BaseModel):
    status: int
    ease_factor: float
    interval: int
    total_reviews: int
    correct_count: int


class WordInSession(BaseModel):
    word_id: int
    spelling: str
    phonetic: Optional[str]
    definitions: List[Dict[str, str]]
    sentences: Optional[List[Dict[str, str]]]
    mnemonic: Optional[str]
    audio_url: Optional[str]
    progress: WordProgressInfo


class StudySessionStats(BaseModel):
    total_due: int
    new_words: int
    review_words: int


class StudySessionResponse(BaseModel):
    session_id: str
    words: List[Dict[str, Any]]
    stats: StudySessionStats


class StudySubmitRequest(BaseModel):
    session_id: str
    word_id: int
    quality: int = Field(..., ge=0, le=5)
    time_spent: float = Field(..., ge=0)


class StudySubmitResponse(BaseModel):
    next_review_at: datetime
    interval: int
    ease_factor: float
    status: int


class ChartData(BaseModel):
    dates: List[str]
    reviews: List[int]
    accuracy: List[float]


class StudyStatsResponse(BaseModel):
    total_words: int
    mastered: int
    learning: int
    new: int
    daily_streak: int
    accuracy_rate: float
    time_spent_minutes: int
    chart_data: ChartData

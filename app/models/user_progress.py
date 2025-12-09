from sqlalchemy import Column, BigInteger, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    status = Column(Integer, default=0, nullable=False)
    next_review_at = Column(DateTime(timezone=True), nullable=True)
    ease_factor = Column(Float, default=2.5, nullable=False)
    interval = Column(Integer, default=0, nullable=False)
    repetitions = Column(Integer, default=0, nullable=False)
    last_review_at = Column(DateTime(timezone=True), nullable=True)
    total_reviews = Column(Integer, default=0, nullable=False)
    correct_count = Column(Integer, default=0, nullable=False)
    history = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_user_next_review', 'user_id', 'next_review_at'),
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_user_word_unique', 'user_id', 'word_id', unique=True),
    )

    def __repr__(self):
        return f"<UserProgress(id={self.id}, user_id={self.user_id}, word_id={self.word_id}, status={self.status})>"

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    spelling = Column(String(100), unique=True, index=True, nullable=False)
    phonetic = Column(String(100), nullable=True)
    definitions = Column(JSONB, nullable=False)
    sentences = Column(JSONB, nullable=True)
    mnemonic = Column(Text, nullable=True)
    difficulty = Column(Integer, default=3)
    frequency_rank = Column(Integer, nullable=True)
    tags = Column(JSONB, nullable=True)
    audio_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    ai_generated = Column(Boolean, default=False, nullable=False)
    quality_score = Column(Float, default=0.5)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Word(id={self.id}, spelling='{self.spelling}')>"

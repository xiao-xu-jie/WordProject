from sqlalchemy import Column, BigInteger, Integer, Text, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class FeedbackType(str, enum.Enum):
    HELPFUL = "helpful"
    INCORRECT = "incorrect"
    INAPPROPRIATE = "inappropriate"


class ContentType(str, enum.Enum):
    DEFINITION = "definition"
    SENTENCE = "sentence"
    MNEMONIC = "mnemonic"


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    feedback_type = Column(SQLEnum(FeedbackType), nullable=False)
    content_type = Column(SQLEnum(ContentType), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserFeedback(id={self.id}, user_id={self.user_id}, word_id={self.word_id})>"

from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserStudyPlan(Base):
    __tablename__ = "user_study_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    name = Column(String(200), nullable=False)
    daily_new = Column(Integer, default=20, nullable=False)
    daily_review = Column(Integer, default=100, nullable=False)
    start_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserStudyPlan(id={self.id}, name='{self.name}', user_id={self.user_id})>"

from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class TaskType(str, enum.Enum):
    PDF_PARSE = "pdf_parse"
    AI_ENRICH = "ai_enrich"
    AUDIO_GENERATE = "audio_generate"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CeleryTask(Base):
    __tablename__ = "celery_tasks"

    id = Column(BigInteger, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<CeleryTask(id={self.id}, task_id='{self.task_id}', status='{self.status}')>"

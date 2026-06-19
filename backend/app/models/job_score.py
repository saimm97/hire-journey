import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobScore(Base):
    __tablename__ = "job_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("search_sessions.session_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.resume_id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)  # empty for keyword overlap
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="job_scores")
    session: Mapped["SearchSession"] = relationship(back_populates="job_scores")
    user: Mapped["User"] = relationship(back_populates="job_scores")
    resume: Mapped["Resume"] = relationship(back_populates="job_scores")

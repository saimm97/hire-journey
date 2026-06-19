import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.resume_id"), nullable=False)
    match_score: Mapped[int] = mapped_column(Integer, nullable=False)  # LLM deep score, 0-100
    strengths: Mapped[dict] = mapped_column(JSON, nullable=True)       # ["Strong Python background", ...]
    weaknesses: Mapped[dict] = mapped_column(JSON, nullable=True)      # ["Missing Kubernetes experience", ...]
    recommendations: Mapped[dict] = mapped_column(JSON, nullable=True) # ["Highlight FastAPI projects", ...]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="evaluations")
    user: Mapped["User"] = relationship(back_populates="evaluations")
    resume: Mapped["Resume"] = relationship(back_populates="evaluations")

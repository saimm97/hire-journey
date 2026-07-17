from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.profile import Profile


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    match_score: Mapped[int] = mapped_column(Integer, nullable=False)  # LLM deep score, 0-100
    strengths: Mapped[dict] = mapped_column(  # ["Strong Python background", ...]
        JSON, nullable=True
    )
    weaknesses: Mapped[dict] = mapped_column(  # ["Missing Kubernetes experience", ...]
        JSON, nullable=True
    )
    recommendations: Mapped[dict] = mapped_column(  # ["Highlight FastAPI projects", ...]
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="evaluations")
    profile: Mapped["Profile"] = relationship(back_populates="evaluations")

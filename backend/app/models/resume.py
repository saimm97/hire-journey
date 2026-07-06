import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Full ResumeExtraction dump: identity, summary, skills, experience, education, projects.
    parsed_content: Mapped[dict] = mapped_column(JSON, nullable=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="resumes")
    search_sessions: Mapped[list["SearchSession"]] = relationship(back_populates="resume")
    job_scores: Mapped[list["JobScore"]] = relationship(back_populates="resume")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="resume")
    tailored_resumes: Mapped[list["TailoredResume"]] = relationship(back_populates="source_resume")

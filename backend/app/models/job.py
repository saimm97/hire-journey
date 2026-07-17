from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.evaluation import Evaluation
    from app.models.tailored_resume import TailoredResume


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("url", name="uq_jobs_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    parsed_desc: Mapped[dict] = mapped_column(  # {required_skills: [], nice_to_have: []}
        JSON, nullable=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    salary_min: Mapped[int] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="jobs")
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    tailored_resumes: Mapped[list["TailoredResume"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

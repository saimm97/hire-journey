import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.evaluation import Evaluation
    from app.models.job_score import JobScore
    from app.models.search_session import SearchSession
    from app.models.tailored_resume import TailoredResume
    from app.models.user import User


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = (
        CheckConstraint("slot_number IN (1, 2)", name="ck_resumes_slot_number"),
        UniqueConstraint("user_id", "slot_number", name="uq_resumes_user_slot"),
        Index(
            "uq_resumes_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_content: Mapped[dict | None] = mapped_column(JSON)
    raw_content: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="resumes")
    search_sessions: Mapped[list["SearchSession"]] = relationship(back_populates="resume")
    job_scores: Mapped[list["JobScore"]] = relationship(back_populates="resume")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="resume")
    tailored_resumes: Mapped[list["TailoredResume"]] = relationship(back_populates="source_resume")

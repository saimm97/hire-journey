import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Candidate(Base):
    __tablename__ = "candidates"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    github_url: Mapped[str | None] = mapped_column(String(255))
    portfolio_url: Mapped[str | None] = mapped_column(String(255))
    # Professional summary, editable by the user; seeded from the parsed CV.
    summary: Mapped[str | None] = mapped_column(Text)
    minimum_salary: Mapped[int | None] = mapped_column(Integer)
    tech_stack: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    # The full parsed LinkedIn export (URL + all parsed fields), set by the
    # LinkedIn endpoint. Self-contained, so there is no flat linkedin_url column.
    linkedin_data: Mapped[dict | None] = mapped_column(JSON)
    # Required: the roles the user is targeting. Defaults to an empty array so a
    # candidate auto-created from a CV upload is valid; set via the profile endpoint.
    desired_role: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default=text("'{}'")
    )
    source_resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.resume_id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="candidate")

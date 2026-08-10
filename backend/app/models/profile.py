from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.employment import EmploymentHistory
    from app.models.evaluation import Evaluation
    from app.models.project import ProfileProject
    from app.models.tailored_resume import TailoredResume
    from app.models.technology import ProfileTechnology
    from app.models.user import User


from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint(
            "minimum_salary IS NULL OR minimum_salary >= 0",
            name="ck_profiles_minimum_salary_nonnegative",
        ),
        CheckConstraint(
            "jsonb_typeof(social_links) = 'object'",
            name="ck_profiles_social_links_object",
        ),
        CheckConstraint("jsonb_typeof(education) = 'array'", name="ck_profiles_education_array"),
        CheckConstraint(
            "jsonb_typeof(certifications) = 'array'",
            name="ck_profiles_certifications_array",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    location: Mapped[str | None] = mapped_column(String(255))
    social_links: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    education: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    certifications: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    title: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text)
    minimum_salary: Mapped[int | None] = mapped_column(Integer)
    desired_locations: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default=text("'{}'")
    )
    desired_roles: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default=text("'{}'")
    )
    work_modes_preferred: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default=text("'{}'")
    )
    seniority_level: Mapped[str | None] = mapped_column(String(50))
    source_resume_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("resumes.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="profile")
    project_memberships: Mapped[list["ProfileProject"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    employments: Mapped[list["EmploymentHistory"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    technologies: Mapped[list["ProfileTechnology"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    tailored_resumes: Mapped[list["TailoredResume"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

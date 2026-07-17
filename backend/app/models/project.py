from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.technology import Technology


class Project(Base):
    """A bare project identity; per-profile details live on ProfileProject."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile_memberships: Mapped[list["ProfileProject"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProfileProject(Base):
    __tablename__ = "profile_projects"
    __table_args__ = (
        UniqueConstraint("profile_id", "project_id", name="uq_profile_projects_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text)
    github_url: Mapped[str | None] = mapped_column(String(255))
    deployed_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped["Profile"] = relationship(back_populates="project_memberships")
    project: Mapped["Project"] = relationship(back_populates="profile_memberships")
    technologies: Mapped[list["ProfileProjectTechnology"]] = relationship(
        back_populates="profile_project", cascade="all, delete-orphan"
    )


class ProfileProjectTechnology(Base):
    """Normalized tech stack of one profile's project (replaces the string array)."""

    __tablename__ = "profile_project_technologies"

    profile_project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("profile_projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    technology_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("technologies.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    profile_project: Mapped["ProfileProject"] = relationship(back_populates="technologies")
    technology: Mapped["Technology"] = relationship()

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base

if TYPE_CHECKING:
    from app.models.profile import Profile


class Technology(Base):
    __tablename__ = "technologies"
    __table_args__ = (CheckConstraint("name = lower(name)", name="ck_technologies_name_lowercase"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profiles: Mapped[list["ProfileTechnology"]] = relationship(back_populates="technology")

    @validates("name")
    def _lowercase_name(self, key: str, value: str) -> str:
        return " ".join(value.strip().lower().split())


class ProfileTechnology(Base):
    __tablename__ = "profile_technologies"

    profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    technology_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("technologies.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    profile: Mapped["Profile"] = relationship(back_populates="technologies")
    technology: Mapped["Technology"] = relationship(back_populates="profiles")

    @property
    def name(self) -> str:
        return self.technology.name

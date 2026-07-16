import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.profile import Profile


class Technology(Base):
    __tablename__ = "technologies"

    technology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profiles: Mapped[list["ProfileTechnology"]] = relationship(back_populates="technology")


class ProfileTechnology(Base):
    __tablename__ = "profile_technologies"
    __table_args__ = (
        CheckConstraint(
            "years_experience IS NULL OR years_experience >= 0",
            name="ck_profile_technologies_years_nonnegative",
        ),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.profile_id", ondelete="CASCADE"),
        primary_key=True,
    )
    technology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technologies.technology_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    proficiency: Mapped[str | None] = mapped_column(String(30))
    years_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))

    profile: Mapped["Profile"] = relationship(back_populates="technologies")
    technology: Mapped["Technology"] = relationship(back_populates="profiles")

    @property
    def canonical_name(self) -> str:
        return self.technology.canonical_name

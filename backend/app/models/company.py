from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Company(Base):
    """A normalized employer referenced from resume employment history.

    The optional source fields remain mapped for compatibility with the shared
    migration history and downstream job-pipeline branches.
    """

    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("name", name="uq_companies_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    careers_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    source_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # "greenhouse", "ashby", "lever"
    base_url: Mapped[str] = mapped_column(String(255), nullable=True)

    jobs: Mapped[list["Job"]] = relationship(back_populates="source")

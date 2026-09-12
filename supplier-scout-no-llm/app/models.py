from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    category: Mapped[str] = mapped_column(String(140), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    region: Mapped[str] = mapped_column(String(160), index=True)
    website: Mapped[str] = mapped_column(String(500))
    contact: Mapped[str | None] = mapped_column(String(240), nullable=True)
    min_order: Mapped[str | None] = mapped_column(String(180), nullable=True)
    price_hint: Mapped[str | None] = mapped_column(String(180), nullable=True)
    certificates: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(String(500))
    source_checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    data_completeness: Mapped[float] = mapped_column(Float, default=0.0)
    verified_contact: Mapped[bool] = mapped_column(Boolean, default=False)

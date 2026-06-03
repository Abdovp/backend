from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), index=True)
    event_name: Mapped[str] = mapped_column(String(64))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    event_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    platforms: Mapped[str] = mapped_column(Text, default="")
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

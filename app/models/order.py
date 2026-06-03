from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(String(32))
    total: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[str] = mapped_column(String(64))
    product_name: Mapped[str] = mapped_column(String(255))
    offer: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    line_total: Mapped[float] = mapped_column(Numeric(10, 2))
    is_upsell: Mapped[bool] = mapped_column(Boolean, default=False)

    order: Mapped["Order"] = relationship(back_populates="items")

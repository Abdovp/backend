from datetime import date, datetime

from typing import Literal

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class AdminLoginResponse(BaseModel):
    token: str
    expires_at: datetime
    username: str


class FunnelStep(BaseModel):
    event_name: str
    label: str
    count: int
    rate_from_previous: float | None = None


class DailyMetric(BaseModel):
    date: date
    page_views: int
    orders: int
    revenue: float


class ProductMetric(BaseModel):
    product_id: str
    product_name: str
    orders: int
    quantity: int
    revenue: float


class AdminMetricsResponse(BaseModel):
    from_date: date
    to_date: date
    morocco_only: bool = True
    page_views: int
    view_content: int
    add_to_cart: int
    initiate_checkout: int
    orders: int
    revenue: float
    average_order_value: float
    conversion_rate: float
    checkout_conversion_rate: float
    upsell_orders: int
    upsell_rate: float
    pending_orders: int
    confirmed_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int
    confirmation_rate: float
    delivery_rate: float
    funnel: list[FunnelStep]
    daily: list[DailyMetric]
    top_products: list[ProductMetric]


class AdminOrderItem(BaseModel):
    product_id: str
    product_name: str
    offer: int
    quantity: int
    unit_price: float
    line_total: float
    is_upsell: bool


class AdminOrderSummary(BaseModel):
    id: int
    public_order_id: str
    event_id: str
    customer_name: str
    phone: str
    total: float
    status: str
    client_ip: str | None = None
    country_code: str | None = None
    has_upsell: bool
    sheet_sent: bool
    created_at: datetime
    item_count: int


class AdminOrderListResponse(BaseModel):
    items: list[AdminOrderSummary]
    total: int
    page: int
    limit: int
    pages: int


class AdminOrderDetail(AdminOrderSummary):
    admin_notes: str | None = None
    updated_at: datetime | None = None
    items: list[AdminOrderItem]
    capi_platforms: list[str] = []


class AdminOrderUpdate(BaseModel):
    status: Literal["pending", "confirmed", "shipped", "delivered", "cancelled", "returned"] | None = None
    admin_notes: str | None = Field(default=None, max_length=2000)

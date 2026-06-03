from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    product_id: str
    product_name: str
    sku: str | None = None
    offer: int = Field(ge=1, le=3)
    quantity: int = Field(ge=1, default=1)
    unit_price: float = Field(gt=0)
    is_upsell: bool = False


class OrderCreate(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    customer_name: str = Field(min_length=2, max_length=255)
    address: str = Field(default="", max_length=500)
    phone: str = Field(min_length=8, max_length=32)
    items: list[OrderItemCreate] = Field(min_length=1)
    total: float = Field(gt=0)
    source_url: str | None = None
    user_agent: str | None = None
    client_ip: str | None = None
    fbp: str | None = None
    fbc: str | None = None


class OrderItemResponse(BaseModel):
    product_id: str
    product_name: str
    offer: int
    quantity: int
    unit_price: float
    line_total: float
    is_upsell: bool


class OrderResponse(BaseModel):
    id: int
    public_order_id: str
    event_id: str
    status: str
    total: float
    items: list[OrderItemResponse]
    capi_sent: list[str]


class UpsellItemCreate(BaseModel):
    product_id: str
    product_name: str
    unit_price: float = Field(gt=0)
    offer: int = Field(ge=1, le=3, default=1)
    quantity: int = Field(ge=1, default=1)


class OrderFinalize(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    upsell: UpsellItemCreate | None = None


class OrderFinalizeResponse(BaseModel):
    ok: bool = True
    total: float
    already_sent: bool = False

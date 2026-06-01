import json
from pydantic import BaseModel, Field


class TrackingEventCreate(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    event_name: str = Field(min_length=2, max_length=64)
    event_data: dict | None = None
    order_id: int | None = None


class TrackingEventResponse(BaseModel):
    id: int
    event_id: str
    event_name: str
    order_id: int | None = None

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.database import get_engine
from app.schemas.events import TrackingEventCreate, TrackingEventResponse
from app.services.events import record_tracking_event

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=TrackingEventResponse)
def create_tracking_event(payload: TrackingEventCreate, db: Session = Depends(get_db)):
    if get_engine() is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    event = record_tracking_event(db, payload)
    return TrackingEventResponse(
        id=event.id,
        event_id=event.event_id,
        event_name=event.event_name,
        order_id=event.order_id,
    )

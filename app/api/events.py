from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.database import get_engine
from app.schemas.events import TrackingEventCreate, TrackingEventResponse
from app.services.events import record_tracking_event
from app.services.ip_geo import get_client_ip, resolve_country_code

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=TrackingEventResponse)
def create_tracking_event(payload: TrackingEventCreate, request: Request, db: Session = Depends(get_db)):
    if get_engine() is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    client_ip = get_client_ip(request)
    country_code = resolve_country_code(client_ip)

    event = record_tracking_event(db, payload, client_ip=client_ip, country_code=country_code)
    return TrackingEventResponse(
        id=event.id,
        event_id=event.event_id,
        event_name=event.event_name,
        order_id=event.order_id,
    )

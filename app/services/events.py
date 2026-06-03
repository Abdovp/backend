import json
import logging

from sqlalchemy.orm import Session

from app.models.tracking import TrackingEvent
from app.schemas.events import TrackingEventCreate

logger = logging.getLogger(__name__)


def record_tracking_event(
    db: Session,
    data: TrackingEventCreate,
    platforms: str = "",
    client_ip: str | None = None,
    country_code: str | None = None,
) -> TrackingEvent:
    event = TrackingEvent(
        event_id=data.event_id,
        event_name=data.event_name,
        order_id=data.order_id,
        event_data=json.dumps(data.event_data or {}, ensure_ascii=False),
        platforms=platforms,
        client_ip=client_ip,
        country_code=country_code,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info("Recorded tracking event %s (%s)", data.event_name, data.event_id)
    return event

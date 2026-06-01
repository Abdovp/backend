from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import SessionLocal, get_engine
from app.schemas.order import OrderCreate, OrderItemResponse, OrderResponse
from app.services.orders import create_order, notify_google_sheet

router = APIRouter(prefix="/api/orders", tags=["orders"])


def get_db():
    if get_engine() is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=OrderResponse)
def submit_order(payload: OrderCreate, request: Request, db: Session = Depends(get_db)):
    if get_engine() is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        order, capi_sent = create_order(db, payload, client_ip, user_agent)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order already submitted") from exc
    except ValueError as exc:
        if str(exc) == "invalid_phone":
            raise HTTPException(status_code=422, detail="Invalid Moroccan phone number") from exc
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not create order") from exc

    settings = get_settings()
    notify_google_sheet(order, settings.google_sheet_webhook_url)

    return OrderResponse(
        id=order.id,
        event_id=order.event_id,
        status=order.status,
        total=float(order.total),
        items=[
            OrderItemResponse(
                product_id=item.product_id,
                product_name=item.product_name,
                offer=item.offer,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                line_total=float(item.line_total),
                is_upsell=item.is_upsell,
            )
            for item in order.items
        ],
        capi_sent=capi_sent,
    )

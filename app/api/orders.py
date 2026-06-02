from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import check_database_connection
from app.deps import get_db
from app.database import get_engine
from app.schemas.order import (
    OrderCreate,
    OrderFinalize,
    OrderFinalizeResponse,
    OrderItemResponse,
    OrderResponse,
)
from app.services.orders import create_order, finalize_order_for_sheet
from app.services.sheet_webhook import make_boya_order_id

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderResponse)
def submit_order(payload: OrderCreate, request: Request, db: Session = Depends(get_db)):
    if get_engine() is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    db_ok, db_detail = check_database_connection()
    if not db_ok:
        raise HTTPException(status_code=503, detail="Database unavailable")

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
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not create order") from exc

    public_order_id = make_boya_order_id(order.id)

    return OrderResponse(
        id=order.id,
        public_order_id=public_order_id,
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


@router.post("/{order_id}/finalize", response_model=OrderFinalizeResponse)
def finalize_order(order_id: int, payload: OrderFinalize, db: Session = Depends(get_db)):
    if get_engine() is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        order, already_sent = finalize_order_for_sheet(
            db,
            order_id,
            payload.event_id,
            payload.upsell,
            get_settings().google_sheet_webhook_url,
        )
    except ValueError as exc:
        if str(exc) == "not_found":
            raise HTTPException(status_code=404, detail="Order not found") from exc
        raise
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not finalize order") from exc

    return OrderFinalizeResponse(
        total=float(order.total),
        already_sent=already_sent,
    )

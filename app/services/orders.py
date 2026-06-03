import json
import logging

from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.tracking import TrackingEvent
from app.schemas.order import OrderCreate, UpsellItemCreate
from app.services.capi import dispatch_purchase_events
from app.services.ip_geo import resolve_country_code
from app.services.phone import normalize_moroccan_phone, validate_moroccan_phone
from app.services.sheet_webhook import notify_google_sheet

logger = logging.getLogger(__name__)


def create_order(db: Session, data: OrderCreate, client_ip: str | None, user_agent: str | None) -> tuple[Order, list[str]]:
    if not validate_moroccan_phone(data.phone):
        raise ValueError("invalid_phone")

    phone = normalize_moroccan_phone(data.phone)
    assert phone is not None

    resolved_ip = data.client_ip or client_ip
    country_code = resolve_country_code(resolved_ip)

    order = Order(
        event_id=data.event_id,
        customer_name=data.customer_name.strip(),
        address=data.address.strip(),
        phone=phone,
        total=data.total,
        status="pending",
        client_ip=resolved_ip,
        country_code=country_code,
    )

    for item in data.items:
        line_total = round(item.unit_price * item.quantity, 2)
        order.items.append(
            OrderItem(
                product_id=item.product_id,
                product_name=item.product_name,
                offer=item.offer,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=line_total,
                is_upsell=item.is_upsell,
            )
        )

    db.add(order)
    db.flush()

    capi_payload = {
        "event_id": data.event_id,
        "order_id": order.id,
        "customer_name": order.customer_name,
        "phone": order.phone,
        "source_url": data.source_url,
        "client_ip": resolved_ip,
        "user_agent": data.user_agent or user_agent,
        "fbp": data.fbp,
        "fbc": data.fbc,
        "items": [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "line_total": float(item.line_total),
            }
            for item in order.items
        ],
    }
    sent = dispatch_purchase_events(capi_payload)

    db.add(
        TrackingEvent(
            event_id=data.event_id,
            event_name="Purchase",
            order_id=order.id,
            event_data=json.dumps(
                {
                    "total": float(order.total),
                    "items": [
                        {
                            "product_id": item.product_id,
                            "product_name": item.product_name,
                            "offer": item.offer,
                            "quantity": item.quantity,
                            "unit_price": float(item.unit_price),
                            "line_total": float(item.line_total),
                        }
                        for item in order.items
                    ],
                },
                ensure_ascii=False,
            ),
            platforms=",".join(sent),
            client_ip=resolved_ip,
            country_code=country_code,
        )
    )

    db.commit()
    db.refresh(order)
    return order, sent


def finalize_order_for_sheet(
    db: Session,
    order_id: int,
    event_id: str,
    upsell: UpsellItemCreate | None,
    webhook_url: str | None,
) -> tuple[Order, bool]:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None or order.event_id != event_id:
        raise ValueError("not_found")

    already_sent = (
        db.query(TrackingEvent)
        .filter(
            TrackingEvent.order_id == order_id,
            TrackingEvent.event_name == "SheetNotify",
        )
        .first()
        is not None
    )
    if already_sent:
        db.refresh(order)
        return order, True

    if upsell is not None:
        has_upsell = any(
            item.product_id == upsell.product_id and item.is_upsell for item in order.items
        )
        if not has_upsell:
            line_total = round(upsell.unit_price * upsell.quantity, 2)
            order.items.append(
                OrderItem(
                    product_id=upsell.product_id,
                    product_name=upsell.product_name,
                    offer=upsell.offer,
                    quantity=upsell.quantity,
                    unit_price=upsell.unit_price,
                    line_total=line_total,
                    is_upsell=True,
                )
            )
            order.total = round(float(order.total) + line_total, 2)

    db.add(
        TrackingEvent(
            event_id=event_id,
            event_name="SheetNotify",
            order_id=order.id,
            event_data=json.dumps({"total": float(order.total)}, ensure_ascii=False),
            platforms="google_sheet",
        )
    )
    db.commit()
    db.refresh(order)

    notify_google_sheet(order, webhook_url)
    return order, False

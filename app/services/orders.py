import json
import logging

import requests
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.tracking import TrackingEvent
from app.schemas.order import OrderCreate
from app.services.capi import dispatch_purchase_events
from app.services.phone import normalize_moroccan_phone, validate_moroccan_phone

logger = logging.getLogger(__name__)


def create_order(db: Session, data: OrderCreate, client_ip: str | None, user_agent: str | None) -> tuple[Order, list[str]]:
    if not validate_moroccan_phone(data.phone):
        raise ValueError("invalid_phone")

    phone = normalize_moroccan_phone(data.phone)
    assert phone is not None

    order = Order(
        event_id=data.event_id,
        customer_name=data.customer_name.strip(),
        address=data.address.strip(),
        phone=phone,
        total=data.total,
        status="pending",
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
        "client_ip": data.client_ip or client_ip,
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
        )
    )

    db.commit()
    db.refresh(order)
    return order, sent


def notify_google_sheet(order: Order, webhook_url: str | None) -> None:
    if not webhook_url:
        return

    payload = {
        "order_id": order.id,
        "event_id": order.event_id,
        "name": order.customer_name,
        "phone": order.phone,
        "address": order.address,
        "total": float(order.total),
        "status": order.status,
        "items": [
            {
                "product_id": item.product_id,
                "name": item.product_name,
                "offer": item.offer,
                "quantity": item.quantity,
                "price": float(item.unit_price),
            }
            for item in order.items
        ],
    }

    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as exc:
        logger.warning("Google Sheet webhook failed: %s", exc)

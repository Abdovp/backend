import logging
from datetime import datetime

import requests

from app.catalog.products import get_product_sku
from app.models.order import Order
from app.services.phone import normalize_moroccan_phone

logger = logging.getLogger(__name__)


def make_boya_order_id(order_id: int) -> str:
    return f"boya{order_id:06d}"


def format_sheet_date(dt: datetime) -> str:
    return f"{dt.day}/{dt.month}/{dt.strftime('%y')}"


def format_phone_for_sheet(phone: str) -> str:
    normalized = normalize_moroccan_phone(phone) or phone.strip()
    if normalized.startswith("+212"):
        return f"0{normalized[4:]}"
    return normalized


def line_piece_count(offer: int, quantity: int) -> int:
    return max(1, offer * quantity)


def build_sheet_row(order: Order, *, public_order_id: str | None = None) -> dict[str, str]:
    items = list(order.items)
    order_id = public_order_id or make_boya_order_id(order.id)
    created = order.created_at or datetime.utcnow()

    produit = "/".join(item.product_name for item in items)
    sku = "/".join(get_product_sku(item.product_id) for item in items)
    qte = "/".join(str(line_piece_count(item.offer, item.quantity)) for item in items)
    total_value = float(order.total)
    total_label = f"{int(total_value) if total_value.is_integer() else total_value} dh"

    return {
        "date": format_sheet_date(created),
        "orderid": order_id,
        "nom": order.customer_name.strip(),
        "téléphone": format_phone_for_sheet(order.phone),
        "produit": produit,
        "sku": sku,
        "QTé": qte,
        "prix total": total_label,
    }


def notify_google_sheet(order: Order, webhook_url: str | None) -> None:
    if not webhook_url:
        return

    payload = build_sheet_row(order)

    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        if not response.ok:
            logger.warning(
                "Google Sheet webhook HTTP %s: %s",
                response.status_code,
                response.text[:500],
            )
    except Exception as exc:
        logger.warning("Google Sheet webhook failed: %s", exc)

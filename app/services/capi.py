import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import get_settings
from app.services.hashing import hash_name, sha256
from app.services.phone import normalize_moroccan_phone

logger = logging.getLogger(__name__)


def _contents(items: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]], float]:
    content_ids = [item["product_id"] for item in items]
    contents = [
        {
            "content_id": item["product_id"],
            "quantity": item["quantity"],
            "price": float(item["unit_price"]),
        }
        for item in items
    ]
    value = sum(float(item["line_total"]) for item in items)
    return content_ids, contents, value


def send_facebook_purchase(payload: dict[str, Any]) -> bool:
    settings = get_settings()
    if not settings.facebook_capi_token or not settings.facebook_pixel_id:
        return False

    phone = normalize_moroccan_phone(payload["phone"])
    user_data: dict[str, Any] = {
        "ph": [sha256(phone)] if phone else [],
        "fn": [hash_name(payload["customer_name"])] if payload.get("customer_name") else [],
    }
    if payload.get("client_ip"):
        user_data["client_ip_address"] = payload["client_ip"]
    if payload.get("user_agent"):
        user_data["client_user_agent"] = payload["user_agent"]
    if payload.get("fbp"):
        user_data["fbp"] = payload["fbp"]
    if payload.get("fbc"):
        user_data["fbc"] = payload["fbc"]

    content_ids, contents, value = _contents(payload["items"])
    event = {
        "event_name": payload["event_name"],
        "event_time": int(time.time()),
        "event_id": payload["event_id"],
        "action_source": "website",
        "event_source_url": payload.get("source_url") or f"{settings.frontend_url.rstrip('/')}/thank-you",
        "user_data": user_data,
        "custom_data": {
            "currency": "MAD",
            "value": value,
            "content_ids": content_ids,
            "contents": contents,
            "content_type": "product",
            "order_id": str(payload.get("order_id", payload["event_id"])),
        },
    }

    url = f"https://graph.facebook.com/{settings.meta_api_version}/{settings.facebook_pixel_id}/events"
    try:
        response = requests.post(
            url,
            params={"access_token": settings.facebook_capi_token},
            json={"data": [event]},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Facebook CAPI failed: %s", exc)
        return False


def send_tiktok_purchase(payload: dict[str, Any]) -> bool:
    settings = get_settings()
    if not settings.tiktok_capi_token or not settings.tiktok_pixel_id:
        return False

    phone = normalize_moroccan_phone(payload["phone"])
    content_ids, contents, value = _contents(payload["items"])
    user_data: dict[str, Any] = {}
    if phone:
        user_data["phone_number"] = sha256(phone)
    if payload.get("ttp"):
        user_data["ttp"] = payload["ttp"]

    context: dict[str, Any] = {
        "user": user_data,
        "page": {"url": payload.get("source_url") or f"{settings.frontend_url.rstrip('/')}/thank-you"},
    }
    if payload.get("client_ip"):
        context["ip"] = payload["client_ip"]
    if payload.get("user_agent"):
        context["user_agent"] = payload["user_agent"]
    if payload.get("ttclid"):
        context["ad"] = {"callback": payload["ttclid"]}

    body = {
        "pixel_code": settings.tiktok_pixel_id,
        "event": "Purchase",
        "event_id": payload["event_id"],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "context": context,
        "properties": {
            "currency": "MAD",
            "value": value,
            "content_type": "product",
            "contents": contents,
            "content_ids": content_ids,
        },
    }

    try:
        response = requests.post(
            f"https://business-api.tiktok.com/open_api/{settings.tiktok_api_version}/pixel/track/",
            headers={"Access-Token": settings.tiktok_capi_token, "Content-Type": "application/json"},
            json=body,
            timeout=10,
        )
        data = response.json()
        if response.status_code >= 400 or data.get("code") not in (0, None):
            logger.warning(
                "TikTok CAPI rejected event (status=%s): %s body=%s",
                response.status_code,
                data,
                body,
            )
            return False
        return True
    except Exception as exc:
        logger.warning("TikTok CAPI failed: %s", exc)
        return False


def send_snapchat_purchase(payload: dict[str, Any]) -> bool:
    settings = get_settings()
    if not settings.snapchat_capi_token or not settings.snapchat_pixel_id:
        return False

    phone = normalize_moroccan_phone(payload["phone"])
    _, contents, value = _contents(payload["items"])
    user_data: dict[str, Any] = {}
    if phone:
        user_data["phone_number"] = sha256(phone)
    if payload.get("client_ip"):
        user_data["client_ip_address"] = payload["client_ip"]

    body = {
        "pixel_id": settings.snapchat_pixel_id,
        "event_type": "PURCHASE",
        "event_conversion_type": "WEB",
        "event_tag": payload["event_id"],
        "timestamp": int(time.time() * 1000),
        "hashed_email": [],
        "hashed_phone_number": [user_data["phone_number"]] if user_data.get("phone_number") else [],
        "user_agent": payload.get("user_agent"),
        "page_url": payload.get("source_url"),
        "price": value,
        "currency": "MAD",
        "item_ids": [item["product_id"] for item in payload["items"]],
        "number_items": sum(item["quantity"] for item in payload["items"]),
    }

    try:
        response = requests.post(
            "https://tr.snapchat.com/v2/conversion",
            headers={
                "Authorization": f"Bearer {settings.snapchat_capi_token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Snapchat CAPI failed: %s", exc)
        return False


def dispatch_purchase_events(payload: dict[str, Any]) -> list[str]:
    settings = get_settings()
    if not settings.enable_capi:
        return []

    payload = {**payload, "event_name": "Purchase"}
    sent: list[str] = []

    if settings.enable_meta_capi and send_facebook_purchase(payload):
        sent.append("facebook")
    if settings.enable_tiktok_capi and send_tiktok_purchase(payload):
        sent.append("tiktok")
    if settings.enable_snap_capi and send_snapchat_purchase(payload):
        sent.append("snapchat")

    return sent

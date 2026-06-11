import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import get_settings
from app.services.hashing import hash_name, hash_phone, hash_phone_tiktok
from app.services.phone import normalize_moroccan_phone

logger = logging.getLogger(__name__)


def _meta_contents(items: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]], float]:
    content_ids = [item["product_id"] for item in items]
    contents = [
        {
            "id": item["product_id"],
            "quantity": item["quantity"],
            "item_price": float(item["unit_price"]),
        }
        for item in items
    ]
    value = sum(float(item["line_total"]) for item in items)
    return content_ids, contents, value


def _tiktok_contents(items: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]], float]:
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
    user_data: dict[str, Any] = {}
    if phone:
        user_data["ph"] = [hash_phone(phone)]
    if payload.get("customer_name"):
        hashed_name = hash_name(payload["customer_name"])
        if hashed_name:
            user_data["fn"] = [hashed_name]
    if payload.get("client_ip"):
        user_data["client_ip_address"] = payload["client_ip"]
    if payload.get("user_agent"):
        user_data["client_user_agent"] = payload["user_agent"]
    if payload.get("fbp"):
        user_data["fbp"] = payload["fbp"]
    if payload.get("fbc"):
        user_data["fbc"] = payload["fbc"]

    content_ids, contents, value = _meta_contents(payload["items"])
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
        data = response.json()
        if response.status_code >= 400 or data.get("error"):
            logger.warning("Facebook CAPI rejected event (status=%s): %s", response.status_code, data)
            return False
        return True
    except Exception as exc:
        logger.warning("Facebook CAPI failed: %s", exc)
        return False


def send_tiktok_purchase(payload: dict[str, Any]) -> bool:
    settings = get_settings()
    if not settings.tiktok_capi_token or not settings.tiktok_pixel_id:
        return False

    phone = normalize_moroccan_phone(payload["phone"])
    content_ids, contents, value = _tiktok_contents(payload["items"])
    user_data: dict[str, Any] = {}
    if phone:
        user_data["phone_number"] = hash_phone_tiktok(phone)
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
                "TikTok CAPI rejected event (status=%s): %s",
                response.status_code,
                data,
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
    content_ids, _, value = _tiktok_contents(payload["items"])
    event_id = payload["event_id"]
    order_ref = str(payload.get("order_id", event_id))

    body = {
        "pixel_id": settings.snapchat_pixel_id,
        "event_type": "PURCHASE",
        "event_conversion_type": "WEB",
        "event_tag": event_id,
        "client_dedup_id": event_id,
        "transaction_id": order_ref,
        "timestamp": int(time.time() * 1000),
        "hashed_phone_number": [hash_phone(phone)] if phone else [],
        "user_agent": payload.get("user_agent"),
        "page_url": payload.get("source_url"),
        "price": value,
        "currency": "MAD",
        "item_ids": content_ids,
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
        if response.status_code >= 400:
            logger.warning(
                "Snapchat CAPI rejected event (status=%s): %s",
                response.status_code,
                response.text[:500],
            )
            return False
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

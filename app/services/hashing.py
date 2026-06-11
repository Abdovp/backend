import hashlib
import re


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_email(email: str) -> str:
    return sha256(email.strip().lower())


def hash_name(name: str) -> str:
    first = name.strip().lower().split()[0] if name.strip() else ""
    return sha256(first) if first else ""


def hash_phone(phone: str) -> str:
    """Normalize to digits with country code, then SHA256 (Meta/Snap CAPI)."""
    cleaned = phone.strip()
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    digits = re.sub(r"\D", "", cleaned)
    return sha256(digits) if digits else ""


def hash_phone_tiktok(phone: str) -> str:
    """Normalize to E.164 with leading +, then SHA256 (TikTok CAPI)."""
    cleaned = phone.strip()
    if not cleaned:
        return ""
    digits = re.sub(r"\D", "", cleaned[1:] if cleaned.startswith("+") else cleaned)
    e164 = f"+{digits}" if digits else ""
    return sha256(e164) if e164 else ""

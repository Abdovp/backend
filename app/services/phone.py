import re


def normalize_moroccan_phone(phone: str) -> str | None:
    cleaned = re.sub(r"[\s\-()]", "", phone.strip())
    if not cleaned:
        return None

    if cleaned.startswith("+212"):
        digits = cleaned[4:]
    elif cleaned.startswith("00212"):
        digits = cleaned[5:]
    elif cleaned.startswith("0"):
        digits = cleaned[1:]
    else:
        digits = cleaned

    if not re.fullmatch(r"[67]\d{8}", digits):
        return None

    return f"+212{digits}"


def validate_moroccan_phone(phone: str) -> bool:
    return normalize_moroccan_phone(phone) is not None

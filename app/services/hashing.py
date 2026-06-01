import hashlib


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_email(email: str) -> str:
    return sha256(email.strip().lower())


def hash_name(name: str) -> str:
    first = name.strip().lower().split()[0] if name.strip() else ""
    return sha256(first) if first else ""

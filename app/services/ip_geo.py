import ipaddress
import logging
from functools import lru_cache

import requests
from fastapi import Request

logger = logging.getLogger(__name__)

# Verified Morocco allocations (AFRINIC / RIPE). External lookup used as fallback.
MOROCCO_CIDRS = [
    # Maroc Telecom / IAM
    "196.96.0.0/11",
    "41.88.0.0/13",
    "41.248.0.0/13",
    "105.152.0.0/13",
    "196.12.0.0/15",
    # Orange Morocco (Méditelecom)
    "41.136.0.0/13",
    "196.32.0.0/15",
    "196.34.0.0/16",
    # Inwi (Wana Corporate)
    "105.190.0.0/15",
    "105.71.0.0/16",
    # Other / shared allocations
    "102.129.176.0/21",
    "105.66.0.0/15",
    "105.156.0.0/14",
    "197.145.0.0/16",
    "41.137.0.0/16",
    "41.142.0.0/15",
    "41.250.0.0/16",
    "196.200.0.0/14",
    "196.206.0.0/15",
    "154.117.0.0/16",
    "154.118.0.0/16",
    "196.1.96.0/19",
    "196.1.128.0/18",
]

_MOROCCO_NETWORKS = tuple(ipaddress.ip_network(cidr, strict=False) for cidr in MOROCCO_CIDRS)


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        for part in forwarded.split(","):
            candidate = part.strip()
            if candidate:
                try:
                    addr = ipaddress.ip_address(candidate)
                    if not (addr.is_private or addr.is_loopback or addr.is_reserved):
                        return candidate
                except ValueError:
                    continue
    if request.client and request.client.host:
        return request.client.host
    return None


def _matches_morocco_cidr(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in network for network in _MOROCCO_NETWORKS)


@lru_cache(maxsize=4096)
def _lookup_country_code(ip: str) -> str | None:
    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip}?fields=countryCode",
            timeout=1.5,
        )
        if response.ok:
            code = response.json().get("countryCode")
            if isinstance(code, str) and len(code) == 2:
                return code.upper()
    except requests.RequestException as exc:
        logger.debug("IP lookup failed for %s: %s", ip, exc)
    return None


def resolve_country_code(ip: str | None) -> str | None:
    if not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback:
            return None
    except ValueError:
        return None
    if _matches_morocco_cidr(ip):
        return "MA"
    return _lookup_country_code(ip)


def is_morocco_ip(ip: str | None) -> bool:
    return resolve_country_code(ip) == "MA"

import os
from functools import lru_cache


@lru_cache
def get_settings():
    return Settings()


class Settings:
    database_url: str | None
    google_sheet_webhook_url: str | None
    facebook_capi_token: str | None
    tiktok_capi_token: str | None
    snapchat_capi_token: str | None
    facebook_pixel_id: str | None
    tiktok_pixel_id: str | None
    snapchat_pixel_id: str | None
    domain: str | None

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "").strip() or None
        self.google_sheet_webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip() or None
        self.facebook_capi_token = os.getenv("FACEBOOK_CAPI_TOKEN", "").strip() or None
        self.tiktok_capi_token = os.getenv("TIKTOK_CAPI_TOKEN", "").strip() or None
        self.snapchat_capi_token = os.getenv("SNAPCHAT_CAPI_TOKEN", "").strip() or None
        self.facebook_pixel_id = os.getenv("FACEBOOK_PIXEL_ID", "").strip() or None
        self.tiktok_pixel_id = os.getenv("TIKTOK_PIXEL_ID", "").strip() or None
        self.snapchat_pixel_id = os.getenv("SNAPCHAT_PIXEL_ID", "").strip() or None
        self.domain = os.getenv("DOMAIN", "").strip() or None

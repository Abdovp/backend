import os
from functools import lru_cache


def _env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


@lru_cache
def get_settings():
    return Settings()


class Settings:
    app_env: str
    app_name: str
    api_base_url: str
    frontend_url: str
    database_url: str | None
    cors_origins: list[str]
    google_sheets_webhook_url: str | None
    meta_pixel_id: str | None
    meta_access_token: str | None
    meta_api_version: str
    tiktok_pixel_code: str | None
    tiktok_access_token: str | None
    tiktok_api_version: str
    snap_pixel_id: str | None
    snap_access_token: str | None
    enable_capi: bool
    enable_meta_capi: bool
    enable_tiktok_capi: bool
    enable_snap_capi: bool

    def __init__(self):
        self.app_env = _env("APP_ENV") or "production"
        self.app_name = _env("APP_NAME") or "Boya Shop API"
        self.api_base_url = _env("API_BASE_URL", "DOMAIN") or "https://api.boyashop.store"
        self.frontend_url = _env("FRONTEND_URL") or "https://boyashop.store"
        self.database_url = _env("DATABASE_URL")

        cors_raw = _env("CORS_ORIGINS")
        if cors_raw:
            self.cors_origins = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
        else:
            self.cors_origins = [
                "https://boyashop.store",
                "https://www.boyashop.store",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]

        self.google_sheets_webhook_url = _env("GOOGLE_SHEETS_WEBHOOK_URL", "GOOGLE_SHEET_WEBHOOK_URL")

        self.meta_pixel_id = _env("META_PIXEL_ID", "FACEBOOK_PIXEL_ID")
        self.meta_access_token = _env("META_ACCESS_TOKEN", "FACEBOOK_CAPI_TOKEN")
        self.meta_api_version = _env("META_API_VERSION") or "v20.0"

        self.tiktok_pixel_code = _env("TIKTOK_PIXEL_CODE", "TIKTOK_PIXEL_ID")
        self.tiktok_access_token = _env("TIKTOK_ACCESS_TOKEN", "TIKTOK_CAPI_TOKEN")
        self.tiktok_api_version = _env("TIKTOK_API_VERSION") or "v1.3"

        self.snap_pixel_id = _env("SNAP_PIXEL_ID", "SNAPCHAT_PIXEL_ID")
        self.snap_access_token = _env("SNAP_ACCESS_TOKEN", "SNAPCHAT_CAPI_TOKEN")

        self.enable_capi = _env_bool("ENABLE_CAPI", True)
        self.enable_meta_capi = _env_bool("ENABLE_META_CAPI", True)
        self.enable_tiktok_capi = _env_bool("ENABLE_TIKTOK_CAPI", True)
        self.enable_snap_capi = _env_bool("ENABLE_SNAP_CAPI", True)

    # Backward-compatible aliases used elsewhere in the codebase.
    @property
    def facebook_pixel_id(self) -> str | None:
        return self.meta_pixel_id

    @property
    def facebook_capi_token(self) -> str | None:
        return self.meta_access_token

    @property
    def tiktok_pixel_id(self) -> str | None:
        return self.tiktok_pixel_code

    @property
    def tiktok_capi_token(self) -> str | None:
        return self.tiktok_access_token

    @property
    def snapchat_pixel_id(self) -> str | None:
        return self.snap_pixel_id

    @property
    def snapchat_capi_token(self) -> str | None:
        return self.snap_access_token

    @property
    def google_sheet_webhook_url(self) -> str | None:
        return self.google_sheets_webhook_url

    @property
    def domain(self) -> str | None:
        return self.api_base_url.replace("https://", "").replace("http://", "").strip("/")

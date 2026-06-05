"""Store catalog — SKUs and Arabic names used for Google Sheets webhooks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogProduct:
    product_id: str
    sku: str
    name_ar: str


PRODUCT_CATALOG: dict[str, CatalogProduct] = {
    "cooling-pack": CatalogProduct(
        product_id="cooling-pack",
        sku="BOYA-CP-2847",
        name_ar="باك الحماية من سخونة السيارة",
    ),
    "magnetic-holder": CatalogProduct(
        product_id="magnetic-holder",
        sku="BOYA-MH-9153",
        name_ar="حامل الهاتف المغناطيسي للسيارة",
    ),
    "car-vacuum": CatalogProduct(
        product_id="car-vacuum",
        sku="BOYA-CV-4471",
        name_ar="مكنسة السيارة 3 في 1",
    ),
}


def get_catalog_product(product_id: str) -> CatalogProduct | None:
    return PRODUCT_CATALOG.get(product_id)


def get_product_sku(product_id: str) -> str:
    product = get_catalog_product(product_id)
    if product:
        return product.sku
    safe_id = product_id.replace("-", "").upper()[:8]
    return f"BOYA-UNK-{safe_id or 'ITEM'}"

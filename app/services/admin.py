import math
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem
from app.models.tracking import TrackingEvent
from app.schemas.admin import (
    AdminMetricsResponse,
    AdminOrderDetail,
    AdminOrderItem,
    AdminOrderListResponse,
    AdminOrderSummary,
    DailyMetric,
    FunnelStep,
    ProductMetric,
)
from app.services.sheet_webhook import make_boya_order_id

FUNNEL_EVENTS = [
    ("PageView", "Visits"),
    ("ViewContent", "View Product"),
    ("AddToCart", "Add to Cart"),
    ("InitiateCheckout", "Initiate Checkout"),
    ("Purchase", "Orders"),
]

ORDER_STATUSES = ("pending", "confirmed", "shipped", "delivered", "cancelled", "returned")
CONFIRMED_PIPELINE_STATUSES = frozenset({"confirmed", "shipped", "delivered"})
DELIVERED_STATUSES = frozenset({"delivered"})


def _day_bounds(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(from_date, time.min)
    end = datetime.combine(to_date + timedelta(days=1), time.min)
    return start, end


def _morocco_event_filter():
    return TrackingEvent.country_code == "MA"


def _morocco_order_filter():
    return Order.country_code == "MA"


def get_admin_metrics(
    db: Session,
    from_date: date,
    to_date: date,
    morocco_only: bool = True,
    exclude_ips: list[str] | None = None,
) -> AdminMetricsResponse:
    start, end = _day_bounds(from_date, to_date)

    event_filters = [
        TrackingEvent.created_at >= start,
        TrackingEvent.created_at < end,
        TrackingEvent.event_name.in_([name for name, _ in FUNNEL_EVENTS]),
    ]
    if morocco_only:
        event_filters.append(_morocco_event_filter())
    if exclude_ips:
        event_filters.append(or_(TrackingEvent.client_ip == None, TrackingEvent.client_ip.not_in(exclude_ips)))

    event_counts = dict(
        db.execute(
            select(TrackingEvent.event_name, func.count())
            .where(*event_filters)
            .group_by(TrackingEvent.event_name)
        ).all()
    )

    order_filters = [Order.created_at >= start, Order.created_at < end]
    if morocco_only:
        order_filters.append(_morocco_order_filter())
    if exclude_ips:
        order_filters.append(or_(Order.client_ip == None, Order.client_ip.not_in(exclude_ips)))

    orders = db.scalars(select(Order).where(*order_filters).options(joinedload(Order.items))).unique().all()
    order_count = len(orders)
    revenue = round(sum(float(order.total) for order in orders), 2)
    aov = round(revenue / order_count, 2) if order_count else 0.0

    page_views = int(event_counts.get("PageView", 0))
    view_content = int(event_counts.get("ViewContent", 0))
    add_to_cart = int(event_counts.get("AddToCart", 0))
    initiate_checkout = int(event_counts.get("InitiateCheckout", 0))
    purchase_events = int(event_counts.get("Purchase", 0))

    conversion_rate = round((order_count / page_views) * 100, 2) if page_views else 0.0
    checkout_conversion_rate = round((order_count / initiate_checkout) * 100, 2) if initiate_checkout else 0.0

    upsell_orders = sum(1 for order in orders if any(item.is_upsell for item in order.items))
    upsell_rate = round((upsell_orders / order_count) * 100, 2) if order_count else 0.0

    status_counts = {status: 0 for status in ORDER_STATUSES}
    for order in orders:
        if order.status in status_counts:
            status_counts[order.status] += 1

    confirmed_orders = sum(status_counts[status] for status in CONFIRMED_PIPELINE_STATUSES)
    delivered_orders = status_counts["delivered"]
    actionable_orders = order_count - status_counts["cancelled"] - status_counts["returned"]
    confirmation_rate = (
        round((confirmed_orders / actionable_orders) * 100, 2) if actionable_orders else 0.0
    )
    delivery_rate = round((delivered_orders / confirmed_orders) * 100, 2) if confirmed_orders else 0.0
    cancelled_orders = status_counts["cancelled"]
    cancellation_rate = round((cancelled_orders / order_count) * 100, 2) if order_count else 0.0

    funnel_values = [
        page_views,
        view_content,
        add_to_cart,
        initiate_checkout,
        max(order_count, purchase_events),
    ]
    funnel: list[FunnelStep] = []
    for index, (event_name, label) in enumerate(FUNNEL_EVENTS):
        count = funnel_values[index]
        prev = funnel_values[index - 1] if index > 0 else None
        rate = round((count / prev) * 100, 2) if prev and prev > 0 else None
        funnel.append(FunnelStep(event_name=event_name, label=label, count=count, rate_from_previous=rate))

    daily: list[DailyMetric] = []
    current = from_date
    while current <= to_date:
        day_start, day_end = _day_bounds(current, current)
        day_event_filters = [
            TrackingEvent.created_at >= day_start,
            TrackingEvent.created_at < day_end,
            TrackingEvent.event_name == "PageView",
        ]
        if morocco_only:
            day_event_filters.append(_morocco_event_filter())
        if exclude_ips:
            day_event_filters.append(or_(TrackingEvent.client_ip == None, TrackingEvent.client_ip.not_in(exclude_ips)))
        day_views = db.scalar(
            select(func.count()).select_from(TrackingEvent).where(*day_event_filters)
        ) or 0

        day_order_filters = [Order.created_at >= day_start, Order.created_at < day_end]
        if morocco_only:
            day_order_filters.append(_morocco_order_filter())
        if exclude_ips:
            day_order_filters.append(or_(Order.client_ip == None, Order.client_ip.not_in(exclude_ips)))
        day_orders = db.scalars(select(Order).where(*day_order_filters)).all()
        day_revenue = round(sum(float(order.total) for order in day_orders), 2)
        daily.append(
            DailyMetric(
                date=current,
                page_views=int(day_views),
                orders=len(day_orders),
                revenue=day_revenue,
            )
        )
        current += timedelta(days=1)

    product_stats: dict[str, ProductMetric] = {}
    for order in orders:
        for item in order.items:
            if item.is_upsell:
                continue
            key = item.product_id
            if key not in product_stats:
                product_stats[key] = ProductMetric(
                    product_id=item.product_id,
                    product_name=item.product_name,
                    orders=0,
                    quantity=0,
                    revenue=0.0,
                )
            product_stats[key].orders += 1
            product_stats[key].quantity += item.quantity
            product_stats[key].revenue = round(product_stats[key].revenue + float(item.line_total), 2)

    top_products = sorted(product_stats.values(), key=lambda row: row.revenue, reverse=True)[:5]

    return AdminMetricsResponse(
        from_date=from_date,
        to_date=to_date,
        morocco_only=morocco_only,
        page_views=page_views,
        view_content=view_content,
        add_to_cart=add_to_cart,
        initiate_checkout=initiate_checkout,
        orders=order_count,
        revenue=revenue,
        average_order_value=aov,
        conversion_rate=conversion_rate,
        checkout_conversion_rate=checkout_conversion_rate,
        upsell_orders=upsell_orders,
        upsell_rate=upsell_rate,
        pending_orders=status_counts["pending"],
        confirmed_orders=confirmed_orders,
        shipped_orders=status_counts["shipped"],
        delivered_orders=delivered_orders,
        cancelled_orders=cancelled_orders,
        confirmation_rate=confirmation_rate,
        delivery_rate=delivery_rate,
        cancellation_rate=cancellation_rate,
        funnel=funnel,
        daily=daily,
        top_products=top_products,
    )


def _order_has_sheet(db: Session, order_id: int) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(TrackingEvent)
            .where(
                TrackingEvent.order_id == order_id,
                TrackingEvent.event_name == "SheetNotify",
            )
        )
        or 0
    ) > 0


def _order_capi_platforms(db: Session, order_id: int) -> list[str]:
    row = db.scalar(
        select(TrackingEvent)
        .where(TrackingEvent.order_id == order_id, TrackingEvent.event_name == "Purchase")
        .order_by(TrackingEvent.id.desc())
        .limit(1)
    )
    if row is None or not row.platforms:
        return []
    return [part.strip() for part in row.platforms.split(",") if part.strip()]


def _to_summary(order: Order, sheet_sent: bool, capi_platforms: list[str] | None = None) -> AdminOrderSummary:
    return AdminOrderSummary(
        id=order.id,
        public_order_id=make_boya_order_id(order.id),
        event_id=order.event_id,
        customer_name=order.customer_name,
        phone=order.phone,
        total=float(order.total),
        status=order.status,
        client_ip=order.client_ip,
        country_code=order.country_code,
        has_upsell=any(item.is_upsell for item in order.items),
        sheet_sent=sheet_sent,
        created_at=order.created_at,
        item_count=len(order.items),
        capi_platforms=capi_platforms or [],
    )


def list_admin_orders(
    db: Session,
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
    search: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> AdminOrderListResponse:
    filters = []
    if status:
        filters.append(Order.status == status)
    if from_date:
        filters.append(Order.created_at >= datetime.combine(from_date, time.min))
    if to_date:
        filters.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), time.min))
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Order.customer_name.ilike(term),
                Order.phone.ilike(term),
                Order.event_id.ilike(term),
            )
        )

    total = db.scalar(select(func.count()).select_from(Order).where(*filters)) or 0
    pages = max(1, math.ceil(total / limit)) if total else 1
    page = min(max(page, 1), pages)
    offset = (page - 1) * limit

    orders = db.scalars(
        select(Order)
        .where(*filters)
        .options(joinedload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).unique().all()

    order_ids = [o.id for o in orders]
    platform_rows = db.execute(
        select(TrackingEvent.order_id, TrackingEvent.platforms)
        .where(
            TrackingEvent.order_id.in_(order_ids),
            TrackingEvent.event_name == "Purchase",
        )
        .distinct(TrackingEvent.order_id)
    ).all()
    platforms_by_order: dict[int, list[str]] = {}
    for row in platform_rows:
        if row.order_id and row.platforms:
            platforms_by_order[row.order_id] = [p.strip() for p in row.platforms.split(",") if p.strip()]

    items = [_to_summary(order, _order_has_sheet(db, order.id), platforms_by_order.get(order.id)) for order in orders]

    return AdminOrderListResponse(items=items, total=total, page=page, limit=limit, pages=pages)


def get_admin_order(db: Session, order_id: int) -> AdminOrderDetail | None:
    order = db.scalar(
        select(Order).where(Order.id == order_id).options(joinedload(Order.items))
    )
    if order is None:
        return None

    summary = _to_summary(order, _order_has_sheet(db, order.id))
    return AdminOrderDetail(
        **summary.model_dump(),
        admin_notes=order.admin_notes,
        updated_at=order.updated_at,
        items=[
            AdminOrderItem(
                product_id=item.product_id,
                product_name=item.product_name,
                offer=item.offer,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                line_total=float(item.line_total),
                is_upsell=item.is_upsell,
            )
            for item in order.items
        ],
        capi_platforms=_order_capi_platforms(db, order.id),
    )


def update_admin_order(
    db: Session,
    order_id: int,
    status: str | None = None,
    admin_notes: str | None = None,
) -> AdminOrderDetail | None:
    order = db.scalar(
        select(Order).where(Order.id == order_id).options(joinedload(Order.items))
    )
    if order is None:
        return None

    if status is not None:
        order.status = status
    if admin_notes is not None:
        order.admin_notes = admin_notes.strip() or None
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return get_admin_order(db, order_id)

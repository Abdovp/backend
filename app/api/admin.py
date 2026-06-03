from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_admin_user, get_db
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMetricsResponse,
    AdminOrderDetail,
    AdminOrderListResponse,
    AdminOrderUpdate,
)
from app.services.admin import get_admin_metrics, get_admin_order, list_admin_orders, update_admin_order
from app.services.auth import authenticate_admin, create_admin_token

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest):
    if not authenticate_admin(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token, expires = create_admin_token(payload.username)
    return AdminLoginResponse(token=token, expires_at=expires, username=payload.username)


@router.get("/me")
def admin_me(username: str = Depends(get_admin_user)):
    return {"username": username}


@router.get("/metrics", response_model=AdminMetricsResponse)
def admin_metrics(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    morocco_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    _username: str = Depends(get_admin_user),
):
    today = date.today()
    start = from_date or (today - timedelta(days=29))
    end = to_date or today
    if start > end:
        raise HTTPException(status_code=422, detail="'from' must be before 'to'")
    return get_admin_metrics(db, start, end, morocco_only=morocco_only)


@router.get("/orders", response_model=AdminOrderListResponse)
def admin_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    _username: str = Depends(get_admin_user),
):
    return list_admin_orders(
        db,
        page=page,
        limit=limit,
        status=status,
        search=search,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/orders/{order_id}", response_model=AdminOrderDetail)
def admin_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    _username: str = Depends(get_admin_user),
):
    order = get_admin_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/orders/{order_id}", response_model=AdminOrderDetail)
def admin_order_update(
    order_id: int,
    payload: AdminOrderUpdate,
    db: Session = Depends(get_db),
    _username: str = Depends(get_admin_user),
):
    if payload.status is None and payload.admin_notes is None:
        raise HTTPException(status_code=422, detail="Nothing to update")
    order = update_admin_order(db, order_id, payload.status, payload.admin_notes)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

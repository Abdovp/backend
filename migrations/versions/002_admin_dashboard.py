"""Admin dashboard fields: IP geo, order notes, indexes

Revision ID: 002_admin
Revises: 001_initial
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_admin"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("client_ip", sa.String(length=45), nullable=True))
    op.add_column("orders", sa.Column("country_code", sa.String(length=2), nullable=True))
    op.add_column("orders", sa.Column("admin_notes", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.create_index("ix_orders_country_code", "orders", ["country_code"], unique=False)
    op.create_index("ix_orders_created_at", "orders", ["created_at"], unique=False)
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)

    op.add_column("tracking_events", sa.Column("client_ip", sa.String(length=45), nullable=True))
    op.add_column("tracking_events", sa.Column("country_code", sa.String(length=2), nullable=True))
    op.create_index("ix_tracking_events_country_code", "tracking_events", ["country_code"], unique=False)
    op.create_index("ix_tracking_events_event_name_created_at", "tracking_events", ["event_name", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tracking_events_event_name_created_at", table_name="tracking_events")
    op.drop_index("ix_tracking_events_country_code", table_name="tracking_events")
    op.drop_column("tracking_events", "country_code")
    op.drop_column("tracking_events", "client_ip")

    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_country_code", table_name="orders")
    op.drop_column("orders", "updated_at")
    op.drop_column("orders", "admin_notes")
    op.drop_column("orders", "country_code")
    op.drop_column("orders", "client_ip")

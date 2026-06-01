-- Run this in pgweb → SQL if tables are missing and backend cannot migrate.
-- Safe to run on an empty database (uses IF NOT EXISTS where supported).

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) NOT NULL UNIQUE,
    customer_name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(32) NOT NULL,
    total NUMERIC(10, 2) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_orders_event_id ON orders (event_id);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id VARCHAR(64) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    offer INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL,
    line_total NUMERIC(10, 2) NOT NULL,
    is_upsell BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS tracking_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) NOT NULL,
    event_name VARCHAR(64) NOT NULL,
    order_id INTEGER REFERENCES orders(id),
    event_data TEXT,
    platforms TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_tracking_events_event_id ON tracking_events (event_id);

CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);

INSERT INTO alembic_version (version_num)
VALUES ('001_initial')
ON CONFLICT (version_num) DO NOTHING;

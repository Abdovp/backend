-- Run this AFTER migration_002_admin.sql to confirm the schema is ready.
-- Each query returns visible rows in pgweb.

-- 1) Alembic version (should be 002_admin)
SELECT version_num AS alembic_version FROM alembic_version;

-- 2) New columns on orders (expect 4 rows: client_ip, country_code, admin_notes, updated_at)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'orders'
  AND column_name IN ('client_ip', 'country_code', 'admin_notes', 'updated_at')
ORDER BY column_name;

-- 3) New columns on tracking_events (expect 2 rows: client_ip, country_code)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'tracking_events'
  AND column_name IN ('client_ip', 'country_code')
ORDER BY column_name;

-- 4) Indexes created by migration
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'ix_orders_country_code',
    'ix_orders_created_at',
    'ix_orders_status',
    'ix_tracking_events_country_code',
    'ix_tracking_events_event_name_created_at'
  )
ORDER BY indexname;

-- 5) Quick row counts
SELECT
  (SELECT COUNT(*) FROM orders) AS orders,
  (SELECT COUNT(*) FROM tracking_events) AS tracking_events,
  (SELECT COUNT(*) FROM tracking_events WHERE country_code = 'MA') AS morocco_events;

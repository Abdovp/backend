-- Admin dashboard migration (run in pgweb / psql)
-- NOTE: pgweb often shows "0 rows" for ALTER TABLE — that is normal.
-- Run migration_002_admin_verify.sql afterward to confirm.

-- ── orders ──
ALTER TABLE orders ADD COLUMN IF NOT EXISTS client_ip VARCHAR(45);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS country_code VARCHAR(2);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS admin_notes TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_orders_country_code ON orders (country_code);
CREATE INDEX IF NOT EXISTS ix_orders_created_at ON orders (created_at);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status);

-- ── tracking_events ──
ALTER TABLE tracking_events ADD COLUMN IF NOT EXISTS client_ip VARCHAR(45);
ALTER TABLE tracking_events ADD COLUMN IF NOT EXISTS country_code VARCHAR(2);

CREATE INDEX IF NOT EXISTS ix_tracking_events_country_code ON tracking_events (country_code);
CREATE INDEX IF NOT EXISTS ix_tracking_events_event_name_created_at ON tracking_events (event_name, created_at);

-- ── alembic version ──
UPDATE alembic_version SET version_num = '002_admin' WHERE version_num = '001_initial';
INSERT INTO alembic_version (version_num)
SELECT '002_admin'
WHERE NOT EXISTS (SELECT 1 FROM alembic_version WHERE version_num = '002_admin');

-- ── visible confirmation (run this block if pgweb only runs one statement at a time) ──
SELECT
  CASE
    WHEN EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name = 'orders' AND column_name = 'client_ip'
    ) THEN 'OK: orders.client_ip exists'
    ELSE 'MISSING: orders.client_ip'
  END AS orders_client_ip,
  CASE
    WHEN EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name = 'tracking_events' AND column_name = 'country_code'
    ) THEN 'OK: tracking_events.country_code exists'
    ELSE 'MISSING: tracking_events.country_code'
  END AS tracking_country_code,
  (SELECT version_num FROM alembic_version LIMIT 1) AS alembic_version;

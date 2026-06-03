-- Admin dashboard migration (run in pgweb / psql if Alembic cannot migrate)
-- Safe to run once on production after 001_initial.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS client_ip VARCHAR(45);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS country_code VARCHAR(2);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS admin_notes TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_orders_country_code ON orders (country_code);
CREATE INDEX IF NOT EXISTS ix_orders_created_at ON orders (created_at);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status);

ALTER TABLE tracking_events ADD COLUMN IF NOT EXISTS client_ip VARCHAR(45);
ALTER TABLE tracking_events ADD COLUMN IF NOT EXISTS country_code VARCHAR(2);

CREATE INDEX IF NOT EXISTS ix_tracking_events_country_code ON tracking_events (country_code);
CREATE INDEX IF NOT EXISTS ix_tracking_events_event_name_created_at ON tracking_events (event_name, created_at);

UPDATE alembic_version SET version_num = '002_admin'
WHERE version_num = '001_initial';

INSERT INTO alembic_version (version_num)
SELECT '002_admin'
WHERE NOT EXISTS (SELECT 1 FROM alembic_version);

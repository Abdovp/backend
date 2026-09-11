-- Reset admin dashboard metrics data (orders + tracking events).
-- WARNING: This permanently deletes order history and analytics events.
-- Run in pgweb or psql only when you are sure.

BEGIN;

TRUNCATE TABLE tracking_events, order_items, orders RESTART IDENTITY CASCADE;

COMMIT;

-- Verification counts (should all be 0)
SELECT
  (SELECT COUNT(*) FROM orders) AS orders,
  (SELECT COUNT(*) FROM order_items) AS order_items,
  (SELECT COUNT(*) FROM tracking_events) AS tracking_events;

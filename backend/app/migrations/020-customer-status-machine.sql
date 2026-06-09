-- 020-customer-status-machine.sql
-- Add customer status column with 7-state lifecycle machine.
-- new_lead → active → converted → vip | inactive → churned
-- Scheduled transitions run daily at 02:00 (APScheduler).

-- 1. Add status column
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'new_lead';

-- 2. Migrate existing lifecycle data to new status
--    Map common lifecycle values to new status enum
UPDATE customers
SET status = CASE
    WHEN lifecycle IN ('lead', 'prospect') THEN 'new_lead'
    WHEN lifecycle = 'active' THEN 'active'
    WHEN lifecycle IN ('customer', 'deal', 'done') THEN 'converted'
    WHEN lifecycle = 'vip' THEN 'vip'
    WHEN lifecycle IN ('dormant', 'sleeping', 'inactive') THEN 'inactive'
    WHEN lifecycle IN ('churned', 'lost', 'dead') THEN 'churned'
    ELSE 'new_lead'
END
WHERE deleted_at IS NULL;

-- 3. Index for scheduler queries
CREATE INDEX IF NOT EXISTS ix_customers_status_interaction
    ON customers (status, last_contacted_at)
    WHERE deleted_at IS NULL;

-- 4. Index for VIP revenue queries
CREATE INDEX IF NOT EXISTS ix_sales_orders_customer_completed
    ON sales_orders (customer_id, order_date, total_amount)
    WHERE deleted_at IS NULL AND status = 'completed';

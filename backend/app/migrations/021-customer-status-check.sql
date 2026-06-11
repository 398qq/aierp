-- 021-customer-status-check.sql
-- Add CHECK constraint to enforce valid status values at the database level.
-- Complements the application-layer state machine in domain/states/sales.py.

-- 1. Add CHECK constraint for customer status column
ALTER TABLE customers
    ADD CONSTRAINT ck_customers_status
    CHECK (status IN ('new_lead', 'active', 'converted', 'vip', 'inactive', 'churned'));

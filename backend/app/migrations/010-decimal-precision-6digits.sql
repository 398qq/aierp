-- Migration: Increase decimal precision to 6 decimal places
-- Date: 2026-05-25
-- Description: Change all DECIMAL(15,2) and DECIMAL(12,4) columns to DECIMAL(20,6)

-- Purchase Orders
ALTER TABLE purchase_orders ALTER COLUMN total_amount TYPE DECIMAL(20,6);
ALTER TABLE purchase_order_items ALTER COLUMN unit_price TYPE DECIMAL(20,6);
ALTER TABLE purchase_order_items ALTER COLUMN amount TYPE DECIMAL(20,6);

-- Payments
ALTER TABLE payments ALTER COLUMN amount TYPE DECIMAL(20,6);

-- Sales - Opportunities
ALTER TABLE opportunities ALTER COLUMN amount TYPE DECIMAL(20,6);

-- Sales - Quotations
ALTER TABLE quotations ALTER COLUMN total_amount TYPE DECIMAL(20,6);
ALTER TABLE quotation_items ALTER COLUMN unit_price TYPE DECIMAL(20,6);
ALTER TABLE quotation_items ALTER COLUMN total_price TYPE DECIMAL(20,6);

-- Sales - Sales Orders
ALTER TABLE sales_orders ALTER COLUMN total_amount TYPE DECIMAL(20,6);
ALTER TABLE sales_order_items ALTER COLUMN unit_price TYPE DECIMAL(20,6);
ALTER TABLE sales_order_items ALTER COLUMN total_price TYPE DECIMAL(20,6);

-- Finance - Payment Records
ALTER TABLE payment_records ALTER COLUMN amount TYPE DECIMAL(20,6);

-- Finance - Invoices
ALTER TABLE invoices ALTER COLUMN amount TYPE DECIMAL(20,6);
ALTER TABLE invoices ALTER COLUMN tax_amount TYPE DECIMAL(20,6);

-- Finance - Sales Targets
ALTER TABLE sales_targets ALTER COLUMN target_amount TYPE DECIMAL(20,6);
ALTER TABLE sales_targets ALTER COLUMN actual_amount TYPE DECIMAL(20,6);

-- Finance - Contracts
ALTER TABLE contracts ALTER COLUMN amount TYPE DECIMAL(20,6);

-- Accounting - Journal Entry Lines
ALTER TABLE journal_entry_lines ALTER COLUMN debit TYPE DECIMAL(20,6);
ALTER TABLE journal_entry_lines ALTER COLUMN credit TYPE DECIMAL(20,6);

-- Accounting - Bank Reconciliations
ALTER TABLE bank_reconciliations ALTER COLUMN bank_amount TYPE DECIMAL(20,6);
ALTER TABLE bank_reconciliations ALTER COLUMN difference TYPE DECIMAL(20,6);

-- Approvals
ALTER TABLE approval_rules ALTER COLUMN min_amount TYPE DECIMAL(20,6);

-- Products - Supplier Products
ALTER TABLE supplier_products ALTER COLUMN cost_price TYPE DECIMAL(20,6);

-- Inventory
ALTER TABLE inventories ALTER COLUMN unit_price TYPE DECIMAL(20,6);

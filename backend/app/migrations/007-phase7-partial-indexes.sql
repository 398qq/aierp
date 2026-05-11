-- Migration 007: Partial indexes for soft-delete performance
-- Every query filters deleted_at IS NULL; without partial indexes, all rows (including deleted) are scanned.
-- Partial indexes exclude deleted rows, shrinking index size and improving query speed.

-- High-traffic tables: frequent list/filter queries
CREATE INDEX IF NOT EXISTS idx_customers_active ON customers (id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customers_status_active ON customers (status, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customers_level_active ON customers (level) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_products_active ON products (id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_products_sku_active ON products (sku) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_products_brand_active ON products (brand_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_opportunities_active ON opportunities (status, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_opportunities_customer_active ON opportunities (customer_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_opportunities_assigned_active ON opportunities (assigned_to) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_quotations_active ON quotations (status, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quotations_customer_active ON quotations (customer_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_sales_orders_active ON sales_orders (status, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_orders_customer_active ON sales_orders (customer_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_delivery_notes_active ON delivery_notes (status, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_delivery_notes_order_active ON delivery_notes (sales_order_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_invoices_active ON invoices (status, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_invoices_customer_active ON invoices (customer_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_purchase_orders_active ON purchase_orders (status, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_active ON purchase_orders (supplier_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_tickets_active ON tickets (status, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tickets_assigned_active ON tickets (assigned_to) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_suppliers_active ON suppliers (id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_brands_active ON brands (id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_warehouses_active ON warehouses (id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_inventories_active ON inventories (product_id, warehouse_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_active ON inventory_transactions (product_id, created_at DESC) WHERE deleted_at IS NULL;

-- RBAC tables
CREATE INDEX IF NOT EXISTS idx_permissions_active ON permissions (resource, action) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_roles_active ON roles (id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_audit_logs_active ON audit_logs (created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_active ON audit_logs (user_id, created_at DESC) WHERE deleted_at IS NULL;

-- Customer-related tables
CREATE INDEX IF NOT EXISTS idx_customer_contacts_active ON customer_contacts (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customer_follow_ups_active ON customer_follow_ups (customer_id, due_date) WHERE deleted_at IS NULL;

-- Notifications and approvals
CREATE INDEX IF NOT EXISTS idx_notifications_active ON notifications (user_id, is_read, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_approval_requests_active ON approval_requests (status, created_at DESC) WHERE deleted_at IS NULL;

-- Sales/Finance auxiliary tables
CREATE INDEX IF NOT EXISTS idx_sales_targets_active ON sales_targets (period) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_payment_records_active ON payment_records (invoice_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_contracts_active ON contracts (customer_id) WHERE deleted_at IS NULL;

-- Account tables
CREATE INDEX IF NOT EXISTS idx_accounts_active ON accounts (id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_journal_entries_active ON journal_entries (account_id, created_at DESC) WHERE deleted_at IS NULL;

-- Foreign key indexes for frequently joined tables
CREATE INDEX IF NOT EXISTS idx_quotation_items_quote ON quotation_items (quotation_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_order_items_order ON sales_order_items (order_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_delivery_note_items_note ON delivery_note_items (delivery_note_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_order ON purchase_order_items (order_id) WHERE deleted_at IS NULL;

-- Inquiries
CREATE INDEX IF NOT EXISTS idx_inquiries_active ON inquiries (status, created_at DESC) WHERE deleted_at IS NULL;

-- AIERP critical database indexes
-- Adds missing indexes on hot-path query columns to prevent full table scans
-- Generated as part of the 30-day ERP hardening roadmap

-- ============================================================
-- Sales tables
-- ============================================================

-- Opportunities: filter by customer, status, stage
CREATE INDEX IF NOT EXISTS idx_opportunities_customer_id
  ON opportunities (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_opportunities_status
  ON opportunities (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_opportunities_stage
  ON opportunities (stage) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_opportunities_assigned_to
  ON opportunities (assigned_to) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_opportunities_created_at
  ON opportunities (created_at DESC);

-- Quotations: filter by customer, status, opportunity
CREATE INDEX IF NOT EXISTS idx_quotations_customer_id
  ON quotations (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quotations_status
  ON quotations (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quotations_opportunity_id
  ON quotations (opportunity_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quotations_valid_until
  ON quotations (valid_until) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quotations_quotation_no
  ON quotations (quotation_no) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quotations_created_at
  ON quotations (created_at DESC);

-- Quotation items: filter by quotation, product
CREATE INDEX IF NOT EXISTS idx_quotation_items_quotation_id
  ON quotation_items (quotation_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quotation_items_product_id
  ON quotation_items (product_id) WHERE deleted_at IS NULL;

-- Sales orders: filter by customer, status, quotation
CREATE INDEX IF NOT EXISTS idx_sales_orders_customer_id
  ON sales_orders (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_orders_status
  ON sales_orders (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_orders_quotation_id
  ON sales_orders (quotation_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_orders_order_no
  ON sales_orders (order_no) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_orders_order_date
  ON sales_orders (order_date DESC);
CREATE INDEX IF NOT EXISTS idx_sales_orders_created_at
  ON sales_orders (created_at DESC);

-- Sales order items: filter by order, product
CREATE INDEX IF NOT EXISTS idx_sales_order_items_order_id
  ON sales_order_items (order_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_order_items_product_id
  ON sales_order_items (product_id) WHERE deleted_at IS NULL;

-- Delivery notes: filter by sales_order, customer, status
CREATE INDEX IF NOT EXISTS idx_delivery_notes_sales_order_id
  ON delivery_notes (sales_order_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_delivery_notes_customer_id
  ON delivery_notes (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_delivery_notes_status
  ON delivery_notes (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_delivery_notes_delivery_no
  ON delivery_notes (delivery_no) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_delivery_notes_delivery_date
  ON delivery_notes (delivery_date DESC);

-- Delivery note items
CREATE INDEX IF NOT EXISTS idx_delivery_note_items_delivery_note_id
  ON delivery_note_items (delivery_note_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_delivery_note_items_product_id
  ON delivery_note_items (product_id) WHERE deleted_at IS NULL;

-- Inquiries
CREATE INDEX IF NOT EXISTS idx_inquiries_customer_id
  ON inquiries (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_inquiries_status
  ON inquiries (status) WHERE deleted_at IS NULL;

-- ============================================================
-- Customer / Product master data
-- ============================================================

-- Customers
CREATE INDEX IF NOT EXISTS idx_customers_code
  ON customers (code) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customers_name
  ON customers (name) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customers_level
  ON customers (level) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customers_owner
  ON customers (owner) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customers_industry
  ON customers (industry) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customers_region
  ON customers (region) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customers_last_contacted_at
  ON customers (last_contacted_at DESC NULLS LAST) WHERE deleted_at IS NULL;

-- Customer contacts
CREATE INDEX IF NOT EXISTS idx_customer_contacts_customer_id
  ON customer_contacts (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customer_contacts_phone
  ON customer_contacts (phone) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customer_contacts_email
  ON customer_contacts (email) WHERE deleted_at IS NULL;

-- Customer follow ups
CREATE INDEX IF NOT EXISTS idx_customer_follow_ups_customer_id
  ON customer_follow_ups (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customer_follow_ups_assigned_to
  ON customer_follow_ups (assigned_to) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customer_follow_ups_planned_at
  ON customer_follow_ups (planned_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customer_follow_ups_status
  ON customer_follow_ups (status) WHERE deleted_at IS NULL;

-- Customer tags links
CREATE INDEX IF NOT EXISTS idx_customer_tag_links_tag_id
  ON customer_tag_links (tag_id);

-- Customer logs
CREATE INDEX IF NOT EXISTS idx_customer_logs_customer_id
  ON customer_logs (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customer_logs_created_at
  ON customer_logs (created_at DESC);

-- Alert events / rules
CREATE INDEX IF NOT EXISTS idx_alert_events_rule_id
  ON alert_events (rule_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_alert_events_customer_id
  ON alert_events (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_alert_events_is_resolved
  ON alert_events (is_resolved) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled
  ON alert_rules (enabled) WHERE deleted_at IS NULL;

-- ============================================================
-- Products
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_products_sku
  ON products (sku) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_products_name
  ON products (name) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_products_brand_id
  ON products (brand_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_products_category
  ON products (category) WHERE deleted_at IS NULL;

-- Inventory: hot path for reservation / deduction
CREATE INDEX IF NOT EXISTS idx_inventories_product_id
  ON inventories (product_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_inventories_warehouse_id
  ON inventories (warehouse_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_inventories_quantity
  ON inventories (product_id, warehouse_id, quantity) WHERE deleted_at IS NULL;

-- Inventory transactions
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_product_id
  ON inventory_transactions (product_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_warehouse_id
  ON inventory_transactions (warehouse_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_type
  ON inventory_transactions (type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_created_at
  ON inventory_transactions (created_at DESC);

-- Supplier products
CREATE INDEX IF NOT EXISTS idx_supplier_products_supplier_id
  ON supplier_products (supplier_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_supplier_products_product_id
  ON supplier_products (product_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_supplier_products_is_preferred
  ON supplier_products (is_preferred) WHERE deleted_at IS NULL;

-- Brands
CREATE INDEX IF NOT EXISTS idx_brands_code
  ON brands (code) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_brands_status
  ON brands (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_brands_brand_type
  ON brands (brand_type) WHERE deleted_at IS NULL;

-- Suppliers
CREATE INDEX IF NOT EXISTS idx_suppliers_name
  ON suppliers (name) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_suppliers_supplier_type
  ON suppliers (supplier_type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_suppliers_region
  ON suppliers (region) WHERE deleted_at IS NULL;

-- ============================================================
-- Procurement
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_id
  ON purchase_orders (supplier_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_purchase_orders_status
  ON purchase_orders (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_purchase_orders_order_no
  ON purchase_orders (order_no) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_purchase_orders_expected_date
  ON purchase_orders (expected_date);

CREATE INDEX IF NOT EXISTS idx_purchase_order_items_order_id
  ON purchase_order_items (order_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_product_id
  ON purchase_order_items (product_id) WHERE deleted_at IS NULL;

-- Payments (transaction.py)
CREATE INDEX IF NOT EXISTS idx_payments_customer_id
  ON payments (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_payments_supplier_id
  ON payments (supplier_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_payments_paid_at
  ON payments (paid_at DESC);
CREATE INDEX IF NOT EXISTS idx_payments_type
  ON payments (type) WHERE deleted_at IS NULL;

-- Tickets / visits / samples
CREATE INDEX IF NOT EXISTS idx_tickets_customer_id
  ON tickets (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tickets_assigned_to
  ON tickets (assigned_to) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tickets_status
  ON tickets (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tickets_priority
  ON tickets (priority) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_visits_customer_id
  ON visits (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_visits_contact_id
  ON visits (contact_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_visits_visit_date
  ON visits (visit_date DESC);
CREATE INDEX IF NOT EXISTS idx_visits_assigned_to
  ON visits (assigned_to) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_samples_customer_id
  ON samples (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_samples_product_id
  ON samples (product_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_samples_status
  ON samples (status) WHERE deleted_at IS NULL;

-- ============================================================
-- Finance
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_payment_records_sales_order_id
  ON payment_records (sales_order_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_payment_records_customer_id
  ON payment_records (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_payment_records_delivery_note_id
  ON payment_records (delivery_note_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_payment_records_status
  ON payment_records (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_payment_records_payment_date
  ON payment_records (payment_date DESC);

CREATE INDEX IF NOT EXISTS idx_invoices_sales_order_id
  ON invoices (sales_order_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_invoices_customer_id
  ON invoices (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_invoices_status
  ON invoices (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_no
  ON invoices (invoice_no) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_date
  ON invoices (invoice_date DESC);

CREATE INDEX IF NOT EXISTS idx_sales_targets_user_id
  ON sales_targets (user_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_targets_period
  ON sales_targets (period) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_targets_status
  ON sales_targets (status) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_contracts_customer_id
  ON contracts (customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_contracts_status
  ON contracts (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_contracts_expire_date
  ON contracts (expire_date);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id
  ON notifications (user_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notifications_is_read
  ON notifications (is_read) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notifications_type
  ON notifications (type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notifications_created_at
  ON notifications (created_at DESC);

-- ============================================================
-- Accounting (Phase 6)
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_journal_entries_entry_date
  ON journal_entries (entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_journal_entries_status
  ON journal_entries (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_entry_id
  ON journal_entry_lines (entry_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_account_id
  ON journal_entry_lines (account_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_bank_reconciliations_payment_id
  ON bank_reconciliations (payment_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_bank_reconciliations_reconciled_at
  ON bank_reconciliations (reconciled_at DESC);

-- ============================================================
-- Approval & Audit
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_approval_rules_doc_type
  ON approval_rules (doc_type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_approval_rules_enabled
  ON approval_rules (enabled) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_approval_requests_status
  ON approval_requests (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_approval_requests_doc_type_id
  ON approval_requests (doc_type, doc_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_submitter_id
  ON approval_requests (submitter_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_approval_actions_request_id
  ON approval_actions (request_id);
CREATE INDEX IF NOT EXISTS idx_approval_actions_approver_id
  ON approval_actions (approver_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id
  ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource
  ON audit_logs (resource, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action
  ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at
  ON audit_logs (created_at DESC);

-- ============================================================
-- User / RBAC
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
  ON users (username) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_role
  ON users (role) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_is_active
  ON users (is_active) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id
  ON user_roles (user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id
  ON user_roles (role_id);

CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id
  ON role_permissions (role_id);

-- ============================================================
-- Documents & dashboards
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_documents_entity
  ON documents (entity_type, entity_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by
  ON documents (uploaded_by) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_user_id
  ON dashboard_widgets (user_id) WHERE deleted_at IS NULL;

-- Integration configs
CREATE INDEX IF NOT EXISTS idx_integration_configs_type
  ON integration_configs (type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_integration_configs_enabled
  ON integration_configs (enabled) WHERE deleted_at IS NULL;

-- Report templates
CREATE INDEX IF NOT EXISTS idx_report_templates_user_id
  ON report_templates (user_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_report_templates_type
  ON report_templates (report_type) WHERE deleted_at IS NULL;

-- Analyze critical tables to verify planner can use indexes
ANALYZE opportunities;
ANALYZE quotations;
ANALYZE sales_orders;
ANALYZE delivery_notes;
ANALYZE customers;
ANALYZE products;
ANALYZE inventories;
ANALYZE payment_records;
ANALYZE invoices;

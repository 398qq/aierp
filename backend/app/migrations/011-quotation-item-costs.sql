ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS cost_price DECIMAL(20,6);
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS untaxed_cost DECIMAL(20,6);
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS taxed_cost DECIMAL(20,6);
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS sales_profit DECIMAL(20,6);

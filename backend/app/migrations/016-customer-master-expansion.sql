-- 016: Customer master data expansion — professional B2B ERP fields
BEGIN;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS website             VARCHAR(500);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS tax_id              VARCHAR(50);     -- 纳税人识别号
ALTER TABLE customers ADD COLUMN IF NOT EXISTS registration_number VARCHAR(50);     -- 统一社会信用代码
ALTER TABLE customers ADD COLUMN IF NOT EXISTS invoice_title       VARCHAR(255);    -- 发票抬头
ALTER TABLE customers ADD COLUMN IF NOT EXISTS invoice_address     TEXT;            -- 发票地址
ALTER TABLE customers ADD COLUMN IF NOT EXISTS bank_name           VARCHAR(255);    -- 开户行
ALTER TABLE customers ADD COLUMN IF NOT EXISTS bank_account        VARCHAR(50);     -- 银行账号
ALTER TABLE customers ADD COLUMN IF NOT EXISTS price_tier          VARCHAR(20);     -- 价格等级
ALTER TABLE customers ADD COLUMN IF NOT EXISTS annual_revenue      DOUBLE PRECISION;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS employee_count      INTEGER;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS payment_terms       VARCHAR(100);    -- Net 30 / 月结30天
ALTER TABLE customers ADD COLUMN IF NOT EXISTS payment_method      VARCHAR(50);     -- T/T / L/C
ALTER TABLE customers ADD COLUMN IF NOT EXISTS currency            VARCHAR(3)  NOT NULL DEFAULT 'CNY';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS delivery_address    TEXT;            -- 收货地址
ALTER TABLE customers ADD COLUMN IF NOT EXISTS default_incoterm    VARCHAR(20);     -- FOB / CIF / EXW

CREATE INDEX IF NOT EXISTS idx_customers_tax_id   ON customers (tax_id)    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customers_currency ON customers (currency)  WHERE deleted_at IS NULL;

COMMIT;

-- 025: Unit of Measure dictionary + product packaging levels
BEGIN;

-- ============================================================
-- 1. 计量单位字典表（含计数单位 + 包装单位）
-- ============================================================
CREATE TABLE IF NOT EXISTS uom_dict (
    code        VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,
    uom_type    VARCHAR(20) NOT NULL DEFAULT 'count',   -- count / package
    category    VARCHAR(30),
    description TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    deleted_at  TIMESTAMPTZ
);

-- 计数单位（uom_type = 'count'）
INSERT INTO uom_dict (code, name, uom_type, category, sort_order) VALUES
    ('PCS',      '个',     'count', 'count',     1),
    ('PC',       '只',     'count', 'count',     2),
    ('EA',       '件',     'count', 'count',     3),
    ('SET',      '套',     'count', 'count',     4),
    ('PAIR',     '对',     'count', 'count',     5),
    ('UNIT',     '台',     'count', 'unit',      6),
    ('SHEET',    '张',     'count', 'sheet',     7),
    ('ROLL',     '卷',     'count', 'roll',      8),
    ('LOT',      '批',     'count', 'batch',     9),
    ('GROUP',    '组',     'count', 'count',    10),
    ('CARD',     '卡',     'count', 'unit',     11),
    ('BOARD',    '板',     'count', 'unit',     12),
    ('MODULE',   '模组',   'count', 'unit',     13);

-- 包装单位（uom_type = 'package'）
INSERT INTO uom_dict (code, name, uom_type, category, sort_order) VALUES
    ('BULK',         '散装',     'package', 'bulk',         20),
    ('REEL',         '盘装',     'package', 'reel',         21),
    ('TAPE',         '编带',     'package', 'tape',         22),
    ('TUBE',         '管装',     'package', 'tube',         23),
    ('TRAY',         '托盘装',   'package', 'tray',         24),
    ('BOX',          '盒装',     'package', 'box',          25),
    ('BAG',          '袋装',     'package', 'bag',          26),
    ('CARTON',       '箱装',     'package', 'carton',       27),
    ('WAFFLE_PACK',  '华夫盒',   'package', 'tray',         28),
    ('WAFER_BOX',    '晶圆盒',   'package', 'box',          29),
    ('FULL_REEL',    '整盘',     'package', 'reel',         30),
    ('PARTIAL_REEL', '零盘',     'package', 'reel',         31),
    ('FULL_PACK',    '整包',     'package', 'pack',         32),
    ('LOOSE',        '零散',     'package', 'loose',        33),
    ('PKG',          '包',       'package', 'pack',         34),
    ('BDL',          '捆',       'package', 'bundle',       35),
    ('CAN',          '罐',       'package', 'container',    36),
    ('BTL',          '瓶',       'package', 'container',    37),
    ('DRUM',         '桶',       'package', 'container',    38),
    ('MPQ',          '最小包装', 'package', NULL,           39),
    ('SPQ',          '标准包装', 'package', NULL,           40);

-- ============================================================
-- 2. 产品包装层级表
-- ============================================================
CREATE TABLE IF NOT EXISTS product_pack_levels (
    id              BIGSERIAL PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    uom_code        VARCHAR(10) NOT NULL REFERENCES uom_dict(code),
    pack_level      SMALLINT NOT NULL CHECK (pack_level BETWEEN 0 AND 2),
    qty_per_parent  DECIMAL(18, 4) NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ppl_product_level
    ON product_pack_levels(product_id, pack_level) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_ppl_product
    ON product_pack_levels(product_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_ppl_uom
    ON product_pack_levels(uom_code) WHERE deleted_at IS NULL;

COMMIT;

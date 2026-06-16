"""
leads_pipeline/run_leads.py
潜在客户自动化管道 - 主入口

用法:
  # Step 1: AI 抓取模式（AI 用 web_search / tyc-mcp 跑后写 raw_leads_*.json）
  python3 run_leads.py ingest --file raw_leads_cjc8988_2026-06-14.json
  python3 run_leads.py ingest --file raw_leads_hk32_2026-06-14.json
  python3 run_leads.py ingest --file raw_leads_qmi8658b_2026-06-14.json
  
  # Step 2: 生成周报
  python3 run_leads.py digest
  
  # Step 3: 一键跑（聚合所有积压 raw_* 文件）
  python3 run_leads.py run-all --note "第一批试跑"
"""
import os
import re
import sys
import json
import time
import argparse
import psycopg2
import psycopg2.extras
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

# DB config
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "aierp",
    "password": "aierp",
    "dbname": "aierp",
}

# 加载 ERP .env
os.environ.setdefault("DB_PASSWORD", "aierp")
try:
    with open("/home/ttdiy/aierp/backend/.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
except FileNotFoundError:
    pass

DB_CONFIG["password"] = os.environ.get("DB_PASSWORD", "aierp")
DB_CONFIG["host"] = os.environ.get("DB_HOST", "localhost")
DB_CONFIG["port"] = int(os.environ.get("DB_PORT", "5432"))
DB_CONFIG["user"] = os.environ.get("DB_USER", "aierp")
DB_CONFIG["dbname"] = os.environ.get("DB_NAME", "aierp")

RAW_DIR = Path("/home/ttdiy/aierp/leads_pipeline/raw")
RAW_DIR.mkdir(exist_ok=True)
DIGEST_DIR = Path("/home/ttdiy/.openclaw/workspace/1_业务开发/机会池/周报")
DIGEST_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 数据库工具
# ============================================================
def db_conn():
    return psycopg2.connect(**DB_CONFIG)


def get_existing_customer_names() -> set:
    """从 ERP 拉所有客户名（含简称）"""
    conn = db_conn()
    names = set()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, short_name, code FROM customers
                WHERE deleted_at IS NULL
            """)
            for r in cur.fetchall():
                n, s, c = r
                if n: names.add(n.strip())
                if s: names.add(s.strip())
                if c: names.add(c.strip())
    finally:
        conn.close()
    return names


def get_product_by_sku(sku: str) -> Optional[Dict]:
    conn = db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT p.id, p.sku, p.name, b.name as brand
                FROM products p LEFT JOIN brands b ON p.brand_id = b.id
                WHERE p.sku ILIKE %s AND p.deleted_at IS NULL
                LIMIT 1
            """, (f"%{sku}%",))
            return cur.fetchone()
    finally:
        conn.close()


def insert_potential_customer(lead: Dict) -> int:
    conn = db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO potential_customers (
                    name, short_name, region, industry, estimated_size,
                    registered_capital, source, source_url, discovery_query,
                    source_signals, target_product_ids, target_product_skus,
                    recommended_brands, contact_name, contact_title, contact_phone,
                    contact_email, confidence_score, weekly_digest_id, notes
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING
                RETURNING id
            """, (
                lead.get("name"),
                lead.get("short_name"),
                lead.get("region"),
                lead.get("industry"),
                lead.get("estimated_size"),
                lead.get("registered_capital"),
                lead.get("source"),
                lead.get("source_url"),
                lead.get("discovery_query"),
                json.dumps(lead.get("source_signals", {}), ensure_ascii=False),
                json.dumps(lead.get("target_product_ids", [])),
                json.dumps(lead.get("target_product_skus", [])),
                json.dumps(lead.get("recommended_brands", [])),
                lead.get("contact_name"),
                lead.get("contact_title"),
                lead.get("contact_phone"),
                lead.get("contact_email"),
                lead.get("confidence_score", 0.5),
                lead.get("weekly_digest_id"),
                lead.get("notes"),
            ))
            row = cur.fetchone()
            conn.commit()
            return row[0] if row else -1
    finally:
        conn.close()


def get_potential_customers(status: str = "pending", digest_id: Optional[str] = None) -> List[Dict]:
    conn = db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if digest_id:
                cur.execute("""
                    SELECT * FROM potential_customers
                    WHERE status = %s AND weekly_digest_id = %s
                    ORDER BY confidence_score DESC, created_at DESC
                """, (status, digest_id))
            else:
                cur.execute("""
                    SELECT * FROM potential_customers
                    WHERE status = %s
                    ORDER BY confidence_score DESC, created_at DESC
                """, (status,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def create_digest_record(digest_id: str, products: List[str], sources: List[str],
                         raw_count: int, dedup_count: int, new_count: int, report_path: str) -> int:
    conn = db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO weekly_digests (
                    digest_id, period_start, period_end, products_covered, sources_run,
                    raw_leads_count, deduped_count, new_to_erp_count, report_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (digest_id) DO UPDATE SET
                    raw_leads_count = EXCLUDED.raw_leads_count,
                    deduped_count = EXCLUDED.deduped_count,
                    new_to_erp_count = EXCLUDED.new_to_erp_count,
                    report_path = EXCLUDED.report_path
                RETURNING id
            """, (
                digest_id, date.today(), date.today(),
                json.dumps(products), json.dumps(sources),
                raw_count, dedup_count, new_count, report_path,
            ))
            row = cur.fetchone()
            conn.commit()
            return row[0] if row else -1
    finally:
        conn.close()


# ============================================================
# 命令: ingest
# ============================================================
def cmd_ingest(args):
    """从 raw_leads_*.json 文件入库到 potential_customers"""
    if not args.file.exists():
        print(f"❌ File not found: {args.file}")
        return 1
    
    print(f"📥 Ingesting: {args.file}")
    data = json.loads(args.file.read_text(encoding="utf-8"))
    print(f"   target_sku in file: {data.get('target_sku', 'MISSING')}")
    
    digest_id = args.digest_id or f"WD-{date.today().isoformat()}"
    
    # 加载 ERP 已有客户
    print("🔍 Loading ERP customer names for dedup...")
    existing = get_existing_customer_names()
    print(f"   ERP has {len(existing)} names")
    
    raw_count = 0
    new_count = 0
    dup_count = 0
    
    for lead in data.get("leads", []):
        raw_count += 1
        name = lead.get("name", "").strip()
        if not name:
            continue
        
        # 去重检查
        name_norm = re.sub(r'(深圳市|广州市|东莞市|广东|科技|公司|有限公司|有限|责任)', '', name)
        is_dup = False
        for ex in existing:
            ex_norm = re.sub(r'(深圳市|广州市|东莞市|广东|科技|公司|有限公司|有限|责任)', '', ex)
            if len(name_norm) >= 4 and (name_norm in ex_norm or ex_norm in name_norm):
                is_dup = True
                break
        
        if is_dup:
            dup_count += 1
            continue
        
        # 关联产品（用 SKU 模糊匹配，因为 raw 文件可能写 CJC8988 短码）
        sku = data.get("target_sku", "")
        if sku:
            prod = get_product_by_sku(sku)
            if prod:
                lead["target_product_ids"] = [prod["id"]]
                lead["target_product_skus"] = [prod["sku"]]
                lead["recommended_brands"] = [prod["brand"]]
            else:
                # 找不到对应产品，存原始 SKU 字符串
                lead["target_product_skus"] = [sku]
        
        lead["weekly_digest_id"] = digest_id
        # source_signals: 保留源链接 + 标记 target_sku（不覆盖 raw 文件里的源字段）
        signals = lead.get("source_signals") or {}
        if not isinstance(signals, dict):
            signals = {}
        if data.get("target_sku"):
            signals["target_sku"] = data["target_sku"]
        signals["source_url"] = lead.get("source_url", "")
        signals["source_name"] = data.get("source", "unknown")
        lead["source_signals"] = signals
        
        pid = insert_potential_customer(lead)
        if pid > 0:
            new_count += 1
            print(f"  ✅ [{pid}] {name} → {lead.get('region', '?')}")
        else:
            dup_count += 1
    
    print(f"\n📊 Ingest 汇总:")
    print(f"   原始: {raw_count}")
    print(f"   新增: {new_count}")
    print(f"   跳过(重复/已存): {dup_count}")
    return 0


# ============================================================
# 命令: digest
# ============================================================
def cmd_digest(args):
    """生成周报 Markdown"""
    digest_id = args.digest_id or f"WD-{date.today().isoformat()}"
    
    print(f"📊 Generating digest: {digest_id}")
    leads = get_potential_customers(status="pending", digest_id=digest_id)
    
    if not leads:
        print(f"⚠️ No pending leads for {digest_id}")
        return 1
    
    # 按产品分组
    by_product: Dict[str, List[Dict]] = {}
    for lead in leads:
        skus = lead.get("target_product_skus") or ["未知"]
        for sku in skus:
            by_product.setdefault(sku, []).append(lead)
    
    # 按规模分梯队
    def tier(emp_str):
        if not emp_str: return "🥉"
        n = re.search(r'(\d+)', emp_str)
        if not n: return "🥉"
        n = int(n.group(1))
        if n >= 200: return "🥇"
        if n >= 50: return "🥈"
        return "🥉"
    
    # 写报告
    report_path = DIGEST_DIR / f"{digest_id}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# {digest_id} 潜在客户周报\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**总线索数**: {len(leads)}\n\n")
        f.write(f"---\n\n")
        
        for sku, items in by_product.items():
            f.write(f"## 📦 料号: {sku}\n\n")
            f.write(f"**线索数**: {len(items)}\n\n")
            f.write(f"| # | 梯队 | 公司 | 地区 | 规模 | 联系人 | 电话 | 来源 | 置信度 | 备注 |\n")
            f.write(f"|---|---|---|---|---|---|---|---|---|---|\n")
            for i, lead in enumerate(items, 1):
                f.write(f"| {i} | {tier(lead.get('estimated_size', ''))} | "
                       f"{lead.get('name', '')} | {lead.get('region', '')} | "
                       f"{lead.get('estimated_size', '')} | "
                       f"{lead.get('contact_name', '')} | {lead.get('contact_phone', '')} | "
                       f"{lead.get('source', '')} | "
                       f"{lead.get('confidence_score', '')} | "
                       f"{(lead.get('notes', '') or '')[:50]} |\n")
            f.write(f"\n")
    
    # 更新周报记录
    sources_used = list(set(l.get("source", "") for l in leads))
    products_used = list(by_product.keys())
    create_digest_record(
        digest_id, products_used, sources_used,
        raw_count=len(leads), dedup_count=len(leads), new_count=len(leads),
        report_path=str(report_path),
    )
    
    print(f"✅ 报告已生成: {report_path}")
    print(f"   料号: {len(products_used)} 个")
    print(f"   线索: {len(leads)} 条")
    return 0


# ============================================================
# 命令: run-all
# ============================================================
def cmd_run_all(args):
    """一键跑：扫描 raw/ 下所有 raw_*.json，按顺序 ingest + digest"""
    files = sorted(RAW_DIR.glob("raw_*.json"))
    if not files:
        print(f"⚠️ No raw files in {RAW_DIR}")
        return 1
    
    print(f"📋 找到 {len(files)} 个原始文件")
    for f in files:
        print(f"   - {f.name}")
    
    digest_id = f"WD-{date.today().isoformat()}"
    
    for f in files:
        # 解析文件名约定: raw_<sku>_<date>.json
        # raw_leads_cjc8988_2026-06-14.json
        m = re.match(r"raw_(?:leads_)?(.+?)_\d{4}-\d{2}-\d{2}\.json", f.name)
        sku = m.group(1) if m else ""
        print(f"\n{'='*60}")
        print(f"📥 Ingest: {f.name}  (sku={sku or '?'})")
        print(f"{'='*60}")
        data = json.loads(f.read_text(encoding="utf-8"))
        data["target_sku"] = sku
        # 重新写回
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # 调用 ingest
        args.file = f
        args.digest_id = digest_id
        cmd_ingest(args)
        # 清表里上次跑遗留的 unknown target_sku (避免重复)
    _cleanup_unknown_skus()
    
    # 跑 digest
    print(f"\n{'='*60}")
    print(f"📊 生成周报: {digest_id}")
    print(f"{'='*60}")
    args.digest_id = digest_id
    return cmd_digest(args)


def _cleanup_unknown_skus():
    """把 product_skus=未知 的潜在客户, 根据 source_signals.target_sku 回填"""
    conn = db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE potential_customers
                SET target_product_skus = jsonb_build_array(source_signals->>'target_sku')
                WHERE target_product_skus ? '未知'
                  AND source_signals ? 'target_sku'
            """)
            updated = cur.rowcount
            conn.commit()
            if updated:
                print(f"  🧹 回填 target_sku: {updated} 条")
    finally:
        conn.close()


# ============================================================
# main
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    
    p_ing = sub.add_parser("ingest")
    p_ing.add_argument("--file", type=Path, required=True)
    p_ing.add_argument("--digest-id", type=str, default=None)
    p_ing.set_defaults(func=cmd_ingest)
    
    p_dig = sub.add_parser("digest")
    p_dig.add_argument("--digest-id", type=str, default=None)
    p_dig.set_defaults(func=cmd_digest)
    
    p_all = sub.add_parser("run-all")
    p_all.add_argument("--note", type=str, default="")
    p_all.set_defaults(func=cmd_run_all)
    
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)

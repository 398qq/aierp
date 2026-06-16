"""
leads_pipeline/telegram_notify.py
生成周报 + 通过 OpenClaw message tool 推送
注：实际推送由 AI 进程用 message tool 触发，本脚本只输出待发消息
"""
import os
import sys
import json
import psycopg2
import psycopg2.extras
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/home/ttdiy/aierp/backend/.env")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "user": os.environ.get("DB_USER", "aierp"),
    "password": os.environ.get("DB_PASSWORD", "aierp"),
    "dbname": os.environ.get("DB_NAME", "aierp"),
}

DIGEST_DIR = Path("/home/ttdiy/.openclaw/workspace/1_业务开发/机会池/周报")
PENDING_DIR = Path("/home/ttdiy/aierp/leads_pipeline/pending_telegram")
PENDING_DIR.mkdir(exist_ok=True)


def get_potential_customers(digest_id: str) -> list:
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT name, region, estimated_size, source, confidence_score,
                       target_product_skus, contact_name, contact_phone, notes
                FROM potential_customers
                WHERE weekly_digest_id = %s AND status = 'pending'
                ORDER BY confidence_score DESC
            """, (digest_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def mark_telegram_sent(digest_id: str):
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE weekly_digests SET telegram_sent = TRUE WHERE digest_id = %s", (digest_id,))
            conn.commit()
    finally:
        conn.close()


def format_lead(lead: dict) -> str:
    name = lead["name"][:20]
    region = (lead.get("region") or "")[:10]
    size = lead.get("estimated_size") or "?"
    conf = lead.get("confidence_score") or 0
    return f"  • {name} | {region} | {size} | conf={conf:.2f}"


def build_message(leads: list, digest_id: str) -> str:
    """构造 Telegram 推送消息（限长 4096 字符）"""
    total = len(leads)
    msg = f"📊 *{digest_id} 潜在客户周报*\n"
    msg += f"共 {total} 条新线索\n\n"
    
    by_sku = {}
    for lead in leads:
        for sku in (lead.get("target_product_skus") or ["未知"]):
            by_sku.setdefault(sku, []).append(lead)
    
    for sku, items in by_sku.items():
        msg += f"📦 *{sku}* ({len(items)} 家)\n"
        for lead in items[:5]:
            msg += format_lead(lead) + "\n"
        if len(items) > 5:
            msg += f"  ... 还有 {len(items) - 5} 条\n"
        msg += "\n"
    
    msg += f"📁 完整: `~/.openclaw/workspace/1_业务开发/机会池/周报/{digest_id}.md`\n"
    msg += f"🎯 哪些入库？告诉我，我批量写 ERP。"
    return msg


def save_pending(digest_id: str, message: str) -> Path:
    """把待推送消息写到文件，AI 看到就推"""
    path = PENDING_DIR / f"{digest_id}.md"
    path.write_text(message, encoding="utf-8")
    return path


def main():
    digest_id = sys.argv[1] if len(sys.argv) > 1 else f"WD-{date.today().isoformat()}"
    
    leads = get_potential_customers(digest_id)
    if not leads:
        print(f"⚠️ {digest_id} 无新线索")
        return 0
    
    msg = build_message(leads, digest_id)
    path = save_pending(digest_id, msg)
    print(f"📝 消息已存: {path}")
    print(f"\n--- 预览 ({len(msg)} 字符) ---")
    print(msg)
    print(f"--- 预览完 ---\n")
    print(f"💡 提示: AI 进程检测到 PENDING_DIR 下的文件后, 用 message tool 推送到 Telegram")
    
    mark_telegram_sent(digest_id)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

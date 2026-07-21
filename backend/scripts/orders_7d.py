"""aierp ERP — 近7天销售订单查询"""
import datetime
import pathlib
import sys

from sqlalchemy import create_engine, text

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402

engine = create_engine(settings.DATABASE_URL_SYNC)

SEVEN_DAYS_AGO = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()

query = text("""
SELECT
    so.id,
    so.order_no,
    so.order_date AT TIME ZONE 'Asia/Shanghai' AS order_date_cst,
    so.total_amount,
    so.status,
    c.name AS customer_name,
    (SELECT json_agg(json_build_object(
        'product_name', soi.product_name,
        'quantity', soi.quantity,
        'total_price', soi.total_price
    )) FROM sales_order_items soi WHERE soi.order_id = so.id) AS items
FROM sales_orders so
LEFT JOIN customers c ON c.id = so.customer_id
WHERE so.order_date >= CAST(:seven_days_ago AS timestamp)
ORDER BY so.order_date DESC
""")

with engine.connect() as conn:
    rows = conn.execute(query, {"seven_days_ago": SEVEN_DAYS_AGO}).fetchall()

# Build output
orders = []
for r in rows:
    order_id, order_no, order_date_cst, total, status, customer, items_json = r
    total = float(total) if total else 0.0
    items = items_json if items_json else []
    item_summary = ", ".join(f"{i['product_name']}×{i['quantity']}" for i in items[:3])
    if len(items) > 3:
        item_summary += f" ...共{len(items)}项"
    orders.append({
        "id": order_id,
        "order_no": order_no or "",
        "order_date": str(order_date_cst)[:19] if order_date_cst else "",
        "customer": customer or "未知客户",
        "status": status or "unknown",
        "total": total,
        "items_display": item_summary,
    })

total_amount = sum(o["total"] for o in orders)
status_counts = {}
for o in orders:
    s = o["status"]
    status_counts[s] = status_counts.get(s, 0) + 1

# Timestamp in CST
now_cst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
ts = now_cst.strftime("%Y-%m-%d %H:%M")

print(f"TIMESTAMP:{ts}")
print(f"TOTAL_ORDERS:{len(orders)}")
print(f"TOTAL_AMOUNT:{total_amount:.2f}")
for s, c in sorted(status_counts.items()):
    print(f"STATUS:{s}:{c}")
for o in orders:
    d = o["order_date"][5:10] if o["order_date"] else "??-??"
    print(f"ORDER:{o['order_no']}|{d}|{o['customer']}|{o['status']}|{o['total']:.2f}|{o['items_display']}")

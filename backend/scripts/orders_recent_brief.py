"""Brief on recent orders — show last 30 days to give context."""
import json
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = "http://localhost:8080/api/v1"

def login():
    data = json.dumps({"username": "admin", "password": "admin123"}).encode()
    req = urllib.request.Request(f"{BASE}/auth/login", data=data,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["data"]["token"]

def fetch_page(token, page, page_size=100):
    req = urllib.request.Request(
        f"{BASE}/sales-orders?page={page}&page_size={page_size}&sort_by=id&sort_order=desc",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["data"]

token = login()
data = fetch_page(token, 1, 100)
items = data.get("list", [])
total = data.get("total", 0)
print(f"Total orders in DB: {total}")
print(f"Fetched (newest {len(items)}):")
print()

now = datetime.now(timezone.utc)
buckets = {"today": 0, "7d": 0, "30d": 0, "older": 0}
for o in items:
    od = o.get("order_date")
    if not od: continue
    dt = datetime.fromisoformat(od.replace("Z", "+00:00"))
    days_ago = (now - dt).days
    if days_ago < 1: buckets["today"] += 1
    elif days_ago < 7: buckets["7d"] += 1
    elif days_ago < 30: buckets["30d"] += 1
    else: buckets["older"] += 1

print("Age buckets (of newest 100):")
for k, v in buckets.items():
    print(f"  {k:>8}  {v}")
print()

# Print last 30 days
print("Orders from last 30 days (newest → oldest):")
print()
print(f"  {'id':>4}  {'order_no':<18}  {'order_date':<20}  {'customer':<28}  {'status':<12}  {'amount':>12}  {'items':>5}")
print("  " + "-"*120)
for o in items:
    od = o.get("order_date")
    if not od: continue
    dt = datetime.fromisoformat(od.replace("Z", "+00:00"))
    if (now - dt).days > 30: break
    cust = o.get("customer") or {}
    cust_name = cust.get("name", "?") if isinstance(cust, dict) else str(cust)
    print(f"  {o.get('id'):>4}  {(o.get('order_no') or ''):<18}  {od[:19]:<20}  {cust_name[:28]:<28}  {(o.get('status') or ''):<12}  {(o.get('total_amount') or 0):>12,.2f}  {len(o.get('items') or []):>5}")

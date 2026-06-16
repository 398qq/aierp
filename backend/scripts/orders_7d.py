"""Fetch sales orders from the last 7 days, paginating through the API."""
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE = "http://localhost:8080/api/v1"
USER = "admin"
PWD = "admin123"

def login():
    data = json.dumps({"username": USER, "password": PWD}).encode()
    req = urllib.request.Request(
        f"{BASE}/auth/login",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        body = json.loads(r.read())
    return body["data"]["token"]

def fetch_page(token, page, page_size=100):
    req = urllib.request.Request(
        f"{BASE}/sales-orders?page={page}&page_size={page_size}&sort_by=id&sort_order=desc",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read())
    return body["data"]

def main():
    token = login()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    print(f"Cutoff (UTC): {cutoff.isoformat()}")
    print(f"Cutoff (local-ish): {cutoff.astimezone().isoformat()}")
    print("---")

    collected = []
    page = 1
    while True:
        data = fetch_page(token, page, page_size=100)
        items = data.get("list", [])
        if not items:
            break
        collected.extend(items)
        # Stop if this page is older than cutoff AND we're not on first page
        # (we always scan newest first; stop when oldest on page < cutoff)
        oldest_on_page = items[-1]
        od = oldest_on_page.get("order_date")
        if od:
            try:
                od_dt = datetime.fromisoformat(od.replace("Z", "+00:00"))
            except Exception:
                od_dt = None
            if od_dt and od_dt < cutoff and page > 1:
                # the previous batch was already at/above cutoff; this whole page is below
                # drop anything below cutoff from this page, but stop
                collected = [o for o in collected if _within(o, cutoff)]
                break
        if page >= 50:
            print("safety break at page 50")
            break
        if len(items) < 100:
            break
        page += 1

    # Final filter (defensive)
    recent = [o for o in collected if _within(o, cutoff)]
    print(f"Total fetched: {len(collected)} | In last 7d: {len(recent)}")
    print("---")
    # Pretty summary
    total_amount = 0.0
    status_counts = {}
    for o in recent:
        s = o.get("status", "?")
        status_counts[s] = status_counts.get(s, 0) + 1
        total_amount += float(o.get("total_amount") or 0)
    print("Status breakdown:")
    for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"  {s:>16}  {c}")
    print(f"Total amount (sum): {total_amount:,.2f}")
    print("---")
    print("Orders:")
    for o in recent:
        print(json.dumps({
            "id": o.get("id"),
            "order_no": o.get("order_no"),
            "order_date": o.get("order_date"),
            "customer": (o.get("customer") or {}).get("name") if isinstance(o.get("customer"), dict) else o.get("customer_name"),
            "status": o.get("status"),
            "total": o.get("total_amount"),
            "currency": o.get("currency"),
            "items": len(o.get("items") or []),
        }, ensure_ascii=False))

def _within(o, cutoff):
    od = o.get("order_date")
    if not od:
        return False
    try:
        dt = datetime.fromisoformat(od.replace("Z", "+00:00"))
    except Exception:
        return False
    return dt >= cutoff

if __name__ == "__main__":
    main()

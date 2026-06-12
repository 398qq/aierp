#!/usr/bin/env python3
"""Screenshot the Commission list page using Playwright (Python).

Run from repo root:  python3 scripts/screenshot-commission.py
"""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("/home/ttdiy/aierp/docs/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND = "http://localhost:3002"
USERNAME = os.getenv("AIERP_LOGIN_USERNAME", "admin")
PASSWORD = os.getenv("AIERP_LOGIN_PASSWORD", "admin123")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        device_scale_factor=2,
        locale="zh-CN",
    )
    page = ctx.new_page()

    print("→ login page")
    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.screenshot(path=str(OUT_DIR / "01-login.png"))
    print("  saved 01-login.png")

    print("→ login as admin")
    page.fill('input[type="text"]', USERNAME)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{FRONTEND}/", timeout=10000)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT_DIR / "02-dashboard.png"))
    print("  saved 02-dashboard.png")

    print("→ /finance/commissions")
    # Pre-warm the page (first load is slow due to lazy chunk + dev compile)
    page.goto(f"{FRONTEND}/finance/commissions", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    # Reload to get a clean state with all data fetched
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path=str(OUT_DIR / "03-commission-list.png"))
    print("  saved 03-commission-list.png")

    print("→ open create drawer")
    try:
        page.click('button:has-text("新建佣金")', timeout=3000)
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT_DIR / "04-commission-drawer.png"))
        print("  saved 04-commission-drawer.png")
    except Exception as e:
        print(f"  (drawer button not found, skipped: {e})")

    browser.close()

print(f"\n✓ done. screenshots in {OUT_DIR}")

#!/usr/bin/env python3
"""Screenshot the Global 360 dashboard."""

from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("/home/ttdiy/aierp/docs/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND = "http://localhost:3002"
from lib.erp_auth import get_erp_creds

USERNAME, PASSWORD = get_erp_creds()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900}, device_scale_factor=2, locale="zh-CN"
    )
    page = ctx.new_page()

    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.fill('input[type="text"]', USERNAME)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{FRONTEND}/", timeout=10000)
    page.wait_for_load_state("networkidle")

    # Navigate to Global 360
    page.goto(f"{FRONTEND}/dashboard/global360", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(8000)  # AI call takes time
    page.screenshot(path=str(OUT_DIR / "05-global360.png"), full_page=True)
    print("  saved 05-global360.png")

    browser.close()
print(f"\n✓ done. screenshots in {OUT_DIR}")

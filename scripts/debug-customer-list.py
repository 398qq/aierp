#!/usr/bin/env python3
"""Debug customer list — capture the actual error."""

from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3002"
from lib.erp_auth import get_erp_creds

USERNAME, PASSWORD = get_erp_creds()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
    page = ctx.new_page()

    # Capture all network errors
    failed_requests = []
    page.on(
        "requestfailed",
        lambda req: failed_requests.append(
            {
                "url": req.url,
                "failure": req.failure,
            }
        ),
    )
    api_responses = []
    page.on(
        "response",
        lambda resp: api_responses.append(
            {
                "url": resp.url,
                "status": resp.status,
                "body": "" if resp.status >= 400 else None,
            }
        ),
    )

    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.fill('input[type="text"]', USERNAME)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{FRONTEND}/", timeout=10000)
    page.wait_for_load_state("networkidle")

    print("=== Navigating to /customers ===")
    page.goto(f"{FRONTEND}/customers", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

    # Check for error toast
    error_toasts = page.locator(".ant-message-error").all_text_contents()
    print("Error toasts:", error_toasts)

    # Find the network response for /customers
    print("\n=== API responses for /customers ===")
    for resp in api_responses:
        if "/customers" in resp["url"] and "import" not in resp["url"]:
            print(f"  {resp['status']}  {resp['url']}")

    print("\n=== Failed requests ===")
    for req in failed_requests:
        if "/customers" in req["url"] or "customer" in req["url"]:
            print(f"  {req['url']}  failure={req['failure']}")

    # Try to capture page console errors
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"{msg.type}: {msg.text}"))

    page.reload(wait_until="networkidle")
    page.wait_for_timeout(3000)

    print("\n=== Console errors ===")
    for msg in console_msgs:
        if msg.startswith("error") or msg.startswith("warn"):
            print(f"  {msg}")

    # Check the page state
    page_text = page.locator("body").text_content()
    if "加载" in page_text or "失败" in page_text:
        print(f"\nPage contains error text: {page_text[:200]}")

    page.screenshot(path="/tmp/customer-error.png", full_page=True)
    print("\nScreenshot saved to /tmp/customer-error.png")

    browser.close()

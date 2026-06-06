"""Verify customer list loads correctly on /customers page."""
import asyncio
from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()

        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type in ("error", "warning") else None)
        api_responses: list[tuple[str, int, int]] = []

        async def on_response(r):
            if "/api/v1/customers?" in r.url:
                try:
                    body = await r.body()
                    api_responses.append((r.url, r.status, len(body or b"")))
                except Exception:
                    api_responses.append((r.url, r.status, -1))

        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        token_resp = await ctx.request.post(
            "http://localhost:8080/api/v1/auth/login",
            data={"username": "testadmin", "password": "admin123"},
        )
        token_data = await token_resp.json()
        token = token_data["data"]["token"]

        await page.goto("http://localhost:3002/", wait_until="domcontentloaded")
        await page.evaluate(f"localStorage.setItem('token', '{token}')")
        await page.goto("http://localhost:3002/customers", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        await page.screenshot(path="/tmp/customer-fixed.png", full_page=True)
        print("Screenshot: /tmp/customer-fixed.png")

        rows = await page.locator(".ant-table-tbody tr.ant-table-row").count()
        print(f"Visible table rows: {rows}")

        for url, status, size in api_responses:
            print(f"  API: {url[-80:]} → {status} ({size} bytes)")

        error_toast = await page.locator(".ant-message-error, .ant-notification-notice-error").count()
        print(f"Error toasts visible: {error_toast}")

        smart_list_text = await page.locator("text=/智能客户列表/").first.inner_text() if await page.locator("text=/智能客户列表/").count() else "N/A"
        print(f"Smart list header: {smart_list_text!r}")

        await browser.close()


asyncio.run(main())

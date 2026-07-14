/** E2E test — Commission full lifecycle (PRD-012 section 9.4).

Covers: create → submit → approve → pay, batch approve.
Requires: backend :8080 + frontend :3002 already running.

  npx playwright test
*/

import { test, expect } from "@playwright/test";

const API = "http://localhost:8080/api/v1";

// ── helpers ───────────────────────────────────────────────────────────

async function getAuth(request: any): Promise<{ token: string; userId: number }> {
  const loginResp = await request.post(`${API}/auth/login`, {
    data: { username: "admin", password: "admin123" },
  });
  if (loginResp.status() !== 200) throw new Error(`Login: ${await loginResp.text()}`);
  const token = (await loginResp.json()).data.token;

  const meResp = await request.get(`${API}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (meResp.status() !== 200) throw new Error(`Auth/me: ${await meResp.text()}`);
  return { token, userId: (await meResp.json()).data.user_id };
}

async function createCustomer(request: any, token: string): Promise<number> {
  const resp = await request.post(`${API}/customers`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: `E2E-${Date.now()}`, industry: "电子", level: "A" },
  });
  if (![200, 201].includes(resp.status())) throw new Error(`Customer: ${await resp.text()}`);
  return (await resp.json()).data.id;
}

async function createSalesOrder(request: any, token: string, customerId: number): Promise<number> {
  const resp = await request.post(`${API}/sales-orders`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { customer_id: customerId, order_date: "2026-07-10", total_amount: 100000, status: "confirmed" },
  });
  if (![200, 201].includes(resp.status())) throw new Error(`SO: ${await resp.text()}`);
  return (await resp.json()).data.id;
}

/** Dismiss antd message toasts that block pointer events. */
async function dismissToasts(page: any) {
  const closeIcons = page.locator(".ant-message-notice .anticon-close");
  const count = await closeIcons.count();
  for (let i = 0; i < count; i++) {
    await closeIcons.nth(i).click({ force: true }).catch(() => {});
  }
  await page.waitForTimeout(300);
}

// ── tests ─────────────────────────────────────────────────────────────

test.describe("Commission E2E lifecycle", () => {
  test("full flow: create → submit → approve → pay", async ({ page, request }) => {
    test.setTimeout(90000);

    const { token, userId } = await getAuth(request);
    await page.context().addCookies([
      { name: "aierp_token", value: token, domain: "localhost", path: "/" },
    ]);
    const customerId = await createCustomer(request, token);
    const soId = await createSalesOrder(request, token, customerId);

    await page.goto("/finance/commissions");
    await expect(page.getByText("佣金管理")).toBeVisible();

    // Open drawer and fill form
    await dismissToasts(page);
    await page.getByRole("button", { name: /新建佣金/ }).click({ force: true });
    await expect(page.locator(".ant-drawer-title")).toBeVisible();

    await page.locator("#sales_order_id").fill(String(soId));
    await page.locator("#sales_user_id").fill(String(userId));
    await page.getByLabel(/佣金基数/).fill("50000");
    await page.getByLabel(/比例/).fill("0.05");
    await page.waitForTimeout(200);

    // Submit form
    await page.locator(".ant-drawer-footer").getByRole("button", { name: /创/ }).click({ force: true });
    await page.waitForTimeout(1500);
    await dismissToasts(page);

    // Verify draft row exists
    await expect(page.getByText("草稿").first()).toBeVisible({ timeout: 8000 });

    // Submit → pending_approval
    await page.getByRole("button", { name: "提交审批" }).first().click({ force: true });
    await page.waitForTimeout(800);
    await expect(page.getByText("待审批").first()).toBeVisible({ timeout: 5000 });

    // Approve → approved
    await page.getByRole("button", { name: "审批" }).first().click({ force: true });
    await page.waitForTimeout(800);
    await expect(page.getByText("已审批").first()).toBeVisible({ timeout: 5000 });

    // Pay → paid
    await page.getByRole("button", { name: "标记发放" }).first().click({ force: true });
    await page.waitForTimeout(800);
    await expect(page.getByText("已发放").first()).toBeVisible({ timeout: 5000 });
  });

  test("batch approve multiple commissions", async ({ page, request }) => {
    test.setTimeout(90000);

    const { token, userId } = await getAuth(request);
    await page.context().addCookies([
      { name: "aierp_token", value: token, domain: "localhost", path: "/" },
    ]);
    const customerId = await createCustomer(request, token);
    const so1 = await createSalesOrder(request, token, customerId);
    const so2 = await createSalesOrder(request, token, customerId);

    await page.goto("/finance/commissions");
    await expect(page.getByText("佣金管理")).toBeVisible();

    // Create two commissions
    for (const soId of [so1, so2]) {
      await dismissToasts(page);
      await page.getByRole("button", { name: /新建佣金/ }).click({ force: true });
      await expect(page.locator(".ant-drawer-title")).toBeVisible();

      await page.locator("#sales_order_id").fill(String(soId));
      await page.locator("#sales_user_id").fill(String(userId));
      await page.getByLabel(/佣金基数/).fill("30000");
      await page.getByLabel(/比例/).fill("0.03");
      await page.waitForTimeout(200);

      await page.locator(".ant-drawer-footer").getByRole("button", { name: /创/ }).click({ force: true });
      await page.waitForTimeout(1500);
      await dismissToasts(page);
    }

    // Submit both to pending_approval
    const submitBtns = page.getByRole("button", { name: "提交审批" });
    const count = await submitBtns.count();
    for (let i = 0; i < count; i++) {
      await submitBtns.first().click({ force: true });
      await page.waitForTimeout(600);
    }

    // Select rows individually (select-all checkbox may not trigger React state)
    await dismissToasts(page);
    const rowCheckboxes = page.locator("td.ant-table-selection-column input[type=checkbox]");
    const rowCount = await rowCheckboxes.count();
    for (let i = 0; i < rowCount; i++) {
      await rowCheckboxes.nth(i).click({ force: true });
      await page.waitForTimeout(200);
    }
    await expect(page.getByText(/已选/)).toBeVisible({ timeout: 5000 });

    await page.getByRole("button", { name: "批量审批" }).click({ force: true });
    await page.waitForTimeout(1000);

    await expect(page.getByText("已审批").first()).toBeVisible({ timeout: 5000 });
  });
});

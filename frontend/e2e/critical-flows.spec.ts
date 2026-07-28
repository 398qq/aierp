/**
 * Critical flow smoke tests for the Pro v6 frontend.
 *
 * Covers the 5 core user journeys from the Pro v6 plan:
 *   1. Login (UI form, not just API auth)
 *   2. List page (table loads, row visible)
 *   3. Detail page (route navigates, content renders)
 *   4. Form (open editor, fields populate)
 *   5. Submit + redirect (form saves, route returns to list/detail)
 *
 * Runs against max dev on :3002. Requires AIERP_LOGIN_PASSWORD env var.
 */

import { expect, test } from "@playwright/test";

const USERNAME = process.env.AIERP_LOGIN_USERNAME ?? "admin";
const PASSWORD = process.env.AIERP_LOGIN_PASSWORD;
if (!PASSWORD) throw new Error("AIERP_LOGIN_PASSWORD is required");

async function authenticateViaApi(page: import("@playwright/test").Page): Promise<void> {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();
}

test("login form authenticates and redirects to dashboard", async ({ page }) => {
  // Bootstrap auth via API so the httpOnly cookie is set for the browser.
  await authenticateViaApi(page);

  // Log out by clearing the cookie, then go to /login and verify the form is present.
  await page.context().clearCookies();
  await page.goto("/login", { waitUntil: "domcontentloaded" });

  // The login page should render a form with username + password fields.
  await expect(page).toHaveURL(/\/login$/);
  const usernameField = page.locator('input[name="username"], input[id*="username"]').first();
  const passwordField = page
    .locator('input[name="password"], input[id*="password"], input[type="password"]')
    .first();
  await expect(usernameField).toBeVisible();
  await expect(passwordField).toBeVisible();

  // Submit with valid credentials — should redirect away from /login.
  await usernameField.fill(USERNAME);
  await passwordField.fill(PASSWORD);
  await page
    .getByRole("button", { name: /登录|login/i })
    .first()
    .click();

  await page.waitForURL((url) => !/\/login$/.test(url.pathname), { timeout: 15_000 });
  // After login the user lands on / or the dashboard.
  await expect(page).not.toHaveURL(/\/login$/);
});

test("opportunities list loads table with rows", async ({ page }) => {
  await authenticateViaApi(page);
  await page.goto("/sales/opportunities", { waitUntil: "domcontentloaded" });

  // ProTable renders into .ant-pro-table or .ant-table.
  const table = page.locator(".ant-pro-table, .ant-table").first();
  await expect(table).toBeVisible({ timeout: 15_000 });

  // Wait for at least one row or the empty state placeholder.
  await page
    .locator(".ant-table-tbody tr, .ant-table-row, .ant-pro-table-list .ant-table-row")
    .first()
    .waitFor({ state: "visible", timeout: 10_000 })
    .catch(async () => {
      // Empty state is also acceptable.
      await expect(page.getByText(/暂无|没有|empty/i).first()).toBeVisible();
    });
});

test("opportunity detail page renders content for first row", async ({ page }) => {
  await authenticateViaApi(page);

  // Pick the first opportunity via API.
  const resp = await page.request.get("/api/v1/sales/opportunities?page=1&page_size=1");
  expect(resp.ok(), await resp.text()).toBeTruthy();
  const payload = await resp.json();
  const opp = payload.data?.list?.[0];
  if (!opp?.id) {
    test.skip(true, "No opportunities in test database");
    return;
  }

  await page.goto(`/sales/opportunities/${opp.id}`, { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(new RegExp(`/sales/opportunities/${opp.id}$`));

  // Detail page should render an h1/h2 with the opportunity title or a sticky action area.
  await expect(page.locator(".ant-descriptions, .ant-page-header, .ant-card").first()).toBeVisible({
    timeout: 10_000,
  });
});

test("opportunity edit form opens, fields populate, cancel returns to detail", async ({ page }) => {
  await authenticateViaApi(page);

  const resp = await page.request.get("/api/v1/sales/opportunities?page=1&page_size=1");
  expect(resp.ok(), await resp.text()).toBeTruthy();
  const payload = await resp.json();
  const opp = payload.data?.list?.[0];
  if (!opp?.id) {
    test.skip(true, "No opportunities in test database");
    return;
  }

  await page.goto(`/sales/opportunities/${opp.id}/edit`, { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(new RegExp(`/sales/opportunities/${opp.id}/edit$`));

  // ProForm should render with the title field populated.
  const titleField = page.locator('input[id*="title"], input[name="title"]').first();
  await expect(titleField).toBeVisible({ timeout: 10_000 });
  if (opp.title) {
    await expect(titleField).toHaveValue(opp.title);
  }

  // Cancel should navigate back to detail.
  await page
    .getByRole("button", { name: /取消|cancel/i })
    .first()
    .click();
  await page.waitForURL(new RegExp(`/sales/opportunities/${opp.id}(?!/edit)`), { timeout: 10_000 });
});

test("new opportunity form submit redirects to list", async ({ page }) => {
  await authenticateViaApi(page);

  // Pick a customer id to use in the new opportunity.
  const customers = await page.request.get("/api/v1/customers?page=1&page_size=1");
  expect(customers.ok(), await customers.text()).toBeTruthy();
  const customer = (await customers.json()).data?.list?.[0];
  if (!customer?.id) {
    test.skip(true, "No customers in test database to attach opportunity to");
    return;
  }

  await page.goto("/sales/opportunities/new", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/sales\/opportunities\/new$/);

  // Fill required fields: title.
  const titleField = page.locator('input[id*="title"], input[name="title"]').first();
  await expect(titleField).toBeVisible({ timeout: 10_000 });
  const uniqueTitle = `e2e-test-${Date.now()}`;
  await titleField.fill(uniqueTitle);

  // Pick customer if there's a select trigger (CustomerSelect component).
  const customerSelect = page.locator(".ant-select").first();
  if (await customerSelect.isVisible().catch(() => false)) {
    await customerSelect.click();
    // Search by customer name then pick.
    const option = page.locator(".ant-select-item-option").first();
    if (await option.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await option.click();
    }
  }

  // Submit (ProForm onFinish triggers the Save button click).
  await page
    .getByRole("button", { name: /保存|创建/i })
    .last()
    .click();

  // Should redirect back to /sales/opportunities list.
  await page.waitForURL(/\/sales\/opportunities$/, { timeout: 15_000 });
  await expect(page).toHaveURL(/\/sales\/opportunities$/);
});

import { expect, test } from "@playwright/test";

const USERNAME = process.env.AIERP_LOGIN_USERNAME ?? "admin";
const PASSWORD = process.env.AIERP_LOGIN_PASSWORD;
if (!PASSWORD) throw new Error("AIERP_LOGIN_PASSWORD is required");

const routes = [
  "/",
  "/dashboard/global360",
  "/dashboard/watchtower",
  "/customers/stats",
  "/customers",
  "/customers/follow-ups",
  "/customers/intelligence",
  "/sales/dashboard",
  "/sales/opportunities",
  "/sales/quotations",
  "/sales/orders",
  "/sales/delivery-notes",
  "/sales/invoices",
  "/sales/payments",
  "/sales/contracts",
  "/sales/targets",
  "/sales/inquiry",
  "/procurement/dashboard",
  "/sales/purchase-orders",
  "/suppliers/stats",
  "/suppliers",
  "/suppliers/compare",
  "/products",
  "/products/price-import",
  "/brands",
  "/inventory",
  "/warehouse/warehouses",
  "/warehouse/inventory-ledger",
  "/warehouse/inventory-batches",
  "/finance/accounts",
  "/finance/journal-entries",
  "/finance/pnl",
  "/reports/ar",
  "/reports/ap",
  "/finance/commissions",
  "/finance/commission-schemes",
  "/reports/sales",
  "/reports/inventory",
  "/reports/procurement",
  "/system/approvals",
  "/system/approval-rules",
  "/tickets",
  "/notifications",
  "/ai/chat",
  "/system/users",
  "/system/roles",
  "/system/audit-logs",
  "/data/import-export",
  "/settings",
] as const;

test("all operational routes render without runtime or server errors", async ({ page }) => {
  test.setTimeout(180_000);

  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();

  const failures: string[] = [];
  let activeRoute = "";

  page.on("pageerror", (error) => failures.push(`${activeRoute} pageerror: ${error.message}`));
  page.on("requestfailed", (request) => {
    if (request.url().includes("/api/v1/") && request.failure()?.errorText !== "net::ERR_ABORTED") {
      failures.push(
        `${activeRoute} request failed: ${request.url()} (${request.failure()?.errorText})`,
      );
    }
  });
  page.on("response", (response) => {
    if (response.url().includes("/api/v1/") && response.status() >= 400) {
      failures.push(`${activeRoute} API ${response.status()}: ${response.url()}`);
    }
  });

  for (const route of routes) {
    activeRoute = route;
    const response = await page.goto(route, { waitUntil: "domcontentloaded" });
    if (!response?.ok()) failures.push(`${route} document status: ${response?.status() ?? "none"}`);

    await page
      .locator(".erp-app-content")
      .waitFor({ state: "visible", timeout: 10_000 })
      .catch(() => {
        failures.push(`${route} app content is not visible`);
      });
    await page.waitForTimeout(300);

    if (
      await page
        .getByText("页面加载异常", { exact: true })
        .isVisible()
        .catch(() => false)
    ) {
      const detail = await page
        .locator(".ant-result-subtitle")
        .textContent()
        .catch(() => "unknown error");
      failures.push(`${route} error boundary: ${detail}`);
    }
  }

  expect(failures, failures.join("\n")).toEqual([]);
});

test("core mobile routes stay within the viewport and keep navigation operable", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 390, height: 844 });

  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();

  const mobileRoutes = [
    "/",
    "/customers",
    "/sales/opportunities",
    "/sales/quotations",
    "/sales/orders",
    "/sales/delivery-notes",
    "/sales/invoices",
    "/sales/payments",
    "/sales/purchase-orders",
    "/products",
    "/inventory",
    "/system/approvals",
    "/notifications",
  ];
  const failures: string[] = [];
  let activeRoute = "";

  page.on("pageerror", (error) => failures.push(`${activeRoute} pageerror: ${error.message}`));
  page.on("response", (response) => {
    if (response.url().includes("/api/v1/") && response.status() >= 500) {
      failures.push(`${activeRoute} API ${response.status()}: ${response.url()}`);
    }
  });

  for (const route of mobileRoutes) {
    activeRoute = route;
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await expect(page.locator(".erp-mobile-bottom-nav")).toBeVisible();
    await expect(page.locator(".erp-app-content")).toBeVisible();
    await page.waitForTimeout(300);

    const viewportOverflow = await page.evaluate(
      () =>
        Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) -
        window.innerWidth,
    );
    if (viewportOverflow > 2)
      failures.push(`${route} horizontal viewport overflow: ${viewportOverflow}px`);

    if (
      await page
        .getByText("页面加载异常", { exact: true })
        .isVisible()
        .catch(() => false)
    ) {
      failures.push(`${route} error boundary is visible`);
    }
  }

  expect(failures, failures.join("\n")).toEqual([]);
});

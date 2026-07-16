import { expect, test } from "@playwright/test";

test("product ledger header and fixed columns stay aligned", async ({ page }) => {
  await page.setViewportSize({ width: 1420, height: 600 });
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: "admin", password: "admin123" },
  });
  expect(login.ok(), await login.text()).toBeTruthy();

  await page.goto("/products", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("产品台账", { exact: false }).first()).toBeVisible();
  await expect(page.locator(".product-table-panel .ant-table-tbody tr").first()).toBeVisible();
  await page.locator(".product-table-panel").evaluate((panel) => {
    window.scrollTo({ top: panel.getBoundingClientRect().top + window.scrollY, behavior: "instant" });
  });
  await page.waitForTimeout(100);

  const layout = await page.evaluate(() => {
    const panelHeader = document.querySelector<HTMLElement>(".product-table-header");
    const headerRow = document.querySelector<HTMLElement>(
      ".product-table-panel .ant-table-thead > tr",
    );
    const firstBodyRow = document.querySelector<HTMLElement>(
      ".product-table-panel .ant-table-tbody > tr",
    );
    const cells = Array.from(
      document.querySelectorAll<HTMLElement>(
        ".product-table-panel .ant-table-thead > tr > th",
      ),
    );
    const scrollBody = document.querySelector<HTMLElement>(
      ".product-table-panel .ant-table-content",
    );

    return {
      headerGap: headerRow && panelHeader
        ? Math.round(headerRow.getBoundingClientRect().top - panelHeader.getBoundingClientRect().bottom)
        : null,
      bodyGap: headerRow && firstBodyRow
        ? Math.round(firstBodyRow.getBoundingClientRect().top - headerRow.getBoundingClientRect().bottom)
        : null,
      headerTitles: cells.map((cell) => cell.textContent?.trim() || "").filter(Boolean),
      tableOverflow: scrollBody ? scrollBody.scrollWidth - scrollBody.clientWidth : null,
      viewportOverflow:
        Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
      stickyTop: headerRow ? getComputedStyle(headerRow.firstElementChild as Element).top : null,
    };
  });

  expect(layout.headerGap).not.toBeNull();
  expect(layout.headerGap).toBeLessThanOrEqual(2);
  expect(layout.bodyGap).toBeGreaterThanOrEqual(-1);
  expect(layout.headerTitles.slice(0, 2)).toEqual(["SKU", "产品名称"]);
  expect(layout.stickyTop).toBe("auto");
  expect(layout.tableOverflow).toBeGreaterThan(0);
  expect(layout.viewportOverflow).toBeLessThanOrEqual(2);
});

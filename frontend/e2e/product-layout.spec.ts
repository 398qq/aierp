import { expect, test } from "@playwright/test";

const USERNAME = process.env.AIERP_LOGIN_USERNAME ?? "admin";
const PASSWORD = process.env.AIERP_LOGIN_PASSWORD;
if (!PASSWORD) throw new Error("AIERP_LOGIN_PASSWORD is required");

test("product ledger header and fixed columns stay aligned", async ({ page }) => {
  await page.setViewportSize({ width: 1420, height: 600 });
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();

  await page.goto("/products", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("产品台账", { exact: false }).first()).toBeVisible();
  await expect(page.locator(".product-health-toolbar")).toBeVisible();
  await expect(page.locator(".product-health-metric")).toHaveCount(5);
  await expect(page.locator(".product-task-button")).toHaveCount(7);
  await expect(page.locator(".product-table-panel .ant-table-tbody tr").first()).toBeVisible();
  await page.locator(".product-table-panel").evaluate((panel) => {
    window.scrollTo({
      top: panel.getBoundingClientRect().top + window.scrollY,
      behavior: "instant",
    });
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
      document.querySelectorAll<HTMLElement>(".product-table-panel .ant-table-thead > tr > th"),
    );
    const scrollBody = document.querySelector<HTMLElement>(
      ".product-table-panel .ant-table-content",
    );
    const taskButtons = Array.from(document.querySelectorAll<HTMLElement>(".product-task-button"));

    return {
      headerGap:
        headerRow && panelHeader
          ? Math.round(
              headerRow.getBoundingClientRect().top - panelHeader.getBoundingClientRect().bottom,
            )
          : null,
      bodyGap:
        headerRow && firstBodyRow
          ? Math.round(
              firstBodyRow.getBoundingClientRect().top - headerRow.getBoundingClientRect().bottom,
            )
          : null,
      headerTitles: cells.map((cell) => cell.textContent?.trim() || "").filter(Boolean),
      tableOverflow: scrollBody ? scrollBody.scrollWidth - scrollBody.clientWidth : null,
      viewportOverflow:
        Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) -
        window.innerWidth,
      stickyTop: headerRow ? getComputedStyle(headerRow.firstElementChild as Element).top : null,
      taskTops: taskButtons.map((button) => Math.round(button.getBoundingClientRect().top)),
    };
  });

  expect(layout.headerGap).not.toBeNull();
  expect(layout.headerGap).toBeLessThanOrEqual(2);
  expect(layout.bodyGap).toBeGreaterThanOrEqual(-1);
  expect(layout.headerTitles.slice(0, 2)).toEqual(["SKU", "产品名称"]);
  expect(layout.headerTitles).toContain("安全库存");
  expect(layout.headerTitles).toContain("默认仓库");
  expect(layout.stickyTop).toBe("auto");
  expect(layout.tableOverflow).toBeGreaterThan(0);
  expect(layout.viewportOverflow).toBeLessThanOrEqual(2);
  expect(new Set(layout.taskTops).size).toBe(1);
});

test("product name opens the standalone product detail page", async ({ page }) => {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();

  await page.goto("/products", { waitUntil: "domcontentloaded" });
  const productName = page.locator(".product-table-panel .product-name-link").first();
  await expect(productName).toBeVisible();
  await productName.click();

  await expect(page).toHaveURL(/\/products\/\d+$/);
  await expect(page.getByRole("button", { name: "返回列表" })).toBeVisible();
  await expect(page.getByText("生产日期", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "编辑" }).click();
  await expect(page).toHaveURL(/\/products\/\d+\/edit$/);
  await expect(page.getByRole("heading", { name: "编辑产品主数据" })).toBeVisible();
  await expect(page.locator(".ant-modal")).toHaveCount(0);
  await expect(page.getByLabel("生产日期")).toBeVisible();

  const specNameFields = page.getByLabel("参数名称");
  const specCount = await specNameFields.count();
  await page.getByRole("button", { name: "添加规格字段" }).click();
  await expect(specNameFields).toHaveCount(specCount + 1);
});

test("product detail provides supplier relationship management", async ({ page }) => {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();
  const products = await page.request.get("/api/v1/products?page=1&page_size=1");
  const product = (await products.json()).data.list[0];

  await page.goto(`/products/${product.id}`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "添加供应商" }).click();
  await expect(page.getByRole("dialog", { name: "添加供应商关系" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: /供应商/ })).toBeVisible();
  await expect(page.getByLabel("供应商料号")).toBeVisible();
  await expect(page.getByLabel("采购价")).toBeVisible();
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "批量添加" }).click();
  await expect(page.getByRole("dialog", { name: "批量添加供应商关系" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: /供应商（可多选）/ })).toBeVisible();
});

test("product editor loads brands beyond the default first page", async ({ page }) => {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();
  const products = await page.request.get("/api/v1/products?page=1&page_size=1");
  const product = (await products.json()).data.list[0];
  const brands = await page.request.get("/api/v1/brands?page=2&page_size=20");
  const laterBrand = (await brands.json()).data.list[0];
  expect(laterBrand?.name).toBeTruthy();

  await page.goto(`/products/${product.id}/edit`, { waitUntil: "domcontentloaded" });
  const brandSelect = page.getByRole("combobox", { name: "品牌" });
  await brandSelect.click();
  await brandSelect.fill(laterBrand.name);
  await expect(page.getByRole("option", { name: new RegExp(laterBrand.name) })).toHaveCount(1);
});

test("product ledger supports changing rows per page", async ({ page }) => {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();
  await page.goto("/products", { waitUntil: "domcontentloaded" });

  const pageSizeSelect = page.locator(".ant-pagination-options-size-changer");
  await expect(pageSizeSelect).toContainText("20 条/页");
  await pageSizeSelect.click();
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes("/api/v1/products") &&
        response.url().includes("page_size=50") &&
        response.ok(),
    ),
    page.getByRole("option", { name: "50 条/页" }).click(),
  ]);
  await expect(pageSizeSelect).toContainText("50 条/页");
  await expect(page.getByText(/第 1-50 条 \/ 共 \d+ 条/)).toBeVisible();
});

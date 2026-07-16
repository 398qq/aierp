import { expect, test } from "@playwright/test";

test("brand detail opens a standalone editor and saves changes", async ({ page }) => {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: "admin", password: "admin123" },
  });
  expect(login.ok(), await login.text()).toBeTruthy();

  const brands = await page.request.get("/api/v1/brands?page=1&page_size=1");
  expect(brands.ok(), await brands.text()).toBeTruthy();
  const payload = await brands.json();
  const brand = payload.data.list[0];
  expect(brand?.id).toBeTruthy();

  await page.goto(`/brands/${brand.id}`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "编辑" }).first().click();

  await expect(page).toHaveURL(new RegExp(`/brands/${brand.id}/edit$`));
  await expect(page.getByRole("heading", { name: "编辑品牌主数据" })).toBeVisible();
  await expect(page.locator(".ant-modal")).toHaveCount(0);
  await expect(page.getByLabel("品牌名称")).toHaveValue(brand.name);

  await page.getByRole("button", { name: "保存" }).first().click();
  await expect(page).toHaveURL(new RegExp(`/brands/${brand.id}$`));
  await expect(page.getByText("更新成功", { exact: true })).toBeVisible();
});

test("brand detail provides manual product association", async ({ page }) => {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: "admin", password: "admin123" },
  });
  expect(login.ok(), await login.text()).toBeTruthy();
  const brands = await page.request.get("/api/v1/brands?page=1&page_size=1");
  const brand = (await brands.json()).data.list[0];

  await page.goto(`/brands/${brand.id}`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "手动关联产品" }).click();
  await expect(page.getByRole("dialog", { name: "关联产品" })).toBeVisible();
  await expect(page.getByText("仅显示尚未归属品牌的产品")).toBeVisible();
});

test("associated products expose view edit and unlink actions", async ({ page }) => {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: "admin", password: "admin123" },
  });
  expect(login.ok(), await login.text()).toBeTruthy();
  const products = await page.request.get("/api/v1/products?page=1&page_size=100");
  const product = (await products.json()).data.list.find((item: { brand_id?: number }) => item.brand_id);
  test.skip(!product, "当前没有已关联品牌的产品");

  await page.goto(`/brands/${product.brand_id}`, { waitUntil: "domcontentloaded" });
  const row = page.locator(".ant-table-tbody tr", { hasText: product.name }).first();
  await expect(row.getByRole("button", { name: "查看" })).toBeVisible();
  await expect(row.getByRole("button", { name: "编辑" })).toBeVisible();
  await expect(row.getByRole("button", { name: "解除关联" })).toBeVisible();
});

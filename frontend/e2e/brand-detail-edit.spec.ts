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
  await page.getByRole("button", { name: "编辑" }).click();

  await expect(page).toHaveURL(new RegExp(`/brands/${brand.id}/edit$`));
  await expect(page.getByRole("heading", { name: "编辑品牌主数据" })).toBeVisible();
  await expect(page.locator(".ant-modal")).toHaveCount(0);
  await expect(page.getByLabel("品牌名称")).toHaveValue(brand.name);

  await page.getByRole("button", { name: "保存" }).first().click();
  await expect(page).toHaveURL(new RegExp(`/brands/${brand.id}$`));
  await expect(page.getByText("更新成功", { exact: true })).toBeVisible();
});

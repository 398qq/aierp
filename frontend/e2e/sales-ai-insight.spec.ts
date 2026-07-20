import { expect, test, type Page } from "@playwright/test";

const USERNAME = process.env.AIERP_LOGIN_USERNAME ?? "admin";
const PASSWORD = process.env.AIERP_LOGIN_PASSWORD;
if (!PASSWORD) throw new Error("AIERP_LOGIN_PASSWORD is required");

type Box = { x: number; y: number; width: number; height: number };

function boxesOverlap(a: Box, b: Box) {
  return !(
    a.x + a.width <= b.x ||
    b.x + b.width <= a.x ||
    a.y + a.height <= b.y ||
    b.y + b.height <= a.y
  );
}

async function expectNoInsightOverflow(page: Page) {
  const result = await page.locator(".sales-ai-insight").evaluate((element) => ({
    overflow: element.scrollWidth - element.clientWidth,
    geometry: [element, element.parentElement, element.parentElement?.parentElement]
      .filter((node): node is HTMLElement => Boolean(node))
      .map(
        (node) =>
          `${node.tagName}.${node.className}: client=${node.clientWidth}, scroll=${node.scrollWidth}`,
      ),
    offenders: [...element.querySelectorAll<HTMLElement>("*")]
      .filter((child) => child.scrollWidth - child.clientWidth > 2)
      .map(
        (child) =>
          `${child.tagName}.${child.className}: ${child.scrollWidth - child.clientWidth}px`,
      )
      .slice(0, 8),
  }));
  expect(result.overflow, [...result.geometry, ...result.offenders].join("\n")).toBeLessThanOrEqual(
    2,
  );
}

test("sales order AI flags wrap inside the insight card", async ({ page }) => {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();

  const listResponse = await page.request.get("/api/v1/sales-orders?page=1&page_size=20");
  expect(listResponse.ok(), await listResponse.text()).toBeTruthy();
  const orders = (await listResponse.json()).data.list as Array<{ id: number }>;

  const orderId = orders[0]?.id;
  expect(orderId, "需要至少一张订单测试数据").toBeDefined();
  const detailResponse = await page.request.get(`/api/v1/sales-orders/${orderId}?include_ai=false`);
  expect(detailResponse.ok(), await detailResponse.text()).toBeTruthy();
  const detailBody = await detailResponse.json();
  detailBody.data.ai = {
    delivery_risk: "medium",
    payment_risk: "low",
    health_score: 72,
    flags: [
      "下单与交货同日期，电子元器件备货和物流时间极短，存在需要业务人员立即确认的履约压力",
      "no_payment_terms_documented_and_customer_credit_history_requires_review",
    ],
  };
  const flags = detailBody.data.ai.flags as string[];
  const longestFlag = [...flags].sort((a, b) => b.length - a.length)[0];
  expect(longestFlag, "需要至少一个 AI 标记").toBeTruthy();

  await page.route(`**/api/v1/sales-orders/${orderId}?include_ai=true`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(detailBody),
    }),
  );

  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto(`/sales/orders/${orderId}`);
  const flag = page.getByText(longestFlag, { exact: true });
  await expect(flag).toBeVisible({ timeout: 20_000 });
  const healthLabel = page.getByText("健康分", { exact: true });
  const deliveryLabel = page.getByText("交货风险", { exact: true });
  await expect(healthLabel).toBeVisible();
  await expect(deliveryLabel).toBeVisible();

  const tagBox = await flag.boundingBox();
  const contentBox = await page.locator(".sales-ai-insight .ant-card-body").boundingBox();
  const tagsBox = await flag
    .locator("xpath=ancestor::div[contains(@class, 'sales-ai-insight-tags')]")
    .boundingBox();
  const healthLabelBox = await healthLabel.boundingBox();
  const deliveryLabelBox = await deliveryLabel.boundingBox();
  expect(tagBox).not.toBeNull();
  expect(contentBox).not.toBeNull();
  expect(tagsBox).not.toBeNull();
  expect(healthLabelBox).not.toBeNull();
  expect(deliveryLabelBox).not.toBeNull();
  expect(tagBox!.x + tagBox!.width).toBeLessThanOrEqual(contentBox!.x + contentBox!.width + 1);
  expect(tagsBox!.width).toBeGreaterThan(contentBox!.width * 0.7);
  expect(healthLabelBox!.height).toBeLessThanOrEqual(30);
  const labelsOverlap = !(
    healthLabelBox!.x + healthLabelBox!.width <= deliveryLabelBox!.x ||
    deliveryLabelBox!.x + deliveryLabelBox!.width <= healthLabelBox!.x ||
    healthLabelBox!.y + healthLabelBox!.height <= deliveryLabelBox!.y ||
    deliveryLabelBox!.y + deliveryLabelBox!.height <= healthLabelBox!.y
  );
  expect(labelsOverlap).toBe(false);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByText(longestFlag, { exact: true })).toBeVisible();
  await expectNoInsightOverflow(page);
});

test("delivery AI metrics do not overlap and issues stay inside the card", async ({ page }) => {
  const login = await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  expect(login.ok(), await login.text()).toBeTruthy();

  const listResponse = await page.request.get("/api/v1/delivery-notes?page=1&page_size=1");
  expect(listResponse.ok(), await listResponse.text()).toBeTruthy();
  const noteId = (await listResponse.json()).data.list[0]?.id as number | undefined;
  expect(noteId, "需要至少一张发货单测试数据").toBeDefined();

  const detailResponse = await page.request.get(
    `/api/v1/delivery-notes/${noteId}?include_ai=false`,
  );
  expect(detailResponse.ok(), await detailResponse.text()).toBeTruthy();
  const detailBody = await detailResponse.json();
  const longIssue = "缺少物流商、运单号、运输方式等关键字段，无法判断跨境清关或国内配送节点风险";
  detailBody.data.ai = {
    completion_risk: "high",
    signing_delay_probability: 85,
    issues: [longIssue],
  };
  await page.route(`**/api/v1/delivery-notes/${noteId}?include_ai=true`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(detailBody),
    }),
  );

  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto(`/sales/delivery-notes/${noteId}`);
  const riskLabel = page.getByText("完成风险", { exact: true });
  const delayLabel = page.getByText("签收延迟概率", { exact: true });
  const issue = page.getByText(longIssue, { exact: true });
  await expect(riskLabel).toBeVisible({ timeout: 20_000 });
  await expect(delayLabel).toBeVisible();
  await expect(issue).toBeVisible();

  const riskBox = await riskLabel.boundingBox();
  const delayBox = await delayLabel.boundingBox();
  const issueBox = await issue.boundingBox();
  const cardBox = await page.locator(".sales-ai-insight .ant-card-body").boundingBox();
  expect(riskBox).not.toBeNull();
  expect(delayBox).not.toBeNull();
  expect(issueBox).not.toBeNull();
  expect(cardBox).not.toBeNull();
  const metricsOverlap = !(
    riskBox!.x + riskBox!.width <= delayBox!.x ||
    delayBox!.x + delayBox!.width <= riskBox!.x ||
    riskBox!.y + riskBox!.height <= delayBox!.y ||
    delayBox!.y + delayBox!.height <= riskBox!.y
  );
  expect(metricsOverlap).toBe(false);
  expect(issueBox!.x + issueBox!.width).toBeLessThanOrEqual(cardBox!.x + cardBox!.width + 1);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByText(longIssue, { exact: true })).toBeVisible();
  await expectNoInsightOverflow(page);
});

test("opportunity AI layout handles long actions and concerns", async ({ page }) => {
  await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  const list = await page.request.get("/api/v1/opportunities?page=1&page_size=1");
  const id = (await list.json()).data.list[0]?.id as number;
  expect(id).toBeTruthy();
  const detail = await page.request.get(`/api/v1/opportunities/${id}?include_ai=false`);
  const body = await detail.json();
  const longAction =
    "立即联系客户确认预算审批人、项目时间表和样品验证计划，并在本周内形成下一轮报价策略";
  body.data.ai = {
    risk_level: "medium",
    win_probability: 58,
    next_best_action: longAction,
    key_concerns: ["客户决策链尚未明确且项目交期紧张，需要持续确认关键节点"],
  };
  await page.route(`**/api/v1/opportunities/${id}?include_ai=true`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) }),
  );
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto(`/sales/opportunities/${id}`);
  const insight = page.locator(".sales-ai-insight");
  const risk = insight.getByText("风险等级", { exact: true });
  const probability = insight.getByText("赢单概率", { exact: true });
  const action = page.getByText(longAction, { exact: true });
  await expect(action).toBeVisible({ timeout: 20_000 });
  const riskBox = await risk.boundingBox();
  const probabilityBox = await probability.boundingBox();
  const actionBox = await action.boundingBox();
  const cardBox = await page.locator(".sales-ai-insight .ant-card-body").boundingBox();
  expect(boxesOverlap(riskBox!, probabilityBox!)).toBe(false);
  expect(actionBox!.x + actionBox!.width).toBeLessThanOrEqual(cardBox!.x + cardBox!.width + 1);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByText(longAction, { exact: true })).toBeVisible();
  await expectNoInsightOverflow(page);
});

test("quotation AI layout handles long assessment and suggestions", async ({ page }) => {
  await page.request.post("/api/v1/auth/login", {
    data: { username: USERNAME, password: PASSWORD },
  });
  const list = await page.request.get("/api/v1/quotations?page=1&page_size=1");
  const id = (await list.json()).data.list[0]?.id as number;
  expect(id).toBeTruthy();
  const detail = await page.request.get(`/api/v1/quotations/${id}?include_ai=false`);
  const body = await detail.json();
  const assessment =
    "当前报价毛利空间有限，需要结合客户年度采购量、付款周期和替代料方案综合评估后再确认底价";
  body.data.ai = {
    pricing_health: "fair",
    win_probability: 64,
    margin_assessment: assessment,
    improvement_suggestions: ["补充阶梯价格与有效期，并明确汇率波动和交货周期变化时的价格调整规则"],
  };
  await page.route(`**/api/v1/quotations/${id}?include_ai=true`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) }),
  );
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto(`/sales/quotations/${id}`);
  await page.getByRole("switch").first().click();
  const insight = page.locator(".sales-ai-insight");
  const health = insight.getByText("定价健康度", { exact: true });
  const probability = insight.getByText("赢单概率", { exact: true });
  const assessmentText = page.getByText(assessment, { exact: true });
  await expect(assessmentText).toBeVisible({ timeout: 20_000 });
  const healthBox = await health.boundingBox();
  const probabilityBox = await probability.boundingBox();
  const assessmentBox = await assessmentText.boundingBox();
  const cardBox = await page.locator(".sales-ai-insight .ant-card-body").boundingBox();
  expect(boxesOverlap(healthBox!, probabilityBox!)).toBe(false);
  expect(assessmentBox!.x + assessmentBox!.width).toBeLessThanOrEqual(
    cardBox!.x + cardBox!.width + 1,
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await page.getByRole("switch").first().click();
  await expect(page.getByText(assessment, { exact: true })).toBeVisible();
  await expectNoInsightOverflow(page);
});

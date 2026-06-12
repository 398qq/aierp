// Screenshot the Commission list page (and login if needed).
// Run from the repo root:  /home/ttdiy/.local/bin/playwright screenshot scripts/screenshot-commission.mjs http://localhost:3002/login docs/screenshots/01-login.png
//
// Or use the runner: node scripts/screenshot-commission.mjs

import { chromium } from "/home/ttdiy/.local/lib/node_modules/playwright/index.mjs";
import { mkdirSync } from "node:fs";

const OUT_DIR = "/home/ttdiy/aierp/docs/screenshots";
mkdirSync(OUT_DIR, { recursive: true });

const FRONTEND = "http://localhost:3002";
const USERNAME = process.env.AIERP_LOGIN_USERNAME ?? "admin";
const PASSWORD = process.env.AIERP_LOGIN_PASSWORD ?? "admin123";

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
  locale: "zh-CN",
});
const page = await ctx.newPage();

console.log("→ login page");
await page.goto(`${FRONTEND}/login`, { waitUntil: "networkidle" });
await page.screenshot({ path: `${OUT_DIR}/01-login.png`, fullPage: false });
console.log("  saved 01-login.png");

// Login as admin
console.log("→ login as admin");
await page.fill('input[placeholder*="用户"], input[type="text"]', USERNAME);
await page.fill('input[type="password"]', PASSWORD);
await page.click('button[type="submit"]');
await page.waitForURL(`${FRONTEND}/`, { timeout: 10000 });
await page.waitForLoadState("networkidle");
await page.screenshot({ path: `${OUT_DIR}/02-dashboard.png`, fullPage: false });
console.log("  saved 02-dashboard.png");

// Navigate to commission list
console.log("→ /finance/commissions");
await page.goto(`${FRONTEND}/finance/commissions`, { waitUntil: "networkidle" });
await page.waitForTimeout(800); // let table render
await page.screenshot({ path: `${OUT_DIR}/03-commission-list.png`, fullPage: false });
console.log("  saved 03-commission-list.png");

// Open the create drawer
console.log("→ open create drawer");
try {
  await page.click('button:has-text("新建佣金")', { timeout: 3000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT_DIR}/04-commission-drawer.png`, fullPage: false });
  console.log("  saved 04-commission-drawer.png");
} catch (e) {
  console.log("  (drawer button not found, skipped)");
}

await browser.close();
console.log("\n✓ done. screenshots in", OUT_DIR);

// End-to-end smoke test: drives the real dashboard against a real running backend with a
// headless Chromium (Playwright). Not part of `npm run lint`/CI by default -- it needs the
// backend up on :8000 (see ../../README.md) and makes live network calls (discovery hits the
// real HN/YC sources), so it's a manual/pre-release check, not a fast unit test.
//
// Usage (from frontend/):
//   npx playwright install chromium   # once
//   npm run dev &                     # in another terminal, or let this assume it's running
//   node e2e/smoke.mjs
//
// Screenshots land in e2e/screenshots/ (gitignored). Exits non-zero if the browser logged any
// console error, so it doubles as a rough regression check, not just a screenshot dump.

import { mkdirSync } from "node:fs";
import { chromium } from "playwright";

const SCREENSHOT_DIR = process.argv[2] ?? new URL("./screenshots", import.meta.url).pathname;
mkdirSync(SCREENSHOT_DIR, { recursive: true });

const browser = await chromium.launch({ args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const consoleErrors = [];
page.on("console", (msg) => {
  if (msg.type() === "error") consoleErrors.push(msg.text());
});
page.on("pageerror", (err) => consoleErrors.push(`pageerror: ${err.message}`));

async function shot(name) {
  await page.screenshot({ path: `${SCREENSHOT_DIR}/${name}.png` });
  console.log(`screenshot: ${name}.png`);
}

console.log("nav /");
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await shot("01-initial");

const nameInput = page.locator("#full-name");
if (await nameInput.isVisible().catch(() => false)) {
  console.log("onboarding form visible -- filling it out");
  await nameInput.fill("Playwright Smoke Test");
  await page.locator('button:has-text("Continue")').click();
  await page.waitForSelector("text=Set up your search profile", { timeout: 15000 });
  await shot("02-after-onboarding");

  console.log("creating the default search profile");
  await page.locator('button:has-text("Create search profile")').click();
  await page.waitForSelector(".tabs .tab", { timeout: 15000 });
  await shot("03-profiles-created");
} else {
  console.log("candidate already exists -- skipping onboarding");
}

await page.waitForSelector(".tabs .tab", { timeout: 15000 });
await shot("04-dashboard-loaded");

console.log("selecting Startup Outreach tab and running discovery");
await page.locator('.tab:has-text("Startup Outreach")').click();
await page.locator('button:has-text("Run discovery")').click();
await page.waitForSelector("tbody tr", { timeout: 60000 });
await shot("05-jobs-discovered");

console.log("clicking the first job row");
await page.locator("tbody tr").first().click();
await page.waitForSelector(".drawer", { timeout: 10000 });
await shot("06-job-detail-drawer");

console.log("running company research");
const researchButton = page.locator('.drawer button:has-text("Run research")');
if (await researchButton.isVisible().catch(() => false)) {
  await researchButton.click();
  await page.waitForTimeout(3000);
  await shot("07-research-done");
}

console.log("generating outreach (if enabled for this profile)");
const outreachButton = page.locator('.drawer button:has-text("Generate outreach")');
if (await outreachButton.isVisible().catch(() => false)) {
  await outreachButton.click();
  await page.waitForSelector(".message-variant", { timeout: 20000 });
  await shot("08-outreach-generated");

  console.log("editing the first message variant and saving");
  const firstTextarea = page.locator(".message-variant textarea").first();
  await firstTextarea.fill("Hand-edited by the Playwright smoke test.");
  await page.locator('.message-variant button:has-text("Save edits")').first().click();
  await page.waitForTimeout(1000);
  await shot("09-message-edited");
} else {
  console.log("outreach section not present");
}

console.log("changing status via dropdown");
const statusSelect = page.locator(".drawer select");
await statusSelect.selectOption("READY_TO_CONTACT");
await page.waitForTimeout(1000);
await shot("10-status-changed");

console.log("closing drawer, confirming table reflects new status");
await page.locator(".drawer-close").click();
await page.waitForTimeout(500);
await shot("11-back-to-table");

console.log("opening the All Applications tab -- cross-profile search/filter/sort");
await page.locator('.tab:has-text("All Applications")').click();
await page.waitForSelector(".filter-bar", { timeout: 10000 });
await page.waitForTimeout(500);
await shot("12-all-applications");

const jobCompanySearch = page.locator(
  'input[aria-label="Search applications by job title or company"]'
);
await jobCompanySearch.fill("engineer");
await page.waitForTimeout(600); // debounced search
await shot("13-all-applications-search");
await jobCompanySearch.fill("");

console.log("filtering by location and visa status");
await page.locator('input[aria-label="Filter by location"]').fill("New York");
await page.waitForTimeout(300);
await shot("13b-all-applications-location-filter");
await page.locator('select[aria-label="Filter by visa sponsorship status"]').selectOption("");
await page.locator('input[aria-label="Filter by location"]').fill("");

await page.locator("th.sortable").first().click();
await page.waitForTimeout(300);
await shot("14-all-applications-sorted");

const firstAppRow = page.locator("tbody tr").first();
if (await firstAppRow.isVisible().catch(() => false)) {
  await firstAppRow.click();
  await page.waitForSelector(".drawer", { timeout: 10000 });
  await shot("15-all-applications-detail");

  console.log("checking visa sponsorship for the selected job");
  const visaButton = page.locator(
    '.drawer button:has-text("Check visa sponsorship"), .drawer button:has-text("Re-check")'
  );
  if (await visaButton.isVisible().catch(() => false)) {
    await visaButton.click();
    await page.waitForTimeout(2000);
    await shot("16-visa-checked");
  }

  await page.locator(".drawer-close").click();
}

await browser.close();

if (consoleErrors.length > 0) {
  console.error("console errors detected:", JSON.stringify(consoleErrors, null, 2));
  process.exit(1);
}
console.log("OK -- no console errors");

const baseUrl = process.env.PEQUIFLUX_UI_URL || "http://127.0.0.1:8501/";
const viewport = { width: 1440, height: 1200 };
const playwrightModule = process.env.PLAYWRIGHT_MODULE || "playwright";
const { chromium } = await import(playwrightModule);
const captureMode = process.env.PEQUIFLUX_SCREENSHOT_MODE || "full";

const shots = {
  initial: "assets/screenshots/pequiflux-ui-01-initial.png",
  inputsLoaded: "assets/screenshots/pequiflux-ui-02-inputs-loaded.png",
  canonical: "assets/screenshots/pequiflux-ui.png",
  result: "assets/screenshots/pequiflux-ui-03-decision-result.png",
  evidence: "assets/screenshots/pequiflux-ui-04-evidence-and-operator.png",
  tools: "assets/screenshots/pequiflux-ui-05-tool-audit.png",
  writeup: "docs/writeup_assets/pequiflux-ui.png",
};

async function waitForApp(page) {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.getByText("PequiFlux Yard Copilot").first().waitFor({ timeout: 120000 });
  await page.waitForTimeout(1200);
}

async function clickButton(page, label) {
  await page.getByRole("button", { name: label }).first().click();
  await page.waitForTimeout(1200);
}

async function screenshot(page, path) {
  await page.screenshot({ path, fullPage: false });
}

async function screenshotElement(locator, path) {
  await locator.screenshot({ path });
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });

try {
  await waitForApp(page);
  if (captureMode === "full") {
    await screenshot(page, shots.initial);

    await clickButton(page, "Carregar exemplo");
    await page.waitForTimeout(2000);
    await screenshot(page, shots.inputsLoaded);

    await clickButton(page, "Carregar e analisar exemplo");
  }
  await page.getByText("Momento da decisão").first().waitFor({ timeout: 180000 });
  await screenshot(page, shots.canonical);
  await screenshot(page, shots.result);
  await screenshot(page, shots.writeup);

  await page.getByText("Mensagem ao motorista").first().scrollIntoViewIfNeeded();
  await page.waitForTimeout(900);
  await screenshot(page, shots.evidence);

  await page.getByText("Ver auditoria técnica").first().click();
  const planner = page.getByText("Gemma Tool Planner").first();
  await planner.waitFor({ timeout: 30000 });
  const toolsCard = page.locator(".tools-card").first();
  await toolsCard.waitFor({ timeout: 30000 });
  await page.waitForTimeout(900);
  await screenshotElement(toolsCard, shots.tools);
} finally {
  await browser.close();
}

for (const path of Object.values(shots)) {
  console.log(path);
}

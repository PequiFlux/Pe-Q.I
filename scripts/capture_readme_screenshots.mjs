const baseUrl = process.env.PEQUIFLUX_UI_URL || "http://127.0.0.1:8501/";
const viewport = { width: 1440, height: 1200 };
const playwrightModule = process.env.PLAYWRIGHT_MODULE || "playwright";
const { chromium } = await import(playwrightModule);
const captureMode = process.env.PEQUIFLUX_SCREENSHOT_MODE || "full";
const language =
  (process.env.PEQUIFLUX_SCREENSHOT_LANGUAGE ||
    process.env.PEQUIFLUX_UI_DEFAULT_LANGUAGE ||
    "en")
    .trim()
    .toLowerCase()
    .startsWith("pt")
    ? "pt"
    : "en";

const copy = {
  en: {
    languageOption: "English",
    load: "Load example",
    loadAnalyze: "Load and analyze example",
    decisionMoment: "Decision moment",
    analysisResult: "Analysis result",
    driverMessage: "Message to driver",
    audit: "View technical audit",
    planner: "Gemma Tool Planner",
    rawPayload: "Raw payload",
    provenance: "provenance",
    sourceHashes: "source_hashes",
  },
  pt: {
    languageOption: "Português",
    load: "Carregar exemplo",
    loadAnalyze: "Carregar e analisar exemplo",
    decisionMoment: "Momento da decisão",
    analysisResult: "Resultado da análise",
    driverMessage: "Mensagem ao motorista",
    audit: "Ver auditoria técnica",
    planner: "Gemma Tool Planner",
    rawPayload: "Payload bruto",
    provenance: "provenance",
    sourceHashes: "source_hashes",
  },
}[language];

const shots = {
  initial: "assets/screenshots/pequiflux-ui-01-initial.png",
  inputsLoaded: "assets/screenshots/pequiflux-ui-02-inputs-loaded.png",
  canonical: "assets/screenshots/pequiflux-ui.png",
  result: "assets/screenshots/pequiflux-ui-03-decision-result.png",
  evidence: "assets/screenshots/pequiflux-ui-04-evidence-and-operator.png",
  tools: "assets/screenshots/pequiflux-ui-05-tool-audit.png",
  payloadProvenance: "assets/screenshots/pequiflux-ui-06-payload-provenance.png",
  payloadHashes: "assets/screenshots/pequiflux-ui-07-payload-source-hashes.png",
  writeup: "docs/writeup_assets/pequiflux-ui.png",
};

async function waitForApp(page) {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.getByText("PequiFlux Yard Copilot").first().waitFor({ timeout: 120000 });
  await page.waitForTimeout(1200);
}

async function ensureLanguage(page) {
  const option = page.getByLabel(copy.languageOption).first();
  if ((await option.count()) > 0) {
    await option.check({ force: true });
    await page.waitForTimeout(1200);
  }
  await page.getByText(copy.load, { exact: true }).first().waitFor({ timeout: 30000 });
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

async function scrollToText(page, text, top = 96) {
  const locator = page.getByText(text).first();
  await locator.waitFor({ timeout: 120000 });
  await locator.evaluate((element, targetTop) => {
    element.scrollIntoView({ block: "start", inline: "nearest" });
    window.scrollBy(0, -targetTop);
    let parent = element.parentElement;
    while (parent) {
      if (parent.scrollHeight > parent.clientHeight) {
        parent.scrollTop = Math.max(0, parent.scrollTop - targetTop);
      }
      parent = parent.parentElement;
    }
  }, top);
  await page.waitForTimeout(1100);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });

try {
  await waitForApp(page);
  await ensureLanguage(page);
  if (captureMode === "full") {
    await screenshot(page, shots.initial);

    await clickButton(page, copy.load);
    await page.waitForTimeout(2000);
    await screenshot(page, shots.inputsLoaded);

    await clickButton(page, copy.loadAnalyze);
  }
  await page.getByText(copy.decisionMoment).first().waitFor({ timeout: 180000 });
  await scrollToText(page, copy.analysisResult, 70);
  await screenshot(page, shots.canonical);
  await screenshot(page, shots.result);
  await screenshot(page, shots.writeup);

  await scrollToText(page, copy.driverMessage, 120);
  await page.waitForTimeout(900);
  await screenshot(page, shots.evidence);

  await page.getByText(copy.audit).first().click();
  const planner = page.getByText(copy.planner).first();
  await planner.waitFor({ timeout: 30000 });
  const toolsCard = page.locator(".tools-card").first();
  await toolsCard.waitFor({ timeout: 30000 });
  await page.waitForTimeout(900);
  await screenshotElement(toolsCard, shots.tools);

  await page.getByText(copy.rawPayload).first().click();
  await scrollToText(page, copy.provenance, 180);
  await screenshot(page, shots.payloadProvenance);
  await scrollToText(page, copy.sourceHashes, 180);
  await screenshot(page, shots.payloadHashes);
} finally {
  await browser.close();
}

for (const path of Object.values(shots)) {
  console.log(path);
}

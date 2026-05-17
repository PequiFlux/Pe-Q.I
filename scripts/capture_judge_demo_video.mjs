import { copyFile, mkdir, unlink } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const baseUrl = process.env.PEQUIFLUX_UI_URL || "http://127.0.0.1:8501/";
const outputPath = resolve(
  process.env.PEQUIFLUX_JUDGE_VIDEO_PATH ||
    "artifacts/judge-demo/pequiflux-gemma-proof.webm",
);
const tempDir = resolve(
  process.env.PEQUIFLUX_JUDGE_VIDEO_TMPDIR ||
    "artifacts/judge-demo/.tmp-video",
);
const viewport = { width: 1440, height: 1200 };
const playwrightModule = process.env.PLAYWRIGHT_MODULE || "playwright";
const playwright = await import(playwrightModule);
const chromium = playwright.chromium || playwright.default?.chromium;

if (!chromium) {
  throw new Error(`Unable to resolve chromium from module: ${playwrightModule}`);
}

async function waitForApp(page) {
  console.log("step=wait_for_app:start");
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.getByText("PequiFlux Yard Copilot").first().waitFor({ timeout: 120000 });
  await page.getByText("Operational input").first().waitFor({ timeout: 120000 });
  await page.waitForTimeout(1200);
  console.log("step=wait_for_app:done");
}

async function assertEnglishInterface(page, marker = "initial") {
  const portugueseMarkers = [
    "Momento da decisão",
    "Prova Gemma 4",
    "Ver auditoria técnica",
    "Modo teste ativo",
    "Analisar com Gemma 4",
    "Chamar TRK",
    "Fila de caminhões",
  ];

  for (const text of portugueseMarkers) {
    const locator = page.getByText(text, { exact: false });
    const count = await locator.count();
    for (let index = 0; index < count; index += 1) {
      if (await locator.nth(index).isVisible()) {
        throw new Error(
          `Judge demo capture failed: Portuguese UI text "${text}" is visible at ${marker}.`,
        );
      }
    }
  }
}

async function ensureNotInTestMode(page) {
  console.log("step=ensure_runtime:start");
  await page.getByText("Decision moment").first().waitFor({ timeout: 180000 });
  const bodyText = await page.locator("body").innerText();
  const runtimeMatch = bodyText.match(/Ollama\s*[·•-]\s*(gemma4:(e4b|e2b))/);

  if (!runtimeMatch) {
    throw new Error("Judge demo capture failed: runtime proof card did not show Ollama Gemma.");
  }

  if (/Test mode is active|Do not use test mode for the judge recording\./.test(bodyText)) {
    throw new Error("Judge demo capture refused: UI is still showing test mode.");
  }

  await assertEnglishInterface(page, "runtime proof");
  const runtimeLabel = `Ollama · ${runtimeMatch[1]}`;
  console.log(`step=ensure_runtime:done runtime=${runtimeLabel}`);
  return runtimeLabel;
}

async function clickAnalyze(page) {
  console.log("step=click_analyze:start");
  const readyMarker = page.getByText("Decision moment").first();
  if ((await readyMarker.count()) > 0 && (await readyMarker.isVisible())) {
    console.log("step=click_analyze:already_ready");
    return;
  }

  await page
    .getByRole("button", { name: /Load and analyze example/ })
    .first()
    .click();
  console.log("step=click_analyze:clicked");
}

async function showQueueOptimization(page) {
  console.log("step=show_queue_optimization:start");
  await page.getByText("Decision queue").first().waitFor({ timeout: 60000 });
  await page.getByText("Decision queue").first().scrollIntoViewIfNeeded();
  await page.waitForTimeout(2200);
  await page.getByText("called now").first().waitFor({ timeout: 30000 });
  console.log("step=show_queue_optimization:done");
}

async function revealProofSequence(page) {
  console.log("step=reveal_proof:start");
  await page.getByText("Decision moment").first().waitFor({ timeout: 180000 });
  await page.waitForTimeout(1600);

  const proofCard = page.getByText("Judge proof").first();
  await proofCard.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1800);

  await showQueueOptimization(page);

  const auditToggle = page.getByText("View technical audit").first();
  await auditToggle.scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  await auditToggle.click();

  await page.getByText("Auditable trail").first().waitFor({ timeout: 30000 });
  const planner = page.getByText("Gemma Tool Planner").first();
  await planner.waitFor({ timeout: 30000 });
  await planner.scrollIntoViewIfNeeded();
  await page.waitForTimeout(3200);
  await assertEnglishInterface(page, "audit proof");
  console.log("step=reveal_proof:done");
}

await mkdir(dirname(outputPath), { recursive: true });
await mkdir(tempDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport,
  recordVideo: {
    dir: tempDir,
    size: viewport,
  },
});
const page = await context.newPage();
const video = page.video();

let runtimeLabel = "unknown";

try {
  await waitForApp(page);
  await assertEnglishInterface(page, "initial load");
  await clickAnalyze(page);
  runtimeLabel = await ensureNotInTestMode(page);
  await revealProofSequence(page);
  await page.waitForTimeout(1000);
  console.log("step=capture:ready_to_close");
} finally {
  await context.close();
  await browser.close();
}

if (!video) {
  throw new Error("Judge demo capture failed: Playwright video handle is unavailable.");
}

const recordedVideoPath = await video.path();
await copyFile(recordedVideoPath, outputPath);
await unlink(recordedVideoPath);
console.log(`video=${outputPath}`);
console.log(`runtime=${runtimeLabel}`);

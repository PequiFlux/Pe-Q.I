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
  await page.waitForTimeout(1200);
  console.log("step=wait_for_app:done");
}

async function ensureNotInTestMode(page) {
  console.log("step=ensure_runtime:start");
  await page.getByText("Momento da decisão").first().waitFor({ timeout: 180000 });
  const bodyText = await page.locator("body").innerText();
  const runtimeMatch = bodyText.match(/Ollama\s*[·•-]\s*(gemma4:(e4b|e2b))/);

  if (!runtimeMatch) {
    throw new Error("Judge demo capture failed: runtime proof card did not show Ollama Gemma.");
  }

  if (/Modo teste ativo|Não use modo teste para a gravação da banca\./.test(bodyText)) {
    throw new Error("Judge demo capture refused: UI is still showing test mode.");
  }

  const runtimeLabel = `Ollama · ${runtimeMatch[1]}`;
  console.log(`step=ensure_runtime:done runtime=${runtimeLabel}`);
  return runtimeLabel;
}

async function clickAnalyze(page) {
  console.log("step=click_analyze:start");
  const readyMarker = page.getByText("Momento da decisão").first();
  if ((await readyMarker.count()) > 0 && (await readyMarker.isVisible())) {
    console.log("step=click_analyze:already_ready");
    return;
  }

  await page
    .getByRole("button", { name: /Carregar e analisar exemplo|Load and analyze example/ })
    .first()
    .click();
  console.log("step=click_analyze:clicked");
}

async function revealProofSequence(page) {
  console.log("step=reveal_proof:start");
  await page.getByText("Momento da decisão").first().waitFor({ timeout: 180000 });
  await page.waitForTimeout(1600);

  const proofCard = page.getByText("Prova Gemma 4 para a banca").first();
  await proofCard.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1800);

  const auditToggle = page.getByText("Ver auditoria técnica").first();
  await auditToggle.scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  await auditToggle.click();

  const planner = page.getByText("Gemma Tool Planner").first();
  await planner.waitFor({ timeout: 30000 });
  await planner.scrollIntoViewIfNeeded();
  await page.waitForTimeout(2200);
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

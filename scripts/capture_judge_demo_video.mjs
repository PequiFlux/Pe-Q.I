import { copyFile, mkdir, unlink } from "node:fs/promises";
import { spawn } from "node:child_process";
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

function runFfmpeg(args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn("ffmpeg", args, { stdio: "inherit" });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolvePromise();
      } else {
        reject(new Error(`ffmpeg exited with code ${code}`));
      }
    });
  });
}

async function enhanceRecordedVideo(inputPath, finalPath) {
  const enhancedPath = `${finalPath}.enhanced.tmp.webm`;
  const videoFilter = [
    "scale=1536:-2:flags=lanczos",
    "crop=1536:1080:0:100",
    "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x111418",
    "unsharp=5:5:0.65:3:3:0.2",
    "eq=contrast=1.06:saturation=1.06:gamma=1.02",
    "fps=30",
  ].join(",");

  await runFfmpeg([
    "-hide_banner",
    "-y",
    "-i",
    inputPath,
    "-vf",
    videoFilter,
    "-an",
    "-c:v",
    "libvpx-vp9",
    "-deadline",
    "good",
    "-crf",
    "32",
    "-b:v",
    "0",
    "-row-mt",
    "1",
    "-pix_fmt",
    "yuv420p",
    enhancedPath,
  ]);
  await copyFile(enhancedPath, finalPath);
  await unlink(enhancedPath).catch(() => undefined);
}

async function installPresentationLayer(page) {
  await page.addStyleTag({
    content: `
      .judge-demo-cursor {
        position: fixed;
        left: 0;
        top: 0;
        z-index: 2147483647;
        width: 34px;
        height: 34px;
        pointer-events: none;
        opacity: 0;
        transform: translate3d(40px, 40px, 0);
        transition: opacity 180ms ease;
        filter: drop-shadow(0 10px 18px rgba(8, 22, 38, 0.36));
      }

      .judge-demo-cursor svg {
        display: block;
        width: 34px;
        height: 34px;
      }

      .judge-demo-spotlight {
        position: fixed;
        z-index: 2147483646;
        pointer-events: none;
        border: 4px solid rgba(252, 191, 73, 0.96);
        border-radius: 18px;
        box-shadow:
          0 0 0 9999px rgba(5, 15, 30, 0.12),
          0 0 0 8px rgba(252, 191, 73, 0.22),
          0 20px 45px rgba(5, 15, 30, 0.24);
        opacity: 0;
        transform: translate3d(0, 0, 0) scale(0.985);
        transition:
          left 360ms ease,
          top 360ms ease,
          width 360ms ease,
          height 360ms ease,
          opacity 220ms ease,
          transform 360ms ease;
      }

      .judge-demo-spotlight.is-visible {
        opacity: 1;
        transform: translate3d(0, 0, 0) scale(1);
      }

      .judge-demo-pulse {
        position: fixed;
        z-index: 2147483645;
        width: 16px;
        height: 16px;
        margin-left: -8px;
        margin-top: -8px;
        pointer-events: none;
        border: 3px solid rgba(23, 128, 108, 0.95);
        border-radius: 999px;
        animation: judge-demo-pulse 720ms ease-out forwards;
      }

      @keyframes judge-demo-pulse {
        from {
          opacity: 0.9;
          transform: scale(0.7);
        }
        to {
          opacity: 0;
          transform: scale(5.4);
        }
      }
    `,
  });

  await page.evaluate(() => {
    const cursor = document.createElement("div");
    cursor.className = "judge-demo-cursor";
    cursor.innerHTML = `
      <svg viewBox="0 0 42 42" aria-hidden="true">
        <path
          d="M8 4l24 21-12 2.2 7.3 10.9-5.4 3.6-7.1-10.7-7.7 8.2L8 4z"
          fill="#f8fafc"
          stroke="#0f2f3d"
          stroke-width="2.7"
          stroke-linejoin="round"
        />
      </svg>
    `;
    document.body.appendChild(cursor);

    const spotlight = document.createElement("div");
    spotlight.className = "judge-demo-spotlight";
    document.body.appendChild(spotlight);

    window.__judgeDemoPresentation = {
      cursor,
      cursorX: 56,
      cursorY: 56,
      spotlight,
    };
  });
}

async function easeMouseTo(page, x, y, duration = 900) {
  await page.evaluate(
    ({ x: targetX, y: targetY, durationMs }) =>
      new Promise((resolve) => {
        const state = window.__judgeDemoPresentation;
        if (!state) {
          resolve();
          return;
        }

        const startX = state.cursorX;
        const startY = state.cursorY;
        const startTime = performance.now();
        state.cursor.style.opacity = "1";

        function easeInOutCubic(t) {
          return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        }

        function frame(now) {
          const progress = Math.min((now - startTime) / durationMs, 1);
          const eased = easeInOutCubic(progress);
          const currentX = startX + (targetX - startX) * eased;
          const currentY = startY + (targetY - startY) * eased;
          state.cursorX = currentX;
          state.cursorY = currentY;
          state.cursor.style.transform = `translate3d(${currentX}px, ${currentY}px, 0)`;

          if (progress < 1) {
            requestAnimationFrame(frame);
          } else {
            resolve();
          }
        }

        requestAnimationFrame(frame);
      }),
    { x, y, durationMs: duration },
  );
  await page.mouse.move(x + 3, y + 3, { steps: 12 });
}

async function scrollToLocator(page, locator, offsetRatio = 0.22) {
  await locator.waitFor({ timeout: 120000 });
  await locator.evaluate(
    (element, ratio) => {
      const rect = element.getBoundingClientRect();
      const targetTop = window.scrollY + rect.top - window.innerHeight * ratio;
      window.scrollTo({ top: Math.max(0, targetTop), behavior: "smooth" });
    },
    offsetRatio,
  );
  await page.waitForTimeout(1300);
}

async function scrollToSafeFrame(page, locator, options = {}) {
  const { top = 120, settle = 950 } = options;
  await locator.waitFor({ timeout: 120000 });
  await locator.evaluate((element, targetTop) => {
    const rect = element.getBoundingClientRect();
    const desiredTop = window.scrollY + rect.top - targetTop;
    window.scrollTo({ top: Math.max(0, desiredTop), behavior: "smooth" });
  }, top);
  await page.waitForTimeout(settle);
  await page.waitForFunction(
    ({ selectorText, minTop, maxTop }) => {
      const candidates = Array.from(document.body.querySelectorAll("*"));
      const target = candidates.find((element) =>
        element.textContent?.includes(selectorText),
      );
      if (!target) {
        return true;
      }
      const rect = target.getBoundingClientRect();
      return rect.top >= minTop && rect.top <= maxTop;
    },
    {
      selectorText: await locator.evaluate((element) => element.textContent?.trim() || ""),
      minTop: 24,
      maxTop: viewport.height * 0.72,
    },
    { timeout: 3500 },
  ).catch(() => undefined);
}

function clampFrame(frame) {
  const left = Math.max(12, Math.min(frame.left, viewport.width - 120));
  const top = Math.max(12, Math.min(frame.top, viewport.height - 120));
  const width = Math.max(140, Math.min(frame.width, viewport.width - left - 18));
  const height = Math.max(70, Math.min(frame.height, viewport.height - top - 18));
  return { left, top, width, height };
}

async function spotlightLocator(page, locator, options = {}) {
  const {
    padding = 18,
    duration = 850,
    offsetRatio = 0.22,
    frameBelow = 0,
    minFrameWidth = 0,
    safeTop,
  } = options;
  if (safeTop !== undefined) {
    await scrollToSafeFrame(page, locator, { top: safeTop });
  } else {
    await scrollToLocator(page, locator, offsetRatio);
  }
  const box = await locator.boundingBox();
  if (!box) {
    throw new Error("Judge demo capture failed: unable to locate spotlight target.");
  }

  const frameWidth = Math.max(box.width + padding * 2, minFrameWidth);
  const rect = clampFrame({
    left: box.x - padding,
    top: box.y - padding,
    width: frameWidth,
    height: box.height + padding * 2 + frameBelow,
  });
  const cursorX = Math.min(rect.left + rect.width - 26, viewport.width - 52);
  const cursorY = Math.min(rect.top + 26, viewport.height - 52);

  await easeMouseTo(page, cursorX, cursorY, duration);
  await page.evaluate(({ left, top, width, height }) => {
    const state = window.__judgeDemoPresentation;
    if (!state) {
      return;
    }
    state.spotlight.style.left = `${left}px`;
    state.spotlight.style.top = `${top}px`;
    state.spotlight.style.width = `${width}px`;
    state.spotlight.style.height = `${height}px`;
    state.spotlight.classList.add("is-visible");
  }, rect);
  await page.waitForTimeout(950);
}

async function spotlightSection(page, titleLocator, options = {}) {
  const {
    padding = 24,
    duration = 950,
    frameBelow = 520,
    minFrameWidth = 980,
    safeTop = 118,
    hold = 1300,
  } = options;
  await spotlightLocator(page, titleLocator, {
    padding,
    duration,
    frameBelow,
    minFrameWidth,
    safeTop,
  });
  await page.waitForTimeout(hold);
}

async function clearSpotlight(page) {
  await page.evaluate(() => {
    const state = window.__judgeDemoPresentation;
    state?.spotlight.classList.remove("is-visible");
  });
  await page.waitForTimeout(300);
}

async function clickLocatorWithPointer(page, locator) {
  await spotlightLocator(page, locator, { padding: 14, duration: 700, offsetRatio: 0.28 });
  const box = await locator.boundingBox();
  if (!box) {
    throw new Error("Judge demo capture failed: unable to click target.");
  }
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await easeMouseTo(page, x, y, 420);
  await page.evaluate(({ x: pulseX, y: pulseY }) => {
    const pulse = document.createElement("div");
    pulse.className = "judge-demo-pulse";
    pulse.style.left = `${pulseX}px`;
    pulse.style.top = `${pulseY}px`;
    document.body.appendChild(pulse);
    window.setTimeout(() => pulse.remove(), 780);
  }, { x, y });
  await locator.click();
  await page.waitForTimeout(900);
}

async function waitForApp(page) {
  console.log("step=wait_for_app:start");
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.getByText("PequiFlux Yard Copilot").first().waitFor({ timeout: 120000 });
  await page.getByText("Operational input").first().waitFor({ timeout: 120000 });
  await installPresentationLayer(page);
  await easeMouseTo(page, 104, 94, 700);
  await spotlightSection(page, page.getByText("PequiFlux Yard Copilot").first(), {
    padding: 20,
    duration: 720,
    frameBelow: 210,
    minFrameWidth: 940,
    safeTop: 68,
    hold: 900,
  });
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
    .waitFor({ timeout: 120000 });
  await clickLocatorWithPointer(
    page,
    page.getByRole("button", { name: /Load and analyze example/ }).first(),
  );
  console.log("step=click_analyze:clicked");
}

async function showQueueOptimization(page) {
  console.log("step=show_queue_optimization:start");
  const queueTitle = page.getByText("Decision queue").first();
  await queueTitle.waitFor({ timeout: 60000 });
  await spotlightSection(page, queueTitle, {
    padding: 22,
    duration: 980,
    frameBelow: 650,
    minFrameWidth: 1060,
    safeTop: 100,
    hold: 1500,
  });
  await page.getByText("called now").first().waitFor({ timeout: 30000 });
  await spotlightLocator(page, page.getByText("called now").first(), {
    padding: 18,
    frameBelow: 160,
    minFrameWidth: 620,
    duration: 850,
    safeTop: 270,
  });
  console.log("step=show_queue_optimization:done");
}

async function revealProofSequence(page) {
  console.log("step=reveal_proof:start");
  await page.getByText("Decision moment").first().waitFor({ timeout: 180000 });
  await spotlightSection(page, page.getByText("Decision moment").first(), {
    padding: 24,
    duration: 900,
    frameBelow: 600,
    minFrameWidth: 1080,
    safeTop: 92,
    hold: 1600,
  });

  const proofCard = page.getByText("Judge proof").first();
  await spotlightSection(page, proofCard, {
    padding: 22,
    duration: 940,
    frameBelow: 500,
    minFrameWidth: 920,
    safeTop: 110,
    hold: 1400,
  });

  await showQueueOptimization(page);

  const auditToggle = page.getByText("View technical audit").first();
  await clickLocatorWithPointer(page, auditToggle);

  await page.getByText("Auditable trail").first().waitFor({ timeout: 30000 });
  const planner = page.getByText("Gemma Tool Planner").first();
  await planner.waitFor({ timeout: 30000 });
  await spotlightSection(page, page.getByText("Auditable trail").first(), {
    padding: 22,
    duration: 900,
    frameBelow: 620,
    minFrameWidth: 1080,
    safeTop: 96,
    hold: 1350,
  });
  await spotlightLocator(page, planner, {
    padding: 22,
    frameBelow: 360,
    minFrameWidth: 980,
    duration: 980,
    safeTop: 160,
  });
  await clearSpotlight(page);
  await page.waitForTimeout(1600);
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
await enhanceRecordedVideo(recordedVideoPath, outputPath);
await unlink(recordedVideoPath);
console.log(`video=${outputPath}`);
console.log(`runtime=${runtimeLabel}`);

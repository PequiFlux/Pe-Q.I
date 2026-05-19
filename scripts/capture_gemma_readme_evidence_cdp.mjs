import { mkdir, rm, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { spawn } from "node:child_process";

const baseUrl = process.env.PEQUIFLUX_UI_URL || "http://127.0.0.1:8501/";
const chromePath =
  process.env.CHROME_PATH || "/ms-playwright/chromium-1181/chrome-linux/chrome";
const remotePort = Number(process.env.CHROME_REMOTE_DEBUGGING_PORT || "9224");
const viewport = { width: 1440, height: 1100 };

const labels = {
  loadAnalyze: "Carregar e analisar exemplo",
  decisionMoment: "Momento da decisão",
  liveProof: "Gemma 4 executando no fluxo real",
  runtime: "Ollama · gemma4:e2b",
  interpreter: "Documento interpretado pelo Gemma 4",
  audit: "Ver auditoria técnica",
  planner: "Gemma Tool Planner",
};

const shots = {
  proof: "assets/screenshots/pequiflux-gemma-01-live-result-proof.png",
  extraction: "assets/screenshots/pequiflux-gemma-02-ticket-interpretation.png",
  planner: "assets/screenshots/pequiflux-gemma-03-tool-planner.png",
};

class CdpClient {
  constructor(webSocketUrl) {
    this.webSocketUrl = webSocketUrl;
    this.id = 0;
    this.pending = new Map();
  }

  async connect() {
    this.ws = new WebSocket(this.webSocketUrl);
    this.ws.addEventListener("message", (event) => {
      const payload = JSON.parse(event.data);
      if (!payload.id) {
        return;
      }
      const waiter = this.pending.get(payload.id);
      if (!waiter) {
        return;
      }
      this.pending.delete(payload.id);
      if (payload.error) {
        waiter.reject(new Error(JSON.stringify(payload.error)));
      } else {
        waiter.resolve(payload.result || {});
      }
    });
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
  }

  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }

  close() {
    this.ws.close();
  }
}

async function delay(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitFor(condition, description, timeout = 300000) {
  const started = Date.now();
  let lastError;
  while (Date.now() - started < timeout) {
    try {
      if (await condition()) {
        return;
      }
    } catch (error) {
      lastError = error;
    }
    await delay(500);
  }
  const suffix = lastError ? ` Last error: ${lastError.message}` : "";
  throw new Error(`Timed out waiting for ${description}.${suffix}`);
}

async function waitForJson(path, timeout = 30000) {
  const url = `http://127.0.0.1:${remotePort}${path}`;
  let responsePayload;
  await waitFor(async () => {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        return false;
      }
      responsePayload = await response.json();
      return true;
    } catch {
      return false;
    }
  }, url, timeout);
  return responsePayload;
}

async function createPageTarget() {
  const response = await fetch(`http://127.0.0.1:${remotePort}/json/new?about:blank`, {
    method: "PUT",
  });
  if (!response.ok) {
    throw new Error(`Chrome target creation failed: HTTP ${response.status}`);
  }
  return response.json();
}

async function evaluate(client, expression) {
  const result = await client.send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (result.exceptionDetails) {
    throw new Error(JSON.stringify(result.exceptionDetails));
  }
  return result.result?.value;
}

function jsString(value) {
  return JSON.stringify(value);
}

async function textVisible(client, text) {
  return evaluate(
    client,
    `(() => {
      const needle = ${jsString(text)}.toLowerCase();
      return (document.body?.innerText || "").toLowerCase().includes(needle);
    })()`,
  );
}

async function waitForText(client, text, timeout = 300000) {
  await waitFor(() => textVisible(client, text), `text "${text}"`, timeout);
}

async function clickButton(client, text) {
  const clicked = await evaluate(
    client,
    `(() => {
      const needle = ${jsString(text)}.toLowerCase();
      const button = Array.from(document.querySelectorAll("button"))
        .find((element) => (element.innerText || "").toLowerCase().includes(needle));
      if (!button) return false;
      button.click();
      return true;
    })()`,
  );
  if (!clicked) {
    throw new Error(`Button not found: ${text}`);
  }
  await delay(1200);
}

async function clickText(client, text) {
  const clicked = await evaluate(
    client,
    `(() => {
      const needle = ${jsString(text)}.toLowerCase();
      const candidates = Array.from(document.querySelectorAll("button, summary, label, div, span"))
        .filter((element) => (element.innerText || "").toLowerCase().includes(needle))
        .sort((a, b) => (a.innerText || "").length - (b.innerText || "").length);
      const element = candidates[0];
      if (!element) return false;
      const clickable = element.closest("button, summary, label, [role='button']") || element;
      clickable.click();
      return true;
    })()`,
  );
  if (!clicked) {
    throw new Error(`Clickable text not found: ${text}`);
  }
  await delay(1200);
}

async function scrollToText(client, text, top = 80) {
  const found = await evaluate(
    client,
    `(() => {
      const needle = ${jsString(text)}.toLowerCase();
      const candidates = Array.from(document.querySelectorAll("h1, h2, h3, p, span, strong, div"))
        .filter((element) => {
          const text = (element.innerText || "").trim().toLowerCase();
          const rect = element.getBoundingClientRect();
          return text.includes(needle) && rect.width > 0 && rect.height > 0;
        })
        .sort((a, b) => {
          const aText = (a.innerText || "").trim().toLowerCase();
          const bText = (b.innerText || "").trim().toLowerCase();
          if (aText === needle && bText !== needle) return -1;
          if (bText === needle && aText !== needle) return 1;
          return aText.length - bText.length;
        });
      const element = candidates[0];
      if (!element) return false;
      element.scrollIntoView({ block: "start", inline: "nearest" });
      const offset = ${Number(top)};
      window.scrollBy(0, -offset);
      let parent = element.parentElement;
      while (parent) {
        if (parent.scrollHeight > parent.clientHeight) {
          parent.scrollTop = Math.max(0, parent.scrollTop - offset);
        }
        parent = parent.parentElement;
      }
      return true;
    })()`,
  );
  if (!found) {
    throw new Error(`Text not found for scroll: ${text}`);
  }
  await delay(1000);
}

async function screenshot(client, path) {
  await mkdir(dirname(resolve(path)), { recursive: true });
  const result = await client.send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
  });
  await writeFile(resolve(path), Buffer.from(result.data, "base64"));
  console.log(`captured=${path}`);
}

async function screenshotElement(client, selector, path) {
  const rect = await evaluate(
    client,
    `(() => {
      const element = document.querySelector(${jsString(selector)});
      if (!element) return null;
      element.scrollIntoView({ block: "center", inline: "center" });
      const rect = element.getBoundingClientRect();
      return {
        x: Math.max(0, rect.left),
        y: Math.max(0, rect.top),
        width: Math.max(1, rect.width),
        height: Math.max(1, rect.height),
      };
    })()`,
  );
  if (!rect) {
    throw new Error(`Element not found: ${selector}`);
  }
  await delay(900);
  const result = await client.send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: true,
    clip: { ...rect, scale: 1 },
  });
  await mkdir(dirname(resolve(path)), { recursive: true });
  await writeFile(resolve(path), Buffer.from(result.data, "base64"));
  console.log(`captured=${path}`);
}

async function screenshotArticleContaining(client, text, path) {
  const rect = await evaluate(
    client,
    `(() => {
      const needle = ${jsString(text)}.toLowerCase();
      const match = Array.from(document.querySelectorAll("article, section, div"))
        .filter((element) => {
          const value = (element.innerText || "").toLowerCase();
          const rect = element.getBoundingClientRect();
          return value.includes(needle) && rect.width > 0 && rect.height > 0;
        })
        .sort((a, b) => (a.innerText || "").length - (b.innerText || "").length)[0];
      if (!match) return null;
      match.scrollIntoView({ block: "center", inline: "center" });
      const rect = match.getBoundingClientRect();
      return {
        x: Math.max(0, rect.left),
        y: Math.max(0, rect.top),
        width: Math.max(1, rect.width),
        height: Math.max(1, rect.height),
      };
    })()`,
  );
  if (!rect) {
    throw new Error(`Article not found for text: ${text}`);
  }
  await delay(900);
  const result = await client.send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: true,
    clip: { ...rect, scale: 1 },
  });
  await mkdir(dirname(resolve(path)), { recursive: true });
  await writeFile(resolve(path), Buffer.from(result.data, "base64"));
  console.log(`captured=${path}`);
}

async function main() {
  const profileDir = `/tmp/pequiflux-gemma-chrome-${process.pid}`;
  const chrome = spawn(chromePath, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--hide-scrollbars",
    `--remote-debugging-port=${remotePort}`,
    `--user-data-dir=${profileDir}`,
    `--window-size=${viewport.width},${viewport.height}`,
    "about:blank",
  ]);

  let client;
  try {
    await waitForJson("/json/version", 30000);
    const target = await createPageTarget();
    client = new CdpClient(target.webSocketDebuggerUrl);
    await client.connect();
    await client.send("Page.enable");
    await client.send("Runtime.enable");
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await client.send("Page.navigate", { url: baseUrl });
    await waitForText(client, "PequiFlux Yard Copilot");
    await clickButton(client, labels.loadAnalyze);
    await waitForText(client, labels.liveProof, 300000);
    await waitForText(client, labels.runtime, 300000);
    await waitForText(client, "TRK-005", 300000);
    await waitForText(client, "DST-COV-01", 300000);
    await scrollToText(client, labels.decisionMoment, 80);
    await screenshot(client, shots.proof);
    await screenshotArticleContaining(client, labels.interpreter, shots.extraction);
    await clickText(client, labels.audit);
    await waitForText(client, labels.planner, 60000);
    await screenshotElement(client, ".tools-card", shots.planner);
  } finally {
    if (client) {
      try {
        client.close();
      } catch {
        // Chrome may already be closing.
      }
    }
    chrome.kill("SIGTERM");
    await rm(profileDir, { recursive: true, force: true });
  }
}

await main();

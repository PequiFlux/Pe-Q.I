import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { spawn } from "node:child_process";

const baseUrl = process.env.PEQUIFLUX_UI_URL || "http://127.0.0.1:8501/";
const captureMode = process.env.PEQUIFLUX_SCREENSHOT_MODE || "full";
const chromePath =
  process.env.CHROME_PATH || "/ms-playwright/chromium-1181/chrome-linux/chrome";
const remotePort = Number(process.env.CHROME_REMOTE_DEBUGGING_PORT || "9222");
const viewport = { width: 1440, height: 1200 };
const englishOperatorNote =
  "High rain blocks open hoppers; covered DST-COV-01 is compatible with TRK-005 right now.";
const s10ResourceJson = (
  await readFile(
    resolve("scenarios/cases/S10_FIFO_BREAK_JUSTIFIED/resource_state.json"),
    "utf-8",
  )
).trim();

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

const labels = {
  language: "English",
  load: "Load example",
  loadAnalyze: "Load and analyze example",
  analyzeGemma: "Analyze with Gemma 4",
  analyzeText: "Analyze in test mode",
  analysisResult: "Analysis result",
  decisionMoment: "Decision moment",
  driverMessage: "Message to driver",
  audit: "View technical audit",
  planner: "Gemma Tool Planner",
  rawPayload: "Raw payload",
  provenance: "provenance",
  sourceHashes: "source_hashes",
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

async function waitFor(condition, description, timeout = 120000) {
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
      const haystack = [document.title || "", document.body?.innerText || ""]
        .join("\\n")
        .toLowerCase();
      return haystack.includes(needle);
    })()`,
  );
}

async function waitForText(client, text, timeout = 120000) {
  await waitFor(() => textVisible(client, text), `text "${text}"`, timeout);
}

async function clickButton(client, text) {
  const clicked = await evaluate(
    client,
    `(() => {
      const needle = ${jsString(text)}.toLowerCase();
      const button = Array.from(document.querySelectorAll("button"))
        .find((element) => element.innerText && element.innerText.toLowerCase().includes(needle));
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

async function clickAnyButton(client, labelsToTry) {
  for (const label of labelsToTry) {
    const clicked = await evaluate(
      client,
      `(() => {
        const needle = ${jsString(label)}.toLowerCase();
        const button = Array.from(document.querySelectorAll("button"))
          .find((element) => element.innerText && element.innerText.toLowerCase().includes(needle));
        if (!button) return false;
        button.click();
        return true;
      })()`,
    );
    if (clicked) {
      await delay(1200);
      return label;
    }
  }
  throw new Error(`None of these buttons were found: ${labelsToTry.join(", ")}`);
}

async function clickText(client, text) {
  const clicked = await evaluate(
    client,
    `(() => {
      const needle = ${jsString(text)}.toLowerCase();
      const candidates = Array.from(document.querySelectorAll("button, summary, label, div, span"))
        .filter((element) => element.innerText && element.innerText.toLowerCase().includes(needle))
        .sort((a, b) => a.innerText.length - b.innerText.length);
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

async function chooseEnglish(client) {
  await evaluate(
    client,
    `(() => {
      const label = Array.from(document.querySelectorAll("label"))
        .find((element) => element.innerText && element.innerText.includes(${jsString(labels.language)}));
      if (label) label.click();
      return true;
    })()`,
  );
  await waitForText(client, labels.load, 30000);
}

async function chooseRadioOption(client, groupLabel, optionText) {
  const selected = await evaluate(
    client,
    `(() => {
      const groupNeedle = ${jsString(groupLabel)}.toLowerCase();
      const optionNeedle = ${jsString(optionText)}.toLowerCase();
      const group = Array.from(document.querySelectorAll("[role='radiogroup']"))
        .find((element) => (element.getAttribute("aria-label") || "").toLowerCase().includes(groupNeedle));
      if (!group) return false;
      const label = Array.from(group.querySelectorAll("label"))
        .find((element) => (element.innerText || "").toLowerCase().includes(optionNeedle));
      if (!label) return false;
      label.click();
      return true;
    })()`,
  );
  if (!selected) {
    throw new Error(`Radio option not found: ${groupLabel} -> ${optionText}`);
  }
  await delay(1200);
}

async function setTextArea(client, label, value) {
  const updated = await evaluate(
    client,
    `(() => {
      const area = document.querySelector(\`textarea[aria-label="${label}"]\`);
      if (!area) return false;
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value",
      ).set;
      setter.call(area, ${jsString(value)});
      area.dispatchEvent(new Event("input", { bubbles: true }));
      area.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`,
  );
  if (!updated) {
    throw new Error(`Textarea not found: ${label}`);
  }
  await delay(900);
}

async function replaceOperatorNote(client) {
  await setTextArea(client, "Operator note", englishOperatorNote);
}

async function replaceResourceJson(client) {
  await setTextArea(client, "Resources JSON", s10ResourceJson);
  await delay(900);
}

async function scrollToText(client, text, top = 96) {
  const found = await evaluate(
    client,
    `(() => {
      const needle = ${jsString(text)}.toLowerCase();
      const candidates = Array.from(document.querySelectorAll("h1, h2, h3, p, span, strong, button, summary, div"))
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
  await delay(1100);
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

async function main() {
  const profileDir = `/tmp/pequiflux-chrome-${process.pid}`;
  const chrome = spawn(chromePath, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
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
    console.log(`step=navigate:${baseUrl}`);
    await client.send("Page.navigate", { url: baseUrl });
    await waitForText(client, "PequiFlux Yard Copilot");
    await delay(1200);
    if (captureMode !== "autorun") {
      await chooseEnglish(client);
    }

    if (captureMode === "autorun") {
      console.log("step=autorun_result");
      await waitForText(client, labels.decisionMoment, 300000);
      await scrollToText(client, labels.decisionMoment, 100);
      await screenshot(client, shots.canonical);
      await screenshot(client, shots.result);
      await screenshot(client, shots.writeup);
      await scrollToText(client, labels.driverMessage, 120);
      await screenshot(client, shots.evidence);
      console.log("step=autorun_audit");
      await clickText(client, labels.audit);
      await waitForText(client, labels.planner, 30000);
      await screenshotElement(client, ".tools-card", shots.tools);
      await clickText(client, labels.rawPayload);
      await waitForText(client, labels.provenance, 30000);
      await scrollToText(client, labels.provenance, 180);
      await screenshot(client, shots.payloadProvenance);
      await waitForText(client, labels.sourceHashes, 30000);
      await scrollToText(client, labels.sourceHashes, 180);
      await screenshot(client, shots.payloadHashes);
      return;
    }

    console.log("step=initial");
    await screenshot(client, shots.initial);

    console.log("step=load_example");
    await clickButton(client, labels.load);
    await waitForText(client, "Versioned example loaded as fixture CSV.");
    await chooseRadioOption(client, "Resource mode", "JSON");
    await waitForText(client, "Resources JSON");
    await replaceResourceJson(client);
    await replaceOperatorNote(client);
    await waitForText(client, "4/4 essential blocks ready.");
    await scrollToText(client, "Operational input", 80);
    await screenshot(client, shots.inputsLoaded);

    console.log("step=analyze");
    await clickAnyButton(client, [labels.analyzeGemma, labels.analyzeText]);
    await waitForText(client, labels.decisionMoment, 180000);
    await scrollToText(client, labels.decisionMoment, 100);
    await screenshot(client, shots.canonical);
    await screenshot(client, shots.result);
    await screenshot(client, shots.writeup);

    await scrollToText(client, labels.driverMessage, 120);
    await screenshot(client, shots.evidence);

    console.log("step=audit");
    await clickText(client, labels.audit);
    await waitForText(client, labels.planner, 30000);
    await screenshotElement(client, ".tools-card", shots.tools);
    await clickText(client, labels.rawPayload);
    await waitForText(client, labels.provenance, 30000);
    await scrollToText(client, labels.provenance, 180);
    await screenshot(client, shots.payloadProvenance);
    await waitForText(client, labels.sourceHashes, 30000);
    await scrollToText(client, labels.sourceHashes, 180);
    await screenshot(client, shots.payloadHashes);
  } finally {
    if (client) {
      try {
        await client.send("Browser.close");
      } catch {
        client.close();
      }
    }
    chrome.kill("SIGTERM");
    try {
      await rm(profileDir, {
        recursive: true,
        force: true,
        maxRetries: 5,
        retryDelay: 100,
      });
    } catch {
      // The temporary Chrome profile may still have files closing after Browser.close.
    }
  }

  for (const path of Object.values(shots)) {
    console.log(path);
  }
}

await main();

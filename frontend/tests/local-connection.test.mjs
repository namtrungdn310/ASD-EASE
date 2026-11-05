import assert from "node:assert/strict";
import { after, afterEach, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { JSDOM } from "jsdom";
import { createServer } from "vite";
import react from "@vitejs/plugin-react";

let server, LocalConnection, current;
before(async () => {
  server = await createServer({ configFile: false, root: fileURLToPath(new URL("../", import.meta.url)),
    plugins: [react()], server: { middlewareMode: true, hmr: false }, appType: "custom" });
  ({ LocalConnection } = await server.ssrLoadModule("/src/components/LocalConnection.tsx"));
});
after(async () => { await server?.close(); });
afterEach(async () => { await current?.dispose(); current = undefined; });

async function mount(fetchImpl, strict = false) {
  const dom = new JSDOM('<div id="root"></div>', { url: "http://localhost:5173" });
  const timers = new Map();
  let id = 0;
  dom.window.setTimeout = (callback, delay) => { timers.set(++id, { callback, delay }); return id; };
  dom.window.clearTimeout = timer => timers.delete(timer);
  Object.defineProperty(dom.window.document, "visibilityState", { value: "visible", configurable: true });
  const saved = new Map();
  for (const [key, value] of Object.entries({ window: dom.window, document: dom.window.document,
    navigator: dom.window.navigator, HTMLElement: dom.window.HTMLElement, fetch: fetchImpl, IS_REACT_ACT_ENVIRONMENT: true })) {
    saved.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { value, configurable: true, writable: true });
  }
  const element = React.createElement(LocalConnection, null, React.createElement("p", { id: "dashboard" }, "Live dashboard"));
  const root = createRoot(dom.window.document.getElementById("root"));
  current = { dom, timers, root, async dispose() {
    await act(async () => root.unmount());
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
    dom.window.close();
  } };
  await act(async () => root.render(strict ? React.createElement(React.StrictMode, null, element) : element));
  return current;
}

const ok = () => Promise.resolve({ ok: true, json: async () => ({ authenticated: true }) });

test("opens local session before mounting dashboard without any token input", async () => {
  const calls = [];
  let finish;
  const pending = new Promise(resolve => { finish = resolve; });
  const page = await mount((url, options) => { calls.push({ url, options }); return pending; });
  assert.ok(page.dom.window.document.querySelector('[role="status"]'));
  assert.equal(page.dom.window.document.querySelector("#dashboard"), null);
  assert.equal(page.dom.window.document.querySelector("input"), null);
  assert.equal(calls[0].url, "/__local/session");
  assert.equal(calls[0].options.credentials, "include");
  assert.equal(calls[0].options.body, undefined);
  await act(async () => finish(await ok()));
  assert.ok(page.dom.window.document.querySelector("#dashboard"));
});

test("temporarily unavailable service retries automatically and becomes ready", async () => {
  let count = 0;
  const page = await mount(() => ++count === 1
    ? Promise.resolve({ ok: false, json: async () => ({ error: "LOCAL_SERVICE_UNAVAILABLE" }) }) : ok());
  assert.ok(page.dom.window.document.querySelector('[role="alert"]'));
  assert.equal(page.dom.window.document.querySelector("button").textContent.trim(), "Thử lại");
  const retry = [...page.timers.values()].find(timer => timer.delay === 3000);
  assert.ok(retry);
  await act(async () => retry.callback());
  assert.ok(page.dom.window.document.querySelector("#dashboard"));
});

test("refreshes session while preserving dashboard mount and history", async () => {
  let calls = 0;
  const page = await mount(() => { calls++; return ok(); });
  const dashboard = page.dom.window.document.querySelector("#dashboard");
  const refresh = [...page.timers.values()].find(timer => timer.delay === 20*60*1000);
  await act(async () => refresh.callback());
  assert.equal(calls, 2);
  assert.equal(page.dom.window.document.querySelector("#dashboard"), dashboard);
  await act(async () => page.dom.window.document.dispatchEvent(new page.dom.window.Event("visibilitychange")));
  assert.equal(calls, 3);
  assert.equal(page.dom.window.document.querySelector("#dashboard"), dashboard);
});

test("StrictMode cleanup cancels old request; unmount removes timers", async () => {
  const signals = [];
  const page = await mount((url, options) => { signals.push(options.signal); return ok(); }, true);
  assert.equal(signals.length, 2);
  assert.equal(signals[0].aborted, true);
  assert.ok(page.dom.window.document.querySelector("#dashboard"));
  await act(async () => page.root.unmount());
  assert.equal(signals[1].aborted, true);
  assert.equal(page.timers.size, 0);
});

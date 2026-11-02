import assert from "node:assert/strict";
import { after, afterEach, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { JSDOM } from "jsdom";
import { createServer } from "vite";

// Dùng mã/hook thật để kiểm tra mount/cập nhật/unmount React.
// jsdom không kiểm chứng bố cục, nét vẽ biểu đồ hoặc trình đọc màn hình.
let server;
let useLiveTelemetry;
let Dashboard;
let current;
const payload = (patch = {}) => ({
  schema_version: "1.0", device_id: "device-a", session_id: "session-a",
  timestamp_ms: 1000, data_origin: "SYNTHETIC", hr_bpm: 72,
  gsr: { raw: 1234, delta: 0 }, movement: { score: 0.2 },
  signal_quality: { ppg: 1, gsr: 0.9, imu: 0.8 },
  prediction: { probability: 0.25, state: "NORMAL" },
  firmware_version: "test", model_version: "test", ...patch,
});

before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL("../", import.meta.url)),
    server: { middlewareMode: true, hmr: false }, appType: "custom",
  });
  ({ useLiveTelemetry } = await server.ssrLoadModule("/src/hooks/useLiveTelemetry.ts"));
  ({ Dashboard } = await server.ssrLoadModule("/src/pages/Dashboard.tsx"));
});
after(async () => { await server?.close(); });
afterEach(async () => { await current?.dispose(); current = undefined; });

async function mount({ strict = false, dashboard = false, failures = 0, timeout = 5000 } = {}) {
  const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: "http://localhost:5173" });
  let now = 0;
  let timerId = 0;
  let latest;
  let attempts = 0;
  let layoutWarnings = 0;
  let mounted = true;
  const timers = new Map();
  const sockets = [];
  const addTimer = (callback, delay, repeat) => {
    const id = ++timerId;
    timers.set(id, { callback, at: now + delay, delay, repeat });
    return id;
  };
  dom.window.setTimeout = (callback, delay) => addTimer(callback, delay, false);
  dom.window.clearTimeout = (id) => timers.delete(id);
  dom.window.setInterval = (callback, delay) => addTimer(callback, delay, true);
  dom.window.clearInterval = (id) => timers.delete(id);
  class FakeWebSocket {
    static OPEN = 1;
    readyState = 0;
    onopen = null; onclose = null; onerror = null; onmessage = null;
    constructor(url) {
      attempts++;
      if (attempts <= failures) throw new Error("simulated constructor failure");
      this.url = url;
      sockets.push(this);
    }
    open() { this.readyState = 1; this.onopen?.({}); }
    sendPayload(value) { this.onmessage?.({ data: JSON.stringify(value) }); }
    close() { this.readyState = 3; this.onclose?.({}); }
  }
  class NoLayoutResizeObserver { observe() {} unobserve() {} disconnect() {} }
  const nativePerformance = globalThis.performance;
  const clock = new Proxy(nativePerformance, {
    get(target, key) {
      if (key === "now") return () => now;
      const value = Reflect.get(target, key, target);
      return typeof value === "function" ? value.bind(target) : value;
    },
  });
  const globals = {
    window: dom.window, document: dom.window.document,
    navigator: dom.window.navigator, HTMLElement: dom.window.HTMLElement,
    WebSocket: FakeWebSocket, ResizeObserver: NoLayoutResizeObserver,
    performance: clock, IS_REACT_ACT_ENVIRONMENT: true,
  };
  const saved = new Map();
  for (const [key, value] of Object.entries(globals)) {
    saved.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { value, configurable: true, writable: true });
  }
  const container = dom.window.document.getElementById("root");
  const root = createRoot(container);
  const nativeWarn = console.warn;
  console.warn = (...args) => {
    // jsdom không tính bố cục; chỉ ghi nhận cảnh báo Recharts đã biết.
    if (String(args[0]).includes("The width(0) and height(0) of chart")) {
      layoutWarnings++;
      return;
    }
    nativeWarn(...args);
  };
  function Probe() { latest = useLiveTelemetry(timeout); return null; }
  const node = React.createElement(dashboard ? Dashboard : Probe);
  const mutate = async (callback) => { await act(async () => { callback(); }); };
  const unmount = async () => {
    if (mounted) { await act(async () => { root.unmount(); }); mounted = false; }
  };
  current = {
    sockets, timers, container, mutate, unmount,
    view: () => latest,
    attempts: () => attempts,
    layoutWarnings: () => layoutWarnings,
    advance: async (milliseconds) => {
      const until = now + milliseconds;
      await mutate(() => {
        while (true) {
          const due = [...timers].filter(([, timer]) => timer.at <= until)
            .sort((a, b) => a[1].at - b[1].at)[0];
          if (!due) break;
          const [id, timer] = due;
          now = timer.at;
          if (timer.repeat) timer.at += timer.delay; else timers.delete(id);
          timer.callback();
        }
        now = until;
      });
    },
    dispose: async () => {
      try { await unmount(); }
      finally {
        console.warn = nativeWarn;
        dom.window.close();
        for (const [key, descriptor] of saved) {
          if (descriptor) Object.defineProperty(globalThis, key, descriptor);
          else delete globalThis[key];
        }
      }
    },
  };
  await act(async () => { root.render(strict ? React.createElement(React.StrictMode, null, node) : node); });
  return current;
}

test("real hook starts disconnected, waits on open, then becomes live", async () => {
  const h = await mount();
  assert.equal(h.view().connectionStatus, "backend_disconnected");
  assert.equal(h.view().telemetry, null);
  assert.equal(h.sockets.length, 1);
  await h.mutate(() => h.sockets[0].open());
  assert.equal(h.view().backendConnected, true);
  assert.equal(h.view().connectionStatus, "waiting");
  await h.mutate(() => h.sockets[0].sendPayload(payload()));
  assert.equal(h.view().connectionStatus, "live");
  assert.equal(h.view().selectedDeviceId, "device-a");
  assert.equal(h.view().points.length, 1);
});

test("stale timer is receive-clock based and duplicate samples do not refresh it", async () => {
  const h = await mount();
  const socket = h.sockets[0];
  await h.mutate(() => { socket.open(); socket.sendPayload(payload()); });
  await h.advance(4500);
  assert.equal(h.view().connectionStatus, "live");
  await h.mutate(() => socket.sendPayload(payload()));
  await h.advance(500);
  assert.equal(h.view().connectionStatus, "stale");
  assert.equal(h.view().backendConnected, true);
  assert.equal(h.view().points.length, 1);
  await h.mutate(() => socket.sendPayload(payload({ timestamp_ms: 2000 })));
  assert.equal(h.view().connectionStatus, "live");
  assert.equal(h.view().points.length, 2);
});

test("malformed JSON, invalid shapes, binary and closed-socket messages are ignored", async () => {
  const h = await mount();
  const socket = h.sockets[0];
  await h.mutate(() => socket.sendPayload(payload()));
  assert.equal(h.view().telemetry, null);
  await h.mutate(() => socket.open());
  for (const data of ["{", "{}", "null", "[]", JSON.stringify(payload({ movement: null })), new Uint8Array([1, 2])]) {
    await h.mutate(() => socket.onmessage({ data }));
    assert.equal(h.view().connectionStatus, "waiting");
    assert.equal(h.view().telemetry, null);
  }
  await h.mutate(() => socket.sendPayload(payload()));
  assert.equal(h.view().connectionStatus, "live");
});

test("device selection and session/origin resets do not mix chart histories", async () => {
  const h = await mount();
  const socket = h.sockets[0];
  await h.mutate(() => {
    socket.open(); socket.sendPayload(payload());
    socket.sendPayload(payload({ timestamp_ms: 2000 }));
    socket.sendPayload(payload({ device_id: "device-b", timestamp_ms: 9000, hr_bpm: 88 }));
  });
  assert.equal(h.view().telemetry.device_id, "device-a");
  assert.equal(h.view().points.length, 2);
  await h.mutate(() => h.view().setSelectedDeviceId("device-b"));
  assert.equal(h.view().telemetry.hr_bpm, 88);
  assert.equal(h.view().points.length, 1);
  for (const patch of [{ session_id: "session-b", timestamp_ms: 10000 }, { data_origin: "DEVICE", timestamp_ms: 11000 }, { timestamp_ms: 0 }]) {
    await h.mutate(() => socket.sendPayload(payload({ device_id: "device-b", ...patch })));
    assert.equal(h.view().points.length, 1);
  }
  await h.mutate(() => socket.sendPayload(payload({ device_id: "__proto__" })));
  assert.deepEqual(h.view().deviceIds, ["device-a", "device-b", "__proto__"]);
});

test("real hook caps history and preserves nullable measurements", async () => {
  const h = await mount();
  const socket = h.sockets[0];
  await h.mutate(() => {
    socket.open();
    for (let i = 1; i <= 75; i++) socket.sendPayload(payload({ timestamp_ms: i * 1000 }));
  });
  assert.equal(h.view().points.length, 60);
  assert.equal(h.view().points[0].time, 16);
  await h.mutate(() => socket.sendPayload(payload({ timestamp_ms: 76000, hr_bpm: null, gsr: { raw: null, delta: null }, movement: { score: null }, prediction: { probability: null, state: "UNCERTAIN" } })));
  assert.deepEqual(h.view().points.at(-1), { time: 76, hr: null, gsr: null, movement: null, probability: null });
});

test("reconnect waits for a new selected-device sample, not old data or duplicates", async () => {
  const h = await mount();
  const first = h.sockets[0];
  await h.mutate(() => { first.open(); first.sendPayload(payload()); });
  await h.advance(100);
  const oldCallbacks = { open: first.onopen, message: first.onmessage, close: first.onclose, error: first.onerror };
  await h.mutate(() => { first.close(); oldCallbacks.close({}); });
  assert.equal(h.view().connectionStatus, "backend_disconnected");
  assert.equal(h.timers.size, 2);
  await h.advance(1499);
  assert.equal(h.sockets.length, 1);
  await h.advance(1);
  const second = h.sockets[1];
  await h.mutate(() => second.open());
  assert.equal(h.view().connectionStatus, "waiting");
  assert.equal(h.view().telemetry.device_id, "device-a");
  await h.mutate(() => {
    oldCallbacks.open({}); oldCallbacks.message({ data: JSON.stringify(payload({ timestamp_ms: 9999 })) }); oldCallbacks.error({});
    second.sendPayload(payload());
    second.sendPayload(payload({ device_id: "device-b" }));
  });
  assert.equal(h.view().connectionStatus, "waiting");
  assert.equal(second.readyState, 1);
  await h.mutate(() => second.sendPayload(payload({ timestamp_ms: 2000 })));
  assert.equal(h.view().connectionStatus, "live");
});

test("constructor failures retry once per delay and unmount cancels pending retry", async () => {
  const h = await mount({ failures: 2 });
  assert.equal(h.attempts(), 1);
  await h.advance(1500);
  assert.equal(h.attempts(), 2);
  await h.advance(1500);
  assert.equal(h.attempts(), 3);
  await h.mutate(() => h.sockets[0].onerror({}));
  assert.equal(h.timers.size, 2);
  await h.unmount();
  assert.equal(h.timers.size, 0);
  await h.advance(10000);
  assert.equal(h.attempts(), 3);
});

test("StrictMode effect replay leaves one active socket and complete unmount cleanup", async () => {
  const h = await mount({ strict: true });
  assert.equal(h.sockets.length, 2);
  assert.equal(h.sockets[0].readyState, 3);
  assert.equal(h.sockets[0].onmessage, null);
  assert.equal(h.timers.size, 1);
  const active = h.sockets[1];
  await h.mutate(() => { active.open(); active.sendPayload(payload()); });
  assert.equal(h.view().connectionStatus, "live");
  const late = active.onmessage;
  await h.unmount();
  assert.equal(active.readyState, 3);
  for (const key of ["onopen", "onclose", "onerror", "onmessage"]) assert.equal(active[key], null);
  assert.equal(h.timers.size, 0);
  await h.mutate(() => late({ data: JSON.stringify(payload({ timestamp_ms: 2000 })) }));
  await h.advance(10000);
  assert.equal(h.sockets.length, 2);
});

test("custom timeout is respected without recreating the socket", async () => {
  const h = await mount({ timeout: 1000 });
  await h.mutate(() => { h.sockets[0].open(); h.sockets[0].sendPayload(payload()); });
  await h.advance(1000);
  assert.equal(h.view().connectionStatus, "stale");
  assert.equal(h.sockets.length, 1);
});

test("Dashboard uses real hook and DOM selection across live, stale and reconnect", async () => {
  const h = await mount({ dashboard: true, strict: true });
  const socket = h.sockets.at(-1);
  const text = () => h.container.textContent;
  assert.equal(h.container.querySelector("select").disabled, true);
  await h.mutate(() => socket.open());
  assert.ok(text().includes("Đang chờ dữ liệu"));
  await h.mutate(() => {
    socket.sendPayload(payload());
    socket.sendPayload(payload({ device_id: "device-b", session_id: "session-b", hr_bpm: 88 }));
  });
  assert.ok(text().includes("72.0 bpm"));
  assert.ok(text().includes("SYNTHETIC DATA"));
  const select = h.container.querySelector("select");
  await h.mutate(() => {
    select.value = "device-b";
    select.dispatchEvent(new window.Event("change", { bubbles: true }));
  });
  assert.ok(text().includes("88.0 bpm"));
  assert.ok(text().includes("session-b"));
  assert.ok(!text().includes("72.0 bpm"));
  await h.advance(5000);
  assert.ok(text().includes("Dữ liệu đã cũ"));
  assert.ok(text().includes("Đang hiển thị dữ liệu nhận trước đó"));
  assert.ok(!text().includes("NORMAL"));
  await h.mutate(() => socket.close());
  assert.ok(text().includes("Mất kết nối backend"));
  await h.advance(1500);
  const next = h.sockets.at(-1);
  await h.mutate(() => next.open());
  assert.ok(text().includes("Đang chờ dữ liệu"));
  assert.ok(!text().includes("NORMAL"));
  await h.mutate(() => next.sendPayload(payload({ device_id: "device-b", session_id: "session-b", timestamp_ms: 2000, hr_bpm: 89 })));
  assert.ok(text().includes("89.0 bpm"));
  assert.ok(text().includes("Dữ liệu đang cập nhật"));
  assert.ok(text().includes("NORMAL"));
  assert.ok(h.layoutWarnings() > 0, "zero-size chart warnings are expected: jsdom does not verify layout");
});

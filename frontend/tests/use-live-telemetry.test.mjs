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
let LocalConnection;
let current;
const payload = (patch = {}) => ({
  schema_version: "1.0", device_id: "device-a", session_id: "session-a",
  timestamp_ms: 1000, data_origin: "DEVICE", hr_bpm: 72,
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
  ({ LocalConnection } = await server.ssrLoadModule("/src/components/LocalConnection.tsx"));
});
after(async () => { await server?.close(); });
afterEach(async () => { await current?.dispose(); current = undefined; });

test("manual connection receives engineering-v2 HR through the real hook", async () => {
  const h = await mount({ connect: false, devices: [{ device_id: "device-a", last_seen_at: null }] });
  assert.equal(h.sockets.length, 0);
  assert.equal(h.view().selectedDeviceId, "device-a");
  await h.mutate(() => h.view().connectDevice());
  assert.equal(h.sockets.length, 1);
  await h.mutate(() => h.sockets[0].open());
  await h.mutate(() => h.sockets[0].sendPayload(payload({
    schema_version: "1.2", firmware_version: "0.4.0-tracker",
    movement: { score: .2, acceleration: { x: 0, y: 0, z: 9.8 }, angular_velocity: { x: 0, y: 0, z: 0 } },
    signal_quality: { method: "engineering-v2", window_ms: 8000,
      hr: { score: .85, reason: "ok" }, gsr: { score: 1, reason: "ok" },
      acceleration: { score: 1, reason: "ok" }, rotation: { score: 1, reason: "ok" } },
  })));
  assert.equal(h.view().connectionStatus, "live");
  assert.equal(h.view().telemetry.hr_bpm, 72);
  assert.equal(h.view().telemetry.signal_quality.hr.score, .85);
  assert.equal(h.view().points[0].hr, 72);
  await h.mutate(() => h.view().disconnectDevice());
  assert.equal(h.view().monitoring, false);
});

async function mount({ strict = false, dashboard = false, failures = 0, timeout = 5000, localSession = false,
  connect = true, devices = [{ device_id: "device-a", last_seen_at: null }, { device_id: "device-b", last_seen_at: null }], savedPreference = null, storageBlocked = false } = {}) {
  const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: "http://localhost:5173" });
  const preferenceKey = 'asd-ease:device:http://localhost:8000';
  if (savedPreference) dom.window.localStorage.setItem(preferenceKey, JSON.stringify({ source: 'DEVICE', ...savedPreference }));
  if (storageBlocked) Object.defineProperty(dom.window, 'localStorage', { get() { throw new Error('blocked'); } });
  let now = 0;
  let timerId = 0;
  let latest;
  let attempts = 0;
  let layoutWarnings = 0;
  let mounted = true;
  const timers = new Map();
  const sockets = [];
  const authRequests = [];
  const sessionRequests = [];
  let sessionRows = [];
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
    sent = [];
    emitClose = true;
    constructor(url) {
      attempts++;
      if (attempts <= failures) throw new Error("simulated constructor failure");
      this.url = url;
      sockets.push(this);
    }
    open() { this.readyState = 1; this.onopen?.({}); }
    sendPayload(value) { this.onmessage?.({ data: JSON.stringify(value) }); }
    send(value) { this.sent.push(value); }
    close() { this.readyState = 3; if (this.emitClose) this.onclose?.({}); }
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
    fetch: async (url, options) => {
      if (String(url).endsWith('/api/v1/devices')) {
        return { ok: true, status: 200, json: async () => structuredClone(devices.map(row => ({ data_origin: 'DEVICE', ...row }))) };
      }
      if (String(url).endsWith('/api/v1/sessions')) {
        sessionRequests.push({ url, options });
        return { ok: true, status: 200, json: async () => structuredClone(sessionRows) };
      }
      authRequests.push({ url, options });
      return { ok: true, json: async () => ({ authenticated: true }) };
    },
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
  const page = React.createElement(dashboard ? Dashboard : Probe);
  const node = localSession ? React.createElement(LocalConnection, null, page) : page;
  const mutate = async (callback) => { await act(async () => { callback(); }); };
  const unmount = async () => {
    if (mounted) { await act(async () => { root.unmount(); }); mounted = false; }
  };
  current = {
    sockets, timers, container, mutate, unmount, authRequests, sessionRequests,
    savedPreference: () => JSON.parse(dom.window.localStorage.getItem(preferenceKey)),
    setSessionRows: rows => { sessionRows = rows; },
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
  // Tests of an active transport explicitly perform the same connection action as the user.
  if (connect) await mutate(() => {
    if (dashboard) container.querySelector('.device-connect-button').click();
    else latest.connectDevice();
  });
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

test("one offline device appears in the header before telemetry and is never marked connected by the catalog", async () => {
  const h = await mount({ connect: false, dashboard: true, strict: true, devices: [{ device_id: 'ESP32-001', last_seen_at: null }] });
  const select = h.container.querySelector('header .header-device select');
  assert.ok(select);
  assert.equal(select.value, 'ESP32-001');
  assert.equal(select.disabled, false);
  assert.equal(select.closest('.header-device').querySelector('.header-device-name').textContent, 'ESP32-001');
  assert.equal(select.closest('.header-device').querySelector('.connection-badge svg'), null);
  assert.ok(select.closest('.header-device').lastElementChild.classList.contains('header-device-arrow'));
  assert.ok(select.closest('.header-device').querySelector('.connection-badge'));
  assert.equal(h.container.querySelector('main select'), null);
  assert.equal(h.container.querySelector('.connection-badge').dataset.deviceConnected, 'false');
  assert.equal(h.sockets.length, 0);
  await h.mutate(() => h.container.querySelector('.device-connect-button').click());
  await h.mutate(() => h.sockets.at(-1).open());
  assert.equal(h.container.querySelector('.connection-badge').dataset.deviceConnected, 'false');
  await h.mutate(() => h.sockets.at(-1).sendPayload(payload({ device_id: 'ESP32-001' })));
  assert.equal(h.container.querySelector('.connection-badge').dataset.deviceConnected, 'true');
});

test("remembered device wins over other live devices and survives a new page mount", async () => {
  const devices = [{ device_id: 'device-a', last_seen_at: '2026-11-11T00:00:00Z' },
    { device_id: 'device-b', last_seen_at: null }];
  let h = await mount({ devices, savedPreference: { selected: 'device-b', ids: ['device-a', 'device-b'] } });
  assert.equal(h.view().selectedDeviceId, 'device-b');
  await h.mutate(() => { h.sockets[0].open(); h.sockets[0].sendPayload(payload()); });
  assert.equal(h.view().selectedDeviceId, 'device-b');
  assert.equal(h.view().telemetry, null);
  assert.equal(h.view().connectionStatus, 'waiting');
  await h.mutate(() => h.view().setSelectedDeviceId('device-a'));
  const saved = h.savedPreference();
  assert.equal(saved.selected, 'device-a');
  await h.dispose(); current = undefined;
  h = await mount({ devices, savedPreference: saved });
  assert.equal(h.view().selectedDeviceId, 'device-a');
  assert.equal(h.view().connectionStatus, 'backend_disconnected');
  assert.equal(h.view().telemetry, null);
});

test("without saved choice the most recently measured device wins; blocked storage is tolerated", async () => {
  const h = await mount({ storageBlocked: true, devices: [
    { device_id: 'device-a', last_seen_at: null },
    { device_id: 'device-b', last_seen_at: '2026-11-11T01:00:00Z' },
    { device_id: 'device-c', last_seen_at: '2026-11-10T01:00:00Z' },
  ] });
  assert.equal(h.view().selectedDeviceId, 'device-b');
  assert.equal(h.view().telemetry, null);
  await h.mutate(() => h.view().setSelectedDeviceId('device-c'));
  assert.equal(h.view().selectedDeviceId, 'device-c');
});

test("malformed catalog does not break websocket measurements or inject device names", async () => {
  const h = await mount({ devices: [{ device_id: '<script>', last_seen_at: null }], savedPreference: { selected: 'device-a', ids: ['device-a'] } });
  assert.deepEqual(h.view().deviceIds, ['device-a']);
  await h.mutate(() => { h.sockets[0].open(); h.sockets[0].sendPayload(payload()); });
  assert.equal(h.view().selectedDeviceId, 'device-a');
  assert.equal(h.view().connectionStatus, 'live');
});

test("only real devices remain after catalog refresh and synthetic frames cannot reintroduce them", async () => {
  const h = await mount({ dashboard: true, devices: [
    { device_id: 'SIM-001', data_origin: 'SYNTHETIC', last_seen_at: '2026-11-11T02:00:00Z' },
    { device_id: 'ESP32-001', data_origin: 'DEVICE', last_seen_at: null },
    { device_id: 'SIM-OTHER', data_origin: 'SYNTHETIC', last_seen_at: null },
  ], savedPreference: { selected: 'SIM-001', ids: ['SIM-001', 'SIM-OTHER', 'ESP32-001'] } });
  const select = h.container.querySelector('select');
  assert.deepEqual([...select.options].map(option => option.value), ['ESP32-001']);
  assert.equal(select.value, 'ESP32-001');
  assert.equal(select.disabled, false);
  assert.deepEqual(h.savedPreference().ids, ['ESP32-001']);
  await h.mutate(() => {
    h.sockets[0].open();
    h.sockets[0].sendPayload(payload({ device_id: 'SIM-NEW', data_origin: 'SYNTHETIC' }));
  });
  assert.equal(select.options.length, 1);
  assert.equal(h.container.querySelector('.connection-badge').dataset.deviceConnected, 'false');
  await h.mutate(() => h.sockets[0].sendPayload(payload({ device_id: 'ESP32-001' })));
  assert.equal(h.container.querySelector('.connection-badge').dataset.deviceConnected, 'true');
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
  assert.equal(h.view().monitoring, false);
  assert.equal(h.view().telemetry, null);
  await h.mutate(() => h.view().connectDevice());
  const selectedSocket = h.sockets.at(-1);
  await h.mutate(() => { selectedSocket.open(); selectedSocket.sendPayload(payload({ device_id: "device-b", timestamp_ms: 9000, hr_bpm: 88 })); });
  assert.equal(h.view().telemetry.hr_bpm, 88);
  assert.equal(h.view().points.length, 1);
  for (const patch of [{ session_id: "session-b", timestamp_ms: 10000 }, { timestamp_ms: 0 }]) {
    await h.mutate(() => selectedSocket.sendPayload(payload({ device_id: "device-b", ...patch })));
    assert.equal(h.view().points.length, 1);
  }
  await h.mutate(() => selectedSocket.sendPayload(payload({ device_id: "__proto__" })));
  assert.deepEqual(h.view().deviceIds, ["device-a", "device-b"]);
});

test("real hook caps history and preserves nullable measurements", async () => {
  const h = await mount();
  const socket = h.sockets[0];
  await h.mutate(() => {
    socket.open();
    for (let i = 1; i <= 75; i++) socket.sendPayload(payload({ timestamp_ms: i * 1000 }));
  });
  assert.equal(h.view().points.length, 61);
  assert.equal(h.view().points[0].time, 15);
  assert.equal(h.view().historySeconds, 74);
  await h.mutate(() => socket.sendPayload(payload({ timestamp_ms: 76000, hr_bpm: null, gsr: { raw: null, delta: null }, movement: { score: null }, prediction: { probability: null, state: "UNCERTAIN" } })));
  assert.deepEqual(h.view().points.at(-1), { time: 76, hr: null, gsr: null, movement: null,
    ax: null, ay: null, az: null, gx: null, gy: null, gz: null, probability: null, predictionState: "UNCERTAIN" });
});

test("reconnect waits for a new selected-device sample, not old data or duplicates", async () => {
  const h = await mount();
  const first = h.sockets[0];
  await h.mutate(() => { first.open(); first.sendPayload(payload()); });
  await h.advance(100);
  const oldCallbacks = { open: first.onopen, message: first.onmessage, close: first.onclose, error: first.onerror };
  await h.mutate(() => { first.close(); oldCallbacks.close({}); });
  assert.equal(h.view().connectionStatus, "backend_disconnected");
  assert.ok([...h.timers.values()].some(timer => !timer.repeat && timer.delay === 1500));
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
  assert.ok([...h.timers.values()].some(timer => !timer.repeat && timer.delay === 1500));
  await h.unmount();
  assert.equal(h.timers.size, 0);
  await h.advance(10000);
  assert.equal(h.attempts(), 3);
});

test("StrictMode effect replay leaves one active socket and complete unmount cleanup", async () => {
  const h = await mount({ strict: true });
  assert.equal(h.sockets.length, 1); // Manual connect occurs after StrictMode mount replay.
  assert.ok([...h.timers.values()].some(timer => !timer.repeat && timer.delay === 10000));
  const active = h.sockets[0];
  await h.mutate(() => { active.open(); active.sendPayload(payload()); });
  assert.ok([...h.timers.values()].every(timer => timer.repeat));
  assert.equal(h.view().connectionStatus, "live");
  const late = active.onmessage;
  await h.unmount();
  assert.equal(active.readyState, 3);
  for (const key of ["onopen", "onclose", "onerror", "onmessage"]) assert.equal(active[key], null);
  assert.equal(h.timers.size, 0);
  await h.mutate(() => late({ data: JSON.stringify(payload({ timestamp_ms: 2000 })) }));
  await h.advance(10000);
  assert.equal(h.sockets.length, 1);
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
  const deviceConnected = () => h.container.querySelector(".connection-badge").dataset.deviceConnected;
  assert.equal(h.container.querySelector("select").disabled, false);
  assert.equal(deviceConnected(), "false");
  await h.mutate(() => socket.open());
  assert.ok(text().includes("Chờ dữ liệu"));
  assert.equal(deviceConnected(), "false"); // Socket mở chưa đủ để báo thiết bị kết nối.
  await h.mutate(() => {
    socket.sendPayload(payload());
    socket.sendPayload(payload({ device_id: "device-b", session_id: "session-b", hr_bpm: 88 }));
  });
  assert.ok(text().includes("72.0 bpm"));
  assert.equal(deviceConnected(), "true");
  assert.ok(!text().includes("Dữ liệu giả lập"));
  const select = h.container.querySelector("select");
  await h.mutate(() => {
    select.value = "device-b";
    select.dispatchEvent(new window.Event("change", { bubbles: true }));
  });
  assert.equal(deviceConnected(), "false");
  await h.mutate(() => h.container.querySelector('.device-connect-button').click());
  const selectedSocket = h.sockets.at(-1);
  await h.mutate(() => { selectedSocket.open(); selectedSocket.sendPayload(payload({ device_id: "device-b", session_id: "session-b", hr_bpm: 88 })); });
  assert.ok(text().includes("88.0 bpm"));
  assert.ok(text().includes("session-b"));
  assert.ok(!text().includes("72.0 bpm"));
  await h.advance(5000);
  assert.equal(deviceConnected(), "false");
  assert.ok(text().includes("Dữ liệu cũ"));
  assert.equal(h.container.querySelector('.stream-notice'), null);
  assert.ok(!text().includes("Bình thường"));
  await h.mutate(() => selectedSocket.close());
  assert.equal(deviceConnected(), "false");
  await h.advance(1500);
  const next = h.sockets.at(-1);
  await h.mutate(() => next.open());
  assert.equal(deviceConnected(), "false");
  assert.ok(text().includes("Chờ dữ liệu"));
  assert.ok(!text().includes("Bình thường"));
  await h.mutate(() => next.sendPayload(payload({ device_id: "device-b", session_id: "session-b", timestamp_ms: 2000, hr_bpm: 89 })));
  assert.ok(text().includes("89.0 bpm"));
  assert.equal(deviceConnected(), "true");
  assert.ok(text().includes("Đang cập nhật"));
  assert.ok(text().includes("Bình thường"));
  assert.ok(h.layoutWarnings() > 0, "zero-size chart warnings are expected: jsdom does not verify layout");
});

test("Dashboard 1.1 shows four sensor groups, magnitudes and signed axes from the real hook", async () => {
  const h = await mount({ dashboard: true, strict: true });
  const socket = h.sockets.at(-1);
  await h.mutate(() => {
    socket.open();
    socket.sendPayload(payload({ schema_version: "1.1", data_origin: "DEVICE", model_version: "none",
      prediction: { probability: null, state: "UNCERTAIN" },
      signal_quality: { ppg: 0, imu: 0, gsr: 0 },
      movement: { score: 0.1, acceleration: { x: 3, y: 4, z: 12 }, angular_velocity: { x: -3, y: -4, z: -12 } },
    }));
  });
  const panels = h.container.querySelectorAll(".sensor-panel");
  assert.equal(panels.length, 4);
  assert.equal(panels[2].querySelector(".sensor-value").textContent.trim(), "13.00 m/s²");
  assert.equal(panels[3].querySelector(".sensor-value").textContent.trim(), "13.00 °/s");
  assert.deepEqual([...panels[3].querySelectorAll(".axis-readings dd")].map(node => node.textContent), ["-3.00", "-4.00", "-12.00"]);
  assert.equal(h.container.querySelector("details"), null);
  assert.ok([...h.container.querySelectorAll('.metric-quality')].every(node => node.getAttribute('aria-label').includes('Chưa đánh giá')));
  const prediction = h.container.querySelector(".prediction-panel");
  assert.ok(prediction.textContent.includes("Chưa có mô hình"));
  assert.equal(prediction.querySelector(".prediction-probability").textContent, "—");
  await h.mutate(() => socket.sendPayload(payload({ timestamp_ms: 2000, data_origin: "DEVICE",
    model_version: "edge-model-v1", prediction: { probability: 0.83, state: "ATTENTION" },
  })));
  assert.ok(prediction.textContent.includes("Cần theo dõi"));
  assert.equal(prediction.querySelector(".prediction-probability").textContent, "83%");
  assert.ok(prediction.textContent.includes("edge-model-v1"));
  await h.advance(5000);
  assert.equal(prediction.querySelector(".prediction-probability").textContent, "—");
  assert.ok(!prediction.textContent.includes("Cần theo dõi"));
  assert.ok(prediction.textContent.includes("Tạm ngưng"));
  assert.ok(h.container.querySelector('.connection-badge').textContent.includes("Dữ liệu cũ"));
  assert.equal(prediction.querySelector('.prediction-details-button'), null);
});

test("silent OPEN socket recovers even when close callback never arrives", async () => {
  const h = await mount();
  const socket = h.sockets[0];
  await h.mutate(() => { socket.open(); socket.sendPayload(payload()); });
  socket.emitClose = false;
  await h.advance(10000);
  assert.deepEqual(socket.sent, ["ping"]);
  await h.advance(5000);
  assert.equal(h.view().connectionStatus, "backend_disconnected");
  await h.advance(1500);
  assert.equal(h.sockets.length, 2);
  assert.equal(h.authRequests.length, 1);
  await h.mutate(() => { h.sockets[1].open(); h.sockets[1].sendPayload(payload({ timestamp_ms: 2000 })); });
  assert.equal(h.view().connectionStatus, "live");
  assert.equal(h.view().points.length, 2);
});

test("CONNECTING socket has a deadline and retries without reloading the page", async () => {
  const h = await mount();
  h.sockets[0].emitClose = false;
  await h.advance(10000);
  await h.advance(1500);
  assert.equal(h.sockets.length, 2);
});

test("reconnect renews local cookie before opening the replacement websocket", async () => {
  const h = await mount();
  await h.mutate(() => h.sockets[0].open());
  await h.mutate(() => h.sockets[0].close());
  await h.advance(1500);
  assert.equal(h.authRequests.length, 1);
  assert.equal(h.authRequests[0].url, "/__local/session");
  assert.equal(h.authRequests[0].options.credentials, "include");
  assert.equal(h.authRequests[0].options.body, undefined);
  assert.equal(h.sockets.length, 2);
});

test("first Dashboard waiting socket recovers without remount or hard refresh", async () => {
  const h = await mount({ dashboard: true, localSession: true, strict: true });
  const main = h.container.querySelector("#dashboard-content");
  const first = h.sockets.at(-1);
  await h.mutate(() => first.open());
  assert.ok(h.container.textContent.includes("Chờ dữ liệu"));
  first.emitClose = false;
  await h.advance(10000);
  assert.deepEqual(first.sent, ["ping"]);
  await h.advance(5000);
  await h.advance(1500);
  const recovered = h.sockets.at(-1);
  assert.notEqual(recovered, first);
  await h.mutate(() => { recovered.open(); recovered.sendPayload(payload()); });
  assert.equal(h.container.querySelector("#dashboard-content"), main);
  assert.ok(h.container.textContent.includes("Đang cập nhật"));
  assert.ok(h.container.textContent.includes("72.0 bpm"));
});

test("pong keeps transport alive without making an absent or old sensor sample live", async () => {
  const h = await mount();
  const socket = h.sockets[0];
  await h.mutate(() => socket.open());
  await h.advance(10000);
  await h.mutate(() => socket.onmessage({ data: "pong" }));
  assert.equal(h.view().connectionStatus, "waiting");
  await h.mutate(() => socket.sendPayload(payload()));
  await h.advance(10000);
  await h.mutate(() => socket.onmessage({ data: "pong" }));
  assert.equal(h.view().connectionStatus, "stale");
  assert.equal(h.view().points.length, 1);
  assert.equal(h.sockets.length, 1);
});

test("online/pageshow recovery clears waiting connection without a close event", async () => {
  const h = await mount();
  const first = h.sockets[0];
  first.emitClose = false;
  await h.mutate(() => window.dispatchEvent(new window.Event("online")));
  assert.equal(h.sockets.length, 2);
  const second = h.sockets[1];
  await h.mutate(() => { second.open(); second.sendPayload(payload()); second.close(); });
  await h.mutate(() => window.dispatchEvent(new window.PageTransitionEvent("pageshow", { persisted: true })));
  const third = h.sockets.at(-1);
  await h.mutate(() => third.open());
  assert.equal(h.view().connectionStatus, "waiting"); // Clock vẫn0; không dùng history làm mẫu của kết nối mới.
  await h.mutate(() => third.sendPayload(payload()));
  assert.equal(h.view().connectionStatus, "waiting"); // Gói trùng cũng không làm mới.
  await h.mutate(() => third.sendPayload(payload({ timestamp_ms: 2000 })));
  assert.equal(h.view().connectionStatus, "live");
});

test("automatic session panel only reads backend state and waits for confirmed session telemetry", async () => {
  const h = await mount({ dashboard: true, strict: true });
  const row = { session_id: "AUTO-UNIT", device_id: "device-a", data_origin: "DEVICE", state: "STARTING",
    requested_at: "2026-11-05T12:00:00Z", started_at: null, stopped_at: null, recording_complete: false,
    incomplete_reasons: ["RECORDING_NOT_FINISHED"] };
  h.setSessionRows([row]);
  const socket = h.sockets.at(-1);
  const frame = patch => payload({ data_origin: "DEVICE", session_id: null, model_version: "none",
    prediction: { probability: null, state: "UNCERTAIN" }, ...patch });
  await h.mutate(() => { socket.open(); socket.sendPayload(frame()); });
  const panel = () => h.container.querySelector('.header-session');
  const header = h.container.querySelector('.header-status');
  assert.equal(panel().parentElement, header);
  assert.equal(panel().nextElementSibling?.className, 'device-actions');
  assert.ok(panel().nextElementSibling.querySelector('.connection-badge'));
  assert.equal(h.container.querySelector('main .header-session'), null);
  assert.equal(h.container.querySelector('.session-control'), null);
  assert.ok(panel().textContent.includes("Đang chờ ESP xác nhận phiên"));
  assert.equal(panel().querySelector("button"), null);
  assert.ok(!panel().textContent.includes("Phiên đang hoạt động"));
  h.setSessionRows([{ ...row, state: "RECORDING", started_at: "2026-11-05T12:00:01Z" }]);
  await h.advance(1000);
  assert.ok(panel().textContent.includes("Đang chờ dữ liệu trong phiên"));
  await h.mutate(() => socket.sendPayload(frame({ timestamp_ms: 100, session_id: row.session_id })));
  assert.ok(panel().textContent.includes("Phiên đang hoạt động"));
  assert.ok(panel().textContent.includes("UNIT"));
  assert.ok(!panel().textContent.includes("AUTO-UNIT"));
  assert.equal(h.sessionRequests.every(request => request.options.method === "GET" && request.options.credentials === "include"), true);
  await h.advance(5000);
  assert.ok(!panel().textContent.includes("Phiên đang hoạt động"));
  assert.ok(panel().textContent.includes("Đang chờ dữ liệu trong phiên"));
  await h.unmount();
  assert.equal(h.timers.size, 0);
});

test("changing devices never keeps the other device's session label or issues a Start", async () => {
  const h = await mount({ dashboard: true });
  h.setSessionRows([{ session_id: "AUTO-A", device_id: "device-a", data_origin: "DEVICE", state: "RECORDING",
    requested_at: "2026-11-05T12:00:00Z", started_at: "2026-11-05T12:00:01Z", stopped_at: null,
    recording_complete: false, incomplete_reasons: [] }]);
  const socket = h.sockets[0];
  await h.mutate(() => {
    socket.open();
    socket.sendPayload(payload({ data_origin: "DEVICE", session_id: "AUTO-A" }));
    socket.sendPayload(payload({ device_id: "device-b", data_origin: "DEVICE", session_id: null }));
  });
  assert.equal(h.container.querySelector('.header-session-value').textContent, "A");
  await h.mutate(() => {
    const select = h.container.querySelector('select');
    select.value = 'device-b'; select.dispatchEvent(new window.Event('change', { bubbles: true }));
  });
  assert.equal(h.container.querySelector('.header-session'), null);
  assert.ok(h.sessionRequests.every(request => request.options.method === "GET"));
});

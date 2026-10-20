import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

// Real source/components, with only the network hook replaced for UI branch tests.
// These are not browser-layout, DOM-event or real React hook lifecycle tests.
let server;
let Dashboard;
let DeviceStatus;
let parser;
let streams;
let validation;
let snapshot;
let selection;
const fixtureKey = "__asdEaseDashboardTestSnapshot";

const payload = (changes = {}) => ({
  schema_version: "1.0",
  device_id: "device-a",
  session_id: "session-a",
  timestamp_ms: 1000,
  data_origin: "DEVICE",
  hr_bpm: 72,
  gsr: { raw: 1234, delta: -1 },
  movement: { score: 0.2 },
  signal_quality: { ppg: 0.9, gsr: 0.8, imu: 0.7 },
  prediction: { probability: 0.25, state: "NORMAL" },
  firmware_version: "test-firmware",
  model_version: "test-model",
  ...changes,
});

before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL("../", import.meta.url)),
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
    plugins: [{
      name: "dashboard-test-hook",
      enforce: "pre",
      resolveId(id) {
        if (id === "../hooks/useLiveTelemetry") {
          return "\0dashboard-test-hook";
        }
      },
      load(id) {
        if (id === "\0dashboard-test-hook") {
          return `export function useLiveTelemetry() { return globalThis.${fixtureKey}(); }`;
        }
      },
    }],
  });
  ({ Dashboard } = await server.ssrLoadModule("/src/pages/Dashboard.tsx"));
  ({ DeviceStatus } = await server.ssrLoadModule("/src/components/DeviceStatus.tsx"));
  parser = await server.ssrLoadModule("/src/utils/parseTelemetry.ts");
  streams = await server.ssrLoadModule("/src/utils/telemetryStream.ts");
  validation = await server.ssrLoadModule("/src/utils/validation.ts");
  globalThis[fixtureKey] = () => snapshot;
});

after(async () => {
  delete globalThis[fixtureKey];
  await server?.close();
});

function setup(changes = {}) {
  selection = undefined;
  snapshot = {
    telemetry: payload(),
    points: [{ time: 1, hr: 72, gsr: 1234, movement: 0.2, probability: 0.25 }],
    connectionStatus: "live",
    deviceIds: ["device-a", "device-b"],
    selectedDeviceId: "device-a",
    setSelectedDeviceId: (id) => { selection = id; },
    ...changes,
  };
  return renderToStaticMarkup(React.createElement(Dashboard));
}

function elements(node, predicate) {
  if (!React.isValidElement(node)) return [];
  return [
    ...(predicate(node) ? [node] : []),
    ...React.Children.toArray(node.props.children)
      .flatMap((child) => elements(child, predicate)),
  ];
}

test("live dashboard renders current prediction, quality and metrics", () => {
  const html = setup();
  for (const text of ["Dữ liệu đang cập nhật", "NORMAL", "25%", "90%", "72.0 bpm", "1234.0 ADC", "session-a"]) {
    assert.ok(html.includes(text), text);
  }
  assert.ok(!html.includes("Đang hiển thị dữ liệu nhận trước đó"));
  assert.ok(!html.includes("SYNTHETIC DATA"));
});

for (const [status, label] of [
  ["stale", "Dữ liệu đã cũ"],
  ["backend_disconnected", "Mất kết nối backend"],
  ["waiting", "Đang chờ dữ liệu"],
]) {
  test(`${status} retains old metrics but hides current prediction and quality`, () => {
    const html = setup({ connectionStatus: status });
    for (const text of [label, "Đang hiển thị dữ liệu nhận trước đó", "Chưa có dữ liệu hiện tại", "72.0 bpm", "không phải dữ liệu trực tiếp"]) {
      assert.ok(html.includes(text), text);
    }
    for (const text of ["NORMAL", "25%", "90%", "CALIBRATING"]) {
      assert.ok(!html.includes(text), text);
    }
  });
}

test("empty dashboard disables selection without inventing measurements", () => {
  const html = setup({ telemetry: null, points: [], deviceIds: [], selectedDeviceId: null, connectionStatus: "waiting" });
  assert.match(html, /<select[^>]*disabled/);
  for (const text of ["Chưa nhận dữ liệu thiết bị", "Chưa có dữ liệu hiện tại", "Schema: —", "Firmware: —"]) {
    assert.ok(html.includes(text), text);
  }
  for (const text of ["CALIBRATING", "NORMAL", "0%", "0.0 bpm", "Đang hiển thị dữ liệu nhận trước đó"]) {
    assert.ok(!html.includes(text), text);
  }
});

test("synthetic provenance survives stale and disconnected states", () => {
  for (const status of ["live", "stale", "waiting", "backend_disconnected"]) {
    assert.ok(setup({ telemetry: payload({ data_origin: "SYNTHETIC" }), connectionStatus: status }).includes("SYNTHETIC DATA"));
  }
});

test("null measurements stay unavailable while real zero remains visible", () => {
  const html = setup({ telemetry: payload({ hr_bpm: null, gsr: { raw: null, delta: null }, movement: { score: null }, prediction: { probability: null, state: "UNCERTAIN" }, session_id: null }) });
  assert.ok(html.includes("UNCERTAIN"));
  assert.ok(html.includes("Chưa gắn phiên"));
  assert.ok(!html.includes("0.0 bpm"));
  assert.ok(!html.includes("0.0 ADC"));
  const zero = setup({ telemetry: payload({ gsr: { raw: 0, delta: 0 }, movement: { score: 0 }, prediction: { probability: 0, state: "NORMAL" } }) });
  assert.ok(zero.includes("0.0 ADC"));
  assert.ok(zero.includes("0%"));
});

test("selector has accessible associations and forwards chosen id to hook", () => {
  setup();
  const tree = Dashboard();
  const select = elements(tree, (element) => element.type === "select")[0];
  const label = elements(tree, (element) => element.type === "label")[0];
  assert.equal(select.props.value, "device-a");
  assert.equal(select.props.disabled, false);
  assert.equal(label.props.htmlFor, select.props.id);
  assert.equal(elements(tree, (element) => element.props.id === select.props["aria-describedby"]).length, 1);
  select.props.onChange({ target: { value: "device-b" } });
  assert.equal(selection, "device-b");
  select.props.onChange({ target: { value: "" } });
  assert.equal(selection, null);
  const html = setup({ selectedDeviceId: "device-b", telemetry: payload({ device_id: "device-b", hr_bpm: 88, session_id: "session-b" }) });
  assert.match(html, /<option value="device-b" selected="">/);
  assert.ok(html.includes("88.0 bpm"));
  assert.ok(html.includes("session-b"));
  assert.ok(!html.includes("72.0 bpm"));
});

test("all four charts receive selected stream history even when stale", () => {
  setup({ connectionStatus: "stale" });
  const chartElements = elements(Dashboard(), (element) => Array.isArray(element.props.data));
  assert.equal(chartElements.length, 4);
  for (const chart of chartElements) assert.equal(chart.props.data, snapshot.points);
});

test("device and session identifiers are rendered as text, not HTML", () => {
  const attack = '<script>alert("x")</script>';
  const html = setup({ telemetry: payload({ device_id: attack, session_id: attack }), selectedDeviceId: attack, deviceIds: [attack] });
  assert.ok(!html.includes("<script>"));
  assert.ok(html.includes("&lt;script&gt;"));
});

test("DeviceStatus prioritizes explicit status and keeps polite announcements", () => {
  for (const [status, text] of [["live", "Dữ liệu đang cập nhật"], ["stale", "Dữ liệu đã cũ"], ["waiting", "Đang chờ dữ liệu"], ["backend_disconnected", "Mất kết nối backend"]]) {
    const html = renderToStaticMarkup(React.createElement(DeviceStatus, { status, connected: status !== "live" }));
    assert.ok(html.includes(text));
    assert.ok(html.includes('role="status"'));
    assert.ok(html.includes('aria-live="polite"'));
    assert.ok(html.includes("Chưa có thiết bị"));
  }
});

test("validation rejects arrays, numeric strings and non-finite numbers", () => {
  assert.equal(validation.isRecord({}), true);
  for (const value of [null, [], "{}", 1]) assert.equal(validation.isRecord(value), false);
  for (const value of [NaN, Infinity, -Infinity, "1", null]) assert.equal(validation.isFiniteNumber(value), false);
  assert.equal(validation.isNumberInRange(0, 0, 1), true);
  assert.equal(validation.isNumberInRange(1, 0, 1), true);
  assert.equal(validation.isNumberInRange(1.1, 0, 1), false);
});

test("parser accepts nulls and rejects malformed, missing and invalid fields", () => {
  const valid = payload();
  assert.deepEqual(parser.parseTelemetry(JSON.stringify(valid)), valid);
  assert.equal(parser.isTelemetry(payload({ hr_bpm: null, session_id: null })), true);
  for (const text of ["{", "null", "[]", "{}", '{"hr_bpm":1e999}']) assert.equal(parser.parseTelemetry(text), null);
  for (const key of Object.keys(valid)) {
    const missing = { ...valid };
    delete missing[key];
    assert.equal(parser.isTelemetry(missing), false, key);
  }
  for (const patch of [{ movement: null }, { gsr: [] }, { timestamp_ms: 1.5 }, { timestamp_ms: Number.MAX_SAFE_INTEGER + 1 }, { hr_bpm: 241 }, { data_origin: "OTHER" }, { signal_quality: { ppg: 2, gsr: 1, imu: 1 } }, { prediction: { probability: 0.5, state: "STALE" } }]) {
    assert.equal(parser.isTelemetry(payload(patch)), false);
  }
});

test("stream buffer is immutable, capped at 60 and duplicates do not refresh", () => {
  let current = streams.updateTelemetryStream(null, payload(), 100);
  for (let index = 2; index <= 125; index++) {
    const previous = current;
    const saved = structuredClone(previous);
    current = streams.updateTelemetryStream(previous, payload({ timestamp_ms: index * 1000 }), index * 100);
    assert.deepEqual(previous, saved);
    assert.equal(current.points.length, Math.min(index, 60));
  }
  assert.equal(current.points[0].time, 66);
  assert.equal(current.points.at(-1).time, 125);
  assert.equal(streams.updateTelemetryStream(current, payload({ timestamp_ms: 125000 }), 99999), current);
  assert.equal(current.receivedAtMs, 12500);
});

test("stream resets on device, session, origin or backward timestamp", () => {
  const first = streams.updateTelemetryStream(null, payload(), 100);
  const previous = streams.updateTelemetryStream(first, payload({ timestamp_ms: 2000 }), 200);
  for (const patch of [{ device_id: "device-b" }, { session_id: "session-b" }, { session_id: null }, { data_origin: "SYNTHETIC" }, { timestamp_ms: 0 }]) {
    const next = streams.updateTelemetryStream(previous, payload({ timestamp_ms: 2000, ...patch }), 300);
    assert.equal(next.points.length, 1);
    assert.equal(next.receivedAtMs, 300);
  }
});

test("freshness uses receive clock and respects default/custom timeout boundaries", () => {
  const stream = streams.updateTelemetryStream(null, payload({ timestamp_ms: 99999999 }), 100);
  assert.equal(streams.getConnectionStatus(false, stream, 100), "backend_disconnected");
  assert.equal(streams.getConnectionStatus(true, null, 100), "waiting");
  assert.equal(streams.getConnectionStatus(true, stream, 5099), "live");
  assert.equal(streams.getConnectionStatus(true, stream, 5100), "stale");
  assert.equal(streams.getConnectionStatus(true, stream, 349, 250), "live");
  assert.equal(streams.getConnectionStatus(true, stream, 350, 250), "stale");
});

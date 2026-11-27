import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

// Dùng mã/component thật; chỉ thay hook mạng để thử các nhánh hiển thị.
// Không kiểm tra bố cục, sự kiện DOM hoặc vòng đời hook thật trong file này.
let server;
let Dashboard;
let DeviceStatus;
let ImuReadings;
let PredictionPanel;
let parser;
let streams;
let validation;
let heartRateDisplay;
let heartRatePlot;
let forecastHeartRate;
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
  ({ ImuReadings } = await server.ssrLoadModule("/src/components/ImuReadings.tsx"));
  ({ PredictionPanel } = await server.ssrLoadModule("/src/components/PredictionPanel.tsx"));
  parser = await server.ssrLoadModule("/src/utils/parseTelemetry.ts");
  streams = await server.ssrLoadModule("/src/utils/telemetryStream.ts");
  validation = await server.ssrLoadModule("/src/utils/validation.ts");
  ({ heartRateDisplay, heartRatePlot, forecastHeartRate } = await server.ssrLoadModule("/src/utils/heartRateDisplay.ts"));
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
    historySeconds: 0,
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

const plain = html => html.replace(/<[^>]*>/g, "").replace(/\s+/g, " ");

test("header shows one connecting status while keeping the connect action disabled", () => {
  const html = setup({ connectionStatus: "waiting", monitoring: true, connectionTimedOut: false });
  const header = html.slice(0, html.indexOf("<main"));
  assert.equal((plain(header).match(/Đang kết nối/g) ?? []).length, 1);
  assert.match(header, /Đang kết nối <span class="connection-dots" aria-hidden="true">/);
  assert.match(header, /<button[^>]*class="device-connect-button"[^>]*disabled=""[^>]*aria-busy="true"[^>]*>Kết nối<\/button>/);
});

test("header enables disconnect after live data and retry after a timeout", () => {
  const live = setup({ monitoring: true, connectionStatus: "live", connectionTimedOut: false });
  assert.match(live, /<button[^>]*class="device-connect-button"[^>]*aria-busy="false"[^>]*data-connected="true"[^>]*>Ngắt kết nối<\/button>/);
  assert.ok(!live.includes('class="connection-dots"'));
  const timedOut = setup({ monitoring: true, connectionStatus: "waiting", connectionTimedOut: true });
  assert.match(timedOut, /<button[^>]*class="device-connect-button"[^>]*aria-busy="false"[^>]*>Thử lại<\/button>/);
  assert.ok(!timedOut.includes('class="connection-dots"'));
});

test("demo HR labels a bounded last estimate without filling the chart or telemetry", () => {
  const telemetry = payload({ firmware_version: "0.3.16-demo", hr_bpm: null, timestamp_ms: 6000 });
  const points = [{ time: 1, hr: 72 }, { time: 6, hr: null }];
  const original = JSON.stringify({ telemetry, points });
  const html = setup({ telemetry, points });
  assert.ok(plain(html).includes("Nhịp tim ước tính"));
  assert.ok(plain(html).includes("72.0 bpm"));
  assert.ok(plain(html).includes("Nhận cách đây 5 giây"));
  assert.equal(JSON.stringify({ telemetry, points }), original);
  assert.equal(heartRateDisplay({ ...telemetry, timestamp_ms: 11000 }, points, true).held, true);
  assert.equal(heartRateDisplay({ ...telemetry, timestamp_ms: 11001 }, points, true).value, null);
  assert.equal(heartRateDisplay(telemetry, points, false).value, null);
  assert.equal(heartRateDisplay({ ...telemetry, firmware_version: "0.3.13-led10" }, points, true).value, null);
  assert.equal(heartRateDisplay({ ...telemetry, timestamp_ms: 500 }, points, true).value, null);
  assert.equal(heartRateDisplay(telemetry, [], true).value, null);
  const newest = heartRateDisplay({ ...telemetry, hr_bpm: 78 }, points, true);
  assert.equal(newest.value, 78);
  assert.equal(newest.held, false);
});

test("live dashboard renders current prediction, quality and metrics", () => {
  const html = setup();
  for (const text of ["Đang cập nhật", "Bình thường", "25%", "72.0 bpm", "1234 ADC", "session-a"]) {
    assert.ok(plain(html).includes(text), text);
  }
  assert.ok(!html.includes("Đang hiển thị dữ liệu nhận trước đó"));
  assert.ok(!html.includes("Dữ liệu giả lập"));
});

test("tracker HR is labelled as an estimate and keeps the same expiry semantics", () => {
  const telemetry = payload({ firmware_version: "0.3.17-tracker", hr_bpm: 78 });
  let html = setup({ telemetry });
  assert.ok(plain(html).includes("Nhịp tim ước tính"));
  assert.ok(!plain(html).includes("Theo dõi chu kỳ"));
  assert.ok(plain(html).includes("78.0 bpm"));
  const points = [{ time: 1, hr: 78 }, { time: 6, hr: null }];
  html = setup({ telemetry: { ...telemetry, hr_bpm: null, timestamp_ms: 6000 }, points });
  assert.ok(plain(html).includes("Đang duy trì · 5 giây chờ xung mới"));
  assert.ok(plain(html).includes("Nét đứt: nhịp duy trì tối đa 15 giây"));
  assert.equal(heartRateDisplay({ ...telemetry, hr_bpm: null, timestamp_ms: 16000 }, points, true).predicted, true);
  assert.equal(heartRateDisplay({ ...telemetry, hr_bpm: null, timestamp_ms: 16001 }, points, true).value, null);
  assert.equal(heartRateDisplay({ ...telemetry, hr_bpm: null, timestamp_ms: 6000 }, points, false).value, null);
  const noContactTelemetry = {
    ...telemetry, schema_version: "1.2", hr_bpm: null, timestamp_ms: 2000,
    movement: { score: 0.1, acceleration: { x: 0, y: 0, z: 9.8 }, angular_velocity: { x: 0, y: 0, z: 0 } },
    signal_quality: {
      method: "engineering-v2", window_ms: 8000,
      hr: { score: 0, reason: "no_contact" }, gsr: { score: 1, reason: "ok" },
      acceleration: { score: 1, reason: "ok" }, rotation: { score: 1, reason: "ok" },
    },
  };
  const noContactDisplay = heartRateDisplay(noContactTelemetry, [{ time: 1, hr: 78 }, { time: 2, hr: null, hrNoContact: true }], true);
  assert.equal(noContactDisplay.value, null);
  assert.equal(noContactDisplay.predicted, false);
  const noContactPlot = heartRatePlot([{ time: 1, hr: 78 }, { time: 2, hr: null, hrNoContact: true }, { time: 3, hr: null, hrNoContact: true }], true);
  assert.equal(noContactPlot[1].hrForecast, null);
  assert.equal(noContactPlot[2].hrForecast, null);
});

test("forecast bridges only short gaps in a separate series and never alters measurements", () => {
  const points = [{ time: 0, hr: 70 }, { time: 1, hr: 71 }, { time: 2, hr: 72 },
    ...Array.from({ length: 16 }, (_, index) => ({ time: index + 3, hr: null })), { time: 19, hr: 75 }];
  const original = JSON.stringify(points);
  const output = heartRatePlot(points, true);
  assert.equal(output[2].hrForecast, 72); // Điểm nối vào đường tạm tính.
  assert.ok(output[3].hrForecast > 72 && output[3].hrForecast < 75);
  assert.ok(output[17].hrForecast !== null); // Hạn15giây tính từ HR thật, không từ dự báo trước đó.
  assert.equal(output[18].hrForecast, null);
  assert.equal(output[19].hrForecast, null); // Không nối qua đoạn đã hết hạn.
  assert.equal(JSON.stringify(points), original);
  assert.ok(output.slice(3, 19).every(point => point.hr === null));
  assert.ok(heartRatePlot(points, false).every(point => point.hrForecast === null));
  assert.equal(forecastHeartRate([{ time: 0, hr: null }], 1), null);
  assert.equal(forecastHeartRate([{ time: 2, hr: 70 }, { time: 1, hr: null }], 3), null);
  assert.equal(forecastHeartRate([{ time: 2, hr: 70 }], 1), null);
  assert.equal(forecastHeartRate([{ time: 0, hr: 40 }], 2).value, 40); // Không sửa40 thành nhịp nghỉ đẹp.
});

test("forecast trend is bounded and stops after reconnect history is cleared", () => {
  const points = [{ time: 0, hr: 70 }, { time: 1, hr: 90 }, { time: 2, hr: 110 }];
  const prediction = forecastHeartRate(points, 17);
  assert.ok(prediction.value > 110 && prediction.value < 113);
  assert.equal(forecastHeartRate(points, 17.001), null);
  assert.equal(forecastHeartRate([], 17), null);
  assert.equal(forecastHeartRate([{ time: 0, hr: 70 }, { time: 1, hr: 90 }, { time: 2, hr: 70 }], 5).value, 70);
});

for (const [status, label] of [
  ["stale", "Dữ liệu cũ"],
  ["backend_disconnected", "Chưa kết nối"],
  ["waiting", "Chờ dữ liệu"],
]) {
  test(`${status} retains old metrics but hides current prediction and quality`, () => {
    const html = setup({ connectionStatus: status });
    for (const text of [label, "72.0 bpm"]) {
      assert.ok(plain(html).includes(text), text);
    }
    for (const text of ["Bình thường", "25%", "90%", "Đang hiệu chuẩn"]) {
      assert.ok(!html.includes(text), text);
    }
    assert.ok(!html.includes('stream-notice')); // Khung nhắc đã được người dùng yêu cầu bỏ.
  });
}

test("empty dashboard disables selection without inventing measurements", () => {
  const html = setup({ telemetry: null, points: [], deviceIds: [], selectedDeviceId: null, connectionStatus: "waiting" });
  assert.match(html, /<select[^>]*disabled/);
  for (const text of ["Chưa có thiết bị", "— mẫu", "Gói dữ liệu", "Firmware"]) {
    assert.ok(html.includes(text), text);
  }
  assert.ok(!html.includes('stream-notice'));
  for (const text of ["Đang hiệu chuẩn", "Bình thường", "0%", "0.0 bpm", "Đang hiển thị dữ liệu nhận trước đó"]) {
    assert.ok(!html.includes(text), text);
  }
});

test("dashboard removes global counts and reports only measured points in each card", () => {
  const points = [
    { time: 1, hr: 75, gsr: null, ax: 1, ay: 2, az: 3, gx: 1, gy: 2, gz: 3 },
    { time: 2, hr: null, hrForecast: 75, gsr: 1234, ax: 1, ay: 2, az: 3, gx: null, gy: null, gz: null },
    { time: 3, hr: null, hrForecast: 75, gsr: null, ax: 1, ay: 2, az: 3, gx: 1, gy: 2, gz: 3 },
  ];
  const html = setup({ points });
  assert.ok(!html.includes('page-toolbar'));
  assert.ok(!html.includes('Thông số cảm biến'));
  assert.equal([...html.matchAll(/class="metric-sample-count"[^>]*>— mẫu/g)].length, 4);
  assert.ok(html.includes('sidebar-device-info'));
  assert.ok(!html.includes('device-details'));
  const offline = setup({ points, connectionStatus: 'stale' });
  assert.equal([...offline.matchAll(/class="metric-sample-count"[^>]*>— mẫu/g)].length, 4);
});

test("synthetic provenance survives stale and disconnected states", () => {
  for (const status of ["live", "stale", "waiting", "backend_disconnected"]) {
    const html = setup({ telemetry: payload({ data_origin: "SYNTHETIC" }), connectionStatus: status });
    assert.ok(html.includes("Dữ liệu giả lập"));
    assert.ok(html.includes('data-origin="SYNTHETIC"'));
  }
});

test("null measurements stay unavailable while real zero remains visible", () => {
  const html = setup({ telemetry: payload({ hr_bpm: null, gsr: { raw: null, delta: null }, movement: { score: null }, prediction: { probability: null, state: "UNCERTAIN" }, session_id: null, model_version: "none" }) });
  assert.ok(html.includes("Chưa có mô hình"));
  assert.ok(!html.includes("Giữ cảm biến yên trên da để tìm nhịp."));
  assert.ok(html.includes("Chưa có mẫu hợp lệ"));
  assert.ok(!html.includes("Thiết bị chưa chạy mô hình AI."));
  assert.ok(!html.includes('class="header-session"'));
  assert.ok(!html.includes("0.0 bpm"));
  assert.ok(!html.includes("0.0 ADC"));
  const zero = setup({ telemetry: payload({ gsr: { raw: 0, delta: 0 }, movement: { score: 0 }, prediction: { probability: 0, state: "NORMAL" } }) });
  assert.ok(plain(zero).includes("0 ADC"));
  assert.ok(zero.includes("0%"));
});

test("device without model keeps quality unestimated and prepares prediction slots without invented data", () => {
  const html = setup({ telemetry: payload({ model_version: "none",
    signal_quality: { ppg: 0, imu: 0, gsr: 0 },
    prediction: { probability: null, state: "UNCERTAIN" } }) });
  assert.ok(!html.includes("Thiết bị chưa chạy mô hình AI."));
  assert.ok(html.includes("Chưa đánh giá"));
  assert.ok(!plain(html).includes("0%"));
  for (const label of ["Dự đoán AI", "Trạng thái dự đoán", "Xác suất"]) {
    assert.ok(html.includes(label), label);
  }
  assert.ok(!html.includes('aria-label="Biểu đồ Xác suất'));
  assert.ok(html.includes('sidebar-device-info'));
  assert.ok(!html.includes('prediction-history'));
});

test("selector keeps accessible associations and sidebar retains device metadata", () => {
  const html = setup({ selectedDeviceId: "device-b", telemetry: payload({ device_id: "device-b", hr_bpm: 88, session_id: "session-b" }) });
  assert.match(html, /<label[^>]*for="live-device"/);
  assert.match(html, /<select[^>]*id="live-device"[^>]*aria-describedby="device-selection-help"/);
  assert.match(html, /<option value="device-b" selected="">/);
  assert.ok(plain(html).includes("88.0 bpm"));
  assert.ok(html.includes("session-b"));
  assert.ok(!plain(html).includes("72.0 bpm"));
  assert.ok(html.includes('aria-current="page"'));
});

test("device and session identifiers are rendered as text, not HTML", () => {
  const attack = '<script>alert("x")</script>';
  const html = setup({ telemetry: payload({ device_id: attack, session_id: attack }), selectedDeviceId: attack, deviceIds: [attack] });
  assert.ok(!html.includes("<script>"));
  assert.ok(html.includes("&lt;script&gt;"));
});

test("DeviceStatus prioritizes explicit status and keeps polite announcements", () => {
  for (const [status, text] of [["live", "Đang cập nhật"], ["stale", "Dữ liệu cũ"], ["waiting", "Chờ dữ liệu"], ["backend_disconnected", "Chưa kết nối"]]) {
    const html = renderToStaticMarkup(React.createElement(DeviceStatus, { status, connected: status !== "live" }));
    assert.ok(html.includes(text));
    assert.ok(html.includes('role="status"'));
    assert.ok(html.includes('aria-live="polite"'));
    assert.ok(html.includes("Chưa có thiết bị"));
    assert.ok(html.includes(status === "live" ? "Đã kết nối" : "Chưa kết nối"));
    assert.ok(html.includes(`data-device-connected="${status === "live"}"`));
    if (status !== "live") assert.ok(!html.includes("Đã kết nối"));
  }
});

test("prediction panel waits for telemetry or model and never shows results from no-model DEVICE", () => {
  const render = (telemetry, live, points = []) => renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry, live, points }));
  const empty = render(null, false);
  assert.ok(empty.includes("Chờ dữ liệu"));
  assert.ok(!empty.includes("prediction-history"));
  assert.ok(!plain(empty).includes("0%"));
  const invalidModel = render(payload({ model_version: "none", prediction: { probability: 0.8, state: "ATTENTION" } }), true,
    [{ time: 1, probability: 0.8 }]);
  assert.ok(invalidModel.includes("Chưa có mô hình"));
  assert.ok(!invalidModel.includes("Cần theo dõi"));
  assert.ok(!plain(invalidModel).includes("80%"));
  assert.ok(!invalidModel.includes("prediction-history"));
});

test("prediction panel renders every supported state and preserves probability boundaries", () => {
  for (const [state, label, probability] of [
    ["NORMAL", "Bình thường", 0], ["ATTENTION", "Cần theo dõi", 1],
    ["UNCERTAIN", "Chưa xác định", null], ["CALIBRATING", "Đang hiệu chuẩn", null],
  ]) {
    const html = renderToStaticMarkup(React.createElement(PredictionPanel, {
      telemetry: payload({ model_version: "model-v1", prediction: { state, probability } }),
      live: true, points: [],
    }));
    assert.ok(html.includes(label), label);
    assert.ok(html.includes("model-v1"));
    if (probability !== null) assert.ok(plain(html).includes(`${probability * 100}%`));
    else assert.ok(!plain(html).includes("0%"));
  }
});

test("stale prediction hides current values and leaves history to the reports page", () => {
  const html = renderToStaticMarkup(React.createElement(PredictionPanel, {
    telemetry: payload({ prediction: { probability: 0.91, state: "ATTENTION" } }),
    live: false, points: [{ time: 1, probability: 0.91 }],
  }));
  assert.ok(html.includes("Tạm ngưng"));
  assert.ok(!html.includes("prediction-history"));
  assert.ok(!html.includes("Cần theo dõi"));
  assert.ok(!plain(html).includes("91%"));
  assert.ok(!html.includes('aria-label="Biểu đồ Xác suất'));
});

test("synthetic predictions are explicitly marked even with model_version none", () => {
  for (const live of [true, false]) {
    const html = renderToStaticMarkup(React.createElement(PredictionPanel, {
      telemetry: payload({ data_origin: "SYNTHETIC", model_version: "none" }),
      live, points: [{ time: 1, probability: 0.25 }],
    }));
    assert.ok(html.includes("Giả lập") || html.includes("giả lập"));
    if (live) assert.ok(plain(html).includes("25%"));
    else assert.ok(!plain(html).includes("25%"));
    assert.ok(!html.includes('prediction-history'));
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

test("stream retains 60 seconds immutably and duplicates do not refresh", () => {
  let current = streams.updateTelemetryStream(null, payload(), 100);
  for (let index = 2; index <= 125; index++) {
    const previous = current;
    const saved = structuredClone(previous);
    current = streams.updateTelemetryStream(previous, payload({ timestamp_ms: index * 1000 }), index * 100);
    assert.deepEqual(previous, saved);
    assert.equal(current.points.length, Math.min(index, 61));
  }
  assert.equal(current.points[0].time, 65);
  assert.equal(current.points.at(-1).time, 125);
  assert.equal(streams.updateTelemetryStream(current, payload({ timestamp_ms: 125000 }), 99999), current);
  assert.equal(current.receivedAtMs, 12500);
  assert.equal(current.firstTimestampMs, 1000);
});

test("time window handles fast samples and long dropouts without counting phantom points", () => {
  let current = null;
  for (let i = 0; i <= 140; i++) current = streams.updateTelemetryStream(current, payload({ timestamp_ms: i * 500 }), i);
  assert.equal(current.points.length, 121); // 2 Hz trong 60 giây, không giới hạn theo 60 gói.
  assert.equal(current.points[0].time, 10);
  current = streams.updateTelemetryStream(current, payload({ timestamp_ms: 140000 }), 1000);
  assert.equal(current.points.length, 1);
  assert.equal(current.points[0].time, 140);
  assert.equal(current.firstTimestampMs, 0);
  current = streams.updateTelemetryStream(current, payload({ timestamp_ms: 0 }), 1001);
  assert.equal(current.firstTimestampMs, 0);
  assert.equal(current.points.length, 1);
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

const axesPayload = (movement = {}) => payload({ schema_version: "1.1", movement: {
  score: 0.3, acceleration: { x: -0.5, y: 0, z: 9.806 },
  angular_velocity: { x: -90, y: 0, z: 20.5 }, ...movement,
} });

test("1.1 parser requires complete finite vectors and correct version", () => {
  assert.equal(parser.isTelemetry(axesPayload()), true);
  assert.equal(parser.isTelemetry(axesPayload({ acceleration: null, angular_velocity: null })), true);
  for (const acceleration of [undefined, {}, [], { x: 1, y: 2 }, { x: 1, y: 2, z: "3" },
      { x: true, y: 0, z: 9.8 }, { x: Infinity, y: 0, z: 9.8 }, { x: 1, y: 2, z: 3, w: 4 }]) {
    assert.equal(parser.isTelemetry(axesPayload({ acceleration })), false);
    assert.equal(parser.isTelemetry(axesPayload({ angular_velocity: acceleration })), false);
  }
  assert.equal(parser.isTelemetry({ ...axesPayload(), schema_version: "1.0" }), false);
  assert.equal(parser.isTelemetry({ ...axesPayload(), schema_version: "2.0" }), false);
});

test("separate IMU readings render signed axes and physical units, including zero", () => {
  const html = setup({ telemetry: axesPayload() });
  for (const label of ["Gia tốc", "Tốc độ xoay", "m/s²", "°/s", "Ax", "Ay", "Az", "Gx", "Gy", "Gz", "-0.50", "0.00", "9.81", "-90.00", "20.50"]) {
    assert.ok(html.includes(label), label);
  }
  assert.ok(!html.includes("Điểm chuyển động"));
  const missing = setup({ telemetry: axesPayload({ acceleration: null, angular_velocity: null }) });
  assert.ok(missing.includes("Chưa có mẫu hợp lệ"));
  assert.ok(!missing.includes("0.00"));
  const combined = setup({ telemetry: axesPayload({
    acceleration: { x: 3, y: 4, z: 12 },
    angular_velocity: { x: -3, y: -4, z: -12 },
  }) });
  assert.equal((combined.match(/Độ lớn tổng hợp/g) ?? []).length, 2);
  assert.equal((combined.match(/>13\.00</g) ?? []).length, 2);
  assert.ok(combined.includes("-12.00")); // Giữ dấu từng trục, độ lớn luôn không âm.
  assert.ok(!combined.includes("Gia tốc gồm trọng lực"));
  const stationary = setup({ telemetry: axesPayload({
    acceleration: { x: 0, y: 0, z: 9.80665 },
    angular_velocity: { x: 0, y: 0, z: 0 },
  }) });
  assert.match(stationary, /sensor-value[^>]*><span>9\.81</);
  assert.match(stationary, /sensor-value[^>]*><span>0\.00</);
});

test("1.1 stream preserves six axes and separates missing groups and protocol versions", () => {
  const first = streams.updateTelemetryStream(null, axesPayload(), 100);
  const point = first.points[0];
  assert.deepEqual([point.ax, point.ay, point.az, point.gx, point.gy, point.gz], [-0.5, 0, 9.806, -90, 0, 20.5]);
  const missing = streams.updateTelemetryStream(first, { ...axesPayload({ acceleration: null }), timestamp_ms: 2000 }, 200);
  assert.deepEqual([missing.points[1].ax, missing.points[1].ay, missing.points[1].az], [null, null, null]);
  assert.equal(missing.points[1].gx, -90);
  const legacy = streams.updateTelemetryStream(missing, payload({ timestamp_ms: 3000 }), 300);
  assert.equal(legacy.points.length, 1);
  assert.deepEqual([legacy.points[0].ax, legacy.points[0].gx], [null, null]);
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

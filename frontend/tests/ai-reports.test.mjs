import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let server, eventTime, listAiReportPage, clearAiReports, AiReports, formatDuration, inferReason, PredictionPanel, Dashboard, updateTelemetryStream, resetStreamAiWindow;
const workspaceFixture = "__asdWorkspaceNavigationTest";
before(async () => {
  server = await createServer({ root: fileURLToPath(new URL("../", import.meta.url)),
    server: { middlewareMode: true, hmr: false }, appType: "custom",
    plugins: [{ name: "workspace-test-hooks", enforce: "pre",
      resolveId(id) {
        if (id === "../hooks/useLiveTelemetry") return "\0workspace-live-fixture";
        if (id === "../hooks/useDeviceSession") return "\0workspace-session-fixture";
      },
      load(id) {
        if (id === "\0workspace-live-fixture") return `import { useEffect } from "react";
          export function useLiveTelemetry() {
            useEffect(() => { globalThis.${workspaceFixture}.mounts++; return () => { globalThis.${workspaceFixture}.unmounts++; }; }, []);
            return globalThis.${workspaceFixture}.snapshot;
          }`;
        if (id === "\0workspace-session-fixture") return 'export function useDeviceSession() { return {session:null,verified:true,error:""}; }';
      } }],
  });
  ({ eventTime, listAiReportPage, clearAiReports } = await server.ssrLoadModule("/src/api/reports.ts"));
  ({ AiReports, formatDuration, inferReason } = await server.ssrLoadModule("/src/pages/AiReports.tsx"));
  ({ PredictionPanel } = await server.ssrLoadModule("/src/components/PredictionPanel.tsx"));
  ({ Dashboard } = await server.ssrLoadModule("/src/pages/Dashboard.tsx"));
  ({ updateTelemetryStream, resetStreamAiWindow } = await server.ssrLoadModule("/src/utils/telemetryStream.ts"));
});
after(async () => { await server?.close(); });
const event = (id, second, patch = {}) => ({ id, device_id: "ESP-001", session_id: "SESSION-A", state: "ATTENTION",
  record_count: 1, reason: null, ended_at: `2026-11-15T00:00:${String(second).padStart(2, "0")}`, probability: .7, timestamp_ms: second * 1000, created_at: `2026-11-15T00:00:${String(second).padStart(2, "0")}`, ...patch });

test("report history treats backend naive times as UTC", () => {
  assert.equal(eventTime("2026-11-15T00:00:00"), Date.parse("2026-11-15T00:00:00Z"));
  assert.equal(eventTime("2026-11-15T07:00:00+07:00"), Date.parse("2026-11-15T00:00:00Z"));

});

test("report API selects the current device and excludes normal, unknown and invalid probabilities", async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async (url, options) => {
      assert.equal(url.searchParams.get("device_id"), "ESP-001");
      assert.equal(url.searchParams.get("page"), "2");
      assert.equal(url.pathname, "/api/v1/reports/ai");
      assert.equal(options.credentials, "include");
      return { ok: true, status: 200, json: async () => ({ total: 25, page: 2, page_size: 10, items: [event(1, 1), event(2, 2, { state: "NORMAL" }),
        event(3, 3, { state: "UNCERTAIN", probability: null }), event(4, 4, { device_id: "ESP-OTHER" }),
        event(5, 5, { probability: 1.1 }), event(6, 6, { probability: null })] }) };
    };
    const result = await listAiReportPage("ESP-001", 2, new AbortController().signal);
    assert.deepEqual(result.items.map(row => row.id), [1]);
  } finally { globalThis.fetch = original; }
});

test("report empty state is honest and current AI panel no longer contains history", () => {
  const report = renderToStaticMarkup(React.createElement(AiReports, { deviceId: null }));
  assert.ok(report.includes("Chi tiết cảnh báo"));
  assert.ok(report.includes("0 kết quả"));
  assert.ok(report.includes("Lý do"));
  assert.ok(!report.includes("Những thời điểm cần chú ý"));
  assert.ok(!report.includes("Cảnh báo nghiêm trọng"));
  const current = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: null, live: false }));
  assert.ok(current.includes("Dự đoán AI"));
  assert.ok(!current.includes("Lịch sử"));
});

test("formatDuration formats seconds <= 59 and minutes + seconds > 59", () => {
  assert.equal(formatDuration(0), "0 giây");
  assert.equal(formatDuration(25), "25 giây");
  assert.equal(formatDuration(59), "59 giây");
  assert.equal(formatDuration(60), "1 phút");
  assert.equal(formatDuration(75), "1 phút 15 giây");
  assert.equal(formatDuration(120), "2 phút");
  assert.equal(formatDuration(135), "2 phút 15 giây");
});

test("inferReason provides domain-accurate explanation when backend reason is null", () => {
  assert.equal(inferReason({ reason: "Tùy biến" }), "Tùy biến");
  assert.equal(inferReason({ reason: null, probability: 0.9 }), "EDA, PPG tăng cao, ACC tĩnh");
  assert.equal(inferReason({ reason: null, probability: 0.75 }), "EDA, PPG vượt ngưỡng, ACC ổn định");
  assert.equal(inferReason({ reason: null, probability: 0.58 }), "EDA, PPG dao động, ACC biến thiên");
  assert.equal(inferReason({ reason: null, probability: 0.4 }), "EDA, PPG, ACC biến thiên");
});

test("PredictionPanel displays countdown for CALIBRATING (60s) and NORMAL/ATTENTION (10s)", () => {
  const baseTelemetry = {
    device_id: "ESP-001", session_id: "S-1", timestamp_ms: 60000,
    firmware_version: "1.0", model_version: "wesad_lr_v1_folded", data_origin: "DEVICE",
    schema_version: "1.2", hr_bpm: 75, gsr: { raw: 1500, delta: 0 },
    movement: { score: 0.1 },
    signal_quality: { hr: { status: "good", score: 0.9 }, gsr: { status: "good", score: 0.9 }, motion: { status: "good", score: 0.9 } },
    prediction: { state: "CALIBRATING", probability: null }
  };

  // CALIBRATING with 1 sample -> (60s)
  const calibPoints1 = [{ time: 1, predictionState: "CALIBRATING", probability: null }];
  const htmlCalib1 = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: baseTelemetry, points: calibPoints1, live: true }));
  assert.ok(htmlCalib1.includes("Đang hiệu chuẩn"));
  assert.ok(htmlCalib1.includes("(60s)"));

  // CALIBRATING with 20 samples -> (41s)
  const calibPoints20 = Array.from({ length: 20 }, (_, i) => ({ time: i + 1, predictionState: "CALIBRATING", probability: null }));
  const htmlCalib20 = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: baseTelemetry, points: calibPoints20, live: true }));
  assert.ok(htmlCalib20.includes("(41s)"));

  // CALIBRATING with loose wrist (no_contact): main countdown stays at 51s, grace counts down | 5s, | 4s
  const looseTelemetry = {
    ...baseTelemetry,
    signal_quality: { ...baseTelemetry.signal_quality, hr: { status: "unavailable", score: 0, reason: "no_contact" } }
  };
  const loosePoints1 = [
    ...Array.from({ length: 10 }, (_, i) => ({ time: i + 1, predictionState: "CALIBRATING", probability: null })),
    { time: 11, predictionState: "CALIBRATING", probability: null, hrNoContact: true }
  ];
  const htmlLoose1 = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: looseTelemetry, points: loosePoints1, live: true }));
  assert.ok(htmlLoose1.includes("(51s | 5s)"));

  const loosePoints2 = [
    ...Array.from({ length: 10 }, (_, i) => ({ time: i + 1, predictionState: "CALIBRATING", probability: null })),
    { time: 11, predictionState: "CALIBRATING", probability: null, hrNoContact: true },
    { time: 12, predictionState: "CALIBRATING", probability: null, hrNoContact: true }
  ];
  const htmlLoose2 = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: looseTelemetry, points: loosePoints2, live: true }));
  assert.ok(htmlLoose2.includes("(51s | 4s)"));

  // NORMAL with 1 sample -> (10s)
  const normalTelemetry = { ...baseTelemetry, prediction: { state: "NORMAL", probability: 0.3 } };
  const normalPoints1 = [{ time: 61, predictionState: "NORMAL", probability: 0.3 }];
  const htmlNormal1 = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: normalTelemetry, points: normalPoints1, live: true }));
  assert.ok(htmlNormal1.includes("Bình thường"));
  assert.ok(htmlNormal1.includes("(10s)"));

  // NORMAL at 3rd second of 10s step -> (8s)
  const normalPoints3 = [
    { time: 60, predictionState: "CALIBRATING", probability: null },
    { time: 61, predictionState: "NORMAL", probability: 0.3 },
    { time: 62, predictionState: "NORMAL", probability: 0.3 },
    { time: 63, predictionState: "NORMAL", probability: 0.3 },
  ];
  const htmlNormal3 = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: normalTelemetry, points: normalPoints3, live: true }));
  assert.ok(htmlNormal3.includes("(8s)"));

  // NORMAL with loose wrist (no_contact): main 10s countdown pauses at (8s), 5s grace counts down | 5s, | 4s
  const looseNormalTelemetry = {
    ...normalTelemetry,
    signal_quality: { ...normalTelemetry.signal_quality, hr: { status: "unavailable", score: 0, reason: "no_contact" } }
  };
  const normalLoosePoints1 = [
    ...normalPoints3,
    { time: 64, predictionState: "NORMAL", probability: 0.3, hrNoContact: true, noContactSeconds: 1 }
  ];
  const htmlNormalLoose1 = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: looseNormalTelemetry, points: normalLoosePoints1, live: true }));
  assert.ok(htmlNormalLoose1.includes("Bình thường"));
  assert.ok(htmlNormalLoose1.includes("(8s | 5s)"));

  const normalLoosePoints2 = [
    ...normalPoints3,
    { time: 64, predictionState: "NORMAL", probability: 0.3, hrNoContact: true, noContactSeconds: 1 },
    { time: 65, predictionState: "NORMAL", probability: 0.3, hrNoContact: true, noContactSeconds: 2 }
  ];
  const htmlNormalLoose2 = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: looseNormalTelemetry, points: normalLoosePoints2, live: true }));
  assert.ok(htmlNormalLoose2.includes("(8s | 4s)"));

  // ATTENTION with loose wrist: shows "Cần theo dõi" with (8s | 5s)
  const attentionTelemetry = { ...baseTelemetry, prediction: { state: "ATTENTION", probability: 0.85 } };
  const looseAttentionTelemetry = {
    ...attentionTelemetry,
    signal_quality: { ...attentionTelemetry.signal_quality, hr: { status: "unavailable", score: 0, reason: "no_contact" } }
  };
  const attentionPoints = [
    { time: 60, predictionState: "CALIBRATING", probability: null },
    { time: 61, predictionState: "ATTENTION", probability: 0.85 },
    { time: 62, predictionState: "ATTENTION", probability: 0.85 },
    { time: 63, predictionState: "ATTENTION", probability: 0.85 },
    { time: 64, predictionState: "ATTENTION", probability: 0.85, hrNoContact: true, noContactSeconds: 1 }
  ];
  const htmlAttentionLoose = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: looseAttentionTelemetry, points: attentionPoints, live: true }));
  assert.ok(htmlAttentionLoose.includes("Cần theo dõi"));
  assert.ok(htmlAttentionLoose.includes("(8s | 5s)"));

  // Contact lost > 5s from NORMAL -> grace expired, resets to CALIBRATING (60s)
  const normalLoosePoints6 = [
    ...normalPoints3,
    ...Array.from({ length: 6 }, (_, i) => ({ time: 64 + i, predictionState: "NORMAL", probability: 0.3, hrNoContact: true, noContactSeconds: i + 1 }))
  ];
  const htmlNormalLooseExpired = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: looseNormalTelemetry, points: normalLoosePoints6, live: true }));
  assert.ok(htmlNormalLooseExpired.includes("Đang hiệu chuẩn"));
  assert.ok(htmlNormalLooseExpired.includes("(60s)"));
});

test("updateTelemetryStream preserves 5s grace countdown when ATTENTION drops to CALIBRATING regardless of HR reason", () => {
  const makeTel = (sec, state, prob, reason = "ok") => ({
    device_id: "ESP-001", session_id: "S-1", timestamp_ms: sec * 1000,
    firmware_version: "0.4.7-rr-average-tracker", model_version: "wesad_lr_v1_folded", data_origin: "DEVICE",
    schema_version: "1.2", hr_bpm: reason === "ok" ? 84 : null, gsr: { raw: 1500, delta: 0 },
    movement: { score: 0.1, acceleration: { x: 0, y: 9.8, z: 0 }, angular_velocity: { x: 0, y: 0, z: 0 } },
    signal_quality: {
      method: "engineering-v2", window_ms: 8000,
      hr: { status: reason === "ok" ? "good" : "unavailable", score: reason === "ok" ? 0.9 : 0, reason },
      gsr: { status: "good", score: 0.9, reason: "ok" },
      acceleration: { status: "good", score: 0.9, reason: "ok" },
      rotation: { status: "good", score: 0.9, reason: "ok" },
    },
    prediction: { state, probability: prob }
  });

  let stream = null;
  stream = updateTelemetryStream(stream, makeTel(60, "CALIBRATING", null), 60000);
  stream = updateTelemetryStream(stream, makeTel(61, "ATTENTION", 0.85), 61000);
  stream = updateTelemetryStream(stream, makeTel(62, "ATTENTION", 0.85), 62000);
  stream = updateTelemetryStream(stream, makeTel(63, "ATTENTION", 0.85), 63000);

  // Immediately after ATTENTION, firmware emits CALIBRATING with reason = "warming_up" (not "no_contact")
  for (let i = 0; i < 5; i++) {
    const reason = i === 0 ? "warming_up" : i === 1 ? "weak_signal" : "no_contact";
    stream = updateTelemetryStream(stream, makeTel(64 + i, "CALIBRATING", null, reason), (64 + i) * 1000);
    const html = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: stream.telemetry, points: stream.points, live: true }));
    assert.ok(html.includes("Cần theo dõi"), `second ${i + 1} should keep Cần theo dõi`);
    assert.ok(html.includes(`(8s | ${5 - i}s)`), `second ${i + 1} should show (8s | ${5 - i}s), got: ${html}`);
  }

  // At 6th second (> 5s grace), resets to CALIBRATING (60s)
  stream = updateTelemetryStream(stream, makeTel(69, "CALIBRATING", null, "warming_up"), 69000);
  const htmlExpired = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: stream.telemetry, points: stream.points, live: true }));
  assert.ok(htmlExpired.includes("Đang hiệu chuẩn"));
  assert.ok(htmlExpired.includes("(60s)"));
});

test("resetStreamAiWindow restarts 60s calibration without triggering 5s grace countdown and PredictionPanel renders Reset button", () => {
  const makeTel = (sec, state, prob) => ({
    device_id: "ESP-001", session_id: "S-1", timestamp_ms: sec * 1000,
    firmware_version: "0.4.7-rr-average-tracker", model_version: "wesad_lr_v1_folded", data_origin: "DEVICE",
    schema_version: "1.2", hr_bpm: 84, gsr: { raw: 1500, delta: 0 },
    movement: { score: 0.1, acceleration: { x: 0, y: 9.8, z: 0 }, angular_velocity: { x: 0, y: 0, z: 0 } },
    signal_quality: {
      method: "engineering-v2", window_ms: 8000,
      hr: { status: "good", score: 0.9, reason: "ok" },
      gsr: { status: "good", score: 0.9, reason: "ok" },
      acceleration: { status: "good", score: 0.9, reason: "ok" },
      rotation: { status: "good", score: 0.9, reason: "ok" },
    },
    prediction: { state, probability: prob }
  });

  let stream = null;
  stream = updateTelemetryStream(stream, makeTel(61, "ATTENTION", 0.85), 61000);
  stream = updateTelemetryStream(stream, makeTel(62, "ATTENTION", 0.85), 62000);

  // User clicks Reset dữ liệu AI
  stream = resetStreamAiWindow(stream);
  assert.equal(stream.telemetry.prediction.state, "CALIBRATING");
  assert.equal(stream.telemetry.prediction.probability, null);
  assert.equal(stream.points.length, 2); // keeps sensor curves
  const htmlResetImmediate = renderToStaticMarkup(React.createElement(PredictionPanel, {
    telemetry: stream.telemetry, points: stream.points, live: true, onResetAi: () => {},
  }));
  assert.ok(htmlResetImmediate.includes("Đang hiệu chuẩn"));
  assert.ok(htmlResetImmediate.includes("(60s)"));
  assert.ok(htmlResetImmediate.includes("Đo lại cửa sổ 60s"));
  assert.ok(!htmlResetImmediate.includes("disabled=\"\""));

  // One lingering in-flight pre-reset packet stays cleanly in CALIBRATING
  stream = updateTelemetryStream(stream, makeTel(63, "ATTENTION", 0.85), 63000);
  assert.equal(stream.telemetry.prediction.state, "CALIBRATING");

  // Next fresh CALIBRATING packets from ESP32 count down 60s -> 59s without 5s grace trap
  stream = updateTelemetryStream(stream, makeTel(64, "CALIBRATING", null), 64000);
  const htmlFresh1 = renderToStaticMarkup(React.createElement(PredictionPanel, {
    telemetry: stream.telemetry, points: stream.points, live: true, onResetAi: () => {},
  }));
  assert.ok(htmlFresh1.includes("Đang hiệu chuẩn"));
  assert.ok(htmlFresh1.includes("(60s)"));

  stream = updateTelemetryStream(stream, makeTel(65, "CALIBRATING", null), 65000);
  const htmlFresh2 = renderToStaticMarkup(React.createElement(PredictionPanel, {
    telemetry: stream.telemetry, points: stream.points, live: true, onResetAi: () => {},
  }));
  assert.ok(htmlFresh2.includes("Đang hiệu chuẩn"));
  assert.ok(htmlFresh2.includes("(59s)"));

  // Button is disabled when offline
  const htmlOffline = renderToStaticMarkup(React.createElement(PredictionPanel, {
    telemetry: stream.telemetry, points: stream.points, live: false, onResetAi: () => {},
  }));
  assert.ok(htmlOffline.includes("disabled"));
});

test("UNCERTAIN never morphs into CALIBRATING or triggers false 5s grace from older NORMAL points", () => {
  const makeTel = (sec, state, prob, reason = "ok") => ({
    device_id: "ESP-001", session_id: "S-1", timestamp_ms: sec * 1000,
    firmware_version: "0.4.7-rr-average-tracker", model_version: "wesad_lr_v1_folded", data_origin: "DEVICE",
    schema_version: "1.2", hr_bpm: reason === "ok" ? 76 : null, gsr: { raw: 2500, delta: 0 },
    movement: { score: 0.05, acceleration: { x: 0, y: 9.8, z: 0 }, angular_velocity: { x: 0, y: 0, z: 0 } },
    signal_quality: {
      method: "engineering-v2", window_ms: 8000,
      hr: { status: reason === "ok" ? "good" : "unavailable", score: reason === "ok" ? 0.9 : 0, reason },
      gsr: { status: "good", score: 0.9, reason: "ok" },
      acceleration: { status: "good", score: 0.9, reason: "ok" },
      rotation: { status: "good", score: 0.9, reason: "ok" },
    },
    prediction: { state, probability: prob },
  });

  // Old NORMAL packet in history followed by UNCERTAIN (device sitting on desk, not worn)
  let stream = null;
  stream = updateTelemetryStream(stream, makeTel(1, "NORMAL", 0.2, "no_contact"), 1000);
  for (let sec = 2; sec <= 12; sec++) {
    stream = updateTelemetryStream(stream, makeTel(sec, "UNCERTAIN", null, "no_contact"), sec * 1000);
    const html = renderToStaticMarkup(React.createElement(PredictionPanel, {
      telemetry: stream.telemetry, points: stream.points, live: true,
    }));
    assert.ok(html.includes("Chưa xác định"), `second ${sec} must display Chưa xác định, got: ${html}`);
    assert.ok(!html.includes("Đang hiệu chuẩn"), `second ${sec} must not morph UNCERTAIN to CALIBRATING`);
    assert.ok(!html.includes("(60s)"), `second ${sec} must not show 60s countdown during UNCERTAIN`);
  }

  // User finally puts strap on -> transitions cleanly to CALIBRATING (60s) without triggering 5s grace countdown
  stream = updateTelemetryStream(stream, makeTel(13, "CALIBRATING", null, "warming_up"), 13000);
  const htmlStart = renderToStaticMarkup(React.createElement(PredictionPanel, {
    telemetry: stream.telemetry, points: stream.points, live: true,
  }));
  assert.ok(htmlStart.includes("Đang hiệu chuẩn"));
  assert.ok(htmlStart.includes("(60s)"));
  assert.ok(!htmlStart.includes("|"), `fresh calibration after UNCERTAIN must not show grace countdown: ${htmlStart}`);
});

test("sidebar navigation retains monitoring, metadata and controls while reports use backend history", async () => {
  const { JSDOM } = await import("jsdom");
  const { createRoot } = await import("react-dom/client");
  const { act } = React;
  const dom = new JSDOM('<div id="root"></div>', { url: "http://localhost:5173/#devices" });
  const saved = new Map();
  for (const [key, value] of Object.entries({ window: dom.window, document: dom.window.document,
    HTMLElement: dom.window.HTMLElement, IS_REACT_ACT_ENVIRONMENT: true })) {
    saved.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { value, configurable: true, writable: true });
  }
  const fetchBefore = globalThis.fetch;
  let disconnected = 0, selected;
  const telemetry = { device_id: "ESP-001", session_id: "AUTO-abc123", timestamp_ms: 12000, data_origin: "DEVICE",
    schema_version: "1.0", firmware_version: "0.4.7-tracker", model_version: "none", hr_bpm: null,
    gsr: { raw: null, delta: null }, movement: { score: null }, signal_quality: { ppg: 0, gsr: 0, imu: 0 },
    prediction: { probability: null, state: "UNCERTAIN" } };
  globalThis[workspaceFixture] = { mounts: 0, unmounts: 0, snapshot: { telemetry, points: [],
    deviceIds: ["ESP-001", "ESP-002"], selectedDeviceId: "ESP-001", connectionStatus: "live",
    monitoring: true, connectionTimedOut: false, setSelectedDeviceId: value => { selected = value; },
    connectDevice() {}, disconnectDevice() { disconnected++; } } };
  globalThis.fetch = async url => {
    const page = Number(url.searchParams.get("page"));
    const items = Array.from({ length: 12 }, (_, i) => event(i + 1, i + 1, { record_count: 2 }))
      .slice((page - 1) * 10, page * 10);
    return { ok: true, status: 200, json: async () => ({ items, total: 12, page, page_size: 10 }) };
  };
  const container = dom.window.document.getElementById("root");
  const root = createRoot(container);
  try {
    await act(async () => root.render(React.createElement(Dashboard)));
    assert.equal(container.querySelectorAll(".sensor-panel").length, 4);
    assert.equal(container.querySelectorAll(".sidebar-brand img").length, 1);
    assert.equal(container.querySelectorAll(".sidebar-device-info dl > div").length, 3);
    assert.ok(container.querySelector(".sidebar-device-info .sidebar-footnote"));
    await act(async () => container.querySelector(".sidebar-toggle").click());
    assert.equal(container.querySelector(".workspace-shell").dataset.sidebarCollapsed, "true");
    assert.equal(container.querySelector(".sidebar-toggle").getAttribute("aria-expanded"), "false");
    assert.equal(container.querySelector(".sidebar-brand img").getAttribute("src"), "/brand/asd-ease-mark.svg");
    assert.equal(container.querySelectorAll(".sensor-panel").length, 4);
    assert.equal(globalThis[workspaceFixture].mounts, 1);
    assert.equal(globalThis[workspaceFixture].unmounts, 0);
    await act(async () => container.querySelector(".sidebar-toggle").click());
    assert.equal(container.querySelector(".workspace-shell").dataset.sidebarCollapsed, "false");
    assert.ok(container.querySelector(".header-session").textContent.includes("abc123"));
    await act(async () => {
      container.querySelector('a[href="#reports"]').click();
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    assert.equal(container.querySelectorAll(".sensor-panel").length, 0);
    assert.ok(container.querySelector(".ai-reports"));
    assert.ok(container.querySelector(".report-table-card").textContent.includes("Cần theo dõi"));
    assert.equal(container.querySelectorAll(".report-table-card tbody tr").length, 10);
    const pageButtons = () => [...container.querySelectorAll(".report-pagination button")];
    await act(async () => { pageButtons()[1].click(); await new Promise(resolve => setTimeout(resolve, 0)); });
    assert.equal(container.querySelectorAll(".report-table-card tbody tr").length, 2);
    assert.ok(container.querySelector(".report-pagination").textContent.includes("Trang 2 / 2"));
    assert.equal(pageButtons()[1].disabled, true);
    await act(async () => { pageButtons()[0].click(); await new Promise(resolve => setTimeout(resolve, 0)); });
    assert.equal(container.querySelectorAll(".report-table-card tbody tr").length, 10);
    assert.equal(globalThis[workspaceFixture].mounts, 1);
    assert.equal(globalThis[workspaceFixture].unmounts, 0);
    await act(async () => {
      container.querySelector('a[href="#devices"]').click();
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    assert.equal(container.querySelectorAll(".sensor-panel").length, 4);
    globalThis[workspaceFixture].snapshot.telemetry = { ...telemetry, model_version: "model-v1",
      prediction: { state: "ATTENTION", probability: .8 } };
    await act(async () => root.render(React.createElement(Dashboard)));
    assert.equal(container.querySelector(".prediction-alert-summary"), null);
    assert.equal(container.querySelector(".prediction-period").textContent, "—");
    await act(async () => container.querySelector(".prediction-details-button").click());
    assert.ok(container.querySelector(".report-history-card"));
    await act(async () => container.querySelector('a[href="#devices"]').click());
    const select = container.querySelector("select");
    await act(async () => { select.value = "ESP-002"; select.dispatchEvent(new dom.window.Event("change", { bubbles: true })); });
    assert.equal(selected, "ESP-002");
    await act(async () => container.querySelector(".device-connect-button").click());
    assert.equal(disconnected, 1);
    assert.equal(globalThis[workspaceFixture].mounts, 1);
  } finally {
    await act(async () => root.unmount());
    dom.window.close();
    globalThis.fetch = fetchBefore;
    delete globalThis[workspaceFixture];
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];
    }
  }
});

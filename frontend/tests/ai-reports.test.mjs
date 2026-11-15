import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let server, eventTime, listAiReportPage, AiReports, PredictionPanel, Dashboard;
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
  ({ eventTime, listAiReportPage } = await server.ssrLoadModule("/src/api/reports.ts"));
  ({ AiReports } = await server.ssrLoadModule("/src/pages/AiReports.tsx"));
  ({ PredictionPanel } = await server.ssrLoadModule("/src/components/PredictionPanel.tsx"));
  ({ Dashboard } = await server.ssrLoadModule("/src/pages/Dashboard.tsx"));
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
  assert.ok(report.includes("Lịch sử dự đoán AI"));
  assert.ok(report.includes("0 kết quả"));
  assert.ok(report.includes("Lý do"));
  assert.ok(!report.includes("Những thời điểm cần chú ý"));
  assert.ok(!report.includes("Cảnh báo nghiêm trọng"));
  const current = renderToStaticMarkup(React.createElement(PredictionPanel, { telemetry: null, live: false }));
  assert.ok(current.includes("Dự đoán AI"));
  assert.ok(!current.includes("Lịch sử"));
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
    assert.ok(container.querySelector(".report-table-card").textContent.includes("Cần chú ý"));
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

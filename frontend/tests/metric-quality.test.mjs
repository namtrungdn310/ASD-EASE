import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let server, parser, MetricQuality, ImuReadings, updateTelemetryStream;
const frame = () => ({
  schema_version: "1.2", device_id: "ESP32-001", session_id: null,
  timestamp_ms: 1000, data_origin: "DEVICE", hr_bpm: null,
  gsr: { raw: 1234, delta: null },
  movement: { score: null, acceleration: { x: 0, y: 0, z: 9.8 }, angular_velocity: { x: 1, y: 2, z: 3 } },
  signal_quality: {
    method: "engineering-v1", window_ms: 8000,
    hr: { score: 0, reason: "no_contact" }, gsr: { score: 1, reason: "ok" },
    acceleration: { score: .5, reason: "saturated" }, rotation: { score: null, reason: "calibrating" },
  },
  prediction: { probability: null, state: "UNCERTAIN" }, firmware_version: "quality-test", model_version: "none",
});
before(async () => {
  server = await createServer({ root: fileURLToPath(new URL("../", import.meta.url)),
    server: { middlewareMode: true, hmr: false }, appType: "custom" });
  parser = await server.ssrLoadModule("/src/utils/parseTelemetry.ts");
  ({ MetricQuality } = await server.ssrLoadModule("/src/components/MetricQuality.tsx"));
  ({ ImuReadings } = await server.ssrLoadModule("/src/components/ImuReadings.tsx"));
  ({ updateTelemetryStream } = await server.ssrLoadModule("/src/utils/telemetryStream.ts"));
});
after(async () => { await server?.close(); });

test("quality parser distinguishes zero, null and malformed scores", () => {
  assert.ok(parser.isTelemetry(frame()));
  for (const score of [-.1, 1.1, true, "0.8", NaN, Infinity, null]) {
    const value = frame(); value.signal_quality.hr.score = score;
    assert.equal(parser.isTelemetry(value), false);
  }
  for (const change of [{ method: "accuracy" }, { window_ms: 5000 }, { extra: true },
    { hr: { score: .9, reason: "stale" } }, { rotation: { score: null, reason: "ok" } },
    { gsr: { score: 1, reason: ["ok"] } }]) {
    const value = frame(); Object.assign(value.signal_quality, change);
    assert.equal(parser.isTelemetry(value), false);
  }
  const legacy = frame(); legacy.schema_version = "1.1";
  assert.equal(parser.isTelemetry(legacy), false);
  legacy.schema_version = 1.1;
  legacy.signal_quality = { ppg: .9, gsr: .9, imu: .9 };
  assert.equal(parser.isTelemetry(legacy), false);
});
test("card shows real zero and never shows old percentage while offline", () => {
  const render = props => renderToStaticMarkup(React.createElement(MetricQuality, props));
  assert.match(render({ reading: frame().signal_quality.hr, live: true }), /0%/);
  const unknown = render({ reading: frame().signal_quality.rotation, live: true });
  assert.doesNotMatch(unknown, /\d+%/);
  assert.match(unknown, /Đang hiệu chỉnh/);
  const offline = render({ reading: frame().signal_quality.gsr, live: false });
  assert.doesNotMatch(offline, /100%/);
  assert.match(offline, /Không có dữ liệu mới/);
  assert.match(offline, /— mẫu/);
});

test("acceleration and rotation use independent quality readings", () => {
  const markup = renderToStaticMarkup(React.createElement(ImuReadings, { telemetry: frame(), live: true }));
  assert.match(markup, /50%/);
  assert.match(markup, /Đang hiệu chỉnh/);
  assert.match(markup, /9\.80/);
  const stream = updateTelemetryStream(null, frame(), 1000);
  assert.equal(stream.points[0].az, 9.8);
  assert.equal(stream.points[0].gz, 3);
});

test("sample counts come from acquisition, not chart length or score", () => {
  const value = frame();
  value.signal_quality.hr.sample_count = 397;
  assert.ok(parser.isTelemetry(value));
  const render = live => renderToStaticMarkup(React.createElement(MetricQuality, { reading: value.signal_quality.hr, live }));
  assert.match(render(true), /397 mẫu/);
  assert.match(render(true), /0%/);
  assert.match(render(false), /— mẫu/);
  for (const count of [-1, true, "400", 1.5, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
    value.signal_quality.hr.sample_count = count;
    assert.equal(parser.isTelemetry(value), false);
  }
  value.signal_quality.hr.sample_count = 0;
  assert.ok(parser.isTelemetry(value));
  value.signal_quality.hr.sample_count = null;
  assert.ok(parser.isTelemetry(value));
});

test("quality parser accepts the explicit v2 method and preserves v1", () => {
  for(const method of ["engineering-v1","engineering-v2"]){
    const value=frame();value.signal_quality.method=method;assert.ok(parser.isTelemetry(value));
  }
  const invalid=frame();invalid.signal_quality.method="engineering-v3";
  assert.equal(parser.isTelemetry(invalid),false);
});

import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let server, createEmptyAccumulator, stepDatasetCapture, DataLabelModal;

before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL("../", import.meta.url)),
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
    logLevel: "silent",
  });
  ({ createEmptyAccumulator, stepDatasetCapture } = await server.ssrLoadModule("/src/hooks/useDatasetCapture.ts"));
  ({ DataLabelModal } = await server.ssrLoadModule("/src/components/DataLabelModal.tsx"));
});

after(async () => {
  await server?.close();
});

function makeTel(sec, state, reason = "ok") {
  return {
    device_id: "ESP32-001",
    session_id: "AUTO-1",
    timestamp_ms: sec * 1000,
    firmware_version: "0.4.7-rr-average-tracker",
    model_version: "wesad_lr_v1_folded",
    data_origin: "DEVICE",
    schema_version: "1.2",
    hr_bpm: reason === "ok" ? 80 : null,
    gsr: { raw: 1750, delta: null },
    movement: {
      score: 0.05,
      acceleration: { x: 0.1, y: 0.2, z: 9.8 },
      angular_velocity: { x: 0, y: 0, z: 0 },
    },
    signal_quality: {
      method: "engineering-v2",
      window_ms: 8000,
      hr: { status: reason === "ok" ? "good" : "unavailable", score: reason === "ok" ? 0.9 : 0, reason },
      gsr: { status: "good", score: 0.9, reason: "ok" },
      acceleration: { status: "good", score: 0.9, reason: "ok" },
      rotation: { status: "good", score: 0.9, reason: "ok" },
    },
    prediction: { state, probability: state === "NORMAL" ? 0.25 : state === "ATTENTION" ? 0.82 : null },
  };
}

test("stepDatasetCapture skips first 60s CALIBRATING and 5s no_contact tail, then emits capture on UNCERTAIN", () => {
  const acc = createEmptyAccumulator();

  for (let s = 1; s <= 60; s++) {
    assert.equal(stepDatasetCapture(acc, makeTel(s, "CALIBRATING"), true), null);
  }
  assert.equal(acc.samples.length, 0);

  for (let s = 61; s <= 75; s++) {
    assert.equal(stepDatasetCapture(acc, makeTel(s, "NORMAL"), true), null);
  }
  assert.equal(acc.samples.length, 15);

  for (let s = 76; s <= 80; s++) {
    assert.equal(stepDatasetCapture(acc, makeTel(s, "NORMAL", "no_contact"), true), null);
  }
  assert.equal(acc.samples.length, 15);

  const ready = stepDatasetCapture(acc, makeTel(81, "UNCERTAIN", "no_contact"), true);
  assert.ok(ready !== null);
  assert.equal(ready.deviceId, "ESP32-001");
  assert.equal(ready.samples.length, 15);
  assert.equal(ready.durationSeconds, 15);
  assert.equal(acc.samples.length, 0);
});

test("DataLabelModal renders duration, sample count and Stress/No stress dropdown", () => {
  const html = renderToStaticMarkup(
    React.createElement(DataLabelModal, {
      capture: {
        deviceId: "ESP32-001",
        sessionId: "AUTO-1",
        durationSeconds: 75,
        samples: Array.from({ length: 75 }, (_, i) => ({
          timestamp_ms: (61 + i) * 1000,
          hr_bpm: 82,
          gsr_raw: 1800,
          gsr_delta: null,
          ax: 0,
          ay: 0,
          az: 9.8,
        })),
      },
      onClose: () => {},
    }),
  );
  assert.ok(html.includes("Gán nhãn dữ liệu vừa thu"));
  assert.ok(html.includes("1 phút 15 giây"));
  assert.ok(html.includes("75 mẫu"));
  assert.ok(html.includes("Không stress (No stress)"));
  assert.ok(html.includes("Stress"));
  assert.ok(html.includes("Lưu dữ liệu"));
  assert.ok(html.includes("Bỏ qua"));
});

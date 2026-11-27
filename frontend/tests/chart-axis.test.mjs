import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { JSDOM } from "jsdom";
import { createServer } from "vite";

let server, axes, useChartAxis, MetricChart, ImuChart, chartFormat, chartWindow;
before(async () => {
  server = await createServer({ configFile: false, root: fileURLToPath(new URL("../", import.meta.url)),
    ssr: { noExternal: ["recharts"] },
    server: { middlewareMode: true, hmr: false }, appType: "custom",
    plugins: [{ name: "axis-chart-probe", enforce: "pre",
      resolveId(id) { if (id === "recharts") return "\0axis-chart-probe"; },
      load(id) {
        if (id !== "\0axis-chart-probe") return;
        return `import React from "react";
          export const YAxis = props => React.createElement("output", {"data-axis": JSON.stringify({domain: props.domain, ticks: props.ticks})});
          export const Line = props => React.createElement("i", {"data-series": props.dataKey});
          export const LineChart = props => React.createElement("div", {"data-sync": props.syncId}, props.children);
          export const ResponsiveContainer = props => React.createElement("div", {"data-chart-height": props.height}, props.children);
          export const CartesianGrid = () => null;
          export const Tooltip = () => null;
          export const XAxis = props => React.createElement("output", {"data-time-axis": JSON.stringify({domain: props.domain, hide: props.hide ?? false})});
          export const Legend = () => null;`;
      } }],
  });
  axes = await server.ssrLoadModule("/src/utils/chartAxis.ts");
  chartFormat = await server.ssrLoadModule("/src/utils/chartFormat.ts");
  chartWindow = await server.ssrLoadModule("/src/utils/chartWindow.ts");
  ({ useChartAxis } = await server.ssrLoadModule("/src/hooks/useChartAxis.ts"));
  ({ MetricChart } = await server.ssrLoadModule("/src/components/MetricChart.tsx"));
  ({ ImuChart } = await server.ssrLoadModule("/src/components/ImuChart.tsx"));
});
after(async () => { await server?.close(); });
const point = (time, patch = {}) => ({ time, hr: null, gsr: null, movement: null, ax: null,
  ay: null, az: null, gx: null, gy: null, gz: null, probability: null, ...patch });
const step = (state, kind, data) => axes.advanceAxis(state, kind, axes.observeAxis(kind, data));

test("shared 60-second domain and evenly spaced time ticks ignore arrival density", () => {
  const data = [point(40), point(61), point(99.25), point(100)];
  assert.deepEqual(chartFormat.chartTimeDomain(data), [40, 100]);
  assert.deepEqual(chartFormat.chartTimeTicks(data), [40, 50, 60, 70, 80, 90, 100]);
  assert.deepEqual(chartFormat.chartTimeDomain([point(1)]), [0, 60]);
  assert.deepEqual(chartFormat.chartTimeTicks([]), [0, 10, 20, 30, 40, 50, 60]);
});
test("drawing inserts null breaks after missing packets without mutating raw history or forecast", () => {
  const data = [point(1, { hr: 70, hrForecast: null }), point(2, { hr: 71, hrForecast: null }),
    point(8, { hr: 75, hrForecast: 74 })];
  const saved = structuredClone(data);
  const plot = chartWindow.withChartGaps(data);
  assert.equal(plot.length, 4);
  assert.equal(plot[2].time, 5);
  assert.equal(plot[2].hr, null);
  assert.equal(plot[2].hrForecast, null);
  assert.equal(plot[3], data[2]);
  assert.deepEqual(data, saved);
  assert.equal(chartWindow.withChartGaps([point(0), point(1), point(3)]).length, 4);
  assert.equal(chartWindow.withChartGaps([point(0), point(1.1)]).length, 2);
});

test("focused ranges retain minimum spans without a broad fixed HR or gyro floor", () => {
  assert.deepEqual(step(null, "hr", [point(1, { hr: 75 })]).domain, [60, 90]);
  assert.deepEqual(step(null, "az", [point(1, { az: -9.9 })]).domain, [-10, -9.8]);
  assert.deepEqual(step(null, "angular_velocity", [point(1, { gx: -.04, gy: .07, gz: -.02 })]).domain, [-.2, .2]);
  assert.deepEqual(step(null, "probability", [point(1, { probability: .9 })]).domain, [0, 1]);
});
test("all real and forecast values remain visible, with no input mutation", () => {
  const data = [point(1, { hr: 20 }), point(2, { hr: 240, hrForecast: 244 })];
  const original = JSON.stringify(data);
  const hr = step(null, "hr", data).domain;
  assert.ok(hr[0] <= 20 && hr[1] >= 244);
  const gyro = step(null, "angular_velocity", [point(1, { gx: -249, gy: .02, gz: 190 })]).domain;
  assert.equal(gyro[0], -gyro[1]);
  assert.ok(gyro[0] <= -249 && gyro[1] >= 190);
  const accel = step(null, "ax", [point(1, { ax: -19.6 }), point(2, { ax: 15 })]).domain;
  assert.ok(accel[0] <= -19.6 && accel[1] >= 15);
  assert.equal(JSON.stringify(data), original);
});
test("GSR keeps at least 100 ADC and respects both rail ends", () => {
  for (const values of [[2484, 2488], [0, 5], [4090, 4095], [0, 4095]]) {
    const domain = step(null, "gsr", values.map((gsr, i) => point(i, { gsr }))).domain;
    assert.ok(domain[0] >= 0 && domain[1] <= 4095);
    assert.ok(domain[0] <= Math.min(...values) && domain[1] >= Math.max(...values));
    assert.ok(domain[1] - domain[0] >= 100);
    assert.ok(axes.axisTicks(domain, true).every(Number.isInteger));
  }
});
test("spike expands immediately then shrinks after 15 seconds of fresh stable data", () => {
  let state = step(null, "angular_velocity", [point(0, { gx: 0 })]);
  state = step(state, "angular_velocity", [point(1, { gx: 40 })]);
  assert.ok(state.domain[1] >= 40);
  const large = state.domain;
  for (let t = 2; t < 17; t++) {
    state = step(state, "angular_velocity", [point(t, { gx: .02 })]);
    assert.deepEqual(state.domain, large);
  }
  state = step(state, "angular_velocity", [point(17, { gx: .03 })]);
  assert.deepEqual(state.domain, [-.2, .2]);
});
test("visible spike, null tail, duplicate renders and gaps cannot complete contraction", () => {
  let state = step(null, "angular_velocity", [point(0, { gx: 40 })]);
  for (let t = 1; t <= 20; t++) state = step(state, "angular_velocity", [point(0, { gx: 40 }), point(t, { gx: 0 })]);
  assert.ok(state.domain[1] >= 40);
  state = step(state, "angular_velocity", [point(21, { gx: 0 })]);
  for (let i = 0; i < 100; i++) state = step(state, "angular_velocity", [point(21, { gx: 0 })]);
  assert.ok(state.domain[1] >= 40);
  state = step(state, "angular_velocity", [point(21, { gx: 0 }), point(40)]);
  assert.equal(state.pending, null);
  state = step(state, "angular_velocity", [point(60, { gx: 0 })]);
  assert.ok(state.domain[1] >= 40);
});
test("new outlier cancels pending contraction and clock reset forgets the old scale", () => {
  let state = step(null, "hr", [point(20, { hr: 200 })]);
  state = step(state, "hr", [point(21, { hr: 80 })]);
  state = step(state, "hr", [point(22, { hr: 235 })]);
  assert.ok(state.domain[1] >= 235);
  assert.equal(state.pending, null);
  state = step(state, "hr", [point(0, { hr: 80 })]);
  assert.deepEqual(state.domain, [65, 95]);
});
test("invalid and absent samples do not become zero or corrupt bounds", () => {
  const observation = axes.observeAxis("hr", [point(1, { hr: NaN }), point(2, { hr: Infinity }), point(3)]);
  assert.equal(observation.min, null);
  assert.equal(observation.sampleTime, null);
  assert.deepEqual(step(null, "hr", []).domain, [40, 160]);
  assert.deepEqual(step(null, "gsr", []).domain, [0, 4095]);
});

test("HR and GSR contraction covers the stable interval after a level change", () => {
  let hr = step(null, "hr", [point(0, { hr: 161 })]);
  assert.deepEqual(hr.domain, [145, 180]);
  for (let t = 1; t <= 17; t++) hr = step(hr, "hr", [point(t, { hr: 80 })]);
  assert.deepEqual(hr.domain, [65, 95]);
  let gsr = step(null, "gsr", [point(0, { gsr: 0 }), point(1, { gsr: 4095 })]);
  for (let t = 2; t <= 17; t++) gsr = step(gsr, "gsr", [point(t, { gsr: 2400 + t * 3 })]);
  assert.ok(gsr.domain[1] - gsr.domain[0] < 4095);
  assert.ok(gsr.domain[1] - gsr.domain[0] >= 100);
  assert.ok(gsr.domain[0] <= 2406 && gsr.domain[1] >= 2451);
});

test("first sample immediately replaces the empty fallback scale", () => {
  const empty = step(null, "gsr", [point(1)]);
  const measured = step(empty, "gsr", [point(2, { gsr: 2485 })]);
  assert.ok(measured.domain[1] - measured.domain[0] < 200);
  assert.ok(measured.domain[0] <= 2485 && measured.domain[1] >= 2485);
  const a = step(null, "ax", [point(1, { ax: -1.02, ay: .93, az: -9.99 })]).domain;
  const z = step(null, "az", [point(1, { ax: -1.02, ay: .93, az: -9.99 })]).domain;
  assert.ok(a[1] - a[0] < .3 && z[1] - z[0] < .3);
  assert.ok(a[0] > -2 && z[1] < -9);
});

test("real hook and chart bindings survive StrictMode, duplicate arrays and stream switch", async () => {
  const dom = new JSDOM('<div id="root"></div>');
  const saved = new Map();
  for (const [key, value] of Object.entries({ window: dom.window, document: dom.window.document,
    HTMLElement: dom.window.HTMLElement, IS_REACT_ACT_ENVIRONMENT: true })) {
    saved.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { value, configurable: true, writable: true });
  }
  const container = dom.window.document.getElementById("root"), root = createRoot(container);
  function Probe({ data }) {
    return React.createElement("output", { "data-hook": JSON.stringify(useChartAxis("hr", data)) });
  }
  const render = async (data, key = "device-a") => {
    await act(async () => root.render(React.createElement(React.StrictMode, null,
      React.createElement(Probe, { data, key }),
      React.createElement(MetricChart, { key: key + "-hr", title: "HR", data, dataKey: "hr", unit: "bpm", color: "blue",
        forecast: { dataKey: "hrForecast", name: "Nhịp duy trì", color: "orange" } }),
      React.createElement(ImuChart, { key: key + "-imu", data, kind: "angular_velocity" }))));
  };
  try {
    await render([point(0, { hr: 200, gx: -.04 })]);
    const initial = JSON.parse(container.querySelector('[data-hook]').dataset.hook);
    assert.ok(initial[1] >= 200);
    for (let t = 1; t <= 15; t++) {
      await render([point(t, { hr: 80, gx: .03 })]);
      // Parent rerender có thể tạo mảng mới mà không có gói mới.
      await render([point(t, { hr: 80, gx: .03 })]);
      const current = JSON.parse(container.querySelector('[data-hook]').dataset.hook);
      assert.ok(current[1] >= 200 && current[0] <= 80);
    }
    await render([point(16, { hr: 80, gx: .03 })]);
    await render([point(17, { hr: 80, gx: .03 })]);
    assert.deepEqual(JSON.parse(container.querySelector('[data-hook]').dataset.hook), [65, 95]);
    const bound = [...container.querySelectorAll('[data-axis]')].map(el => JSON.parse(el.dataset.axis).domain);
    assert.deepEqual(bound, [[65, 95], [-.2, .2]]);
    await render([point(18, { hr: 240, gx: 60 })]);
    assert.ok(JSON.parse(container.querySelector('[data-axis]').dataset.axis).domain[1] >= 240);
    await render([point(18, { hr: 80, gx: 0 })], "device-b");
    assert.deepEqual(JSON.parse(container.querySelector('[data-hook]').dataset.hook), [65, 95]);
    await render([point(19, { hrForecast: 239, gx: 0 })], "device-b");
    assert.ok(JSON.parse(container.querySelector('[data-axis]').dataset.axis).domain[1] >= 239);
    assert.ok(container.querySelector('[data-series="hrForecast"]'));
    const accelerationData = [point(20, { ax: -1.02, ay: .93, az: -9.99 }),
      point(21, { ax: -1.01, ay: .95, az: -9.98 })];
    const original = JSON.stringify(accelerationData);
    await act(async () => root.render(React.createElement(ImuChart, { data: accelerationData, kind: "acceleration", embedded: true })));
    const strips = [...container.querySelectorAll('.imu-strip')];
    assert.equal(strips.length, 3);
    assert.deepEqual(strips.map(el => el.querySelector('.imu-strip-plot').style.height), ['56px', '56px', '92px']);
    assert.deepEqual(strips.map(el => el.querySelector('[data-chart-height]').dataset.chartHeight), ['56', '56', '92']);
    assert.equal(container.querySelectorAll('.imu-strip .plot-area').length, 0);
    assert.deepEqual(strips.map(el => el.querySelector('[data-series]').dataset.series), ['ax', 'ay', 'az']);
    const bounds = strips.map(el => JSON.parse(el.querySelector('[data-axis]').dataset.axis).domain);
    assert.ok(bounds.every(d => d[1] - d[0] < .4));
    assert.ok(bounds[0][0] <= -1.02 && bounds[1][1] >= .95 && bounds[2][0] <= -9.99);
    const times = strips.map(el => JSON.parse(el.querySelector('[data-time-axis]').dataset.timeAxis));
    assert.deepEqual(times.map(t => t.domain), [[0,60], [0,60], [0,60]]);
    assert.deepEqual(times.map(t => t.hide), [true,true,false]);
    assert.equal(new Set([...container.querySelectorAll('[data-sync]')].map(el => el.dataset.sync)).size, 1);
    assert.equal(JSON.stringify(accelerationData), original);
    await act(async () => root.render(React.createElement(ImuChart, { data: [point(22, { ax: 1, az: -9.9 })], kind: "acceleration", embedded: true })));
    assert.equal(container.querySelectorAll('.imu-strip-empty').length, 1);
    assert.ok(container.querySelectorAll('.imu-strip')[1].textContent.includes('Chưa có mẫu'));
  } finally {
    await act(async () => root.unmount()); dom.window.close();
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];
    }
  }
});

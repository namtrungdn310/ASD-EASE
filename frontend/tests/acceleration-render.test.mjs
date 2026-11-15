import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { JSDOM, VirtualConsole } from "jsdom";
import { createServer } from "vite";

// Recharts thật, kích thước DOM giả để tái hiện việc parent bị đo thành200px.
// Không thay cho kiểm tra CSS/pixel trên browser.
test("actual Recharts SVG fits three strips into the measured 200px container", async () => {
  const browserErrors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', error => browserErrors.push(error));
  const dom = new JSDOM('<div id="root"></div>', { pretendToBeVisual: true, virtualConsole });
  let measuredWidth = 480;
  const observers = new Set();
  dom.window.HTMLElement.prototype.getBoundingClientRect = () => ({
    width: measuredWidth, height: 200, top: 0, left: 0, right: measuredWidth, bottom: 200, x: 0, y: 0, toJSON() {},
  });
  class Observer {
    constructor(callback) { this.callback = callback; }
    observe() { observers.add(this); this.callback([{ contentRect: { width: measuredWidth, height: 200 } }]); }
    unobserve() {}
    disconnect() { observers.delete(this); }
  }
  const saved = new Map();
  for (const [key, value] of Object.entries({ window: dom.window, document: dom.window.document,
    navigator: dom.window.navigator, HTMLElement: dom.window.HTMLElement, ResizeObserver: Observer,
    requestAnimationFrame: dom.window.requestAnimationFrame.bind(dom.window),
    cancelAnimationFrame: dom.window.cancelAnimationFrame.bind(dom.window),
    IS_REACT_ACT_ENVIRONMENT: true })) {
    saved.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { value, configurable: true, writable: true });
  }
  let server, root;
  try {
    server = await createServer({ configFile: false, root: fileURLToPath(new URL("../", import.meta.url)),
      server: { middlewareMode: true, hmr: false }, appType: "custom" });
    const { ImuChart } = await server.ssrLoadModule("/src/components/ImuChart.tsx");
    const { MetricChart } = await server.ssrLoadModule("/src/components/MetricChart.tsx");
    const data = Array.from({ length: 20 }, (_, i) => ({ time: i, hr: null, gsr: null, movement: null,
      ax: -1.02 + Math.sin(i) * .01, ay: .93 + Math.sin(i + 1) * .01,
      az: -9.99 + Math.sin(i + 2) * .01, gx: 0, gy: 0, gz: 0, probability: null }));
    const container = dom.window.document.getElementById("root");
    root = createRoot(container);
    await act(async () => root.render(React.createElement(ImuChart, { data, kind: "acceleration", embedded: true })));
    const strips = [...container.querySelectorAll('.imu-strip')];
    assert.equal(strips.length, 3);
    const expectedHeights = [50, 50, 88];
    for (const [index, strip] of strips.entries()) {
      const svg = strip.querySelector('svg.recharts-surface');
      assert.ok(svg, `strip ${index} must draw actual SVG`);
      assert.equal(Number(svg.getAttribute('height')), expectedHeights[index]);
      const yLabels = [...strip.querySelectorAll('.recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value')];
      assert.equal(yLabels.length, 1, `strip ${index} must show only its middle Y tick`);
      assert.equal(strip.querySelectorAll('.recharts-cartesian-grid-horizontal line').length, 1,
        'each acceleration strip uses one guide line, not a separate full grid');
      if (index === 2) {
        const timeLabel = strip.querySelector('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value');
        assert.ok(timeLabel);
        const lowestY = Math.max(...yLabels.map(label => Number(label.getAttribute('y'))));
        assert.ok(Number(timeLabel.getAttribute('y')) - lowestY >= 20, 'time label too close to bottom Y label');
      }
      const curve = strip.querySelector('path.recharts-line-curve');
      assert.ok(curve, `strip ${index} must draw its own real line`);
      const coordinates = [...curve.getAttribute('d').matchAll(/[ML](-?[\d.]+),(-?[\d.]+)/g)];
      assert.ok(coordinates.length >= 10);
      assert.ok(coordinates.every(([, , y]) => Number(y) >= 0 && Number(y) <= expectedHeights[index]),
        `strip ${index} curve escaped its SVG height`);
    }
    assert.equal(container.querySelectorAll('.imu-strips .recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value').length, 3,
      'the entire acceleration panel must show exactly three Y values');
    const timeLabels = () => [...container.querySelectorAll('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value')].map(t => t.textContent);
    assert.deepEqual(timeLabels(), ['00:00', '00:15', '00:30', '00:45', '01:00']);
    const resize = async width => {
      measuredWidth = width;
      await act(async () => {
        for (const observer of observers) observer.callback([{ contentRect: { width, height: 200 } }]);
      });
    };
    await resize(320);
    assert.deepEqual(timeLabels(), ['00:00', '00:15', '00:30', '00:45', '01:00']);
    await resize(480);
    const measured = data.map(point => ({ ...point, hr: 75, gsr: 1800 }));
    await act(async () => root.render(React.createElement(React.Fragment, null,
      React.createElement('div', { 'data-normal-chart': 'hr' }, React.createElement(MetricChart,
        { title: 'HR', data: measured, dataKey: 'hr', color: 'blue', unit: 'bpm' })),
      React.createElement('div', { 'data-normal-chart': 'gsr' }, React.createElement(MetricChart,
        { title: 'GSR', data: measured, dataKey: 'gsr', color: 'green', unit: 'ADC' })),
      React.createElement('div', { 'data-normal-chart': 'gyro' }, React.createElement(ImuChart,
        { data: measured, kind: 'angular_velocity', embedded: true }))
    )));
    for (const chart of container.querySelectorAll('[data-normal-chart]')) {
      const ticks = [...chart.querySelectorAll('.recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value')];
      assert.equal(ticks.length, 3);
      const firstTime = chart.querySelector('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value');
      assert.ok(firstTime);
      const bottomTick = Math.max(...ticks.map(tick => Number(tick.getAttribute('y'))));
      assert.ok(Number(firstTime.getAttribute('y')) - bottomTick >= 20);
      assert.deepEqual([...chart.querySelectorAll('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value')].map(t => t.textContent),
        ['00:00', '00:15', '00:30', '00:45', '01:00']);
    }
    await resize(320);
    for (const chart of container.querySelectorAll('[data-normal-chart]')) {
      assert.deepEqual([...chart.querySelectorAll('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value')].map(t => t.textContent),
        ['00:00', '00:15', '00:30', '00:45', '01:00']);
    }
    assert.deepEqual(browserErrors, []);
  } finally {
    if (root) await act(async () => root.unmount());
    await server?.close();
    // Chờ middleware Recharts dọn công việc frame trước khi tháo môi trường DOM.
    await act(async () => { await new Promise(resolve => dom.window.requestAnimationFrame(() => dom.window.requestAnimationFrame(resolve))); });
    dom.window.close();
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];
    }
  }
});

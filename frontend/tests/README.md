# Frontend regression checks

Run from `frontend` with Node 22 and installed dependencies:

```powershell
npm test
npm run build
```

`live-telemetry.test.mjs` uses Node's test runner and Vite's SSR loader to
execute the real TypeScript helpers and React components without adding
dependencies. Only the Dashboard network hook is substituted with a controlled
fixture. Tests run serially because they share that fixture.

Coverage includes four connection-state views, empty data, old prediction
suppression, synthetic provenance, nullable/zero measurements, selector props and
callback, chart data forwarding, identifier escaping, payload validation,
immutable 60-point buffers, stream resets and freshness boundaries. The frontend
CI job runs this suite before the production build.

These tests do **not** exercise real hook state/effect scheduling, DOM-dispatched
selection events, WebSocket reconnection, CSS layout, chart drawing, screen-reader
announcements or the backend/simulator path. Real React hook lifecycle tests and
browser/simulator verification are still required before completing integration
branch 02; see `docs/integration/02-frontend-live-connection-status.md`.

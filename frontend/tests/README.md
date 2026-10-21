# Frontend regression checks

Run from `frontend` with Node 22 and installed dependencies:

```powershell
npm test
npm run build
```

`live-telemetry.test.mjs` uses Node's test runner and Vite's SSR loader to
execute real TypeScript helpers and React components. Only this file's Dashboard
network hook is substituted with a controlled fixture. Its tests run serially
because they share that fixture.

Coverage includes four connection-state views, empty data, old prediction
suppression, synthetic provenance, nullable/zero measurements, selector props and
callback, chart data forwarding, identifier escaping, payload validation,
immutable 60-point buffers, stream resets and freshness boundaries. The frontend
CI job runs this suite before the production build.

`use-live-telemetry.test.mjs` mounts the actual hook with React DOM and jsdom,
including StrictMode effect replay, state updates, timeout/duplicate behavior,
constructor/error retries, socket callback isolation, device selection, session
resets, nullable data and unmount cleanup. WebSocket and receive clock/timers are
controlled doubles; the hook and React lifecycle are not mocked. Its Dashboard
test dispatches a DOM change event and verifies live -> stale -> disconnected ->
waiting -> live. Only the expected Recharts zero-size warnings are counted rather
than printed because jsdom has no layout engine; no geometry/pixel claims follow.

Current total: 26 tests. jsdom is a development-only dependency.

For the independent real HTTP/WebSocket transport test, install both Python
requirements sets (backend and ai, including uvicorn's standard extras), then run
from the repository root:

```powershell
.\.venv\Scripts\python.exe .github/scripts/check-mock-transport.py
```

It starts a temporary backend on a free loopback port with an isolated SQLite DB,
replays three simulator scenarios, compares all 18 received messages to their
source payloads, checks invalid payload rejection and reconnects a subscriber.
It stops its own backend afterward and does not modify the normal app DB.

These layers do **not** verify a real browser, CSS layout, chart drawing,
screen-reader announcements or an uninterrupted simulator-to-browser path.
Visual verification is still required before completing integration branch 02;
see `docs/integration/02-frontend-live-connection-status.md`.

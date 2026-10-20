# Branch 02 — Verification evidence

Date: 2026-10-20 (Asia/Saigon). Branch: `fix/frontend-live-connection-status`.
Core source was typed by Trung; this verification step changes tests, dependency
metadata and documentation only. No merge into dev/main is authorized here.

Branch changes: runtime telemetry validation, per-device/session/origin chart
history (60 points), separate backend/data freshness states, reconnect cleanup,
device selector, explicit old-data warnings and retained synthetic provenance.

## Verified

| Check | Command / evidence | Result |
|---|---|---|
| Frontend regression + real React lifecycle | `cd frontend; npm test` | 26/26 tests PASS |
| TypeScript and production build | `cd frontend; npm run build` | PASS; bundle >500 kB warning remains |
| Production dependency audit | `cd frontend; npm audit --omit=dev` | 0 vulnerabilities |
| Backend regression | `.venv/Scripts/python.exe -m pytest -q` from backend | 13 PASS; dependency deprecation warning |
| AI regression | `.venv/Scripts/python.exe -m pytest -q` from ai | 15 PASS; dependency deprecation warnings |
| Simulator HTTP -> real backend -> WebSocket | `.venv/Scripts/python.exe .github/scripts/check-mock-transport.py` | PASS, 18/18 exact payload matches across NORMAL_REST, POOR_SIGNAL and DISCONNECT_RECONNECT |
| Transport resilience | Same isolated transport script | HTTP 422 invalid payload not broadcast; 2-second send pause preserved acquisition timestamps; reconnected subscriber received new payload |
| Compose configuration | `docker compose config --quiet` | PASS |
| Shared firmware headers | `.venv/Scripts/python.exe .github/scripts/check-firmware-headers.py` | All four header combinations PASS; no hardware verification |
| Current Docker stack | `docker compose up -d --build backend frontend` | Both images built and containers started; backend healthy |
| Local serving | HTTP GET localhost:8000/api/v1/health and localhost:5173 | Both HTTP 200; not visual evidence |

The transport script uses a temporary database and port, not the normal app DB.
Its two-second pause does not prove the default five-second stale timeout;
stale timing is tested separately with controlled time in the React suite.

## Test boundaries

- Server rendering: real components/helpers, mock hook for controlled view states.
- React lifecycle: real React DOM/hooks/StrictMode in jsdom; fake WebSocket, clock
  and timers. Includes a real DOM selection event and reconnect view transitions.
- Chart history forwarding and 60-point buffering are verified. Pixel rendering,
  CSS responsiveness and layout are not verified by jsdom. Its expected zero-size
  chart warnings are counted in the test rather than treated as browser evidence.
- Transport: real simulator replay, HTTP, FastAPI validation and live WebSocket;
  no browser is involved. This is not a single simulator-to-browser E2E run.

## Open blocker — visual acceptance

`BLOCKED_BROWSER`: browser runtime initialization succeeded but URL selection
returned `No browser is available`; supported discovery returned `[]`. The
browser skill's troubleshooting flow was followed; no separate browser-control
tool or source-code workaround was used to claim visual verification.

Phase 02 remains IN_PROGRESS. Do not mark this branch DONE or ready for merge
until browser evidence is reviewed. No hardware claim is made.

## Manual browser acceptance to unblock

1. Start the current build with `docker compose up -d --build backend frontend`.
2. Open `http://localhost:5173`, hard-refresh, and verify backend online/waiting
   before replay. Historical data is not automatically fetched into a new page.
3. From the repository root, replay synthetic telemetry:

   ```powershell
   $env:PYTHONPATH = (Resolve-Path .\ai).Path
   .\.venv\Scripts\python.exe -m simulator.mock_device --scenario attention_mock --duration 15
   ```

4. During replay, record an image with live status, `SYNTHETIC DATA`, SIM-001,
   session, current measurements and visible chart traces. This is engineering
   synthetic data, not clinical/research evidence.
5. Leave the page open after replay exits. After at least six seconds, record
   stale status, old-data warning, retained chart/metrics, and unavailable current
   prediction/quality. Synthetic provenance must remain visible.
6. Replay `poor_signal` and check UNCERTAIN/null probability without a fake 0%.
7. With the page open, stop only the backend (`docker compose stop backend`),
   record disconnected state, then start it (`docker compose start backend`).
   Confirm waiting until a new sample arrives, then live after replay restarts.
8. Check the selector with two device IDs, keyboard access, 375px width and
   desktop width; capture any overflow/errors. Two-device logic has automated DOM
   coverage, but this does not replace visual inspection.
9. Attach screenshots and browser/device details, then tick the visual checklist
   in the branch plan. Do not invent PASS from build or HTTP 200 alone.

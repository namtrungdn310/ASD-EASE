# Local configuration and development setup

## Configuration ownership

- `.env.example` is a tracked template with development defaults, not a working secret file.
- Backend settings in `backend/app/core/config.py` load `.env` relative to the process working directory. Run native backend commands from `backend/`.
- Native Vite reads configuration from the frontend project directory. Use `frontend/.env.local` for local overrides.
- `VITE_*` values are public browser configuration. Do not put passwords, tokens or Wi-Fi credentials in them.
- `.env`, `.env.local` and other `.env.*` files are ignored; `.env.example` remains tracked.

## Native backend

From the repository root, copy the template only if you do not already have a local backend configuration:

```powershell
Copy-Item -LiteralPath .env.example -Destination backend/.env
```

The template contains backend settings plus Vite examples. `Settings` ignores extra keys; the Vite values in this backend file do not configure the frontend.

Run the receiver from `backend/` so relative storage and SQLite paths resolve there:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Pop-Location
```

`DATABASE_URL`, `RAW_STORAGE_DIR` and `CORS_ORIGINS` are the settings currently supported by this template. Host/port are Uvicorn command arguments, not fields in the current settings model.

## Native frontend

Create a local `frontend/.env.local` with these public values if overrides are needed:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/api/v1/ws/live
```

Then run from the repository root:

```powershell
npm --prefix frontend run dev
```

Vite reads environment values at startup/build. Restart the development server after editing them, or rebuild a production bundle. A static frontend container does not pick up new browser configuration simply by changing runtime environment variables.

## Docker Compose

```powershell
docker compose --profile ai config --quiet
docker compose up -d --build backend frontend
```

`compose.yaml` explicitly sets backend container storage paths and frontend `build.args`. Placing values in root `.env` does not override constants that are not interpolated in Compose. To change those settings, update the appropriate Compose configuration and rebuild the frontend when its Vite arguments change. Keep any actual credential in an ignored local file.

## Firmware and LAN

- `ai/edge_firmware/platformio.ini` currently uses environment `esp32s3_supermini`, firmware `0.2.0`, a generic `esp32-s3-devkitc-1` board definition and a configured 4 MB flash size. Those are build settings, not measured hardware evidence.
- Build from the repository root: `.\.venv\Scripts\pio.exe run -d ai/edge_firmware`.
- Local firmware credentials belong in `ai/edge_firmware/include/network_config.h`, which is ignored. The example header is tracked. The networking client is planned work and is not enabled just by creating this file.
- An ESP32 must address the receiver using the laptop LAN IP and port `8000`; `localhost` on the ESP32 refers to the ESP32 itself.
- If a browser runs on a different LAN computer, its localhost is also not the receiver laptop. Frontend API/WS URLs and backend CORS origins must match that setup.

## IDE-generated files

`ai/edge_firmware/.vscode/` and `compile_commands.json` are local generated files. They are intentionally untracked so paths such as another developer's home/toolchain directory cannot become shared configuration. Untracking them preserves existing files on disk; regenerate local configuration through PlatformIO as needed.

See [hardware profile](HARDWARE_PROFILE.md) for wiring/configuration evidence still required and [integration progress](integration/PROGRESS.md) for the current branch work.

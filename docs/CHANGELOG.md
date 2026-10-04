# Changelog

## Unreleased

### Added

- Initial three-module repository scaffold, documentation system and 25 phase plans.
- Git repository initialized with `main` as the integration branch and generated/private artifacts ignored.
- Two-person GitHub workflow, PR template, CODEOWNERS review request and CI checks for protected `dev`/`main` branches.
- FastAPI/SQLite/raw-file receiver with telemetry, raw-batch and WebSocket paths.
- React telemetry dashboard with visible synthetic-data provenance.
- Reproducible multimodal synthetic generator, manifest, validation and replay simulator.
- ESP32-S3 PlatformIO skeleton and hardware profiler with unverified GPIO configuration.
- Docker Compose stack and optional AI profile.
- Verified backend/AI tests, frontend and Docker builds, live HTTP-to-WebSocket delivery, raw-batch storage and simulated disconnect/reconnect behavior.
- Verified the firmware skeleton compiles with PlatformIO's temporary conservative ESP32-S3 profile; no physical-board claim is implied.

### Changed

- Upgraded frontend Tailwind integration to the current Vite plugin path; production dependency audit now reports zero known vulnerabilities.
- Refined protected-branch review policy: collaborator PRs require owner approval, while the named owner may use a PR-only bypass on owner-authored PRs after all required checks pass and the branch is conflict-free.

### Fixed

- Corrected the Arduino `Esp.h` include casing so firmware builds on case-sensitive Linux CI runners.
- Replaced the missing favicon declaration with a cache-busted ASD-EASE wearable signal icon so browsers no longer reuse an icon from an older localhost project.

### Removed

- None.

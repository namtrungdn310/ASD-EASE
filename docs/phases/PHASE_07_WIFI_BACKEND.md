# Phase 07 — Wi-Fi Backend

## Status

NOT_STARTED

## Owner

IT (firmware networking/serialization and backend); AUTOMATION supports hardware, drivers and measured sampling.

## Detailed Implementation Plan

Use the [IT integration overview](../integration/README.md), [contract plan](../integration/03-device-ingestion-contract.md), [session-lifecycle plan](../integration/04-backend-session-lifecycle.md) and [firmware telemetry plan](../integration/05-firmware-telemetry-client.md). Track branch work in [integration progress](../integration/PROGRESS.md). This planning update does not change the phase status or replace real-device acceptance evidence.

## Objective

Send real ESP32 telemetry to the local FastAPI receiver over LAN.

## Why This Phase Exists

Replaces mock transport without moving inference to laptop.

## Dependencies

Phase 06, Phase 02

## Inputs

Verified ESP32 networking and laptop LAN address.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

ai/edge_firmware/src/communication/...; backend/...

## Implementation Notes

Keep credentials local; use bounded timeouts and contract version 1.0.

## Tests

Real device POST to LAN IP; validation and reconnect tests.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 07; no automatic work on the next phase.

## Known Risks

Firewall, DHCP, credentials or blocking network calls.

## Debug / Rollback Strategy

Use health endpoint and serial network diagnostics; fall back to isolated LAN.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 08 — Data Logger



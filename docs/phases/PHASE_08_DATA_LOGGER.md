# Phase 08 — Data Logger

## Status

NOT_STARTED

## Owner

IT

## Detailed Implementation Plan

Use the [raw-ingestion plan](../integration/06-backend-raw-ingestion.md), [firmware raw-batching plan](../integration/07-firmware-raw-batching.md), [recording/export plan](../integration/08-backend-recording-export.md), [session UI plan](../integration/09-frontend-recording-control.md) and [E2E acceptance plan](../integration/10-e2e-device-ingestion.md). Track branches in [integration progress](../integration/PROGRESS.md). The detailed plan does not itself complete this phase.

## Objective

Persist synchronized real raw batches and session metadata.

## Why This Phase Exists

Creates auditable input for actual dataset collection.

## Dependencies

Phase 07

## Inputs

Real streams, raw-batch endpoint and session IDs.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

backend/app/services/raw_storage.py; backend/app/api/v1/raw_data.py

## Implementation Notes

Use files for high-rate data and SQLite only for metadata.

## Tests

Start/stop session; ingest batches; reload and verify counts/order.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 08; no automatic work on the next phase.

## Known Risks

Partial files, storage exhaustion or schema drift.

## Debug / Rollback Strategy

Preserve source files; validate line-by-line and start a new session.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 09 — Dataset Collection


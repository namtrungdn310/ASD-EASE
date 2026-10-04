# Phase 15 — Model Export

## Status

NOT_STARTED

## Owner

IT

## Objective

Export the selected, approved small model and complete provenance metadata.

## Why This Phase Exists

ESP32 inference needs deterministic portable parameters.

## Dependencies

Phase 14

## Inputs

Selected model and frozen feature order.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/src/export/...; AI/edge_firmware/include/model_generated.h

## Implementation Notes

Generate code/data; do not use untrusted joblib; retain version and feature order.

## Tests

Round-trip load and fixed-vector Python checks.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 15; no automatic work on the next phase.

## Known Risks

Order, precision or unsupported-operation mismatch.

## Debug / Rollback Strategy

Compare each parameter/output with source artifact.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 16 — Edge Inference


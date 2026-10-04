# Phase 12 — Rule Baselines

## Status

NOT_STARTED

## Owner

IT

## Objective

Implement transparent HR, HR+GSR and HR+GSR+IMU engineering baselines.

## Why This Phase Exists

Provides honest comparators before ML.

## Dependencies

Phase 11

## Inputs

Feature tables with split/provenance metadata.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/src/training/...; AI/src/evaluation/...

## Implementation Notes

Tune only on training data and quality-gate invalid windows.

## Tests

Participant/session split evaluation on available real data; report measured metrics only.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 12; no automatic work on the next phase.

## Known Risks

Threshold leakage, overfitting or clinical overstatement.

## Debug / Rollback Strategy

Re-run from frozen split and inspect confusion cases.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 13 — ML Experiments


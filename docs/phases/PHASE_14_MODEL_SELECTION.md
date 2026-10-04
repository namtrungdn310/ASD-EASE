# Phase 14 — Model Selection

## Status

NOT_STARTED

## Owner

SHARED

## Objective

Select or reject candidates using measured accuracy and deployment constraints.

## Why This Phase Exists

The most complex or highest-F1 model may not be competition-suitable.

## Dependencies

Phase 13

## Inputs

Rule/ML results, size, latency and interpretability evidence.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/src/evaluation/...; docs/PROGRESS.md

## Implementation Notes

Compare precision, recall, F1, false alerts, size, latency, memory and stability when measured. Synthetic-only performance can validate software behavior but cannot select or validate the final real-world research model.

## Tests

Reproduce evaluation on held-out real data and review failure modes; audit participant/session/trial split boundaries and training-data provenance.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 14; no automatic work on the next phase.

## Known Risks

Metric cherry-picking or synthetic-only selection.

## Debug / Rollback Strategy

Return to experiment registry and predefined criteria.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 15 — Model Export

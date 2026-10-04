# Phase 13 — ML Experiments

## Status

NOT_STARTED

## Owner

IT

## Objective

Run small-model experiments with explicit data provenance.

## Why This Phase Exists

Tests whether limited ML improves engineering criteria over rules.

## Dependencies

Phase 12

## Inputs

Leakage-safe splits and feature definitions.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/src/training/...; AI/models/experiments/...

## Implementation Notes

Logistic regression, decision tree and small random forest; mark synthetic-only models `SYNTHETIC_ONLY`.

## Tests

Reproducible pipeline smoke test; split audit; measured evaluations by origin.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 13; no automatic work on the next phase.

## Known Risks

Generated data may make labels trivially separable or bias selection.

## Debug / Rollback Strategy

Remove revealing fields, increase overlap and retain real holdout.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 14 — Model Selection


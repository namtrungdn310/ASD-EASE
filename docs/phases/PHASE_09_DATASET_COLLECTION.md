# Phase 09 — Dataset Collection

## Status

NOT_STARTED

## Owner

SHARED

## Objective

Collect protocol-compliant real sessions separately from synthetic sessions.

## Why This Phase Exists

Scientific phases require independent real observations; generated data is insufficient.

## Dependencies

Phase 08

## Inputs

Approved protocol, pseudonymous IDs, working logger.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/data/raw/...; docs/DATASET_PROTOCOL.md

## Implementation Notes

Separate real/synthetic namespaces, provenance and trials; never mark complete from synthetic sessions.

## Tests

Validate consent/protocol as applicable, manifests, sample counts and held-out plan.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 09; no automatic work on the next phase.

## Known Risks

Privacy, insufficient coverage, imbalance or label ambiguity.

## Debug / Rollback Strategy

Stop collection on protocol/privacy issues; quarantine incomplete sessions.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 10 — Signal Processing


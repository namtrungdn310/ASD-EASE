# Development Workflow

`main` is the stable release-quality branch; `dev` is the daily integration branch. Both are protected against direct pushes. All work uses focused branches such as `feature/backend-*`, `feature/frontend-*`, `feature/firmware-*`, `feature/ai-*`, `fix/*`, `docs/*` and `chore/*`. Work branches open reviewed PRs into `dev`; only `dev` opens promotion PRs into `main`. See [GIT_WORKFLOW.md](GIT_WORKFLOW.md) for the exact two-person process.

Before merge: code builds, relevant tests pass, API remains compatible, the active phase document and `PROGRESS.md` are updated. Code changes update `CHANGELOG.md`; architecture changes update `DECISIONS.md`.

Any wire-contract change must update backend Pydantic, frontend TypeScript, firmware C++ and `API_CONTRACT.md` together. No silent changes.

At each phase boundary: run tests, evaluate every acceptance criterion, record only real evidence, report blockers, update progress and stop. Future placeholders do not complete a phase. Physical phases require physical evidence and scientific phases require actual experiments.

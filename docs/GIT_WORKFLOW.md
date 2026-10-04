# Git and GitHub Workflow for Two Contributors

## Branch roles

- `main`: stable, reviewed integration baseline. No direct push. Only PRs from `dev` are accepted.
- `dev`: daily integration branch. No direct push. Receives reviewed PRs from short-lived work branches.
- `feature/<scope>-<description>`: new functionality, for example `feature/backend-session-filter`.
- `fix/<scope>-<description>`: bug fixes.
- `docs/<description>`: documentation-only work.
- `chore/<description>`: CI, tooling or maintenance.

Do not share one feature branch between both contributors. Keep each branch focused on one reviewable outcome.

## Required flow

```text
feature/*, fix/*, docs/*, chore/*
                 |
                 | Pull Request + CI + review policy
                 v
                dev
                 |
                 | Pull Request from dev + CI + review policy
                 v
                main
```

The IT owner reviews the Automation student's PRs. For an owner-authored PR, the owner may select **Bypass rules and merge** without another approval, but only after every required CI check passes, the branch is up to date and conflict-free, and all review conversations are resolved. Neither contributor may directly push to protected branches. The owner must use this bypass only for their own PRs.

## First-time collaborator setup

The repository owner opens **Settings → Collaborators → Add people**, enters the Automation student's GitHub username and grants **Write** access. Do not grant Admin access. The student accepts the email/GitHub invitation and clones:

```powershell
git clone https://github.com/namtrungdn310/ASD-EASE.git
cd ASD-EASE
git switch dev
git pull --ff-only origin dev
```

Each contributor sets their own identity:

```powershell
git config user.name "YOUR NAME"
git config user.email "YOUR VERIFIED GITHUB EMAIL"
```

## Start a task

Always branch from the latest `dev`:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c feature/firmware-max30102
```

Use `feature/backend-*`, `feature/frontend-*`, `feature/ai-*`, or `feature/firmware-*` when practical. Never branch new work from a stale feature branch.

## Commit and publish the work branch

```powershell
git status
git add <specific-files>
git diff --staged
git commit -m "feat(firmware): add MAX30102 driver skeleton"
git push -u origin feature/firmware-max30102
```

Prefer Conventional Commit prefixes: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`. Never use `git add .` without first reviewing `git status`.

## Pull request into dev

On GitHub choose:

- Base: `dev`
- Compare: the work branch
- Reviewer: the repository owner when the Automation student opens the PR

Complete the PR template, wait for every required CI check, and address all review comments. An Automation-student PR requires the owner's approval; new commits invalidate stale approval. For an owner-authored PR, the owner may select **Bypass rules and merge** after verifying the final diff, all required checks, update status and conflict status. All conversations must be resolved. Use **Squash and merge**, then delete the work branch.

After merge, both contributors synchronize:

```powershell
git switch dev
git pull --ff-only origin dev
git branch -d feature/firmware-max30102
```

## Promote dev to main

Only promote a reviewed, integrated milestone:

1. Confirm relevant acceptance criteria and documentation are updated.
2. Open a PR with base `main` and compare `dev`.
3. Wait for all CI checks. An Automation-student PR also requires the owner's approval; for an owner-authored PR, the owner may select **Bypass rules and merge** after verifying the final diff is conflict-free.
4. Resolve every conversation.
5. Use **Squash and merge** only when the PR represents one release unit; otherwise use **Rebase and merge** to retain reviewed commits.
6. Never force-push or delete `main`/`dev`.

## Hotfix rule

Even urgent fixes use `fix/* → dev → main`. If `main` needs an exceptional emergency fix, create the branch from `main`, open a reviewed PR to `main`, then immediately merge the same fix back into `dev`. This exception should be rare and requires the owner's explicit decision; the current CI policy accepts normal `main` PRs only from `dev`, so temporarily changing that policy must itself be reviewed.

## Repository protection expected

Both `main` and `dev` require:

- Pull request before merge.
- One owner approval for collaborator-authored PRs.
- Stale collaborator-PR approvals are dismissed after new commits; owner-authored PRs may use the named owner's PR-only bypass.
- All required CI checks passing on an up-to-date branch.
- All review conversations resolved.
- Linear history.
- Admin enforcement for branch protection; the named owner's ruleset bypass is available only while merging a PR and must be used only on owner-authored PRs.
- Force pushes and branch deletion disabled.

The default branch is `dev`, so new clones and GitHub's default PR target naturally point to daily integration rather than stable `main`.

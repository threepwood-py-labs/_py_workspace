# Workspace Hygiene Follow-ups

Consolidated from the former top-level `TODOFORREAL.md`.
Resolved items are kept briefly for traceability alongside open follow-ups.

## Workspace Alignment Findings

1. Remove or formalize the orphaned top-level source tree at `src/many_panelz_explorer/file_icons.py`.
   The same module path already exists in `many-panelz-explorer/src/many_panelz_explorer/file_icons.py`, and the two copies have diverged. This creates an ambiguous source of truth.

2. Update the workspace project inventory in `_py_workspace/specs/AGENTS.md`.
   The Quick Startup Project Map omits `backlogooze`, even though it is present in the workspace and has a normal `pyproject.toml`.

3. Update workspace-wide audit and backlog docs to include `backlogooze`.
   [`audit-2026-03.md`](audit-2026-03.md) and [`ideas-backlog.md`](ideas-backlog.md)
   currently cover the other sibling repos but skip `backlogooze`.

4. [DONE] Remove machine-specific absolute paths from active markdown docs.
   `_py_workspace/README.md` and `_py_template/COPIER_ROLLOUT_RUNBOOK.md` were
   updated to use workspace-relative wording instead of hardcoded local paths.

5. [DONE] Fix the documented local quality-check commands in `prowlarr-ui/README.md`.
   The README now matches the current `pyproject.toml` scripts for tests, lint
   checks, and standalone packaging.

6. Reconcile changelog policy with actual repo state.
   `_py_workspace/specs/AGENTS.md` says significant project changes should go into `docs/CHANGELOG.md`, but these repos currently do not have that file:
   - `arr-helper-ui`
   - `backlogooze`
   - `git-statuz`
   - `many-panelz-explorer`
   - `pdf-search-downloader-ui`
   - `prowlarr-ui`
   - `qbiremo-enhanced`

## Repo Hygiene Suggestions

1. Add a machine-readable workspace manifest under `_py_workspace`.
   Use it as the source for the project map, audit docs, and workspace-level summaries instead of maintaining repo lists by hand.

2. Decide whether the top-level `src/` directory is intentional.
   If it is not intentional, remove it. If it is intentional, give it explicit ownership, docs, and a clear reason to exist outside the sibling repos.
   Policy note: repo-owned package code must live inside the owning repo, not under the workspace root `src/`.

3. Standardize README quality-check sections from `_py_template`.
   The child repos should document the same task model unless there is a repo-specific exception. Apply template fixes in `_py_template` first, then propagate with `copier update`.

4. Either make `docs/CHANGELOG.md` part of the default template or relax the workspace rule.
   The current policy is stricter than the current repo set.

5. [DONE] Move ad hoc root docs into a stable workspace docs area.
   Workspace-level notes now live under `_py_workspace/docs/workspace/`.

6. Review branch and remote consistency across sibling repos.
   Most repos use `develop`, but `backlogooze` is on `master`, `pdf-search-downloader-ui` is on `main`, and both currently have no `origin` remote.
   If those are intentional exceptions, document them.

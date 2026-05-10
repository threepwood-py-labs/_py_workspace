# _py_workspace

Shared support repository for this Python workspace.

This repository holds cross-project scripts, specifications, and reference material used by the sibling projects in this workspace.

## Structure

| Folder | Purpose |
|---|---|
| `docs/workspace/` | Consolidated workspace audits, hygiene notes, and idea backlogs |
| `scripts/` | Shared utility scripts (batch operations, build helpers, etc.) |
| `specs/` | Shared specifications, design documents, ADRs |
| `snippets/` | Reusable code snippets and reference patterns |

## Materialize

Use `scripts/materialize.py` to create and bootstrap the canonical flat Python
workspace. The command manages sibling repositories under one workspace root,
normalizes their canonical branch to `develop`, ensures the GitHub default branch
is `develop`, and runs each repository's `scripts/windows/setup_env.py` when it
exists.

Materialize also manages the org-facing repositories:

- `.github` - GitHub organization profile content
- `threepwood-py-labs.github.io` - static GitHub Pages landing site

On a real run, materialize persists `THREEPWOOD_PY_WORKSPACE_ROOT` to the
current process and to the Windows user environment. Restart existing shells to
pick up the persisted value.

Preview the plan without changing repositories:

```powershell
python scripts/materialize.py --dry-run
```

Materialize the default workspace root:

```powershell
python scripts/materialize.py
```

Common options:

```powershell
python scripts/materialize.py --target-root C:\tmp\py-workspace --owner threepwood-py-labs
python scripts/materialize.py --skip-setup
```

Safety behavior:

- existing repositories with uncommitted changes fail before branch movement
- missing canonical GitHub repositories are created as public org repos
- missing local repositories are cloned from the canonical org repo
- current checked-out work is moved to local `develop`
- remote `develop` is updated with `--force-with-lease` when it already exists
- old local branches such as `main`, `master`, or feature branches are preserved
- release tags and release packages are never created by materialize
- `THREEPWOOD_PY_WORKSPACE_ROOT` is updated during real materialize runs

After a real run, the command writes
`docs/workspace/materialize-status.md` with the latest workspace-relative repo
status.

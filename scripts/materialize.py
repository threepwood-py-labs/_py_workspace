"""Materialize and bootstrap the canonical Python workspace."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

DEFAULT_GITHUB_OWNER = "threepwood-py-labs"
CANONICAL_BRANCH = "develop"
STATUS_REPORT_PATH = Path("docs") / "workspace" / "materialize-status.md"
WORKSPACE_REPOSITORIES: tuple[str, ...] = (
    "_py_template",
    "_py_workspace",
    "arr-helper-ui",
    "backlogooze",
    "git-statuz",
    "many-panelz-explorer",
    "mp3gain-gui-py",
    "pdf-search-downloader-ui",
    "prowlarr-ui",
    "qbiremo-enhanced",
    "threep-commons",
    "video-duperz",
    "web-pagez-to-pdf",
)


class SetupResult(StrEnum):
    """Per-repository setup outcome values."""

    DRY_RUN = "dry-run"
    PASSED = "passed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class MaterializeOptions:
    """Resolved materialize command options."""

    target_root: Path
    owner: str
    dry_run: bool
    skip_setup: bool


@dataclass(frozen=True, slots=True)
class RepoStatus:
    """Status summary for one materialized repository."""

    name: str
    relative_path: str
    remote: str
    branch: str
    default_branch: str
    setup_result: SetupResult


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for workspace materialization."""

    parser = argparse.ArgumentParser(
        prog="materialize.py",
        description="Materialize and bootstrap the canonical Python workspace.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=None,
        help="Directory that contains the sibling repositories.",
    )
    parser.add_argument(
        "--owner",
        default=None,
        help="GitHub owner or organization for canonical repositories.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without mutating repositories or running setup.",
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip per-repository scripts/windows/setup_env.py bootstrap.",
    )
    return parser


def resolve_default_target_root() -> Path:
    """Resolve the default flat workspace root."""

    return Path(__file__).resolve().parents[2]


def resolve_script_repo_root() -> Path:
    """Resolve the `_py_workspace` repository root that contains this script."""

    return Path(__file__).resolve().parents[1]


def run_command(
    args: Sequence[str],
    *,
    cwd: Path,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one command and optionally raise on failure."""

    result = subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 and not allow_failure:
        command_text = " ".join(args)
        message = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise RuntimeError(f"{command_text}: {message}")
    return result


def parse_github_owner(remote_url: str) -> str | None:
    """Extract the GitHub owner from a remote URL."""

    cleaned_url = remote_url.strip()
    if cleaned_url.startswith("https://github.com/"):
        suffix = cleaned_url.removeprefix("https://github.com/")
    elif cleaned_url.startswith("git@github.com:"):
        suffix = cleaned_url.removeprefix("git@github.com:")
    else:
        return None
    parts = suffix.removesuffix(".git").split("/")
    if len(parts) < 2 or not parts[0]:
        return None
    return parts[0]


def detect_github_owner(script_repo_root: Path) -> str:
    """Detect the GitHub owner from the current `_py_workspace` origin remote."""

    result = run_command(
        ["git", "remote", "get-url", "origin"],
        cwd=script_repo_root,
        allow_failure=True,
    )
    if result.returncode != 0:
        return DEFAULT_GITHUB_OWNER
    return parse_github_owner(result.stdout) or DEFAULT_GITHUB_OWNER


def ensure_tool_available(tool_name: str, cwd: Path) -> None:
    """Raise if a required command-line tool is unavailable."""

    result = run_command([tool_name, "--version"], cwd=cwd, allow_failure=True)
    if result.returncode != 0:
        raise RuntimeError(f"Required tool is not available on PATH: {tool_name}")


def canonical_remote(owner: str, repo_name: str) -> str:
    """Return the canonical HTTPS GitHub remote for one repository."""

    return f"https://github.com/{owner}/{repo_name}.git"


def repo_exists_on_github(owner: str, repo_name: str, cwd: Path) -> bool:
    """Return whether one canonical GitHub repository exists."""

    result = run_command(
        ["gh", "repo", "view", f"{owner}/{repo_name}", "--json", "name"],
        cwd=cwd,
        allow_failure=True,
    )
    return result.returncode == 0


def ensure_github_repo(owner: str, repo_name: str, cwd: Path, *, dry_run: bool) -> None:
    """Ensure one public canonical GitHub repository exists."""

    if repo_exists_on_github(owner, repo_name, cwd):
        return
    command = ["gh", "repo", "create", f"{owner}/{repo_name}", "--public"]
    if dry_run:
        print(f"DRY-RUN create GitHub repo: {' '.join(command)}")
        return
    run_command(command, cwd=cwd)


def clone_missing_repo(owner: str, repo_name: str, target_path: Path, *, dry_run: bool) -> None:
    """Clone one missing repository into the flat workspace."""

    command = [
        "gh",
        "repo",
        "clone",
        f"{owner}/{repo_name}",
        str(target_path),
    ]
    if dry_run:
        print(f"DRY-RUN clone repo: {' '.join(command)}")
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(command, cwd=target_path.parent)


def ensure_git_worktree(repo_path: Path, repo_name: str) -> None:
    """Validate that an existing path is a Git worktree."""

    if not (repo_path / ".git").exists():
        raise RuntimeError(f"Existing repository path is not a Git worktree: {repo_name}")


def assert_clean_repo(repo_path: Path, repo_name: str) -> None:
    """Fail before moving branch pointers when local changes exist."""

    result = run_command(["git", "status", "--short"], cwd=repo_path)
    if result.stdout.strip():
        raise RuntimeError(
            f"Repository '{repo_name}' has uncommitted changes; commit or clean it first."
        )


def get_current_branch(repo_path: Path) -> str:
    """Return the currently checked-out Git branch name."""

    result = run_command(["git", "branch", "--show-current"], cwd=repo_path)
    return result.stdout.strip() or "(detached)"


def remote_exists(repo_path: Path, remote_name: str) -> bool:
    """Return whether a Git remote exists."""

    result = run_command(
        ["git", "remote", "get-url", remote_name],
        cwd=repo_path,
        allow_failure=True,
    )
    return result.returncode == 0


def ensure_origin(repo_path: Path, repo_name: str, owner: str, *, dry_run: bool) -> None:
    """Add or normalize the origin remote to the canonical GitHub URL."""

    remote_url = canonical_remote(owner, repo_name)
    if dry_run:
        print(f"DRY-RUN ensure origin {repo_name}: {remote_url}")
        return
    if remote_exists(repo_path, "origin"):
        run_command(["git", "remote", "set-url", "origin", remote_url], cwd=repo_path)
        return
    run_command(["git", "remote", "add", "origin", remote_url], cwd=repo_path)


def ref_exists(repo_path: Path, ref_name: str) -> bool:
    """Return whether a Git ref exists."""

    result = run_command(
        ["git", "show-ref", "--verify", "--quiet", ref_name],
        cwd=repo_path,
        allow_failure=True,
    )
    return result.returncode == 0


def run_branch_normalization(repo_path: Path, repo_name: str, *, dry_run: bool) -> None:
    """Move current checked-out work onto the canonical develop branch."""

    if dry_run:
        branch = get_current_branch(repo_path)
        print(f"DRY-RUN normalize {repo_name}: {branch} -> {CANONICAL_BRANCH}")
        return

    run_command(["git", "fetch", "origin", "--prune"], cwd=repo_path)
    run_command(["git", "branch", "-f", CANONICAL_BRANCH, "HEAD"], cwd=repo_path)
    run_command(["git", "checkout", CANONICAL_BRANCH], cwd=repo_path)
    remote_ref = f"refs/remotes/origin/{CANONICAL_BRANCH}"
    push_command = ["git", "push", "-u", "origin", CANONICAL_BRANCH]
    if ref_exists(repo_path, remote_ref):
        push_command.append("--force-with-lease")
    run_command(push_command, cwd=repo_path)


def set_default_branch(owner: str, repo_name: str, *, cwd: Path, dry_run: bool) -> None:
    """Set the GitHub repository default branch to develop."""

    command = [
        "gh",
        "repo",
        "edit",
        f"{owner}/{repo_name}",
        "--default-branch",
        CANONICAL_BRANCH,
    ]
    if dry_run:
        print(f"DRY-RUN set default branch: {' '.join(command)}")
        return
    run_command(command, cwd=cwd)


def run_setup(repo_path: Path, repo_name: str, *, dry_run: bool, skip_setup: bool) -> SetupResult:
    """Run one repository setup script when available."""

    setup_script = repo_path / "scripts" / "windows" / "setup_env.py"
    if skip_setup or not setup_script.is_file():
        return SetupResult.SKIPPED
    if dry_run:
        print(f"DRY-RUN setup {repo_name}: python {setup_script}")
        return SetupResult.DRY_RUN
    result = run_command(
        ["python", "scripts/windows/setup_env.py"],
        cwd=repo_path,
        allow_failure=True,
    )
    if result.returncode == 0:
        return SetupResult.PASSED
    print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
    return SetupResult.FAILED


def materialize_repo(options: MaterializeOptions, repo_name: str) -> RepoStatus:
    """Materialize and bootstrap one canonical repository."""

    repo_path = options.target_root / repo_name
    ensure_github_repo(options.owner, repo_name, options.target_root, dry_run=options.dry_run)
    if not repo_path.exists():
        clone_missing_repo(options.owner, repo_name, repo_path, dry_run=options.dry_run)
    else:
        ensure_git_worktree(repo_path, repo_name)

    if not options.dry_run:
        assert_clean_repo(repo_path, repo_name)
    ensure_origin(repo_path, repo_name, options.owner, dry_run=options.dry_run)
    run_branch_normalization(repo_path, repo_name, dry_run=options.dry_run)
    set_default_branch(options.owner, repo_name, cwd=options.target_root, dry_run=options.dry_run)
    setup_result = run_setup(
        repo_path,
        repo_name,
        dry_run=options.dry_run,
        skip_setup=options.skip_setup,
    )
    branch = CANONICAL_BRANCH if options.dry_run else get_current_branch(repo_path)
    return RepoStatus(
        name=repo_name,
        relative_path=repo_name,
        remote=canonical_remote(options.owner, repo_name),
        branch=branch,
        default_branch=CANONICAL_BRANCH,
        setup_result=setup_result,
    )


def build_status_report(statuses: Sequence[RepoStatus]) -> str:
    """Return the generated Markdown materialization status report."""

    lines = [
        "# Materialize Status",
        "",
        "Generated by `python scripts/materialize.py`.",
        "",
        "| Repo | Path | Remote | Branch | Default | Setup |",
        "|---|---|---|---|---|---|",
    ]
    for status in statuses:
        lines.append(
            "| "
            f"{status.name} | "
            f"`{status.relative_path}` | "
            f"{status.remote} | "
            f"`{status.branch}` | "
            f"`{status.default_branch}` | "
            f"{status.setup_result} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_status_report(target_root: Path, statuses: Sequence[RepoStatus], *, dry_run: bool) -> None:
    """Write the generated workspace materialization status report."""

    report_path = target_root / "_py_workspace" / STATUS_REPORT_PATH
    content = build_status_report(statuses)
    if dry_run:
        print(f"DRY-RUN write status report: {report_path}")
        print(content)
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8", newline="\n")


def parse_options(argv: Sequence[str] | None) -> MaterializeOptions:
    """Parse command-line arguments into resolved options."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    target_root = (
        args.target_root.resolve()
        if args.target_root is not None
        else resolve_default_target_root()
    )
    owner = args.owner or detect_github_owner(resolve_script_repo_root())
    return MaterializeOptions(
        target_root=target_root,
        owner=owner,
        dry_run=bool(args.dry_run),
        skip_setup=bool(args.skip_setup),
    )


def materialize_workspace(options: MaterializeOptions) -> int:
    """Materialize all canonical workspace repositories."""

    ensure_tool_available("git", options.target_root)
    ensure_tool_available("gh", options.target_root)
    statuses: list[RepoStatus] = []
    failures: list[str] = []
    for repo_name in WORKSPACE_REPOSITORIES:
        print(f"==> {repo_name}")
        try:
            statuses.append(materialize_repo(options, repo_name))
        except RuntimeError as exc:
            failures.append(f"{repo_name}: {exc}")

    write_status_report(options.target_root, statuses, dry_run=options.dry_run)
    if failures:
        print("Materialize completed with failures:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return EXIT_FAILURE
    print(f"Materialized {len(statuses)} repositories.")
    return EXIT_SUCCESS


def main(argv: Sequence[str] | None = None) -> int:
    """Run the materialize CLI."""

    try:
        options = parse_options(argv)
        return materialize_workspace(options)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())

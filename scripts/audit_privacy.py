"""Audit Git-tracked workspace files for private information leaks."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2

DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[1]
    / "manifests"
    / "privacy-guard"
    / "policy.v1.json"
)

type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)
type JsonObject = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class GuardRule:
    """One configured privacy rule."""

    id: str
    reason: str
    regex: str


@dataclass(frozen=True, slots=True)
class PrivacyPolicy:
    """Resolved tracked-file privacy policy."""

    version: str
    excluded_path_regexes: tuple[str, ...]
    path_rules: tuple[GuardRule, ...]
    content_rules: tuple[GuardRule, ...]


@dataclass(frozen=True, slots=True)
class AuditOptions:
    """Resolved audit command options."""

    target_root: Path
    policy_path: Path
    repos: tuple[str, ...]
    summary_path: Path | None
    json_output: bool


@dataclass(frozen=True, slots=True)
class PrivacyFinding:
    """One privacy audit finding."""

    repo: str
    path: str
    rule: str
    reason: str
    line: int | None
    preview: str | None

    def to_json(self) -> JsonObject:
        """Return a JSON-compatible representation of this finding."""

        return {
            "repo": self.repo,
            "path": self.path,
            "rule": self.rule,
            "reason": self.reason,
            "line": self.line,
            "preview": self.preview,
        }


@dataclass(frozen=True, slots=True)
class RepoAuditSummary:
    """Privacy audit summary for one repository."""

    repo: str
    repo_root: Path
    scanned_tracked_files: int
    excluded_tracked_files: tuple[str, ...]
    findings: tuple[PrivacyFinding, ...]
    missing: bool = False

    def to_json(self) -> JsonObject:
        """Return a JSON-compatible representation of this repository summary."""

        return {
            "repo": self.repo,
            "repoRoot": str(self.repo_root),
            "scannedTrackedFiles": self.scanned_tracked_files,
            "excludedTrackedFiles": list(self.excluded_tracked_files),
            "findings": [finding.to_json() for finding in self.findings],
            "missing": self.missing,
            "passed": not self.findings and not self.missing,
        }


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for tracked-file privacy audits."""

    parser = argparse.ArgumentParser(
        prog="audit_privacy.py",
        description="Audit Git-tracked workspace files for private information leaks.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=None,
        help="Workspace root containing the sibling repositories.",
    )
    parser.add_argument(
        "--policy-path",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="Privacy policy JSON manifest to apply.",
    )
    parser.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Repository name to audit. Repeat to audit multiple repos.",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=None,
        help="Optional JSON summary output path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full JSON summary instead of human-readable output.",
    )
    return parser


def resolve_default_target_root() -> Path:
    """Resolve the default flat workspace root."""

    return Path(__file__).resolve().parents[2]


def load_workspace_repositories() -> tuple[str, ...]:
    """Return the canonical materialized workspace repository list."""

    import materialize

    return tuple(materialize.WORKSPACE_REPOSITORIES)


def parse_options(argv: Sequence[str] | None) -> AuditOptions:
    """Parse CLI arguments into resolved audit options."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    target_root = (
        args.target_root.resolve()
        if args.target_root is not None
        else resolve_default_target_root()
    )
    selected_repos = tuple(str(repo).strip() for repo in args.repo if str(repo).strip())
    repositories = selected_repos or load_workspace_repositories()
    unknown_repos = sorted(set(selected_repos) - set(load_workspace_repositories()))
    if unknown_repos:
        parser.error("unknown repo filter(s): " + ", ".join(unknown_repos))
    return AuditOptions(
        target_root=target_root,
        policy_path=args.policy_path.resolve(),
        repos=repositories,
        summary_path=args.summary_path.resolve()
        if args.summary_path is not None
        else None,
        json_output=bool(args.json),
    )


def require_mapping(value: JsonValue, label: str) -> JsonObject:
    """Return a JSON object or raise for invalid manifest shape."""

    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object.")
    return value


def require_string(value: JsonValue, label: str) -> str:
    """Return a JSON string or raise for invalid manifest shape."""

    if not isinstance(value, str):
        raise RuntimeError(f"{label} must be a string.")
    return value


def require_string_list(value: JsonValue, label: str) -> tuple[str, ...]:
    """Return a tuple of strings or raise for invalid manifest shape."""

    if not isinstance(value, list):
        raise RuntimeError(f"{label} must be a list.")
    strings: list[str] = []
    for index, item in enumerate(value):
        strings.append(require_string(item, f"{label}[{index}]"))
    return tuple(strings)


def load_rule_list(value: JsonValue, label: str) -> tuple[GuardRule, ...]:
    """Load one list of guard rules from a JSON value."""

    if not isinstance(value, list):
        raise RuntimeError(f"{label} must be a list.")
    rules: list[GuardRule] = []
    for index, item in enumerate(value):
        entry = require_mapping(item, f"{label}[{index}]")
        rules.append(
            GuardRule(
                id=require_string(entry.get("id"), f"{label}[{index}].id"),
                reason=require_string(entry.get("reason"), f"{label}[{index}].reason"),
                regex=require_string(entry.get("regex"), f"{label}[{index}].regex"),
            )
        )
    return tuple(rules)


def load_policy(policy_path: Path, repo_root: Path) -> PrivacyPolicy:
    """Load and expand the tracked-file privacy policy."""

    if not policy_path.is_file():
        raise RuntimeError(f"Privacy policy manifest is missing: {policy_path}")
    raw_policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy = require_mapping(raw_policy, "policy")
    version = require_string(policy.get("policyVersion"), "policy.policyVersion")
    excluded_path_regexes = require_string_list(
        policy.get("excludedPathRegexes", []),
        "policy.excludedPathRegexes",
    )
    path_rules = load_rule_list(policy.get("pathRules", []), "policy.pathRules")
    content_rules = load_rule_list(
        policy.get("contentRules", []), "policy.contentRules"
    )
    dynamic_path_rules, dynamic_content_rules = build_personal_identifier_rules(
        repo_root
    )
    return PrivacyPolicy(
        version=version,
        excluded_path_regexes=excluded_path_regexes,
        path_rules=path_rules + dynamic_path_rules,
        content_rules=content_rules + dynamic_content_rules,
    )


def build_personal_identifier_rules(
    repo_root: Path,
) -> tuple[tuple[GuardRule, ...], tuple[GuardRule, ...]]:
    """Build privacy rules from environment and local identifier overrides."""

    identifiers = get_personal_identifiers(repo_root)
    path_rules = tuple(
        GuardRule(
            id="personal-identifier-filename",
            reason="Tracked filenames must not embed configured personal identifiers.",
            regex=rf"(^|[\\/])[^\\/]*{re.escape(identifier)}[^\\/]*$",
        )
        for identifier in identifiers
    )
    content_rules = tuple(
        GuardRule(
            id="personal-identifier-content",
            reason="Tracked content must not expose configured personal identifiers.",
            regex=rf"(?i)\b(user(name)?|profile|home|owner|author)\b\s*[:=]\s*[\"']?{re.escape(identifier)}\b",
        )
        for identifier in identifiers
    )
    return path_rules, content_rules


def get_personal_identifiers(repo_root: Path) -> tuple[str, ...]:
    """Return environment-derived and local privacy identifiers."""

    candidates: list[str] = []
    for variable_name in ("USERPROFILE", "HOME"):
        profile_path = os.environ.get(variable_name, "")
        if profile_path:
            candidates.append(Path(profile_path).name)
    for variable_name in ("USERNAME", "USER"):
        value = os.environ.get(variable_name, "")
        if value:
            candidates.append(value)
    candidates.extend(
        split_identifier_override(
            os.environ.get("TRACKED_FILE_PRIVACY_IDENTIFIERS", "")
        )
    )

    local_identifier_path = repo_root / ".tracked-file-privacy-identifiers.local.json"
    if local_identifier_path.is_file():
        local_policy = require_mapping(
            json.loads(local_identifier_path.read_text(encoding="utf-8")),
            str(local_identifier_path),
        )
        candidates.extend(read_local_identifiers(local_policy))

    seen: set[str] = set()
    identifiers: list[str] = []
    for candidate in candidates:
        identifier = candidate.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,}", identifier):
            continue
        if identifier in seen:
            continue
        seen.add(identifier)
        identifiers.append(identifier)
    return tuple(identifiers)


def split_identifier_override(raw_value: str) -> tuple[str, ...]:
    """Split a local environment override into identifier candidates."""

    return tuple(
        value.strip() for value in re.split(r"[,;]", raw_value) if value.strip()
    )


def read_local_identifiers(local_policy: JsonObject) -> tuple[str, ...]:
    """Read personal identifiers from a local untracked policy override."""

    raw_identifiers = local_policy.get("personalIdentifiers", [])
    if not isinstance(raw_identifiers, list):
        return ()
    identifiers: list[str] = []
    for item in raw_identifiers:
        if isinstance(item, str) and item.strip():
            identifiers.append(item.strip())
    return tuple(identifiers)


def run_git(repo_root: Path, args: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    """Run Git in one repository and capture byte output."""

    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def get_tracked_files(repo_root: Path) -> tuple[str, ...]:
    """Return Git-tracked paths under one repository."""

    result = run_git(repo_root, ["ls-files", "-z"])
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"git ls-files failed for '{repo_root}'." + (f" {detail}" if detail else "")
        )
    decoded = result.stdout.decode("utf-8", errors="surrogateescape")
    return tuple(entry for entry in decoded.split("\0") if entry.strip())


def is_excluded_path(relative_path: str, regexes: Sequence[str]) -> bool:
    """Return whether a tracked path is excluded by policy."""

    return any(
        re.search(regex, relative_path, flags=re.IGNORECASE) for regex in regexes
    )


def audit_repo(
    repo_name: str, repo_root: Path, policy: PrivacyPolicy
) -> RepoAuditSummary:
    """Audit one repository for tracked-file privacy findings."""

    if not repo_root.exists():
        return RepoAuditSummary(
            repo=repo_name,
            repo_root=repo_root,
            scanned_tracked_files=0,
            excluded_tracked_files=(),
            findings=(),
            missing=True,
        )
    tracked_files = get_tracked_files(repo_root)
    scanned_files: list[str] = []
    excluded_files: list[str] = []
    findings: list[PrivacyFinding] = []
    for relative_path in tracked_files:
        if is_excluded_path(relative_path, policy.excluded_path_regexes):
            excluded_files.append(relative_path)
            continue
        scanned_files.append(relative_path)
        findings.extend(find_path_matches(repo_name, relative_path, policy.path_rules))
    findings.extend(
        find_content_matches(repo_name, repo_root, scanned_files, policy.content_rules)
    )
    return RepoAuditSummary(
        repo=repo_name,
        repo_root=repo_root,
        scanned_tracked_files=len(scanned_files),
        excluded_tracked_files=tuple(excluded_files),
        findings=tuple(findings),
    )


def find_path_matches(
    repo_name: str,
    relative_path: str,
    rules: Iterable[GuardRule],
) -> tuple[PrivacyFinding, ...]:
    """Return path privacy findings for one tracked path."""

    for rule in rules:
        if re.search(rule.regex, relative_path, flags=re.IGNORECASE):
            return (
                PrivacyFinding(
                    repo=repo_name,
                    path=relative_path,
                    rule=rule.id,
                    reason=rule.reason,
                    line=None,
                    preview=None,
                ),
            )
    return ()


def find_content_matches(
    repo_name: str,
    repo_root: Path,
    relative_paths: Sequence[str],
    rules: Sequence[GuardRule],
) -> tuple[PrivacyFinding, ...]:
    """Return content privacy findings for tracked text files."""

    matches: list[PrivacyFinding] = []
    compiled_rules = tuple((rule, re.compile(rule.regex)) for rule in rules)
    for relative_path in relative_paths:
        file_path = repo_root / relative_path
        if not file_path.is_file():
            continue
        raw_content = file_path.read_bytes()
        if b"\0" in raw_content:
            continue
        lines = raw_content.decode("utf-8", errors="replace").splitlines()
        for line_number, line in enumerate(lines, start=1):
            for rule, compiled in compiled_rules:
                if compiled.search(line):
                    matches.append(
                        PrivacyFinding(
                            repo=repo_name,
                            path=relative_path,
                            rule=rule.id,
                            reason=rule.reason,
                            line=line_number,
                            preview=line.strip(),
                        )
                    )
                    break
    return tuple(matches)


def build_summary(options: AuditOptions, policy: PrivacyPolicy) -> JsonObject:
    """Run the audit and build the JSON-compatible summary."""

    repo_summaries = tuple(
        audit_repo(repo_name, options.target_root / repo_name, policy)
        for repo_name in options.repos
    )
    finding_count = sum(len(summary.findings) for summary in repo_summaries)
    missing_repos = tuple(summary.repo for summary in repo_summaries if summary.missing)
    return {
        "schemaVersion": "workspace-privacy-audit-summary/v1",
        "policyVersion": policy.version,
        "workspaceRoot": str(options.target_root),
        "repoCount": len(repo_summaries),
        "findingCount": finding_count,
        "missingRepos": list(missing_repos),
        "repos": [summary.to_json() for summary in repo_summaries],
        "passed": finding_count == 0,
    }


def write_summary(summary: JsonObject, summary_path: Path | None) -> None:
    """Write an optional JSON summary file."""

    if summary_path is None:
        return
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2), encoding="utf-8", newline="\n"
    )


def print_human_summary(summary: JsonObject) -> None:
    """Print a compact human-readable audit summary."""

    repo_count = int(summary["repoCount"])
    finding_count = int(summary["findingCount"])
    missing_repos = tuple(str(repo) for repo in summary["missingRepos"])
    print(f"Privacy audit scanned {repo_count} repos.")
    if missing_repos:
        print("Missing repos: " + ", ".join(missing_repos))
    if finding_count == 0:
        print("No tracked-file privacy findings.")
        return
    print(f"Findings: {finding_count}")
    repos = summary["repos"]
    if not isinstance(repos, list):
        return
    for repo_entry in repos:
        if not isinstance(repo_entry, dict):
            continue
        findings = repo_entry.get("findings", [])
        if not isinstance(findings, list) or not findings:
            continue
        print(f"==> {repo_entry.get('repo')}")
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            line = finding.get("line")
            location = str(finding.get("path"))
            if isinstance(line, int):
                location = f"{location}:{line}"
            print(f"  - {location} [{finding.get('rule')}] {finding.get('reason')}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tracked-file privacy audit CLI."""

    try:
        options = parse_options(argv)
        policy = load_policy(options.policy_path, options.target_root)
        summary = build_summary(options, policy)
        write_summary(summary, options.summary_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_USAGE

    if options.json_output:
        print(json.dumps(summary, indent=2))
    else:
        print_human_summary(summary)
    return EXIT_SUCCESS if bool(summary["passed"]) else EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())

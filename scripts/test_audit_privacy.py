"""Unit tests for the workspace privacy audit helper."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_PATH = SCRIPT_DIR / "audit_privacy.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "workspace_audit_privacy",
    MODULE_PATH,
)
assert MODULE_SPEC is not None
assert MODULE_SPEC.loader is not None
audit_privacy = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules["workspace_audit_privacy"] = audit_privacy
MODULE_SPEC.loader.exec_module(audit_privacy)


class PrivacyAuditTests(unittest.TestCase):
    """Test tracked-file privacy audit behavior."""

    def setUp(self) -> None:
        """Create a temporary workspace and policy for each test."""

        companion_root = Path("C:/tmp/pycompa/_USERPROFILE/privacy-audit-tests")
        companion_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=companion_root)
        self.workspace_root = Path(self.temp_dir.name)
        self.policy_path = self.workspace_root / "policy.v1.json"
        self.policy_path.write_text(
            json.dumps(
                {
                    "policyVersion": "test-policy/v1",
                    "excludedPathRegexes": ["(^|[\\\\/])build([\\\\/]|$)"],
                    "pathRules": [
                        {
                            "id": "tracked-env-file",
                            "reason": "No env files.",
                            "regex": "(^|[\\\\/])\\.env(\\..*)?$",
                        }
                    ],
                    "contentRules": [
                        {
                            "id": "windows-user-profile-path",
                            "reason": "No user profile paths.",
                            "regex": "C:\\\\Users\\\\[A-Za-z0-9_][A-Za-z0-9._-]*",
                        }
                    ],
                }
            ),
            encoding="utf-8",
            newline="\n",
        )

    def tearDown(self) -> None:
        """Dispose of the temporary workspace."""

        self.temp_dir.cleanup()

    def test_clean_repo_passes(self) -> None:
        """Pass when tracked content has no private data."""

        repo_root = self.create_repo("demo", {"README.md": "# Demo\n"})
        policy = audit_privacy.load_policy(self.policy_path, self.workspace_root)
        summary = audit_privacy.audit_repo("demo", repo_root, policy)

        self.assertFalse(summary.findings)
        self.assertEqual(summary.scanned_tracked_files, 1)

    def test_windows_user_profile_path_fails(self) -> None:
        """Fail when tracked text contains a Windows user profile path."""

        repo_root = self.create_repo(
            "demo",
            {"README.md": "local path: C:\\Users\\alice\\project\n"},
        )
        policy = audit_privacy.load_policy(self.policy_path, self.workspace_root)
        summary = audit_privacy.audit_repo("demo", repo_root, policy)

        self.assertEqual(len(summary.findings), 1)
        self.assertEqual(summary.findings[0].rule, "windows-user-profile-path")
        self.assertEqual(summary.findings[0].line, 1)

    def test_personal_identifier_filename_fails(self) -> None:
        """Fail when tracked filenames contain configured personal identifiers."""

        repo_root = self.create_repo("demo", {"notes/alice-private.md": "ok\n"})
        with mock.patch.dict(
            os.environ,
            {"TRACKED_FILE_PRIVACY_IDENTIFIERS": "alice"},
            clear=True,
        ):
            policy = audit_privacy.load_policy(self.policy_path, self.workspace_root)
        summary = audit_privacy.audit_repo("demo", repo_root, policy)

        self.assertEqual(len(summary.findings), 1)
        self.assertEqual(summary.findings[0].rule, "personal-identifier-filename")

    def test_personal_identifier_content_fails(self) -> None:
        """Fail when tracked content exposes configured personal identifiers."""

        repo_root = self.create_repo("demo", {"owner.txt": "owner = alice\n"})
        with mock.patch.dict(
            os.environ,
            {"TRACKED_FILE_PRIVACY_IDENTIFIERS": "alice"},
            clear=True,
        ):
            policy = audit_privacy.load_policy(self.policy_path, self.workspace_root)
        summary = audit_privacy.audit_repo("demo", repo_root, policy)

        self.assertEqual(len(summary.findings), 1)
        self.assertEqual(summary.findings[0].rule, "personal-identifier-content")

    def test_excluded_build_path_is_not_scanned(self) -> None:
        """Ignore tracked paths excluded by policy."""

        repo_root = self.create_repo(
            "demo",
            {"build/report.txt": "local path: C:\\Users\\alice\\project\n"},
        )
        policy = audit_privacy.load_policy(self.policy_path, self.workspace_root)
        summary = audit_privacy.audit_repo("demo", repo_root, policy)

        self.assertFalse(summary.findings)
        self.assertEqual(summary.scanned_tracked_files, 0)
        self.assertEqual(summary.excluded_tracked_files, ("build/report.txt",))

    def test_summary_path_writes_json_summary(self) -> None:
        """Write machine-readable JSON summaries when requested."""

        self.create_repo("demo", {"README.md": "# Demo\n"})
        summary_path = self.workspace_root / "summary.json"
        with mock.patch.object(
            audit_privacy,
            "load_workspace_repositories",
            return_value=("demo",),
        ):
            with redirect_stdout(io.StringIO()):
                exit_code = audit_privacy.main(
                    [
                        "--target-root",
                        str(self.workspace_root),
                        "--policy-path",
                        str(self.policy_path),
                        "--repo",
                        "demo",
                        "--summary-path",
                        str(summary_path),
                        "--json",
                    ]
                )

        self.assertEqual(exit_code, audit_privacy.EXIT_SUCCESS)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["repoCount"], 1)

    def test_repo_filter_rejects_unknown_repo(self) -> None:
        """Reject unknown repository filters before scanning."""

        with mock.patch.object(
            audit_privacy,
            "load_workspace_repositories",
            return_value=("known",),
        ):
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as context:
                    audit_privacy.parse_options(["--repo", "unknown"])

        self.assertNotEqual(context.exception.code, audit_privacy.EXIT_SUCCESS)

    def create_repo(self, name: str, files: dict[str, str]) -> Path:
        """Create a temporary Git repo with tracked files."""

        repo_root = self.workspace_root / name
        repo_root.mkdir()
        self.run_git(repo_root, "init")
        for relative_path, content in files.items():
            target_path = repo_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8", newline="\n")
        self.run_git(repo_root, "add", ".")
        return repo_root

    def run_git(self, repo_root: Path, *args: str) -> None:
        """Run one Git command in a test repository."""

        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            self.fail(f"git {' '.join(args)} failed: {detail}")


if __name__ == "__main__":
    unittest.main()

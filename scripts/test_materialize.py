"""Unit tests for the workspace materialize helper."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_PATH = SCRIPT_DIR / "materialize.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "workspace_materialize",
    MODULE_PATH,
)
assert MODULE_SPEC is not None
assert MODULE_SPEC.loader is not None
materialize = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules["workspace_materialize"] = materialize
MODULE_SPEC.loader.exec_module(materialize)


class MaterializeTests(unittest.TestCase):
    """Test materialize planning and execution helpers."""

    def setUp(self) -> None:
        """Create a temporary workspace root for each test."""

        self.temp_dir = tempfile.TemporaryDirectory()
        self.target_root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Dispose of the temporary workspace root."""

        self.temp_dir.cleanup()

    def test_dry_run_does_not_mutate_remote_or_setup(self) -> None:
        """Preview repository actions without invoking push, edit, or setup."""

        repo_path = self.target_root / "demo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()
        options = materialize.MaterializeOptions(
            target_root=self.target_root,
            owner="owner",
            dry_run=True,
            skip_setup=False,
        )

        with mock.patch.object(materialize, "repo_exists_on_github", return_value=True):
            with mock.patch.object(
                materialize,
                "get_current_branch",
                return_value="feature/demo",
            ):
                status = materialize.materialize_repo(options, "demo")

        self.assertEqual(status.branch, materialize.CANONICAL_BRANCH)
        self.assertEqual(status.setup_result, materialize.SetupResult.SKIPPED)

    def test_dry_run_missing_repo_returns_preview_status(self) -> None:
        """Avoid inspecting missing local paths during dry-run previews."""

        options = materialize.MaterializeOptions(
            target_root=self.target_root,
            owner="owner",
            dry_run=True,
            skip_setup=False,
        )
        with mock.patch.object(materialize, "repo_exists_on_github", return_value=False):
            status = materialize.materialize_repo(options, "missing-demo")

        self.assertEqual(status.name, "missing-demo")
        self.assertEqual(status.branch, materialize.CANONICAL_BRANCH)
        self.assertEqual(status.setup_result, materialize.SetupResult.DRY_RUN)

    def test_missing_github_repo_is_created_publicly(self) -> None:
        """Create missing canonical GitHub repositories as public repos."""

        with mock.patch.object(
            materialize,
            "repo_exists_on_github",
            return_value=False,
        ):
            with mock.patch.object(materialize, "run_command") as run_mock:
                materialize.ensure_github_repo(
                    "owner",
                    "demo",
                    self.target_root,
                    dry_run=False,
                )

        run_mock.assert_called_once_with(
            ["gh", "repo", "create", "owner/demo", "--public"],
            cwd=self.target_root,
        )

    def test_org_profile_and_pages_repos_are_canonical(self) -> None:
        """Keep org-facing repositories in the canonical materialize set."""

        self.assertIn(".github", materialize.WORKSPACE_REPOSITORIES)
        self.assertIn(
            "threepwood-py-labs.github.io",
            materialize.WORKSPACE_REPOSITORIES,
        )

    def test_missing_origin_is_added(self) -> None:
        """Add canonical origin remote when no origin exists."""

        repo_path = self.target_root / "demo"
        repo_path.mkdir()
        with mock.patch.object(materialize, "remote_exists", return_value=False):
            with mock.patch.object(materialize, "run_command") as run_mock:
                materialize.ensure_origin(repo_path, "demo", "owner", dry_run=False)

        run_mock.assert_called_once_with(
            [
                "git",
                "remote",
                "add",
                "origin",
                "https://github.com/owner/demo.git",
            ],
            cwd=repo_path,
        )

    def test_dirty_repo_is_rejected_before_branch_move(self) -> None:
        """Reject uncommitted changes before canonical branch normalization."""

        completed = mock.Mock(returncode=0, stdout=" M README.md\n", stderr="")
        with mock.patch.object(materialize, "run_command", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "uncommitted changes"):
                materialize.assert_clean_repo(self.target_root / "demo", "demo")

    def test_branch_normalization_force_pushes_existing_remote_develop(self) -> None:
        """Move current work to develop and lease-protect existing remote develop."""

        repo_path = self.target_root / "demo"
        calls: list[list[str]] = []

        def fake_run_command(
            args: list[str],
            *,
            cwd: Path,
            allow_failure: bool = False,
        ) -> mock.Mock:
            del cwd, allow_failure
            calls.append(args)
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(materialize, "run_command", side_effect=fake_run_command):
            with mock.patch.object(materialize, "ref_exists", return_value=True):
                with mock.patch.object(
                    materialize,
                    "get_current_branch",
                    return_value="feature/demo",
                ):
                    materialize.run_branch_normalization(repo_path, "demo", dry_run=False)

        self.assertIn(["git", "branch", "-f", "develop", "HEAD"], calls)
        self.assertIn(
            ["git", "push", "-u", "--force-with-lease", "origin", "develop"],
            calls,
        )

    def test_empty_repo_defers_branch_normalization(self) -> None:
        """Do not force branches before an empty repository has its first commit."""

        repo_path = self.target_root / "demo"
        calls: list[list[str]] = []

        def fake_run_command(
            args: list[str],
            *,
            cwd: Path,
            allow_failure: bool = False,
        ) -> mock.Mock:
            del cwd, allow_failure
            calls.append(args)
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(materialize, "run_command", side_effect=fake_run_command):
            with mock.patch.object(
                materialize,
                "get_current_branch",
                return_value="(detached)",
            ):
                with mock.patch.object(materialize, "head_exists", return_value=False):
                    materialize.run_branch_normalization(repo_path, "demo", dry_run=False)

        self.assertNotIn(["git", "branch", "-f", "develop", "HEAD"], calls)
        self.assertNotIn(["git", "push", "-u", "origin", "develop"], calls)

    def test_branch_normalization_skips_current_develop_force_update(self) -> None:
        """Avoid force-updating develop while it is checked out."""

        repo_path = self.target_root / "demo"
        calls: list[list[str]] = []

        def fake_run_command(
            args: list[str],
            *,
            cwd: Path,
            allow_failure: bool = False,
        ) -> mock.Mock:
            del cwd, allow_failure
            calls.append(args)
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(materialize, "run_command", side_effect=fake_run_command):
            with mock.patch.object(materialize, "ref_exists", return_value=True):
                with mock.patch.object(
                    materialize,
                    "get_current_branch",
                    return_value="develop",
                ):
                    materialize.run_branch_normalization(repo_path, "demo", dry_run=False)

        self.assertNotIn(["git", "branch", "-f", "develop", "HEAD"], calls)
        self.assertIn(
            ["git", "push", "-u", "--force-with-lease", "origin", "develop"],
            calls,
        )

    def test_setup_runs_only_when_script_exists(self) -> None:
        """Run per-repo setup only when the Windows setup helper exists."""

        repo_path = self.target_root / "demo"
        setup_script = repo_path / "scripts" / "windows" / "setup_env.py"
        setup_script.parent.mkdir(parents=True)
        setup_script.write_text("print('setup')\n", encoding="utf-8")
        completed = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(materialize, "run_command", return_value=completed):
            result = materialize.run_setup(
                repo_path,
                "demo",
                dry_run=False,
                skip_setup=False,
            )

        self.assertEqual(result, materialize.SetupResult.PASSED)

    def test_status_report_uses_workspace_relative_paths(self) -> None:
        """Avoid committing machine-specific absolute paths in status reports."""

        report = materialize.build_status_report(
            [
                materialize.RepoStatus(
                    name="demo",
                    relative_path="demo",
                    remote="https://github.com/owner/demo.git",
                    branch="develop",
                    default_branch="develop",
                    setup_result=materialize.SetupResult.PASSED,
                )
            ]
        )

        self.assertIn("`demo`", report)
        self.assertNotIn(str(self.target_root), report)

    def test_environment_persistence_skips_windows_registry_in_dry_run(self) -> None:
        """Avoid mutating process or user environment in dry-run mode."""

        with mock.patch.dict(materialize.os.environ, {}, clear=True):
            materialize.set_workspace_root_environment(self.target_root, dry_run=True)

        self.assertNotIn(
            materialize.WORKSPACE_ROOT_ENV_VAR,
            materialize.os.environ,
        )

    def test_environment_persistence_sets_process_environment(self) -> None:
        """Set the current process environment during a real materialize run."""

        with mock.patch.object(materialize.sys, "platform", "linux"):
            with mock.patch.dict(materialize.os.environ, {}, clear=True):
                materialize.set_workspace_root_environment(self.target_root, dry_run=False)
                self.assertEqual(
                    materialize.os.environ[materialize.WORKSPACE_ROOT_ENV_VAR],
                    str(self.target_root.resolve()),
                )

    def test_environment_persistence_writes_windows_user_environment(self) -> None:
        """Persist the workspace root into the Windows user environment."""

        fake_winreg = mock.Mock()
        fake_key = mock.MagicMock()
        fake_winreg.HKEY_CURRENT_USER = object()
        fake_winreg.KEY_SET_VALUE = object()
        fake_winreg.REG_EXPAND_SZ = object()
        fake_winreg.OpenKey.return_value = fake_key
        with mock.patch.object(materialize.sys, "platform", "win32"):
            with mock.patch.dict(sys.modules, {"winreg": fake_winreg}):
                materialize.set_workspace_root_environment(
                    self.target_root,
                    dry_run=False,
                )

        fake_winreg.SetValueEx.assert_called_once()


if __name__ == "__main__":
    unittest.main()

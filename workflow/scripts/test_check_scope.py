"""Checks role scopes, hook events and fixed dirty candidates with stdlib tools."""

import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import check_scope
from check_scope import ROOT, in_scope, load_scope, relative_to_root

SCRIPT = ROOT / "workflow" / "scripts" / "check_scope.py"


def run_hook(role, tool_input, cwd=ROOT):
    event = {"tool_name": "Edit", "tool_input": tool_input, "cwd": str(cwd)}
    if role:
        event["agent_type"] = role
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--hook"],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
    )


class ScopeTest(unittest.TestCase):
    def test_glob_star_and_double_star(self):
        self.assertTrue(check_scope.matches("src/a.py", ["src/*"]))
        self.assertFalse(check_scope.matches("src/app/a.py", ["src/*"]))
        self.assertTrue(check_scope.matches("src/app/tests/a.py", ["src/**/tests/**"]))
        self.assertTrue(check_scope.matches("src/tests/a.py", ["src/**/tests/**"]))
        self.assertTrue(
            check_scope.matches("requirements.txt", ["**/requirements*.txt"])
        )

    def test_builder_can_update_specs_tests_code_and_guides(self):
        scope = load_scope("builder")
        for path in [
            "workflow/specs/product/rounds.md",
            "workflow/plans/a.md",
            "src/rounds/views.py",
            "src/rounds/tests/test_views.py",
            "src/e2e/test_round.py",
            "pytest.ini",
            "docs/UserGuide.md",
            "requirements.txt",
            ".github/workflows/ci.yml",
        ]:
            self.assertTrue(in_scope(path, scope), path)

    def test_builder_cannot_rewrite_its_controls_or_read_secret_files(self):
        scope = load_scope("builder")
        for path in [
            "AGENTS.md",
            "CLAUDE.md",
            "workflow/agents/builder.md",
            "workflow/scripts/check_scope.py",
            "workflow/skills/slice.md",
            ".claude/settings.json",
            ".codex/hooks.json",
            ".env",
            ".env.production",
            "src/.env.local",
            "docs/Reflections.md",
        ]:
            self.assertFalse(in_scope(path, scope), path)

    def test_review_roles_have_no_write_scope(self):
        for role in ["verifier", "security-reviewer"]:
            self.assertFalse(in_scope("src/rounds/views.py", load_scope(role)))

    def test_unknown_role_and_relative_paths(self):
        self.assertIsNone(load_scope("no-such-role"))
        self.assertEqual(relative_to_root(ROOT / "src/a.py"), "src/a.py")
        self.assertIsNone(relative_to_root(ROOT.parent / "elsewhere.py"))


class HookTest(unittest.TestCase):
    def test_builder_controls_blocked_but_tests_allowed(self):
        self.assertEqual(run_hook("builder", {"file_path": "AGENTS.md"}).returncode, 2)
        self.assertEqual(
            run_hook("builder", {"file_path": "src/tests/test_a.py"}).returncode, 0
        )

    def test_reviewers_and_outside_path_blocked(self):
        for role in ["verifier", "security_reviewer"]:
            self.assertEqual(run_hook(role, {"file_path": "src/a.py"}).returncode, 2)
        self.assertEqual(
            run_hook("builder", {"file_path": str(ROOT.parent / "a.py")}).returncode, 2
        )

    def test_patch_checks_all_paths_and_renames(self):
        patch_text = (
            "*** Begin Patch\n*** Update File: src/a.py\n"
            "*** Move to: AGENTS.md\n*** End Patch\n"
        )
        self.assertEqual(run_hook("builder", {"command": patch_text}).returncode, 2)
        patch_text = (
            "*** Begin Patch\r\n***  Update File: src/a.py \r\n"
            "*** Add File: src/b.py\r\n*** End Patch\r\n"
        )
        self.assertEqual(run_hook("builder", {"input": patch_text}).returncode, 0)

    def test_missing_paths_blocked_for_known_role(self):
        for tool_input in [{}, {"patch": "not a patch"}]:
            self.assertEqual(run_hook("builder", tool_input).returncode, 2)

    def test_main_and_unknown_roles_are_explicitly_not_enforced(self):
        for role in [None, "general-purpose"]:
            self.assertEqual(run_hook(role, {"file_path": "AGENTS.md"}).returncode, 0)

    def test_invalid_json_is_not_success(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--hook"],
            input="{",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)


class WorkingTreeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.git("init", "-q")
        self.write("src/rounds/views.py")
        self.write("AGENTS.md")
        self.git("add", "src", "AGENTS.md")
        self.git("commit", "-q", "-m", "init")
        self.base = self.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def write(self, rel_path, text="x\n"):
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def scope_check(self, role, base=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return check_scope.check_working_tree(role, base, self.root)

    def snapshot_file(self):
        # Outside the throwaway repo, so the manifest does not hash itself.
        target = Path(self.tmp.name).with_suffix(".snapshot.json")
        target.write_text(
            json.dumps(check_scope.candidate_snapshot(self.root)), encoding="utf-8"
        )
        self.addCleanup(target.unlink, missing_ok=True)
        return target

    def snapshot_check(self, path, role=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return check_scope.check_snapshot(path, role, self.root)

    def test_changes_untracked_deletion_and_rename(self):
        self.write("src/rounds/views.py", "y\n")
        self.write("src/rounds/new.py")
        self.assertEqual(self.scope_check("builder", self.base), 0)
        self.write("workflow/agents/builder.md")
        self.assertEqual(self.scope_check("builder", self.base), 1)
        (self.root / "workflow/agents/builder.md").unlink()
        self.git("mv", "AGENTS.md", "src/moved.py")
        self.assertEqual(self.scope_check("builder"), 1)

    def test_agent_commit_caught_with_base(self):
        self.write("src/rounds/views.py", "y\n")
        self.git("commit", "-q", "-am", "agent commit")
        self.assertEqual(self.scope_check("builder", self.base), 1)

    def test_dirty_baseline_only_charges_new_content_to_role(self):
        self.write("AGENTS.md", "existing human edits\n")
        baseline = self.snapshot_file()
        self.write("src/rounds/views.py", "builder edits\n")
        self.assertEqual(self.snapshot_check(baseline, "builder"), 0)
        self.write("AGENTS.md", "changed by builder\n")
        self.assertEqual(self.snapshot_check(baseline, "builder"), 1)

    def test_review_candidate_detects_untracked_and_index_changes(self):
        self.write("src/new.py")
        baseline = self.snapshot_file()
        self.assertEqual(self.snapshot_check(baseline), 0)
        self.write("src/new.py", "changed\n")
        self.assertEqual(self.snapshot_check(baseline), 1)
        self.write("src/new.py")
        self.git("add", "src/new.py")
        self.assertEqual(self.snapshot_check(baseline), 1)

    def test_snapshot_skips_secret_env_and_rejects_other_repository(self):
        self.write(".env", "synthetic secret\n")
        self.write(".env.example", "EMPTY=\n")
        snapshot = check_scope.candidate_snapshot(self.root)
        self.assertNotIn(".env", snapshot["files"])
        self.assertIn(".env.example", snapshot["files"])
        baseline = self.snapshot_file()
        with self.assertRaises(ValueError):
            check_scope.load_snapshot(baseline, self.root.parent)

    def test_snapshot_detects_deletion_and_moved_head(self):
        baseline = self.snapshot_file()
        (self.root / "src/rounds/views.py").unlink()
        self.assertEqual(self.snapshot_check(baseline), 1)
        self.git("commit", "-q", "-am", "delete")
        self.assertEqual(self.snapshot_check(baseline, "builder"), 1)

    def test_role_staging_is_caught_without_content_change(self):
        self.write("src/new.py")
        baseline = self.snapshot_file()
        self.git("add", "src/new.py")
        self.assertEqual(self.snapshot_check(baseline, "builder"), 1)

    def test_redirected_parent_is_rejected_before_reading(self):
        # The index still names src/rounds/views.py after its parent is replaced.
        (self.root / "src/rounds/views.py").unlink()
        (self.root / "src/rounds").rmdir()
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside)
            (target / "views.py").write_text(
                "synthetic external secret", encoding="utf-8"
            )
            try:
                os.symlink(target, self.root / "src/rounds", target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory symlink unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "redirected parent"):
                check_scope.candidate_snapshot(self.root)

    def test_windows_reparse_parent_is_rejected_without_reading(self):
        real_lstat = Path.lstat

        def directory_metadata(path):
            if path == self.root / "src/rounds":
                return SimpleNamespace(
                    st_mode=stat.S_IFDIR,
                    st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
                )
            return real_lstat(path)

        with (
            patch.object(Path, "lstat", directory_metadata),
            self.assertRaisesRegex(ValueError, "redirected parent"),
        ):
            check_scope.candidate_snapshot(self.root)


if __name__ == "__main__":
    unittest.main()

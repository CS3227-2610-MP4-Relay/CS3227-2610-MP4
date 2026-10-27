"""Check #66 project defaults and native command decisions without executing GitHub."""

import ast
import json
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from check_scope import ROOT
from test_adapters import GITHUB_CHANGING_COMMANDS

RULES = ROOT / ".codex" / "rules" / "github.rules"
CODEX = shutil.which("codex")


class CodexApprovalConfigTest(unittest.TestCase):
    def test_project_defaults_route_approvals_to_a_person(self):
        with (ROOT / ".codex" / "config.toml").open("rb") as file:
            config = tomllib.load(file)
        self.assertEqual(config["approval_policy"], "on-request")
        self.assertEqual(config["approvals_reviewer"], "user")
        self.assertEqual(config["sandbox_mode"], "workspace-write")
        self.assertIs(config["sandbox_workspace_write"]["network_access"], False)

    def test_rules_are_literal_prompt_prefixes_without_allow_exceptions(self):
        """CI checks the committed policy shape even when Codex is not installed."""
        statements = ast.parse(RULES.read_text(encoding="utf-8")).body
        patterns = []
        for statement in statements:
            self.assertIsInstance(statement, ast.Expr)
            call = statement.value
            self.assertIsInstance(call, ast.Call)
            self.assertIsInstance(call.func, ast.Name)
            self.assertEqual(call.func.id, "prefix_rule")
            self.assertFalse(call.args)
            fields = {item.arg: ast.literal_eval(item.value) for item in call.keywords}
            self.assertEqual(fields["decision"], "prompt")
            self.assertTrue(fields["justification"].strip())
            self.assertTrue(fields["match"])
            self.assertTrue(fields["not_match"])
            patterns.append(fields["pattern"])
        self.assertEqual(patterns, [[["gh", "gh.exe"]], [["git", "git.exe"], "push"]])


@unittest.skipUnless(CODEX, "Codex CLI unavailable; native evaluator not exercised")
class CodexNativeApprovalTest(unittest.TestCase):
    def evaluate(self, command, extra_rules=None):
        """Pass argv to the evaluator; never run the command being classified."""
        args = [CODEX, "execpolicy", "check", "--rules", str(RULES)]
        if extra_rules:
            args.extend(["--rules", str(extra_rules)])
        result = subprocess.run(
            [*args, "--", *command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        return json.loads(result.stdout)

    def test_direct_github_commands_prompt_including_delivery_and_reads(self):
        commands = [command.split() for command in GITHUB_CHANGING_COMMANDS]
        commands.extend(
            [
                ["gh", "pr", "edit", "999999", "--title", "probe"],
                ["gh", "pr", "edit", "999999", "-b", "probe"],
                ["gh", "pr", "edit", "999999", "-Bmain"],
                ["gh", "pr", "edit", "999999", "-m", "probe"],
                ["gh", "-Rexample/example", "pr", "ready", "999999"],
                ["gh", "pr", "--repo=example/example", "ready", "999999"],
                ["gh", "api", "--method", "PATCH", "repos/example/example"],
                ["gh", "pr", "view", "999999"],
                ["gh", "alias-defined-by-user"],
                ["gh", "future-command"],
            ]
        )
        for command in commands:
            for executable in (command[0], command[0] + ".exe"):
                with self.subTest(command=command, executable=executable):
                    result = self.evaluate([executable, *command[1:]])
                    self.assertEqual(result.get("decision"), "prompt")

    def test_unmatched_forms_are_not_reported_as_covered(self):
        for command in (
            ["git", "status"],
            ["git.exe", "diff"],
            ["git", "-C", "example", "push"],
            ["GH", "pr", "ready", "999999"],
            ["/usr/bin/gh", "pr", "ready", "999999"],
            ["powershell", "-Command", "gh pr ready 999999"],
            ["bash", "-lc", "git status && gh pr ready 999999"],
        ):
            with self.subTest(command=command):
                result = self.evaluate(command)
                self.assertEqual(result["matchedRules"], [])
                self.assertNotIn("decision", result)

    def test_prompt_overrides_a_broad_allow_rule(self):
        with tempfile.TemporaryDirectory() as directory:
            allow = Path(directory) / "allow.rules"
            allow.write_text(
                'prefix_rule(pattern = ["gh"], decision = "allow")\n',
                encoding="utf-8",
            )
            result = self.evaluate(["gh", "pr", "ready", "999999"], allow)
        self.assertEqual(result["decision"], "prompt")


if __name__ == "__main__":
    unittest.main()

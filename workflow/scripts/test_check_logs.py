"""Tests for check_logs.py. Run: python -m unittest discover -s workflow/scripts"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_logs


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


GOOD = """# A session

Slice: #1 · Tier: Fast lane · Tool: none · Date: 2026-10-21

Tokens: unavailable; no usage collected.

## Requests

## Agent runs

## Decisions and corrections

## Problems
"""


class LogChecks(unittest.TestCase):
    def test_no_saved_logs_is_valid_for_a_fresh_repo(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(check_logs, "LOGS", Path(folder) / "absent"),
        ):
            self.assertEqual(check_logs.main(), 0)

    def test_a_complete_log_has_no_findings(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "001-a-session.md"
            write(log, GOOD)
            self.assertEqual(check_logs.findings(log), [])

    def test_a_missing_tokens_line_and_section_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "001-a-session.md"
            write(
                log,
                GOOD.replace(
                    "Tokens: unavailable; no usage collected.\n\n", ""
                ).replace("## Problems\n", ""),
            )
            messages = [message for _, message in check_logs.findings(log)]
            self.assertIn("header has no Tokens: line", messages)
            self.assertIn("missing section ## Problems", messages)

    def test_a_name_outside_the_convention_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "notes.md"
            write(log, GOOD)
            messages = [message for _, message in check_logs.findings(log)]
            self.assertIn("file name is not NNN-kebab.md", messages)


if __name__ == "__main__":
    unittest.main()

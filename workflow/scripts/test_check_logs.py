"""Tests for check_logs.py. Run: python -m unittest discover -s workflow/scripts"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_logs


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


GOOD = (
    "# A session\n\n"
    "Slice: #1 · Tier: Fast lane · Tool: none · "
    "Orchestrator model: unavailable (no metadata) · Date: 2026-10-21\n\n"
    "Tokens: unavailable; no usage collected.\n\n"
    "| Agent/source | Input | Cached input | Output | Reasoning output | Total | "
    "Recorded elapsed span |\n"
    "| --- | ---: | ---: | ---: | ---: | ---: | --- |\n"
    "| Orchestrator — unavailable | unavailable | unavailable | unavailable | "
    "unavailable | unavailable | unavailable |\n\n"
    "## Requests\n\n## Agent runs\n\n## Decisions and corrections\n\n## Problems\n"
)

TABLE = GOOD[GOOD.index("| Agent/source") : GOOD.index("## Requests")].rstrip()


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

    def test_missing_or_empty_orchestrator_model_is_reported(self):
        for replacement in ("", "Orchestrator model: "):
            with (
                self.subTest(replacement=replacement),
                tempfile.TemporaryDirectory() as folder,
            ):
                log = Path(folder) / "001-a-session.md"
                write(
                    log,
                    GOOD.replace(
                        "Orchestrator model: unavailable (no metadata)", replacement
                    ),
                )
                messages = [message for _, message in check_logs.findings(log)]
                self.assertIn("header has no orchestrator model value", messages)

    def test_missing_misplaced_or_malformed_token_table_is_reported(self):
        table_lines = TABLE.splitlines()
        invalid = (
            GOOD.replace(TABLE, ""),
            GOOD.replace(TABLE, "").replace("## Requests", "## Requests\n" + TABLE),
            GOOD.replace(TABLE, "Some prose before the table.\n\n" + TABLE),
            GOOD.replace("| Input | Cached input |", "| Cached input | Input |"),
            GOOD.replace(table_lines[1], "| invalid |"),
            GOOD.replace(table_lines[2], ""),
            GOOD.replace(table_lines[2], "| Orchestrator | 0 |"),
            GOOD.replace("| Orchestrator — unavailable |", "| |"),
        )
        for number, text in enumerate(invalid):
            with self.subTest(case=number), tempfile.TemporaryDirectory() as folder:
                log = Path(folder) / "001-a-session.md"
                write(log, text)
                messages = [message for _, message in check_logs.findings(log)]
                self.assertTrue(any("token table" in message for message in messages))


if __name__ == "__main__":
    unittest.main()

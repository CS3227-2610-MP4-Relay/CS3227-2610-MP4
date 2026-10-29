"""Regression checks for shared usage and incomplete selected-source accounting."""

import contextlib
import io
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import resource_usage as usage
from test_resource_usage import START, codex, counts, meta


def turn(identity, second=0):
    return {
        "type": "turn_context",
        "timestamp": (START + timedelta(seconds=second)).isoformat(),
        "payload": {"turn_id": identity},
    }


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def write(self, name, records):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
        )
        return path

    def snapshot(self, paths, second):
        return usage.collect(paths, now=START + timedelta(seconds=second))

    def test_rewritten_shared_turns_are_counted_once(self):
        parent = self.write("parent.jsonl", [meta()])
        baseline = self.snapshot([parent], 0)
        self.write(
            parent.name,
            [
                meta(),
                turn("shared"),
                codex(counts(100, 10), second=1),
                codex(counts(200, 20), counts(100, 10), second=2),
            ],
        )
        for copied_second in (1, 10):
            with self.subTest(copied_second=copied_second):
                child = self.write(
                    "child.jsonl",
                    [
                        meta(
                            "child", "parent", timestamp=START + timedelta(seconds=10)
                        ),
                        turn("shared", copied_second),
                        codex(counts(100, 10), second=copied_second),
                        codex(
                            counts(200, 20), counts(100, 10), second=copied_second + 1
                        ),
                        turn("new", 12),
                        codex(counts(225, 23), counts(25, 3), second=12),
                    ],
                )
                result = usage.report(self.snapshot([parent, child], 13), baseline)
                self.assertEqual(result["tokens"]["total_tokens"], 248)
                self.assertEqual(
                    sum(r["tokens"]["total_tokens"] for r in result["sessions"]), 248
                )

    def test_independent_turns_with_equal_counters_remain_independent(self):
        paths = [
            self.write(
                name + ".jsonl",
                [meta(name), turn(name), codex(counts(100, 10), second=1)],
            )
            for name in ("one", "two")
        ]
        baseline_paths = [self.write("empty.jsonl", [meta("empty")])]
        baseline = self.snapshot(baseline_paths, 0)
        result = usage.report(self.snapshot([*baseline_paths, *paths], 2), baseline)
        self.assertEqual(result["tokens"]["total_tokens"], None)  # empty stays unknown
        self.assertEqual(
            sum(r["tokens"]["total_tokens"] or 0 for r in result["sessions"]), 220
        )

    def test_changed_identity_recovers_proven_baseline_with_or_without_old_file(self):
        initial = [meta(), turn("shared"), codex(counts(100, 10), second=1)]
        parent = self.write("parent.jsonl", initial)
        baseline = self.snapshot([parent], 5)
        changed = self.write(
            "changed.jsonl",
            [
                meta("changed"),
                turn("shared", 6),
                codex(counts(100, 10), second=6),
                turn("fresh", 7),
                codex(counts(150, 15), counts(50, 5), second=7),
            ],
        )
        for paths in ([parent, changed], [changed]):
            with self.subTest(retained_old=len(paths) == 2):
                result = usage.report(self.snapshot(paths, 8), baseline)
                self.assertEqual(result["tokens"]["total_tokens"], 55)
                self.assertNotIn(
                    "added_session_has_no_task_start_baseline", result["warnings"]
                )

    def test_new_work_on_partially_copied_same_turn_uses_range_difference(self):
        parent = self.write(
            "parent.jsonl", [meta(), turn("shared"), codex(counts(100, 10), second=1)]
        )
        baseline = self.snapshot([parent], 5)
        changed = self.write(
            "changed.jsonl",
            [
                meta("changed"),
                turn("shared", 6),
                codex(counts(150, 15), counts(50, 5), second=6),
            ],
        )
        result = usage.report(self.snapshot([parent, changed], 7), baseline)
        self.assertEqual(result["tokens"]["total_tokens"], 55)
        with self.assertRaisesRegex(ValueError, "baseline sessions missing"):
            usage.report(self.snapshot([changed], 7), baseline)

    def test_old_unbaselined_extra_work_is_not_recovered_as_new_usage(self):
        parent = self.write(
            "parent.jsonl", [meta(), turn("shared"), codex(counts(100, 10), second=1)]
        )
        baseline = self.snapshot([parent], 5)
        changed = self.write(
            "changed.jsonl",
            [
                meta("changed"),
                turn("shared", 1),
                codex(counts(100, 10), second=1),
                turn("old-extra", 2),
                codex(counts(150, 15), counts(50, 5), second=2),
            ],
        )
        result = usage.report(self.snapshot([parent, changed], 7), baseline)
        self.assertIsNone(result["tokens"]["total_tokens"])
        self.assertIn("added_session_has_no_task_start_baseline", result["warnings"])

    def test_related_legacy_copied_history_is_unavailable_instead_of_double_counted(
        self,
    ):
        parent = self.write("parent.jsonl", [meta()])
        baseline = self.snapshot([parent], 0)
        self.write(parent.name, [meta(), codex(counts(100, 10), second=1)])
        child = self.write(
            "child.jsonl",
            [
                meta("child", "parent", timestamp=START + timedelta(seconds=10)),
                codex(counts(100, 10), second=10),
                codex(counts(125, 13), counts(25, 3), second=11),
            ],
        )
        result = usage.report(self.snapshot([parent, child], 12), baseline)
        self.assertIsNone(result["tokens"]["total_tokens"])
        self.assertIn("codex_shared_history_unresolved", result["warnings"])

    def test_new_provenance_validation_suppresses_arbitrary_content(self):
        path = self.write(
            "private-source.jsonl",
            [meta(), turn("shared"), codex(counts(10, 1), second=1)],
        )
        valid = self.snapshot([path], 2)
        key = next(iter(valid["sessions"]))
        self.assertTrue(valid["sessions"][key].get("provenance"))
        turn_key = next(iter(valid["sessions"][key]["provenance"]))
        for bad in (
            "SECRET",
            [],
            {"PRIVATE-ID": {}},
            {turn_key: {"ranges": {"input_tokens": [[-1, 5]]}}},
        ):
            with self.subTest(bad=bad):
                baseline = json.loads(json.dumps(valid))
                baseline["sessions"][key]["provenance"] = bad
                baseline_path = self.root / "baseline.json"
                baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
                output, error = io.StringIO(), io.StringIO()
                with (
                    contextlib.redirect_stdout(output),
                    contextlib.redirect_stderr(error),
                ):
                    self.assertEqual(
                        usage.main(
                            [
                                "report",
                                "--codex",
                                str(path),
                                "--baseline",
                                str(baseline_path),
                            ]
                        ),
                        1,
                    )
                rendered = output.getvalue() + error.getvalue()
                for private in ("SECRET", "PRIVATE-ID", str(path), "Traceback"):
                    self.assertNotIn(private, rendered)

    def test_native_truncation_cannot_look_like_zero_usage(self):
        path = self.write(
            "source.jsonl", [meta(), turn("shared"), codex(counts(100, 10), second=1)]
        )
        baseline = self.snapshot([path], 2)
        self.write(path.name, [meta(), turn("shared"), codex(counts(10, 1), second=3)])
        result = usage.report(self.snapshot([path], 4), baseline)
        self.assertIsNone(result["tokens"]["total_tokens"])
        self.assertIn("source_truncated_or_replaced_since_baseline", result["warnings"])

    def test_legacy_baseline_accepts_optional_native_extension(self):
        path = self.write(
            "source.jsonl", [meta(), turn("shared"), codex(counts(100, 10), second=1)]
        )
        baseline = self.snapshot([path], 2)
        for session in baseline["sessions"].values():
            for field in ("provenance", "usage_fingerprints", "ancestor", "tree"):
                session.pop(field, None)
        self.write(
            path.name,
            [
                meta(),
                turn("shared"),
                codex(counts(100, 10), second=1),
                codex(counts(150, 15), counts(50, 5), second=3),
            ],
        )
        result = usage.report(self.snapshot([path], 4), baseline)
        self.assertEqual(result["tokens"]["total_tokens"], 55)

    def test_legacy_parent_and_native_copy_do_not_double_count(self):
        parent = self.write("parent.jsonl", [meta(), codex(counts(100, 10), second=1)])
        baseline = self.snapshot([parent], 2)
        child = self.write(
            "child.jsonl",
            [
                meta("child", "parent", timestamp=START + timedelta(seconds=3)),
                turn("unknown-parent-turn", 3),
                codex(counts(100, 10), second=3),
            ],
        )
        result = usage.report(self.snapshot([parent, child], 4), baseline)
        self.assertIsNone(result["tokens"]["total_tokens"])
        self.assertIn("codex_shared_history_unresolved", result["warnings"])


if __name__ == "__main__":
    unittest.main()

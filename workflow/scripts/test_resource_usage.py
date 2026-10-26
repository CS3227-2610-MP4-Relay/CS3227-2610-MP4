"""Synthetic telemetry checks; no user histories or network access required."""

import contextlib
import io
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

import resource_usage as usage

START = datetime(2026, 10, 25, 10, tzinfo=UTC)


def counts(input_tokens, output_tokens, cached=0, reasoning=0):
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached,
        "cache_write_input_tokens": 0,
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning,
        "total_tokens": input_tokens + output_tokens,
    }


def meta(identity="parent", parent=None, project=".", timestamp=None):
    return {
        "type": "session_meta",
        "payload": {
            "id": identity,
            "cwd": str(Path(project).resolve()),
            "parent_thread_id": parent,
            "timestamp": (timestamp or START).isoformat(),
            "base_instructions": "SECRET PROMPT MUST NEVER BE EMITTED",
        },
    }


def codex(total, last=None, second=0):
    return {
        "timestamp": (START + timedelta(seconds=second)).isoformat(),
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"total_token_usage": total, "last_token_usage": last or total},
        },
    }


def claude(identity="m1", output=5, **extra):
    return {
        "timestamp": START.isoformat(),
        "sessionId": "claude-session",
        "type": "assistant",
        "requestId": "request-" + identity,
        "message": {
            "id": identity,
            "content": "SECRET ASSISTANT BODY MUST NEVER BE EMITTED",
            "usage": {
                "input_tokens": 10,
                "cache_read_input_tokens": 20,
                "cache_creation_input_tokens": 30,
                "output_tokens": output,
            },
        },
        **extra,
    }


class ResourceUsageTests(unittest.TestCase):
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

    def tokens(self, snapshot):
        return next(iter(snapshot["sessions"].values()))["tokens"]

    def test_cumulative_snapshots_duplicates_and_resets(self):
        path = self.write(
            "codex.jsonl",
            [
                meta(),
                codex(counts(100, 10, cached=80)),
                codex(counts(100, 10, cached=80), second=1),
                codex(counts(150, 15, cached=100), second=2),
                codex(counts(20, 2), second=3),
                codex(counts(35, 4), second=4),
            ],
        )
        result = usage.collect([path])
        self.assertEqual(self.tokens(result)["input_tokens"], 185)
        self.assertEqual(self.tokens(result)["output_tokens"], 19)
        self.assertIn("codex_counter_reset", result["warnings"])

    def test_fork_does_not_recount_inherited_cumulative_history(self):
        path = self.write(
            "fork.jsonl",
            [
                meta("child", "parent"),
                codex(counts(1050, 105), counts(50, 5)),
                codex(counts(1100, 110), counts(50, 5), second=1),
            ],
        )
        result = usage.collect([path])
        self.assertEqual(self.tokens(result)["total_tokens"], 110)
        self.assertIn("codex_inherited_or_missing_initial_history", result["warnings"])

    def test_duplicate_codex_session_files_are_merged(self):
        records = [meta(), codex(counts(10, 3))]
        first = self.write("first.jsonl", records)
        second = self.write("copy.jsonl", records + [codex(counts(20, 5), second=1)])
        result = usage.collect([first, second, first])
        self.assertEqual(len(result["sessions"]), 1)
        self.assertEqual(self.tokens(result)["total_tokens"], 25)

    def test_codex_export_turns_and_ambiguous_mixed_events(self):
        turn = {"type": "turn.completed", "usage": counts(10, 2)}
        path = self.write(
            "export.jsonl", [{"type": "thread.started", "thread_id": "t"}, turn]
        )
        self.assertEqual(self.tokens(usage.collect([path]))["total_tokens"], 12)
        path = self.write("export.jsonl", [meta(), codex(counts(10, 2)), turn])
        result = usage.collect([path])
        self.assertTrue(all(value is None for value in self.tokens(result).values()))
        self.assertIn("mixed_codex_telemetry_is_ambiguous", result["warnings"])

    def test_multiple_export_segments_cannot_be_deduplicated_by_line_or_amount(self):
        header = {"type": "thread.started", "thread_id": "same-thread"}
        turn = {"type": "turn.completed", "usage": counts(10, 2)}
        first = self.write("first.jsonl", [header, turn])
        shifted_copy = self.write(
            "copy.jsonl", [header, {"type": "turn.started"}, turn]
        )
        same_index_segment = self.write("segment.jsonl", [header, turn])
        for other in (shifted_copy, same_index_segment):
            with self.subTest(other=other.name):
                result = usage.collect([first, other])
                self.assertIsNone(self.tokens(result)["total_tokens"])
                self.assertIn(
                    "multiple_codex_exports_are_ambiguous", result["warnings"]
                )

    def test_identical_codex_export_turns_are_distinct_work(self):
        turn = {"type": "turn.completed", "usage": counts(10, 2)}
        path = self.write(
            "turns.jsonl",
            [
                {"type": "thread.started", "thread_id": "t"},
                turn,
                turn,
            ],
        )
        self.assertEqual(self.tokens(usage.collect([path]))["total_tokens"], 24)

    def test_codex_export_missing_turn_usage_invalidates_session_and_report(self):
        header = {"type": "thread.started", "thread_id": "t"}
        complete = {"type": "turn.completed", "usage": counts(10, 2)}
        path = self.write("export.jsonl", [header])
        baseline = usage.collect([path], now=START)
        for missing in (None, {}, "invalid"):
            for first in (True, False):
                with self.subTest(usage=missing, missing_first=first):
                    incomplete = {"type": "turn.completed"}
                    if missing is not None:
                        incomplete["usage"] = missing
                    turns = [incomplete, complete] if first else [complete, incomplete]
                    self.write("export.jsonl", [header, *turns])
                    current = usage.collect([path], now=START + timedelta(seconds=1))
                    self.assertTrue(
                        all(value is None for value in self.tokens(current).values())
                    )
                    self.assertIn("codex_turn_usage_incomplete", current["warnings"])
                    report = usage.report(current, baseline)
                    self.assertIsNone(report["tokens"]["total_tokens"])
                    self.assertIn("codex_turn_usage_incomplete", report["warnings"])

    def test_copied_parent_history_is_not_charged_to_child(self):
        path = self.write(
            "child.jsonl",
            [
                meta("child", "parent", timestamp=START + timedelta(seconds=5)),
                codex(counts(1000, 100)),
                codex(counts(1020, 102), counts(20, 2), second=6),
            ],
        )
        result = usage.collect([path])
        self.assertEqual(self.tokens(result)["total_tokens"], 22)
        self.assertIn("codex_copied_history_excluded", result["warnings"])

    def test_empty_start_baseline_differs_from_missing_runtime_telemetry(self):
        path = self.write("new.jsonl", [meta()])
        baseline = usage.collect([path], now=START)
        self.assertIsNone(self.tokens(baseline)["total_tokens"])
        self.write("new.jsonl", [meta(), codex(counts(20, 2), second=1)])
        result = usage.report(usage.collect([path], now=START), baseline)
        self.assertEqual(result["tokens"]["total_tokens"], 22)
        self.write(
            "new.jsonl",
            [
                meta(),
                {
                    "type": "event_msg",
                    "payload": {"type": "agent_message"},
                },
            ],
        )
        unsupported = usage.collect([path], now=START)
        self.write("new.jsonl", [meta(), codex(counts(20, 2), second=1)])
        result = usage.report(usage.collect([path], now=START), unsupported)
        self.assertIsNone(result["tokens"]["total_tokens"])

    def test_claude_session_identity_may_appear_after_initial_record(self):
        records = [{"type": "queue-operation"}, claude()]
        first = self.write("first.jsonl", records)
        second = self.write("second.jsonl", records)
        result = usage.collect(claude_paths=[first, second])
        self.assertEqual(len(result["sessions"]), 1)
        self.assertEqual(self.tokens(result)["total_tokens"], 65)

    def test_claude_duplicates_streaming_updates_cache_and_separate_agents(self):
        first = self.write("claude.jsonl", [claude(), claude(output=8), claude("m2")])
        copy = self.write("copy.jsonl", [claude()])
        child = self.write("subagents/agent-a.jsonl", [claude("m3", agentId="a")])
        result = usage.collect(claude_paths=[first, copy, child])
        self.assertEqual(len(result["sessions"]), 2)
        parent = next(
            session
            for session in result["sessions"].values()
            if session["observations"] == 2
        )
        self.assertEqual(parent["tokens"]["input_tokens"], 120)
        self.assertEqual(parent["tokens"]["cached_input_tokens"], 40)
        self.assertEqual(parent["tokens"]["cache_write_input_tokens"], 60)
        self.assertEqual(parent["tokens"]["output_tokens"], 13)
        self.assertIsNone(parent["tokens"]["reasoning_output_tokens"])

    def test_partial_claude_output_update_recomputes_message_total(self):
        partial = claude(output=8)
        partial["message"]["usage"] = {"output_tokens": 8}
        path = self.write("partial-output.jsonl", [claude(), partial])
        tokens = self.tokens(usage.collect(claude_paths=[path]))
        self.assertEqual(tokens["input_tokens"], 60)
        self.assertEqual(tokens["output_tokens"], 8)
        self.assertEqual(tokens["total_tokens"], 68)

    def test_claude_missing_message_usage_invalidates_session_and_report(self):
        path = self.write("claude.jsonl", [claude()])
        baseline = usage.collect(claude_paths=[path], now=START)
        for missing in (None, {}, "invalid"):
            for first in (True, False):
                with self.subTest(usage=missing, missing_first=first):
                    incomplete = claude("m2")
                    if missing is None:
                        incomplete["message"].pop("usage")
                    else:
                        incomplete["message"]["usage"] = missing
                    records = (
                        [incomplete, claude()] if first else [claude(), incomplete]
                    )
                    self.write("claude.jsonl", records)
                    current = usage.collect(
                        claude_paths=[path], now=START + timedelta(seconds=1)
                    )
                    self.assertTrue(
                        all(value is None for value in self.tokens(current).values())
                    )
                    self.assertIn(
                        "claude_message_usage_incomplete", current["warnings"]
                    )
                    report = usage.report(current, baseline)
                    self.assertIsNone(report["tokens"]["total_tokens"])
                    self.assertIn("claude_message_usage_incomplete", report["warnings"])

    def test_claude_missing_fragment_can_be_completed_by_same_message(self):
        incomplete = claude()
        incomplete["message"].pop("usage")
        for records in ([incomplete, claude()], [claude(), incomplete]):
            with self.subTest(records=records):
                path = self.write("claude.jsonl", records)
                current = usage.collect(claude_paths=[path])
                self.assertEqual(self.tokens(current)["total_tokens"], 65)
                self.assertNotIn("claude_message_usage_incomplete", current["warnings"])

    def test_claude_unidentified_message_does_not_leave_a_numeric_subtotal(self):
        unidentified = claude("m2")
        unidentified["message"].pop("id")
        path = self.write("claude.jsonl", [claude(), unidentified])
        current = usage.collect(claude_paths=[path])
        self.assertTrue(all(value is None for value in self.tokens(current).values()))
        self.assertIn("claude_usage_without_message_id_skipped", current["warnings"])
        self.assertIn("claude_message_usage_incomplete", current["warnings"])

    def test_partial_claude_cache_update_recomputes_input_and_message_total(self):
        partial = claude()
        partial["message"]["usage"] = {"cache_read_input_tokens": 22}
        path = self.write("partial-cache.jsonl", [claude(), partial])
        tokens = self.tokens(usage.collect(claude_paths=[path]))
        self.assertEqual(tokens["cached_input_tokens"], 22)
        self.assertEqual(tokens["input_tokens"], 62)
        self.assertEqual(tokens["total_tokens"], 67)

    def test_missing_telemetry_is_null_and_incomplete_json_is_reported(self):
        path = self.write(
            "broken.jsonl",
            [
                meta(),
                {"type": "response_item", "payload": {"role": "assistant"}},
            ],
        )
        with path.open("a", encoding="utf-8") as source:
            source.write('{"unfinished":')
        result = usage.collect([path])
        self.assertTrue(all(value is None for value in self.tokens(result).values()))
        self.assertIn("malformed_or_incomplete_jsonl", result["warnings"])
        self.assertIn("session_has_no_supported_usage", result["warnings"])

    def test_missing_counter_is_not_silently_treated_as_zero(self):
        partial = counts(20, 2)
        partial.pop("cached_input_tokens")
        path = self.write(
            "partial.jsonl", [meta(), codex(counts(10, 1)), codex(partial, second=1)]
        )
        self.assertIsNone(self.tokens(usage.collect([path]))["cached_input_tokens"])
        record = claude()
        record["message"]["usage"].pop("cache_creation_input_tokens")
        path = self.write("claude-partial.jsonl", [record])
        result = usage.collect(claude_paths=[path])
        self.assertIsNone(self.tokens(result)["input_tokens"])
        self.assertEqual(self.tokens(result)["output_tokens"], 5)

    def test_baseline_excludes_previous_work_and_tracks_elapsed_context(self):
        path = self.write("task.jsonl", [meta(), codex(counts(1000, 100))])
        baseline = usage.collect([path], now=START + timedelta(seconds=1))
        with path.open("a", encoding="utf-8") as source:
            source.write(json.dumps(codex(counts(1100, 120), second=2)) + "\n")
        current = usage.collect([path], now=START + timedelta(seconds=11))
        result = usage.report(current, baseline, retries=2, repair_rounds=1)
        self.assertEqual(result["tokens"]["total_tokens"], 120)
        self.assertEqual(result["elapsed_seconds"], 10)
        self.assertEqual((result["retries"], result["repair_rounds"]), (2, 1))
        self.assertIsNone(usage.report(current, baseline)["retries"])

    def test_new_child_after_baseline_counts_but_added_history_is_unavailable(self):
        parent = self.write("parent.jsonl", [meta(), codex(counts(100, 10))])
        baseline = usage.collect([parent], now=START + timedelta(seconds=1))
        child = self.write(
            "child.jsonl",
            [
                meta("new", "parent", timestamp=START + timedelta(seconds=2)),
                codex(counts(20, 2), second=3),
            ],
        )
        result = usage.report(
            usage.collect([parent, child], now=START + timedelta(seconds=4)), baseline
        )
        self.assertEqual(result["tokens"]["total_tokens"], 22)
        old = self.write("historical.jsonl", [meta("old"), codex(counts(500, 50))])
        result = usage.report(
            usage.collect([parent, old], now=START + timedelta(seconds=4)), baseline
        )
        self.assertIsNone(result["tokens"]["total_tokens"])
        self.assertIn("added_session_has_no_task_start_baseline", result["warnings"])

    def test_missing_source_and_truncated_source_cannot_look_like_savings(self):
        path = self.write("task.jsonl", [meta(), codex(counts(100, 10))])
        baseline = usage.collect([path], now=START)
        with self.assertRaisesRegex(ValueError, "baseline sessions missing"):
            usage.report(usage.collect(now=START), baseline)
        path = self.write("task.jsonl", [meta(), codex(counts(10, 1))])
        result = usage.report(usage.collect([path], now=START), baseline)
        self.assertIsNone(result["tokens"]["input_tokens"])
        self.assertIn("source_truncated_or_replaced_since_baseline", result["warnings"])

    def test_child_discovery_is_bounded_by_ancestry_and_project(self):
        parent = self.write("parent.jsonl", [meta(project=self.root)])
        child = self.write("child.jsonl", [meta("child", "parent", self.root)])
        grandchild = self.write("grandchild.jsonl", [meta("grand", "child", self.root)])
        self.write("unrelated.jsonl", [meta("other", project=self.root)])
        self.write(
            "wrong-project.jsonl", [meta("wrong", "parent", self.root / "elsewhere")]
        )
        self.assertEqual(
            set(usage.discover_children([parent], self.root, self.root)),
            {parent, child, grandchild},
        )

    def test_cli_is_read_only_and_emits_no_prompt_body_or_path(self):
        path = self.write("secret-name.jsonl", [meta(), codex(counts(10, 1))])
        original = path.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(usage.main(["snapshot", "--codex", str(path)]), 0)
        rendered = output.getvalue()
        self.assertNotIn("SECRET", rendered)
        self.assertNotIn(str(path), rendered)
        self.assertNotIn("parent", rendered)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(json.loads(rendered)["kind"], "usage_snapshot")

    def test_cli_rejects_invalid_baseline_without_echoing_its_contents(self):
        path = self.write("source.jsonl", [meta(), codex(counts(10, 1))])
        baseline = self.write("invalid.json", [{"secret": "DO NOT ECHO"}])
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            self.assertEqual(
                usage.main(
                    ["report", "--codex", str(path), "--baseline", str(baseline)]
                ),
                1,
            )
        self.assertNotIn("DO NOT ECHO", error.getvalue())
        self.assertNotIn(str(path), error.getvalue())

    def test_invalid_baseline_session_rows_return_clean_errors(self):
        path = self.write("source.jsonl", [meta(), codex(counts(10, 1))])
        valid = usage.collect([path], now=START)
        key = next(iter(valid["sessions"]))
        malformed = [None, [], {"tokens": None}, {"tokens": []}]
        bad_counter = json.loads(json.dumps(valid["sessions"][key]))
        bad_counter["tokens"]["input_tokens"] = -1
        malformed.append(bad_counter)
        for row in malformed:
            with self.subTest(row=row):
                snapshot = json.loads(json.dumps(valid))
                snapshot["sessions"][key] = row
                baseline = self.root / "baseline.json"
                baseline.write_text(json.dumps(snapshot), encoding="utf-8")
                error = io.StringIO()
                with contextlib.redirect_stderr(error):
                    self.assertEqual(
                        usage.main(
                            [
                                "report",
                                "--codex",
                                str(path),
                                "--baseline",
                                str(baseline),
                            ]
                        ),
                        1,
                    )
                self.assertNotIn("Traceback", error.getvalue())
                self.assertNotIn(str(path), error.getvalue())

    def test_snapshot_warning_validation_never_emits_arbitrary_baseline_text(self):
        path = self.write("source.jsonl", [meta(), codex(counts(10, 1))])
        valid = usage.collect([path], now=START)
        secret = "TOP_SECRET_WARNING_CONTENT"
        private_path = str(self.root / "private-history")
        invalid = [[secret], [private_path], secret, {secret: 1}, [1], [None], None]
        for warnings in invalid:
            with self.subTest(warnings=warnings):
                snapshot = json.loads(json.dumps(valid))
                snapshot["warnings"] = warnings
                baseline = self.root / "baseline.json"
                baseline.write_text(json.dumps(snapshot), encoding="utf-8")
                output = io.StringIO()
                error = io.StringIO()
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
                                str(baseline),
                            ]
                        ),
                        1,
                    )
                rendered = output.getvalue() + error.getvalue()
                self.assertNotIn(secret, rendered)
                self.assertNotIn(private_path, rendered)
                self.assertNotIn("Traceback", rendered)
                with self.assertRaises(ValueError):
                    usage.report(snapshot, valid)

    def test_every_known_generated_warning_code_is_accepted(self):
        path = self.write("source.jsonl", [meta(), codex(counts(10, 1))])
        snapshot = usage.collect([path], now=START)
        with path.open("a", encoding="utf-8") as source:
            source.write('{"unfinished":')
        generated = usage.collect([path], now=START)
        result = usage.report(generated, snapshot)
        self.assertIn("malformed_or_incomplete_jsonl", result["warnings"])
        for code in usage.WARNING_CODES:
            with self.subTest(code=code):
                baseline = json.loads(json.dumps(snapshot))
                baseline["warnings"] = [code]
                self.assertIn(code, usage.report(snapshot, baseline)["warnings"])

    def test_invalid_codex_metadata_identity_returns_no_path_traceback(self):
        for identity in (123, 0, None, [], {"secret": "private"}, ""):
            for record in (
                {"type": "session_meta", "payload": {"id": identity}},
                {"type": "thread.started", "thread_id": identity},
            ):
                with self.subTest(identity=identity, kind=record["type"]):
                    path = self.write("private-source.jsonl", [record])
                    output = io.StringIO()
                    error = io.StringIO()
                    with (
                        contextlib.redirect_stdout(output),
                        contextlib.redirect_stderr(error),
                    ):
                        self.assertEqual(
                            usage.main(["snapshot", "--codex", str(path)]), 1
                        )
                    rendered = output.getvalue() + error.getvalue()
                    self.assertNotIn(str(path), rendered)
                    self.assertNotIn("Traceback", rendered)
                    self.assertNotIn("private", rendered)


if __name__ == "__main__":
    unittest.main()

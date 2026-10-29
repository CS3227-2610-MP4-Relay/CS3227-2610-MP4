"""Reproduce #83 using synthetic telemetry; characterize, do not repair, behavior.

Run by file path. No real session files, network, or credentials are accessed.
Assertions pin observations of the collector investigated in the linked report;
they are not acceptance criteria for a future accounting implementation.
"""

import json
import tempfile
from datetime import timedelta
from pathlib import Path

import resource_usage as usage
from test_resource_usage import START, codex, counts, meta


def _write(root, name, records):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8"
    )
    return path


def _snapshot(paths, second):
    return usage.collect(paths, now=START + timedelta(seconds=second))


def _check(results, case, actual, expected):
    if actual != expected:
        raise AssertionError(f"{case}: observation changed: {actual!r} != {expected!r}")
    results.append({"case": case, **actual})


def _measurement(report):
    return {"total": report["tokens"]["total_tokens"], "warnings": report["warnings"]}


def _forks(root, results):
    parent = _write(root, "parent.jsonl", [meta()])
    baseline = _snapshot([parent], 0)
    history = [
        codex(counts(100, 10), second=1),
        codex(counts(200, 20), counts(100, 10), second=2),
    ]
    _write(root, parent.name, [meta(), *history])
    header = meta("fork", "parent", timestamp=START + timedelta(seconds=10))
    fresh = codex(counts(225, 23), counts(25, 3), second=12)
    rewritten = [
        codex(counts(100, 10), second=10),
        codex(counts(200, 20), counts(100, 10), second=11),
    ]
    child = _write(root, "fork.jsonl", [header, *rewritten, fresh])
    # Unique work is the parent's 220 plus the child's new 28, not 468.
    actual = usage.report(_snapshot([parent, child], 13), baseline)
    _check(
        results,
        "rewritten_fork_overlap",
        _measurement(actual),
        {"total": 468, "warnings": []},
    )

    _write(root, child.name, [header, *history, fresh])
    actual = usage.report(_snapshot([parent, child], 13), baseline)
    _check(
        results,
        "preserved_fork_timestamps",
        _measurement(actual),
        {
            "total": 248,
            "warnings": [
                "codex_copied_history_excluded",
                "codex_inherited_or_missing_initial_history",
            ],
        },
    )

    # Equal counters alone do not establish shared work or ancestry.
    independent = _write(root, "independent.jsonl", [meta("independent"), *history])
    actual = usage.report(_snapshot([parent, independent], 13), baseline)
    _check(
        results,
        "independent_equal_counters",
        _measurement(actual),
        {"total": 440, "warnings": []},
    )


def _continuations(root, results):
    initial = [meta(), codex(counts(100, 10), second=1)]
    parent = _write(root, "original.jsonl", initial)
    baseline = _snapshot([parent], 5)
    fresh = codex(counts(150, 15), counts(50, 5), second=6)
    same = _write(root, "same-id.jsonl", [*initial, fresh])
    actual = usage.report(_snapshot([parent, same], 7), baseline)
    _check(
        results,
        "same_identity_continuation",
        _measurement(actual),
        {"total": 55, "warnings": []},
    )

    changed = _write(root, "changed-id.jsonl", [meta("continuation"), fresh])
    actual = usage.report(_snapshot([parent, changed], 7), baseline)
    _check(
        results,
        "changed_identity_old_start",
        _measurement(actual),
        {
            "total": None,
            "warnings": [
                "added_session_has_no_task_start_baseline",
                "codex_inherited_or_missing_initial_history",
            ],
        },
    )
    try:
        usage.report(_snapshot([changed], 7), baseline)
    except ValueError as error:
        _check(
            results,
            "original_baseline_source_omitted",
            {"error": str(error)},
            {"error": "baseline sessions missing; include every original source"},
        )
    else:
        raise AssertionError("Omitting an original baseline identity was accepted")

    # A fresh identity/start and replayed events can look like entirely new work.
    _write(
        root,
        changed.name,
        [
            meta("continuation", timestamp=START + timedelta(seconds=6)),
            codex(counts(100, 10), second=7),
            codex(counts(150, 15), counts(50, 5), second=8),
        ],
    )
    actual = usage.report(_snapshot([parent, changed], 9), baseline)
    _check(
        results,
        "changed_identity_rewritten_history",
        _measurement(actual),
        {"total": 165, "warnings": []},
    )


def _discovery(root, results):
    root.mkdir()
    parent = _write(root, "parent.jsonl", [meta(project=root)])
    _write(root, "child.jsonl", [meta("child", "parent", project=root)])
    nested = meta("nested", project=root)
    nested["payload"]["source"] = {
        "subagent": {
            "thread_spawn": {"parent_thread_id": "child"},
        }
    }
    _write(root, "nested.jsonl", [nested])
    guardian = meta("guardian", "parent", project=root)
    guardian["payload"]["source"] = {"subagent": {"other": "guardian"}}
    _write(root, "guardian.jsonl", [guardian])
    _write(root, "unlinked.jsonl", [meta("unlinked", project=root)])
    _write(root, "other-cwd.jsonl", [meta("elsewhere", "parent", project=root.parent)])
    outside = _write(
        root.parent,
        "previous-day/outside.jsonl",
        [
            meta("outside", "parent", project=root),
        ],
    )
    selected = usage.discover_children([parent], root, root)
    _check(
        results,
        "bounded_descendant_discovery",
        {"selected": sorted(path.name for path in selected)},
        {"selected": ["child.jsonl", "guardian.jsonl", "nested.jsonl", "parent.jsonl"]},
    )
    explicit = usage.discover_children([parent, outside], root, root)
    _check(
        results,
        "explicit_other_directory_source",
        {"selected": sorted(path.name for path in explicit)},
        {
            "selected": [
                "child.jsonl",
                "guardian.jsonl",
                "nested.jsonl",
                "outside.jsonl",
                "parent.jsonl",
            ]
        },
    )

    # Discovery cannot restore the start counters of an omitted, older source.
    old = _write(
        root,
        "old-guardian.jsonl",
        [
            meta("old-guardian", "parent", project=root),
            codex(counts(10, 1), second=1),
        ],
    )
    baseline = _snapshot([parent], 5)
    actual = usage.report(_snapshot([parent, old], 6), baseline)
    _check(
        results,
        "older_approval_missing_baseline",
        _measurement(actual),
        {
            "total": None,
            "warnings": ["added_session_has_no_task_start_baseline"],
        },
    )


def _subtotals(root, results):
    active = _write(root, "active.jsonl", [meta("active")])
    idle = _write(root, "idle.jsonl", [meta("idle")])
    baseline = _snapshot([active, idle], 1)
    _write(root, active.name, [meta("active"), codex(counts(100, 10), second=2)])
    actual = usage.report(_snapshot([active, idle], 3), baseline)
    available = [
        row["tokens"]["total_tokens"]
        for row in actual["sessions"]
        if row["tokens"]["total_tokens"] is not None
    ]
    _check(
        results,
        "inactive_masks_measurable_subtotal",
        {
            **_measurement(actual),
            "available_subtotal": sum(available),
            "available_sessions": len(available),
            "selected_sessions": 2,
        },
        {
            "total": None,
            "warnings": [],
            "available_subtotal": 110,
            "available_sessions": 1,
            "selected_sessions": 2,
        },
    )

    _write(
        root,
        idle.name,
        [
            meta("idle"),
            {
                "timestamp": (START + timedelta(seconds=2)).isoformat(),
                "type": "event_msg",
                "payload": {"type": "agent_message"},
            },
        ],
    )
    actual = usage.report(_snapshot([active, idle], 3), baseline)
    _check(
        results,
        "used_session_without_supported_usage",
        _measurement(actual),
        {
            "total": None,
            "warnings": ["session_has_no_supported_usage"],
        },
    )


def main():
    """Assert and print synthetic observations; leave no telemetry files behind."""
    results = []
    with tempfile.TemporaryDirectory(prefix="relay-83-") as directory:
        root = Path(directory)
        _forks(root / "forks", results)
        _continuations(root / "continuations", results)
        _discovery(root / "discovery", results)
        _subtotals(root / "subtotals", results)
    print(
        json.dumps(
            {"scope": "synthetic_characterization_only", "cases": results}, indent=2
        )
    )


if __name__ == "__main__":
    main()

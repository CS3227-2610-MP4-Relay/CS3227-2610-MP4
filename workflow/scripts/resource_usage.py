"""Read selected agent JSONL telemetry; emit private snapshots or task deltas.

No prompts, message bodies, local paths, or credentials are emitted. This is an
observational counter, not a billing tool. Take a snapshot before starting work;
report with the same files plus any new delegated sessions afterwards. Source
logs are never modified. Keep snapshots outside version control.
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

METRICS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
SCHEMA = 1
WARNING_CODES = frozenset(
    {
        "malformed_or_incomplete_jsonl",
        "non_object_jsonl_record",
        "codex_copied_history_excluded",
        "claude_usage_without_message_id_skipped",
        "claude_message_usage_incomplete",
        "codex_turn_usage_incomplete",
        "mixed_codex_telemetry_is_ambiguous",
        "multiple_codex_exports_are_ambiguous",
        "codex_counter_reset",
        "codex_counter_reset_ambiguous",
        "codex_subset_counter_decrease",
        "codex_inherited_or_missing_initial_history",
        "session_has_no_supported_usage",
        "added_session_has_no_task_start_baseline",
        "source_truncated_or_replaced_since_baseline",
    }
)


def _object(value):
    return value if isinstance(value, dict) else {}


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _time(value):
    try:
        result = datetime.fromisoformat(value)
        return result if result.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def _identity(platform, identity):
    if not isinstance(identity, str) or not identity:
        raise ValueError("invalid session identity")
    return platform + ":" + hashlib.sha256(identity.encode()).hexdigest()[:24]


def _warnings(snapshot):
    warnings = snapshot.get("warnings")
    if not isinstance(warnings, list) or any(
        not isinstance(code, str) or code not in WARNING_CODES for code in warnings
    ):
        raise ValueError("invalid snapshot warning codes")
    return set(warnings)


def _records(path, warnings):
    with path.open(encoding="utf-8-sig") as source:
        for line in source:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except (ValueError, UnicodeError):
                warnings.add("malformed_or_incomplete_jsonl")
                continue
            if not isinstance(record, dict):
                warnings.add("non_object_jsonl_record")
                continue
            yield record


def _metadata(path):
    with path.open(encoding="utf-8-sig") as source:
        try:
            record = json.loads(source.readline())
        except ValueError:
            return {}
    if isinstance(record, dict) and record.get("type") == "session_meta":
        metadata = _object(record.get("payload"))
    elif isinstance(record, dict) and record.get("type") == "thread.started":
        metadata = {"id": record.get("thread_id")}
    else:
        return {}
    if not isinstance(metadata.get("id"), str) or not metadata["id"]:
        raise ValueError("invalid session metadata identity")
    return metadata


def discover_children(paths, directory, project):
    """Select only Codex descendants in one explicit directory and project."""
    if not directory.is_dir() or not project.is_dir():
        raise ValueError("child directory and project must be existing directories")
    selected = {path.resolve() for path in paths}
    metadata = {path: _metadata(path) for path in selected}
    candidates = sorted(directory.glob("*.jsonl"))
    if len(candidates) > 1000:
        raise ValueError("child directory exceeds 1000 files; select a narrower one")
    expected = project.resolve()
    for path in candidates:
        resolved = path.resolve()
        if resolved in metadata:
            continue
        meta = _metadata(path)
        cwd = meta.get("cwd")
        if isinstance(cwd, str) and Path(cwd).resolve() == expected:
            metadata[resolved] = meta
    while True:
        ids = {metadata[path].get("id") for path in selected}
        additions = set()
        for path, meta in metadata.items():
            spawn = _object(_object(meta.get("source")).get("subagent"))
            parent = meta.get("parent_thread_id") or _object(
                spawn.get("thread_spawn")
            ).get("parent_thread_id")
            if path not in selected and parent and parent in ids:
                additions.add(path)
        if not additions:
            return sorted(selected)
        selected.update(additions)


def _codex_usage(usage):
    result = {field: _count(usage.get(field)) for field in METRICS}
    if result["total_tokens"] is None:
        parts = [result["input_tokens"], result["output_tokens"]]
        if all(part is not None for part in parts):
            result["total_tokens"] = sum(parts)
    return result


def _claude_usage(usage):
    result = {field: None for field in METRICS}
    for field in ("input_tokens", "output_tokens"):
        result[field] = _count(usage.get(field))
    result["cached_input_tokens"] = _count(usage.get("cache_read_input_tokens"))
    result["cache_write_input_tokens"] = _count(
        usage.get("cache_creation_input_tokens")
    )
    # Claude input_tokens excludes cache reads and writes. Normalize it to total
    # input for comparison with Codex; the subsets must not be added a second time.
    parts = [
        result["input_tokens"],
        result["cached_input_tokens"],
        result["cache_write_input_tokens"],
    ]
    result["input_tokens"] = (
        sum(parts) if all(part is not None for part in parts) else None
    )
    if result["input_tokens"] is not None and result["output_tokens"] is not None:
        result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    return result


def collect(codex_paths=(), claude_paths=(), now=None):
    """Return aggregate-only telemetry from explicitly selected files."""
    warnings = set()
    streams = {}
    for platform, paths in (("codex", codex_paths), ("claude", claude_paths)):
        for path in sorted({Path(path).resolve() for path in paths}):
            meta = _metadata(path) if platform == "codex" else {}
            identity = meta.get("id") or str(path)
            awaiting_usage = bool(meta.get("id"))
            if platform == "claude":
                first = next(
                    (
                        record
                        for record in _records(path, warnings)
                        if isinstance(record.get("sessionId"), str)
                    ),
                    {},
                )
                session_id = first.get("sessionId")
                agent_id = first.get("agentId") or (
                    path.stem if path.parent.name == "subagents" else "coordinator"
                )
                if isinstance(session_id, str):
                    identity = session_id + ":" + str(agent_id)
                    awaiting_usage = True
            key = _identity(platform, identity)
            stream = streams.setdefault(
                key,
                {
                    "platform": platform,
                    "started_at": None,
                    "events": [],
                    "export_sources": set(),
                    "awaiting_usage": awaiting_usage,
                    "missing_message_id": False,
                },
            )
            if _time(meta.get("timestamp")):
                stream["started_at"] = meta["timestamp"]
            for index, record in enumerate(_records(path, warnings)):
                stamp = record.get("timestamp")
                if _time(stamp) and stream["started_at"] is None:
                    stream["started_at"] = stamp
                payload = _object(record.get("payload"))
                if platform == "codex":
                    event_time = _time(stamp)
                    created = _time(meta.get("timestamp"))
                    if event_time and created and event_time < created:
                        if payload.get("type") == "token_count":
                            warnings.add("codex_copied_history_excluded")
                        continue
                    if (
                        payload.get("role") == "assistant"
                        or payload.get("type")
                        in ("agent_message", "agent_reasoning", "task_complete")
                        or record.get("type") in ("turn.completed", "turn.failed")
                    ):
                        stream["awaiting_usage"] = False
                    info = _object(payload.get("info"))
                    if (
                        record.get("type") == "event_msg"
                        and payload.get("type") == "token_count"
                        and isinstance(info.get("total_token_usage"), dict)
                    ):
                        stream["events"].append(
                            (stamp or "", index, "cumulative", info)
                        )
                        stream["awaiting_usage"] = False
                    elif record.get("type") == "turn.completed":
                        stream["export_sources"].add(path)
                        stream["events"].append(
                            (stamp or "", index, "turn", _object(record.get("usage")))
                        )
                else:
                    message = _object(record.get("message"))
                    if record.get("type") == "assistant":
                        stream["awaiting_usage"] = False
                    if record.get("type") != "assistant":
                        continue
                    message_id = message.get("id")
                    if not isinstance(message_id, str) or not message_id:
                        warnings.add("claude_usage_without_message_id_skipped")
                        stream["missing_message_id"] = True
                        continue
                    counters = _object(message.get("usage"))
                    # Session transcripts may repeat one assistant message for
                    # multiple content blocks. Keep its largest reported counters.
                    stream["events"].append(
                        (
                            message_id,
                            {
                                field: _count(counters.get(field))
                                for field in (
                                    "input_tokens",
                                    "output_tokens",
                                    "cache_read_input_tokens",
                                    "cache_creation_input_tokens",
                                )
                            },
                        )
                    )

    sessions = {}
    for key, stream in streams.items():
        totals = {field: None for field in METRICS}
        events = stream.pop("events")
        export_sources = stream.pop("export_sources")
        missing_message_id = stream.pop("missing_message_id")
        observations = 0
        if stream["platform"] == "claude":
            messages = {}
            for message_id, usage in events:
                merged = messages.setdefault(message_id, {})
                for field, value in usage.items():
                    if value is not None:
                        merged[field] = max(merged.get(field, 0), value)
            messages = {
                message_id: _claude_usage(counters)
                for message_id, counters in messages.items()
            }
            observations = len(messages)
            if missing_message_id or any(
                counters[field] is None
                for counters in messages.values()
                for field in ("input_tokens", "output_tokens", "total_tokens")
            ):
                warnings.add("claude_message_usage_incomplete")
            for field in METRICS:
                values = [usage.get(field) for usage in messages.values()]
                if (
                    not missing_message_id
                    and values
                    and all(value is not None for value in values)
                ):
                    totals[field] = sum(values)
        else:
            cumulative = [event for event in events if event[2] == "cumulative"]
            ambiguous = False
            if cumulative and export_sources:
                warnings.add("mixed_codex_telemetry_is_ambiguous")
                ambiguous = True
            if len(export_sources) > 1:
                warnings.add("multiple_codex_exports_are_ambiguous")
                ambiguous = True
            chosen = cumulative or [event for event in events if event[2] == "turn"]
            previous = None
            seen = set()
            unavailable = set()
            for stamp, index, kind, info in sorted(
                chosen,
                key=lambda item: (
                    _time(item[0]) or datetime.min.replace(tzinfo=UTC),
                    item[1],
                ),
            ):
                raw = info.get("total_token_usage", info)
                current = _codex_usage(raw)
                if kind == "turn" and any(
                    current[field] is None
                    for field in ("input_tokens", "output_tokens", "total_tokens")
                ):
                    warnings.add("codex_turn_usage_incomplete")
                signature = (
                    stamp,
                    index if kind == "turn" else None,
                    json.dumps(raw, sort_keys=True),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                if kind == "cumulative" and current == previous:
                    continue
                increment = current.copy()
                last = _codex_usage(_object(info.get("last_token_usage")))
                if kind == "cumulative" and previous is not None:
                    decreased = {
                        field
                        for field in METRICS
                        if current[field] is not None
                        and previous[field] is not None
                        and current[field] < previous[field]
                    }
                    primary = ("input_tokens", "output_tokens", "total_tokens")
                    if decreased.intersection(primary):
                        if all(
                            current[field] is not None
                            and previous[field] is not None
                            and current[field] <= previous[field]
                            for field in primary
                        ):
                            warnings.add("codex_counter_reset")
                        else:
                            warnings.add("codex_counter_reset_ambiguous")
                            increment = {field: None for field in METRICS}
                    else:
                        if decreased:
                            warnings.add("codex_subset_counter_decrease")
                        increment = {
                            field: (
                                current[field] - previous[field]
                                if current[field] is not None
                                and previous[field] is not None
                                and field not in decreased
                                else None
                            )
                            for field in METRICS
                        }
                elif kind == "cumulative" and any(
                    last[field] is not None
                    and current[field] is not None
                    and last[field] < current[field]
                    for field in METRICS
                ):
                    warnings.add("codex_inherited_or_missing_initial_history")
                    increment = last
                for field, value in increment.items():
                    if value is not None:
                        totals[field] = (totals[field] or 0) + value
                    else:
                        unavailable.add(field)
                previous = current
                observations += 1
            for field in unavailable:
                totals[field] = None
            if ambiguous:
                totals = {field: None for field in METRICS}
        if not observations and not stream["awaiting_usage"]:
            warnings.add("session_has_no_supported_usage")
        sessions[key] = {**stream, "observations": observations, "tokens": totals}
    return {
        "schema_version": SCHEMA,
        "kind": "usage_snapshot",
        "captured_at": (now or datetime.now(UTC)).isoformat(),
        "sessions": sessions,
        "warnings": sorted(warnings),
    }


def report(current, baseline, retries=None, repair_rounds=None):
    """Subtract a start snapshot, refusing to treat added history as task usage."""
    if baseline.get("schema_version") != SCHEMA or baseline.get("kind") != (
        "usage_snapshot"
    ):
        raise ValueError("baseline is not a supported usage snapshot")
    start = _time(baseline.get("captured_at"))
    end = _time(current.get("captured_at"))
    if start is None or end is None or end < start:
        raise ValueError("invalid snapshot timestamps")
    warnings = _warnings(current) | _warnings(baseline)
    old_sessions = baseline.get("sessions")
    if not isinstance(old_sessions, dict):
        raise TypeError("invalid baseline sessions")
    for session in old_sessions.values():
        if not isinstance(session, dict) or not isinstance(session.get("tokens"), dict):
            raise TypeError("invalid baseline session")
        if type(session.get("awaiting_usage")) is not bool:
            raise TypeError("invalid baseline session state")
        for field in METRICS:
            tokens = session["tokens"]
            if field not in tokens or (
                tokens[field] is not None and _count(tokens[field]) is None
            ):
                raise ValueError("invalid baseline token counter")
    missing = set(old_sessions) - set(current["sessions"])
    if missing:
        raise ValueError("baseline sessions missing; include every original source")
    rows = []
    for key, session in current["sessions"].items():
        previous = old_sessions.get(key)
        started = _time(session.get("started_at"))
        historical = previous is None and (started is None or started < start)
        if historical:
            warnings.add("added_session_has_no_task_start_baseline")
        values = {}
        for field in METRICS:
            after = session["tokens"][field]
            before = previous["tokens"].get(field) if previous else 0
            if previous and previous.get("awaiting_usage"):
                before = 0
            value = None
            if not historical and after is not None and before is not None:
                if after >= before:
                    value = after - before
                else:
                    warnings.add("source_truncated_or_replaced_since_baseline")
            values[field] = value
        rows.append({"session": key, "platform": session["platform"], "tokens": values})
    totals = {}
    for field in METRICS:
        values = [row["tokens"][field] for row in rows]
        totals[field] = (
            sum(values)
            if values and all(value is not None for value in values)
            else None
        )
    return {
        "schema_version": SCHEMA,
        "kind": "task_usage",
        "started_at": baseline["captured_at"],
        "ended_at": current["captured_at"],
        "elapsed_seconds": round((end - start).total_seconds(), 3),
        "retries": retries,
        "repair_rounds": repair_rounds,
        "session_count": len(rows),
        "tokens": totals,
        "sessions": rows,
        "warnings": sorted(warnings),
        "coverage": "selected_sources_only; warnings may indicate incomplete telemetry",
    }


def _nonnegative(value):
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return result


def main(argv=None):
    """Print a JSON snapshot or task usage report without modifying any logs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("snapshot", "report"))
    parser.add_argument("--codex", type=Path, action="append", default=[])
    parser.add_argument("--claude", type=Path, action="append", default=[])
    parser.add_argument("--codex-children", type=Path)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--retries", type=_nonnegative)
    parser.add_argument("--repair-rounds", type=_nonnegative)
    args = parser.parse_args(argv)
    if not args.codex and not args.claude:
        parser.error("select at least one --codex or --claude file")
    if args.command == "report" and args.baseline is None:
        parser.error("report requires --baseline from before the task")
    if args.command == "snapshot" and args.baseline:
        parser.error("--baseline is only used with report")
    if args.codex_children and (not args.project or not args.codex):
        parser.error("--codex-children requires --project and a --codex parent")
    try:
        paths = args.codex
        if args.codex_children:
            paths = discover_children(paths, args.codex_children, args.project)
        current = collect(paths, args.claude)
        if args.command == "report":
            baseline = json.loads(args.baseline.read_text(encoding="utf-8-sig"))
            if not isinstance(baseline, dict):
                raise ValueError("baseline must be a JSON object")
            current = report(current, baseline, args.retries, args.repair_rounds)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError):
        print(
            "usage error: unreadable source or invalid telemetry/baseline",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(current, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

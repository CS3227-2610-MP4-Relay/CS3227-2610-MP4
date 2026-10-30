"""Score one finished experiment run: python evaluate.py <run_id>

Works on a copy of the run's repository, so the candidate is never changed. Writes
out/<run_id>.eval.json with the run's cost, speed, hidden-suite and verification
results, diff size, commits and a transcript audit. Mutation testing and the blind
review are separate steps (mutate.py, review.py).
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

EXP = Path(os.environ["EXP"])
PRIVATE = Path(os.environ["PRIVATE"])
HIDDEN = PRIVATE / "eval" / "zz_hidden"
PROJECTS = Path.home() / ".claude" / "projects"
COUNT = re.compile(r"(\d+) (passed|failed|errors?|skipped)")


def sh(cmd, cwd, env=None):
    """Run a shell command and return its exit code and combined output."""
    done = subprocess.run(  # noqa: PLW1510 - the exit code is the result
        cmd,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
        executable="/bin/bash",
    )
    return done.returncode, done.stdout + done.stderr


def counts(output):
    """Pytest's summary counts from its last lines."""
    found = {}
    for line in output.strip().splitlines()[-3:]:
        for number, kind in COUNT.findall(line):
            found[kind.rstrip("s") if kind.startswith("error") else kind] = int(number)
    return found


def area(path):
    """The part of the repository a changed path belongs to."""
    if path.startswith("src/") and ("/tests/" in path or "/test_" in path):
        return "tests"
    for prefix, name in (
        ("src/", "code"),
        ("workflow/specs/", "specs"),
        ("docs/", "docs"),
        ("workflow/plans/", "plans"),
    ):
        if path.startswith(prefix):
            return name
    return "other"


def stream_records(run):
    """Every JSON record the headless session streamed."""
    records = []
    for line in (EXP / "out" / f"{run}.stream.jsonl").read_text().splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def tool_uses(records):
    """(parent tool-use id, tool name, input) for every tool call in the stream."""
    for record in records:
        if record.get("type") != "assistant":
            continue
        for block in record.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                parent = record.get("parent_tool_use_id")
                yield parent, block.get("name"), block.get("input", {})


def subagent_transcripts(session_id):
    """Tool calls recorded in the session's subagent transcripts on disk."""
    calls = []
    for path in PROJECTS.glob(f"*/{session_id}/subagents/*.jsonl"):
        for line in path.read_text().splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = record.get("message", {}).get("content", [])
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append((path.stem, block.get("name"), block.get("input", {})))
    return calls


def audit(calls, repo, session_id=None):
    """Tool inputs that reach outside the run's own clone and session folders."""
    allowed = (
        str(repo),
        str(EXP / "venv"),
        str(EXP / "addons"),
        "/dev/null",
        "/tmp/",
        "/private/tmp/pytest",
    )
    own_session = f"-exp-runs-{repo.name}/"
    outside = []
    for _, name, given in calls:
        text = json.dumps(given)
        for path in re.findall(
            r"(/(?:Users|private|tmp|var|opt|etc)/[^\s\"'`;|&)]*)", text
        ):
            if path.startswith(allowed) or own_session in path:
                continue
            if session_id and f"/{session_id}/" in path:
                continue
            if "site-packages" not in path:
                outside.append({"tool": name, "path": path[:200]})
    return outside


def hidden_suite(copy, run):
    """Run the hidden acceptance suite in the copy and count outcomes by group."""
    target = copy / "src" / "zz_hidden"
    shutil.copytree(HIDDEN, target)
    report = copy / "hidden.xml"
    code, output = sh(
        f"source .venv/bin/activate && pytest -q -p no:cacheprovider "
        f"src/zz_hidden --junitxml={report}",
        copy,
        {"TOX_PARALLEL_ENV": f"hid_{run}".replace("-", "_")},
    )
    groups = {"refusal": [0, 0], "allowed": [0, 0]}
    failures = []
    if report.exists():
        for case in ET.parse(report).getroot().iter("testcase"):
            name = case.get("name", "")
            group = "allowed" if "_accepted" in name else "refusal"
            failed = case.find("failure") is not None or case.find("error") is not None
            groups[group][0 if failed else 1] += 1
            if failed:
                failures.append(name)
    shutil.rmtree(target)
    return {
        "exit": code,
        "refusal_passed": groups["refusal"][1],
        "refusal_failed": groups["refusal"][0],
        "allowed_passed": groups["allowed"][1],
        "allowed_failed": groups["allowed"][0],
        "failures": failures[:40],
        "tail": output.strip().splitlines()[-1:] if output.strip() else [],
    }


def verification(copy, run):
    """Django checks, Ruff and the full pytest suite on the candidate."""
    env = {"TOX_PARALLEL_ENV": f"ver_{run}".replace("-", "_")}
    steps = {
        "django_check": "python src/manage.py check --settings=relay.settings.test",
        "migrations": "python src/manage.py makemigrations --check --dry-run "
        "--settings=relay.settings.test",
        "ruff_check": "ruff check .",
        "ruff_format": "ruff format --check .",
        "pytest": "pytest -q -p no:cacheprovider",
    }
    results = {}
    for name, command in steps.items():
        code, output = sh(f"source .venv/bin/activate && {command}", copy, env)
        results[name] = {"exit": code}
        if name == "pytest":
            results[name].update(counts(output))
            results[name]["failed_tests"] = [
                line.split(" ")[1]
                for line in output.splitlines()
                if line.startswith("FAILED ")
            ][:20]
    results["all_passed"] = all(
        step["exit"] == 0 for step in results.values() if isinstance(step, dict)
    )
    return results


def history(copy, arm_base):
    """The run's commits, each with the areas it touched, and spec-first order."""
    log = sh(f"git log --reverse --format=%H%x09%s {arm_base}..HEAD", copy)[1]
    commits = []
    for line in log.strip().splitlines():
        sha, subject = line.split("\t", 1)
        files = sh(f"git show --name-only --format= {sha}", copy)[1].split()
        commits.append(
            {
                "sha": sha[:7],
                "subject": subject,
                "areas": sorted({area(path) for path in files}),
            }
        )
    first = {}
    for index, commit in enumerate(commits):
        for name in commit["areas"]:
            first.setdefault(name, index)
    spec_first = None
    if "specs" in first and "code" in first:
        spec_first = first["specs"] <= first["code"]
    return commits, spec_first


def diff_size(copy, arm_base):
    """Added and deleted lines by area, uncommitted and untracked work included."""
    sh("git add -A -N .", copy)
    sizes = {}
    output = sh(f"git diff --numstat {arm_base}", copy)[1]
    for line in output.strip().splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-":
            continue
        entry = sizes.setdefault(area(path), [0, 0])
        entry[0] += int(added)
        entry[1] += int(deleted)
    return sizes


def usage(records, end):
    """Cost, time, turns and tokens for the whole session.

    A headless session that waits for background subagents emits one result
    record per turn segment. Cost and model usage in each are cumulative, while
    turns and API time are per segment, so those are summed. Wall time comes from
    the launcher. The stream's per-message usage splits cached tokens between the
    orchestrator and its subagents.
    """
    results = [r for r in records if r.get("type") == "result"]
    last = results[-1] if results else {}
    messages = {}
    for record in records:
        if record.get("type") == "assistant":
            message = record.get("message", {})
            side = "subagents" if record.get("parent_tool_use_id") else "orchestrator"
            messages[message.get("id")] = (side, message.get("usage") or {})
    split = {"orchestrator": {}, "subagents": {}}
    for side, tokens in messages.values():
        for key in ("cache_read_input_tokens", "cache_creation_input_tokens"):
            split[side][key] = split[side].get(key, 0) + (tokens.get(key) or 0)
    started = datetime.fromisoformat(end["start"])
    ended = datetime.fromisoformat(end["end"])
    denials = [d for r in results for d in (r.get("permission_denials") or [])]
    costs = [r.get("total_cost_usd") or 0 for r in results]
    return {
        "is_error": any(r.get("is_error") for r in results),
        "subtype": last.get("subtype"),
        "result_records": len(results),
        "cost_usd": max(costs) if costs else None,
        "wall_s": round((ended - started).total_seconds()),
        "api_s": round(sum(r.get("duration_api_ms") or 0 for r in results) / 1000),
        "turns": sum(r.get("num_turns") or 0 for r in results),
        "model_usage": last.get("modelUsage"),
        "cache_split": split,
        "permission_denials": len(denials),
        "denied": [
            {"tool": d.get("tool_name"), "input": json.dumps(d.get("tool_input"))[:160]}
            for d in denials
        ][:10],
        "final_report": (last.get("result") or "")[:6000],
        "session_id": last.get("session_id"),
    }


# DeepSeek v4.1 Flash list prices on OpenRouter, US$ per token, read on 2026-10-30.
DEEPSEEK_PRICE = {"input": 0.045e-6, "cache_read": 0.006e-6, "output": 0.5e-6}
CODEX_SESSIONS = Path.home() / ".codex" / "sessions"
HERMES_STATE = Path.home() / ".hermes" / "state.db"


def wall(end):
    """Seconds between the launcher's start and end stamps."""
    started, ended = (datetime.fromisoformat(end[key]) for key in ("start", "end"))
    return round((ended - started).total_seconds())


def codex_usage(run, repo, end):
    """Usage, tool calls and subagents from every Codex session in the run's clone.

    Codex writes one rollout file per thread, including spawned agents. Each
    file's last token count is that thread's total; input includes cached input.
    """
    totals = {"input": 0, "cached": 0, "output": 0, "reasoning": 0}
    calls, threads = [], []
    for path in CODEX_SESSIONS.rglob("rollout-*.jsonl"):
        lines = path.read_text().splitlines()
        if not lines:
            continue
        meta = json.loads(lines[0]).get("payload", {})
        if meta.get("cwd") != str(repo):
            continue
        threads.append(str(meta.get("source")))
        last = None
        for line in lines:
            entry = json.loads(line)
            payload = entry.get("payload") or {}
            if payload.get("type") == "token_count" and payload.get("info"):
                last = payload["info"]["total_token_usage"]
            if payload.get("type") == "function_call":
                name = payload.get("name")
                try:
                    given = json.loads(payload.get("arguments") or "{}")
                except json.JSONDecodeError:
                    given = {"raw": payload.get("arguments")}
                calls.append((None, name, given))
        if last:
            totals["input"] += last.get("input_tokens", 0)
            totals["cached"] += last.get("cached_input_tokens", 0)
            totals["output"] += last.get("output_tokens", 0)
            totals["reasoning"] += last.get("reasoning_output_tokens", 0)
    cost = (
        (totals["input"] - totals["cached"]) * DEEPSEEK_PRICE["input"]
        + totals["cached"] * DEEPSEEK_PRICE["cache_read"]
        + totals["output"] * DEEPSEEK_PRICE["output"]
    )
    turns = sum(
        1
        for line in (EXP / "out" / f"{run}.codex.jsonl").read_text().splitlines()
        if '"turn.completed"' in line
    )
    last_message = EXP / "out" / f"{run}.last.txt"
    spent = {
        "is_error": end["exit"] != 0,
        "cost_usd": cost,
        "cost_basis": "computed from tokens at OpenRouter list prices",
        "wall_s": wall(end),
        "turns": turns,
        "model_usage": {end.get("model", "deepseek"): totals},
        "threads": threads,
        "permission_denials": 0,
        "final_report": last_message.read_text()[:6000]
        if last_message.exists()
        else "",
        "session_id": None,
    }
    # Spawned role agents only; "guardian" threads are Codex's approval reviewer.
    return spent, calls, [t for t in threads if "thread_spawn" in t]


def hermes_usage(run, end):
    """Usage of a Hermes run and its delegated children, from Hermes's session store.

    The usage report's cost includes delegated children but its token counts do
    not, so tokens come from the session store: the run's session plus every
    session whose parent it is. Tool calls are not streamed and are not audited.
    """
    report = json.loads((EXP / "out" / f"{run}.hermes-usage.json").read_text())
    session = report.get("session_id")
    store = sqlite3.connect(f"file:{HERMES_STATE}?mode=ro", uri=True)
    rows = store.execute(
        "select id, input_tokens, cache_read_tokens, output_tokens, "
        "reasoning_tokens, estimated_cost_usd from sessions "
        "where id = ? or parent_session_id = ?",
        (session, session),
    ).fetchall()
    store.close()
    totals = {"input": 0, "cached": 0, "output": 0, "reasoning": 0}
    for row in rows:
        for key, value in zip(totals, row[1:5], strict=True):
            totals[key] += value or 0
    children = [row[0] for row in rows if row[0] != session]
    last_message = EXP / "out" / f"{run}.last.txt"
    spent = {
        "is_error": bool(report.get("failed")) or end["exit"] != 0,
        "cost_usd": sum(row[5] or 0 for row in rows),
        "cost_basis": report.get("cost_source"),
        "wall_s": wall(end),
        "turns": report.get("api_calls"),
        "model_usage": {report.get("model"): totals},
        "permission_denials": 0,
        "final_report": last_message.read_text()[:6000]
        if last_message.exists()
        else "",
        "session_id": session,
    }
    return spent, [], ["delegated"] * len(children)


def main(run):
    """Score `run` and write its evaluation file."""
    meta = json.loads((EXP / "out" / f"{run}.meta.json").read_text())
    end = json.loads((EXP / "out" / f"{run}.end.json").read_text())
    repo = EXP / "runs" / run
    copy = PRIVATE / "evalwt" / run
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(repo, copy, symlinks=True)

    disk = []
    if (EXP / "out" / f"{run}.codex.jsonl").exists():
        spent, calls, agents = codex_usage(run, repo, end)
    elif (EXP / "out" / f"{run}.hermes-usage.json").exists():
        spent, calls, agents = hermes_usage(run, end)
    else:
        records = stream_records(run)
        spent = usage(records, end)
        calls = list(tool_uses(records))
        if spent["session_id"]:
            disk = subagent_transcripts(spent["session_id"])
        agents = [
            given.get("subagent_type", "?")
            for parent, name, given in calls
            if name in ("Task", "Agent") and parent is None
        ]
    commits, spec_first = history(copy, meta["arm_base"])
    dirty = bool(sh("git status --porcelain", copy)[1].strip())
    evaluation = {
        **meta,
        "start": end["start"],
        "end": end["end"],
        "exit": end["exit"],
        "usage": spent,
        "subagents": agents,
        "tool_calls": {"stream": len(calls), "subagent_transcripts": len(disk)},
        "commits": commits,
        "spec_first": spec_first,
        "uncommitted_changes": dirty,
        "diff": diff_size(copy, meta["arm_base"]),
        "verification": verification(copy, run),
        "hidden": hidden_suite(copy, run),
        "outside_access": audit(calls + disk, repo, spent["session_id"])[:50],
    }
    (EXP / "out" / f"{run}.eval.json").write_text(json.dumps(evaluation, indent=2))
    h, v = evaluation["hidden"], evaluation["verification"]
    print(
        f"{run}: ${spent['cost_usd']:.2f} {spent['wall_s']}s turns={spent['turns']} "
        f"agents={len(agents)} hidden={h['refusal_passed']}/108+"
        f"{h['allowed_passed']}/24 verify={v['all_passed']} "
        f"commits={len(commits)} spec_first={spec_first} "
        f"outside={len(evaluation['outside_access'])}"
    )


if __name__ == "__main__":
    main(sys.argv[1])

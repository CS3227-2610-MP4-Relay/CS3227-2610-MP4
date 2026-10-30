"""Collect every scored run into results/runs.csv and results/summary.json.

Reads out/<run>.eval.json, out/<run>.mutants.json and out/<run>.review.json.
A run missing a step is reported with that step empty, never as zero. The
hidden_refusal and hidden_allowed columns split task 1's suite; hidden_passed
and hidden_failed total either task's.
"""

import csv
import json
import os
import statistics
import sys
from pathlib import Path

EXP = Path(os.environ["EXP"])
RESULTS = Path(__file__).resolve().parent.parent / "results"

FIELDS = [
    "run",
    "task",
    "arm",
    "tool",
    "model",
    "cost_usd",
    "wall_min",
    "turns",
    "subagent_runs",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "orchestrator_cache_read",
    "subagent_cache_read",
    "orchestrator_cache_write",
    "subagent_cache_write",
    "hidden_refusal",
    "hidden_allowed",
    "hidden_passed",
    "hidden_failed",
    "verify_passed",
    "pytest_passed",
    "mutants_killed",
    "review_high",
    "review_medium",
    "review_low",
    "review_score",
    "mergeable",
    "commits",
    "spec_first",
    "code_lines",
    "test_lines",
    "spec_lines",
    "doc_lines",
    "plan_lines",
    "other_lines",
    "outside_access",
    "denied_actions",
]


def load(run, step):
    """One step's JSON for `run`, or None when that step has not run."""
    path = EXP / "out" / f"{run}.{step}.json"
    return json.loads(path.read_text()) if path.exists() else None


def row(run):
    """One CSV row for `run`."""
    evaluation = load(run, "eval")
    mutants = load(run, "mutants")
    review = load(run, "review")
    spent = evaluation["usage"]
    models = spent.get("model_usage") or {}
    split = spent.get("cache_split") or {}
    diff = evaluation["diff"]
    hidden = evaluation["hidden"]
    verdict = (review or {}).get("verdict") or {}
    severities = [f.get("severity") for f in verdict.get("findings", [])]
    scores = verdict.get("scores") or {}
    end = json.loads((EXP / "out" / f"{run}.end.json").read_text())
    model, tool = end["model"], end.get("tool", "claude")
    return {
        "run": run,
        "task": evaluation.get("task", "1"),
        "arm": evaluation["arm"],
        "tool": tool,
        "model": model,
        "cost_usd": round(spent["cost_usd"], 2),
        "wall_min": round(spent["wall_s"] / 60, 1),
        "turns": spent["turns"],
        "subagent_runs": len(evaluation["subagents"]),
        # Claude Code reports camelCase totals; the Codex and Hermes readers
        # use short names.
        "output_tokens": sum(
            m.get("outputTokens", m.get("output", 0)) for m in models.values()
        ),
        "cache_read_tokens": sum(
            m.get("cacheReadInputTokens", m.get("cached", 0)) for m in models.values()
        ),
        "cache_write_tokens": sum(
            m.get("cacheCreationInputTokens", 0) for m in models.values()
        ),
        "orchestrator_cache_read": split.get("orchestrator", {}).get(
            "cache_read_input_tokens"
        ),
        "subagent_cache_read": split.get("subagents", {}).get(
            "cache_read_input_tokens"
        ),
        "orchestrator_cache_write": split.get("orchestrator", {}).get(
            "cache_creation_input_tokens"
        ),
        "subagent_cache_write": split.get("subagents", {}).get(
            "cache_creation_input_tokens"
        ),
        "hidden_refusal": evaluation["hidden"]["refusal_passed"],
        "hidden_allowed": evaluation["hidden"]["allowed_passed"],
        "hidden_passed": hidden["refusal_passed"] + hidden["allowed_passed"],
        "hidden_failed": hidden["refusal_failed"] + hidden["allowed_failed"],
        "verify_passed": evaluation["verification"]["all_passed"],
        "pytest_passed": evaluation["verification"]["pytest"].get("passed"),
        "mutants_killed": sum(m["killed"] for m in mutants.values())
        if mutants
        else None,
        "review_high": severities.count("High") if review else None,
        "review_medium": severities.count("Medium") if review else None,
        "review_low": severities.count("Low") if review else None,
        "review_score": round(statistics.mean(scores.values()), 2) if scores else None,
        "mergeable": verdict.get("mergeable"),
        "commits": len(evaluation["commits"]),
        "spec_first": evaluation["spec_first"],
        "code_lines": sum(diff.get("code", [0, 0])),
        "test_lines": sum(diff.get("tests", [0, 0])),
        "spec_lines": sum(diff.get("specs", [0, 0])),
        "doc_lines": sum(diff.get("docs", [0, 0])),
        "plan_lines": sum(diff.get("plans", [0, 0])),
        "other_lines": sum(diff.get("other", [0, 0])),
        "outside_access": len(evaluation["outside_access"]),
        "denied_actions": spent["permission_denials"],
    }


def spread(values):
    """Median, minimum and maximum of the values that exist."""
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "n": len(values),
    }


def main(prefixes):
    """Write the per-run table and the per-arm spreads for runs with `prefixes`."""
    runs = sorted(
        path.name.removesuffix(".eval.json")
        for path in (EXP / "out").glob("*.eval.json")
        if path.name.startswith(tuple(prefixes))
    )
    rows = [row(run) for run in runs]
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "runs.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    numeric = [
        f
        for f in FIELDS
        if f
        not in (
            "run",
            "task",
            "arm",
            "tool",
            "model",
            "mergeable",
            "verify_passed",
            "spec_first",
        )
    ]
    # Keyed by task, then arm: the two tasks' numbers are never pooled.
    summary = {}
    for task, arm in sorted({(r["task"], r["arm"]) for r in rows}):
        mine = [r for r in rows if (r["task"], r["arm"]) == (task, arm)]
        entry = {field: spread([r[field] for r in mine]) for field in numeric}
        entry["runs"] = [r["run"] for r in mine]
        entry["verify_passed"] = [r["verify_passed"] for r in mine]
        entry["spec_first"] = [r["spec_first"] for r in mine]
        entry["mergeable"] = [r["mergeable"] for r in mine]
        summary.setdefault(task, {})[arm] = entry
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2))
    arms = sum(len(by_arm) for by_arm in summary.values())
    print(f"{len(rows)} runs, {arms} task-arm groups")


if __name__ == "__main__":
    # By default every counted run: the comparison, the ideal-setup runs, their
    # references and task 2. Smoke tests are left out.
    main(sys.argv[1:] or ["r1-", "r2-", "r3-", "i", "ref-", "t2-"])

"""Refresh the data block in presentation.html: python slide_data.py

The slides are written by hand. Every number they chart comes from the JSON
block between the `deck-data` script tags, which this script rebuilds from
results/runs.csv and results/analysis.json, so the charts never drift from the
results.
"""

import csv
import json
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
with open(HERE / "results" / "runs.csv") as runs_file:
    RUNS = list(csv.DictReader(runs_file))
ANALYSIS = json.loads((HERE / "results" / "analysis.json").read_text())
DECK = HERE / "presentation.html"

OPUS, SONNET, HAIKU = "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"
DEEPSEEK = "deepseek/deepseek-v4.1-flash"
# Opus reviewers on a Haiku session: reported in the write-up, not pooled here.
VARIANTS = {"i3-haiku-opusreview-1"}

# (label, arm, session model) for the comparison. The run with all three
# add-ons at once is left out: each add-on is compared on its own.
SETUPS = [
    ("MP4 baseline", "mp4", OPUS),
    ("MP3 six roles", "mp3", OPUS),
    ("Solo session", "solo", OPUS),
    ("MP4, Sonnet builder", "mp4-sonnet-builder", OPUS),
    ("MP4, all Sonnet", "mp4-sonnet", SONNET),
    ("MP4, all Haiku", "mp4-haiku", HAIKU),
    ("superpowers", "superpowers", OPUS),
    ("spec-kit", "spec-kit", OPUS),
    ("MP4 + caveman", "caveman", OPUS),
    ("MP4 + ponytail", "ponytail", OPUS),
    ("MP4 + headroom", "headroom", OPUS),
    ("OpenSpec", "openspec", OPUS),
    ("Our setup, v1", "ideal-v1", OPUS),
    # The latest version that ran on each task, picked in latest_ideal().
    ("Our setup, latest", "ideal", OPUS),
]
TASKS = ("1", "2", "3", "4")
# (label, tool, model, MP4 reference arm) for the ideal setup's evaluation.
PLATFORMS = [
    ("Opus", "claude", OPUS, "mp4"),
    ("Sonnet", "claude", SONNET, "mp4-sonnet"),
    ("Haiku", "claude", HAIKU, "mp4-haiku"),
    ("DeepSeek in Codex", "codex", DEEPSEEK, "mp4-inherit"),
    ("DeepSeek in Hermes", "hermes", DEEPSEEK, "mp4-inherit"),
]
VERSIONS = ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8"]
# Setups whose coordinator hands the building to subagents.
MULTI_AGENT = {
    "mp4",
    "mp3",
    "mp4-sonnet-builder",
    "mp4-sonnet",
    "mp4-haiku",
    "caveman",
    "ponytail",
    "headroom",
}
# Runs that ended mid-slice when the coordinator ended its turn while a
# background builder was still working; method.md keeps them out of runs.csv.
CUT_SHORT = ["t3-mp4-1", "t3-ponytail-1", "t3-mp4-haiku-1"]

# Each Medium-or-higher blind-review finding, sorted by hand into the kind of
# gap it is, keyed by run and the start of its summary. main() fails on a
# finding with no kind, so new runs get sorted before the slides change.
FINDING_KINDS = {
    "behaviour": "behaviour missing or wrong where the hidden tests don't look",
    "claims": "spec text claiming more than the code or tests do",
    "decisions": "a decision or accepted risk missing or misrecorded",
    "tests": "an old test weakened, or a coverage gap",
    "earlier": "an earlier requirement dropped, left unmet or contradicted",
    "false": "a reviewer false positive",
}
FINDINGS = {
    ("i1-haiku-1", "rounds.md's rendering rule"): "claims",
    ("i1-haiku-2", "Decisions 2 and 3"): "decisions",
    ("i1-hermes-2", "SECURITY-SPEC.md, the home"): "decisions",
    ("i1-opus-1", "The rendering rule"): "claims",
    ("i1-sonnet-2", "The refusal and acceptance"): "tests",
    ("i2-haiku-2", "RND-1.7, RND-2.8"): "claims",
    ("i2-hermes-1", "Rule 5 now states"): "claims",
    ("i3-sonnet-1", "The edited rendering rule"): "claims",
    ("i4-haiku-1", "Decisions 2 and 3"): "decisions",
    ("i5-sonnet-1", "The edited rendering rule"): "claims",
    ("r1-mp4-sonnet-builder", "`HEX = lambda"): "false",
    ("r1-spec-kit", "The rendering rule"): "claims",
    ("r1-superpowers", "The allowed-character test"): "tests",
    ("r1-superpowers", "The RND-3.6 and RND-5.8"): "tests",
    ("r2-headroom", "The rendering rule"): "claims",
    ("r2-mp4-sonnet", "The new SECURITY-SPEC residual"): "decisions",
    ("r2-mp4-sonnet-builder", "SECURITY-SPEC records"): "decisions",
    ("r2-ponytail", "The build-label rendering"): "tests",
    ("r2-stack", "TECHNICAL-SPEC.md 'Text fields'"): "claims",
    ("r3-mp4", "SECURITY-SPEC records a new"): "decisions",
    ("ref-codex-mp4-1", "The view-level"): "tests",
    ("t2-ideal-v5-sonnet-1", "The new SECURITY-SPEC residual"): "decisions",
    ("t2-ideal-v5-haiku-1", "The retest storage-failure test"): "tests",
    ("t2-mp4-haiku-1", "rounds.md RND-5 says a round closed"): "claims",
    ("t3-ideal-v6-haiku-2", "Result stores no submission"): "earlier",
    ("t3-ideal-v6-opus-1", "SECURITY-SPEC drops the earlier"): "earlier",
    ("t3-ideal-v6-opus-2", "SECURITY-SPEC records result storage"): "earlier",
    ("t3-ideal-v6-sonnet-opusreview-1", "The result storage limit"): "earlier",
    ("t3-ideal-v7-haiku-1", "The result page's case title"): "tests",
    ("t3-ideal-v7-opus-1", "The new Record result journey"): "tests",
    ("t3-openspec-1", "SECURITY-SPEC adds a per-round"): "earlier",
    ("t4-ideal-v8-codex-1", "IPv4-mapped IPv6"): "behaviour",
    ("t4-ideal-v8-codex-1", "The TECHNICAL-SPEC limit-counter note"): "earlier",
    ("t4-ideal-v8-codex-1", "SECURITY-SPEC lists three new residual"): "decisions",
    ("t4-ideal-v8-codex-1", "ACC-3.7's lock/statement-timeout"): "tests",
    ("t4-ideal-v8-haiku-1", "TECHNICAL-SPEC says that after ACC-3"): "behaviour",
    ("t4-ideal-v8-haiku-1", "Against the decision to build"): "earlier",
    ("t4-ideal-v8-opus-1", "The new User Guide storage-failure"): "claims",
    ("t4-ideal-v8-sonnet-1", "The accounts-routes rule still says"): "earlier",
    ("t4-ideal-v8-hermes-1", "canonical_address groups IPv4-mapped"): "behaviour",
    ("t4-mp4-1", "A storage failure while starting"): "behaviour",
    ("t4-mp4-1", "The new sign-in exception"): "earlier",
    ("t4-mp4-codex-1", "The changed technical spec says"): "behaviour",
    ("t4-mp4-codex-1", "ACC-3.1 requires a 429"): "behaviour",
    ("t4-mp4-codex-1", "The technical note says per-address"): "claims",
    ("t3-mp4-sonnet-1", "No test exercises the view's round lock"): "tests",
    ("t4-mp4-haiku-2", "The ACC-3 technical notes were rewritten"): "earlier",
    ("t4-mp4-hermes-1", "Per-address counter rows are created"): "earlier",
    ("t4-mp4-hermes-1", "ACC-3.7's lock/statement-timeout path"): "tests",
    ("t4-mp3-1", "TECHNICAL-SPEC requirement text was rewritten"): "earlier",
    # The starting TECHNICAL-SPEC's accounts-routes rule asks for the 503 on
    # every accounts route once ACC-3 exists, so this one is a false positive.
    ("t4-superpowers-1", "unavailable_on_storage_failure turns"): "false",
    ("t4-superpowers-1", "The candidate rewrote TECHNICAL-SPEC's"): "earlier",
    ("t3-ideal-v8-sonnet-1", "SECURITY-SPEC replaces 'RES must cap"): "earlier",
    ("t3-ideal-v8-codex-1", "The GET builds ResultForm"): "behaviour",
    ("t3-ideal-v8-codex-1", "No unit or e2e test checks"): "tests",
    ("t3-ideal-v8-codex-1", "The User Guide says opening"): "claims",
    ("t3-mp4-haiku-2", "RES-2.6 claims saves racing a retest"): "earlier",
    ("t3-ideal-v8-opus-1", "SECURITY-SPEC leaves an unaccepted open"): "earlier",
}


def finding_kind(finding):
    """The hand-sorted kind of one blind-review finding."""
    for (run, start), kind in FINDINGS.items():
        if finding["run"] == run and finding["summary"].startswith(start):
            return kind
    raise KeyError(f"unsorted finding: {finding['run']}: {finding['summary'][:60]}")


def num(value):
    """A CSV cell as a float, or None when empty."""
    return float(value) if value not in ("", None) else None


def select(task, arm, model, tool="claude"):
    """The counted runs of one arm on one task, model and tool."""
    return [
        r
        for r in RUNS
        if r["task"] == task
        and r["arm"] == arm
        and r["tool"] == tool
        and r["model"] == model
        and r["run"] not in VARIANTS
    ]


def review_text(row):
    """A run's blind-review result in words, or None if it was not reviewed."""
    if row["review_high"] in ("", None):
        return None
    high, medium = int(row["review_high"]), int(row["review_medium"] or 0)
    if not high and not medium:
        return "no High or Medium findings"
    parts = [f"{n} {kind}" for n, kind in ((high, "High"), (medium, "Medium")) if n]
    return " and ".join(parts) + (" finding" if high + medium == 1 else " findings")


def latest_ideal(task, model, tool="claude"):
    """The newest ideal-setup arm with runs on `task`, `model` and `tool`."""
    for version in reversed(VERSIONS):
        if select(task, f"ideal-{version}", model, tool):
            return f"ideal-{version}"
    return None


def median(rows, field):
    """Median of a numeric field over rows that have it, or None."""
    values = [num(r[field]) for r in rows if num(r[field]) is not None]
    return round(statistics.median(values), 2) if values else None


def correct(row):
    """Whether a run passed its whole hidden suite and full verification."""
    return row["hidden_failed"] == "0" and row["verify_passed"] == "True"


RATES = ANALYSIS["opus_cost_split"]["per_million"]


def money(rows):
    """Average estimated dollars: main-session context, subagent context, output."""

    def context(row, who):
        read = num(row[f"{who}_cache_read"]) or 0
        write = num(row[f"{who}_cache_write"]) or 0
        return (read * RATES["cache_read"] + write * RATES["cache_write"]) / 1e6

    def mean(values):
        return round(sum(values) / len(values), 2)

    return {
        "main": mean([context(r, "orchestrator") for r in rows]),
        "subagents": mean([context(r, "subagent") for r in rows]),
        "output": mean([num(r["output_tokens"]) * RATES["output"] / 1e6 for r in rows]),
    }


def setups():
    """Cost, time and quality of each compared setup on each task."""
    out = []
    names = {OPUS: "Opus", SONNET: "Sonnet", HAIKU: "Haiku"}
    for label, arm, model in SETUPS:
        # The model every agent in the setup ran on, or the mix.
        shown = "Opus + Sonnet" if arm == "mp4-sonnet-builder" else names[model]
        entry = {"label": label, "arm": arm, "model": shown}
        for task in TASKS:
            task_arm = latest_ideal(task, model) if arm == "ideal" else arm
            rows = select(task, task_arm, model) if task_arm else []
            if not rows:
                continue
            scored = [r for r in rows if r["mutants_killed"]]
            entry[f"t{task}"] = {
                "arm": task_arm,
                "runs": len(rows),
                "cost": median(rows, "cost_usd"),
                "minutes": median(rows, "wall_min"),
                "subagents": median(rows, "subagent_runs"),
                "correct": sum(1 for r in rows if correct(r)),
                "bugs": sum(int(r["mutants_killed"]) for r in scored),
                "bugs_planted": 5 * len(scored),
                "findings": sum(
                    int(r["review_high"] or 0) + int(r["review_medium"] or 0)
                    for r in rows
                ),
                "money": money(rows) if model == OPUS else None,
            }
        out.append(entry)
    return out


def platforms():
    """MP4 and each ideal version on every model, tool and task that ran it."""
    out = []
    for label, tool, model, reference in PLATFORMS:
        for task in TASKS:
            cells = {"mp4": select(task, reference, model, tool)}
            for version in VERSIONS:
                rows = select(task, f"ideal-{version}", model, tool)
                if rows:
                    cells[version] = rows
            if len(cells) == 1:
                continue
            out.append(
                {
                    "label": label,
                    "task": task,
                    "cells": {
                        key: {
                            "runs": len(rows),
                            "cost": median(rows, "cost_usd"),
                            "minutes": median(rows, "wall_min"),
                            "correct": sum(1 for r in rows if correct(r)),
                        }
                        for key, rows in cells.items()
                        if rows
                    },
                }
            )
    return out


def counted():
    """Every run in the comparison and the ideal evaluation, variants aside."""
    return [r for r in RUNS if r["run"] not in VARIANTS and r["arm"] != "stack"]


def build():
    """The deck's data, as one JSON-ready dictionary."""
    runs = counted()
    scored = [r for r in runs if r["mutants_killed"]]
    kinds = {text: 0 for text in FINDING_KINDS.values()}
    for finding in ANALYSIS["findings"]:
        kinds[FINDING_KINDS[finding_kind(finding)]] += 1
    return {
        "runs_total": len(RUNS),
        "runs_counted": len(runs),
        "runs_correct": sum(1 for r in runs if correct(r)),
        "runs_scored": len(scored),
        "runs_all_bugs": sum(1 for r in scored if r["mutants_killed"] == "5"),
        "findings": kinds,
        "cut_short": {
            "runs": len(CUT_SHORT),
            # Out of every multi-agent run on tasks 3 and 4, these included.
            "of": len(CUT_SHORT)
            + sum(1 for r in runs if r["arm"] in MULTI_AGENT and r["task"] in "34"),
        },
        "runs_high": sum(int(r["review_high"] or 0) for r in runs),
        # Median lines of non-test code each task's candidates changed.
        "code_lines": {
            task: median([r for r in runs if r["task"] == task], "code_lines")
            for task in TASKS
        },
        "headroom_compressed": sorted(
            v["wire_percent"] for v in ANALYSIS["headroom"].values()
        ),
        "setups": setups(),
        "platforms": platforms(),
        "runs": [
            {
                "run": r["run"],
                "task": r["task"],
                "setup": r["arm"],
                "tool": r["tool"],
                "model": r["model"].replace("claude-", "").replace("deepseek/", ""),
                "cost": num(r["cost_usd"]),
                "minutes": num(r["wall_min"]),
                "hidden": f"{r['hidden_passed']}/"
                f"{int(r['hidden_passed']) + int(r['hidden_failed'])}",
                "verified": r["verify_passed"] == "True",
                "bugs": r["mutants_killed"] or None,
                "review": review_text(r),
            }
            for r in RUNS
        ],
    }


def main():
    """Replace the JSON between the deck-data script tags."""
    page = DECK.read_text()
    block = json.dumps(build(), separators=(",", ":"))
    pattern = re.compile(
        r'(<script id="deck-data" type="application/json">)(.*?)(</script>)', re.DOTALL
    )
    assert pattern.search(page), "presentation.html has no deck-data block"
    DECK.write_text(pattern.sub(lambda m: m.group(1) + block + m.group(3), page))
    print(f"wrote {len(block)} characters of deck data")


if __name__ == "__main__":
    main()

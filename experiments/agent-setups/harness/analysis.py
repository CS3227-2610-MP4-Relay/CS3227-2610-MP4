"""Derive the extra results the write-up and slides use: results/analysis.json.

Reads the run outputs in EXP/out: review findings of Medium or higher, headroom's
own compression statistics, and a least-squares split of each single-model Opus
run's reported cost into cache reads, cache writes and output. Run after
aggregate.py.
"""

import csv
import json
import os
import re
from pathlib import Path

EXP = Path(os.environ["EXP"])
RESULTS = Path(__file__).resolve().parent.parent / "results"


def findings(runs):
    """Every Medium or High blind-review finding, with its run and area."""
    found = []
    for run in runs:
        path = EXP / "out" / f"{run}.review.json"
        if not path.exists():
            continue
        verdict = json.loads(path.read_text()).get("verdict", {})
        for finding in verdict.get("findings", []):
            if finding.get("severity") in ("Medium", "High"):
                found.append({"run": run, **finding})
    return found


def headroom(runs):
    """headroom's last reported totals for each run that used its proxy."""
    stats = {}
    for run in runs:
        path = EXP / "out" / f"{run}.headroom.log"
        if not path.exists():
            continue
        log = path.read_text()
        requests = re.findall(r"Total requests:\s+(\d+)", log)
        wire = re.findall(r"Of total wire traffic:\s+([\d.]+)%", log)
        if requests and wire:
            stats[run] = {
                "requests": int(requests[-1]),
                "wire_percent": float(wire[-1]),
            }
    return stats


def report_accuracy(runs):
    """Whether each run's final report states the full-suite count we measured.

    The largest "N passed" in the report is taken as its full-suite claim and
    compared with the pytest count from scoring the same final candidate.
    """
    accuracy = {}
    for run in runs:
        evaluation = json.loads((EXP / "out" / f"{run}.eval.json").read_text())
        report = evaluation["usage"].get("final_report") or ""
        claims = [
            int(n.replace(",", "")) for n in re.findall(r"([\d,]+) passed", report)
        ]
        measured = evaluation["verification"]["pytest"].get("passed")
        if claims and measured:
            accuracy[run] = {
                "reported": max(claims),
                "measured": measured,
                "match": max(claims) == measured,
            }
        else:
            accuracy[run] = {"reported": None, "measured": measured, "match": None}
    return accuracy


def solve(rows):
    """Least-squares fit of cost = read*a + write*b + output*c."""
    size = 3
    matrix = [
        [sum(r[i] * r[j] for r in rows) for j in range(size)] for i in range(size)
    ]
    target = [sum(r[i] * r[3] for r in rows) for i in range(size)]
    augmented = [matrix[i] + [target[i]] for i in range(size)]
    for i in range(size):
        pivot = augmented[i][i]
        augmented[i] = [value / pivot for value in augmented[i]]
        for j in range(size):
            if j != i:
                factor = augmented[j][i]
                augmented[j] = [
                    augmented[j][k] - factor * augmented[i][k] for k in range(size + 1)
                ]
    return [augmented[i][size] for i in range(size)]


def cost_split(runs):
    """The share of Opus cost from cache reads, cache writes and output."""
    rows = []
    for run in runs:
        path = EXP / "out" / f"{run}.eval.json"
        usage = json.loads(path.read_text())["usage"].get("model_usage") or {}
        opus = usage.get("claude-opus-5-5")
        others = [m for m in usage if m not in ("claude-opus-5-5", "claude-haiku-5-5")]
        if opus and not others:
            rows.append(
                (
                    opus["cacheReadInputTokens"],
                    opus["cacheCreationInputTokens"],
                    opus["outputTokens"],
                    opus["costUSD"],
                )
            )
    if len(rows) < 4:
        return None
    read, write, output = solve(rows)
    shares = [
        (
            read * r[0] / (read * r[0] + write * r[1] + output * r[2]),
            write * r[1] / (read * r[0] + write * r[1] + output * r[2]),
            output * r[2] / (read * r[0] + write * r[1] + output * r[2]),
        )
        for r in rows
    ]
    mean = [sum(s[i] for s in shares) / len(shares) for i in range(3)]
    return {
        "runs": len(rows),
        "per_million": {
            "cache_read": read * 1e6,
            "cache_write": write * 1e6,
            "output": output * 1e6,
        },
        "mean_share": {
            "cache_read": mean[0],
            "cache_write": mean[1],
            "output": mean[2],
        },
        "note": "Fitted to Claude Code's reported costs, not published prices.",
    }


def main():
    """Write results/analysis.json from the scored runs listed in runs.csv."""
    with open(RESULTS / "runs.csv") as file:
        runs = [row["run"] for row in csv.DictReader(file)]
    comparison = [run for run in runs if run[:3] in ("r1-", "r2-", "r3-")]
    analysis = {
        "findings": findings(runs),
        "headroom": headroom(runs),
        "opus_cost_split": cost_split(comparison),
        "report_accuracy": report_accuracy(runs),
    }
    (RESULTS / "analysis.json").write_text(json.dumps(analysis, indent=2))
    print(
        f"{len(analysis['findings'])} findings, "
        f"{len(analysis['headroom'])} headroom runs"
    )


if __name__ == "__main__":
    main()

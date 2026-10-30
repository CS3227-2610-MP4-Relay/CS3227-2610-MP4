"""Blind review of one candidate: python review.py <run_id>

Applies the candidate's product changes (source, tests, specs, the two guides) to
a clean copy of the base, under a random label, so the reviewer cannot tell which setup
produced it. A fresh headless Opus session with read-only tools then reviews it
against the issue and decisions with a fixed rubric. The label map stays private.
"""

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

EXP = Path(os.environ["EXP"])
PRIVATE = Path(os.environ["PRIVATE"])
CLAUDE = EXP / "bin" / "claude-2.1.312"
LABELS = PRIVATE / "review" / "labels.json"

RUBRIC = """You are an independent senior reviewer. Review one candidate change to this
Django repository. You cannot run anything; read the code, tests, specs and docs.

The change implements the issue and the human's decisions below. Its diff of
source, tests, specs and the two guides is in `review-diff.patch` at the
repository root, and it is already applied to the working tree, so you can read
the changed files in context. Process artifacts (slice plans, commits, branches,
session logs) are deliberately left out and the change is deliberately applied
uncommitted, so do not report on them; review only the product change.

{task}

Review against the issue, the decisions, the repository's specs and AGENTS.md
writing rules. Look for: behaviour that misses or exceeds the decisions (every
round text input must refuse the nine controls; the marks, joiners and other
scripts must stay allowed), tests that could not fail or miss inputs, specs or
User Guide text that is inaccurate or inconsistent with the code, needless
complexity, and security problems.

End your reply with one JSON object in a ```json block, exactly this shape:
{{"findings": [{{"severity": "High|Medium|Low", "area": "code|tests|specs|docs",
"summary": "one sentence"}}],
"scores": {{"correctness": 1-5, "tests": 1-5, "specs_docs": 1-5,
"simplicity": 1-5, "maintainability": 1-5}},
"mergeable": "yes|after-fixes|no", "summary": "two sentences"}}
High: wrong or unsafe behaviour, or a decision not met. Medium: a real gap a
maintainer must fix before merging. Low: worth fixing, not blocking."""


def git(cwd, *args, check=True):
    """Run git and return its output."""
    return subprocess.run(
        ["git", *args], cwd=cwd, check=check, capture_output=True, text=True
    ).stdout


def task_text():
    """The issue and decisions, without the run's environment notes."""
    prompt = (EXP / "task-prompt.md").read_text()
    return prompt.split("## Environment")[0].strip()


def label_for(run):
    """A stable random label for the run, kept in a private map."""
    labels = json.loads(LABELS.read_text()) if LABELS.exists() else {}
    if run not in labels:
        labels[run] = "cand-" + secrets.token_hex(3)
        LABELS.parent.mkdir(parents=True, exist_ok=True)
        LABELS.write_text(json.dumps(labels, indent=2))
    return labels[run]


def main(run):
    """Review `run` blind and write its review file."""
    meta = json.loads((EXP / "out" / f"{run}.meta.json").read_text())
    candidate = PRIVATE / "evalwt" / run
    label = label_for(run)
    workspace = PRIVATE / "review" / label
    if workspace.exists():
        shutil.rmtree(workspace)
    git(EXP, "clone", "-q", str(EXP / "base"), str(workspace))
    git(workspace, "remote", "remove", "origin")
    git(candidate, "add", "-A", "-N", ".")
    patch = git(
        candidate,
        "diff",
        meta["arm_base"],
        "--",
        "src",
        "workflow/specs",
        "docs/UserGuide.md",
        "docs/DeveloperGuide.md",
        ":(exclude)src/zz_hidden",
    )
    (workspace / "review-diff.patch").write_text(patch)
    git(workspace, "apply", "--whitespace=nowarn", "review-diff.patch")
    prompt = RUBRIC.format(task=task_text())
    done = subprocess.run(  # noqa: PLW1510 - parsed below
        [
            str(CLAUDE),
            "-p",
            prompt,
            "--model",
            "claude-opus-5-5",
            "--effort",
            "high",
            "--output-format",
            "json",
            "--setting-sources",
            "project,local",
            "--strict-mcp-config",
            "--tools",
            "Read,Grep,Glob",
            "--allowedTools",
            "Read,Grep,Glob",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    result = json.loads(done.stdout)
    text = result.get("result") or ""
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    verdict = json.loads(blocks[-1]) if blocks else {"parse_error": text[-500:]}
    review = {
        "run": run,
        "label": label,
        "cost_usd": result.get("total_cost_usd"),
        "duration_s": round((result.get("duration_ms") or 0) / 1000),
        "verdict": verdict,
        "text": text,
    }
    (EXP / "out" / f"{run}.review.json").write_text(json.dumps(review, indent=2))
    findings = verdict.get("findings", [])
    severities = [f.get("severity") for f in findings]
    print(
        f"{run} ({label}): High={severities.count('High')} "
        f"Medium={severities.count('Medium')} Low={severities.count('Low')} "
        f"scores={verdict.get('scores')} mergeable={verdict.get('mergeable')}"
    )


if __name__ == "__main__":
    main(sys.argv[1])

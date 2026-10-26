"""Check every saved session summary against workflow/skills/log.md.

Checks titles, header/model fields, token-table structure, required sections,
file names and numbering. It cannot verify usage values or omitted agent runs.
Exits non-zero on any finding.

Run from the repository root: `python workflow/scripts/check_logs.py`.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "logs"
SECTIONS = (
    "## Requests",
    "## Agent runs",
    "## Decisions and corrections",
    "## Problems",
)
NAME = re.compile(r"^(\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
TOKEN_COLUMNS = (
    "Agent/source",
    "Input",
    "Cached input",
    "Output",
    "Reasoning output",
    "Total",
    "Recorded elapsed span",
)


def _cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _valid_token_table(lines):
    start = next(
        (i for i, line in enumerate(lines) if line.startswith("Tokens:")), None
    )
    if start is None:
        return False
    start += 1
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start + 2 >= len(lines) or tuple(_cells(lines[start])) != TOKEN_COLUMNS:
        return False
    separators = _cells(lines[start + 1])
    if len(separators) != len(TOKEN_COLUMNS) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separators
    ):
        return False
    rows = []
    for line in lines[start + 2 :]:
        if not line.lstrip().startswith("|"):
            break
        rows.append(_cells(line))
    return bool(rows) and all(
        len(row) == len(TOKEN_COLUMNS) and all(row) for row in rows
    )


def findings(path):
    """Return this log file's problems as (path, message) pairs."""
    problems = []
    name = NAME.match(path.name)
    if not name:
        problems.append((path, "file name is not NNN-kebab.md"))
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        problems.append((path, "first line is not a title"))
    for field in ("Slice:", "Tokens:"):
        if not any(line.startswith(field) for line in lines[:6]):
            problems.append((path, f"header has no {field} line"))
    header = next((line for line in lines[:6] if line.startswith("Slice:")), "")
    model = re.search(r"Orchestrator model:([^·]*)", header)
    if not model or not model.group(1).strip():
        problems.append((path, "header has no orchestrator model value"))
    before_requests = (
        lines[: lines.index("## Requests")] if "## Requests" in lines else lines
    )
    if not _valid_token_table(before_requests):
        problems.append(
            (path, "missing or malformed token table immediately after Tokens:")
        )
    for section in SECTIONS:
        if section not in text:
            problems.append((path, f"missing section {section}"))
    return problems


def main():
    """Check every author's folder and report duplicates and gaps."""
    problems = []
    if not LOGS.exists():
        print("0 finding(s): no saved session summaries")
        return 0
    for folder in sorted(p for p in LOGS.iterdir() if p.is_dir()):
        numbers = {}
        for path in sorted(folder.glob("*.md")):
            problems.extend(findings(path))
            match = NAME.match(path.name)
            if match:
                numbers.setdefault(int(match.group(1)), []).append(path.name)
        for number, names in sorted(numbers.items()):
            if len(names) > 1:
                problems.append(
                    (folder, f"number {number:03d} used by {', '.join(names)}")
                )
        expected = list(range(1, len(numbers) + 1))
        gaps = sorted(set(expected) - set(numbers))
        if gaps:
            problems.append((folder, f"no log for number(s) {gaps}"))
    for path, message in problems:
        print(f"{path.relative_to(ROOT)}: {message}")
    print(f"{len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

"""Build presentation.html from the committed results: python build_presentation.py

Reads results/runs.csv and results/analysis.json only, so the slides can be
rebuilt without the run folders. The page is one self-contained HTML file in a
shadcn-like style; it needs the network only for its web font.

Every number on the slides is computed here from those two files. The prose
around them states what the numbers show, so it is reviewed whenever runs are
added.
"""

import csv
import html
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
with open(HERE / "results" / "runs.csv") as runs_file:
    RUNS = list(csv.DictReader(runs_file))
ANALYSIS = json.loads((HERE / "results" / "analysis.json").read_text())
TEMPLATE = (HERE / "harness" / "presentation_template.html").read_text()

OPUS, SONNET, HAIKU = "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"
DEEPSEEK = "deepseek/deepseek-v4.1-flash"
TASKS = {"1": "Task 1 · #68", "2": "Task 2 · #16"}
# A variant run: Opus reviewers on a Haiku session. Reported, not pooled.
VARIANTS = {"i3-haiku-opusreview-1"}
MINUS = chr(0x2212)

# Each Medium-or-higher blind-review finding, sorted by hand into the kind of
# gap it is, keyed by run and the start of its summary. build() fails on a
# finding with no kind, so new runs get sorted before the slides change.
FINDING_KINDS = {
    "claims": "spec text claiming more than the code or tests do",
    "decisions": "a decision or accepted risk missing or misrecorded",
    "tests": "an old test weakened, or a coverage gap",
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
}


def finding_kind(finding):
    """The hand-sorted kind of one blind-review finding."""
    for (run, start), kind in FINDINGS.items():
        if finding["run"] == run and finding["summary"].startswith(start):
            return kind
    raise KeyError(f"unsorted finding: {finding['run']}: {finding['summary'][:60]}")


# (label, arm, session model, group, what it is). The stack arm (all three
# add-ons at once) ran on task 1 only and is left out: each add-on is compared
# on its own.
SETUPS = [
    ("MP4 baseline", "mp4", OPUS, "Workflow", "builder, verifier, security-reviewer"),
    (
        "MP3 six roles",
        "mp3",
        OPUS,
        "Workflow",
        "writers, critic, implementer, reviewers",
    ),
    ("Solo session", "solo", OPUS, "Workflow", "one session plays every MP4 role"),
    (
        "MP4, Sonnet builder",
        "mp4-sonnet-builder",
        OPUS,
        "Model mix",
        "Opus coordinator and reviewers",
    ),
    ("MP4, all Sonnet", "mp4-sonnet", SONNET, "Model mix", "every role on Sonnet"),
    ("superpowers", "superpowers", OPUS, "Methodology", "obra/superpowers skills"),
    ("spec-kit", "spec-kit", OPUS, "Methodology", "GitHub's spec-driven toolkit"),
    ("MP4 + caveman", "caveman", OPUS, "Add-on", "terse-output plugin"),
    ("MP4 + ponytail", "ponytail", OPUS, "Add-on", "smallest-change plugin"),
    ("MP4 + headroom", "headroom", OPUS, "Add-on", "context-compressing proxy"),
    ("Ideal v1", "ideal-v1", OPUS, "Ideal", "first lean slice"),
    ("Ideal v5", "ideal-v5", OPUS, "Ideal", "portable, project-independent"),
]


def num(value):
    """A CSV cell as a float, or None when empty."""
    return float(value) if value not in ("", None) else None


def esc(text):
    """HTML-escape text."""
    return html.escape(str(text))


def signed(ratio):
    """A change as a signed percentage with a true minus sign."""
    return f"{ratio:+.0%}".replace("-", MINUS)


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


def median(rows, field):
    """Median of a numeric field over rows that have it."""
    values = [num(r[field]) for r in rows if num(r[field]) is not None]
    return statistics.median(values) if values else None


def correct(row):
    """Whether a run passed its whole hidden suite and full verification."""
    return row["hidden_failed"] == "0" and row["verify_passed"] == "True"


def base(task, field):
    """MP4's median of `field` on `task`."""
    return median(select(task, "mp4", OPUS), field)


# --- Marks ------------------------------------------------------------------


def bar_path(x, y, length, thickness, radius=4):
    """A horizontal bar, square at the baseline and rounded at its tip."""
    r = min(radius, length / 2, thickness / 2)
    end = x + length
    return (
        f"M{x:.1f},{y:.1f}H{end - r:.1f}"
        f"A{r},{r} 0 0 1 {end:.1f},{y + r:.1f}"
        f"V{y + thickness - r:.1f}"
        f"A{r},{r} 0 0 1 {end - r:.1f},{y + thickness:.1f}"
        f"H{x:.1f}Z"
    )


def legend(keys):
    """A legend row of (series class, label) pairs."""
    items = "".join(
        f'<span class="key"><i class="{role}"></i>{esc(label)}</span>'
        for role, label in keys
    )
    return f'<div class="legend">{items}</div>'


def svg_open(width, height, title):
    """The opening tag of a chart."""
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{esc(title)}">'
    )


def table(head, rows, cls=""):
    """A data table; cells are escaped unless wrapped in Raw."""
    head_html = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{c.html if isinstance(c, Raw) else esc(c)}</td>" for c in row)
        + "</tr>"
        for row in rows
    )
    return (
        f'<table class="{cls}"><thead><tr>{head_html}</tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


class Raw:
    """A table cell that is already HTML."""

    def __init__(self, markup):
        self.html = markup


# --- Charts -----------------------------------------------------------------


def ratio_chart(field, fmt, title):
    """Each setup's median as a share of MP4's on the same task, both tasks.

    Two thin bars per setup grow from 0; a solid line marks MP4 at 100%. The
    tip label is the median and its change from MP4.
    """
    rows = []
    for label, arm, model, _, _ in SETUPS:
        cells = {}
        for task in TASKS:
            runs = select(task, arm, model)
            if runs and base(task, field):
                value = median(runs, field)
                cells[task] = (value / base(task, field), value, runs)
        if cells:
            rows.append((label, arm, cells))
    rows.sort(key=lambda row: (row[2].get("1") or row[2]["2"])[0])
    top = max(1.2, max(c[0] for row in rows for c in row[2].values()) * 1.05)
    left, right, width, bar, gap, band = 180, 150, 900, 11, 2, 32
    scale = (width - left - right) / top
    height = band * len(rows) + 44
    parts = [svg_open(width, height, title)]
    tick = 0.0
    while tick <= top:
        x = left + tick * scale
        role = "grid base" if tick == 1 else "grid"
        parts.append(
            f'<line class="{role}" x1="{x:.1f}" x2="{x:.1f}" y1="6" '
            f'y2="{height - 30}"/><text class="tick" x="{x:.1f}" '
            f'y="{height - 12}" text-anchor="middle">{tick:.0%}</text>'
        )
        tick += 0.25
    for index, (label, arm, cells) in enumerate(rows):
        y0 = 10 + index * band
        strong = " strong" if arm == "mp4" else ""
        parts.append(
            f'<text class="label{strong}" x="{left - 12}" y="{y0 + bar + 5}" '
            f'text-anchor="end">{esc(label)}</text>'
        )
        for slot, task in enumerate(TASKS):
            y = y0 + slot * (bar + gap)
            if task not in cells:
                parts.append(
                    f'<text class="tick" x="{left + 6}" y="{y + bar - 2}">'
                    "not run on this task</text>"
                )
                continue
            ratio, value, runs = cells[task]
            span = max(ratio * scale, 2)
            values = sorted(num(r[field]) for r in runs)
            spread = (
                f", range {fmt(values[0])} to {fmt(values[-1])}"
                if len(values) > 1
                else ""
            )
            count = f"{len(runs)} run{'s' if len(runs) > 1 else ''}"
            tip = (
                f"{label}, {TASKS[task]}: {fmt(value)}, median of {count}{spread}; "
                f"{ratio:.0%} of MP4"
            )
            change = "" if arm == "mp4" else f" · {signed(ratio - 1)}"
            parts.append(
                f'<path class="s{slot + 1}" d="{bar_path(left, y, span, bar)}" '
                f'tabindex="0" data-tip="{esc(tip)}"/>'
                f'<text class="value-small" x="{left + span + 6:.1f}" '
                f'y="{y + bar - 2}">{esc(fmt(value))}{change}</text>'
            )
    parts.append("</svg>")
    return legend([("s1", TASKS["1"]), ("s2", TASKS["2"])]) + "".join(parts)


RATES = ANALYSIS["opus_cost_split"]["per_million"]


def money_parts(runs):
    """Average estimated dollars per run: main-session context, subagents, output."""

    def mean(values):
        return sum(values) / len(values) if values else 0.0

    def context(row, who):
        read = num(row[f"{who}_cache_read"]) or 0
        write = num(row[f"{who}_cache_write"]) or 0
        return (read * RATES["cache_read"] + write * RATES["cache_write"]) / 1e6

    return (
        mean([context(r, "orchestrator") for r in runs]),
        mean([context(r, "subagent") for r in runs]),
        mean([num(r["output_tokens"]) * RATES["output"] / 1e6 for r in runs]),
    )


MONEY_SERIES = [
    ("s1", "Main session: reading and caching context"),
    ("s2", "Subagents: reading and caching context"),
    ("s3", "Output written"),
]


def opus_setups():
    """The setups whose every session ran on Opus."""
    return [s for s in SETUPS if s[2] == OPUS and s[1] != "mp4-sonnet-builder"]


def money_chart():
    """Stacked bars per Opus setup and task: where an average run's money went."""
    groups = []
    for task in TASKS:
        rows = []
        for label, arm, model, _, _ in opus_setups():
            runs = select(task, arm, model)
            if runs:
                rows.append((label, money_parts(runs), len(runs)))
        rows.sort(key=lambda row: -sum(row[1]))
        if rows:
            groups.append((task, rows))
    top = max(sum(parts) for _, rows in groups for _, parts, _ in rows)
    left, right, width, bar, band = 180, 70, 900, 16, 26
    scale = (width - left - right) / top
    height = sum(band * len(rows) + 34 for _, rows in groups) + 30
    marks, y = [], 4
    for task, rows in groups:
        marks.append(
            f'<text class="label strong" x="0" y="{y + 16}">{esc(TASKS[task])}</text>'
        )
        y += 28
        for label, parts, count in rows:
            marks.append(
                f'<text class="label" x="{left - 12}" y="{y + bar - 3}" '
                f'text-anchor="end">{esc(label)}</text>'
            )
            x = left
            for (role, name), dollars in zip(MONEY_SERIES, parts, strict=True):
                span = dollars * scale
                if span < 1:
                    continue
                tip = (
                    f"{label}, {TASKS[task]}: {name.lower()}, about ${dollars:.2f} "
                    f"(average of {count} run{'s' if count > 1 else ''})"
                )
                marks.append(
                    f'<rect class="{role}" x="{x:.1f}" y="{y}" '
                    f'width="{max(span - 2, 1):.1f}" height="{bar}" tabindex="0" '
                    f'data-tip="{esc(tip)}"/>'
                )
                x += span
            marks.append(
                f'<text class="value-small" x="{x + 6:.1f}" y="{y + bar - 3}">'
                f"${sum(parts):.2f}</text>"
            )
            y += band
        y += 6
    grid = []
    step = 2 if top < 16 else 4
    for tick in range(0, int(top) + step, step):
        x = left + tick * scale
        if x > width - right + 1:
            break
        grid.append(
            f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="30" y2="{y - 6}"/>'
            f'<text class="tick" x="{x:.1f}" y="{y + 12}" text-anchor="middle">'
            f"${tick}</text>"
        )
    return (
        legend(MONEY_SERIES)
        + svg_open(
            width,
            height,
            "Estimated cost of an average run, split by where it was spent",
        )
        + "".join(grid + marks)
        + "</svg>"
    )


# --- The ideal setup on each platform ----------------------------------------

PLATFORMS = [
    ("Opus · Claude Code", "claude", OPUS, "mp4"),
    ("Sonnet · Claude Code", "claude", SONNET, "mp4-sonnet"),
    ("Haiku · Claude Code", "claude", HAIKU, "mp4-haiku"),
    ("DeepSeek · Codex", "codex", DEEPSEEK, "mp4-inherit"),
    ("DeepSeek · Hermes", "hermes", DEEPSEEK, "mp4-inherit"),
]
VERSIONS = ["v1", "v2", "v3", "v4", "v5", "v6"]


def platform_cells(task, tool, model, reference):
    """MP4's runs and each ideal version's runs on one platform and task."""
    cells = {"reference": select(task, reference, model, tool)}
    for version in VERSIONS:
        runs = select(task, f"ideal-{version}", model, tool)
        if runs:
            cells[version] = runs
    return cells


def ideal_rows():
    """(platform, task, cells) for every platform and task with ideal runs."""
    rows = []
    for name, tool, model, reference in PLATFORMS:
        for task in TASKS:
            cells = platform_cells(task, tool, model, reference)
            if len(cells) > 1:
                rows.append((name, task, cells))
    return rows


def ideal_chart():
    """Ideal v1 and the latest version, as a share of MP4 on the same platform."""
    series = [("s1", "Ideal v1"), ("s3", "Latest version run")]
    rows = ideal_rows()
    left, right, width, bar, gap, band = 240, 190, 900, 12, 2, 40
    # Only v1 and the latest version are drawn, so only they set the axis.
    ratios = [
        median(cells[v], "cost_usd") / median(cells["reference"], "cost_usd")
        for _, _, cells in rows
        if cells["reference"]
        for v in ("v1", [v for v in VERSIONS if v in cells][-1])
        if v in cells
    ]
    top = max(1.25, max(ratios) * 1.05)
    scale = (width - left - right) / top
    height = band * len(rows) + 44
    parts = [svg_open(width, height, "Ideal setup cost as a share of MP4")]
    for tick in [t / 4 for t in range(int(top * 4) + 1)]:
        x = left + tick * scale
        role = "grid base" if tick == 1 else "grid"
        parts.append(
            f'<line class="{role}" x1="{x:.1f}" x2="{x:.1f}" y1="6" '
            f'y2="{height - 30}"/><text class="tick" x="{x:.1f}" '
            f'y="{height - 12}" text-anchor="middle">{tick:.0%}</text>'
        )
    for index, (name, task, cells) in enumerate(rows):
        y0 = 10 + index * band
        parts.append(
            f'<text class="label" x="{left - 12}" y="{y0 + bar + 5}" '
            f'text-anchor="end">{esc(name)} · task {task}</text>'
        )
        ref = median(cells["reference"], "cost_usd")
        latest = [v for v in VERSIONS if v in cells][-1]
        shown = [("v1", "s1"), (latest, "s3")] if latest != "v1" else [("v1", "s1")]
        for slot, (version, role) in enumerate(shown):
            y = y0 + slot * (bar + gap)
            if version not in cells:
                parts.append(
                    f'<text class="tick" x="{left + 6}" y="{y + bar - 2}">'
                    "v1 not run on this task</text>"
                )
                continue
            cost = median(cells[version], "cost_usd")
            if not ref:
                parts.append(
                    f'<text class="tick" x="{left + 6}" y="{y + bar - 2}">'
                    f"{version}: ${cost:.2f}, no MP4 run to compare</text>"
                )
                continue
            ratio = cost / ref
            span = max(ratio * scale, 2)
            tip = (
                f"{name}, task {task}: ideal {version} ${cost:.2f} against MP4 "
                f"${ref:.2f} ({ratio:.0%})"
            )
            parts.append(
                f'<path class="{role}" d="{bar_path(left, y, span, bar)}" '
                f'tabindex="0" data-tip="{esc(tip)}"/>'
                f'<text class="value-small" x="{left + span + 6:.1f}" '
                f'y="{y + bar - 2}">{version} ${cost:.2f} vs ${ref:.2f}</text>'
            )
    parts.append("</svg>")
    return legend(series) + "".join(parts)


# --- Quality ----------------------------------------------------------------


def counted():
    """Every run in the comparison and ideal evaluation, variants and stack aside."""
    return [r for r in RUNS if r["run"] not in VARIANTS and r["arm"] != "stack"]


# --- Page -------------------------------------------------------------------


def slide(title, body, kicker=""):
    """One slide section."""
    kick = f'<p class="kicker">{esc(kicker)}</p>' if kicker else ""
    return f'<section class="slide">{kick}<h2>{esc(title)}</h2>{body}</section>'


def card(title, body):
    """A titled card."""
    return f'<div class="card"><p class="card-title">{esc(title)}</p>{body}</div>'


def bullets(items):
    """A list of already-escaped HTML items."""
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def flow(steps, cls=""):
    """Numbered step boxes: (title, detail) pairs."""
    boxes = "".join(
        f'<div class="step"><span class="badge">{i}</span><p><b>{esc(a)}</b><br>'
        f'<span class="muted">{esc(b)}</span></p></div>'
        for i, (a, b) in enumerate(steps, start=1)
    )
    return f'<div class="flow {cls}">{boxes}</div>'


def share(task, arm, model=OPUS):
    """A setup's median cost on a task as a share of MP4's, or None."""
    runs = select(task, arm, model)
    return median(runs, "cost_usd") / base(task, "cost_usd") if runs else None


def pct_range(values):
    """A range of shares as signed percentage changes, low to high."""
    values = sorted(v for v in values if v is not None)
    if not values:
        return "n/a"
    low, high = signed(values[0] - 1), signed(values[-1] - 1)
    return low if low == high else f"{low} to {high}"


def less_range(values):
    """A range of shares below 1 as "a–b% less"; mixed ranges stay signed."""
    values = sorted(v for v in values if v is not None)
    if not values:
        return "n/a"
    if values[-1] >= 1:
        return pct_range(values)
    low, high = round((1 - values[-1]) * 100), round((1 - values[0]) * 100)
    return f"{low}% less" if low == high else f"{low}–{high}% less"


def share_range(values):
    """A range of shares as "a–b%" of the reference."""
    values = sorted(v for v in values if v is not None)
    low, high = round(values[0] * 100), round(values[-1] * 100)
    return f"{low}%" if low == high else f"{low}–{high}%"


def hero(value, label):
    """A big number with a short label under it."""
    return (
        f'<div class="hero-stat"><p class="hero-value">{esc(value)}</p>'
        f'<p class="hero-label">{esc(label)}</p></div>'
    )


def headline(title, lead, body="", kicker=""):
    """A finding slide: the finding as the title, one plain sentence, evidence."""
    kick = f'<p class="kicker">{esc(kicker)}</p>' if kicker else ""
    return (
        f'<section class="slide">{kick}<h2 class="finding">{esc(title)}</h2>'
        f'<p class="lead">{lead}</p>{body}</section>'
    )


def kinds_chart(counts):
    """One bar per kind of review finding, longest first."""
    rows = sorted(counts.items(), key=lambda item: -item[1])
    left, width, bar, band = 360, 900, 18, 34
    top = max(count for _, count in rows)
    scale = (width - left - 60) / top
    height = band * len(rows) + 8
    parts = [svg_open(width, height, "Review findings by kind")]
    for index, (label, count) in enumerate(rows):
        y = 6 + index * band
        span = max(count * scale, 2)
        parts.append(
            f'<text class="label" x="{left - 12}" y="{y + bar - 4}" '
            f'text-anchor="end">{esc(label[:1].upper() + label[1:])}</text>'
            f'<path class="s1" d="{bar_path(left, y, span, bar)}" tabindex="0" '
            f'data-tip="{esc(label)}: {count}"/>'
            f'<text class="value-small" x="{left + span + 8:.1f}" '
            f'y="{y + bar - 4}">{count}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def addon_chart():
    """Each add-on's cost as a share of MP4's: task 1 dot, task 2 dot, joined."""
    names = [("caveman", "MP4 + caveman"), ("ponytail", "MP4 + ponytail")]
    names.append(("headroom", "MP4 + headroom"))
    left, right, width, band = 180, 40, 900, 46
    low, high = 0.4, 1.2
    scale = (width - left - right) / (high - low)
    height = band * len(names) + 40

    def x(share_):
        return left + (share_ - low) * scale

    parts = [svg_open(width, height, "Add-on cost as a share of MP4, by task")]
    tick = low
    while tick <= high + 1e-9:
        role = "grid base" if abs(tick - 1) < 1e-9 else "grid"
        parts.append(
            f'<line class="{role}" x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="4" '
            f'y2="{height - 28}"/><text class="tick" x="{x(tick):.1f}" '
            f'y="{height - 10}" text-anchor="middle">{tick:.0%}</text>'
        )
        tick += 0.2
    for index, (arm, label) in enumerate(names):
        y = 22 + index * band
        one, two = share("1", arm), share("2", arm)
        parts.append(
            f'<text class="label" x="{left - 14}" y="{y + 5}" text-anchor="end">'
            f"{esc(label)}</text>"
            f'<line class="link" x1="{x(one):.1f}" x2="{x(two):.1f}" y1="{y}" '
            f'y2="{y}"/>'
        )
        for value, role, task in ((one, "s1", "1"), (two, "s2", "2")):
            tip = f"{label}, {TASKS[task]}: {value:.0%} of MP4's cost"
            parts.append(
                f'<circle class="{role} dot-ring" cx="{x(value):.1f}" cy="{y}" '
                f'r="7" tabindex="0" data-tip="{esc(tip)}"/>'
                f'<text class="value-small" x="{x(value):.1f}" y="{y - 13}" '
                f'text-anchor="middle">{signed(value - 1)}</text>'
            )
    parts.append("</svg>")
    return legend([("s1", TASKS["1"]), ("s2", TASKS["2"])]) + "".join(parts)


def check_cells(rows):
    """Correct, bugs caught and Medium-or-higher findings for one task's runs."""
    if not rows:
        return ["", "", ""]
    right = sum(1 for r in rows if correct(r))
    scored = [r for r in rows if r["mutants_killed"]]
    caught = sum(int(r["mutants_killed"]) for r in scored)
    findings = sum(
        int(r["review_high"] or 0) + int(r["review_medium"] or 0) for r in rows
    )
    mark = "ok" if right == len(rows) else "bad"
    return [
        Raw(f'<span class="{mark}">{right}/{len(rows)}</span>'),
        Raw(
            f'<span class="{"ok" if caught == 5 * len(scored) else "bad"}">'
            f"{caught}/{5 * len(scored)}</span>"
        ),
        str(findings),
    ]


def build():
    """Assemble the slides and write presentation.html."""
    runs = counted()
    right = sum(1 for r in runs if correct(r))
    scored = [r for r in runs if r["mutants_killed"]]
    all_bugs = sum(1 for r in scored if r["mutants_killed"] == "5")
    compared = [
        r
        for _, arm, model, _, _ in SETUPS
        for t in TASKS
        for r in select(t, arm, model)
    ]
    compared_high = sum(int(r["review_high"] or 0) for r in compared)
    single = ["solo", "superpowers", "spec-kit", "ideal-v1", "ideal-v5"]
    single_shares = [share(t, a) for t in TASKS for a in single]
    time_shares = [
        median(select(t, a, OPUS), "wall_min") / base(t, "wall_min")
        for t in TASKS
        for a in single
        if select(t, a, OPUS)
    ]
    addons = ("caveman", "ponytail", "headroom")
    addon_shares = {t: [share(t, a) for a in addons] for t in TASKS}
    mp4_money = {t: money_parts(select(t, "mp4", OPUS)) for t in TASKS}
    sub_share = [m[1] / sum(m) for m in mp4_money.values()]
    mp4_subs = sorted(
        int(num(r["subagent_runs"])) for t in TASKS for r in select(t, "mp4", OPUS)
    )
    findings = ANALYSIS["findings"]
    kinds = [finding_kind(f) for f in findings]
    headroom = [v["wire_percent"] for v in ANALYSIS["headroom"].values()]

    def cost(task, arm, model=OPUS, tool="claude"):
        return f"${median(select(task, arm, model, tool), 'cost_usd'):.2f}"

    def minutes(task, arm, model=OPUS):
        return f"{median(select(task, arm, model), 'wall_min'):.0f} min"

    slides = []
    slides.append(
        '<section class="slide title-slide">'
        '<p class="kicker">Experiment #31 · zheng-jj · October 2026</p>'
        "<h1>What does an agent workflow cost, and what does it buy?</h1>"
        '<p class="lead">We ran twelve ways of setting up a coding agent on two '
        f"real Relay tasks, {len(RUNS)} runs in all, with everything else held "
        "fixed. Then we built a setup from what we learned and tested it on five "
        "models.</p></section>"
    )
    answer = [
        ("Every setup wrote correct code.", f"{right}/{len(runs)} runs correct"),
        (
            "Building in one session costs about half, and takes about half the time.",
            less_range(single_shares),
        ),
        (
            "The money goes on hand-offs between agents.",
            f"about {max(sub_share):.0%} of MP4's cost",
        ),
        (
            "The popular add-ons didn't pay off.",
            f"{pct_range(addon_shares['2'])} on task 2",
        ),
        (
            "Methodology plugins are one session with extra steps.",
            "same cost as one session",
        ),
        (
            "Sonnet is enough for this work.",
            f"{cost('1', 'mp4-sonnet', SONNET)} vs {cost('1', 'mp4')}",
        ),
    ]
    rows = "".join(
        f'<div class="answer"><span class="badge">{i}</span>'
        f'<p class="answer-text">{esc(text)}</p>'
        f'<p class="answer-stat">{esc(number)}</p></div>'
        for i, (text, number) in enumerate(answer, start=1)
    )
    slides.append(
        slide(
            "Six findings",
            f'<div class="answers">{rows}</div>'
            '<p class="lead small-gap">So our ideal setup builds in one session and '
            "keeps one independent reviewer. It gives the same quality at about "
            "half MP4's cost.</p>",
            "The short answer",
        )
    )
    groups = {}
    for label, _, _, group, what in SETUPS:
        groups.setdefault(group, []).append((label, what))
    cards = "".join(
        card(
            group,
            "".join(
                f'<p class="item"><b>{esc(a)}</b><br>'
                f'<span class="muted">{esc(b)}</span></p>'
                for a, b in items
            ),
        )
        for group, items in groups.items()
    )
    slides.append(
        slide(
            "Twelve setups",
            f'<div class="grid three">{cards}</div>'
            '<p class="muted small">Opus 5.5 unless a setup says otherwise. Each '
            "add-on runs on top of MP4, one at a time.</p>",
            "What we compared",
        )
    )
    slides.append(
        slide(
            "Two real Relay tasks",
            '<div class="grid two">'
            + card(
                "Task 1 · #68 · small",
                "<p>Refuse hidden text-direction characters in 12 text "
                "inputs.</p>"
                '<p class="muted">About 15 lines of code. 132 hidden tests. '
                "23 comparison runs.</p>",
            )
            + card(
                "Task 2 · #16 · larger",
                "<p>Let a coordinator request a retest: a new page, form and "
                "service, with a row lock, a build cap and label rules.</p>"
                '<p class="muted">About 120 lines of code. 27 hidden tests. '
                f"{sum(1 for r in RUNS if r['task'] == '2')} runs.</p>",
            )
            + "</div>"
            '<p class="lead">Same prompt, same decisions, same tools and '
            "permissions. Each run got its own clean copy of the repository.</p>",
            "What we compared",
        )
    )
    slides.append(
        slide(
            "How we scored each run",
            flow(
                [
                    ("Hidden tests", "written before any run"),
                    ("Verification", "lint, checks, full test suite"),
                    ("Planted bugs", "its own tests must catch 5"),
                    ("Blind review", "a fresh reviewer, no setup name"),
                    ("Audit", "spec first, commits, no peeking"),
                ],
                "five",
            )
            + '<p class="muted small">Cost is each tool\'s own report at list '
            "prices. Time is wall-clock.</p>",
            "What we compared",
        )
    )
    slides.append(
        headline(
            "Every setup wrote correct code",
            "On both tasks, every compared setup passed every hidden test and "
            "caught every planted bug. So the choice of setup changes cost and "
            "speed, not correctness.",
            '<div class="heroes">'
            + hero(f"{right} / {len(runs)}", "runs passed every hidden test")
            + hero(f"{all_bugs} / {len(scored)}", "caught all 5 planted bugs")
            + hero(str(compared_high), "High issues in the compared setups")
            + "</div>",
            "Finding 1",
        )
    )
    quality = [
        (
            label,
            *check_cells(select("1", arm, model)),
            *check_cells(select("2", arm, model)),
        )
        for label, arm, model, _, _ in SETUPS
    ]
    slides.append(
        slide(
            "Quality, setup by setup",
            '<div class="scroll">'
            + table(
                [
                    "Setup",
                    "T1 correct",
                    "T1 bugs caught",
                    "T1 findings",
                    "T2 correct",
                    "T2 bugs caught",
                    "T2 findings",
                ],
                quality,
                "wide checks",
            )
            + "</div>"
            '<p class="muted small">Findings: blind-review findings of Medium or '
            "High. Blank: not run on that task.</p>",
            "Finding 1",
        )
    )
    slides.append(
        headline(
            "Reviews still found gaps, but not bugs",
            f"Across all {len(RUNS)} runs, the blind reviews raised {len(findings)} "
            "Medium or High findings. None was wrong behaviour. Most were records "
            "that drifted from the code.",
            '<div class="card">'
            + kinds_chart(
                {text: kinds.count(kind) for kind, text in FINDING_KINDS.items()}
            )
            + "</div>",
            "Finding 1",
        )
    )
    slides.append(
        headline(
            "Building in one session costs about half",
            f"Solo, superpowers, spec-kit and the ideal setup cost "
            f"{less_range(single_shares)} than MP4, on both tasks.",
            '<div class="card">'
            + ratio_chart("cost_usd", lambda v: f"${v:.2f}", "Cost relative to MP4")
            + '<p class="muted small">Median cost per run, as a share of MP4 on '
            "the same task. The dark line is MP4.</p></div>",
            "Finding 2",
        )
    )
    slides.append(
        headline(
            "…and takes about half the time",
            f"The same setups finished in {share_range(time_shares)} of MP4's time.",
            '<div class="card">'
            + ratio_chart("wall_min", lambda v: f"{v:.0f} min", "Time relative to MP4")
            + "</div>",
            "Finding 2",
        )
    )
    slides.append(
        headline(
            "The money goes on hand-offs",
            f"About {max(sub_share):.0%} of an MP4 run's cost "
            "is subagents reading the repository again. The single-session setups "
            "barely pay this.",
            '<div class="card">'
            + money_chart()
            + '<p class="muted small">Estimated from each run\'s tokens, with rates '
            "fitted to the Opus runs.</p></div>",
            "Finding 3",
        )
    )
    slides.append(
        slide(
            "Why hand-offs are expensive",
            '<div class="grid two">'
            + card(
                "MP4: a new agent for each step",
                '<div class="lane">'
                '<span class="node main">Coordinator</span>'
                '<span class="node sub">Builder</span>'
                '<span class="node sub">Builder</span>'
                '<span class="node sub">Verifier</span>'
                '<span class="node sub">Security reviewer</span>'
                '<span class="node sub">Builder (repair)</span>'
                '<span class="node sub">Verifier (recheck)</span></div>'
                "<p>Each subagent starts empty. It reads the rules, the specs "
                "and the code again, and pays to cache them again. MP4 started "
                f"{mp4_subs[0]}–{mp4_subs[-1]} of them per run.</p>",
            )
            + card(
                "One session: read once",
                '<div class="lane"><span class="node main">One session: spec, '
                'tests, code, docs</span><span class="node sub">One reviewer'
                "</span></div>"
                "<p>The session keeps what it has read for the whole build. Only "
                "the reviewer starts fresh, and that fresh view is the point of "
                "having it.</p>",
            )
            + "</div>",
            "Finding 3",
        )
    )
    slides.append(
        headline(
            "The add-ons didn't pay off",
            f"On task 1 they looked {less_range(addon_shares['1'])} than MP4. On "
            f"task 2 the saving was gone: {pct_range(addon_shares['2'])}. None "
            "changed quality.",
            '<div class="card">'
            + addon_chart()
            + '<p class="muted small">What actually moved the cost was how many '
            "subagents the coordinator started, not the add-on.</p></div>",
            "Finding 4",
        )
    )
    caveman = {t: median(select(t, "caveman", OPUS), "output_tokens") for t in TASKS}
    mp4_out = {t: median(select(t, "mp4", OPUS), "output_tokens") for t in TASKS}
    slides.append(
        slide(
            "The add-ons, one at a time",
            '<div class="grid three">'
            + card(
                "caveman",
                '<p class="muted">Promise: shorter output.</p>'
                f"<p>Output fell {1 - caveman['1'] / mp4_out['1']:.0%} on task 1 "
                f"and {1 - caveman['2'] / mp4_out['2']:.0%} on task 2. But output "
                "is only about a fifth of the bill.</p>"
                '<p><span class="badge">Small effect</span></p>',
            )
            + card(
                "ponytail",
                '<p class="muted">Promise: the smallest change.</p>'
                "<p>Leaner tests on task 1, same quality. The saving didn't hold "
                "on task 2.</p>"
                '<p><span class="badge">No lasting effect</span></p>',
            )
            + card(
                "headroom",
                '<p class="muted">Promise: compressed context.</p>'
                f"<p>It compressed only {min(headroom):.1f}–{max(headroom):.1f}% "
                "of traffic, and it routes your API key through a proxy.</p>"
                '<p><span class="badge">Not worth the risk</span></p>',
            )
            + "</div>",
            "Finding 4",
        )
    )
    slides.append(
        slide(
            "Methodology plugins are one session with extra steps",
            '<div class="grid two">'
            + card(
                "superpowers",
                f"<p>{cost('1', 'superpowers')} and {cost('2', 'superpowers')}. "
                "Planning and test-first habits, built in one session. One review "
                "subagent.</p>",
            )
            + card(
                "spec-kit",
                f"<p>{cost('1', 'spec-kit')} and {cost('2', 'spec-kit')}. A "
                "spec, plan and task list first, then one session builds. No "
                "independent review.</p>",
            )
            + card(
                "MP3: six roles",
                f"<p>{cost('1', 'mp3')} and {cost('2', 'mp3')}. More roles and "
                "more tests, but nothing extra found. On task 2 it cost as much "
                "as MP4.</p>",
            )
            + card(
                "Solo: one session plays every role",
                f"<p>{cost('1', 'solo')}, the cheapest Opus setup on task 1. Its "
                "weakness: it reviews its own work.</p>",
            )
            + "</div>"
            '<p class="muted small">Costs are medians for task 1 and task 2 '
            "on Opus.</p>",
            "Finding 5",
        )
    )
    slides.append(
        headline(
            "Sonnet is enough",
            "Sonnet passed every check on both tasks, at a fraction of Opus's cost.",
            '<div class="heroes">'
            + hero(
                cost("1", "mp4-sonnet", SONNET),
                f"MP4 on Sonnet, vs {cost('1', 'mp4')} on Opus",
            )
            + hero(cost("2", "ideal-v6", SONNET), "ideal setup on Sonnet, task 2")
            + hero("0", "correctness lost")
            + "</div>",
            "Finding 6",
        )
    )
    slides.append(
        slide(
            "The ideal setup: one session builds, one reviewer checks",
            flow(
                [
                    ("Specify", "requirements first, short plan"),
                    ("Build", "tests first; test every value"),
                    ("Check", "every mention, old test and decision"),
                    ("Freeze", "full verification once"),
                    ("Review", "one independent reviewer"),
                    ("Repair", "two rounds, then ask"),
                ],
                "six",
            )
            + '<div class="grid two">'
            + card(
                "AGENT_PROFILE",
                "<p><b>strong</b> for Opus or Sonnet: the steps as written.</p>"
                "<p><b>guarded</b> for anything else, or when unset: a checklist, "
                "hard stops, and numbers only from commands actually run.</p>",
            )
            + card(
                "One file per project",
                "<p><code>project.md</code> says how to verify, where specs, docs "
                "and accepted risks live, and the size budget. Everything else is "
                "the same in every repository and every tool.</p>",
            )
            + "</div>",
            "The ideal setup",
        )
    )
    slides.append(
        slide(
            "Every rule comes from a run that went wrong",
            table(
                ["Rule", "What happened without it"],
                [
                    ("Build in one session", "Hand-offs cost about half of MP4."),
                    (
                        "Keep one independent reviewer",
                        "A model reviewing itself missed scope problems.",
                    ),
                    (
                        "Never pick your own reviewer model",
                        "Haiku hired Opus, 3× cost.",
                    ),
                    ("Test every listed value", "A sampled test let a bug through."),
                    (
                        "Unset profile means guarded",
                        "A weak model chose the loose path.",
                    ),
                    ("Check every mention", "Specs kept claiming untrue things."),
                    (
                        "Accept only what the human decided",
                        "Two runs invented an approval.",
                    ),
                    (
                        "Mock only outside the change",
                        "A mocked service made a test check nothing.",
                    ),
                    ("No add-ons", "No quality gain, and the savings didn't last."),
                ],
                "wide",
            ),
            "The ideal setup",
        )
    )
    slides.append(
        headline(
            "It works on five models in three tools",
            "Opus, Sonnet and Haiku in Claude Code, and DeepSeek in Codex and "
            "Hermes. Every run was correct.",
            '<div class="card">'
            + ideal_chart()
            + '<p class="muted small">Cost as a share of the MP4 workflow on the '
            "same model and tool. The dark line is MP4.</p></div>",
            "The ideal setup",
        )
    )
    haiku = [
        (
            f"Task {t}",
            label,
            cost(t, arm, HAIKU),
            minutes(t, arm, HAIKU),
        )
        for t, arm, label in (
            ("1", "mp4-haiku", "MP4"),
            ("1", "ideal-v5", "Ideal v5"),
            ("2", "mp4-haiku", "MP4"),
            ("2", "ideal-v5", "Ideal v5"),
            ("2", "ideal-v6", "Ideal v6"),
        )
        if select(t, arm, HAIKU)
    ]
    slides.append(
        headline(
            "On Haiku, it isn't cheaper, but it is faster",
            "MP4's subagents run on cheap Haiku too, and the guarded checklist "
            "adds turns. So the ideal setup can cost more on Haiku, but it still "
            "finished task 2 in about half the time.",
            table(["Task", "Setup", "Cost", "Time"], haiku, "wide"),
            "The ideal setup",
        )
    )
    slides.append(
        slide(
            "Tuning it, v1 to v6",
            flow(
                [
                    ("v1", "one session, one reviewer"),
                    ("v2", "check mentions and old tests"),
                    ("v3", "set the reviewer model; test every value"),
                    ("v4", "unset means guarded"),
                    ("v5", "works in any repository"),
                    ("v6", "real decisions only; no mocking the change"),
                ],
                "six",
            )
            + '<p class="lead">Each version fixed something a run had got wrong. '
            "On task 2, v6 had no Medium or High findings on Sonnet or Haiku, "
            "where v5 had one each.</p>",
            "The ideal setup",
        )
    )
    slides.append(
        slide(
            "Use it",
            '<div class="card"><pre>python install.py /path/to/repo '
            "--project my-project.md\n\n"
            "AGENT_PROFILE=strong  claude --model sonnet\n"
            "AGENT_PROFILE=guarded codex -m &lt;model&gt;\n"
            "AGENT_PROFILE=guarded hermes -m &lt;model&gt;</pre></div>"
            '<p class="lead">The package is in '
            "<code>experiments/agent-setups/ideal/v6/</code>. It adds one "
            "workflow folder, a block in <code>AGENTS.md</code>, and small "
            "adapters for each tool.</p>",
            "The ideal setup",
        )
    )
    slides.append(
        slide(
            "Takeaways",
            '<ol class="takeaways">'
            "<li>Build in one session.</li>"
            "<li>Keep exactly one independent reviewer.</li>"
            "<li>Try the cheaper model first.</li>"
            "<li>Give weaker models a checklist, not freedom.</li>"
            "<li>Before review, check that specs, tests and decisions still "
            "agree.</li>"
            "<li>Write the project's facts down once.</li>"
            "</ol>",
            "Conclusion",
        )
    )
    slides.append(
        slide(
            "Skip, or test on your own work first",
            '<ul class="takeaways">'
            "<li>Token-saving add-ons and proxies.</li>"
            "<li>Adding more agent roles.</li>"
            "<li>Letting the model choose its reviewer or its profile.</li>"
            "<li>Trusting a result from one task.</li>"
            "</ul>",
            "Conclusion",
        )
    )
    slides.append(
        slide(
            "Limits",
            '<ul class="takeaways small-list">'
            "<li>Two tasks, in one Django project, with the decisions given up "
            "front.</li>"
            "<li>One to three runs per setup, so only large differences count.</li>"
            "<li>Quality was at the ceiling, so this mostly measures cost and "
            "time.</li>"
            "<li>Opus wrote the hidden tests and reviews, and built most "
            "candidates.</li>"
            "<li>Costs are list prices; a subscription bills differently.</li>"
            "</ul>",
            "Conclusion",
        )
    )
    appendix = [
        (
            r["run"],
            r["task"],
            r["arm"],
            r["tool"],
            r["model"].replace("claude-", "").replace("deepseek/", ""),
            f"${num(r['cost_usd']):.2f}",
            r["wall_min"],
            f"{r['hidden_passed']}/{int(r['hidden_passed']) + int(r['hidden_failed'])}",
            r["verify_passed"],
            r["mutants_killed"] or "—",
            f"{r['review_high'] or '—'}/{r['review_medium'] or '—'}",
        )
        for r in RUNS
    ]
    slides.append(
        slide(
            "Every run",
            '<div class="scroll">'
            + table(
                [
                    "Run",
                    "Task",
                    "Setup",
                    "Tool",
                    "Model",
                    "Cost",
                    "Min",
                    "Hidden",
                    "Verified",
                    "Bugs caught",
                    "High/Med",
                ],
                appendix,
                "wide small",
            )
            + "</div>",
            "Appendix",
        )
    )
    page = TEMPLATE.replace("<!--SLIDES-->", "\n".join(slides))
    (HERE / "presentation.html").write_text(page)
    print(f"wrote {len(slides)} slides")


if __name__ == "__main__":
    build()

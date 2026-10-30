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
    left, right, width, bar, gap, band = 180, 150, 900, 12, 2, 40
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


def quality_cell(rows):
    """One task's quality summary for a setup: correct runs, bugs caught, findings."""
    if not rows:
        return "not run"
    right = sum(1 for r in rows if correct(r))
    scored = [r for r in rows if r["mutants_killed"]]
    caught = sum(int(r["mutants_killed"]) for r in scored)
    reviewed = [r for r in rows if r["review_high"] != ""]
    high = sum(int(r["review_high"]) for r in reviewed)
    medium = sum(int(r["review_medium"]) for r in reviewed)
    bugs = f"{caught}/{5 * len(scored)}" if scored else "pending"
    findings = f"{high} / {medium}" if reviewed else "pending"
    return f"{right}/{len(rows)} correct · bugs {bugs} · High/Med {findings}"


def quality_rows():
    """Per-setup quality on both tasks."""
    out = []
    for label, arm, model, _, _ in SETUPS:
        cells = [quality_cell(select(task, arm, model)) for task in TASKS]
        if any(c != "not run" for c in cells):
            out.append((label, *cells))
    return out


def counted():
    """Every run in the comparison and ideal evaluation, variants and stack aside."""
    return [r for r in RUNS if r["run"] not in VARIANTS and r["arm"] != "stack"]


# --- Page -------------------------------------------------------------------


def stat(value, label, note=""):
    """A stat tile."""
    extra = f'<p class="muted small">{esc(note)}</p>' if note else ""
    return (
        f'<div class="card stat"><p class="stat-value">{esc(value)}</p>'
        f'<p class="stat-label">{esc(label)}</p>{extra}</div>'
    )


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


def build():
    """Assemble the slides and write presentation.html."""
    runs = counted()
    right = sum(1 for r in runs if correct(r))
    t2 = [r for r in runs if r["task"] == "2"]
    single = ["solo", "superpowers", "spec-kit", "ideal-v1", "ideal-v5"]
    single_shares = {t: [share(t, a) for a in single] for t in TASKS}
    addon_shares = {
        t: [share(t, a) for a in ("caveman", "ponytail", "headroom")] for t in TASKS
    }
    time_shares = {
        t: [
            median(select(t, a, OPUS), "wall_min") / base(t, "wall_min")
            for a in single
            if select(t, a, OPUS)
        ]
        for t in TASKS
    }
    mp4_money = {t: money_parts(select(t, "mp4", OPUS)) for t in TASKS}
    sub_share = {t: m[1] / sum(m) for t, m in mp4_money.items()}
    v5 = {t: share(t, "ideal-v5") for t in TASKS}
    mp4_sub = {t: median(select(t, "mp4", OPUS), "subagent_runs") for t in TASKS}
    findings = ANALYSIS["findings"]
    scored = [r for r in runs if r["mutants_killed"]]
    all_bugs = sum(1 for r in scored if r["mutants_killed"] == "5")
    headroom = [v["wire_percent"] for v in ANALYSIS["headroom"].values()]

    slides = []
    slides.append(
        '<section class="slide title-slide">'
        '<p class="kicker">Experiment #31 · zheng-jj · 30 October 2026</p>'
        "<h1>What does an agent workflow cost, and what does it buy?</h1>"
        '<p class="lead">Twelve ways to set up a coding agent, from MP4\'s '
        "multi-agent slice to popular plugins and methodologies, each run on two "
        "real Relay tasks with everything else held fixed. Then a portable setup "
        "built from the results, tested on five models in three tools.</p>"
        '<div class="grid four">'
        + stat(
            f"{right}/{len(runs)}",
            "runs fully correct",
            "hidden tests and full verification",
        )
        + stat(
            less_range(single_shares["1"] + single_shares["2"]),
            "cost for one-session setups than MP4",
            "same quality, both tasks",
        )
        + stat(
            pct_range(addon_shares["2"]),
            "cost of MP4 with an add-on, task 2",
            f"they looked {less_range(addon_shares['1'])} on task 1",
        )
        + stat(
            less_range([v for v in v5.values() if v]),
            "cost for the portable ideal (v5) than MP4",
            "Opus, both tasks; one independent reviewer kept",
        )
        + "</div></section>"
    )
    slides.append(
        slide(
            "Five findings",
            '<ol class="findings">'
            "<li><b>Quality did not separate the setups.</b> Every comparison run "
            "on both tasks passed its hidden acceptance suite and full "
            "verification, its own tests caught every planted bug, and no blind "
            f"review found a High issue. Across all {len(runs)} runs, "
            f"{all_bugs}/{len(scored)} caught every planted bug.</li>"
            "<li><b>Hand-offs are the cost.</b> In MP4, about "
            f"{sub_share['1']:.0%} (task 1) and {sub_share['2']:.0%} (task 2) of "
            "an average run's money went on subagents re-reading the repository. "
            "Setups that build in one session cost "
            f"{less_range(single_shares['1'] + single_shares['2'])} than MP4 and "
            f"took {share_range(time_shares['1'] + time_shares['2'])} of its "
            "time.</li>"
            "<li><b>The add-ons do not pay.</b> caveman, ponytail and headroom "
            f"cost {less_range(addon_shares['1'])} than MP4 on task 1, but "
            f"{pct_range(addon_shares['2'])} on task 2. What moved was how many "
            "subagents the coordinator started, not the add-on.</li>"
            "<li><b>Methodologies are one session with ceremony.</b> superpowers "
            "and spec-kit matched a single session's cost and quality. They bring "
            "planning and test-first habits, but no independent review "
            "unless asked.</li>"
            "<li><b>The ideal: build in one session, keep one independent "
            "reviewer.</b> The portable version cost about half of MP4 on Opus "
            "and far less on Sonnet, with the same quality. A guarded profile "
            "keeps weaker models on track; on Haiku it is not reliably cheaper "
            "than MP4, but it is up to twice as fast.</li>"
            "</ol>",
            "The answer first",
        )
    )
    groups = {}
    for label, arm, model, group, what in SETUPS:
        groups.setdefault(group, []).append((label, what))
    cards = "".join(
        card(
            group,
            "".join(
                f'<p class="item"><span class="badge">{esc(a)}</span> '
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
            '<p class="muted small">Each add-on runs on top of the MP4 workflow, '
            "one at a time. Opus 5.5 is the session model unless the setup says "
            "otherwise.</p>",
            "What was compared",
        )
    )
    t1_runs = [
        r for r in runs if r["task"] == "1" and r["run"][:3] in ("r1-", "r2-", "r3-")
    ]
    slides.append(
        slide(
            "Two real tasks, everything else fixed",
            '<div class="grid two">'
            + card(
                "Task 1 · #68: refuse hidden text-direction characters",
                bullets(
                    [
                        "Small: one validation rule across 12 round-text inputs.",
                        "Hidden suite: 132 tests (108 refusals, 24 allowed).",
                        (
                            "Planted bugs: no check; two controls allowed; a mark "
                            "refused; build labels unchecked."
                        ),
                        f"{len(t1_runs)} comparison runs: 2 per setup, 3 for MP4.",
                    ]
                ),
            )
            + card(
                "Task 2 · #16: request a retest (RND-5)",
                bullets(
                    [
                        (
                            "Larger: a new page, form and service, checks under a row "
                            "lock, a build cap, label rules and escaping."
                        ),
                        "Hidden suite: 27 HTTP tests.",
                        (
                            "Planted bugs: foreign cases accepted; cap off by one; "
                            "labels compared as typed; any round state accepted; "
                            "label unescaped."
                        ),
                        f"{len(t2)} runs: 1 per setup, 2 for MP4 and v5.",
                    ]
                ),
            )
            + "</div>"
            + card(
                "Held fixed",
                bullets(
                    [
                        "The same prompt and the human's decisions, given up front.",
                        (
                            "Claude Code 2.1.312, pinned and headless; web, GitHub, "
                            "push and installs blocked."
                        ),
                        (
                            "Each run in its own clone with no later history, and its "
                            "own test database."
                        ),
                        "Add-ons loaded per session only, pinned to a commit.",
                        (
                            "The method was written down before the first counted run "
                            "of each task."
                        ),
                    ]
                ),
            ),
            "Method",
        )
    )
    slides.append(
        slide(
            "How each run was scored",
            flow(
                [
                    ("Run", "headless, in its own clone"),
                    ("Hidden suite", "written from the issue before any run"),
                    ("Verification", "Django, migrations, Ruff, full pytest"),
                    ("Planted bugs", "5 per run; its own tests must fail"),
                    ("Blind review", "fresh Opus, random label, product diff"),
                    ("Audit", "spec first, commits, outside access"),
                ]
            )
            + '<p class="muted small">Cost is each tool\'s own report at API list '
            "prices; time is wall-clock. Runs overlapped three or four at a "
            "time.</p>",
            "Method",
        )
    )
    kinds = [finding_kind(f) for f in findings]
    high_count = sum(1 for f in findings if f["severity"] == "High")
    kind_text = "; ".join(
        f"{text} ({kinds.count(kind)})" for kind, text in FINDING_KINDS.items()
    )
    slides.append(
        slide(
            "Finding 1: every setup was correct, on both tasks",
            '<div class="scroll">'
            + table(["Setup", TASKS["1"], TASKS["2"]], quality_rows(), "wide small")
            + "</div>"
            + card(
                "What the blind reviews did find",
                f"<p>{len(findings)} Medium-or-higher findings across all "
                f"{len(RUNS)} runs, {high_count} of them High, both in the "
                "ideal setup's Haiku runs on task 1. None was wrong behaviour. "
                "By kind: "
                f"{kind_text}. Twice, a run recorded a residual as accepted that "
                "the human never accepted.</p>",
            ),
            "Results",
        )
    )
    slides.append(
        slide(
            "Finding 2: one session costs about half of MP4",
            '<div class="card">'
            + ratio_chart("cost_usd", lambda v: f"${v:.2f}", "Cost relative to MP4")
            + '<p class="muted small">Median cost per run as a share of MP4 on the '
            "same task (the line at 100%). Hover a bar for the range.</p></div>",
            "Results",
        )
    )
    slides.append(
        slide(
            "…and finishes in about half the time",
            '<div class="card">'
            + ratio_chart("wall_min", lambda v: f"{v:.0f} min", "Time relative to MP4")
            + '<p class="muted small">Median wall-clock minutes as a share of MP4 '
            "on the same task.</p></div>",
            "Results",
        )
    )
    mp4_write = {t: median(select(t, "mp4", OPUS), "cache_write_tokens") for t in TASKS}
    solo_write = median(select("1", "solo", OPUS), "cache_write_tokens")
    slides.append(
        slide(
            "Why: the money goes on hand-offs",
            '<div class="card">'
            + money_chart()
            + '<p class="muted small">Estimated from each run\'s tokens with rates '
            f"fitted to {ANALYSIS['opus_cost_split']['runs']} single-model Opus "
            "runs: cache reads, cache writes and output. Opus-only setups.</p></div>"
            '<div class="grid three">'
            + stat(
                f"{sub_share['1']:.0%} / {sub_share['2']:.0%}",
                "of MP4's money is subagent context",
                "task 1 / task 2",
            )
            + stat(
                f"{mp4_sub['1']:.0f} / {mp4_sub['2']:.0f}",
                "subagent runs in a median MP4 run",
                "each starts cold and re-reads the repository",
            )
            + stat(
                f"{mp4_write['1'] / solo_write:.1f}×",
                "more context cached by MP4 than by one session",
                "task 1; a cache write costs about 20 cache reads",
            )
            + "</div>",
            "Why it happens",
        )
    )
    slides.append(
        slide(
            "How a hand-off costs money",
            '<div class="grid two">'
            + card(
                "MP4: a coordinator and fresh subagents",
                '<div class="lane">'
                '<span class="node main">Coordinator</span>'
                '<span class="node sub">Builder · checkpoint 1</span>'
                '<span class="node sub">Builder · checkpoint 2</span>'
                '<span class="node sub">Verifier</span>'
                '<span class="node sub">Security reviewer</span>'
                '<span class="node sub">Builder · repair</span>'
                '<span class="node sub">Verifier · recheck</span></div>'
                "<p>Every subagent starts with an empty context. It reads "
                "<code>AGENTS.md</code>, its role, the specs and the code again, "
                "and caches all of it afresh. The coordinator then reads each "
                f"report back. A median MP4 run started {mp4_sub['1']:.0f} of them on "
                f"task 1 and {mp4_sub['2']:.0f} on task 2.</p>",
            )
            + card(
                "One session: build once, review once",
                '<div class="lane">'
                '<span class="node main">Session: spec → tests → code → docs → '
                "checks</span>"
                '<span class="node sub">One reviewer</span></div>'
                "<p>The session keeps its context and its cache for the whole "
                "build, so the repository is read once. One independent reviewer "
                "still reads it cold, because that independence is what catches "
                "what the builder cannot see in its own work.</p>",
            )
            + "</div>",
            "Why it happens",
        )
    )
    addon = {
        name: {t: select(t, name, OPUS) for t in TASKS}
        for name in ("caveman", "ponytail", "headroom", "mp4")
    }

    def addon_line(name, field, fmt):
        return " · ".join(
            f"task {t}: {fmt(median(addon[name][t], field))} vs MP4 "
            f"{fmt(median(addon['mp4'][t], field))}"
            for t in TASKS
            if addon[name][t]
        )

    def addon_subs(task):
        values = sorted(
            int(num(r["subagent_runs"]))
            for name in ("caveman", "ponytail", "headroom")
            for r in addon[name][task]
        )
        return (
            f"{values[0]}–{values[-1]}" if values[0] != values[-1] else str(values[0])
        )

    def mp4_subs(task):
        values = sorted(int(num(r["subagent_runs"])) for r in addon["mp4"][task])
        return (
            f"{values[0]}–{values[-1]}" if values[0] != values[-1] else str(values[0])
        )

    def money(v):
        return f"${v:.2f}"

    def kilo(v):
        return f"{v / 1000:.0f}k"

    def lines(v):
        return f"{v:.0f}"

    slides.append(
        slide(
            "The add-ons, one at a time",
            '<div class="grid three">'
            + card(
                "caveman: terse output",
                bullets(
                    [
                        "<b>Promise:</b> fewer output tokens.",
                        (
                            "<b>Output tokens:</b> "
                            f"{addon_line('caveman', 'output_tokens', kilo)}."
                        ),
                        f"<b>Cost:</b> {addon_line('caveman', 'cost_usd', money)}.",
                        (
                            "<b>Verdict:</b> real but small. Output is about a fifth "
                            "of cost, and reports came out in normal prose anyway."
                        ),
                    ]
                ),
            )
            + card(
                "ponytail: smallest change",
                bullets(
                    [
                        "<b>Promise:</b> smaller diffs.",
                        (
                            "<b>Test lines:</b> "
                            f"{addon_line('ponytail', 'test_lines', lines)}."
                        ),
                        f"<b>Cost:</b> {addon_line('ponytail', 'cost_usd', money)}.",
                        (
                            "<b>Verdict:</b> smaller tests on task 1, same quality; "
                            "no saving that survived task 2."
                        ),
                    ]
                ),
            )
            + card(
                "headroom: compressing proxy",
                bullets(
                    [
                        "<b>Promise:</b> compress the context sent to the model.",
                        (
                            "<b>Compressed:</b> "
                            f"{min(headroom):.1f}–{max(headroom):.1f}% "
                            "of request traffic."
                        ),
                        f"<b>Cost:</b> {addon_line('headroom', 'cost_usd', money)}.",
                        (
                            "<b>Verdict:</b> too little compression to matter, and it "
                            "routes your credentials through a third-party proxy."
                        ),
                    ]
                ),
            )
            + "</div>"
            f'<p class="muted small">Subagent runs per add-on run: {addon_subs("1")} '
            f"on task 1 against MP4's {mp4_subs('1')}; {addon_subs('2')} on task 2 "
            f"against {mp4_subs('2')}. Cost followed the subagent count, not the "
            "add-on. None of the three changed quality.</p>",
            "Results",
        )
    )

    def v_cost(task, arm, model):
        return f"${median(select(task, arm, model), 'cost_usd'):.2f}"

    def setup_line(arm, model=OPUS):
        return " · ".join(
            f"task {t}: ${median(select(t, arm, model), 'cost_usd'):.2f}, "
            f"{median(select(t, arm, model), 'wall_min'):.0f} min"
            for t in TASKS
            if select(t, arm, model)
        )

    slides.append(
        slide(
            "Workflows, models and methodologies",
            '<div class="grid two">'
            + card(
                "MP3 six roles",
                f"<p>{setup_line('mp3')}. The most roles and the most test code, "
                "with no quality gain. It ran cheaper than MP4 only because each "
                "of its roles reads less.</p>",
            )
            + card(
                "Solo session",
                f"<p>{setup_line('solo')}. One session plays every MP4 role: the "
                "cheapest Opus setup on task 1. Its weakness is that it reviews "
                "its own work.</p>",
            )
            + card(
                "Sonnet",
                f"<p>All-Sonnet MP4: {setup_line('mp4-sonnet', SONNET)}. A Sonnet "
                f"builder under Opus: {setup_line('mp4-sonnet-builder')}. Sonnet "
                "was enough for both tasks; the saving comes from running every "
                "session on it.</p>",
            )
            + card(
                "superpowers and spec-kit",
                f"<p>superpowers: {setup_line('superpowers')}. spec-kit: "
                f"{setup_line('spec-kit')}. Both build in one session, so both "
                "cost about what a single session costs. Neither adds an "
                "independent review unless asked.</p>",
            )
            + "</div>",
            "Results",
        )
    )
    slides.append(
        slide(
            "The ideal setup: how it works",
            flow(
                [
                    ("Specify", "requirements first, short plan"),
                    ("Build", "tests fail first; every listed value tested"),
                    ("Check", "every mention, every old test, every decision"),
                    ("Freeze", "full verification on the final commit"),
                    ("Review", "one independent read-only reviewer"),
                    ("Repair", "at most two rounds, then ask"),
                ]
            )
            + '<div class="grid three">'
            + card(
                "Two switches",
                '<p><span class="badge">AGENT_PROFILE</span> <code>strong</code> '
                "for Opus, Sonnet and GPT-5-class models; anything else, or unset, "
                "gets <code>guarded</code>: a ticked checklist, hard stops, tests "
                "shown failing first, a can-the-tests-fail check, and numbers only "
                'from commands run.</p><p><span class="badge">AGENT_REVIEW_MODEL'
                "</span> optionally a stronger reviewer. Otherwise the reviewer "
                "uses the session's model; the model never picks one.</p>",
            )
            + card(
                "One file per project",
                "<p><code>agent-workflow/project.md</code> holds what differs "
                "between repositories: the verification command, folders, where "
                "requirements, docs, plans and accepted risks live, the high-risk "
                "areas and the size budget. The workflow itself never names a "
                "project.</p>",
            )
            + card(
                "Any tool that reads AGENTS.md",
                "<p>The installer adds a marked block to <code>AGENTS.md</code>, "
                "the workflow folder, and adapters: Claude Code subagents and a "
                "skill, Codex agents, and a skill that Codex and Hermes read. "
                "Hermes delegates the review as a task.</p>",
            )
            + "</div>",
            "The ideal setup",
        )
    )
    slides.append(
        slide(
            "Why each rule is there",
            table(
                ["Rule", "Evidence from the runs"],
                [
                    (
                        "Build in one session",
                        (
                            "Subagent context was "
                            f"{sub_share['1']:.0%}–{sub_share['2']:.0%} "
                            "of MP4's money; one-session setups cost about half, with "
                            "the same quality."
                        ),
                    ),
                    (
                        "Keep one independent reviewer",
                        (
                            "A session reviewing itself missed scope and ownership "
                            "problems in the earlier weaker-model run. One reviewer is "
                            "a fraction of MP4's repeated reviews."
                        ),
                    ),
                    (
                        "Reviewer on the session's model unless set",
                        (
                            "Left to choose, Haiku started Opus reviewers on its own "
                            "and tripled its cost (v2)."
                        ),
                    ),
                    (
                        "The three consistency checks",
                        (
                            "Every Medium or High finding was a stale spec, a weakened "
                            "old test or a decision left out of its home."
                        ),
                    ),
                    (
                        "Test each listed value",
                        (
                            "A DeepSeek run sampled the refused characters, and a "
                            "planted bug survived (v2)."
                        ),
                    ),
                    (
                        "Unset profile means guarded",
                        (
                            "A DeepSeek run left to choose took the strong flow (v2); "
                            "from v4 every unset run chose guarded."
                        ),
                    ),
                    (
                        "Project facts in one file",
                        (
                            "Haiku kept putting accepted risks in the plan until "
                            "project.md named their home; the v5 Haiku run got it "
                            "right."
                        ),
                    ),
                    (
                        "Only the human's decisions are accepted (v6)",
                        (
                            "Two runs recorded a residual as accepted that the "
                            "human never accepted."
                        ),
                    ),
                    (
                        "Claims about tests point to a test (v6)",
                        (
                            "The commonest finding was spec text saying tests "
                            "covered something they did not."
                        ),
                    ),
                    (
                        "Mock only outside the change (v6)",
                        (
                            "A v5 Haiku run mocked the whole service, so its "
                            "failure test checked nothing."
                        ),
                    ),
                    (
                        "No add-ons",
                        (
                            "None improved quality; their task-1 savings did not "
                            "survive task 2."
                        ),
                    ),
                ],
                "wide",
            ),
            "The ideal setup",
        )
    )
    ideal_table = []
    for name, task, cells in ideal_rows():
        for key in ["reference", *[v for v in VERSIONS if v in cells]]:
            rows = cells.get(key) or []
            label = "MP4 workflow" if key == "reference" else f"Ideal {key}"
            if not rows:
                continue
            ideal_table.append(
                (
                    f"{name} · task {task}",
                    label,
                    len(rows),
                    f"${median(rows, 'cost_usd'):.2f}",
                    f"{median(rows, 'wall_min'):.0f} min",
                    quality_cell(rows),
                )
            )
    slides.append(
        slide(
            "The ideal setup, measured on five models",
            '<div class="card">'
            + ideal_chart()
            + '<p class="muted small">Median cost as a share of the MP4 workflow on '
            "the same model, tool and task (the line at 100%). DeepSeek v4.1 Flash "
            "ran through OpenRouter in Codex 0.165.0 and Hermes 0.21.3.</p></div>"
            "<details><summary>Every platform and version</summary>"
            + table(
                ["Platform", "Setup", "Runs", "Cost", "Time", "Quality"],
                ideal_table,
                "wide small",
            )
            + "</details>",
            "The ideal setup",
        )
    )
    slides.append(
        slide(
            "Tuning, v1 to v6",
            flow(
                [
                    ("v1", "lean slice, one reviewer, two profiles"),
                    ("v2", "check every mention and every old test"),
                    ("v3", "reviewer model only by setting; test every value"),
                    ("v4", "unset means guarded; decisions mapped in the plan"),
                    ("v5", "project-independent; project facts in one file"),
                    ("v6", "accept only real decisions; back test claims; mock less"),
                ],
                "six",
            )
            + '<div class="grid two">'
            + card(
                "What each step fixed",
                bullets(
                    [
                        "v2 removed the Medium spec findings on Sonnet and Opus.",
                        (
                            "v3 stopped Haiku choosing Opus reviewers, and Hermes "
                            "sampling values."
                        ),
                        "v4 made every unset DeepSeek run choose guarded.",
                        (
                            "v5 let Haiku record accepted risks in the right home, "
                            "and installs into any repository."
                        ),
                    ]
                ),
            )
            + card(
                "v6: three rules from v5's own reviews",
                bullets(
                    [
                        (
                            "v5 on task 2 had one Medium finding each on Sonnet "
                            f"({v_cost('2', 'ideal-v5', SONNET)}) and Haiku "
                            f"({v_cost('2', 'ideal-v5', HAIKU)}): an invented "
                            "approval and a mocked service."
                        ),
                        (
                            "v6 on the same task had none, on Sonnet "
                            f"({v_cost('2', 'ideal-v6', SONNET)}) and Haiku "
                            f"({v_cost('2', 'ideal-v6', HAIKU)}), with every "
                            "planted bug caught."
                        ),
                        (
                            "One run each: the rules cost nothing, but whether "
                            "they reliably help needs more runs."
                        ),
                    ]
                ),
            )
            + "</div>",
            "The ideal setup",
        )
    )
    slides.append(
        slide(
            "Takeaways",
            '<div class="grid two">'
            + card(
                "If you run coding agents on a real repository",
                '<ol class="tight">'
                "<li><b>Build in one session.</b> Hand-offs to builder subagents "
                "doubled cost and time here with no quality gain.</li>"
                "<li><b>Keep exactly one independent reviewer.</b> It is the part a "
                "session cannot do for itself, and it is cheap.</li>"
                "<li><b>Try the cheaper model first.</b> Sonnet passed every check "
                "on both tasks at a fraction of Opus's cost.</li>"
                "<li><b>Give weaker models a checklist, not freedom.</b> Hard "
                "stops, tests shown failing first, numbers only from commands "
                "run.</li>"
                "<li><b>Before review, check consistency.</b> Every mention, every "
                "old test, every decision: that is where the findings were.</li>"
                "<li><b>Write the project's facts down once.</b> Commands, homes "
                "and budgets in one file let the same workflow move between "
                "repositories and tools.</li>"
                "</ol>",
            )
            + card(
                "Skip, or measure first",
                bullets(
                    [
                        (
                            "<b>Output-compression and proxy add-ons:</b> small or no "
                            "savings, and a proxy sees your credentials."
                        ),
                        (
                            "<b>More roles:</b> MP3's six roles cost more and found "
                            "nothing extra."
                        ),
                        (
                            "<b>Letting the model pick its reviewer or profile:</b> it "
                            "chose the expensive or the loose option."
                        ),
                        (
                            "<b>Trusting one task:</b> task 1 made the add-ons look "
                            "useful; task 2 did not."
                        ),
                    ]
                ),
            )
            + "</div>",
            "Conclusion",
        )
    )
    slides.append(
        slide(
            "Limits",
            bullets(
                [
                    (
                        "Two tasks in one Django project, both with the human's "
                        "decisions given up front. Large or ambiguous work, where "
                        "review "
                        "has more to find, may rank the setups differently."
                    ),
                    (
                        "One to three runs per setup and task. Only large, consistent "
                        "differences are worth reading."
                    ),
                    (
                        "Quality hit the ceiling on both tasks, so the comparison "
                        "mostly measures cost and time."
                    ),
                    (
                        "Opus wrote the hidden suites and the blind reviews, and built "
                        "most candidates. The hidden suites and planted bugs are the "
                        "objective checks."
                    ),
                    (
                        "Costs are list prices from each tool's report; the "
                        "subscription bills differently. Runs overlapped, so times "
                        "include contention."
                    ),
                ]
            ),
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

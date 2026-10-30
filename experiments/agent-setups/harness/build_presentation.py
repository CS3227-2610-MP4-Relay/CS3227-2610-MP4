"""Build presentation.html from the committed results: python build_presentation.py

Reads results/runs.csv and results/analysis.json only, so the slides can be
rebuilt without the run folders. The page is one self-contained HTML file in a
shadcn-like style; it needs the network only for its web font.
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

LABELS = {
    "mp4": "MP4 baseline",
    "mp3": "MP3 six roles",
    "solo": "Solo session",
    "mp4-sonnet-builder": "MP4, Sonnet builder",
    "mp4-sonnet": "MP4, all Sonnet",
    "superpowers": "superpowers",
    "spec-kit": "spec-kit",
    "caveman": "MP4 + caveman",
    "ponytail": "MP4 + ponytail",
    "headroom": "MP4 + headroom",
    "stack": "MP4 + all three",
}
COMPARISON = [r for r in RUNS if r["run"][:3] in ("r1-", "r2-", "r3-")]


def num(value):
    """A CSV cell as a float, or None when empty."""
    return float(value) if value not in ("", None) else None


def median(rows, field):
    """Median of a numeric field over rows that have it."""
    values = [num(r[field]) for r in rows if num(r[field]) is not None]
    return statistics.median(values) if values else None


def esc(text):
    """HTML-escape text."""
    return html.escape(str(text))


def by_arm(rows):
    """Rows grouped by arm, in insertion order."""
    groups = {}
    for row in rows:
        groups.setdefault(row["arm"], []).append(row)
    return groups


ARMS = by_arm(COMPARISON)
BASE_COST = median(ARMS["mp4"], "cost_usd")
ORDER = sorted(ARMS, key=lambda arm: median(ARMS[arm], "cost_usd"))


# --- Charts ---------------------------------------------------------------


def range_chart(field, unit, title, fmt):
    """Horizontal dot-and-range chart of `field` per setup, one shared axis."""
    rows = [(arm, [num(r[field]) for r in ARMS[arm]]) for arm in ORDER]
    top = max(max(values) for _, values in rows)
    left, right, row_h, width = 190, 70, 34, 900
    plot = width - left - right
    height = row_h * len(rows) + 40
    step = 2 if top <= 12 else 5 if top <= 35 else 10
    ticks = list(range(0, int(top) + step + 1, step))
    scale = plot / ticks[-1]
    parts = [
        (
            f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{esc(title)}">'
        )
    ]
    for tick in ticks:
        x = left + tick * scale
        parts.append(
            f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="8" y2="{height - 28}"/>'
            f'<text class="tick" x="{x:.1f}" y="{height - 8}" text-anchor="middle">'
            f"{unit}{tick}</text>"
        )
    for index, (arm, values) in enumerate(rows):
        y = 24 + index * row_h
        mid = statistics.median(values)
        low, high = min(values), max(values)
        strong = " strong" if arm == "mp4" else ""
        tip = (
            f"{LABELS[arm]}: median {fmt(mid)}, range {fmt(low)} to {fmt(high)} "
            f"({len(values)} runs)"
        )
        parts.append(
            f'<text class="label{strong}" x="{left - 12}" y="{y + 5}" '
            f'text-anchor="end">{esc(LABELS[arm])}</text>'
            f'<line class="range" x1="{left + low * scale:.1f}" '
            f'x2="{left + high * scale:.1f}" y1="{y}" y2="{y}"/>'
            f'<circle class="dot{strong}" cx="{left + mid * scale:.1f}" cy="{y}" r="7" '
            f'tabindex="0" data-tip="{esc(tip)}"/>'
            f'<text class="value" x="{left + high * scale + 12:.1f}" y="{y + 5}">'
            f"{fmt(mid)}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def share_bar(shares):
    """One stacked bar of the cost split, each segment direct-labelled."""
    width, left = 900, 0
    names = [
        ("cache_read", "Cache reads", "s1"),
        ("cache_write", "Cache writes", "s2"),
        ("output", "Output", "s3"),
    ]
    parts = [
        (
            f'<svg class="chart" viewBox="0 0 {width} 92" role="img" '
            'aria-label="Share of Opus cost by token type">'
        )
    ]
    for key, name, role in names:
        share = shares[key]
        span = share * width
        tip = f"{name}: {share:.0%} of reported Opus cost"
        parts.append(
            f'<rect class="seg {role}" x="{left + 1:.1f}" y="8" width="{span - 2:.1f}" '
            f'height="40" rx="4" tabindex="0" data-tip="{esc(tip)}"/>'
            f'<text class="seg-label" x="{left + 4:.1f}" y="72">{esc(name)} '
            f"{share:.0%}</text>"
        )
        left += span
    parts.append("</svg>")
    return "".join(parts)


def index_chart(groups):
    """Grouped bars of cost as a % of each platform's MP4 reference, one axis."""
    series = [
        ("reference", "MP4 workflow", "s2"),
        ("v1", "Ideal v1", "s1"),
        ("final", "Ideal, latest tested", "s3"),
    ]
    width, left, bottom, height = 900, 60, 40, 330
    plot_h = height - bottom - 20
    group_w = (width - left - 10) / len(groups)
    bar_w = min(42, group_w / 4)
    top = 125
    parts = [
        (
            f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
            'aria-label="Cost of the ideal setup as a share of the MP4 workflow on the '
            'same model and tool">'
        )
    ]
    for tick in (0, 25, 50, 75, 100, 125):
        y = 20 + plot_h - tick / top * plot_h
        parts.append(
            f'<line class="grid{" base" if tick == 100 else ""}" x1="{left}" '
            f'x2="{width - 10}" y1="{y:.1f}" y2="{y:.1f}"/>'
            f'<text class="tick" x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">'
            f"{tick}%</text>"
        )
    for index, (name, values) in enumerate(groups):
        x0 = left + index * group_w + (group_w - bar_w * 3 - 8) / 2
        for position, (key, label, role) in enumerate(series):
            value = values.get(key)
            x = x0 + position * (bar_w + 4)
            if value is None:
                parts.append(
                    f'<text class="tick" x="{x + bar_w / 2:.1f}" y="{20 + plot_h - 6}" '
                    'text-anchor="middle">n/a</text>'
                )
                continue
            percent, dollars = value[0], value[1]
            shown = f"Ideal {value[2]}" if len(value) > 2 else label
            bar_h = min(percent, top) / top * plot_h
            y = 20 + plot_h - bar_h
            tip = f"{name}, {shown}: ${dollars:.2f} ({percent:.0f}% of MP4)"
            parts.append(
                f'<rect class="bar {role}" x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                f'height="{bar_h:.1f}" rx="4" tabindex="0" data-tip="{esc(tip)}"/>'
            )
            if key != "reference":
                parts.append(
                    f'<text class="value" x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" '
                    f'text-anchor="middle">{percent:.0f}%</text>'
                )
        parts.append(
            f'<text class="label" x="{left + index * group_w + group_w / 2:.1f}" '
            f'y="{height - 12}" text-anchor="middle">{esc(name)}</text>'
        )
    parts.append("</svg>")
    legend = "".join(
        f'<span class="key"><i class="{role}"></i>{esc(label)}</span>'
        for _, label, role in series
    )
    return f'<div class="legend">{legend}</div>' + "".join(parts)


# --- Ideal-setup data -------------------------------------------------------

VERSIONS = ["v1", "v2", "v3", "v4"]
PLATFORMS = [
    ("Opus · Claude Code", "claude", "claude-opus-5-5", ARMS["mp4"]),
    ("Sonnet · Claude Code", "claude", "claude-sonnet-5-5", ARMS["mp4-sonnet"]),
    ("Haiku · Claude Code", "claude", "claude-haiku-5-5", None),
    ("DeepSeek · Codex", "codex", "deepseek/deepseek-v4.1-flash", None),
    ("DeepSeek · Hermes", "hermes", "deepseek/deepseek-v4.1-flash", None),
]


def platform_rows(tool, model, arm):
    """The runs of one ideal-setup version or reference on one platform."""
    return [
        r for r in RUNS if r["tool"] == tool and r["model"] == model and r["arm"] == arm
    ]


def ideal_groups():
    """(platform, {series: (% of reference, $ median)}) for the index chart."""
    groups, table = [], []
    for name, tool, model, reference in PLATFORMS:
        ref = reference or [
            r
            for r in RUNS
            if r["run"].startswith("ref-") and r["tool"] == tool and r["model"] == model
        ]
        ref_cost = median(ref, "cost_usd") if ref else None
        values = {}
        if ref_cost:
            values["reference"] = (100.0, ref_cost)
        latest = None
        for version in VERSIONS:
            rows = platform_rows(tool, model, f"ideal-{version}")
            if rows:
                latest = (version, rows)
                table.append((name, version, rows))
        first = platform_rows(tool, model, "ideal-v1")
        if first and ref_cost:
            values["v1"] = (
                median(first, "cost_usd") / ref_cost * 100,
                median(first, "cost_usd"),
            )
        if latest and latest[0] != "v1" and ref_cost:
            cost = median(latest[1], "cost_usd")
            values["final"] = (cost / ref_cost * 100, cost, latest[0])
        table.append((name, "reference", ref))
        groups.append((name, values))
    return groups, table


def quality_cells(rows):
    """Summary cells of hidden suite, verification, mutants and review for rows."""
    if not rows:
        return ["—"] * 6
    hidden = sum(
        1 for r in rows if r["hidden_refusal"] == "108" and r["hidden_allowed"] == "24"
    )
    verified = sum(1 for r in rows if r["verify_passed"] == "True")
    mutants = [r["mutants_killed"] for r in rows if r["mutants_killed"]]
    medium = [r["review_medium"] for r in rows if r["review_medium"] != ""]
    return [
        f"{len(rows)}",
        f"${median(rows, 'cost_usd'):.2f}",
        f"{median(rows, 'wall_min'):.0f} min",
        f"{hidden}/{len(rows)}",
        f"{verified}/{len(rows)}",
        f"{'/'.join(mutants) or '—'} · M {'/'.join(medium) or '—'}",
    ]


# --- Page -------------------------------------------------------------------


def stat(value, label, note=""):
    """A shadcn-style stat card."""
    extra = f'<p class="muted small">{esc(note)}</p>' if note else ""
    return (
        f'<div class="card stat"><p class="stat-value">{esc(value)}</p>'
        f'<p class="stat-label">{esc(label)}</p>{extra}</div>'
    )


def table(head, rows, cls=""):
    """A simple data table."""
    head_html = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in rows
    )
    return (
        f'<table class="{cls}"><thead><tr>{head_html}</tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


def slide(title, body, kicker=""):
    """One slide section."""
    kick = f'<p class="kicker">{esc(kicker)}</p>' if kicker else ""
    return f'<section class="slide">{kick}<h2>{esc(title)}</h2>{body}</section>'


def build():
    """Assemble the slides and write presentation.html."""
    comp = COMPARISON
    all_correct = sum(
        1 for r in comp if r["hidden_refusal"] == "108" and r["hidden_allowed"] == "24"
    )
    mediums = [f for f in ANALYSIS["findings"] if f["run"][:3] in ("r1-", "r2-", "r3-")]
    spec_findings = sum(1 for f in mediums if f.get("area") == "specs")
    test_findings = sum(1 for f in mediums if f.get("area") == "tests")
    split = ANALYSIS["opus_cost_split"]["mean_share"]
    headroom = ANALYSIS["headroom"]
    wire = [v["wire_percent"] for v in headroom.values()]
    sonnet_cut = 1 - median(ARMS["mp4-sonnet"], "cost_usd") / BASE_COST
    groups, ideal_table = ideal_groups()
    v4_costs = [
        num(r["cost_usd"])
        for r in RUNS
        if r["arm"] == "ideal-v4" and r["tool"] in ("codex", "hermes")
    ]
    deepseek_v4 = f"${min(v4_costs):.2f}–{max(v4_costs):.2f}" if v4_costs else "—"

    slides = []
    slides.append(
        '<section class="slide title-slide">'
        '<p class="kicker">Experiment #31 · zheng-jj · 30 October 2026</p>'
        "<h1>What does an agent workflow cost?</h1>"
        '<p class="lead">Eleven setups, one real Relay task, 23 runs in Claude Code. '
        "Then "
        "an ideal setup, built from the results and tested on Opus, Sonnet and Haiku "
        "in Claude Code and on DeepSeek v4.1 Flash in Codex and Hermes.</p>"
        '<div class="grid four">'
        + stat(
            f"{all_correct}/{len(comp)}", "runs fully correct", "132/132 hidden tests"
        )
        + stat(f"−{sonnet_cut:.0%}", "cost, all-Sonnet vs MP4", "same quality")
        + stat("2–3×", "faster in one session", "12 vs 30 minutes")
        + stat(deepseek_v4, "ideal v4 on DeepSeek", "Codex and Hermes, all correct")
        + "</div></section>"
    )
    slides.append(
        slide(
            "One task, everything else fixed",
            '<div class="grid two"><div class="card">'
            '<p class="card-title">The task</p>'
            "<p>Issue #68: refuse hidden text-direction characters in round text. "
            "Every run starts from <code>01f9a24</code>, the commit the real slice "
            "started from, with the same prompt and the human's decisions given up "
            "front. The merged PR #71 is the hidden reference.</p>"
            '<p class="card-title">Measured</p>'
            "<ul><li>Cost and tokens (Claude Code's own report)</li><li>Wall time and "
            "turns</li><li>Quality: hidden tests, mutants, blind review</li>"
            "<li>Process: spec-first, commits, scope, leakage</li></ul></div>"
            '<div class="card"><p class="card-title">Kept identical</p><ul>'
            "<li>Claude Code 2.1.312, pinned binary, headless</li>"
            "<li>Same permissions; web, GitHub, push and installs blocked</li>"
            "<li>Own clone per run with no later history, own test database</li>"
            "<li>Add-ons loaded per session only, pinned to a commit</li>"
            "<li>Method frozen before the first counted run</li>"
            "<li>2 runs per setup, 3 for the baseline, seeded order</li></ul>"
            "</div></div>",
            "Method",
        )
    )
    groups_html = [
        (
            "Workflow",
            [
                ("MP4 baseline", "builder → verifier → security-reviewer"),
                (
                    "MP3 six roles",
                    "spec-writer, critic, test-writer, implementer, reviewers",
                ),
                ("Solo", "one session plays every role"),
            ],
        ),
        (
            "Models",
            [
                ("MP4, Sonnet builder", "Opus coordinator and reviewers"),
                ("MP4, all Sonnet", "every role on Sonnet"),
            ],
        ),
        (
            "Methodologies",
            [
                ("superpowers", "obra/superpowers skills"),
                ("spec-kit", "GitHub's spec-driven toolkit"),
            ],
        ),
        (
            "Add-ons on MP4",
            [
                ("caveman", "terse output"),
                ("ponytail", "smallest change"),
                ("headroom", "compressing proxy"),
                ("all three", "stacked"),
            ],
        ),
    ]
    cards = "".join(
        f'<div class="card"><p class="card-title">{esc(name)}</p>'
        + "".join(
            f'<p class="item"><span class="badge">{esc(a)}</span> {esc(b)}</p>'
            for a, b in items
        )
        + "</div>"
        for name, items in groups_html
    )
    slides.append(
        slide("Eleven setups", f'<div class="grid four">{cards}</div>', "Arms")
    )
    slides.append(
        slide(
            "Quality hit the ceiling",
            '<div class="grid four">'
            + stat(
                f"{all_correct}/{len(comp)}",
                "passed the hidden suite",
                "132 tests each",
            )
            + stat(f"{len(comp)}/{len(comp)}", "passed full verification")
            + stat(f"{5 * len(comp)}/{5 * len(comp)}", "planted bugs caught")
            + stat("0", "High review findings", f"{len(mediums)} Medium in total")
            + "</div>"
            '<div class="card"><p class="card-title">'
            "What the blind reviews did find</p>"
            f"<p><b>{spec_findings}</b> Medium findings were a second spec left saying "
            f"something no longer true. <b>{test_findings}</b> were about tests: two "
            "old tests switched to an allowed input, dropping what they checked; one "
            "coverage gap; one reviewer false positive. None is wrong behaviour, and "
            "the stale-spec and switched-test patterns became explicit checks in the "
            "ideal setup.</p>"
            "</div>",
            "Results",
        )
    )
    cost_rows = [
        (
            LABELS[a],
            len(ARMS[a]),
            f"${median(ARMS[a], 'cost_usd'):.2f}",
            f"{median(ARMS[a], 'cost_usd') / BASE_COST - 1:+.0%}",
            f"{median(ARMS[a], 'wall_min'):.0f}",
            f"{median(ARMS[a], 'subagent_runs'):.0f}",
        )
        for a in ORDER
    ]
    slides.append(
        slide(
            "Cost per setup",
            '<div class="card">'
            + range_chart(
                "cost_usd",
                "$",
                "Median cost per setup, with range",
                lambda v: f"${v:.2f}",
            )
            + '<p class="muted small">Dot: median. Line: range across runs. List '
            "prices from Claude Code's report.</p><details><summary>Table</summary>"
            + table(
                ["Setup", "Runs", "Cost", "vs MP4", "Minutes", "Subagent runs"],
                cost_rows,
            )
            + "</details></div>",
            "Results",
        )
    )
    slides.append(
        slide(
            "Time per setup",
            '<div class="card">'
            + range_chart(
                "wall_min",
                "",
                "Median minutes per setup, with range",
                lambda v: f"{v:.0f} min",
            )
            + '<p class="muted small">Single-session setups finish in 11–14 minutes; '
            "MP4's hand-offs take 27–30. Runs overlapped three at a time.</p></div>",
            "Results",
        )
    )
    slides.append(
        slide(
            "Where the money goes",
            '<div class="card">'
            + share_bar(split)
            + '<p class="muted small">Split of each single-model Opus run\'s reported '
            f"cost, fitted across {ANALYSIS['opus_cost_split']['runs']} runs.</p></div>"
            '<div class="grid three">'
            + stat(
                "50–70%",
                "of MP4's cached reads are in subagents",
                "each re-reads the context",
            )
            + stat(
                "4×", "more cache writes in MP4 than solo", "0.50–0.63M vs 0.14–0.15M"
            )
            + stat(
                "+75%",
                "cost when one coordinator chose an extra review",
                "11 vs 8 subagent runs",
            )
            + "</div>",
            "Why",
        )
    )
    addon = by_arm(COMPARISON)
    caveman_out = median(addon["caveman"], "output_tokens")
    mp4_out = median(addon["mp4"], "output_tokens")
    slides.append(
        slide(
            "The add-ons",
            '<div class="grid four">'
            + stat(
                f"−{1 - caveman_out / mp4_out:.0%}",
                "caveman: output tokens",
                "output is about a fifth of cost",
            )
            + stat(
                f"{median(addon['ponytail'], 'test_lines'):.0f} lines",
                "ponytail: test code",
                f"vs {median(addon['mp4'], 'test_lines'):.0f} for MP4; same quality",
            )
            + stat(
                f"{min(wire):.1f}–{max(wire):.1f}%",
                "headroom: traffic compressed",
                "too little to explain any saving",
            )
            + stat(
                f"${median(addon['stack'], 'cost_usd'):.2f}",
                "all three together",
                f"vs ${BASE_COST:.2f} for MP4",
            )
            + "</div>"
            '<div class="card"><p>Every add-on run cost less than every baseline run, '
            "with fewer subagent runs (6 vs 9). With two runs each, that can't be told "
            "apart from the coordinator's own variation. None improved quality, which "
            "was already at the ceiling.</p></div>",
            "Results",
        )
    )
    flow = "".join(
        f'<div class="step"><span class="badge">{i}</span><p><b>{esc(a)}</b><br>'
        f'<span class="muted">{esc(b)}</span></p></div>'
        for i, (a, b) in enumerate(
            [
                ("Specify", "spec first, short plan"),
                ("Build", "tests fail first, smallest change"),
                ("Check", "every mention, every old test"),
                ("Freeze", "full verification, commit"),
                ("Review", "one independent read-only reviewer"),
                ("Repair", "at most two rounds"),
            ],
            start=1,
        )
    )
    slides.append(
        slide(
            "The ideal setup",
            f'<div class="card"><div class="flow">{flow}</div></div>'
            '<div class="grid two"><div class="card"><p class="card-title">Why this '
            "shape</p><ul>"
            "<li>Building in one session removes the hand-offs that drive cost.</li>"
            "<li>An independent reviewer is the one thing a session can't give "
            "itself; the "
            "earlier DeepSeek run showed self-review misses scope and governance.</li>"
            "<li>Subagents inherit the session's model, so a cheap session stays "
            "cheap.</li>"
            "<li>No add-on: none improved quality, and headroom proxies your "
            "credentials.</li></ul></div>"
            '<div class="card"><p class="card-title">One switch: '
            "<code>RELAY_PROFILE</code></p>"
            '<p><span class="badge">strong</span> Opus, Sonnet, GPT-5-class: the lean '
            "slice "
            'as written.</p><p><span class="badge">guarded</span> Haiku, DeepSeek or '
            "unsure: a ticked checklist, hard stops before scope or rule changes, "
            "tests "
            "shown to fail first, a can-fail self-check and numbers only from commands "
            'run.</p><p class="muted small">Unset means guarded (v4): in v2, a '
            "DeepSeek run left to pick for itself followed the strong flow.</p>"
            "</div></div>",
            "Design",
        )
    )
    slides.append(
        slide(
            "One setup, three tools",
            table(
                ["", "Claude Code", "Codex", "Hermes"],
                [
                    ("Rules", "AGENTS.md via CLAUDE.md", "AGENTS.md", "AGENTS.md"),
                    (
                        "Slice skill",
                        ".claude/skills/slice",
                        ".agents/skills/slice",
                        "linked from AGENTS.md",
                    ),
                    (
                        "Reviewer",
                        "Task: verifier",
                        "spawned verifier agent",
                        "delegate_task goal",
                    ),
                    (
                        "Read-only reviewer",
                        "tool list: Read, Grep, Glob",
                        "instructions only",
                        "instructions only",
                    ),
                    (
                        "Model of reviewer",
                        "inherits the session",
                        "inherits the session",
                        "inherits the session",
                    ),
                ],
                "wide",
            )
            + '<div class="card"><p class="card-title">Install and launch</p><pre>'
            "python experiments/agent-setups/ideal/install.py v4 .\n\n"
            "RELAY_PROFILE=strong  claude --model sonnet\n"
            "RELAY_PROFILE=guarded codex -m deepseek/deepseek-v4.1-flash\n"
            "RELAY_PROFILE=guarded hermes -m deepseek/deepseek-v4.1-flash --provider "
            "openrouter"
            "</pre></div>",
            "Design",
        )
    )
    ideal_rows = []
    for name, key, rows in ideal_table:
        label = "MP4 workflow" if key == "reference" else f"Ideal {key}"
        ideal_rows.append((name, label, *quality_cells(rows)))
    slides.append(
        slide(
            "The ideal setup, measured",
            '<div class="card">'
            + index_chart(groups)
            + '<p class="muted small">Cost as a share of the MP4 workflow on the same '
            "model and tool (100%). Hover a bar for dollars.</p></div>"
            "<details><summary>Quality and cost per platform</summary>"
            + table(
                [
                    "Platform",
                    "Setup",
                    "Runs",
                    "Cost",
                    "Time",
                    "Hidden 132/132",
                    "Verification",
                    "Mutants caught · Medium findings",
                ],
                ideal_rows,
                "wide",
            )
            + "</details>",
            "Evaluation",
        )
    )
    tuning = [
        (
            "v1",
            "Lean slice, one reviewer, strong/guarded profiles",
            (
                "All correct; Sonnet $1.35, Opus $4.23; on Hermes 2× cheaper and "
                "4.5× faster than MP4. Two Medium spec findings; one High (Haiku "
                "missed recording two decisions)."
            ),
        ),
        (
            "v2",
            "Check every mention and every old test, builder and reviewer",
            (
                "No Medium findings on Sonnet or Opus. But Haiku chose Opus reviewers "
                "on its own (3× cost), and Hermes sampled the refused characters, so "
                "one planted bug survived."
            ),
        ),
        (
            "v3",
            "Reviewer model only from RELAY_REVIEW_MODEL; test every listed value",
            "Haiku back to $0.92 with clean reviews; Codex and Hermes clean at $0.15.",
        ),
        (
            "v4",
            "Unset profile means guarded; plan maps each human decision",
            (
                "Both unset DeepSeek runs chose guarded; Hermes $0.13 in 10 min. "
                "Haiku still put two residuals in its plan, not the security spec "
                "(High): next, say where residuals live."
            ),
        ),
    ]
    rows = "".join(
        f'<div class="step"><span class="badge">{esc(v)}</span><p><b>{esc(a)}</b>'
        f'<br><span class="muted">{esc(b)}</span></p></div>'
        for v, a, b in tuning
    )
    slides.append(
        slide(
            "Tuning for both kinds of model",
            f'<div class="card"><div class="flow four">{rows}</div></div>'
            '<p class="muted small">Each version was run on the weaker models '
            "(Haiku; DeepSeek in Codex and Hermes) and on Sonnet; see the table on "
            "the previous slide.</p>",
            "Evaluation",
        )
    )
    slides.append(
        slide(
            "Takeaways",
            '<div class="grid two"><div class="card"><p class="card-title">Do</p><ul>'
            "<li>Build in one session; keep exactly one independent reviewer.</li>"
            "<li>Run that session on the cheapest model that passes: Sonnet here.</li>"
            "<li>Give weaker models the guarded profile: checklist, hard stops, "
            "evidence.</li>"
            "<li>Check every mention and every old test before "
            "freezing.</li></ul></div>"
            '<div class="card"><p class="card-title">Mind</p><ul>'
            "<li>One Standard-tier task with decisions given up front.</li>"
            "<li>2–3 runs per setup: only non-overlapping ranges count.</li>"
            "<li>Opus wrote the hidden tests and the blind reviews.</li>"
            "<li>Costs are list prices from each tool's own "
            "report.</li></ul></div></div>",
            "Conclusion",
        )
    )
    appendix = [
        (
            r["run"],
            r["tool"],
            r["model"].replace("claude-", "").replace("deepseek/", ""),
            f"${num(r['cost_usd']):.2f}",
            r["wall_min"],
            f"{r['hidden_refusal']}+{r['hidden_allowed']}",
            r["verify_passed"],
            r["mutants_killed"] or "—",
            f"{r['review_medium'] or '—'}/{r['review_low'] or '—'}",
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
                    "Tool",
                    "Model",
                    "Cost",
                    "Min",
                    "Hidden",
                    "Verified",
                    "Mutants",
                    "Medium/Low",
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


TEMPLATE = (HERE / "harness" / "presentation_template.html").read_text()

if __name__ == "__main__":
    build()

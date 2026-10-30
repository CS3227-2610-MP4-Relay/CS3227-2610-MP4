"""Create one experiment run's repository: a clone of the base plus its arm's setup.

Usage: python setup_arm.py <arm> <run_id>

Every arm starts from the same base commit (01f9a24 plus the test-database
harness commit). Workflow arms then change only the repository's workflow files
and commit that change, so the candidate's own work is everything after the
arm-setup commit. Add-on arms change nothing in the repository; their add-on is
loaded by the launcher.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
BASE, MP3, ADDONS = EXP / "base", EXP / "mp3", EXP / "addons"

ARMS = {
    "mp4": "MP4 consolidated workflow (baseline)",
    "mp3": "MP3 six-role staged workflow",
    "solo": "MP4 workflow, one session plays every role",
    "mp4-sonnet-builder": "MP4 workflow, Sonnet builder, Opus reviewers",
    "mp4-sonnet": "MP4 workflow, Sonnet everywhere",
    "superpowers": "superpowers methodology",
    "spec-kit": "spec-kit Spec-Driven Development flow",
    "caveman": "MP4 workflow + caveman",
    "ponytail": "MP4 workflow + ponytail",
    "headroom": "MP4 workflow + headroom proxy",
    "stack": "MP4 workflow + caveman + ponytail + headroom",
    # Reference and evaluation arms for the ideal setup (after the comparison).
    "mp4-haiku": "MP4 workflow, Haiku everywhere",
    "mp4-inherit": "MP4 workflow, subagents on the session's model (Codex, Hermes)",
    "ideal-v1": "Ideal setup v1",
    "ideal-v2": "Ideal setup v2",
    "ideal-v3": "Ideal setup v3",
    "ideal-v4": "Ideal setup v4",
}
IDEAL = Path(
    os.environ.get(
        "IDEAL",
        "/Users/zheng/Desktop/mp4/relay-setups/experiments/agent-setups/ideal",
    )
)

FEATURE_LINE = (
    "- Feature work follows the [`slice`](workflow/skills/slice.md) skill, run by "
    "the orchestrating session with the role agents in "
    "[`workflow/agents/`](workflow/agents/)."
)
FEATURE_LINES = {
    "solo": (
        "- Feature work follows the [`slice`](workflow/skills/slice.md) skill, with "
        "one session playing every role in turn: it works as the builder, then "
        "reviews its own fixed candidate as the verifier and, when the skill calls "
        "for one, as the security-reviewer, following each role's file in "
        "[`workflow/agents/`](workflow/agents/). No subagents are used."
    ),
    "superpowers": (
        "- Feature work follows the superpowers methodology, using its skills "
        "(brainstorming, writing-plans, subagent-driven-development or "
        "executing-plans, "
        "test-driven-development, requesting-code-review and "
        "verification-before-completion). The `slice` skill and the role agents in "
        "`workflow/agents/` are not used. The specs remain the requirements."
    ),
    "spec-kit": (
        "- Feature work follows spec-kit's Spec-Driven Development flow, using the "
        "`speckit-*` skills in `.claude/skills/` (constitution, specify, clarify, "
        "plan, tasks, analyze, implement) and the files in `.specify/`. The `slice` "
        "skill and "
        "the role agents in `workflow/agents/` are not used. The specs in "
        "`workflow/specs/` remain the requirements; spec-kit's feature documents "
        "describe how this change meets them."
    ),
}

MP3_EFFORT = {
    "spec-writer": "medium",
    "test-writer": "medium",
    "implementer": "medium",
    "devops": "medium",
    "spec-critic": "high",
    "reviewer": "high",
    "security-reviewer": "high",
}


def git(repo, *args):
    """Run git in `repo` and return its trimmed output."""
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def replace_once(path, old, new):
    """Replace the single occurrence of `old` in `path`."""
    text = path.read_text()
    assert text.count(old) == 1, f"{path}: expected one {old[:40]!r}"
    path.write_text(text.replace(old, new))


def set_models(repo, roles, model):
    """Set the `model:` line of each role's Claude adapter."""
    for role in roles:
        path = repo / ".claude" / "agents" / f"{role}.md"
        text = path.read_text()
        text, count = re.subn(r"(?m)^model: .*$", f"model: {model}", text)
        assert count == 1, path
        path.write_text(text)


def replace_tree(src, dest):
    """Replace `dest` with a copy of `src`."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def setup_mp3(repo):
    """Swap MP4's workflow tooling for MP3's, keeping Relay's product specs."""
    agents = (repo / "AGENTS.md").read_text().splitlines()[2]
    mp3_agents = (MP3 / "AGENTS.md").read_text().splitlines()
    mp3_agents[2] = agents
    (repo / "AGENTS.md").write_text("\n".join(mp3_agents) + "\n")
    readme = (MP3 / "workflow" / "README.md").read_text().replace("Deskmate", "Relay")
    (repo / "workflow" / "README.md").write_text(readme)
    parts = ("workflow/agents", "workflow/skills", ".claude/agents", ".claude/skills")
    for part in parts:
        replace_tree(MP3 / part, repo / part)
    for part in (".codex/agents", ".codex/skills"):
        replace_tree(MP3 / part, repo / part)
    shutil.copy(MP3 / ".codex" / "hooks.json", repo / ".codex" / "hooks.json")
    shutil.copy(MP3 / ".claude" / "settings.json", repo / ".claude" / "settings.json")
    shutil.rmtree(repo / ".agents")
    for name in (
        "check_scope.py",
        "test_check_scope.py",
        "test_adapters.py",
        "check_logs.py",
        "test_check_logs.py",
    ):
        scripts = Path("workflow") / "scripts" / name
        shutil.copy(MP3 / scripts, repo / scripts)
    # MP4-only test of MP4's Codex approval rules; MP3 had no equivalent.
    (repo / "workflow" / "scripts" / "test_codex_approvals.py").unlink()
    for role, effort in MP3_EFFORT.items():
        path = repo / ".claude" / "agents" / f"{role}.md"
        text = path.read_text()
        head = f"name: {role}\n"
        assert text.count(head) == 1, path
        path.write_text(
            text.replace(head, f"{head}model: claude-opus-5-5\neffort: {effort}\n")
        )


def setup_spec_kit(repo):
    """Install spec-kit's Claude skills and files with its own CLI."""
    subprocess.run(
        [
            "uvx",
            "--from",
            str(ADDONS / "spec-kit"),
            "specify",
            "init",
            "--here",
            "--force",
            "--non-interactive",
            "--integration",
            "claude",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    # The adapter test lists every skill; spec-kit adds its own speckit-* skills.
    replace_once(
        repo / "workflow" / "scripts" / "test_adapters.py",
        'p.parent.name for p in (ROOT / root / "skills").glob("*/SKILL.md")',
        "p.parent.name\n"
        '                    for p in (ROOT / root / "skills").glob("*/SKILL.md")\n'
        '                    if not p.parent.name.startswith("speckit-")',
    )


def main(arm, run_id):
    """Clone the base for `run_id`, apply `arm`'s setup and record its commits."""
    assert arm in ARMS, arm
    repo = EXP / "runs" / run_id
    assert not repo.exists(), repo
    subprocess.run(["git", "clone", "-q", str(BASE), str(repo)], check=True)
    git(repo, "remote", "remove", "origin")
    git(repo, "config", "user.name", "Relay experiment")
    git(repo, "config", "user.email", "experiment@relay.invalid")
    with open(repo / ".git" / "info" / "exclude", "a") as exclude:
        exclude.write(".venv\n")
    (repo / ".venv").symlink_to(EXP / "venv")

    if arm == "mp3":
        setup_mp3(repo)
    elif arm in FEATURE_LINES:
        if arm == "spec-kit":
            setup_spec_kit(repo)
        replace_once(repo / "AGENTS.md", FEATURE_LINE, FEATURE_LINES[arm])
    if arm == "mp4-sonnet-builder":
        set_models(repo, ["builder"], "claude-sonnet-5-5")
    if arm == "mp4-sonnet":
        roles = ["builder", "verifier", "security-reviewer"]
        set_models(repo, roles, "claude-sonnet-5-5")
    if arm == "mp4-haiku":
        roles = ["builder", "verifier", "security-reviewer"]
        set_models(repo, roles, "claude-haiku-5-5")
    if arm == "mp4-inherit":
        roles = ["builder", "verifier", "security-reviewer"]
        set_models(repo, roles, "inherit")
        for path in (repo / ".codex" / "agents").glob("*.toml"):
            text = re.sub(
                r"(?m)^model(_reasoning_effort)? = .*\n", "", path.read_text()
            )
            path.write_text(text)
    if arm.startswith("ideal-"):
        version = arm.removeprefix("ideal-")
        install = IDEAL / "install.py"
        subprocess.run([sys.executable, str(install), version, str(repo)], check=True)

    if git(repo, "status", "--porcelain"):
        git(repo, "add", "-A")
        message = f"chore: Configure the {arm} setup (experiment)"
        git(repo, "commit", "-q", "-m", message)
    meta = {
        "arm": arm,
        "arm_description": ARMS[arm],
        "run_id": run_id,
        "base": git(BASE, "rev-parse", "HEAD"),
        "arm_base": git(repo, "rev-parse", "HEAD"),
    }
    (EXP / "out" / f"{run_id}.meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta))


if __name__ == "__main__":
    main(*sys.argv[1:])

"""Install the portable agent workflow into any Git repository.

Usage: python install.py <repo> [--project <filled project.md>] [--force]

It copies `agent-workflow/` and the tool adapters, adds the workflow block to the
top of `AGENTS.md` (creating the file if needed), and makes sure `CLAUDE.md`
loads `AGENTS.md`. It never edits other files. An existing
`agent-workflow/project.md` is kept unless --force is given. Without --project,
the template is installed and must be filled in before use.
"""

import argparse
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
START, END = "<!-- agent-workflow:start -->", "<!-- agent-workflow:end -->"

# Source path in this package, then destination path in the repository.
ADAPTERS = [
    ("adapters/claude/agents/aw-reviewer.md", ".claude/agents/aw-reviewer.md"),
    (
        "adapters/claude/agents/aw-security-reviewer.md",
        ".claude/agents/aw-security-reviewer.md",
    ),
    ("adapters/claude/skills/aw-slice/SKILL.md", ".claude/skills/aw-slice/SKILL.md"),
    ("adapters/codex/agents/aw-reviewer.toml", ".codex/agents/aw-reviewer.toml"),
    (
        "adapters/codex/agents/aw-security-reviewer.toml",
        ".codex/agents/aw-security-reviewer.toml",
    ),
    # Codex and Hermes both read skills from .agents/skills.
    ("adapters/agents/skills/aw-slice/SKILL.md", ".agents/skills/aw-slice/SKILL.md"),
]


def add_block(agents):
    """Put the workflow block near the top of AGENTS.md, replacing an older one."""
    block = (HERE / "agents-block.md").read_text().strip()
    if not agents.exists():
        agents.write_text(f"# Agent instructions\n\n{block}\n")
        return
    text = agents.read_text()
    if START in text:
        text = re.sub(
            re.escape(START) + ".*?" + re.escape(END), block, text, flags=re.DOTALL
        )
    else:
        lines = text.split("\n")
        # After the first heading, if the file starts with one.
        at = 1 if lines and lines[0].startswith("#") else 0
        lines[at:at] = ["", block, ""]
        text = "\n".join(lines)
    agents.write_text(text)


def main():
    """Install the workflow into the given repository."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo")
    parser.add_argument("--project", help="a filled-in project.md to install")
    parser.add_argument("--force", action="store_true", help="replace project.md")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()

    target = repo / "agent-workflow"
    keep = (
        (target / "project.md").read_text()
        if (target / "project.md").exists()
        else None
    )
    shutil.copytree(HERE / "agent-workflow", target, dirs_exist_ok=True)
    if args.project:
        shutil.copy(args.project, target / "project.md")
    elif keep is not None and not args.force:
        (target / "project.md").write_text(keep)

    for source, destination in ADAPTERS:
        path = repo / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(HERE / source, path)

    add_block(repo / "AGENTS.md")
    claude = repo / "CLAUDE.md"
    if not claude.exists():
        claude.write_text("@AGENTS.md\n")
    elif "AGENTS.md" not in claude.read_text():
        claude.write_text(claude.read_text().rstrip("\n") + "\n\n@AGENTS.md\n")

    template = (HERE / "agent-workflow" / "project.md").read_text()
    filled = (target / "project.md").read_text() != template
    print(f"installed the agent workflow into {repo}")
    if not filled:
        print("fill in agent-workflow/project.md before the first run")


if __name__ == "__main__":
    main()

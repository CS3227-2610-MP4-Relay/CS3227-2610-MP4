"""Install a version of the ideal setup into a Relay checkout.

Usage: python install.py <version> <repo>, for example `python install.py v1 .`

It copies the version's workflow files, patches AGENTS.md, the verifier role and
the tool adapters, and leaves everything else alone. Run the repository's full
verification afterwards; the adapter tests check that every role and skill still
has its Claude and Codex adapters.
"""

import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

FEATURE_OLD = (
    "- Feature work follows the [`slice`](workflow/skills/slice.md) skill, run by "
    "the orchestrating session with the role agents in "
    "[`workflow/agents/`](workflow/agents/)."
)
FEATURE_NEW = (
    "- Feature work follows the [`slice`](workflow/skills/slice.md) skill: the "
    "coordinating session builds the slice, and independent read-only reviewers from "
    "[`workflow/agents/`](workflow/agents/) check it."
)
PROFILE_SECTION = (
    "## Model profile\n\n"
    "Before starting work, choose your profile. Run `printenv RELAY_PROFILE`: if it "
    "prints `strong` or `guarded`, use that profile. Otherwise use `strong` only if "
    "you are a Claude Opus or Sonnet model or a GPT-5-class model, and `guarded` for "
    "any other model or when unsure. Read `workflow/profiles/<profile>.md` and follow "
    "it together with the slice skill, and name the profile at the start of your "
    "report.\n\n"
)
# From v4: the profile is never chosen by the model; unset means guarded.
PROFILE_SECTION_V4 = (
    "## Model profile\n\n"
    "Before starting work, run `printenv RELAY_PROFILE`. If it prints `strong`, "
    "read `workflow/profiles/strong.md`; otherwise read "
    "`workflow/profiles/guarded.md`. Do not choose a profile yourself. Follow it "
    "together with the slice skill, and name the profile at the start of your "
    "report.\n\n"
)
VERIFIER_OLD = "4. Review correctness, role/workspace isolation,"
VERIFIER_NEW = (
    "4. For a Standard slice with no separate security-reviewer, also apply "
    "[the security-reviewer's checks](security-reviewer.md). Review correctness, "
    "role/workspace isolation,"
)
# From v2: the two checks behind every Medium finding in the comparison runs.
VERIFIER_CHECKS = (
    "4. Repeat the coordinator's two consistency checks yourself: search "
    "`workflow/specs/` and `docs/` for every name the change touches and report "
    "any statement left incomplete, and report any existing test whose input was "
    "switched to one the new rule allows instead of keeping what it tested. "
)
SLICE_DESCRIPTION = (
    "Run a coherent slice, built spec-first in this session and then independently "
    "reviewed. Use only when the human asks to run a slice."
)


def replace_once(path, old, new):
    """Replace the single occurrence of `old` in `path`."""
    text = path.read_text()
    assert text.count(old) == 1, f"{path}: expected one {old[:50]!r}"
    path.write_text(text.replace(old, new))


def main(version, repo):
    """Copy and patch `version` of the ideal setup into `repo`."""
    source, repo = HERE / version, Path(repo).resolve()
    shutil.copytree(source / "workflow", repo / "workflow", dirs_exist_ok=True)

    agents = repo / "AGENTS.md"
    replace_once(agents, FEATURE_OLD, FEATURE_NEW)
    profile = PROFILE_SECTION_V4 if version >= "v4" else PROFILE_SECTION
    replace_once(agents, "## Scope confirmation\n", profile + "## Scope confirmation\n")
    verifier_new = VERIFIER_NEW
    if version != "v1":
        verifier_new = VERIFIER_CHECKS + VERIFIER_NEW.removeprefix("4. ")
    replace_once(
        repo / "workflow" / "agents" / "verifier.md", VERIFIER_OLD, verifier_new
    )

    # Subagents run on the session's model unless the person launching pins one.
    for path in (repo / ".claude" / "agents").glob("*.md"):
        text, count = re.subn(r"(?m)^model: .*$", "model: inherit", path.read_text())
        assert count == 1, path
        path.write_text(text)
    for path in (repo / ".codex" / "agents").glob("*.toml"):
        text = re.sub(r"(?m)^model(_reasoning_effort)? = .*\n", "", path.read_text())
        path.write_text(text)
    for path in (
        repo / ".claude" / "skills" / "slice" / "SKILL.md",
        repo / ".agents" / "skills" / "slice" / "SKILL.md",
    ):
        text = re.sub(
            r"(?m)^description: .*$",
            f"description: {SLICE_DESCRIPTION}",
            path.read_text(),
        )
        path.write_text(text)
    print(f"installed {version} into {repo}")


if __name__ == "__main__":
    main(*sys.argv[1:])

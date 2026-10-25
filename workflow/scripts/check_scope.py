#!/usr/bin/env python3
"""Check file changes against a role agent's write scope.

A role's scope is the `writes` and `never_writes` lists in the front matter of
workflow/agents/<role>.md. A path is in scope if it matches a `writes` pattern
and no `never_writes` pattern. In patterns, `*` stays within one folder and
`**` spans folders.

Usage:
  python workflow/scripts/check_scope.py <role> [--base <commit>]
      Checks every change since <commit> (committed or not, plus untracked
      files), or every uncommitted change if no base is given. Exit 1 if a
      change is out of scope or HEAD has moved from <commit>. Record the base
      with `git rev-parse HEAD` before a role agent runs; check after it ends.
  python workflow/scripts/check_scope.py --hook
      PreToolUse hook for Claude Code (Edit, Write) and Codex (apply_patch).
      Reads the tool call from stdin and exits 2 to block a role agent's edit
      outside its scope. Calls from the main session or from agents without a
      role file are allowed.
  python workflow/scripts/check_scope.py --snapshot <manifest>
      Save HEAD, index identity and hashes of tracked/nonignored files in a
      manifest outside the repository. Never reads secret .env files.
  python workflow/scripts/check_scope.py <role> --since <manifest>
      Check content changes since a snapshot, including existing dirty files.
  python workflow/scripts/check_scope.py --unchanged <manifest>
      Check that the review candidate still matches a snapshot.
"""

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = ROOT / "workflow" / "agents"
SCOPE_KEYS = ("writes", "never_writes")
FLAGS = re.IGNORECASE if os.name == "nt" else 0
PATCH_PATH = re.compile(
    r"^\s*\*\*\*\s*(?:Add File|Update File|Delete File|Move to)\s*:\s*(.+?)\s*$",
    re.MULTILINE,
)


def load_scope(role):
    """Return the role's scope, or None if the role has no file."""
    path = AGENTS_DIR / f"{role.replace('_', '-')}.md"
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path} has no front matter")
    scope = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        if key.strip() in SCOPE_KEYS:
            scope[key.strip()] = json.loads(value)
    missing = [key for key in SCOPE_KEYS if key not in scope]
    if missing:
        raise ValueError(f"{path} front matter lacks {', '.join(missing)}")
    return scope


def glob_to_regex(pattern):
    """Compile a scope pattern into a regular expression."""
    parts = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            parts.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(parts), FLAGS)


def matches(path, patterns):
    """Return whether the path matches any of the patterns."""
    return any(glob_to_regex(pattern).fullmatch(path) for pattern in patterns)


def in_scope(path, scope):
    """Check a repository-relative path that uses forward slashes."""
    return matches(path, scope["writes"]) and not matches(path, scope["never_writes"])


def relative_to_root(path, root=ROOT):
    """Return the path relative to the repository root, or None if outside it."""
    try:
        rel = os.path.relpath(
            os.path.normcase(os.path.abspath(path)), os.path.normcase(root)
        )
    except ValueError:  # another drive on Windows
        return None
    rel = rel.replace("\\", "/")
    return None if rel == ".." or rel.startswith("../") else rel


def git(root, *args):
    """Run git in root and return its output, raising if it fails."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8", errors="replace")


def changed_paths(base=None, root=ROOT):
    """Return changed paths, including both sides of a rename and untracked files."""
    paths = []
    if base:
        paths += [
            p
            for p in git(root, "diff", "--name-only", "--no-renames", "-z", base).split(
                "\0"
            )
            if p
        ]
    entries = git(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all"
    ).split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        if not base or entry.startswith("??"):
            paths.append(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            if not base:
                paths.append(entries[i])
            i += 1
    return sorted(set(paths))


def check_working_tree(role, base=None, root=ROOT):
    """Report out-of-scope changes and a moved HEAD, and return the exit code."""
    scope = load_scope(role)
    if scope is None:
        print(f"Unknown role '{role}': no workflow/agents/{role}.md", file=sys.stderr)
        return 2
    problems = [
        f"  {path}" for path in changed_paths(base, root) if not in_scope(path, scope)
    ]
    if (
        base
        and git(root, "rev-parse", "HEAD").strip()
        != git(root, "rev-parse", base).strip()
    ):
        problems.append(
            f"  HEAD has moved from {base}: "
            "role agents must not commit or switch branches"
        )
    if problems:
        print(f"Outside the {role} scope:")
        print("\n".join(problems))
        return 1
    print(f"All changes are within the {role} scope.")
    return 0


def candidate_snapshot(root=ROOT):
    """Hash review inputs without following symlinks or reading secret env files."""
    paths = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    files = {}
    for name in sorted(set(filter(None, paths.split("\0")))):
        path = root / name
        if path.name == ".env" or (
            path.name.startswith(".env.") and path.name != ".env.example"
        ):
            continue
        cursor = root
        for part in path.relative_to(root).parts[:-1]:
            cursor = cursor / part
            try:
                info = cursor.lstat()
            except FileNotFoundError:
                break
            if stat.S_ISLNK(info.st_mode) or (
                getattr(info, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            ):
                raise ValueError(f"Refusing candidate with redirected parent: {cursor}")
        if path.is_symlink():
            data = os.readlink(path).encode("utf-8")
            kind = "link"
        elif path.is_file():
            data = path.read_bytes()
            kind = "file"
        elif path.exists():
            # Do not falsely identify a submodule or junction by an empty hash.
            raise ValueError(f"Candidate directory needs separate review: {path}")
        else:
            data = b""
            kind = "missing"
        mode = stat.S_IMODE(path.lstat().st_mode) if path.exists() else 0
        files[name] = f"{kind}:{mode}:{hashlib.sha256(data).hexdigest()}"
    head = (
        git(root, "rev-parse", "--verify", "HEAD").strip() if has_head(root) else None
    )
    index = git(root, "ls-files", "--stage", "-z").encode("utf-8")
    return {
        "version": 1,
        "root": str(root.resolve()),
        "head": head,
        "index": hashlib.sha256(index).hexdigest(),
        "files": files,
    }


def has_head(root):
    """Return whether this repository has an initial commit."""
    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=root,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def load_snapshot(path, root=ROOT):
    """Read a versioned manifest and reject a different repository."""
    snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    if snapshot.get("version") != 1 or snapshot.get("root") != str(root.resolve()):
        raise ValueError("snapshot version or repository does not match")
    if not isinstance(snapshot.get("files"), dict):
        raise TypeError("snapshot has no file hashes")
    return snapshot


def check_snapshot(path, role=None, root=ROOT):
    """Check a fixed candidate, or scope changes relative to a dirty baseline."""
    before = load_snapshot(path, root)
    after = candidate_snapshot(root)
    changed = sorted(
        name
        for name in before["files"].keys() | after["files"].keys()
        if before["files"].get(name) != after["files"].get(name)
    )
    if role:
        scope = load_scope(role)
        if scope is None:
            print(f"Unknown role '{role}'", file=sys.stderr)
            return 2
        problems = [name for name in changed if not in_scope(name, scope)]
    else:
        problems = changed
    if before["index"] != after["index"]:
        problems.append("Git index changed")
    if before["head"] != after["head"]:
        problems.append("HEAD moved")
    if problems:
        label = f"Outside the {role} scope" if role else "Candidate changed"
        print(f"{label}:\n" + "\n".join(f"  {name}" for name in problems))
        return 1
    print(
        f"All changes are within the {role} scope." if role else "Candidate unchanged."
    )
    return 0


def check_hook_call():
    """Handle a hook call from stdin, returning 2 to block an out-of-scope edit."""
    try:
        event = json.load(sys.stdin)
    except ValueError:
        print("check_scope hook: stdin is not a JSON tool call", file=sys.stderr)
        return 1
    role = event.get("agent_type")
    if not role:
        return 0
    try:
        scope = load_scope(role)
    except ValueError as error:  # a broken role file blocks rather than allows
        print(f"Cannot read the {role} scope: {error}", file=sys.stderr)
        return 2
    if scope is None:
        return 0
    targets = edited_paths(event.get("tool_input") or {})
    if not targets:
        print(
            f"Blocked: cannot tell which files this {role} edit writes.",
            file=sys.stderr,
        )
        return 2
    for target in targets:
        if not os.path.isabs(target):
            target = os.path.join(event.get("cwd") or ROOT, target)
        rel = relative_to_root(target)
        if rel is None or not in_scope(rel, scope):
            print(
                f"Blocked: {role} may not write {rel or target}. It is outside "
                f"the scope in workflow/agents/{role.replace('_', '-')}.md. "
                "Do not work around this; report it in your handoff.",
                file=sys.stderr,
            )
            return 2
    return 0


def edited_paths(tool_input):
    """Return the paths a Claude Code edit or a Codex apply_patch would write."""
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if target:
        return [target]
    patch = (
        tool_input.get("command")
        or tool_input.get("input")
        or tool_input.get("patch")
        or ""
    )
    return PATCH_PATH.findall(patch) if isinstance(patch, str) else []


def main(args):
    """Run the command in the usage above and return its exit code."""
    if args == ["--hook"]:
        return check_hook_call()
    if len(args) == 2 and args[0] == "--snapshot":
        target = Path(args[1]).resolve()
        if relative_to_root(target) is not None:
            print("Store the snapshot outside the repository.", file=sys.stderr)
            return 2
        target.write_text(
            json.dumps(candidate_snapshot(), indent=2) + "\n", encoding="utf-8"
        )
        return 0
    if len(args) == 2 and args[0] == "--unchanged":
        return check_snapshot(args[1])
    if len(args) == 3 and args[1] == "--since":
        return check_snapshot(args[2], args[0])
    if len(args) == 1 and not args[0].startswith("-"):
        return check_working_tree(args[0])
    if len(args) == 3 and not args[0].startswith("-") and args[1] == "--base":
        return check_working_tree(args[0], args[2])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

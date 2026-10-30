"""Plant the five behavioural mutants in one candidate: python mutate.py <run_id>

Each task's five mutants are fixed in method.md. How each is planted depends on
the candidate's code, so results/mutations/<run_id>.json gives, per mutant,
exact text replacements in the candidate's own files. A mutant is killed when the
candidate's own full test suite fails, and live when the hidden suite fails.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXP = Path(os.environ["EXP"])
PRIVATE = Path(os.environ["PRIVATE"])
RESULTS = Path(__file__).resolve().parent.parent / "results"


def pytest(copy, target, suffix):
    """Run pytest on `target` in `copy`; return whether it passed."""
    done = subprocess.run(  # noqa: PLW1510 - the exit code is the result
        f"source .venv/bin/activate && pytest -q -x -p no:cacheprovider {target}",
        cwd=copy,
        shell=True,
        capture_output=True,
        text=True,
        executable="/bin/bash",
        env={**os.environ, "TOX_PARALLEL_ENV": suffix},
    )
    return done.returncode == 0


def main(run):
    """Plant each mutant in a copy of `run` and record whether it was caught."""
    spec = json.loads((RESULTS / "mutations" / f"{run}.json").read_text())
    source = PRIVATE / "evalwt" / run
    meta = json.loads((EXP / "out" / f"{run}.meta.json").read_text())
    task_dir = {"2": "eval2", "3": "eval3", "4": "eval4"}.get(meta.get("task"), "eval")
    hidden = PRIVATE / task_dir / "zz_hidden"
    outcome = {}
    for mutant, edits in spec["mutants"].items():
        copy = PRIVATE / "mut" / f"{run}-{mutant}"
        if copy.exists():
            shutil.rmtree(copy)
        shutil.copytree(source, copy, symlinks=True)
        for edit in edits:
            path = copy / edit["file"]
            text = path.read_text()
            assert text.count(edit["old"]) == 1, (mutant, edit["file"], edit["old"])
            path.write_text(text.replace(edit["old"], edit["new"]))
        suffix = f"m_{run}_{mutant}".replace("-", "_")
        killed = not pytest(copy, "", suffix)
        shutil.copytree(hidden, copy / "src" / "zz_hidden")
        live = not pytest(copy, "src/zz_hidden", suffix)
        outcome[mutant] = {"killed": killed, "live": live}
        shutil.rmtree(copy)
        print(run, mutant, outcome[mutant])
    (EXP / "out" / f"{run}.mutants.json").write_text(json.dumps(outcome, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])

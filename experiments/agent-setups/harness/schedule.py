"""Run a queue of experiment runs, a few at a time: python schedule.py <queue_file>

Each queue line is "<arm> <run_id> [KEY=VALUE ...]", where TOOL picks Claude Code
(run_arm.sh, the default), Codex or Hermes (run_other.sh) and other keys are
passed as environment. For each run this sets up its repository, launches it
and, when it exits, scores it with evaluate.py. At most SLOTS runs are in
flight, and a run past MAX_WALL seconds is stopped. Progress goes to
out/schedule.log.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

EXP = Path(os.environ["EXP"])
HARNESS = Path(__file__).resolve().parent
SLOTS = int(os.environ.get("SLOTS", "3"))
# A run still going after this many seconds is stopped and reported unfinished.
MAX_WALL = int(os.environ.get("MAX_WALL", "10800"))
PYTHON = str(EXP / "venv" / "bin" / "python")


def log(message):
    """Append a timestamped line to the schedule log."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(EXP / "out" / "schedule.log", "a") as file:
        file.write(f"{stamp} {message}\n")


def launch(arm, run, settings):
    """Set up and start one run; return its process.

    `settings` are the queue line's KEY=VALUE words: TOOL (claude, codex or
    hermes; claude by default), and environment such as MODEL_OVERRIDE and
    RELAY_PROFILE for the session.
    """
    env = dict(word.split("=", 1) for word in settings)
    if not (EXP / "runs" / run).exists():
        setup = subprocess.run(  # noqa: PLW1510 - a failed setup is logged and skipped
            [PYTHON, str(EXP / "bin" / "setup_arm.py"), arm, run],
            env={**os.environ, **env},
            capture_output=True,
            text=True,
        )
        if setup.returncode != 0:
            log(f"setup failed {run}: {setup.stderr.strip()[-300:]}")
            return None
    tool = env.pop("TOOL", "claude")
    log(f"start {run} ({arm}, {tool}, {env})")
    if tool == "claude":
        command = [str(EXP / "bin" / "run_arm.sh"), arm, run]
    else:
        command = [str(EXP / "bin" / "run_other.sh"), tool, arm, run]
    return subprocess.Popen(command, env={**os.environ, **env}, start_new_session=True)


def stop(run):
    """Record a stopped run's end, as its launcher was stopped before writing it."""
    end = EXP / "out" / f"{run}.end.json"
    if not end.exists():
        start = json.loads((EXP / "out" / f"{run}.start.json").read_text())
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        end.write_text(json.dumps({**start, "end": stamp, "exit": "timeout"}))


def main(queue_file):
    """Run every queued run, SLOTS at a time, scoring each as it ends."""
    queue = [line.split() for line in Path(queue_file).read_text().splitlines() if line]
    running, started = {}, {}
    while queue or running:
        while queue and len(running) < SLOTS:
            arm, run, *settings = queue.pop(0)
            if (EXP / "out" / f"{run}.end.json").exists():
                continue
            process = launch(arm, run, settings)
            if process is None:
                continue
            running[run] = process
            started[run] = time.monotonic()
        time.sleep(20)
        for run, process in list(running.items()):
            if process.poll() is None:
                if time.monotonic() - started[run] > MAX_WALL:
                    log(f"timeout {run} after {MAX_WALL}s: stopping it")
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait()
                    stop(run)
                else:
                    continue
            del running[run]
            log(f"end {run} exit={process.returncode}")
            done = subprocess.run(  # noqa: PLW1510 - logged, not raised
                [PYTHON, str(HARNESS / "evaluate.py"), run],
                capture_output=True,
                text=True,
            )
            log(f"eval {run}: {(done.stdout or done.stderr).strip()[-300:]}")


if __name__ == "__main__":
    main(sys.argv[1])

#!/usr/bin/env bash
# Launch one experiment run headlessly: run_arm.sh <arm> <run_id> [prompt_file]
#
# Every run uses the same pinned Claude Code binary, permissions, disallowed
# tools, effort and prompt. Only the arm's model, add-on plugins or proxy differ.
# MODEL_OVERRIDE (or SMOKE_MODEL, for harness smoke tests) overrides the model.
set -euo pipefail

ARM=$1
RUN=$2
EXP=$(cd "$(dirname "$0")/.." && pwd)
PROMPT_FILE=${3:-${PROMPT_FILE:-$EXP/task-prompt.md}}
REPO=$EXP/runs/$RUN
OUT=$EXP/out
CLAUDE=$EXP/bin/claude-2.1.312
ADDONS=$EXP/addons

MODEL=claude-opus-5-5
[[ $ARM == mp4-sonnet ]] && MODEL=claude-sonnet-5-5
MODEL=${MODEL_OVERRIDE:-${SMOKE_MODEL:-$MODEL}}

PLUGINS=()
case $ARM in
  caveman) PLUGINS=(--plugin-dir "$ADDONS/caveman") ;;
  ponytail) PLUGINS=(--plugin-dir "$ADDONS/ponytail") ;;
  superpowers) PLUGINS=(--plugin-dir "$ADDONS/superpowers") ;;
  stack) PLUGINS=(--plugin-dir "$ADDONS/caveman" --plugin-dir "$ADDONS/ponytail") ;;
esac

DISALLOWED=(WebFetch WebSearch "Bash(gh:*)" "Bash(git push:*)" "Bash(git remote:*)"
  "Bash(git fetch:*)" "Bash(git pull:*)" "Bash(git clone:*)" "Bash(curl:*)"
  "Bash(wget:*)" "Bash(docker:*)" "Bash(pip install:*)" "Bash(uv pip:*)")
TOOLS=Task,Bash,Read,Edit,Write,Glob,Grep,Skill,TodoWrite,NotebookEdit
[[ $ARM == solo ]] && TOOLS=Bash,Read,Edit,Write,Glob,Grep,Skill,TodoWrite,NotebookEdit

export TOX_PARALLEL_ENV=${RUN//-/_}
export DISABLE_AUTOUPDATER=1

PROXY_PID=
if [[ $ARM == headroom || $ARM == stack ]]; then
  PORT=$((8800 + $(cksum <<<"$RUN" | cut -d' ' -f1) % 150))
  mkdir -p "$OUT/$RUN.headroom"
  HEADROOM_WORKSPACE_DIR=$OUT/$RUN.headroom HEADROOM_CONFIG_DIR=$OUT/$RUN.headroom \
    DO_NOT_TRACK=1 HEADROOM_BEACON=off \
    "$ADDONS/headroom-venv/bin/headroom" proxy --port "$PORT" \
    --no-subscription-tracking --no-rate-limit >"$OUT/$RUN.headroom.log" 2>&1 &
  PROXY_PID=$!
  for _ in $(seq 60); do
    curl -s -o /dev/null "http://127.0.0.1:$PORT/health" && break
    sleep 1
  done
  export ANTHROPIC_BASE_URL=http://127.0.0.1:$PORT
fi

START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "{\"run\":\"$RUN\",\"arm\":\"$ARM\",\"model\":\"$MODEL\",\"start\":\"$START\"}" >"$OUT/$RUN.start.json"
set +e
(cd "$REPO" && "$CLAUDE" -p "$(cat "$PROMPT_FILE")" \
  --model "$MODEL" --effort high \
  --output-format stream-json --verbose \
  --setting-sources project,local --strict-mcp-config \
  --permission-mode acceptEdits \
  --tools "$TOOLS" --allowedTools "$TOOLS" \
  --disallowedTools "${DISALLOWED[@]}" \
  --max-budget-usd "${MAX_BUDGET_USD:-200}" \
  "${PLUGINS[@]}" \
  </dev/null >"$OUT/$RUN.stream.jsonl" 2>"$OUT/$RUN.stderr")
CODE=$?
set -e
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
[[ -n $PROXY_PID ]] && kill "$PROXY_PID" 2>/dev/null || true
echo "{\"run\":\"$RUN\",\"arm\":\"$ARM\",\"model\":\"$MODEL\",\"start\":\"$START\",\"end\":\"$END\",\"exit\":$CODE}" >"$OUT/$RUN.end.json"
exit $CODE

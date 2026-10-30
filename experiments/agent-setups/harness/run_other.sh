#!/usr/bin/env bash
# Launch one run in Codex or Hermes: run_other.sh <codex|hermes> <arm> <run_id> [prompt_file]
#
# Used only to evaluate the ideal setup, after the Claude Code comparison. Both
# tools run DeepSeek v4.1 Flash through the person's OpenRouter account with
# their normal safety controls on: Codex in its workspace-write sandbox with its
# own approval reviewer, Hermes with its dangerous-command approvals. Web access
# is off and each run gets its own test database, as in the Claude Code runs.
set -euo pipefail

TOOL=$1
ARM=$2
RUN=$3
EXP=$(cd "$(dirname "$0")/.." && pwd)
PROMPT_FILE=${4:-$EXP/task-prompt.md}
REPO=$EXP/runs/$RUN
OUT=$EXP/out
export TOX_PARALLEL_ENV=${RUN//-/_}

START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "{\"run\":\"$RUN\",\"arm\":\"$ARM\",\"tool\":\"$TOOL\",\"start\":\"$START\"}" >"$OUT/$RUN.start.json"
set +e
case $TOOL in
  codex)
    MODEL=${MODEL_OVERRIDE:-deepseek/deepseek-v4.1-flash}
    codex exec --json -C "$REPO" -m "$MODEL" \
      -c sandbox_workspace_write.network_access=true \
      -c web_search=disabled --approve-for-me \
      -o "$OUT/$RUN.last.txt" "$(cat "$PROMPT_FILE")" \
      </dev/null >"$OUT/$RUN.codex.jsonl" 2>"$OUT/$RUN.stderr"
    ;;
  hermes)
    MODEL=${MODEL_OVERRIDE:-deepseek/deepseek-v4.1-flash}
    hermes -z "$(cat "$PROMPT_FILE")" --in "$REPO" \
      -m "$MODEL" --provider openrouter --reasoning high \
      -t terminal,file,skills,todo,delegation --ignore-user-config \
      --usage-file "$OUT/$RUN.hermes-usage.json" \
      </dev/null >"$OUT/$RUN.last.txt" 2>"$OUT/$RUN.stderr"
    ;;
esac
CODE=$?
set -e
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "{\"run\":\"$RUN\",\"arm\":\"$ARM\",\"tool\":\"$TOOL\",\"model\":\"$MODEL\",\"start\":\"$START\",\"end\":\"$END\",\"exit\":$CODE}" >"$OUT/$RUN.end.json"
exit $CODE

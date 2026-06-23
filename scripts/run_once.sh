#!/usr/bin/env bash
#
# run_once.sh -- one heartbeat of the always-on agent.
#
# This is what the scheduler calls. It does NOT need a human. A cron entry or a
# `while true; sleep` loop calls this; that scheduled invocation IS the "no manual
# trigger" — the agent acts on the clock, not on a person.
#
# Flow:
#   1. fetch_feeds.py pulls new items (the dumb reliable sensor)
#   2. claude -p runs the reasoning cycle described in CLAUDE.md (the brain):
#      updates trends.json memory, decides what's a real trend, posts to Slack.
#
# Requirements on the host:
#   - claude (Claude Code CLI) on PATH
#   - ANTHROPIC_API_KEY in .env or exported in the environment
#   - SLACK_WEBHOOK_URL in .env or exported (post_slack.py errors if absent)
#
set -euo pipefail
cd "$(dirname "$0")/.."

# Load .env (project root) -- .env takes priority over existing env vars.
# Handles quoted values (single or double) and skips blank lines / comments.
if [ -f ".env" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    val="${val#\"}" ; val="${val%\"}"
    val="${val#\'}" ; val="${val%\'}"
    export "$key"="$val"
  done < ".env"
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "error: ANTHROPIC_API_KEY not set in .env or environment" >&2
  exit 1
fi

echo "===================== run @ $(date -u +%FT%TZ) ====================="

# 1. Sense
python3 scripts/fetch_feeds.py

NEW=$(python3 -c "import json;print(len(json.load(open('state/new_items.json'))))" 2>/dev/null || echo 0)
echo "new items this cycle: $NEW"

# 2. Think + act. Headless Claude Code, allowed to run our two scripts + edit state.
#    --dangerously-skip-permissions keeps it non-interactive for unattended runs;
#    in a hackathon sandbox that's fine. Tighten with --allowedTools for real use.
claude -p \
  --dangerously-skip-permissions \
  "Run one Anthropic Emerging-Trends cycle exactly as specified in CLAUDE.md. \
The new items are already in state/new_items.json (do not re-fetch). \
Update state/trends.json, append to state/digest.md, and post any qualifying \
trends to Slack via scripts/post_slack.py. If nothing clears the bar, stay quiet \
and just record the run."

echo "===================== end run ====================="

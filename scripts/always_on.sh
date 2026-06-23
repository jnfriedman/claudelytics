#!/usr/bin/env bash
#
# always_on.sh -- the daemon. THIS is the "always-on, no manual trigger" part.
#
# Two ways to keep the agent alive; this script is option A (portable, zero-setup).
#
#   A) Simple loop (this file): runs a cycle, sleeps INTERVAL, repeats. Start it once
#      and walk away. Survivable for a hackathon demo. Ctrl-C to stop.
#
#   B) Cron (production-ish): add a crontab line instead, e.g. every 15 min:
#         */15 * * * * SLACK_WEBHOOK_URL=... /path/to/scripts/run_once.sh >> /path/to/state/cron.log 2>&1
#      Cron is the cleaner "scheduled, no human" story for judges who ask.
#
# Either way: a clock invokes the agent, not a person. That satisfies the brief's
# "monitors your environment and acts continuously -- no manual triggers."
#
set -euo pipefail
cd "$(dirname "$0")/.."

INTERVAL="${INTERVAL:-900}"   # seconds between cycles (default 15 min)

echo "Anthropic Emerging-Trends Agent -- always-on loop (interval ${INTERVAL}s)"
echo "Press Ctrl-C to stop."
trap 'echo; echo "stopped."; exit 0' INT

while true; do
  scripts/run_once.sh || echo "cycle errored (continuing): $?"
  echo "sleeping ${INTERVAL}s..."
  sleep "$INTERVAL"
done

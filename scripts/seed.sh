#!/usr/bin/env bash
#
# seed.sh -- run ONCE before going live.
#
# Problem: on a cold start, every feed item looks "new" (we saw 443 on first fetch).
# If the agent reasoned over all of those, it would post a wall of alerts and the
# "emerging" framing would be meaningless.
#
# Solution: do a silent fetch that marks all currently-existing items as already-seen,
# WITHOUT posting anything. After this, only genuinely new items (published after you
# went live) flow through to the trend reasoning. That's what makes "emerging" honest.
#
# Optionally, you can let Claude pre-build a baseline trends.json from recent history so
# the agent starts with memory instead of a blank slate -- toggle BUILD_BASELINE=1.
#
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Seeding: marking existing feed items as seen (no Slack posts)..."
python3 scripts/fetch_feeds.py >/dev/null
# new_items.json now holds the backlog; we deliberately discard it for alerting.

BUILD_BASELINE="${BUILD_BASELINE:-0}"
if [[ "$BUILD_BASELINE" == "1" ]]; then
  echo "Building baseline trend memory from recent history (no Slack posts)..."
  claude -p --dangerously-skip-permissions \
    "Read state/new_items.json (this is historical backlog, NOT new). Build an initial \
state/trends.json clustering the LAST 30 DAYS of items into themes per CLAUDE.md. \
Set every theme alerted:true so we never retro-spam. Do NOT post anything to Slack. \
Write a short state/digest.md header noting this was the seed run."
fi

# Reset new_items so the first live run starts clean.
echo "[]" > state/new_items.json
echo "Seed complete. Existing items are now baseline. Go live with: scripts/run_once.sh"

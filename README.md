# Anthropic Emerging-Trends Agent

An **always-on agent** (Hackathon Track 01) that watches everything happening around
**Anthropic** — its own announcements, engineering/research posts, the Claude blog, and
how the wider press covers it — and **speaks up in Slack only when a real trend is
emerging**, not on every headline.

No human triggers it. A clock does. It wakes on a schedule, notices what's *new*, folds it
into a long-running memory of themes, and posts to Slack when something crosses from noise
into signal.

## Why this isn't "a cron job with a prompt"

The difference is **memory**. A stateless script re-summarizes whatever it sees. This agent
remembers prior runs in `state/trends.json`, so it can notice that three items over a week
are actually *one story gaining momentum* — and stay silent on routine noise. The
accumulating memory (and its git history) is the proof it's genuinely always-on.

It also reasons across **two rings of evidence**:
- 🅰️ **Primary** — Anthropic's own channels (it's *saying* something).
- 🌍 **Press** — the world covering Anthropic, keyword-filtered (the world *reacting*).

A story in both rings is a stronger trend than either alone. That cross-ring corroboration
is the agent's core judgment — and exactly what a one-shot summarizer can't do.

## Architecture

```
  scheduler (cron / always_on.sh loop)          ← the "no manual trigger"
        │  every N minutes
        ▼
  scripts/fetch_feeds.py   ── dumb, reliable SENSOR (stdlib only)
        │  writes ~/claudelytics-memory/new_items.json (deduped vs seen.json)
        ▼
  claude -p  (CLAUDE.md)   ── the BRAIN
        │  • folds new items into ~/claudelytics-memory/trends.json (theme memory)
        │  • recomputes momentum, decides what clears the "trend" bar
        │  • appends to ~/claudelytics-memory/digest.md every run (the heartbeat)
        ▼
  scripts/post_slack.py    ── posts ONLY qualifying trends (Block Kit)
```

## Quickstart

```bash
# 0. Requirements: claude (Claude Code CLI) on PATH, Python 3.
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"

# 1. Seed: mark all existing feed history as "already seen" so the first live
#    run doesn't post a wall of backlog. (Optional: BUILD_BASELINE=1 to pre-build memory.)
scripts/seed.sh

# 2. Go live — pick one:
scripts/run_once.sh          # a single cycle (good for the demo / cron)
scripts/always_on.sh         # the daemon loop; runs forever, Ctrl-C to stop

# Or cron (the cleanest "scheduled, no human" story):
# */15 * * * * SLACK_WEBHOOK_URL=... /abs/path/scripts/run_once.sh >> state/cron.log 2>&1
```

No webhook handy? Everything still runs — `post_slack.py` prints the exact payload in
**dry-run** mode instead of sending, so the demo never hard-fails.

## Feeds

Anthropic's news page has **no native RSS**, so the primary ring uses community-maintained
scrapes (verified live) from the `Olshansk/rss-feeds` project, split by type so the agent can
tell a launch from a paper from a changelog. The press ring (The Verge AI, arXiv cs.AI) is
keyword-filtered to Anthropic/Claude. Edit `feeds.json` to add sources; if one feed is down,
the fetcher logs it and keeps going.

## Demo script (90 seconds)

1. Show `~/claudelytics-memory/trends.json` — "this is its memory; it's been watching."
2. `scripts/run_once.sh` — watch it fetch, reason, and post a trend to Slack live.
3. Show the Slack message: headline + *why it matters* + cross-ring evidence.
4. Show `~/claudelytics-memory/digest.md` — "one line per cycle; it's been alive for hours."
5. The kicker: run it again with no new items → it correctly stays **silent**. "A good
   analyst is quiet most of the time and right when they speak."

## Files

| Path | Role |
|------|------|
| `CLAUDE.md` | The agent's standing instructions + trend-judgment criteria |
| `feeds.json` | The two rings of sources |
| `scripts/fetch_feeds.py` | Sensor: fetch, dedupe, keyword-filter |
| `scripts/post_slack.py` | Delivery: Block Kit message + dry-run |
| `scripts/run_once.sh` | One cycle (sensor → claude -p brain) |
| `scripts/always_on.sh` | The daemon loop |
| `scripts/seed.sh` | One-time cold-start primer |
| `~/claudelytics-memory/` | Memory: `seen.json`, `trends.json`, `digest.md`, `new_items.json` |
| `state/` | Template state files (repo only, not used at runtime) |

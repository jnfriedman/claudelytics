#!/usr/bin/env python3
"""
post_slack.py  --  Posts a trend alert to Slack via incoming webhook.

Reads SLACK_WEBHOOK_URL from .env (project root), falling back to the environment
variable. Errors out if neither is set. Pass --dry-run to print the payload to
stdout instead of sending.

Usage:
    echo '<json payload>' | python3 post_slack.py
    python3 post_slack.py --dry-run < alert.json
"""
import json, os, sys, urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)


def _load_dotenv(path):
    """Parse a simple KEY=value .env file; returns dict of found vars."""
    result = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                result[key.strip()] = val.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return result


def _resolve_webhook():
    env_file = _load_dotenv(os.path.join(ROOT, ".env"))
    url = env_file.get("SLACK_WEBHOOK_URL") or os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not url:
        print("error: SLACK_WEBHOOK_URL not set in .env or environment", file=sys.stderr)
        sys.exit(1)
    return url


WEBHOOK = _resolve_webhook()
DRY = "--dry-run" in sys.argv


def build_blocks(alert):
    """alert = {headline, momentum, evidence:[{source,title,link,ring}], so_what}"""
    momentum_emoji = {"accelerating": "🚀", "emerging": "📈", "steady": "📊", "cooling": "📉"}
    head = momentum_emoji.get(alert.get("momentum", "emerging"), "📈")
    blocks = [
        {"type": "header", "text": {"type": "plain_text",
            "text": f"{head} {alert['headline']}"[:150]}},
    ]
    if alert.get("so_what"):
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Why it matters:* {alert['so_what']}"}})
    ev_lines = []
    for e in alert.get("evidence", [])[:6]:
        ring_tag = "🅰️" if e.get("ring") == "primary" else "🌍"
        link = e.get("link") or ""
        title = e.get("title", "")[:90]
        ev_lines.append(f"{ring_tag} <{link}|{title}>  _({e.get('source','')})_" if link
                        else f"{ring_tag} {title}  _({e.get('source','')})_")
    if ev_lines:
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
            "text": "*Evidence:*\n" + "\n".join(ev_lines)}})
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
        "text": "🅰️ = Anthropic direct  ·  🌍 = press/world  ·  _Anthropic Emerging-Trends Agent_"}]})
    return {"blocks": blocks}


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print("no payload on stdin", file=sys.stderr)
        return 1
    alert = json.loads(raw)
    payload = build_blocks(alert)

    if DRY:
        print("=== DRY RUN (--dry-run) ===")
        print(json.dumps(payload, indent=2))
        return 0

    req = urllib.request.Request(
        WEBHOOK, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"slack: {r.status}")
        return 0
    except Exception as e:
        print(f"slack post failed: {e}", file=sys.stderr)
        # fall back to printing so the run still produces visible output
        print(json.dumps(payload, indent=2))
        return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
fetch_feeds.py  --  Ring-aware RSS poller for the Anthropic Emerging-Trends Agent.

Pure standard library (no pip installs) so it runs anywhere Claude Code does.

What it does on each run (this is the "always-on" heartbeat):
  1. Reads feeds.json (primary ring = Anthropic's own channels; press ring = world coverage).
  2. Fetches every feed. If a primary feed is down/stale, falls back gracefully.
  3. Filters the press ring to items that actually mention Anthropic/Claude.
  4. Dedupes against state/seen.json so we ONLY surface genuinely new items.
  5. Writes the new items to state/new_items.json for the Claude reasoning step.

It deliberately does NOT decide what's a trend -- that's Claude's job in run_agent.
This script is the dumb, reliable sensor. Claude is the brain.
"""

import json, os, re, sys, time, hashlib, urllib.request, urllib.error
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)          # project root = parent of scripts/
STATE = os.path.expanduser("~/claudelytics-memory")
os.makedirs(STATE, exist_ok=True)

SEEN_PATH = os.path.join(STATE, "seen.json")
NEW_PATH = os.path.join(STATE, "new_items.json")
FEEDS_PATH = os.path.join(ROOT, "feeds.json")

UA = "anthropic-trends-agent/1.0 (hackathon; always-on)"
TIMEOUT = 20


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def parse_items(xml_bytes):
    """Handle both RSS <item> and Atom <entry>. Return list of dicts."""
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    # RSS
    for it in root.iter("item"):
        title = it.findtext("title", "")
        link = it.findtext("link", "")
        desc = it.findtext("description", "")
        pub = it.findtext("pubDate", "")
        items.append({"title": strip_html(title), "link": link.strip(),
                      "summary": strip_html(desc)[:600], "published": pub})

    # Atom
    ns = "{http://www.w3.org/2005/Atom}"
    for it in root.iter(f"{ns}entry"):
        title = it.findtext(f"{ns}title", "")
        link_el = it.find(f"{ns}link")
        link = link_el.get("href") if link_el is not None else ""
        summ = it.findtext(f"{ns}summary", "") or it.findtext(f"{ns}content", "")
        pub = it.findtext(f"{ns}updated", "") or it.findtext(f"{ns}published", "")
        items.append({"title": strip_html(title), "link": (link or "").strip(),
                      "summary": strip_html(summ)[:600], "published": pub})
    return items


def item_id(it):
    return hashlib.sha1((it["link"] or it["title"]).encode("utf-8")).hexdigest()[:16]


def mentions(it, keywords):
    blob = (it["title"] + " " + it["summary"]).lower()
    return any(k.lower() in blob for k in keywords)


def fetch_feed_with_fallback(feed, fallbacks):
    try:
        return parse_items(fetch(feed["url"])), None
    except Exception as e:
        for fb in fallbacks:
            try:
                return parse_items(fetch(fb["url"])), f"used fallback ({fb['name']})"
            except Exception:
                continue
        return [], f"FAILED: {e}"


def main():
    feeds_cfg = load_json(FEEDS_PATH, {})
    seen = set(load_json(SEEN_PATH, []))
    rings = feeds_cfg.get("rings", {})

    new_items = []
    report = []

    for ring_name, ring in rings.items():
        fallbacks = ring.get("fallback_feeds", [])
        kw = ring.get("keyword_filter")
        for feed in ring.get("feeds", []):
            items, note = fetch_feed_with_fallback(feed, fallbacks)
            kept = 0
            for it in items:
                if kw and not mentions(it, kw):
                    continue
                iid = item_id(it)
                if iid in seen:
                    continue
                seen.add(iid)
                it.update({"id": iid, "ring": ring_name,
                           "source": feed["name"], "source_type": feed["type"],
                           "fetched_at": datetime.now(timezone.utc).isoformat()})
                new_items.append(it)
                kept += 1
            report.append(f"  [{ring_name}] {feed['name']}: {len(items)} items, {kept} new"
                          + (f" ({note})" if note else ""))

    with open(SEEN_PATH, "w") as f:
        json.dump(sorted(seen), f, indent=2)
    with open(NEW_PATH, "w") as f:
        json.dump(new_items, f, indent=2)

    print(f"=== fetch_feeds @ {datetime.now(timezone.utc).isoformat()} ===")
    print("\n".join(report))
    print(f"--> {len(new_items)} new item(s) written to state/new_items.json")
    # exit code 0 always; an empty run is normal, not an error
    return 0


if __name__ == "__main__":
    sys.exit(main())

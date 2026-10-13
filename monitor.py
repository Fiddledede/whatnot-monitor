"""
Whatnot -> Discord live monitor.

Checks each Whatnot username's profile page, and when a show is live that we
haven't announced yet, posts "[user] has just gone live!" plus the show link
to a Discord webhook. Already-announced show IDs are kept in state.json so
each show is only announced once.

Settings come from environment variables (set in GitHub, not in this file):
  DISCORD_WEBHOOK_URL  - your Discord webhook (GitHub secret)
  WHATNOT_USERS        - comma-separated usernames, e.g. "seller1,seller2"
  TEST_MESSAGE         - "true" to just send a test message and stop
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
USERS = [u.strip().lstrip("@") for u in os.environ.get("WHATNOT_USERS", "").split(",") if u.strip()]
TEST = os.environ.get("TEST_MESSAGE", "").lower() == "true"
STATE_FILE = "state.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
# Status values that mean "on air right now". Scheduled/upcoming shows use
# other values (e.g. CREATED), so they are ignored.
LIVE_STATUSES = {"PLAYING", "LIVE", "STARTED", "IN_PROGRESS", "ACTIVE"}


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-GB,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def _enclosing_object(text, pos):
    """Return (start, end) of the JSON object that contains position pos."""
    depth, start = 0, -1
    for i in range(pos, -1, -1):
        c = text[i]
        if c == "}":
            depth += 1
        elif c == "{":
            if depth == 0:
                start = i
                break
            depth -= 1
    if start < 0:
        return None
    depth = 0
    for j in range(start, min(len(text), start + 200000)):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return start, j + 1
    return None


def _own_id(text, span):
    """The show's own "id" - the one directly inside its object, not a nested one."""
    start, end = span
    depth = 0
    i = start
    id_re = re.compile(r'"id"\s*:\s*"(' + UUID + r')"')
    while i < end:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 1 and text.startswith('"id"', i):
            m = id_re.match(text, i)
            if m:
                return m.group(1).lower()
        i += 1
    return None


def find_live_shows(html):
    """Return (set of live show IDs, set of all status values seen)."""
    # Page data is often embedded as escaped JSON inside <script> tags.
    text = html.replace('\\"', '"').replace("\\/", "/")
    live, seen = set(), set()

    markers = []
    for m in re.finditer(r'"status"\s*:\s*"([A-Za-z_]+)"', text):
        status = m.group(1).upper()
        seen.add(status)
        if status in LIVE_STATUSES:
            markers.append(m.start())
    # Fallback for pages that mark live shows with a boolean instead.
    markers += [m.start() for m in re.finditer(r'"isLive"\s*:\s*true', text)]

    for pos in markers:
        span = _enclosing_object(text, pos)
        if span:
            show_id = _own_id(text, span)
            if show_id:
                live.add(show_id)

    return live, seen


def post_discord(content):
    data = json.dumps({"content": content}).encode()
    req = urllib.request.Request(WEBHOOK, data=data, headers={
        "Content-Type": "application/json", "User-Agent": "whatnot-live-monitor"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    if not WEBHOOK:
        sys.exit("DISCORD_WEBHOOK_URL is not set - add it as a repository secret.")

    if TEST:
        post_discord("✅ Whatnot live monitor is connected and working.")
        print("Test message sent.")
        return

    if not USERS:
        sys.exit("WHATNOT_USERS is not set - add it as a repository variable.")

    state = load_state()
    changed = False

    for user in USERS:
        url = f"https://www.whatnot.com/user/{user}"
        try:
            html = fetch(url)
        except urllib.error.HTTPError as e:
            print(f"[{user}] Could not load profile (HTTP {e.code}). Skipping.")
            continue
        except Exception as e:  # network hiccup - try again next run
            print(f"[{user}] Could not load profile ({e}). Skipping.")
            continue

        live_ids, seen = find_live_shows(html)
        link_count = len(set(re.findall(r"/live/(" + UUID + ")", html)))
        print(f"[{user}] page {len(html)} chars | show links: {link_count} | "
              f"statuses seen: {sorted(seen) or 'none'} | live now: {sorted(live_ids) or 'none'}")

        announced = state.get(user, [])
        for show_id in sorted(live_ids):
            if show_id in announced:
                continue
            show_url = f"https://www.whatnot.com/live/{show_id}"
            post_discord(f"🔴 **{user}** has just gone live!\n{show_url}")
            print(f"[{user}] Announced {show_url}")
            announced.append(show_id)
            changed = True

        state[user] = announced[-25:]  # keep the file small

    if changed or not os.path.exists(STATE_FILE):
        save_state(state)


if __name__ == "__main__":
    main()

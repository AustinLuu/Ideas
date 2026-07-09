"""
main.py — entrypoint for the build-ideas Discord bot.

Two run modes, controlled by the RUN_MODE env var:

  RUN_MODE=once (default) — fetch sources, generate ideas, post, exit.
    Use this with an external scheduler that starts the process fresh each
    time — e.g. a GitHub Actions cron workflow. Cheapest option: nothing
    runs between posts.

  RUN_MODE=loop — start once and stay running, firing on an internal
    schedule (SCHEDULE_FREQUENCY / SCHEDULE_TIME / SCHEDULE_DAY).
    Use this on an always-on host like Railway or Fly.io.
"""

from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv

from discord_post import post_ideas
from idea_generator import generate_ideas
from sources import get_hn_signals, get_trending_github_repos

load_dotenv()


def run_job() -> None:
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
    num_ideas = int(os.getenv("NUM_IDEAS", "3"))
    trending_days = int(os.getenv("TRENDING_WINDOW_DAYS", "2"))
    language = os.getenv("GITHUB_LANGUAGE") or None

    print("[main] fetching trending signals...")
    github_repos = get_trending_github_repos(days=trending_days, language=language)
    hn_signals = get_hn_signals()
    print(f"[main] got {len(github_repos)} GitHub repos, {len(hn_signals)} HN stories")

    print("[main] generating ideas...")
    ideas = generate_ideas(github_repos, hn_signals, num_ideas=num_ideas)
    print(f"[main] generated {len(ideas)} ideas")

    print("[main] posting to Discord...")
    post_ideas(ideas, webhook_url)
    print("[main] done")


def run_loop() -> None:
    import schedule

    frequency = os.getenv("SCHEDULE_FREQUENCY", "daily")  # "daily" or "weekly"
    at_time = os.getenv("SCHEDULE_TIME", "09:00")  # 24h UTC, e.g. "09:00"
    day = os.getenv("SCHEDULE_DAY", "monday").lower()  # only used if weekly

    if frequency == "weekly":
        getattr(schedule.every(), day).at(at_time).do(run_job)
        print(f"[main] scheduled weekly on {day} at {at_time} UTC")
    else:
        schedule.every().day.at(at_time).do(run_job)
        print(f"[main] scheduled daily at {at_time} UTC")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    mode = os.getenv("RUN_MODE", "once")
    try:
        if mode == "loop":
            run_loop()
        else:
            run_job()
    except KeyError as e:
        print(f"[main] missing required environment variable: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 - top-level guard for a scheduled job
        print(f"[main] job failed: {e}", file=sys.stderr)
        sys.exit(1)

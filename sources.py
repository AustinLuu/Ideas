"""
sources.py — pulls "what's trending" signals from official, key-free APIs.

- GitHub: uses the public Search API (no scraping) to find repos created
  recently that are already gaining stars. This is a decent proxy for
  "trending" and is far more stable than scraping github.com/trending.
- Hacker News: uses the official Firebase API to pull top stories,
  weighted toward "Show HN" posts since those tend to be small, buildable
  projects rather than pure news.
"""

from __future__ import annotations

import datetime
import os
from typing import Any

import requests

GITHUB_API = "https://api.github.com/search/repositories"
HN_API = "https://hacker-news.firebaseio.com/v0"
REQUEST_TIMEOUT = 10


def get_trending_github_repos(
    days: int = 2, limit: int = 8, language: str | None = None
) -> list[dict[str, Any]]:
    """Repos created in the last `days` days, sorted by stars.

    Uses the official GitHub REST Search API — no scraping, no auth required
    (though setting GITHUB_TOKEN in the environment raises the rate limit
    from 60/hr to 5000/hr, which helps if this runs on a schedule).
    """
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    query = f"created:>{since}"
    if language:
        query += f" language:{language}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "build-ideas-bot",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(
            GITHUB_API,
            params={"q": query, "sort": "stars", "order": "desc", "per_page": limit},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except requests.RequestException as e:
        print(f"[sources] GitHub fetch failed, continuing without it: {e}")
        return []

    return [
        {
            "name": item.get("full_name"),
            "url": item.get("html_url"),
            "description": item.get("description") or "",
            "language": item.get("language") or "",
            "stars": item.get("stargazers_count", 0),
        }
        for item in items
    ]


def get_hn_signals(limit: int = 6) -> list[dict[str, Any]]:
    """Top Hacker News stories right now, official Firebase API."""
    try:
        resp = requests.get(f"{HN_API}/topstories.json", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        story_ids = resp.json()[:40]  # scan a bit deeper than `limit` to allow filtering
    except requests.RequestException as e:
        print(f"[sources] HN fetch failed, continuing without it: {e}")
        return []

    stories = []
    for story_id in story_ids:
        if len(stories) >= limit:
            break
        try:
            item_resp = requests.get(
                f"{HN_API}/item/{story_id}.json", timeout=REQUEST_TIMEOUT
            )
            item_resp.raise_for_status()
            item = item_resp.json() or {}
        except requests.RequestException:
            continue

        if item.get("type") != "story" or not item.get("title"):
            continue

        stories.append(
            {
                "title": item["title"],
                "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                "points": item.get("score", 0),
                "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
            }
        )

    return stories

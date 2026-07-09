"""
discord_post.py — formats ideas into a Discord embed and posts via webhook.

Uses a Discord webhook rather than a full bot connection: no gateway, no
bot token, no invite flow — just an HTTP POST. Set one up via
Server Settings -> Integrations -> Webhooks -> New Webhook.
"""

from __future__ import annotations

import datetime
from typing import Any

import requests

EMBED_COLOR = 0x5865F2  # Discord blurple
FIELD_VALUE_LIMIT = 1024


def _format_field_value(idea: dict[str, str]) -> str:
    value = (
        f"{idea.get('pitch', '').strip()}\n\n"
        f"**Stack:** {idea.get('stack', '?')}\n"
        f"**Scope:** {idea.get('scope', '?')}\n"
        f"**Inspired by:** {idea.get('spark', 'original idea')}"
    )
    if len(value) > FIELD_VALUE_LIMIT:
        value = value[: FIELD_VALUE_LIMIT - 3] + "..."
    return value


def post_ideas(ideas: list[dict[str, str]], webhook_url: str) -> None:
    today = datetime.date.today().strftime("%b %d, %Y")

    fields = [
        {
            "name": f"💡 {idea.get('title', 'Untitled idea')}",
            "value": _format_field_value(idea),
            "inline": False,
        }
        for idea in ideas
    ]

    payload = {
        "embeds": [
            {
                "title": f"🔧 Build ideas for {today}",
                "description": "Scoped for an evening or two with Claude Code.",
                "color": EMBED_COLOR,
                "fields": fields,
                "footer": {"text": "Seeded from GitHub + Hacker News trends"},
            }
        ]
    }

    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()

"""
idea_generator.py — turns trending signals into small, scoped build ideas
sized for "an evening or two" with Claude Code, via the Anthropic API.
"""

from __future__ import annotations

import json
import os
from typing import Any

from anthropic import Anthropic

DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """You help a developer pick small, satisfying side projects.
You will be given a snapshot of currently trending GitHub repos and Hacker News
stories. Generate project ideas that:

- Can realistically be built in ONE OR TWO EVENINGS by one person using
  Claude Code (an agentic coding CLI) — not a weekend, not a "real product."
- Are concrete and scoped, not vague ("a tool that helps with X" is bad;
  "a CLI that diffs two JSON API responses and highlights schema drift" is good).
- Are genuinely interesting or a little fun, not generic CRUD apps.
- Where relevant, are loosely inspired by one of the trending items given —
  but don't force a connection that isn't there; an original idea is fine too.

Respond with ONLY a raw JSON array (no markdown fences, no commentary) where
each element has exactly these keys:
  "title": short punchy project name (string)
  "pitch": 2-3 sentence description of what it does (string)
  "stack": suggested language/framework, e.g. "Python + SQLite" (string)
  "scope": one short sentence on why it fits in an evening or two (string)
  "spark": which trending repo or HN story it riffs on, or "original idea" (string)
"""


def _format_sources(github_repos: list[dict[str, Any]], hn_signals: list[dict[str, Any]]) -> str:
    lines = ["## Trending GitHub repos (recently created, gaining stars)"]
    if github_repos:
        for repo in github_repos:
            lines.append(
                f"- {repo['name']} ({repo['language'] or 'unknown lang'}, "
                f"{repo['stars']}★): {repo['description']}"
            )
    else:
        lines.append("(none available right now)")

    lines.append("\n## Hacker News top stories")
    if hn_signals:
        for story in hn_signals:
            lines.append(f"- {story['title']} ({story['points']} points)")
    else:
        lines.append("(none available right now)")

    return "\n".join(lines)


def generate_ideas(
    github_repos: list[dict[str, Any]],
    hn_signals: list[dict[str, Any]],
    num_ideas: int = 3,
    model: str = DEFAULT_MODEL,
) -> list[dict[str, str]]:
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    user_prompt = (
        f"{_format_sources(github_repos, hn_signals)}\n\n"
        f"Generate exactly {num_ideas} project ideas as a JSON array, per the rules above."
    )

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = "".join(block.text for block in response.content if block.type == "text").strip()

    # Defensive cleanup in case the model wraps output in a code fence anyway.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        ideas = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Could not parse idea list as JSON: {e}\nRaw response:\n{text}") from e

    if not isinstance(ideas, list):
        raise RuntimeError(f"Expected a JSON array of ideas, got: {type(ideas)}")

    return ideas

# build-ideas-bot

A scheduled Discord post of small project ideas, sized for an evening or
two with Claude Code. It looks at what's currently trending on GitHub and
Hacker News, feeds that to Claude, and posts a few scoped ideas to a
channel.

No full bot connection required — it uses a Discord **webhook**, so there's
no gateway, no bot token, no invite/permissions flow. Just an HTTP POST.

## 1. Create a Discord webhook

In your server: **Server Settings → Integrations → Webhooks → New Webhook**.
Pick the channel, copy the webhook URL. That's your `DISCORD_WEBHOOK_URL`.

## 2. Get an Anthropic API key

From [console.anthropic.com](https://console.anthropic.com) → API Keys.
That's your `ANTHROPIC_API_KEY`.

## 3. Local setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and fill in DISCORD_WEBHOOK_URL and ANTHROPIC_API_KEY
python main.py   # runs once immediately, posts to your channel
```

If that posts a message with a few ideas, you're set.

## 4. Deploy — recommended: GitHub Actions (actually free)

This bot only needs to run for a few seconds, once a day. That's a perfect
fit for a GitHub Actions scheduled workflow, which costs nothing: unlimited
on public repos, and 2,000 free minutes/month on private ones (this job
uses well under a minute per run).

1. Push this folder to a GitHub repo (private is fine).
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**.
   Add `DISCORD_WEBHOOK_URL` and `ANTHROPIC_API_KEY`.
3. The workflow at `.github/workflows/daily-ideas.yml` is already wired up
   and runs daily at 13:00 UTC. Edit the cron line to change the time, or
   add a day (`0 13 * * 1` = Mondays only) for weekly instead of daily.
4. You can also trigger it manually any time from the repo's **Actions** tab
   (the `workflow_dispatch` trigger).

No server, no uptime to babysit, no bill.

## 5. Deploy — alternative: Railway / Fly.io (persistent worker)

Worth knowing going in: Railway's free option in 2026 is a one-time 30-day
$5 trial, after which it's a $5/month minimum (Hobby plan) or a very
limited $1/month credit tier — it's no longer indefinitely free. Fly.io has
a similar shift toward usage-based billing. For a job this light, GitHub
Actions above will cost you nothing; use this path if you'd rather have a
persistent process/dashboard than a cron workflow.

1. Push this repo, connect it in Railway/Fly as a new project.
2. Set env vars: `DISCORD_WEBHOOK_URL`, `ANTHROPIC_API_KEY`, and importantly
   `RUN_MODE=loop` (this makes it run continuously instead of once-and-exit).
3. It'll use the `Procfile` (`worker: python main.py`) to start.
4. Adjust `SCHEDULE_FREQUENCY` (`daily`/`weekly`), `SCHEDULE_TIME` (24h UTC),
   and `SCHEDULE_DAY` (for weekly) env vars to taste.

## Customizing

All in `.env` / your host's env vars:

| Variable | Default | What it does |
|---|---|---|
| `NUM_IDEAS` | `3` | Ideas per post |
| `TRENDING_WINDOW_DAYS` | `2` | How recent a GitHub repo must be to count as "trending" |
| `GITHUB_LANGUAGE` | (any) | Filter GitHub trending to one language, e.g. `python` |
| `CLAUDE_MODEL` | `claude-sonnet-5` | Swap to `claude-haiku-4-5-20251001` for a cheaper/faster run |
| `GITHUB_TOKEN` | (none) | Optional PAT, raises GitHub API rate limit from 60/hr to 5000/hr |

## How it works

- `sources.py` — pulls recently-created, star-gaining repos from the
  official GitHub Search API, and top stories from the official Hacker
  News Firebase API. No scraping.
- `idea_generator.py` — sends that snapshot to Claude, asking for N scoped,
  buildable-in-an-evening ideas back as JSON.
- `discord_post.py` — formats those into a Discord embed and posts it via
  the webhook.
- `main.py` — orchestrates the above. Runs once and exits by default
  (`RUN_MODE=once`, for external schedulers like GitHub Actions), or loops
  with its own internal schedule (`RUN_MODE=loop`, for always-on hosts).

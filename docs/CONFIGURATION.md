# 🧰 Configuration & collectors

## Environment variables


All settings are configured via environment variables (`.env` file).

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_MODEL_SCREEN` | Model for screening | `haiku` |
| `CLAUDE_MODEL_DEEP` | Model for deep analysis | `opus` |
| `SCORE_WEIGHT_ROI` | ROI weight in final score | `0.4` |
| `SCORE_WEIGHT_FEASIBILITY` | Feasibility weight | `0.35` |
| `SCORE_WEIGHT_COMPLEXITY` | Complexity weight | `0.25` |
| `ALERT_SCORE_THRESHOLD` | Min score for Telegram alert | `7.0` |
| `REDDIT_CLIENT_ID` | Reddit API client ID (optional) | `""` |
| `REDDIT_CLIENT_SECRET` | Reddit API client secret (optional) | `""` |
| `REDDIT_USER_AGENT` | Reddit API user agent | `alpha-scout/1.0` |
| `REDDIT_SUBREDDITS` | Subreddits to monitor (JSON list) | `["algotrading", ...]` |
| `REDDIT_INTERVAL_MIN` | Collection interval (minutes) | `15` |
| `GITHUB_TOKEN` | GitHub token (optional, increases rate limit) | `""` |
| `GITHUB_KEYWORDS` | Search keywords (JSON list) | `["trading bot", ...]` |
| `GITHUB_INTERVAL_MIN` | Collection interval (minutes) | `120` |
| `POLYMARKET_GAMMA_API_URL` | Polymarket Gamma API URL | `https://gamma-api.polymarket.com` |
| `POLYMARKET_VOLUME_SPIKE_PCT` | Volume spike threshold (%) | `200.0` |
| `POLYMARKET_INTERVAL_MIN` | Collection interval (minutes) | `15` |
| `HACKERNEWS_KEYWORDS` | HN filter keywords (JSON list) | `["crypto", "trading", ...]` |
| `HACKERNEWS_INTERVAL_MIN` | Collection interval (minutes) | `60` |
| `RSS_FEEDS` | RSS feed URLs (JSON list) | `["https://coindesk...", ...]` |
| `RSS_INTERVAL_MIN` | Collection interval (minutes) | `60` |
| `TWITTER_USERNAME` | Twitter/X username | `""` |
| `TWITTER_EMAIL` | Twitter/X email | `""` |
| `TWITTER_PASSWORD` | Twitter/X password | `""` |
| `TWITTER_COOKIES_FILE` | Path to cookies file | `data/twitter_cookies.json` |
| `TWITTER_KEYWORDS` | Search keywords (JSON list) | `["polymarket strategy", ...]` |
| `TWITTER_INTERVAL_MIN` | Collection interval (minutes) | `30` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | `""` |
| `TELEGRAM_CHAT_IDS` | Chat IDs for alerts (JSON list) | `[]` |
| `NEWS_INTELLIGENCE_URL` | News Intelligence API URL (optional) | `""` |
| `SCOUT_URL` | Public URL for dashboard links in Telegram | `http://localhost:8900` |
| `WEB_HOST` | Dashboard bind host | `0.0.0.0` |
| `WEB_PORT` | Dashboard port | `8900` |
| `DATA_DIR` | Data directory | `data` |

## Collector behaviour

- Collection runs on each source's configured interval, rather than as a real-time firehose.
- Reddit, GitHub, Hacker News, Polymarket and RSS have separate collectors. Available results depend on source access, credentials and rate limits.
- The X collector uses `twikit` with session cookies, with optional Camoufox login. It is not the official X API. Its Google News RSS fallback returns news articles, not direct X posts; the dashboard reports the collection method.
- Claude Code CLI performs screening and deeper analysis. Run it under an account with working authentication.
- Configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_IDS` to enable alerts. Set `SCOUT_URL` to the dashboard address used in Telegram links.

## Run modes

```bash
python main.py --web       # dashboard and recurring collection
python main.py --collect   # one collection cycle with analysis, when available
python main.py --analyze   # analyze stored ideas that lack a score
```

## Docker

```bash
docker compose up -d
```

The included Compose file exposes the dashboard at `http://localhost:8878` and mounts the host's Claude credentials file read-only into the container. Check the path in `docker-compose.yml` for your installation. Persistent data and logs use named volumes.

The dashboard has no application-level sign-in. For remote access, use an authenticated reverse proxy or private network.

## Storage & extension

Ideas and collection state are stored under `DATA_DIR` as JSON files. Collectors live in `collectors/`; the analyzer, Telegram notifier and web dashboard are separate modules. Defaults are defined in `config.py`.

# Alpha Scout

AI-powered trading idea aggregator. Collects signals from 6 sources, screens with Claude AI, delivers high-score ideas via Telegram.

## How It Works

```
Reddit/GitHub/HN/Twitter/Polymarket/RSS
        |
   Collectors (async, scheduled)
        |
   Deduplication (content hash)
        |
   Screening (Claude Haiku -- fast classify)
        |
   Deep Analysis (Claude Opus -- detailed scoring)
        |
   Score >= 7.0 --> Telegram Alert
```

## Data Sources

| Source | Interval | What |
|--------|----------|------|
| Reddit | 15 min | Posts from algotrading, polymarket, crypto, defi, ethfinance |
| GitHub | 2 hours | Trending repos by keywords |
| Hacker News | 1 hour | Top stories on crypto/trading |
| Twitter/X | 30 min | Tweets on polymarket, crypto alpha, MEV |
| Polymarket | 15 min | Volume spikes (>200% normal) |
| RSS | 1 hour | CoinDesk, TheBlock |

## AI Pipeline

1. **Collect** -- async collectors gather items from all sources
2. **Deduplicate** -- skip already processed items (content hash)
3. **Screen** (Haiku) -- classify: strategy / tool / niche / news / irrelevant
4. **Deep Analysis** (Opus) -- detailed scoring of promising ideas
5. **Score** -- ROI (40%) + Feasibility (35%) + Complexity (25%)
6. **Alert** -- ideas with score >= 7.0 sent as Telegram notification

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.12, asyncio |
| AI | Claude CLI (Haiku screening + Opus analysis) |
| Web | FastAPI + Jinja2 dashboard |
| Twitter | twikit (no API key needed) |
| Notifications | Telegram Bot API |
| Storage | JSON file storage |
| Deploy | Docker, Docker Compose |

## Quick Start

### Prerequisites

- Python 3.12+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- Telegram Bot (via [@BotFather](https://t.me/BotFather))

### Installation

```bash
# Clone
git clone https://github.com/mazamaka/alpha-scout.git
cd alpha-scout

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run with Docker
docker compose up -d

# Or run locally
pip install -r requirements.txt
python main.py --web
```

## Configuration

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

## Dashboard

```
http://localhost:8900
```

## API

| Endpoint | Description |
|----------|------------|
| `GET /` | Web dashboard |
| `GET /api/ideas` | List ideas (with filters) |
| `GET /api/stats` | Statistics |
| `GET /api/collectors` | Collector status |

## Telegram Bot Commands

| Command | Description |
|---------|------------|
| `/start` | Welcome + status |
| `/ideas` | Latest high-score ideas |
| `/ideas <keyword>` | Filter ideas by keyword |
| `/trending` | Current trending categories |
| `/stats` | Collection statistics |

## Project Structure

```
alpha-scout/
├── main.py                  # Entry point
├── config.py                # Pydantic settings
├── collectors/
│   ├── reddit.py            # Reddit collector
│   ├── github.py            # GitHub trending repos
│   ├── hackernews.py        # Hacker News
│   ├── twitter.py           # Twitter/X via twikit
│   ├── twitter_login.py     # Twitter auth helper
│   ├── polymarket.py        # Polymarket volume spikes
│   └── rss.py               # CoinDesk, TheBlock RSS
├── analyzer/
│   ├── claude.py            # Claude CLI screening + deep analysis
│   ├── prompts.py           # Prompts for Claude
│   └── scorer.py            # Idea scoring (ROI, feasibility, complexity)
├── storage/
│   ├── db.py                # JSON file storage
│   └── models.py            # Data models (Pydantic)
├── notifier/
│   └── telegram_bot.py      # Telegram notifications
└── web/
    └── app.py               # FastAPI dashboard
```

## Disclaimer

This project is for educational and research purposes only. Not financial advice. Use at your own risk.

## License

[MIT](LICENSE)

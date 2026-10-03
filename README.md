# 🔭 Alpha Scout

**Collect trading and market-research ideas, filter them with an LLM, and send the useful ones to Telegram.**

Sources → deduplication → screening → deeper analysis → scored ideas and alerts.

## ⚡ What it does

- 🗞️ **Source collection** — Reddit, GitHub, Hacker News, Polymarket, RSS and an X collector with a news fallback.
- 🧠 **Two-stage analysis** — a screening pass followed by deeper evaluation through Claude Code CLI.
- 🎯 **Configurable scoring** — weights and alert thresholds for reviewing collected ideas.
- 💬 **Telegram alerts** — send high-scoring results to configured chats.
- 🖥️ **Web dashboard** — browse ideas and inspect collector status.

## 🔧 Built for a complete workflow

- **Async collection loops** with separate schedules for each source.
- **Content-hash deduplication** and JSON storage for collected ideas.
- **Separate collectors, analyzer and notifier**, with settings managed through environment variables.
- **Local or Docker deployment**, with persistent data and logs.

Collection is **scheduled, not real-time**. Source access can fail independently. The X integration uses session-based access rather than the official API; its fallback is labelled in the dashboard. See **[collector details](docs/CONFIGURATION.md#collector-behaviour)**.

## 🚀 Quick start

Requires **Python 3.12+** and an installed, authenticated **Claude Code CLI**.

```bash
git clone https://github.com/mazamaka/alpha-scout.git
cd alpha-scout
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with the sources and credentials you want to use. For alerts, set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_IDS`.

```bash
WEB_HOST=127.0.0.1 python main.py --web
```

Open **http://localhost:8900**. For Docker setup, collector intervals and scoring options, see **[Configuration →](docs/CONFIGURATION.md)**.

## 🧪 Project scope

The repository contains the collection-to-alert pipeline. It does not execute trades, and an LLM score is a research filter rather than a measured investment return.

---

**Python · asyncio · Claude Code CLI · FastAPI · Jinja2 · Telegram**

**[MIT license](LICENSE)** · Built by **[Maksym Babenko](https://github.com/mazamaka)**.

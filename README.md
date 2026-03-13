# Alpha Scout

Сервис сбора и AI-анализа торговых идей из множества источников. Использует Claude AI для скрининга и deep analysis.

## Архитектура

```
alpha-scout/
├── main.py                  # Entry point
├── config.py                # Pydantic settings
├── collectors/
│   ├── reddit.py            # Reddit (algotrading, polymarket, crypto, defi)
│   ├── github.py            # GitHub trending repos
│   ├── hackernews.py        # Hacker News
│   ├── twitter.py           # Twitter/X через twikit
│   ├── twitter_login.py     # Twitter auth
│   ├── polymarket.py        # Polymarket volume spikes
│   └── rss.py               # CoinDesk, TheBlock RSS
├── analyzer/
│   ├── claude.py            # Claude CLI — screening + deep analysis
│   ├── prompts.py           # Промпты для Claude
│   └── scorer.py            # Скоринг идей (ROI, feasibility, complexity)
├── storage/
│   ├── db.py                # SQLite storage
│   └── models.py            # Data models
├── notifier/
│   └── telegram_bot.py      # Telegram уведомления
└── web/
    └── app.py               # FastAPI dashboard
```

## Стек

- **Python 3.12** + FastAPI + Uvicorn
- **Claude CLI** — AI-скрининг (haiku) + deep analysis (opus)
- **twikit** — Twitter/X scraping без API
- **SQLite** — хранилище идей
- **Telegram Bot API** — уведомления

## Источники данных

| Источник | Интервал | Что собирает |
|----------|----------|-------------|
| Reddit | 15 мин | Посты из algotrading, polymarket, crypto, defi, ethfinance |
| GitHub | 2 часа | Trending repos по ключевым словам |
| Hacker News | 1 час | Top stories по крипто/трейдинг темам |
| Twitter/X | 30 мин | Твиты по polymarket strategy, crypto alpha, MEV и др. |
| Polymarket | 15 мин | Volume spikes (>200% от нормы) |
| RSS | 1 час | CoinDesk, TheBlock |

## AI Pipeline

1. **Сбор** — коллекторы собирают items из всех источников
2. **Дедупликация** — пропуск уже обработанных items
3. **Screening** (haiku) — быстрая классификация: strategy/tool/niche/news/irrelevant
4. **Deep Analysis** (opus) — детальный анализ перспективных идей
5. **Скоринг** — ROI (40%) + Feasibility (35%) + Complexity (25%)
6. **Алерт** — идеи с score ≥ 7.0 → Telegram уведомление

## Конфигурация

Через `.env`:

| Переменная | Описание |
|------------|----------|
| `TWITTER_USERNAME` | Twitter/X логин |
| `TWITTER_EMAIL` | Twitter/X email |
| `TWITTER_PASSWORD` | Twitter/X пароль |

Claude credentials монтируются через Docker volume: `~/.claude/.credentials.json`

## Запуск

```bash
# Docker
docker compose up -d

# Локально
python main.py --web
```

**Dashboard:** http://localhost:8900 | **Prod:** https://scout.maxbob.xyz

## API

| Endpoint | Описание |
|----------|----------|
| `GET /` | Web dashboard |
| `GET /api/ideas` | Список идей (limit, filters) |
| `GET /api/stats` | Статистика (всего, проанализировано, средний score) |
| `GET /api/collectors` | Статус коллекторов |

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Claude CLI
    claude_model_screen: str = "haiku"
    claude_model_deep: str = "opus"

    # Scoring
    score_weight_roi: float = 0.4
    score_weight_feasibility: float = 0.35
    score_weight_complexity: float = 0.25
    alert_score_threshold: float = 7.0

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "alpha-scout/1.0"
    reddit_subreddits: list[str] = [
        "algotrading",
        "polymarket",
        "cryptocurrency",
        "defi",
        "ethfinance",
    ]
    reddit_interval_min: int = 15

    # GitHub
    github_token: str = ""
    github_keywords: list[str] = [
        "trading bot",
        "polymarket",
        "defi bot",
        "mev bot",
        "prediction market",
        "crypto arbitrage",
    ]
    github_interval_min: int = 120

    # Polymarket
    polymarket_gamma_api_url: str = "https://gamma-api.polymarket.com"
    polymarket_volume_spike_pct: float = 200.0
    polymarket_interval_min: int = 15

    # Hacker News
    hackernews_keywords: list[str] = [
        "crypto",
        "trading",
        "defi",
        "prediction market",
        "polymarket",
        "arbitrage",
        "MEV",
        "bitcoin",
        "ethereum",
        "trading bot",
    ]
    hackernews_interval_min: int = 60

    # RSS
    rss_feeds: list[str] = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://www.theblock.co/rss.xml",
    ]
    rss_interval_min: int = 60

    # Twitter / X (twikit login)
    twitter_username: str = ""
    twitter_email: str = ""
    twitter_password: str = ""
    twitter_cookies_file: str = "data/twitter_cookies.json"
    twitter_keywords: list[str] = [
        "polymarket strategy",
        "prediction market alpha",
        "trading bot",
        "MEV",
        "airdrop strategy",
        "crypto alpha",
    ]
    twitter_interval_min: int = 30

    # Telegram bot (notifications)
    telegram_bot_token: str = ""
    telegram_chat_ids: list[int] = []

    # News Intelligence (optional, for enriched analysis)
    news_intelligence_url: str = ""

    # Scout URL (for Telegram bot links)
    scout_url: str = "http://localhost:8900"

    # Web dashboard
    web_host: str = "0.0.0.0"
    web_port: int = 8900

    # Storage
    data_dir: str = "data"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

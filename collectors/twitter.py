"""Twitter/X collector: twikit (cookies from Camoufox login) + Google News RSS fallback."""

import json
import logging
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import httpx

from config import settings
from storage.models import RawItem, SourceType

logger = logging.getLogger(__name__)

MAX_CONTENT_LEN = 2000
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


async def _load_twikit_client() -> "twikit.Client | None":
    """Load twikit client with cookies from Camoufox login."""
    try:
        import twikit
    except ImportError:
        logger.warning("twikit not installed, skipping Twitter API")
        return None

    cookies_path = Path(settings.twitter_cookies_file)
    if not cookies_path.exists():
        logger.info("No Twitter cookies file, will try Camoufox login")
        return None

    try:
        cookies = json.loads(cookies_path.read_text(encoding="utf-8"))
        if "auth_token" not in cookies or "ct0" not in cookies:
            logger.warning("Twitter cookies missing auth_token/ct0")
            return None

        client = twikit.Client(language="en")
        client.set_cookies(cookies)
        logger.info("Twitter: twikit loaded %d cookies from file", len(cookies))
        return client

    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Error loading Twitter cookies: %s", exc)
        return None


async def _try_camoufox_login() -> "twikit.Client | None":
    """Try to re-login via Camoufox and return twikit client."""
    if not settings.twitter_username or not settings.twitter_password:
        return None

    try:
        from collectors.twitter_login import ensure_valid_cookies
    except ImportError:
        logger.warning("twitter_login module not available (camoufox not installed?)")
        return None

    success = await ensure_valid_cookies()
    if success:
        return await _load_twikit_client()
    return None


async def _collect_twikit() -> list[RawItem]:
    """Собрать твиты через twikit (cookies from Camoufox)."""
    # Try loading existing cookies
    client = await _load_twikit_client()

    # If no valid cookies, try Camoufox login
    if not client:
        client = await _try_camoufox_login()

    if not client:
        return []

    items: list[RawItem] = []
    seen_ids: set[str] = set()

    try:
        for keyword in settings.twitter_keywords:
            results = None
            for product in ("Latest", "Top"):
                try:
                    results = await client.search_tweet(
                        keyword, product=product, count=20
                    )
                    break
                except Exception as exc:
                    logger.debug(
                        "Twitter search '%s' (%s) failed: %s", keyword, product, exc
                    )
            if not results:
                logger.warning("Twitter search '%s' failed on all products", keyword)
                continue

            for tweet in results:
                if tweet.id in seen_ids:
                    continue
                seen_ids.add(tweet.id)

                text = tweet.text or ""
                screen_name = tweet.user.screen_name if tweet.user else ""

                items.append(
                    RawItem(
                        source=SourceType.TWITTER,
                        url=f"https://x.com/{screen_name}/status/{tweet.id}",
                        title=text[:150],
                        content=text[:MAX_CONTENT_LEN],
                        author=f"@{screen_name}",
                        score=tweet.favorite_count or 0,
                        metadata={
                            "keyword": keyword,
                            "retweet_count": tweet.retweet_count or 0,
                            "reply_count": tweet.reply_count or 0,
                            "method": "twikit",
                        },
                    ),
                )

        logger.info("Twitter (twikit): collected %d tweets", len(items))
        return items
    except Exception as exc:
        logger.error("Twitter twikit collector failed: %s", exc)
        return []


async def _collect_google_news() -> list[RawItem]:
    """Fallback: Google News RSS по trading keywords."""
    items: list[RawItem] = []
    seen_urls: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for keyword in settings.twitter_keywords:
                url = f"{GOOGLE_NEWS_RSS}?q={quote_plus(keyword)}&hl=en-US&gl=US&ceid=US:en"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                except httpx.HTTPError:
                    continue

                feed = feedparser.parse(resp.text)
                for entry in feed.entries[:15]:
                    entry_url = entry.get("link", "")
                    if not entry_url or entry_url in seen_urls:
                        continue
                    seen_urls.add(entry_url)

                    title = entry.get("title", "")
                    summary = entry.get("summary", "")[:MAX_CONTENT_LEN]
                    source_name = entry.get("source", {})
                    if isinstance(source_name, dict):
                        source_name = source_name.get("title", "")

                    items.append(
                        RawItem(
                            source=SourceType.RSS,
                            url=entry_url,
                            title=title,
                            content=summary or title,
                            author=str(source_name),
                            metadata={
                                "keyword": keyword,
                                "published": entry.get("published", ""),
                                "method": "google_news_rss",
                            },
                        ),
                    )

        logger.info("Twitter/News (Google RSS): collected %d items", len(items))
        return items
    except httpx.HTTPError as exc:
        logger.error("Google News RSS failed: %s", exc)
        return []


# Track collection method for UI status
last_method: str = ""
last_warning: str = ""


async def collect() -> list[RawItem]:
    """Собрать контент: twikit (Camoufox cookies) -> Google News RSS fallback."""
    global last_method, last_warning

    if not settings.twitter_keywords:
        logger.warning("Twitter keywords not configured, skipping")
        return []

    # Попробовать twikit сначала
    items = await _collect_twikit()

    if items:
        last_method = "twikit"
        last_warning = ""
    else:
        # Fallback на Google News RSS
        items = await _collect_google_news()
        last_method = "google_news_rss"
        cookies_path = Path(settings.twitter_cookies_file)
        if not cookies_path.exists():
            last_warning = "Cookies missing — upload cookies to enable real tweets"
        else:
            last_warning = "twikit failed (rate limit?) — using Google News fallback"
        logger.warning("Twitter: %s", last_warning)

    return items

import logging

import feedparser
import httpx

from config import settings
from storage.models import RawItem, SourceType

logger = logging.getLogger(__name__)

MAX_CONTENT_LEN = 2000


async def collect() -> list[RawItem]:
    """Собрать записи из RSS-фидов."""
    if not settings.rss_feeds:
        logger.warning("RSS feeds not configured, skipping")
        return []

    items: list[RawItem] = []
    seen_urls: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for feed_url in settings.rss_feeds:
                try:
                    resp = await client.get(feed_url)
                    if resp.status_code != 200:
                        logger.warning(
                            "RSS feed %s returned %d", feed_url, resp.status_code
                        )
                        continue
                except httpx.HTTPError as exc:
                    logger.warning("RSS feed %s failed: %s", feed_url, exc)
                    continue

                feed = feedparser.parse(resp.text)

                for entry in feed.entries:
                    url = entry.get("link", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    content_detail = entry.get("content", [{}])
                    body = ""
                    if content_detail and isinstance(content_detail, list):
                        body = content_detail[0].get("value", "")

                    content = (body or summary)[:MAX_CONTENT_LEN]

                    author = entry.get("author", "")
                    published = entry.get("published", "")

                    items.append(
                        RawItem(
                            source=SourceType.RSS,
                            url=url,
                            title=title,
                            content=content,
                            author=author,
                            metadata={
                                "feed_url": feed_url,
                                "feed_title": feed.feed.get("title", ""),
                                "published": published,
                                "tags": [
                                    t.get("term", "") for t in entry.get("tags", [])
                                ],
                            },
                        ),
                    )

        logger.info("RSS: collected %d items", len(items))
        return items
    except httpx.HTTPError as exc:
        logger.error("RSS collector failed: %s", exc)
        return []

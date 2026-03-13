import logging
from datetime import datetime, timedelta

import httpx

from config import settings
from storage.models import RawItem, SourceType

logger = logging.getLogger(__name__)

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
MAX_CONTENT_LEN = 2000


async def collect() -> list[RawItem]:
    """Собрать топ историй с Hacker News по ключевым словам."""
    keywords = settings.hackernews_keywords
    if not keywords:
        logger.warning("HackerNews keywords not configured, skipping")
        return []

    one_day_ago = int((datetime.utcnow() - timedelta(hours=24)).timestamp())
    items: list[RawItem] = []
    seen_ids: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            for tag in keywords:
                resp = await client.get(
                    HN_SEARCH_URL,
                    params={
                        "query": tag,
                        "tags": "story",
                        "numericFilters": f"created_at_i>{one_day_ago}",
                        "hitsPerPage": 20,
                    },
                )
                if resp.status_code != 200:
                    logger.warning(
                        "HN search '%s' returned %d",
                        tag,
                        resp.status_code,
                    )
                    continue

                hits = resp.json().get("hits", [])
                for hit in hits:
                    object_id = hit.get("objectID", "")
                    if object_id in seen_ids:
                        continue
                    seen_ids.add(object_id)

                    title = hit.get("title", "") or ""
                    story_text = hit.get("story_text", "") or ""
                    content = f"{title}\n\n{story_text}".strip()[:MAX_CONTENT_LEN]

                    url = (
                        hit.get("url", "")
                        or f"https://news.ycombinator.com/item?id={object_id}"
                    )

                    items.append(
                        RawItem(
                            source=SourceType.HACKERNEWS,
                            url=url,
                            title=title,
                            content=content,
                            author=hit.get("author", ""),
                            score=hit.get("points", 0) or 0,
                            metadata={
                                "object_id": object_id,
                                "num_comments": hit.get("num_comments", 0),
                                "created_at": hit.get("created_at", ""),
                            },
                        ),
                    )

        logger.info("HackerNews: collected %d items", len(items))
        return items
    except httpx.HTTPError as exc:
        logger.error("HackerNews collector failed: %s", exc)
        return []

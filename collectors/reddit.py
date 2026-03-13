"""Reddit collector через публичный JSON API (без OAuth, без API ключей)."""

import logging

import httpx

from config import settings
from storage.models import RawItem, SourceType

logger = logging.getLogger(__name__)

REDDIT_KEYWORDS: set[str] = {
    "trading",
    "bot",
    "strategy",
    "alpha",
    "edge",
    "arbitrage",
    "mev",
    "airdrop",
    "defi",
    "sniper",
    "automation",
    "signal",
}
MAX_CONTENT_LEN = 2000


async def collect() -> list[RawItem]:
    """Собрать посты из Reddit через публичный JSON API."""
    if not settings.reddit_subreddits:
        logger.warning("Reddit subreddits not configured, skipping")
        return []

    items: list[RawItem] = []
    seen_ids: set[str] = set()

    headers = {"User-Agent": settings.reddit_user_agent}

    try:
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True, headers=headers
        ) as client:
            for subreddit in settings.reddit_subreddits:
                for sort in ("hot", "new"):
                    await _fetch_listing(client, subreddit, sort, items, seen_ids)

        logger.info("Reddit: collected %d items", len(items))
        return items
    except httpx.HTTPError as exc:
        logger.error("Reddit collector failed: %s", exc)
        return []


async def _fetch_listing(
    client: httpx.AsyncClient,
    subreddit: str,
    sort: str,
    items: list[RawItem],
    seen_ids: set[str],
) -> None:
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    try:
        resp = await client.get(url, params={"limit": 25})
        if resp.status_code == 429:
            logger.warning("Reddit rate-limited on r/%s/%s", subreddit, sort)
            return
        if resp.status_code != 200:
            logger.warning(
                "Reddit r/%s/%s returned %d", subreddit, sort, resp.status_code
            )
            return
    except httpx.HTTPError as exc:
        logger.warning("Reddit r/%s/%s failed: %s", subreddit, sort, exc)
        return

    data = resp.json().get("data", {})
    children = data.get("children", [])

    for child in children:
        post = child.get("data", {})
        post_id = post.get("id", "")
        if not post_id or post_id in seen_ids:
            continue

        title = post.get("title", "")
        selftext = post.get("selftext", "")

        # Фильтр по ключевым словам
        text_lower = f"{title} {selftext}".lower()
        if not any(kw in text_lower for kw in REDDIT_KEYWORDS):
            continue

        seen_ids.add(post_id)
        permalink = post.get("permalink", "")
        url = f"https://www.reddit.com{permalink}" if permalink else ""

        content = f"{title}\n\n{selftext}".strip()[:MAX_CONTENT_LEN]

        items.append(
            RawItem(
                source=SourceType.REDDIT,
                url=url,
                title=title,
                content=content,
                author=post.get("author", ""),
                score=post.get("score", 0),
                metadata={
                    "subreddit": subreddit,
                    "sort": sort,
                    "num_comments": post.get("num_comments", 0),
                    "created_utc": post.get("created_utc", 0),
                    "upvote_ratio": post.get("upvote_ratio", 0),
                    "link_flair_text": post.get("link_flair_text", ""),
                },
            ),
        )

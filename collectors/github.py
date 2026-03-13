import logging
from datetime import datetime, timedelta

import httpx

from config import settings
from storage.models import RawItem, SourceType

logger = logging.getLogger(__name__)

MAX_CONTENT_LEN = 2000


async def collect() -> list[RawItem]:
    """Собрать trending репозитории с GitHub по ключевым словам."""
    if not settings.github_keywords:
        logger.warning("GitHub keywords not configured, skipping")
        return []

    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    all_items: list[RawItem] = []
    seen_urls: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            for keyword in settings.github_keywords:
                query = f"{keyword} created:>{week_ago}"
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    headers=headers,
                    params={
                        "q": query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 20,
                    },
                )
                if resp.status_code != 200:
                    logger.warning(
                        "GitHub search '%s' returned %d",
                        keyword,
                        resp.status_code,
                    )
                    continue

                repos = resp.json().get("items", [])
                for repo in repos:
                    url = repo.get("html_url", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    description = repo.get("description", "") or ""
                    content = (f"{repo.get('full_name', '')}\n\n{description}")[
                        :MAX_CONTENT_LEN
                    ]

                    all_items.append(
                        RawItem(
                            source=SourceType.GITHUB,
                            url=url,
                            title=repo.get("full_name", ""),
                            content=content,
                            author=repo.get("owner", {}).get("login", ""),
                            score=repo.get("stargazers_count", 0),
                            metadata={
                                "language": repo.get("language", ""),
                                "forks": repo.get("forks_count", 0),
                                "open_issues": repo.get("open_issues_count", 0),
                                "created_at": repo.get("created_at", ""),
                                "updated_at": repo.get("updated_at", ""),
                                "topics": repo.get("topics", []),
                            },
                        ),
                    )

        logger.info("GitHub: collected %d items", len(all_items))
        return all_items
    except httpx.HTTPError as exc:
        logger.error("GitHub collector failed: %s", exc)
        return []

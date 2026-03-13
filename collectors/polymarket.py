import logging

import httpx

from config import settings
from storage.models import RawItem, SourceType

logger = logging.getLogger(__name__)

MAX_CONTENT_LEN = 2000


async def collect() -> list[RawItem]:
    """Собрать активные рынки с Polymarket (Gamma API)."""
    base_url = settings.polymarket_gamma_api_url
    items: list[RawItem] = []

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{base_url}/events",
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": 50,
                    "order": "volume24hr",
                    "ascending": "false",
                },
            )
            if resp.status_code != 200:
                logger.warning("Polymarket API returned %d", resp.status_code)
                return []

            events = resp.json()
            if not isinstance(events, list):
                events = events.get("data", events.get("events", []))

            for event in events:
                markets = event.get("markets", [])
                if not markets:
                    continue

                for market in markets[:5]:  # max 5 markets per event
                    volume_24h = _safe_float(market.get("volume24hr", 0))
                    liquidity = _safe_float(market.get("liquidity", 0))

                    title = market.get("question", "") or event.get("title", "")
                    description = market.get("description", "") or ""
                    content = f"{title}\n\n{description}"[:MAX_CONTENT_LEN]

                    slug = market.get("slug", event.get("slug", ""))
                    url = f"https://polymarket.com/event/{slug}" if slug else ""

                    items.append(
                        RawItem(
                            source=SourceType.POLYMARKET,
                            url=url,
                            title=title,
                            content=content,
                            author="",
                            score=int(volume_24h),
                            metadata={
                                "volume_24h": volume_24h,
                                "liquidity": liquidity,
                                "outcome_prices": market.get("outcomePrices", ""),
                                "end_date": market.get("endDate", ""),
                                "event_title": event.get("title", ""),
                            },
                        ),
                    )

        logger.info("Polymarket: collected %d items", len(items))
        return items
    except httpx.HTTPError as exc:
        logger.error("Polymarket collector failed: %s", exc)
        return []


def _safe_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return 0.0

"""Alpha Scout — Entry Point.

--web      Web dashboard + scheduler (default)
--collect  One-shot data collection
--analyze  One-shot analysis of collected data
"""

import argparse
import asyncio
import logging
import logging.handlers
import sys
import threading
from pathlib import Path

from config import settings

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_handlers: list[logging.Handler] = [logging.StreamHandler()]
try:
    _handlers.append(
        logging.handlers.RotatingFileHandler(
            LOG_DIR / "scout.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
    )
except PermissionError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=_handlers,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

_notifier = None


def _get_notifier():
    """Lazy-init Telegram notifier."""
    global _notifier
    if _notifier is None and settings.telegram_bot_token:
        from notifier.telegram_bot import TelegramNotifier

        _notifier = TelegramNotifier(settings.telegram_bot_token)
        logger.info("Telegram notifier initialized")
    return _notifier


def _update_status(name: str, **kwargs: object) -> None:
    try:
        from web.app import update_collector_status

        update_collector_status(name, **kwargs)
    except ImportError:
        pass


async def _send_alerts(ideas: list) -> None:
    """Send Telegram alerts for high-score ideas."""
    notifier = _get_notifier()
    if not notifier or not settings.telegram_chat_ids:
        return

    for idea in ideas:
        if idea.ai_score and idea.final_score >= settings.alert_score_threshold:
            try:
                await notifier.send_alert(idea, settings.telegram_chat_ids)
                logger.info(
                    "Telegram alert sent: '%s' (score=%.1f)",
                    idea.title[:50],
                    idea.final_score,
                )
            except Exception as e:
                logger.warning("Telegram alert failed for '%s': %s", idea.title[:50], e)


async def run_collector_loop(
    name: str,
    collect_fn: object,
    interval_min: int,
    storage: object,
    analyzer: object,
) -> None:
    """Run a collector in a loop with the given interval."""
    while True:
        try:
            _update_status(name, status="collecting")
            logger.info("Collector [%s] starting...", name)
            items = await collect_fn()
            method = ""
            warning = ""
            if name == "twitter":
                try:
                    from collectors.twitter import last_method, last_warning

                    method = last_method
                    warning = last_warning
                except ImportError:
                    pass

            if items:
                logger.info("Collector [%s] got %d items", name, len(items))
                _update_status(
                    name,
                    status="analyzing",
                    items_count=len(items),
                    method=method,
                    warning=warning,
                )
                ideas = await analyzer.process_items(items, storage)
                await _send_alerts(ideas)
                _update_status(
                    name,
                    status="idle",
                    items_count=len(items),
                    method=method,
                    warning=warning,
                )
            else:
                logger.info("Collector [%s] got 0 items", name)
                _update_status(
                    name, status="idle", items_count=0, method=method, warning=warning
                )
        except Exception as e:
            logger.error("Collector [%s] error: %s", name, e)
            _update_status(name, status="error", error=str(e))
        await asyncio.sleep(interval_min * 60)


async def run_all_collectors(storage: object, analyzer: object) -> None:
    """Run all collectors once (--collect mode)."""
    collectors = _build_collectors()
    for name, collect_fn in collectors:
        try:
            logger.info("Collecting from [%s]...", name)
            items = await collect_fn()
            if items:
                logger.info("[%s] collected %d items", name, len(items))
                if analyzer:
                    ideas = await analyzer.process_items(items, storage)
                    await _send_alerts(ideas)
                else:
                    for item in items:
                        if not storage.is_seen(item.content_hash):
                            storage.mark_seen(item.content_hash)
                logger.info("[%s] done", name)
        except Exception as e:
            logger.error("[%s] error: %s", name, e)


def _build_collectors() -> list[tuple[str, object]]:
    """Build list of (name, async_collect_fn) pairs with lazy imports."""
    collectors: list[tuple[str, object]] = []

    try:
        from collectors.reddit import collect as reddit_collect

        collectors.append(("reddit", reddit_collect))
    except ImportError:
        logger.warning("reddit collector not available")

    try:
        from collectors.github import collect as github_collect

        collectors.append(("github", github_collect))
    except ImportError:
        logger.warning("github collector not available")

    try:
        from collectors.polymarket import collect as polymarket_collect

        collectors.append(("polymarket", polymarket_collect))
    except ImportError:
        logger.warning("polymarket collector not available")

    try:
        from collectors.hackernews import collect as hackernews_collect

        collectors.append(("hackernews", hackernews_collect))
    except ImportError:
        logger.warning("hackernews collector not available")

    try:
        from collectors.rss import collect as rss_collect

        collectors.append(("rss", rss_collect))
    except ImportError:
        logger.warning("rss collector not available")

    try:
        from collectors.twitter import collect as twitter_collect

        collectors.append(("twitter", twitter_collect))
    except ImportError:
        logger.warning("twitter collector not available")

    return collectors


def _get_interval(name: str) -> int:
    """Get collector interval from settings."""
    intervals: dict[str, int] = {
        "reddit": settings.reddit_interval_min,
        "github": settings.github_interval_min,
        "polymarket": settings.polymarket_interval_min,
        "hackernews": settings.hackernews_interval_min,
        "rss": settings.rss_interval_min,
        "twitter": settings.twitter_interval_min,
    }
    return intervals.get(name, 60)


async def run_scheduler(storage: object, analyzer: object) -> None:
    """Run all collector loops concurrently."""
    collectors = _build_collectors()
    if not collectors:
        logger.error("No collectors available, scheduler has nothing to do")
        return

    tasks = []
    for name, collect_fn in collectors:
        interval = _get_interval(name)
        logger.info("Scheduling [%s] every %d min", name, interval)
        tasks.append(
            asyncio.create_task(
                run_collector_loop(name, collect_fn, interval, storage, analyzer)
            )
        )

    # Start Telegram bot polling in background
    notifier = _get_notifier()
    if notifier and settings.telegram_chat_ids:
        logger.info("Starting Telegram bot polling...")
        tasks.append(asyncio.create_task(notifier.handle_updates(storage)))

    await asyncio.gather(*tasks)


def start_web_in_thread() -> None:
    """Start uvicorn web server in a separate thread."""
    import uvicorn

    from web.app import app

    config = uvicorn.Config(
        app,
        host=settings.web_host,
        port=settings.web_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


async def cmd_web() -> None:
    """Main mode: web dashboard + scheduler."""
    from storage.db import IdeaStorage

    storage = IdeaStorage()

    try:
        from analyzer.claude import ClaudeAnalyzer

        analyzer = ClaudeAnalyzer()
    except ImportError:
        logger.warning("ClaudeAnalyzer not available, running without analysis")
        analyzer = None

    logger.info(
        "Starting Alpha Scout: web on %s:%d",
        settings.web_host,
        settings.web_port,
    )

    web_thread = threading.Thread(target=start_web_in_thread, daemon=True)
    web_thread.start()

    if analyzer:
        await run_scheduler(storage, analyzer)
    else:
        logger.info("No analyzer — scheduler disabled, web-only mode")
        web_thread.join()


async def cmd_collect() -> None:
    """One-shot data collection from all sources."""
    from storage.db import IdeaStorage

    storage = IdeaStorage()

    try:
        from analyzer.claude import ClaudeAnalyzer

        analyzer = ClaudeAnalyzer()
    except ImportError:
        analyzer = None

    logger.info("=== ALPHA SCOUT: ONE-SHOT COLLECTION ===")
    await run_all_collectors(storage, analyzer)
    logger.info("=== COLLECTION COMPLETE ===")


async def cmd_analyze() -> None:
    """One-shot analysis of unanalyzed ideas (strategy/niche without ai_score)."""
    from analyzer.claude import ClaudeAnalyzer
    from storage.db import IdeaStorage
    from storage.models import IdeaCategory

    storage = IdeaStorage()

    try:
        analyzer = ClaudeAnalyzer()
    except ImportError:
        logger.error("ClaudeAnalyzer not available, cannot analyze")
        sys.exit(1)

    logger.info("=== ALPHA SCOUT: ONE-SHOT ANALYSIS ===")
    ideas = storage.get_ideas(limit=500)
    unanalyzed = [
        i
        for i in ideas
        if i.ai_score is None
        and i.category in {IdeaCategory.STRATEGY, IdeaCategory.NICHE}
    ]
    logger.info(
        "Found %d unanalyzed strategy/niche ideas out of %d total",
        len(unanalyzed),
        len(ideas),
    )

    if not unanalyzed:
        logger.info("Nothing to analyze")
        return

    analyzed = 0
    for idea in unanalyzed:
        try:
            ai_score = await analyzer.deep_analyze(idea)
            idea.ai_score = ai_score
            from datetime import datetime

            idea.analyzed_at = datetime.utcnow()
            idea.summary = ai_score.strategy_description
            storage.update_idea(
                idea.id,
                ai_score=ai_score,
                analyzed_at=idea.analyzed_at,
                summary=idea.summary,
            )
            analyzed += 1
            logger.info(
                "Analyzed: '%s' -> score=%.1f",
                idea.title[:50],
                idea.final_score,
            )
        except Exception as exc:
            logger.warning("Analysis failed for '%s': %s", idea.title[:50], exc)

    logger.info("=== ANALYSIS COMPLETE: %d/%d analyzed ===", analyzed, len(unanalyzed))


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha Scout — Trading Ideas Scanner")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--web",
        action="store_true",
        default=True,
        help="Web dashboard + scheduler (default)",
    )
    group.add_argument(
        "--collect", action="store_true", help="One-shot data collection"
    )
    group.add_argument("--analyze", action="store_true", help="One-shot analysis")
    args = parser.parse_args()

    if args.collect:
        asyncio.run(cmd_collect())
    elif args.analyze:
        asyncio.run(cmd_analyze())
    else:
        asyncio.run(cmd_web())


if __name__ == "__main__":
    main()

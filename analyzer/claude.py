import asyncio
import json
import logging
import os
import re
import subprocess
from datetime import datetime

import httpx

from analyzer.prompts import DEEP_ANALYSIS_PROMPT, SCREEN_PROMPT
from config import settings
from storage.db import IdeaStorage
from storage.models import AIScore, Idea, IdeaCategory, RawItem

logger = logging.getLogger(__name__)

DEEP_ANALYSIS_CATEGORIES = {IdeaCategory.STRATEGY, IdeaCategory.NICHE}

NEWS_INTELLIGENCE_URL = settings.news_intelligence_url

_CLAUDE_ENV: dict[str, str] | None = None


def _get_clean_env() -> dict[str, str]:
    """Env без CLAUDECODE (чтобы не было nested session error)."""
    global _CLAUDE_ENV
    if _CLAUDE_ENV is None:
        _CLAUDE_ENV = os.environ.copy()
        _CLAUDE_ENV.pop("CLAUDECODE", None)
        _CLAUDE_ENV.setdefault("HOME", os.path.expanduser("~"))
    return _CLAUDE_ENV


def _extract_json(text: str) -> dict:
    """Извлекает JSON из ответа Claude (может быть обёрнут в ```json ... ```)."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    return json.loads(text.strip())


def _call_claude_sync(prompt: str, model: str, timeout: int = 120) -> str:
    """Синхронный вызов Claude CLI через subprocess.run()."""
    cmd = [
        "claude",
        "-p",
        "--output-format",
        "text",
        "--model",
        model,
        "--permission-mode",
        "bypassPermissions",
        "--no-session-persistence",
    ]

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_get_clean_env(),
    )

    if result.returncode != 0:
        err = result.stderr[:200] or result.stdout[:200]
        logger.error(
            "Claude CLI error (model=%s, rc=%d): %s", model, result.returncode, err
        )
        raise RuntimeError(f"Claude CLI failed: {err}")

    return result.stdout.strip()


async def _fetch_news_context(query: str) -> str:
    """Fetch relevant news from News Intelligence for enriching analysis."""
    if not NEWS_INTELLIGENCE_URL:
        return ""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{NEWS_INTELLIGENCE_URL}/search",
                params={"q": query, "limit": 5, "hours": 72},
            )
            if resp.status_code != 200:
                return ""

            articles = resp.json()
            if not articles:
                return ""

            lines = []
            for a in articles[:5]:
                title = a.get("title", "")
                summary = a.get("summary", "")[:200]
                source = a.get("source", "")
                published = a.get("published_at", "")[:10]
                lines.append(f"- [{source}, {published}] {title}: {summary}")

            return "\n".join(lines)
    except Exception as e:
        logger.debug("News Intelligence fetch failed: %s", e)
        return ""


class ClaudeAnalyzer:
    """AI-анализатор идей через Claude CLI."""

    async def _call_claude(self, prompt: str, model: str, timeout: int = 120) -> str:
        """Вызов Claude CLI из asyncio через thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, _call_claude_sync, prompt, model, timeout
        )

    async def screen(self, item: RawItem) -> IdeaCategory:
        """Быстрая классификация через Claude Haiku."""
        prompt = SCREEN_PROMPT.format(
            title=item.title,
            source=item.source.value,
            content=item.content[:2000],
        )

        response = await self._call_claude(prompt, settings.claude_model_screen)

        try:
            data = _extract_json(response)
            category = data.get("category", "irrelevant")
            return IdeaCategory(category)
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.warning(
                "Ошибка парсинга screening ответа для '%s': %s. Ответ: %s",
                item.title[:50],
                exc,
                response[:200],
            )
            return IdeaCategory.IRRELEVANT

    async def deep_analyze(self, idea: Idea) -> AIScore:
        """Глубокий анализ через Claude Opus с контекстом из News Intelligence."""
        news_context = await _fetch_news_context(idea.title)

        news_section = ""
        if news_context:
            news_section = f"\n\nRelated news from News Intelligence:\n{news_context}\n"

        prompt = DEEP_ANALYSIS_PROMPT.format(
            title=idea.title,
            source=idea.source.value,
            url=idea.url,
            content=idea.raw_content[:4000] + news_section,
        )

        response = await self._call_claude(prompt, settings.claude_model_deep)

        data = _extract_json(response)
        return AIScore.model_validate(data)

    async def process_items(
        self, items: list[RawItem], storage: IdeaStorage
    ) -> list[Idea]:
        """Полный pipeline: дедупликация -> screening -> deep analysis -> save."""
        new_items: list[RawItem] = []
        for item in items:
            if storage.is_seen(item.content_hash):
                logger.debug("Пропуск дубликата: %s", item.title[:50])
                continue
            storage.mark_seen(item.content_hash)
            new_items.append(item)
        storage.save_if_dirty()

        if not new_items:
            logger.info("Все %d items — дубликаты, пропуск", len(items))
            return []

        result: list[Idea] = []

        for item in new_items:
            try:
                category = await self.screen(item)
            except RuntimeError:
                logger.exception("Ошибка screening для '%s'", item.title[:50])
                continue

            logger.info("Screening: '%s' -> %s", item.title[:50], category.value)

            idea = Idea(
                category=category,
                source=item.source,
                url=item.url,
                title=item.title,
                summary="",
                raw_content=item.content,
                author=item.author,
                source_score=item.score,
            )

            if category in DEEP_ANALYSIS_CATEGORIES:
                try:
                    ai_score = await self.deep_analyze(idea)
                    idea.ai_score = ai_score
                    idea.analyzed_at = datetime.utcnow()
                    idea.summary = ai_score.strategy_description
                    logger.info(
                        "Deep analysis: '%s' -> score=%.1f",
                        idea.title[:50],
                        idea.final_score,
                    )
                except (json.JSONDecodeError, RuntimeError, ValueError) as exc:
                    logger.warning(
                        "Ошибка deep analysis для '%s': %s",
                        idea.title[:50],
                        exc,
                    )

            storage.add_idea(idea)
            result.append(idea)

        logger.info(
            "Обработано %d из %d items, %d прошли deep analysis",
            len(result),
            len(items),
            sum(1 for i in result if i.ai_score is not None),
        )
        return result

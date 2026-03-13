import logging
from datetime import datetime, timezone

import httpx

from storage.db import IdeaStorage
from storage.models import Idea

logger = logging.getLogger(__name__)

SCOUT_URL = "https://scout.maxbob.xyz"


def _score_bar(value: float, max_val: int = 10) -> str:
    """Visual score bar: ██████░░░░ 6/10."""
    filled = round(value)
    empty = max_val - filled
    return "\u2588" * filled + "\u2591" * empty + f" {value:.0f}/{max_val}"


def _truncate(text: str, limit: int = 120) -> str:
    """Truncate text to limit, adding ... if needed."""
    text = text.replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "\u2026"


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class TelegramNotifier:
    """Telegram bot for Alpha Scout alerts via Bot API + httpx."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.client = httpx.AsyncClient(timeout=30)
        self._offset: int = 0

    async def send_message(
        self, chat_id: int, text: str, parse_mode: str = "HTML"
    ) -> None:
        """Send a message to a Telegram chat."""
        try:
            resp = await self.client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
            )
            data = resp.json()
            if not data.get("ok"):
                logger.error(
                    "Telegram API error for chat %d: %s",
                    chat_id,
                    data.get("description", "unknown"),
                )
        except httpx.HTTPError as exc:
            logger.error("Failed to send message to chat %d: %s", chat_id, exc)

    async def send_alert(self, idea: Idea, chat_ids: list[int]) -> None:
        """Send a hot idea alert to specified chats."""
        if not idea.ai_score:
            return

        s = idea.ai_score
        title = _escape_html(_truncate(idea.title, 120))
        source = idea.source.value.capitalize()
        category = idea.category.value.capitalize()

        lines = [
            f"\U0001f525 <b>HOT IDEA \u2014 {idea.final_score:.1f}/10</b>",
            "",
            f"\U0001f4cc <b>{title}</b>",
            "",
            "\u2500" * 20,
            f"\U0001f4b0 ROI:         <code>{_score_bar(s.roi_potential)}</code>",
            f"\u26a1 Feasibility: <code>{_score_bar(s.feasibility)}</code>",
            f"\U0001f527 Complexity:  <code>{_score_bar(s.complexity)}</code>",
            "\u2500" * 20,
            "",
            f"\U0001f4a1 {_escape_html(_truncate(s.strategy_description, 300))}",
            "",
            f"\U0001f4ce {source} \u2022 {category}",
        ]

        if idea.url:
            lines.append(f'\U0001f517 <a href="{idea.url}">Source</a>')

        lines.append(f'\U0001f310 <a href="{SCOUT_URL}">Alpha Scout Dashboard</a>')

        text = "\n".join(lines)

        for chat_id in chat_ids:
            await self.send_message(chat_id, text)

    async def handle_updates(self, storage: IdeaStorage) -> None:
        """Long polling loop for processing bot commands."""
        logger.info("Starting Telegram bot long polling...")
        while True:
            try:
                resp = await self.client.get(
                    f"{self.base_url}/getUpdates",
                    params={"offset": self._offset, "timeout": 30},
                    timeout=35,
                )
                data = resp.json()
                if not data.get("ok"):
                    logger.error(
                        "getUpdates error: %s", data.get("description", "unknown")
                    )
                    continue

                for update in data.get("result", []):
                    self._offset = update["update_id"] + 1
                    await self._process_update(update, storage)

            except httpx.HTTPError as exc:
                logger.error("Polling error: %s", exc)
            except Exception:
                logger.exception("Unexpected error in polling loop")

    async def _process_update(self, update: dict, storage: IdeaStorage) -> None:
        """Process a single update from Telegram."""
        message = update.get("message")
        if not message or not message.get("text"):
            return

        chat_id: int = message["chat"]["id"]
        text = message["text"].strip()

        if text == "/start":
            await self._cmd_start(chat_id)
        elif text.startswith("/ideas"):
            keyword = text[len("/ideas") :].strip() or None
            await self._cmd_ideas(chat_id, storage, keyword)
        elif text == "/trending":
            await self._cmd_trending(chat_id, storage)
        elif text == "/stats":
            await self._cmd_stats(chat_id, storage)

    async def _cmd_start(self, chat_id: int) -> None:
        """Handle /start command."""
        text = (
            "\U0001f50d <b>Alpha Scout Bot</b>\n\n"
            "Мониторю Reddit, GitHub, Polymarket, HN, Twitter и RSS "
            "в поисках торговых идей и стратегий.\n\n"
            "<b>Команды:</b>\n"
            "/ideas \u2014 Топ-5 идей за сегодня\n"
            "/ideas <i>keyword</i> \u2014 Фильтр по слову\n"
            "/trending \u2014 Популярные категории\n"
            "/stats \u2014 Статистика\n\n"
            f'\U0001f310 <a href="{SCOUT_URL}">Dashboard</a>'
        )
        await self.send_message(chat_id, text)

    async def _cmd_ideas(
        self, chat_id: int, storage: IdeaStorage, keyword: str | None = None
    ) -> None:
        """Handle /ideas command."""
        today = datetime.now(tz=timezone.utc).date()
        ideas = storage.get_ideas(limit=100)
        today_ideas = [
            i for i in ideas if i.created_at.date() == today and i.ai_score is not None
        ]

        if keyword:
            keyword_lower = keyword.lower()
            today_ideas = [i for i in today_ideas if keyword_lower in i.title.lower()]

        top = today_ideas[:5]

        if not top:
            label = f" \u00ab{_escape_html(keyword)}\u00bb" if keyword else ""
            await self.send_message(
                chat_id, f"\U0001f4ad Идей за сегодня{label} не найдено."
            )
            return

        medals = [
            "\U0001f947",
            "\U0001f948",
            "\U0001f949",
            "4\ufe0f\u20e3",
            "5\ufe0f\u20e3",
        ]
        lines = ["\U0001f4cb <b>Top Ideas Today:</b>\n"]

        for idx, idea in enumerate(top):
            medal = medals[idx] if idx < len(medals) else f"{idx + 1}."
            title = _escape_html(_truncate(idea.title, 80))
            source = idea.source.value.capitalize()
            category = idea.category.value.capitalize()

            lines.append(f"{medal} <b>{idea.final_score:.1f}</b> \u2014 {title}")
            link_parts = [f"\U0001f4ce {source} \u2022 {category}"]
            if idea.url:
                link_parts.append(f'<a href="{idea.url}">Source</a>')
            lines.append("     " + " | ".join(link_parts))
            lines.append("")

        lines.append(f'\U0001f310 <a href="{SCOUT_URL}">All ideas on Dashboard</a>')

        await self.send_message(chat_id, "\n".join(lines))

    async def _cmd_trending(self, chat_id: int, storage: IdeaStorage) -> None:
        """Handle /trending command."""
        stats = storage.get_stats()
        by_category: dict[str, int] = stats.get("by_category", {})

        if not by_category:
            await self.send_message(chat_id, "No data available yet.")
            return

        sorted_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
        total = sum(c for _, c in sorted_cats)

        lines = ["\U0001f4c8 <b>Trending Categories:</b>\n"]
        for cat, count in sorted_cats:
            pct = count / total * 100 if total else 0
            bar_len = round(pct / 5)
            bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)
            lines.append(
                f"  <code>{bar}</code> {cat.capitalize()}: <b>{count}</b> ({pct:.0f}%)"
            )

        lines.append(f"\n\U0001f4ca Total: <b>{total}</b> ideas")
        lines.append(f'\U0001f310 <a href="{SCOUT_URL}">Dashboard</a>')

        await self.send_message(chat_id, "\n".join(lines))

    async def _cmd_stats(self, chat_id: int, storage: IdeaStorage) -> None:
        """Handle /stats command."""
        stats = storage.get_stats()

        by_source = stats.get("by_source", {})
        source_lines = []
        for src, cnt in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
            source_lines.append(f"  \u2022 {src.capitalize()}: <b>{cnt}</b>")

        text = (
            "\U0001f4ca <b>Alpha Scout Stats</b>\n\n"
            f"\U0001f4e6 Total ideas: <b>{stats['total']}</b>\n"
            f"\U0001f9ea Analyzed: <b>{stats['analyzed']}</b>\n"
            f"\U0001f525 Hot ideas (score \u22656): <b>{stats['hot_ideas']}</b>\n"
            f"\U0001f4c9 Avg score: <b>{stats['avg_score']}</b>\n\n"
            "\U0001f4e1 <b>By source:</b>\n"
            + "\n".join(source_lines)
            + f'\n\n\U0001f310 <a href="{SCOUT_URL}">Dashboard</a>'
        )
        await self.send_message(chat_id, text)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

import json
import logging
from datetime import datetime
from pathlib import Path

from config import settings
from storage.models import Idea, IdeaCategory, SourceType

logger = logging.getLogger(__name__)


class IdeaStorage:
    """JSON-хранилище идей (аналог polymarket-bot storage)."""

    _instance: "IdeaStorage | None" = None

    def __new__(cls) -> "IdeaStorage":
        """Singleton — одна инстанция на весь процесс."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.data_dir = Path(settings.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.ideas_file = self.data_dir / "ideas.json"
        self.seen_file = self.data_dir / "seen_hashes.json"
        self._ideas: list[Idea] = []
        self._seen_hashes: set[str] = set()
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if self.ideas_file.exists():
            data = json.loads(self.ideas_file.read_text(encoding="utf-8"))
            self._ideas = [Idea.model_validate(item) for item in data]
            logger.info("Загружено %d идей", len(self._ideas))

        if self.seen_file.exists():
            self._seen_hashes = set(
                json.loads(self.seen_file.read_text(encoding="utf-8"))
            )

    def _save(self) -> None:
        data = [idea.model_dump(mode="json") for idea in self._ideas]
        self.ideas_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        self.seen_file.write_text(
            json.dumps(list(self._seen_hashes), ensure_ascii=False),
            encoding="utf-8",
        )
        self._dirty = False

    def save_if_dirty(self) -> None:
        """Сохранить на диск, если были изменения."""
        if self._dirty:
            self._save()

    def is_seen(self, content_hash: str) -> bool:
        return content_hash in self._seen_hashes

    def mark_seen(self, content_hash: str) -> None:
        self._seen_hashes.add(content_hash)
        self._dirty = True

    def add_idea(self, idea: Idea) -> None:
        if not idea.id:
            idea.id = f"{idea.source.value}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(self._ideas)}"
        self._ideas.append(idea)
        self._dirty = True
        self._save()  # save after each idea (important data)
        logger.info(
            "Добавлена идея: %s (score=%.1f)", idea.title[:50], idea.final_score
        )

    def update_idea(self, idea_id: str, **kwargs: object) -> None:
        for idea in self._ideas:
            if idea.id == idea_id:
                for key, value in kwargs.items():
                    setattr(idea, key, value)
                self._dirty = True
                self._save()
                return

    def get_ideas(
        self,
        category: IdeaCategory | None = None,
        source: SourceType | None = None,
        min_score: float = 0.0,
        limit: int = 50,
    ) -> list[Idea]:
        result = self._ideas[:]
        if category:
            result = [i for i in result if i.category == category]
        if source:
            result = [i for i in result if i.source == source]
        if min_score > 0:
            result = [i for i in result if i.final_score >= min_score]
        result.sort(key=lambda x: x.final_score, reverse=True)
        return result[:limit]

    def get_idea_by_id(self, idea_id: str) -> Idea | None:
        for idea in self._ideas:
            if idea.id == idea_id:
                return idea
        return None

    def get_stats(self) -> dict:
        analyzed = [i for i in self._ideas if i.ai_score is not None]
        hot = [i for i in analyzed if i.final_score >= settings.alert_score_threshold]
        by_source: dict[str, int] = {}
        for idea in self._ideas:
            by_source[idea.source.value] = by_source.get(idea.source.value, 0) + 1
        by_category: dict[str, int] = {}
        for idea in self._ideas:
            by_category[idea.category.value] = (
                by_category.get(idea.category.value, 0) + 1
            )
        return {
            "total": len(self._ideas),
            "analyzed": len(analyzed),
            "hot_ideas": len(hot),
            "seen_hashes": len(self._seen_hashes),
            "by_source": by_source,
            "by_category": by_category,
            "avg_score": round(sum(i.final_score for i in analyzed) / len(analyzed), 2)
            if analyzed
            else 0,
        }

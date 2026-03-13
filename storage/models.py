from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class IdeaCategory(str, Enum):
    STRATEGY = "strategy"
    TOOL = "tool"
    NICHE = "niche"
    NEWS = "news"
    IRRELEVANT = "irrelevant"


class SourceType(str, Enum):
    REDDIT = "reddit"
    GITHUB = "github"
    POLYMARKET = "polymarket"
    HACKERNEWS = "hackernews"
    RSS = "rss"
    TWITTER = "twitter"
    TELEGRAM = "telegram"


class RawItem(BaseModel):
    """Сырой элемент из источника данных."""

    source: SourceType
    url: str = ""
    title: str = ""
    content: str = ""
    author: str = ""
    score: int = 0
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        import hashlib

        text = f"{self.url}|{self.title}|{self.content[:200]}"
        return hashlib.md5(text.encode()).hexdigest()


class AIScore(BaseModel):
    """Результат AI-оценки идеи."""

    roi_potential: float = Field(ge=1, le=10, description="Ожидаемая доходность")
    feasibility: float = Field(ge=1, le=10, description="Реализуемость")
    complexity: float = Field(ge=1, le=10, description="Сложность реализации")
    reasoning: str = ""
    strategy_description: str = ""
    similar_bots: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)

    @property
    def final_score(self) -> float:
        from config import settings

        raw = (
            self.roi_potential * settings.score_weight_roi
            + self.feasibility * settings.score_weight_feasibility
            + (10 - self.complexity) * settings.score_weight_complexity
        )
        return round(raw, 2)


class Idea(BaseModel):
    """Идея торговой стратегии или ниши."""

    id: str = ""
    category: IdeaCategory = IdeaCategory.IRRELEVANT
    source: SourceType
    url: str = ""
    title: str = ""
    summary: str = ""
    raw_content: str = ""
    author: str = ""
    source_score: int = 0
    ai_score: AIScore | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    analyzed_at: datetime | None = None

    @property
    def final_score(self) -> float:
        if self.ai_score:
            return self.ai_score.final_score
        return 0.0

"""Web dashboard для Alpha Scout."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings
from storage.db import IdeaStorage
from storage.models import Idea, IdeaCategory, SourceType

logger = logging.getLogger(__name__)

app = FastAPI(title="Alpha Scout Dashboard")

# In-memory collector status tracking
collector_status: dict[str, dict[str, Any]] = {}

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _get_storage() -> IdeaStorage:
    return IdeaStorage()


def _idea_to_dict(idea: Idea) -> dict[str, Any]:
    """Сериализация Idea в dict для JSON/шаблонов."""
    result: dict[str, Any] = {
        "id": idea.id,
        "title": idea.title,
        "summary": idea.summary,
        "category": idea.category.value,
        "source": idea.source.value,
        "url": idea.url,
        "author": idea.author,
        "source_score": idea.source_score,
        "final_score": idea.final_score,
        "created_at": idea.created_at.isoformat() if idea.created_at else "",
        "analyzed_at": idea.analyzed_at.isoformat() if idea.analyzed_at else "",
    }
    if idea.ai_score:
        result["ai_score"] = {
            "roi_potential": idea.ai_score.roi_potential,
            "feasibility": idea.ai_score.feasibility,
            "complexity": idea.ai_score.complexity,
            "reasoning": idea.ai_score.reasoning,
            "strategy_description": idea.ai_score.strategy_description,
            "similar_bots": idea.ai_score.similar_bots,
            "action_items": idea.ai_score.action_items,
        }
    else:
        result["ai_score"] = None
    return result


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Главная страница dashboard."""
    storage = _get_storage()
    stats = storage.get_stats()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "stats": stats},
    )


@app.get("/idea/{idea_id}", response_class=HTMLResponse)
async def idea_detail(request: Request, idea_id: str) -> HTMLResponse:
    """Детальный view идеи."""
    storage = _get_storage()
    idea = storage.get_idea_by_id(idea_id)
    if not idea:
        return HTMLResponse("<h1>Idea not found</h1>", status_code=404)
    return templates.TemplateResponse(
        "idea_detail.html",
        {"request": request, "idea": _idea_to_dict(idea)},
    )


@app.get("/api/ideas")
async def api_ideas(
    category: str | None = None,
    source: str | None = None,
    min_score: float = 0.0,
    limit: int = 50,
) -> JSONResponse:
    """JSON список идей с фильтрами."""
    storage = _get_storage()

    cat: IdeaCategory | None = None
    if category:
        try:
            cat = IdeaCategory(category)
        except ValueError:
            return JSONResponse(
                {"error": f"Invalid category: {category}"}, status_code=400
            )

    src: SourceType | None = None
    if source:
        try:
            src = SourceType(source)
        except ValueError:
            return JSONResponse({"error": f"Invalid source: {source}"}, status_code=400)

    ideas = storage.get_ideas(
        category=cat, source=src, min_score=min_score, limit=limit
    )
    return JSONResponse([_idea_to_dict(i) for i in ideas])


@app.get("/api/stats")
async def api_stats() -> JSONResponse:
    """JSON статистика."""
    storage = _get_storage()
    return JSONResponse(storage.get_stats())


@app.get("/api/idea/{idea_id}")
async def api_idea(idea_id: str) -> JSONResponse:
    """JSON одна идея."""
    storage = _get_storage()
    idea = storage.get_idea_by_id(idea_id)
    if not idea:
        return JSONResponse({"error": "Idea not found"}, status_code=404)
    return JSONResponse(_idea_to_dict(idea))


@app.get("/api/collectors")
async def api_collectors() -> JSONResponse:
    """JSON статусы collectors в реальном времени."""
    return JSONResponse(collector_status)


def update_collector_status(
    name: str,
    *,
    status: str = "idle",
    items_count: int = 0,
    error: str = "",
    method: str = "",
    warning: str = "",
) -> None:
    """Обновить статус collector (вызывается из main.py scheduler)."""
    collector_status[name] = {
        "status": status,
        "items_count": items_count,
        "error": error,
        "method": method,
        "warning": warning,
        "updated_at": datetime.utcnow().isoformat(),
    }


def start_web(host: str | None = None, port: int | None = None) -> None:
    """Запуск web dashboard."""
    _host = host or settings.web_host
    _port = port or settings.web_port
    logger.info("Starting Alpha Scout dashboard at http://%s:%d", _host, _port)
    uvicorn.run(app, host=_host, port=_port, log_level="info")

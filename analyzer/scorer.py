from config import settings
from storage.models import AIScore


def calculate_final_score(ai_score: AIScore) -> float:
    """Final Score = (ROI * 0.4 + Feasibility * 0.35 + (10 - Complexity) * 0.25).

    Args:
        ai_score: AI-оценка идеи с полями roi_potential, feasibility, complexity.

    Returns:
        Взвешенный финальный скор.
    """
    raw = (
        ai_score.roi_potential * settings.score_weight_roi
        + ai_score.feasibility * settings.score_weight_feasibility
        + (10 - ai_score.complexity) * settings.score_weight_complexity
    )
    return round(raw, 2)

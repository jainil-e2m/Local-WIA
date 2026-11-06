from __future__ import annotations

import math
from datetime import UTC, datetime

from .models import Angle


def cosine(a: list[float], b: list[float]) -> float:
    if not a or len(a) != len(b):
        raise ValueError("Vectors must be non-empty and equal length")
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def adjusted_score(
    angle: Angle, history: list[Angle], *, threshold: float, half_life: float, max_penalty: float, as_of: datetime | None = None
) -> tuple[float, float | None]:
    as_of = as_of or datetime.now(UTC)
    similarities: list[float] = []
    if angle.embedding:
        for old in history:
            if old.embedding and old.angle_id != angle.angle_id:
                score = cosine(angle.embedding, old.embedding)
                if score >= threshold:
                    age = max(0.0, (as_of - old.generated_at).total_seconds() / 86400)
                    recency = 2 ** (-age / half_life)
                    similarities.append(max(0.0, min(1.0, (score - threshold) / (1 - threshold))) * recency)
    risk = max(similarities, default=0.0)
    return angle.base_score * (1 - max_penalty * risk), max(similarities, default=None)


def rank(
    angles: list[Angle], history: list[Angle], *, threshold: float, visible_threshold: float, half_life: float, max_penalty: float
) -> list[Angle]:
    results = []
    for angle in angles:
        score, sim = adjusted_score(angle, history, threshold=threshold, half_life=half_life, max_penalty=max_penalty)
        angle.max_similarity, angle.adjusted_score = sim, score
        ready = not angle.strategy or angle.strategy.evidence_readiness == "supported"
        angle.status = "visible" if ready and score > visible_threshold else "suppressed"
        results.append(angle)
    return sorted(results, key=lambda item: item.adjusted_score or 0, reverse=True)

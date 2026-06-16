from __future__ import annotations

from pydantic import BaseModel, Field


class ReportQuery(BaseModel):
    days: int = Field(default=30, ge=1, le=365)


class MetricValue(BaseModel):
    current: float | int | None = None
    previous: float | int | None = None
    delta_pct: float | None = None

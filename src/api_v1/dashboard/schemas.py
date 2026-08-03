from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class ReportQuery(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    since: date | None = None
    until: date | None = None
    force_refresh: bool = False

    @model_validator(mode="after")
    def validate_period(self) -> "ReportQuery":
        if self.since is None and self.until is None:
            return self
        if self.since is None or self.until is None:
            raise ValueError("since and until must be provided together")
        if self.until < self.since:
            raise ValueError("until must be on or after since")
        if (self.until - self.since).days + 1 > 365:
            raise ValueError("custom period cannot exceed 365 days")
        return self


class MetricValue(BaseModel):
    current: float | int | None = None
    previous: float | int | None = None
    delta_pct: float | None = None

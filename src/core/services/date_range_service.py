from __future__ import annotations

from datetime import datetime, timedelta, timezone


class DateRangeService:
    def build_periods(self, *, days: int, now: datetime | None = None) -> dict[str, dict[str, str]]:
        normalized_days = max(1, int(days))
        anchor = (now or datetime.now(timezone.utc)).date()

        current_until = anchor
        current_since = current_until - timedelta(days=normalized_days - 1)
        previous_until = current_since - timedelta(days=1)
        previous_since = previous_until - timedelta(days=normalized_days - 1)

        fmt = lambda value: value.isoformat()
        return {
            "current": {"since": fmt(current_since), "until": fmt(current_until)},
            "previous": {"since": fmt(previous_since), "until": fmt(previous_until)},
        }

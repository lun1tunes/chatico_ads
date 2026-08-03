from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


class DateRangeService:
    def build_periods(
        self,
        *,
        days: int | None = None,
        since: date | str | None = None,
        until: date | str | None = None,
        now: datetime | None = None,
    ) -> dict[str, dict[str, str]]:
        current_since, current_until = self._resolve_current_period(
            days=days,
            since=since,
            until=until,
            now=now,
        )
        current_days = (current_until - current_since).days + 1
        previous_until = current_since - timedelta(days=1)
        previous_since = previous_until - timedelta(days=current_days - 1)

        fmt = lambda value: value.isoformat()
        return {
            "current": {"since": fmt(current_since), "until": fmt(current_until)},
            "previous": {"since": fmt(previous_since), "until": fmt(previous_until)},
        }

    def _resolve_current_period(
        self,
        *,
        days: int | None,
        since: date | str | None,
        until: date | str | None,
        now: datetime | None,
    ) -> tuple[date, date]:
        if since is not None or until is not None:
            if since is None or until is None:
                raise ValueError("Both since and until must be provided together")
            current_since = self._parse_date(since)
            current_until = self._parse_date(until)
            if current_until < current_since:
                raise ValueError("until must be on or after since")
            return current_since, current_until

        normalized_days = max(1, int(days or 30))
        anchor = (now or datetime.now(timezone.utc)).date()
        current_until = anchor
        current_since = current_until - timedelta(days=normalized_days - 1)
        return current_since, current_until

    def _parse_date(self, value: date | str) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

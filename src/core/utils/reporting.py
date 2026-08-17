from __future__ import annotations

from collections import defaultdict

RESULT_PRIORITY = (
    "onsite_conversion.messaging_conversation_started_7d",
    "lead",
    "onsite_conversion.lead_grouped",
    "offsite_conversion.fb_pixel_lead",
)


def to_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def to_int(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def extract_primary_result(actions: list[dict[str, object]] | None) -> tuple[str, int]:
    if not actions:
        return ("result", 0)

    action_map = {str(item.get("action_type", "")): to_int(item.get("value")) for item in actions}
    # Prefer the dominant result count among known action types.
    # Tie-break by RESULT_PRIORITY order so WhatsApp-first accounts keep messaging when counts match.
    best: tuple[int, int, str, int] | None = None  # (-count, priority_index, kind, count)
    for index, action_type in enumerate(RESULT_PRIORITY):
        if action_type not in action_map:
            continue
        count = action_map[action_type]
        if count <= 0:
            continue
        kind = "messages" if "messaging" in action_type else "leads"
        candidate = (-count, index, kind, count)
        if best is None or candidate < best:
            best = candidate
    if best is None:
        return ("result", 0)
    return (best[2], best[3])


def percentage_delta(current: float | int | None, previous: float | int | None) -> float | None:
    current_value = float(current or 0)
    previous_value = float(previous or 0)
    if previous_value == 0:
        return None
    return ((current_value - previous_value) / previous_value) * 100.0


def build_metric(current: float | int | None, previous: float | int | None) -> dict[str, float | int | None]:
    return {
        "current": current,
        "previous": previous,
        "delta_pct": percentage_delta(current, previous),
    }


def group_ads_by_campaign(ads: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for ad in ads:
        campaign_id = str(ad.get("campaign_id") or "").strip()
        if campaign_id:
            grouped[campaign_id].append(ad)
    return dict(grouped)

from __future__ import annotations

import re
from typing import Any


_METRIC_KEYS = (
    "spend",
    "reach",
    "impressions",
    "clicks",
    "ctr",
    "cpm",
    "cpc",
    "results",
    "cost_per_result",
)

_METRIC_ALIASES = {
    "spend": "sp",
    "reach": "rh",
    "impressions": "im",
    "clicks": "cl",
    "ctr": "ctr",
    "cpm": "cpm",
    "cpc": "cpc",
    "results": "rs",
    "cost_per_result": "cpr",
}
_MAX_CAMPAIGNS = 12
_MAX_CREATIVES_PER_CAMPAIGN = 6
_MAX_TEXT_LENGTH = 96
_UNSAFE_TEXT_RE = re.compile(r"[\r\n|;]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _sanitize_text(value: str) -> str:
    sanitized = _UNSAFE_TEXT_RE.sub(" / ", value)
    sanitized = _WHITESPACE_RE.sub(" ", sanitized).strip()
    if len(sanitized) > _MAX_TEXT_LENGTH:
        sanitized = sanitized[: _MAX_TEXT_LENGTH - 3].rstrip() + "..."
    return sanitized


def _round_number(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    return value


def _format_scalar(value: Any) -> str:
    if value is None:
        return "~"
    if isinstance(value, str):
        return _sanitize_text(value) or "~"
    if isinstance(value, float):
        rounded = _round_number(value)
        if isinstance(rounded, float):
            return f"{rounded:.4f}".rstrip("0").rstrip(".")
        return str(rounded)
    return str(value)


def _compact_metric_series(metrics: dict[str, Any]) -> str:
    parts: list[str] = []

    for key in _METRIC_KEYS:
        item = metrics.get(key, {})
        values = [
            _format_scalar(item.get("current")),
            _format_scalar(item.get("previous")),
            _format_scalar(item.get("delta_pct")),
        ]
        while len(values) > 1 and values[-1] == "~":
            values.pop()
        parts.append(f"{_METRIC_ALIASES[key]}:{','.join(values)}")

    return ";".join(parts)


def _compact_creative(creative: dict[str, Any]) -> str:
    creative_metrics = creative["metrics"]
    creative_parts = [
        _format_scalar(creative["name"]),
        _format_scalar(creative["object_type"]),
        _format_scalar(creative_metrics["spend"]),
        _format_scalar(creative_metrics["impressions"]),
        _format_scalar(creative_metrics["clicks"]),
        _format_scalar(creative_metrics["ctr"]),
        _format_scalar(creative_metrics["results"]),
        _format_scalar(creative_metrics["result_kind"]),
    ]
    return "crt|" + "|".join(creative_parts)


def _campaign_sort_key(campaign: dict[str, Any]) -> tuple[float, float, str]:
    metrics = campaign.get("metrics", {})
    spend = metrics.get("spend", {}) if isinstance(metrics, dict) else {}
    results = metrics.get("results", {}) if isinstance(metrics, dict) else {}
    return (
        float(spend.get("current") or 0),
        float(results.get("current") or 0),
        str(campaign.get("name") or ""),
    )


def _creative_sort_key(creative: dict[str, Any]) -> tuple[float, float, str]:
    metrics = creative.get("metrics", {})
    return (
        float(metrics.get("spend") or 0),
        float(metrics.get("results") or 0),
        str(creative.get("name") or ""),
    )


def build_report_context(report: dict[str, object]) -> str:
    account = report["account"]
    summary = report["summary"]

    lines = [
        "fmt|sum/cmp metrics sp,rh,im,cl,ctr,cpm,cpc,rs,cpr as current,previous,delta_pct|crt name|type|sp|im|cl|ctr|rs|rk",
        "acct|"
        + "|".join(
            [
                _format_scalar(account.get("name")),
                _format_scalar(account.get("account_id")),
                _format_scalar(account.get("currency")),
                _format_scalar(account.get("timezone_name")),
            ]
        ),
        "prd|"
        + "|".join(
            [
                report["periods"]["current"]["since"],
                report["periods"]["current"]["until"],
                report["periods"]["previous"]["since"],
                report["periods"]["previous"]["until"],
            ]
        ),
        "sum|"
        + "|".join(
            [
                _format_scalar(summary["primary_result_kind"]),
                _format_scalar(summary["active_campaigns"]),
                _format_scalar(summary["total_campaigns"]),
                _compact_metric_series(summary["metrics"]),
            ]
        ),
    ]

    campaigns = sorted(report["campaigns"], key=_campaign_sort_key, reverse=True)
    limited_campaigns = campaigns[:_MAX_CAMPAIGNS]
    omitted_campaign_count = max(0, len(campaigns) - len(limited_campaigns))
    if omitted_campaign_count:
        lines.append(f"more|cmp|{omitted_campaign_count}")

    for campaign in limited_campaigns:
        lines.append(
            "cmp|"
            + "|".join(
                [
                    _format_scalar(campaign["name"]),
                    _format_scalar(campaign["status"]),
                    _format_scalar(campaign["primary_result_kind"]),
                    _compact_metric_series(campaign["metrics"]),
                ]
            )
        )
        creatives = sorted(campaign["creatives"], key=_creative_sort_key, reverse=True)
        limited_creatives = creatives[:_MAX_CREATIVES_PER_CAMPAIGN]
        lines.extend(_compact_creative(creative) for creative in limited_creatives)

        omitted_creative_count = max(0, len(creatives) - len(limited_creatives))
        if omitted_creative_count:
            lines.append(f"more|crt|{_format_scalar(campaign['name'])}|{omitted_creative_count}")

    return "\n".join(lines)

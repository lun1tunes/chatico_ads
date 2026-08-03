from __future__ import annotations

import re
from typing import Any, Literal

AutoVerdictScope = Literal["account", "campaign", "ad_group", "creative"]

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
_MAX_AD_GROUPS_PER_CAMPAIGN = 6
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


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
        _format_scalar(creative.get("headline")),
        _format_scalar(creative.get("primary_text")),
        _format_scalar(creative.get("call_to_action")),
        _format_scalar(creative.get("destination_url")),
    ]
    return "crt|" + "|".join(creative_parts)


def _compact_ad_group(ad_group: dict[str, Any]) -> str:
    targeting = ad_group.get("targeting", {})
    metrics = ad_group.get("metrics", {})
    ad_group_parts = [
        _format_scalar(ad_group.get("name")),
        _format_scalar(targeting.get("geo") if isinstance(targeting, dict) else None),
        _format_scalar(targeting.get("age") if isinstance(targeting, dict) else None),
        _format_scalar(targeting.get("gender") if isinstance(targeting, dict) else None),
        _format_scalar(targeting.get("audience") if isinstance(targeting, dict) else None),
        _format_scalar(targeting.get("signal") if isinstance(targeting, dict) else None),
        _format_scalar(targeting.get("placement") if isinstance(targeting, dict) else None),
        _format_scalar(targeting.get("device") if isinstance(targeting, dict) else None),
        _format_scalar(metrics.get("spend")),
        _format_scalar(metrics.get("impressions")),
        _format_scalar(metrics.get("clicks")),
        _format_scalar(metrics.get("ctr")),
        _format_scalar(metrics.get("results")),
        _format_scalar(metrics.get("result_kind")),
    ]
    return "grp|" + "|".join(ad_group_parts)


def _campaign_sort_key(campaign: dict[str, Any]) -> tuple[float, float, str]:
    metrics = campaign.get("metrics", {})
    return (
        _metric_current(metrics, "spend"),
        _metric_current(metrics, "results"),
        str(campaign.get("name") or ""),
    )


def _creative_sort_key(creative: dict[str, Any]) -> tuple[float, float, str]:
    metrics = creative.get("metrics", {})
    return (
        float(_number(metrics.get("spend")) or 0),
        float(_number(metrics.get("results")) or 0),
        str(creative.get("name") or ""),
    )


def _ad_group_sort_key(ad_group: dict[str, Any]) -> tuple[float, float, str]:
    metrics = ad_group.get("metrics", {})
    return (
        float(_number(metrics.get("spend")) or 0),
        float(_number(metrics.get("results")) or 0),
        str(ad_group.get("name") or ""),
    )


def _metric_current(metrics: Any, key: str) -> float:
    if not isinstance(metrics, dict):
        return 0.0

    metric = metrics.get(key)
    if isinstance(metric, dict):
        return float(_number(metric.get("current")) or 0)
    return float(_number(metric) or 0)


def _metric_collection_from_entity_metrics(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    spend = _number(metrics.get("spend"))
    reach = _number(metrics.get("reach"))
    impressions = _number(metrics.get("impressions"))
    clicks = _number(metrics.get("clicks"))
    ctr = _number(metrics.get("ctr"))
    if ctr is None and impressions and clicks is not None:
        ctr = (clicks / impressions) * 100

    cpm = _number(metrics.get("cpm"))
    if cpm is None and spend is not None and impressions and impressions > 0:
        cpm = (spend * 1000) / impressions

    cpc = _number(metrics.get("cpc"))
    if cpc is None and spend is not None and clicks and clicks > 0:
        cpc = spend / clicks

    results = _number(metrics.get("results"))
    cost_per_result = _number(metrics.get("cost_per_result"))
    if cost_per_result is None and spend is not None and results and results > 0:
        cost_per_result = spend / results

    values = {
        "spend": spend,
        "reach": reach,
        "impressions": impressions,
        "clicks": clicks,
        "ctr": ctr,
        "cpm": cpm,
        "cpc": cpc,
        "results": results,
        "cost_per_result": cost_per_result,
    }
    return {
        key: {
            "current": values.get(key),
            "previous": None,
            "delta_pct": None,
        }
        for key in _METRIC_KEYS
    }


def _build_summary(
    *,
    primary_result_kind: str | None,
    metrics: dict[str, Any],
    status: str | None = None,
) -> dict[str, Any]:
    active_campaigns = 1 if _is_active_scope(metrics=metrics, status=status) else 0
    return {
        "primary_result_kind": primary_result_kind or "result",
        "active_campaigns": active_campaigns,
        "total_campaigns": 1,
        "metrics": metrics,
    }


def _is_active_scope(*, metrics: dict[str, Any], status: str | None = None) -> bool:
    normalized_status = str(status or "").strip().lower()
    if normalized_status in {"active", "enabled", "serving"}:
        return True

    return any(
        _metric_current(metrics, key) > 0
        for key in ("spend", "impressions", "clicks", "results")
    )


def _report_base(
    report: dict[str, object],
    *,
    summary: dict[str, Any],
    campaigns: list[dict[str, Any]],
) -> dict[str, object]:
    scoped_report: dict[str, object] = {
        "account": report["account"],
        "periods": report["periods"],
        "summary": summary,
        "campaigns": campaigns,
    }
    trend = report.get("trend")
    if trend is not None:
        scoped_report["trend"] = trend
    return scoped_report


def _campaign_ad_groups(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    ad_groups = campaign.get("ad_groups")
    if isinstance(ad_groups, list) and ad_groups:
        return [ad_group for ad_group in ad_groups if isinstance(ad_group, dict)]
    return _derive_ad_groups_from_creatives(campaign)


def _derive_ad_groups_from_creatives(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    creatives = campaign.get("creatives", [])
    if not isinstance(creatives, list):
        return []

    campaign_id = _format_scalar(campaign.get("id"))
    grouped: dict[str, dict[str, Any]] = {}

    for creative in creatives:
        if not isinstance(creative, dict):
            continue

        group_id = str(creative.get("ad_group_id") or f"{campaign_id}-primary-group").strip() or f"{campaign_id}-primary-group"
        group_name = str(creative.get("ad_group_name") or "").strip()
        group = grouped.setdefault(
            group_id,
            {
                "id": group_id,
                "name": group_name,
                "targeting": {},
                "metrics": {
                    "spend": 0.0,
                    "impressions": 0.0,
                    "clicks": 0.0,
                    "ctr": 0.0,
                    "results": 0.0,
                    "result_kind": str(
                        creative.get("metrics", {}).get("result_kind")
                        or campaign.get("primary_result_kind")
                        or "result"
                    ),
                },
            },
        )
        if not group.get("name") and group_name:
            group["name"] = group_name

        creative_metrics = creative.get("metrics", {})
        if not isinstance(creative_metrics, dict):
            continue

        group_metrics = group["metrics"]
        group_metrics["spend"] += float(_number(creative_metrics.get("spend")) or 0)
        group_metrics["impressions"] += float(_number(creative_metrics.get("impressions")) or 0)
        group_metrics["clicks"] += float(_number(creative_metrics.get("clicks")) or 0)
        group_metrics["results"] += float(_number(creative_metrics.get("results")) or 0)

    derived_groups = list(grouped.values())
    for group in derived_groups:
        metrics = group["metrics"]
        impressions = float(_number(metrics.get("impressions")) or 0)
        clicks = float(_number(metrics.get("clicks")) or 0)
        metrics["ctr"] = (clicks / impressions) * 100 if impressions > 0 else 0.0

    return derived_groups


def _normalize_campaign(
    campaign: dict[str, Any],
    *,
    entity_id: str | None = None,
    name: str | None = None,
    metrics: dict[str, Any] | None = None,
    result_kind: str | None = None,
    ad_groups: list[dict[str, Any]] | None = None,
    creatives: list[dict[str, Any]] | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    normalized_campaign = {
        "id": entity_id or campaign.get("id"),
        "name": name if name is not None else campaign.get("name"),
        "status": status if status is not None else campaign.get("status"),
        "primary_result_kind": result_kind if result_kind is not None else campaign.get("primary_result_kind"),
        "metrics": metrics if metrics is not None else campaign.get("metrics", {}),
        "ad_groups": ad_groups if ad_groups is not None else _campaign_ad_groups(campaign),
        "creatives": creatives
        if creatives is not None
        else [creative for creative in campaign.get("creatives", []) if isinstance(creative, dict)],
    }
    if "objective" in campaign:
        normalized_campaign["objective"] = campaign.get("objective")
    return normalized_campaign


def _find_campaign(report: dict[str, object], campaign_id: str | None) -> dict[str, Any] | None:
    normalized_id = str(campaign_id or "").strip()
    if not normalized_id:
        return None

    campaigns = report.get("campaigns", [])
    if not isinstance(campaigns, list):
        return None

    for campaign in campaigns:
        if isinstance(campaign, dict) and str(campaign.get("id") or "").strip() == normalized_id:
            return campaign
    return None


def _campaign_candidates(report: dict[str, object], campaign_id: str | None) -> list[dict[str, Any]]:
    selected_campaign = _find_campaign(report, campaign_id)
    if selected_campaign is not None:
        return [selected_campaign]

    campaigns = report.get("campaigns", [])
    if not isinstance(campaigns, list):
        return []
    return [campaign for campaign in campaigns if isinstance(campaign, dict)]


def _find_ad_group(
    report: dict[str, object],
    *,
    campaign_id: str | None,
    ad_group_id: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    selected_campaign = _find_campaign(report, campaign_id)
    normalized_id = str(ad_group_id or "").strip()
    candidates = [selected_campaign] if selected_campaign is not None else _campaign_candidates(report, campaign_id)

    for campaign in candidates:
        if campaign is None:
            continue
        for ad_group in _campaign_ad_groups(campaign):
            if str(ad_group.get("id") or "").strip() == normalized_id:
                return campaign, ad_group

    return selected_campaign, None


def _find_creative(
    report: dict[str, object],
    *,
    campaign_id: str | None,
    creative_id: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    selected_campaign = _find_campaign(report, campaign_id)
    normalized_id = str(creative_id or "").strip()
    candidates = [selected_campaign] if selected_campaign is not None else _campaign_candidates(report, campaign_id)

    for campaign in candidates:
        if campaign is None:
            continue
        creatives = campaign.get("creatives", [])
        if not isinstance(creatives, list):
            continue
        for creative in creatives:
            if isinstance(creative, dict) and str(creative.get("id") or "").strip() == normalized_id:
                return campaign, creative

    return selected_campaign, None


def _creatives_for_ad_group(campaign: dict[str, Any], ad_group_id: str | None) -> list[dict[str, Any]]:
    creatives = campaign.get("creatives", [])
    if not isinstance(creatives, list):
        return []

    normalized_id = str(ad_group_id or "").strip()
    if not normalized_id:
        return [creative for creative in creatives if isinstance(creative, dict)]

    matched = [
        creative
        for creative in creatives
        if isinstance(creative, dict) and str(creative.get("ad_group_id") or "").strip() == normalized_id
    ]
    if matched:
        return matched

    if len(_campaign_ad_groups(campaign)) == 1:
        return [creative for creative in creatives if isinstance(creative, dict)]
    return []


def _ad_group_for_creative(campaign: dict[str, Any], creative: dict[str, Any]) -> dict[str, Any] | None:
    creative_group_id = str(creative.get("ad_group_id") or "").strip()
    creative_group_name = str(creative.get("ad_group_name") or "").strip()

    for ad_group in _campaign_ad_groups(campaign):
        if creative_group_id and str(ad_group.get("id") or "").strip() == creative_group_id:
            return ad_group
        if creative_group_name and str(ad_group.get("name") or "").strip() == creative_group_name:
            return ad_group

    ad_groups = _campaign_ad_groups(campaign)
    if len(ad_groups) == 1:
        return ad_groups[0]
    return None


def _scope_line(
    *,
    scope: AutoVerdictScope,
    report: dict[str, object],
    campaign: dict[str, Any] | None = None,
    ad_group: dict[str, Any] | None = None,
    creative: dict[str, Any] | None = None,
) -> str:
    account = report["account"]

    if scope == "campaign" and campaign is not None:
        parts = [
            "campaign",
            campaign.get("id"),
            campaign.get("name"),
        ]
    elif scope == "ad_group" and campaign is not None and ad_group is not None:
        parts = [
            "ad_group",
            ad_group.get("id"),
            ad_group.get("name"),
            campaign.get("name"),
        ]
    elif scope == "creative" and campaign is not None and creative is not None:
        parts = [
            "creative",
            creative.get("id"),
            creative.get("name"),
            ad_group.get("name") if isinstance(ad_group, dict) else None,
            campaign.get("name"),
        ]
    else:
        parts = [
            "account",
            account.get("account_id"),
            account.get("name"),
        ]

    return "scope|" + "|".join(_format_scalar(part) for part in parts)


def _build_report_context(report: dict[str, object], *, scope_line: str | None = None) -> str:
    account = report["account"]
    summary = report["summary"]

    lines = [
        "fmt|sum/cmp metrics sp,rh,im,cl,ctr,cpm,cpc,rs,cpr as current,previous,delta_pct|grp name|geo|age|gender|aud|sig|pl|dev|sp|im|cl|ctr|rs|rk|crt name|type|sp|im|cl|ctr|rs|rk",
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
    ]
    if scope_line is not None:
        lines.append(scope_line)
    lines.append(
        "sum|"
        + "|".join(
            [
                _format_scalar(summary["primary_result_kind"]),
                _format_scalar(summary["active_campaigns"]),
                _format_scalar(summary["total_campaigns"]),
                _compact_metric_series(summary["metrics"]),
            ]
        )
    )

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
        ad_groups = sorted(campaign.get("ad_groups", []), key=_ad_group_sort_key, reverse=True)
        limited_ad_groups = ad_groups[:_MAX_AD_GROUPS_PER_CAMPAIGN]
        lines.extend(_compact_ad_group(ad_group) for ad_group in limited_ad_groups)

        omitted_ad_group_count = max(0, len(ad_groups) - len(limited_ad_groups))
        if omitted_ad_group_count:
            lines.append(f"more|grp|{_format_scalar(campaign['name'])}|{omitted_ad_group_count}")

        creatives = sorted(campaign["creatives"], key=_creative_sort_key, reverse=True)
        limited_creatives = creatives[:_MAX_CREATIVES_PER_CAMPAIGN]
        lines.extend(_compact_creative(creative) for creative in limited_creatives)

        omitted_creative_count = max(0, len(creatives) - len(limited_creatives))
        if omitted_creative_count:
            lines.append(f"more|crt|{_format_scalar(campaign['name'])}|{omitted_creative_count}")

    return "\n".join(lines)


def build_report_context(report: dict[str, object]) -> str:
    return _build_report_context(report)


def build_scoped_report_context(
    report: dict[str, object],
    *,
    scope: AutoVerdictScope,
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    creative_id: str | None = None,
) -> tuple[str, AutoVerdictScope, dict[str, object]]:
    normalized_scope = str(scope or "account").strip().lower()
    if normalized_scope not in {"account", "campaign", "ad_group", "creative"}:
        normalized_scope = "account"

    if normalized_scope == "campaign":
        campaign = _find_campaign(report, campaign_id)
        if campaign is not None:
            normalized_campaign = _normalize_campaign(campaign)
            scoped_report = _report_base(
                report,
                summary=_build_summary(
                    primary_result_kind=str(normalized_campaign.get("primary_result_kind") or "result"),
                    metrics=normalized_campaign["metrics"],
                    status=str(normalized_campaign.get("status") or ""),
                ),
                campaigns=[normalized_campaign],
            )
            return (
                _build_report_context(
                    scoped_report,
                    scope_line=_scope_line(scope="campaign", report=report, campaign=normalized_campaign),
                ),
                "campaign",
                scoped_report,
            )

    if normalized_scope == "ad_group":
        campaign, ad_group = _find_ad_group(report, campaign_id=campaign_id, ad_group_id=ad_group_id)
        if campaign is not None and ad_group is not None:
            ad_group_metrics = ad_group.get("metrics", {})
            if not isinstance(ad_group_metrics, dict):
                ad_group_metrics = {}
            summary_metrics = _metric_collection_from_entity_metrics(ad_group_metrics)
            result_kind = str(
                ad_group_metrics.get("result_kind")
                or campaign.get("primary_result_kind")
                or report["summary"].get("primary_result_kind")
                or "result"
            )
            scoped_creatives = _creatives_for_ad_group(campaign, str(ad_group.get("id") or ""))
            synthetic_campaign = _normalize_campaign(
                campaign,
                entity_id=str(ad_group.get("id") or campaign.get("id") or "ad_group"),
                name=str(ad_group.get("name") or campaign.get("name") or "Ad group"),
                metrics=summary_metrics,
                result_kind=result_kind,
                ad_groups=[ad_group],
                creatives=scoped_creatives,
            )
            scoped_report = _report_base(
                report,
                summary=_build_summary(
                    primary_result_kind=result_kind,
                    metrics=summary_metrics,
                    status=str(campaign.get("status") or ""),
                ),
                campaigns=[synthetic_campaign],
            )
            return (
                _build_report_context(
                    scoped_report,
                    scope_line=_scope_line(
                        scope="ad_group",
                        report=report,
                        campaign=campaign,
                        ad_group=ad_group,
                    ),
                ),
                "ad_group",
                scoped_report,
            )

        if campaign is not None:
            return build_scoped_report_context(
                report,
                scope="campaign",
                campaign_id=str(campaign.get("id") or ""),
            )

    if normalized_scope == "creative":
        campaign, creative = _find_creative(report, campaign_id=campaign_id, creative_id=creative_id)
        if campaign is not None and creative is not None:
            creative_metrics = creative.get("metrics", {})
            if not isinstance(creative_metrics, dict):
                creative_metrics = {}
            summary_metrics = _metric_collection_from_entity_metrics(creative_metrics)
            result_kind = str(
                creative_metrics.get("result_kind")
                or campaign.get("primary_result_kind")
                or report["summary"].get("primary_result_kind")
                or "result"
            )
            creative_ad_group = _ad_group_for_creative(campaign, creative)
            peer_creatives = _creatives_for_ad_group(campaign, str(creative.get("ad_group_id") or ""))
            if not peer_creatives:
                peer_creatives = [creative]
            elif all(str(item.get("id") or "") != str(creative.get("id") or "") for item in peer_creatives):
                peer_creatives = [creative, *peer_creatives]

            synthetic_campaign = _normalize_campaign(
                campaign,
                entity_id=str(creative.get("id") or campaign.get("id") or "creative"),
                name=str(creative.get("name") or campaign.get("name") or "Creative"),
                metrics=summary_metrics,
                result_kind=result_kind,
                ad_groups=[creative_ad_group] if creative_ad_group is not None else [],
                creatives=peer_creatives,
            )
            scoped_report = _report_base(
                report,
                summary=_build_summary(
                    primary_result_kind=result_kind,
                    metrics=summary_metrics,
                    status=str(campaign.get("status") or ""),
                ),
                campaigns=[synthetic_campaign],
            )
            return (
                _build_report_context(
                    scoped_report,
                    scope_line=_scope_line(
                        scope="creative",
                        report=report,
                        campaign=campaign,
                        ad_group=creative_ad_group,
                        creative=creative,
                    ),
                ),
                "creative",
                scoped_report,
            )

        if ad_group_id:
            fallback_campaign, fallback_ad_group = _find_ad_group(
                report,
                campaign_id=campaign_id,
                ad_group_id=ad_group_id,
            )
            if fallback_campaign is not None and fallback_ad_group is not None:
                return build_scoped_report_context(
                    report,
                    scope="ad_group",
                    campaign_id=str(fallback_campaign.get("id") or ""),
                    ad_group_id=str(fallback_ad_group.get("id") or ""),
                )

        fallback_campaign = campaign or _find_campaign(report, campaign_id)
        if fallback_campaign is not None:
            return build_scoped_report_context(
                report,
                scope="campaign",
                campaign_id=str(fallback_campaign.get("id") or ""),
            )

    scoped_context = _build_report_context(
        report,
        scope_line=_scope_line(scope="account", report=report),
    )
    return scoped_context, "account", report

from __future__ import annotations

import math
import re
from typing import Any

_WHITESPACE_RE = re.compile(r"\s+")

_RESULT_LABELS = {
    "ru": {
        "leads": ("лид", "лида", "лидов"),
        "conversions": ("конверсия", "конверсии", "конверсий"),
        "result": ("результат", "результата", "результатов"),
        "results": ("результат", "результата", "результатов"),
        "default": ("результат", "результата", "результатов"),
    },
    "kz": {
        "leads": "лид",
        "conversions": "конверсия",
        "result": "нәтиже",
        "results": "нәтиже",
        "default": "нәтиже",
    },
    "en": {
        "leads": ("lead", "leads"),
        "conversions": ("conversion", "conversions"),
        "result": ("result", "results"),
        "results": ("result", "results"),
        "default": ("result", "results"),
    },
}

_MESSAGES = {
    "ru": {
        "intro_temporary": "Серверный AI-ответ временно недоступен, поэтому ниже краткий вывод по метрикам.",
        "intro_unconfigured": "Серверный AI-ключ не настроен, поэтому ниже краткий вывод по метрикам.",
        "not_enough_data": "Доступно недостаточно метрик для точного сравнения периодов.",
        "active_campaigns": "Активно кампаний: {active} из {total}.",
        "leader": "Лидер: {name} - {details}.",
        "risk": "Зона внимания: {name} - {details}.",
        "efficiency": "CTR {ctr}{ctr_delta}, CPC {cpc}{cpc_delta}.",
        "spend_clause": "расход составил {value}{delta}",
        "results_clause": "{label} - {value}{delta}",
        "cpr_clause": "цена результата - {value}{delta}",
        "period_prefix": "За {since} - {until} ",
        "shift_budget": "Следующий шаг: сместить часть бюджета из {from_name} в {to_name}, где цена результата заметно лучше.",
        "scale_winner": "Следующий шаг: аккуратно увеличить бюджет на {name} и проконтролировать, сохранится ли текущая цена результата.",
        "refresh_creatives": "Следующий шаг: обновить креативы и оффер в кампаниях с просевшим CTR.",
        "audit_conversion": "Следующий шаг: проверить посадочную страницу и события конверсии, потому что клики растут быстрее результатов.",
        "review_mix": "Следующий шаг: пересмотреть кампании с расходом и слабым результатом, затем перераспределить бюджет.",
        "unnamed_campaign": "Кампания без названия",
        "spend_detail": "расход {value}",
        "results_detail": "{value} {label}",
        "cpr_detail": "цена результата {value}",
    },
    "kz": {
        "intro_temporary": "Серверлік AI жауабы уақытша қолжетімсіз, сондықтан төменде метрикалар бойынша қысқа қорытынды берілді.",
        "intro_unconfigured": "Серверлік AI кілті бапталмаған, сондықтан төменде метрикалар бойынша қысқа қорытынды берілді.",
        "not_enough_data": "Кезеңдерді дәл салыстыруға метрика жеткіліксіз.",
        "active_campaigns": "Белсенді кампаниялар: {active} / {total}.",
        "leader": "Көшбасшы: {name} - {details}.",
        "risk": "Назар аударатын кампания: {name} - {details}.",
        "efficiency": "CTR {ctr}{ctr_delta}, CPC {cpc}{cpc_delta}.",
        "spend_clause": "шығын {value}{delta}",
        "results_clause": "{label} {value}{delta}",
        "cpr_clause": "бір нәтиже құны {value}{delta}",
        "period_prefix": "{since} - {until} аралығында ",
        "shift_budget": "Келесі қадам: нәтиже құны жақсырақ {to_name} кампаниясына {from_name} кампаниясынан бюджеттің бір бөлігін ауыстыру.",
        "scale_winner": "Келесі қадам: {name} кампаниясының бюджетін абайлап өсіріп, нәтиже құны сақталатынын тексеру.",
        "refresh_creatives": "Келесі қадам: CTR төмендеген кампанияларда креатив пен офферді жаңарту.",
        "audit_conversion": "Келесі қадам: кликтер нәтижеден жылдам өсіп жатқандықтан, landing page мен conversion events-ті тексеру.",
        "review_mix": "Келесі қадам: шығыны бар, бірақ әлсіз нәтиже беретін кампанияларды қарап, бюджетті қайта бөлу.",
        "unnamed_campaign": "Атаусыз кампания",
        "spend_detail": "шығын {value}",
        "results_detail": "{value} {label}",
        "cpr_detail": "бір нәтиже құны {value}",
    },
    "en": {
        "intro_temporary": "The server AI summary is temporarily unavailable, so here is a quick metric-based fallback.",
        "intro_unconfigured": "The server AI key is not configured, so here is a quick metric-based fallback.",
        "not_enough_data": "There is not enough metric data for a reliable period comparison.",
        "active_campaigns": "Active campaigns: {active} of {total}.",
        "leader": "Leader: {name} - {details}.",
        "risk": "Watch item: {name} - {details}.",
        "efficiency": "CTR {ctr}{ctr_delta}, CPC {cpc}{cpc_delta}.",
        "spend_clause": "spend was {value}{delta}",
        "results_clause": "{value} {label}{delta}",
        "cpr_clause": "cost per result was {value}{delta}",
        "period_prefix": "For {since} - {until}, ",
        "shift_budget": "Next action: move part of the budget from {from_name} into {to_name}, where cost per result is meaningfully lower.",
        "scale_winner": "Next action: scale {name} gradually and confirm the current cost per result holds.",
        "refresh_creatives": "Next action: refresh creatives and offers in campaigns with a weaker CTR trend.",
        "audit_conversion": "Next action: audit the landing page and conversion tracking because clicks are growing faster than results.",
        "review_mix": "Next action: review campaigns with spend and weak output, then reallocate budget.",
        "unnamed_campaign": "Unnamed campaign",
        "spend_detail": "spend {value}",
        "results_detail": "{value} {label}",
        "cpr_detail": "cost/result {value}",
    },
}


def _normalize_language(language: str) -> str:
    normalized = (language or "ru").strip().lower()
    return normalized if normalized in _MESSAGES else "ru"


def _message_pack(language: str) -> dict[str, str]:
    return _MESSAGES[_normalize_language(language)]


def _result_label(language: str, result_kind: Any, *, value: float | None = None) -> str:
    normalized_language = _normalize_language(language)
    labels = _RESULT_LABELS[normalized_language]
    key = str(result_kind or "").strip().lower()
    label = labels.get(key, labels["default"])

    if normalized_language == "ru":
        if not isinstance(label, tuple):
            return label
        if value is None or not math.isclose(value, round(value), abs_tol=1e-9):
            return label[2]
        count = abs(int(round(value)))
        last_two = count % 100
        last_one = count % 10
        if 11 <= last_two <= 14:
            return label[2]
        if last_one == 1:
            return label[0]
        if 2 <= last_one <= 4:
            return label[1]
        return label[2]

    if normalized_language == "en":
        if not isinstance(label, tuple):
            return label
        if value is not None and math.isclose(abs(value), 1.0, abs_tol=1e-9):
            return label[0]
        return label[1]

    return label if isinstance(label, str) else label[-1]


def _sanitize_name(value: Any, *, fallback: str) -> str:
    text = _WHITESPACE_RE.sub(" ", str(value or "")).strip()
    return text or fallback


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _metric_number(container: dict[str, Any], key: str, field: str = "current") -> float | None:
    metric = container.get(key, {})
    if not isinstance(metric, dict):
        return None
    return _number(metric.get(field))


def _format_number(value: float | None) -> str | None:
    if value is None:
        return None
    rounded = round(value, 2)
    if math.isclose(rounded, round(rounded), abs_tol=1e-9):
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def _format_delta(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(value, 1)
    if math.isclose(rounded, 0.0, abs_tol=1e-9):
        return " (0%)"
    prefix = "+" if rounded > 0 else ""
    text = f"{rounded:.1f}".rstrip("0").rstrip(".")
    return f" ({prefix}{text}%)"


def _format_money(value: float | None, currency: str | None) -> str | None:
    amount = _format_number(value)
    if amount is None:
        return None
    code = _sanitize_name(currency, fallback="").upper()
    return f"{amount} {code}".strip()


def _campaign_detail(
    campaign: dict[str, Any],
    *,
    language: str,
    currency: str | None,
    result_kind: Any,
) -> str:
    pack = _message_pack(language)
    metrics = campaign.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}

    parts: list[str] = []
    raw_result_value = _metric_number(metrics, "results")
    result_value = _format_number(raw_result_value)
    spend_value = _format_money(_metric_number(metrics, "spend"), currency)
    cpr_value = _format_money(_metric_number(metrics, "cost_per_result"), currency)

    if result_value is not None:
        parts.append(
            pack["results_detail"].format(
                value=result_value,
                label=_result_label(language, result_kind, value=raw_result_value),
            )
        )
    if spend_value is not None:
        parts.append(pack["spend_detail"].format(value=spend_value))
    if cpr_value is not None:
        parts.append(pack["cpr_detail"].format(value=cpr_value))

    return ", ".join(parts)


def _best_campaign(campaigns: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid_campaigns = [campaign for campaign in campaigns if isinstance(campaign, dict)]
    if not valid_campaigns:
        return None

    def sort_key(campaign: dict[str, Any]) -> tuple[float, float, float]:
        metrics = campaign.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        results = _metric_number(metrics, "results") or 0.0
        spend = _metric_number(metrics, "spend") or 0.0
        cpr = _metric_number(metrics, "cost_per_result")
        efficiency = 0.0 if cpr is None or cpr <= 0 else 1.0 / cpr
        return (results, efficiency, spend)

    return max(valid_campaigns, key=sort_key)


def _worst_campaign(campaigns: list[dict[str, Any]], *, exclude: dict[str, Any] | None) -> dict[str, Any] | None:
    candidates = [
        campaign
        for campaign in campaigns
        if isinstance(campaign, dict)
        and campaign is not exclude
        and (_metric_number(campaign.get("metrics", {}), "spend") or 0) > 0
    ]
    if not candidates:
        return None

    def sort_key(campaign: dict[str, Any]) -> tuple[float, float, float]:
        metrics = campaign.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        results = _metric_number(metrics, "results") or 0.0
        spend = _metric_number(metrics, "spend") or 0.0
        cpr = _metric_number(metrics, "cost_per_result")
        zero_result_penalty = 1.0 if math.isclose(results, 0.0, abs_tol=1e-9) and spend > 0 else 0.0
        cpr_value = cpr if cpr is not None else (999999.0 if zero_result_penalty else 0.0)
        return (zero_result_penalty, cpr_value, spend - results)

    return max(candidates, key=sort_key)


def _recommendation(
    *,
    language: str,
    summary_metrics: dict[str, Any],
    best_campaign: dict[str, Any] | None,
    worst_campaign: dict[str, Any] | None,
) -> str:
    pack = _message_pack(language)
    results_delta = _metric_number(summary_metrics, "results", "delta_pct")
    cpr_delta = _metric_number(summary_metrics, "cost_per_result", "delta_pct")
    ctr_delta = _metric_number(summary_metrics, "ctr", "delta_pct")
    clicks_delta = _metric_number(summary_metrics, "clicks", "delta_pct")

    if best_campaign is not None and worst_campaign is not None:
        best_name = _sanitize_name(best_campaign.get("name"), fallback=pack["unnamed_campaign"])
        worst_name = _sanitize_name(worst_campaign.get("name"), fallback=pack["unnamed_campaign"])
        best_metrics = best_campaign.get("metrics", {})
        worst_metrics = worst_campaign.get("metrics", {})
        if not isinstance(best_metrics, dict):
            best_metrics = {}
        if not isinstance(worst_metrics, dict):
            worst_metrics = {}
        best_cpr = _metric_number(best_metrics, "cost_per_result")
        worst_cpr = _metric_number(worst_metrics, "cost_per_result")
        worst_results = _metric_number(worst_metrics, "results") or 0.0
        worst_spend = _metric_number(worst_metrics, "spend") or 0.0
        if worst_spend > 0 and (
            math.isclose(worst_results, 0.0, abs_tol=1e-9)
            or (
                best_cpr is not None
                and best_cpr > 0
                and worst_cpr is not None
                and worst_cpr >= best_cpr * 1.35
            )
        ):
            return pack["shift_budget"].format(from_name=worst_name, to_name=best_name)

    if best_campaign is not None and (results_delta or 0) >= 15 and (cpr_delta is None or cpr_delta <= 5):
        best_name = _sanitize_name(best_campaign.get("name"), fallback=pack["unnamed_campaign"])
        return pack["scale_winner"].format(name=best_name)

    if ctr_delta is not None and ctr_delta <= -10:
        return pack["refresh_creatives"]

    if clicks_delta is not None and clicks_delta >= 10 and (results_delta is None or results_delta <= 0):
        return pack["audit_conversion"]

    return pack["review_mix"]


def build_auto_verdict_fallback_text(
    report: dict[str, Any],
    *,
    language: str,
    reason: str = "temporary_error",
) -> str:
    normalized_language = _normalize_language(language)
    pack = _message_pack(normalized_language)
    account = report.get("account", {})
    periods = report.get("periods", {})
    summary = report.get("summary", {})
    campaigns = report.get("campaigns", [])

    if not isinstance(account, dict):
        account = {}
    if not isinstance(periods, dict):
        periods = {}
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(campaigns, list):
        campaigns = []

    current_period = periods.get("current", {})
    if not isinstance(current_period, dict):
        current_period = {}
    summary_metrics = summary.get("metrics", {})
    if not isinstance(summary_metrics, dict):
        summary_metrics = {}

    currency = account.get("currency")
    primary_result_kind = summary.get("primary_result_kind")
    intro = pack["intro_unconfigured"] if reason == "not_configured" else pack["intro_temporary"]

    spend_value = _format_money(_metric_number(summary_metrics, "spend"), currency)
    raw_results_value = _metric_number(summary_metrics, "results")
    results_value = _format_number(raw_results_value)
    cpr_value = _format_money(_metric_number(summary_metrics, "cost_per_result"), currency)
    since = _sanitize_name(current_period.get("since"), fallback="?")
    until = _sanitize_name(current_period.get("until"), fallback="?")

    metric_clauses: list[str] = []
    if spend_value is not None:
        metric_clauses.append(
            pack["spend_clause"].format(
                value=spend_value,
                delta=_format_delta(_metric_number(summary_metrics, "spend", "delta_pct")),
            )
        )
    if results_value is not None:
        metric_clauses.append(
            pack["results_clause"].format(
                label=_result_label(normalized_language, primary_result_kind, value=raw_results_value),
                value=results_value,
                delta=_format_delta(_metric_number(summary_metrics, "results", "delta_pct")),
            )
        )
    if cpr_value is not None:
        metric_clauses.append(
            pack["cpr_clause"].format(
                value=cpr_value,
                delta=_format_delta(_metric_number(summary_metrics, "cost_per_result", "delta_pct")),
            )
        )

    if metric_clauses:
        comparison_sentence = pack["period_prefix"].format(since=since, until=until) + ", ".join(metric_clauses) + "."
    else:
        comparison_sentence = pack["not_enough_data"]

    best_campaign = _best_campaign(campaigns)
    worst_campaign = _worst_campaign(campaigns, exclude=best_campaign)
    recommendation = _recommendation(
        language=normalized_language,
        summary_metrics=summary_metrics,
        best_campaign=best_campaign,
        worst_campaign=worst_campaign,
    )

    bullets: list[str] = []
    active_campaigns = summary.get("active_campaigns")
    total_campaigns = summary.get("total_campaigns")
    if active_campaigns is not None and total_campaigns is not None:
        bullets.append(f"- {pack['active_campaigns'].format(active=active_campaigns, total=total_campaigns)}")

    if best_campaign is not None:
        best_name = _sanitize_name(best_campaign.get("name"), fallback=pack["unnamed_campaign"])
        best_details = _campaign_detail(
            best_campaign,
            language=normalized_language,
            currency=currency if isinstance(currency, str) else None,
            result_kind=best_campaign.get("primary_result_kind", primary_result_kind),
        )
        if best_details:
            bullets.append(f"- {pack['leader'].format(name=best_name, details=best_details)}")

    if worst_campaign is not None:
        worst_name = _sanitize_name(worst_campaign.get("name"), fallback=pack["unnamed_campaign"])
        worst_details = _campaign_detail(
            worst_campaign,
            language=normalized_language,
            currency=currency if isinstance(currency, str) else None,
            result_kind=worst_campaign.get("primary_result_kind", primary_result_kind),
        )
        if worst_details:
            bullets.append(f"- {pack['risk'].format(name=worst_name, details=worst_details)}")

    ctr_value = _format_number(_metric_number(summary_metrics, "ctr"))
    cpc_value = _format_money(_metric_number(summary_metrics, "cpc"), currency)
    if ctr_value is not None and cpc_value is not None:
        bullets.append(
            "- "
            + pack["efficiency"].format(
                ctr=ctr_value,
                ctr_delta=_format_delta(_metric_number(summary_metrics, "ctr", "delta_pct")),
                cpc=cpc_value,
                cpc_delta=_format_delta(_metric_number(summary_metrics, "cpc", "delta_pct")),
            )
        )

    if bullets:
        return f"{intro} {comparison_sentence} {recommendation}\n\n" + "\n".join(bullets)

    return f"{intro} {comparison_sentence} {recommendation}"

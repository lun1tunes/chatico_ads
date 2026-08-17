from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from time import monotonic
from urllib.parse import parse_qs, urlsplit

from ..interfaces.services import IEncryptionService, IMetaGraphClient, IPublicCreativePreviewClient
from ..models.meta_ad_account import MetaAdAccount
from ..repositories.meta_ad_account import MetaAdAccountRepository
from ..repositories.meta_report_snapshot import MetaReportSnapshotRepository
from ..utils.time import utcnow
from ..utils.reporting import build_metric, extract_primary_result, group_ads_by_campaign, to_float

logger = logging.getLogger(__name__)

_REACH_ESTIMATE_CONCURRENCY = 4


class MetaReportError(Exception):
    pass


class MetaAdAccountNotFoundError(MetaReportError):
    pass


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _resolve_creative_image_url(creative: dict[str, object]) -> str | None:
    story_payloads = _creative_story_payloads(creative)
    video_data = story_payloads.get("video_data", {})
    link_data = story_payloads.get("link_data", {})
    photo_data = story_payloads.get("photo_data", {})
    template_data = story_payloads.get("template_data", {})

    # Inference from Meta AdCreative docs: non-image creatives often surface a better preview through
    # object_story_spec.* than through the generic thumbnail_url field.
    return _first_non_empty(
        creative.get("image_url"),
        video_data.get("image_url"),
        link_data.get("picture"),
        photo_data.get("image_url"),
        template_data.get("picture"),
        creative.get("thumbnail_url"),
    )


def _creative_story_payloads(creative: dict[str, object]) -> dict[str, dict[str, object]]:
    object_story_spec = creative.get("object_story_spec")
    story = object_story_spec if isinstance(object_story_spec, dict) else {}
    payloads: dict[str, dict[str, object]] = {}
    for key in ("video_data", "link_data", "photo_data", "template_data", "text_data"):
        value = story.get(key)
        if isinstance(value, dict):
            payloads[key] = value
    return payloads


def _resolve_creative_primary_text(creative: dict[str, object]) -> str | None:
    values: list[object] = []
    for payload in _creative_story_payloads(creative).values():
        values.extend(
            [
                payload.get("message"),
                payload.get("text"),
                payload.get("body"),
            ]
        )
    return _first_non_empty(*values)


def _resolve_creative_headline(creative: dict[str, object]) -> str | None:
    values: list[object] = []
    for payload in _creative_story_payloads(creative).values():
        values.extend(
            [
                payload.get("name"),
                payload.get("title"),
                payload.get("headline"),
            ]
        )
    return _first_non_empty(*values)


def _resolve_creative_call_to_action(creative: dict[str, object]) -> str | None:
    payloads = _creative_story_payloads(creative)
    for payload in payloads.values():
        direct_type = _first_non_empty(payload.get("call_to_action_type"), payload.get("cta_text"))
        if direct_type:
            return direct_type

        call_to_action = payload.get("call_to_action")
        if isinstance(call_to_action, dict):
            nested_type = _first_non_empty(call_to_action.get("type"))
            if nested_type:
                return nested_type
    return None


def _resolve_creative_destination_url(creative: dict[str, object]) -> str | None:
    payloads = _creative_story_payloads(creative)
    for payload in payloads.values():
        call_to_action = payload.get("call_to_action")
        if isinstance(call_to_action, dict):
            cta_value = call_to_action.get("value")
            if isinstance(cta_value, dict):
                nested_url = _first_non_empty(
                    cta_value.get("link"),
                    cta_value.get("url"),
                    cta_value.get("website_url"),
                )
                if nested_url:
                    return nested_url

        direct_url = _first_non_empty(payload.get("link"), payload.get("url"), payload.get("website_url"))
        if direct_url:
            return direct_url
    return None


def _looks_like_low_res_preview(url: str | None) -> bool:
    if not url:
        return False

    stp_values = parse_qs(urlsplit(url).query).get("stp", [])
    stp = stp_values[0] if stp_values else ""
    low_res_tokens = ("p64x64", "p96x96", "p128x128")
    return any(token in stp for token in low_res_tokens)


def _dedupe_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        marker = normalized.casefold()
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(normalized)

    return unique


_TARGETING_LABEL_RU: dict[str, str] = {
    "small business": "Малый бизнес",
    "small and medium enterprises": "Малый и средний бизнес",
    "small and medium-sized enterprises": "Малый и средний бизнес",
    "small & medium enterprises": "Малый и средний бизнес",
    "sme": "Малый и средний бизнес",
    "smes": "Малый и средний бизнес",
    "entrepreneurship": "Предпринимательство",
    "marketing": "Маркетинг",
    "individual entrepreneur": "Индивидуальный предприниматель",
    "individual entrepreneur or business": "Индивидуальный предприниматель или Бизнес",
    "business owner": "Владелец бизнеса",
    "small business owners": "Владельцы малых предприятий",
    "small business owner": "Владелец малого предприятия",
    "almaty": "Алматы",
    "tselinograd": "Целиноград",
    "astana": "Астана",
    "nur-sultan": "Нур-Султан",
}


def _localize_targeting_label(value: str) -> str:
    key = " ".join(value.replace("‐", "-").replace("–", "-").replace("—", "-").split()).casefold()
    return _TARGETING_LABEL_RU.get(key, value)


def _extract_named_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    values: list[str] = []
    for item in value:
        if isinstance(item, dict):
            label = _first_non_empty(item.get("name"), item.get("label"), item.get("key"), item.get("id"))
            if label:
                values.append(_localize_targeting_label(label))
        elif item is not None:
            label = str(item).strip()
            if label:
                values.append(_localize_targeting_label(label))

    return _dedupe_strings(values)


def _extract_geo_summary(targeting: dict[str, object]) -> str | None:
    geo_locations = targeting.get("geo_locations")
    if not isinstance(geo_locations, dict):
        return None

    geo_values: list[str] = []
    countries = geo_locations.get("countries")
    if isinstance(countries, list):
        geo_values.extend(str(item).strip() for item in countries if str(item).strip())

    for key in ("country_groups", "regions", "cities", "zips"):
        geo_values.extend(_extract_named_values(geo_locations.get(key)))

    unique_values = _dedupe_strings(geo_values)
    return ", ".join(unique_values) or None


def _format_age_summary(targeting: dict[str, object]) -> str | None:
    age_min = _optional_int(targeting.get("age_min"))
    age_max = _optional_int(targeting.get("age_max"))

    if age_min is None and age_max is None:
        return None
    if age_min is not None and age_max is not None:
        return f"{age_min}-{age_max}"
    if age_min is not None:
        return f"{age_min}+"
    return f"up to {age_max}"


def _format_gender_summary(targeting: dict[str, object]) -> str | None:
    genders = targeting.get("genders")
    if not isinstance(genders, list):
        return None

    labels = []
    for item in genders:
        code = _optional_int(item)
        if code == 1:
            labels.append("male")
        elif code == 2:
            labels.append("female")

    unique_labels = _dedupe_strings(labels)
    if len(unique_labels) >= 2:
        return None
    return ", ".join(unique_labels) or None


def _extract_flexible_spec_signals(targeting: dict[str, object]) -> list[str]:
    flexible_spec = targeting.get("flexible_spec")
    if not isinstance(flexible_spec, list):
        return []

    values: list[str] = []
    for item in flexible_spec:
        if not isinstance(item, dict):
            continue
        for nested in item.values():
            values.extend(_extract_named_values(nested))

    return _dedupe_strings(values)


def _extract_flexible_spec_named(targeting: dict[str, object], *keys: str) -> list[str]:
    flexible_spec = targeting.get("flexible_spec")
    if not isinstance(flexible_spec, list):
        return []

    values: list[str] = []
    for item in flexible_spec:
        if not isinstance(item, dict):
            continue
        for key in keys:
            values.extend(_extract_named_values(item.get(key)))

    return _dedupe_strings(values)


def _extract_signal_summary(targeting: dict[str, object]) -> str | None:
    signals = _dedupe_strings(
        [
            *_extract_named_values(targeting.get("interests")),
            *_extract_named_values(targeting.get("behaviors")),
            *_extract_named_values(targeting.get("work_positions")),
            *_extract_flexible_spec_signals(targeting),
        ]
    )
    return ", ".join(signals) or None


def _audience_name_suggests_lookalike(name: str) -> bool:
    lowered = name.casefold()
    return any(token in lowered for token in ("lookalike", "lal", "похож", "ұқсас"))


def _audience_name_suggests_retargeting(name: str) -> bool:
    lowered = name.casefold()
    markers = (
        "retarget",
        "remarket",
        "visitor",
        "website",
        "purchase",
        "checkout",
        "cart",
        "engage",
        "ретаргет",
        "посет",
        "клиент",
    )
    return any(token in lowered for token in markers)


def _targeting_has_lookalike_fields(targeting: dict[str, object]) -> bool:
    for key in ("lookalike_spec", "lookalike", "lookalikes"):
        value = targeting.get(key)
        if value:
            return True
    return False


_PLACEMENT_POSITION_CATALOGS: dict[str, tuple[str, ...]] = {
    "facebook": (
        "feed",
        "right_hand_column",
        "marketplace",
        "video_feeds",
        "story",
        "search",
        "instream_video",
        "facebook_reels",
        "profile_feed",
        "notification",
    ),
    "instagram": (
        "stream",
        "story",
        "explore",
        "explore_home",
        "reels",
        "profile_feed",
        "ig_search",
        "profile_reels",
    ),
    "messenger": (
        "messenger_home",
        "sponsored_messages",
        "story",
    ),
    "audience_network": (
        "classic",
        "instream_video",
        "rewarded_video",
    ),
    "whatsapp": ("status",),
}

_PLACEMENT_POSITION_KEYS: tuple[tuple[str, str], ...] = (
    ("facebook_positions", "facebook"),
    ("instagram_positions", "instagram"),
    ("messenger_positions", "messenger"),
    ("audience_network_positions", "audience_network"),
    ("whatsapp_positions", "whatsapp"),
)


def _placement_key(platform: str, position: str) -> str:
    return f"{platform}:{position}"


def _extract_placements_breakdown(targeting: dict[str, object]) -> dict[str, list[str]]:
    explicit_by_platform: dict[str, list[str]] = {}
    for key, platform in _PLACEMENT_POSITION_KEYS:
        values = _extract_named_values(targeting.get(key))
        if values:
            explicit_by_platform[platform] = values

    publisher_platforms = {
        value.casefold()
        for value in _extract_named_values(targeting.get("publisher_platforms"))
    }

    included: list[str] = []
    excluded: list[str] = []

    if explicit_by_platform:
        active_platforms = set(explicit_by_platform) | {
            platform
            for platform in _PLACEMENT_POSITION_CATALOGS
            if platform in publisher_platforms
        }
        for platform, catalog in _PLACEMENT_POSITION_CATALOGS.items():
            selected = {
                value.casefold()
                for value in explicit_by_platform.get(platform, [])
            }
            if platform in explicit_by_platform:
                for position in catalog:
                    key = _placement_key(platform, position)
                    if position.casefold() in selected:
                        included.append(key)
                    else:
                        excluded.append(key)
                for position in explicit_by_platform[platform]:
                    marker = position.casefold()
                    if marker not in {item.casefold() for item in catalog}:
                        included.append(_placement_key(platform, position))
            elif platform in active_platforms:
                included.extend(_placement_key(platform, position) for position in catalog)
            else:
                excluded.extend(_placement_key(platform, position) for position in catalog)
    elif publisher_platforms:
        for platform, catalog in _PLACEMENT_POSITION_CATALOGS.items():
            keys = [_placement_key(platform, position) for position in catalog]
            if platform in publisher_platforms:
                included.extend(keys)
            else:
                excluded.extend(keys)

    return {
        "included": _dedupe_strings(included),
        "excluded": _dedupe_strings(excluded),
    }


def _extract_targeting_details(targeting: dict[str, object]) -> dict[str, object]:
    interests = _dedupe_strings(
        [
            *_extract_named_values(targeting.get("interests")),
            *_extract_flexible_spec_named(targeting, "interests"),
        ]
    )
    behaviors = _dedupe_strings(
        [
            *_extract_named_values(targeting.get("behaviors")),
            *_extract_flexible_spec_named(targeting, "behaviors", "industry", "life_events"),
        ]
    )
    job_titles = _dedupe_strings(
        [
            *_extract_named_values(targeting.get("work_positions")),
            *_extract_flexible_spec_named(targeting, "work_positions"),
        ]
    )
    custom_audiences = _extract_named_values(targeting.get("custom_audiences"))
    excluded_audiences = _extract_named_values(targeting.get("excluded_custom_audiences"))
    audience_names = [*custom_audiences, *excluded_audiences]

    lookalike = _targeting_has_lookalike_fields(targeting) or any(
        _audience_name_suggests_lookalike(name) for name in audience_names
    )
    retargeting = (not lookalike) and any(
        _audience_name_suggests_retargeting(name) for name in audience_names
    )

    return {
        "interests": interests,
        "behaviors": behaviors,
        "job_titles": job_titles,
        "custom_audiences": custom_audiences,
        "lookalike": lookalike,
        "retargeting": retargeting,
        "placements": _extract_placements_breakdown(targeting),
    }


def _extract_audience_summary(targeting: dict[str, object]) -> str | None:
    included = _extract_named_values(targeting.get("custom_audiences"))
    excluded = _extract_named_values(targeting.get("excluded_custom_audiences"))

    parts: list[str] = []
    if included:
        parts.append(f"incl:{', '.join(included)}")
    if excluded:
        parts.append(f"excl:{', '.join(excluded)}")
    return " ".join(parts) or None


def _extract_placement_summary(targeting: dict[str, object]) -> str | None:
    placements: list[str] = []
    for key, prefix in _PLACEMENT_POSITION_KEYS:
        values = _extract_named_values(targeting.get(key))
        placements.extend(f"{prefix}:{value}" for value in values)

    if placements:
        return ", ".join(_dedupe_strings(placements))

    publisher_platforms = _extract_named_values(targeting.get("publisher_platforms"))
    if publisher_platforms:
        return ", ".join(publisher_platforms)

    return None


def _extract_device_summary(targeting: dict[str, object]) -> str | None:
    devices = _extract_named_values(targeting.get("device_platforms"))
    return ", ".join(devices) or None


def _targeting_has_geo_for_reach(targeting: dict[str, object]) -> bool:
    geo = targeting.get("geo_locations")
    if not isinstance(geo, dict):
        return False
    countries = geo.get("countries")
    if isinstance(countries, list) and any(isinstance(item, str) and item.strip() for item in countries):
        return True
    country_groups = geo.get("country_groups")
    if isinstance(country_groups, list) and country_groups:
        return True
    regions = geo.get("regions")
    cities = geo.get("cities")
    if (isinstance(regions, list) and regions) or (isinstance(cities, list) and cities):
        return True
    return False


def _format_audience_reach_bounds(lower: object, upper: object) -> str | None:
    try:
        lower_value = int(float(str(lower)))
        upper_value = int(float(str(upper)))
    except (TypeError, ValueError):
        return None
    # Meta returns -1 when estimate is unavailable for some custom audiences.
    if lower_value < 0 or upper_value < 0:
        return None
    if lower_value == 0 and upper_value == 0:
        return None

    def _fmt(value: int) -> str:
        return f"{value:,}".replace(",", " ")

    if lower_value == upper_value:
        return _fmt(lower_value)
    low, high = sorted((lower_value, upper_value))
    return f"{_fmt(low)} – {_fmt(high)}"


def _extract_reach_bounds(payload: dict[str, object]) -> tuple[object, object] | None:
    lower = payload.get("users_lower_bound")
    upper = payload.get("users_upper_bound")
    if lower is not None and upper is not None:
        return lower, upper
    estimate = payload.get("estimate_mau_lower_bound"), payload.get("estimate_mau_upper_bound")
    if estimate[0] is not None and estimate[1] is not None:
        return estimate
    return None


def _normalize_targeting(
    targeting_spec: object,
    *,
    audience_reach: str | None = None,
) -> dict[str, object]:
    targeting = targeting_spec if isinstance(targeting_spec, dict) else {}
    normalized: dict[str, object] = {
        "geo": _extract_geo_summary(targeting),
        "age": _format_age_summary(targeting),
        "gender": _format_gender_summary(targeting),
        "audience": _extract_audience_summary(targeting),
        "signal": _extract_signal_summary(targeting),
        "placement": _extract_placement_summary(targeting),
        "device": _extract_device_summary(targeting),
        "details": _extract_targeting_details(targeting),
        "audience_reach": audience_reach,
    }

    summary_parts = [
        f"geo={normalized['geo']}" if normalized["geo"] else None,
        f"age={normalized['age']}" if normalized["age"] else None,
        f"gender={normalized['gender']}" if normalized["gender"] else None,
        f"aud={normalized['audience']}" if normalized["audience"] else None,
        f"sig={normalized['signal']}" if normalized["signal"] else None,
        f"pl={normalized['placement']}" if normalized["placement"] else None,
        f"dev={normalized['device']}" if normalized["device"] else None,
    ]
    normalized["summary"] = "; ".join(part for part in summary_parts if part) or None
    return normalized


def _merge_action_totals(action_totals: dict[str, int], actions: object) -> None:
    if not isinstance(actions, list):
        return

    for item in actions:
        if not isinstance(item, dict):
            continue
        action_type = _optional_string(item.get("action_type"))
        if not action_type:
            continue
        action_totals[action_type] = action_totals.get(action_type, 0) + int(to_float(item.get("value")))


def _serialize_action_totals(action_totals: dict[str, int]) -> list[dict[str, object]]:
    return [{"action_type": key, "value": value} for key, value in action_totals.items()]


def _build_ad_group_metrics_map(ad_insights: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}

    for insight in ad_insights:
        ad_group_id = _optional_string(insight.get("adset_id"))
        if not ad_group_id:
            continue

        grouped.setdefault(
            ad_group_id,
            {
                "id": ad_group_id,
                "campaign_id": _optional_string(insight.get("campaign_id")),
                "name": _optional_string(insight.get("adset_name")),
                "spend": 0.0,
                "impressions": 0,
                "clicks": 0,
                "action_totals": {},
            },
        )
        group = grouped[ad_group_id]
        group["campaign_id"] = group.get("campaign_id") or _optional_string(insight.get("campaign_id"))
        group["name"] = group.get("name") or _optional_string(insight.get("adset_name"))
        group["spend"] = float(group.get("spend") or 0) + to_float(insight.get("spend"))
        group["impressions"] = int(group.get("impressions") or 0) + int(to_float(insight.get("impressions")))
        group["clicks"] = int(group.get("clicks") or 0) + int(to_float(insight.get("clicks")))
        _merge_action_totals(group["action_totals"], insight.get("actions"))

    return grouped


def _ad_group_sort_key(ad_group: dict[str, object]) -> tuple[float, float, str]:
    metrics = ad_group.get("metrics", {})
    return (
        float(metrics.get("spend") or 0),
        float(metrics.get("results") or 0),
        str(ad_group.get("name") or ""),
    )


class MetaReportService:
    def __init__(
        self,
        *,
        meta_client: IMetaGraphClient,
        encryption_service: IEncryptionService,
        preview_client: IPublicCreativePreviewClient | None = None,
        cache_ttl_seconds: int = 45,
        snapshot_cache_ttl_seconds: int = 300,
    ) -> None:
        self.meta_client = meta_client
        self.encryption_service = encryption_service
        self.preview_client = preview_client
        self.cache_ttl_seconds = max(0, int(cache_ttl_seconds))
        self.snapshot_cache_ttl_seconds = max(0, int(snapshot_cache_ttl_seconds))
        self._cache: dict[str, tuple[float, dict[str, object]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def build_report(
        self,
        *,
        account_repo: MetaAdAccountRepository,
        snapshot_repo: MetaReportSnapshotRepository,
        user_id: str,
        external_account_id: str,
        requested_days: int,
        periods: dict[str, dict[str, str]],
        force_refresh: bool = False,
    ) -> dict[str, object]:
        account = await account_repo.get_for_user(user_id=user_id, external_id=external_account_id)
        if account is None:
            raise MetaAdAccountNotFoundError("Meta ad account not found")

        cache_key = self._cache_key(
            user_id=user_id,
            meta_ad_account_id=account.id,
            periods=periods,
        )
        lock = self._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            if not force_refresh:
                cached_report = self._get_cached_report(cache_key)
                if cached_report is not None:
                    return cached_report

                current_since, current_until, previous_since, previous_until = self._parse_period_dates(periods)
                snapshot = await snapshot_repo.get_latest_by_account_and_periods(
                    meta_ad_account_id=account.id,
                    current_since=current_since,
                    current_until=current_until,
                    previous_since=previous_since,
                    previous_until=previous_until,
                    now=utcnow(),
                )
                if snapshot is not None:
                    self._store_cached_report(cache_key, snapshot.payload)
                    return deepcopy(snapshot.payload)

            current_since, current_until, previous_since, previous_until = self._parse_period_dates(periods)
            report = await self._build_report_payload(
                account=account,
                periods=periods,
            )
            fetched_at = utcnow()
            account.last_synced_at = fetched_at
            if self.snapshot_cache_ttl_seconds > 0:
                await snapshot_repo.upsert_snapshot(
                    meta_ad_account_id=account.id,
                    requested_days=requested_days,
                    current_since=current_since,
                    current_until=current_until,
                    previous_since=previous_since,
                    previous_until=previous_until,
                    payload=report,
                    source_fetched_at=fetched_at,
                    expires_at=fetched_at + timedelta(seconds=self.snapshot_cache_ttl_seconds),
                )
            self._store_cached_report(cache_key, report)
            return deepcopy(report)

    def _cache_key(self, *, user_id: str, meta_ad_account_id: str, periods: dict[str, dict[str, str]]) -> str:
        current_since, current_until, previous_since, previous_until = self._parse_period_dates(periods)
        return (
            f"{user_id}:{meta_ad_account_id}:"
            f"{current_since.isoformat()}:{current_until.isoformat()}:"
            f"{previous_since.isoformat()}:{previous_until.isoformat()}"
        )

    def _parse_period_dates(self, periods: dict[str, dict[str, str]]) -> tuple[date, date, date, date]:
        current = periods["current"]
        previous = periods["previous"]
        return (
            date.fromisoformat(current["since"]),
            date.fromisoformat(current["until"]),
            date.fromisoformat(previous["since"]),
            date.fromisoformat(previous["until"]),
        )

    def _get_cached_report(self, cache_key: str) -> dict[str, object] | None:
        if self.cache_ttl_seconds <= 0:
            return None

        cache_entry = self._cache.get(cache_key)
        if cache_entry is None:
            return None

        expires_at, payload = cache_entry
        if expires_at <= monotonic():
            self._cache.pop(cache_key, None)
            return None
        return deepcopy(payload)

    def _store_cached_report(self, cache_key: str, report: dict[str, object]) -> None:
        if self.cache_ttl_seconds <= 0:
            return
        self._cache[cache_key] = (monotonic() + self.cache_ttl_seconds, deepcopy(report))

    def clear_user_cache(self, *, user_id: str) -> None:
        cache_prefix = f"{user_id}:"
        for cache_key in [key for key in self._cache if key.startswith(cache_prefix)]:
            self._cache.pop(cache_key, None)
        for cache_key in [key for key in self._locks if key.startswith(cache_prefix)]:
            self._locks.pop(cache_key, None)

    async def _resolve_creative_preview(self, creative: dict[str, object]) -> str | None:
        preferred_url = _resolve_creative_image_url(creative)
        if preferred_url and not _looks_like_low_res_preview(preferred_url):
            return preferred_url

        if self.preview_client is None:
            return preferred_url

        permalink_url = creative.get("instagram_permalink_url")
        if isinstance(permalink_url, str) and permalink_url.strip():
            fallback_url = await self.preview_client.resolve_instagram_permalink_preview(permalink_url=permalink_url)
            if fallback_url:
                return fallback_url

        return preferred_url

    async def _build_creative_payload(
        self,
        *,
        ad: dict[str, object],
        insight: dict[str, object],
    ) -> dict[str, object]:
        creative = ad.get("creative") or {}
        ad_result_kind, ad_results = extract_primary_result(insight.get("actions"))
        return {
            "id": str(ad.get("id")),
            "name": ad.get("name"),
            "object_type": creative.get("object_type") or "ad",
            "thumbnail_url": creative.get("thumbnail_url"),
            "image_url": await self._resolve_creative_preview(creative),
            "status": _optional_string(ad.get("effective_status")) or _optional_string(ad.get("status")),
            "primary_text": _resolve_creative_primary_text(creative),
            "headline": _resolve_creative_headline(creative),
            "call_to_action": _resolve_creative_call_to_action(creative),
            "destination_url": _resolve_creative_destination_url(creative),
            "source_url": _optional_string(creative.get("instagram_permalink_url")),
            "ad_group_id": _optional_string(insight.get("adset_id")) or _optional_string(ad.get("adset_id")),
            "ad_group_name": _optional_string(insight.get("adset_name")),
            "metrics": {
                "spend": to_float(insight.get("spend")),
                "impressions": int(to_float(insight.get("impressions"))),
                "clicks": int(to_float(insight.get("clicks"))),
                "ctr": to_float(insight.get("ctr")),
                "results": ad_results,
                "result_kind": ad_result_kind,
            },
        }

    async def _resolve_audience_reach_by_ad_set(
        self,
        *,
        account_id: str,
        access_token: str,
        ad_sets: list[dict[str, object]],
    ) -> dict[str, str]:
        """Map ad set id → formatted Estimated Audience Size via /reachestimate."""
        unique_targeting: dict[str, dict[str, object]] = {}
        ad_set_to_key: dict[str, str] = {}

        for ad_set in ad_sets:
            ad_set_id = _optional_string(ad_set.get("id"))
            targeting = ad_set.get("targeting")
            if not ad_set_id or not isinstance(targeting, dict) or not _targeting_has_geo_for_reach(targeting):
                continue
            cache_key = json.dumps(targeting, sort_keys=True, ensure_ascii=False, default=str)
            ad_set_to_key[ad_set_id] = cache_key
            unique_targeting.setdefault(cache_key, targeting)

        if not unique_targeting:
            return {}

        semaphore = asyncio.Semaphore(_REACH_ESTIMATE_CONCURRENCY)

        async def _estimate_key(cache_key: str, targeting: dict[str, object]) -> tuple[str, str | None]:
            async with semaphore:
                try:
                    payload = await self.meta_client.get_reach_estimate(
                        account_id=account_id,
                        access_token=access_token,
                        targeting_spec=targeting,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Failed to fetch Meta reachestimate")
                    return cache_key, None

            if not isinstance(payload, dict):
                return cache_key, None
            bounds = _extract_reach_bounds(payload)
            if bounds is None:
                return cache_key, None
            return cache_key, _format_audience_reach_bounds(bounds[0], bounds[1])

        estimated = await asyncio.gather(
            *(_estimate_key(cache_key, targeting) for cache_key, targeting in unique_targeting.items())
        )
        reach_by_key = {cache_key: reach for cache_key, reach in estimated if reach}
        return {
            ad_set_id: reach_by_key[cache_key]
            for ad_set_id, cache_key in ad_set_to_key.items()
            if cache_key in reach_by_key
        }

    async def _build_report_payload(
        self,
        *,
        account: MetaAdAccount,
        periods: dict[str, dict[str, str]],
    ) -> dict[str, object]:
        access_token = self.encryption_service.decrypt(account.connection.access_token_encrypted)
        current = periods["current"]
        previous = periods["previous"]

        (
            account_info,
            campaigns,
            ad_sets,
            current_account_insights,
            previous_account_insights,
            current_account_daily_insights,
            previous_account_daily_insights,
            current_campaign_insights,
            previous_campaign_insights,
            ads,
            ad_insights,
        ) = await asyncio.gather(
            self.meta_client.get_ad_account(account_id=account.external_id, access_token=access_token),
            self.meta_client.list_campaigns(account_id=account.external_id, access_token=access_token),
            self.meta_client.list_ad_sets(account_id=account.external_id, access_token=access_token),
            self.meta_client.get_account_insights(
                account_id=account.external_id,
                access_token=access_token,
                since=current["since"],
                until=current["until"],
            ),
            self.meta_client.get_account_insights(
                account_id=account.external_id,
                access_token=access_token,
                since=previous["since"],
                until=previous["until"],
            ),
            self.meta_client.get_account_daily_insights(
                account_id=account.external_id,
                access_token=access_token,
                since=current["since"],
                until=current["until"],
            ),
            self.meta_client.get_account_daily_insights(
                account_id=account.external_id,
                access_token=access_token,
                since=previous["since"],
                until=previous["until"],
            ),
            self.meta_client.get_campaign_insights(
                account_id=account.external_id,
                access_token=access_token,
                since=current["since"],
                until=current["until"],
            ),
            self.meta_client.get_campaign_insights(
                account_id=account.external_id,
                access_token=access_token,
                since=previous["since"],
                until=previous["until"],
            ),
            self.meta_client.list_ads(account_id=account.external_id, access_token=access_token),
            self.meta_client.get_ad_insights(
                account_id=account.external_id,
                access_token=access_token,
                since=current["since"],
                until=current["until"],
            ),
        )

        current_campaign_map = {str(item.get("campaign_id")): item for item in current_campaign_insights}
        previous_campaign_map = {str(item.get("campaign_id")): item for item in previous_campaign_insights}
        ad_insight_map = {str(item.get("ad_id")): item for item in ad_insights}
        ads_by_campaign = group_ads_by_campaign(ads)
        ad_sets_by_id = {str(item.get("id")): item for item in ad_sets}
        ad_set_ids_by_campaign: dict[str, set[str]] = defaultdict(set)
        for ad_set in ad_sets:
            campaign_id = _optional_string(ad_set.get("campaign_id"))
            ad_set_id = _optional_string(ad_set.get("id"))
            if campaign_id and ad_set_id:
                ad_set_ids_by_campaign[campaign_id].add(ad_set_id)
        ad_group_metrics_map = _build_ad_group_metrics_map(ad_insights)
        for ad_group_id, metrics in ad_group_metrics_map.items():
            campaign_id = _optional_string(metrics.get("campaign_id"))
            if campaign_id:
                ad_set_ids_by_campaign[campaign_id].add(ad_group_id)

        audience_reach_by_ad_set = await self._resolve_audience_reach_by_ad_set(
            account_id=account.external_id,
            access_token=access_token,
            ad_sets=ad_sets,
        )

        current_result_kind, current_result_count = extract_primary_result(
            current_account_insights.get("actions") if current_account_insights else None
        )
        previous_result_kind, previous_result_count = extract_primary_result(
            previous_account_insights.get("actions") if previous_account_insights else None
        )
        result_kind = current_result_kind if current_result_count else previous_result_kind

        current_spend = to_float(current_account_insights.get("spend") if current_account_insights else 0)
        previous_spend = to_float(previous_account_insights.get("spend") if previous_account_insights else 0)

        current_clicks = int(to_float(current_account_insights.get("clicks") if current_account_insights else 0))
        previous_clicks = int(to_float(previous_account_insights.get("clicks") if previous_account_insights else 0))

        current_cpc = (current_spend / current_clicks) if current_clicks else None
        previous_cpc = (previous_spend / previous_clicks) if previous_clicks else None
        current_cpr = (current_spend / current_result_count) if current_result_count else None
        previous_cpr = (previous_spend / previous_result_count) if previous_result_count else None

        summary = {
            "primary_result_kind": result_kind,
            "metrics": {
                "spend": build_metric(current_spend, previous_spend),
                "reach": build_metric(
                    int(to_float(current_account_insights.get("reach") if current_account_insights else 0)),
                    int(to_float(previous_account_insights.get("reach") if previous_account_insights else 0)),
                ),
                "impressions": build_metric(
                    int(to_float(current_account_insights.get("impressions") if current_account_insights else 0)),
                    int(to_float(previous_account_insights.get("impressions") if previous_account_insights else 0)),
                ),
                "clicks": build_metric(current_clicks, previous_clicks),
                "ctr": build_metric(
                    to_float(current_account_insights.get("ctr") if current_account_insights else 0),
                    to_float(previous_account_insights.get("ctr") if previous_account_insights else 0),
                ),
                "cpm": build_metric(
                    to_float(current_account_insights.get("cpm") if current_account_insights else 0),
                    to_float(previous_account_insights.get("cpm") if previous_account_insights else 0),
                ),
                "cpc": build_metric(current_cpc, previous_cpc),
                "results": build_metric(current_result_count, previous_result_count),
                "cost_per_result": build_metric(current_cpr, previous_cpr),
            },
            "active_campaigns": len(
                [
                    item
                    for item in campaigns
                    if item.get("effective_status") == "ACTIVE" or item.get("status") == "ACTIVE"
                ]
            ),
            "total_campaigns": len(campaigns),
        }

        campaign_payload: list[dict[str, object]] = []
        for campaign in campaigns:
            campaign_id = str(campaign.get("id"))
            current_campaign = current_campaign_map.get(campaign_id, {})
            previous_campaign = previous_campaign_map.get(campaign_id, {})
            campaign_result_kind, campaign_results = extract_primary_result(current_campaign.get("actions"))
            _previous_kind, previous_results = extract_primary_result(previous_campaign.get("actions"))

            campaign_spend = to_float(current_campaign.get("spend"))
            campaign_clicks = int(to_float(current_campaign.get("clicks")))
            previous_campaign_spend = to_float(previous_campaign.get("spend"))
            previous_campaign_clicks = int(to_float(previous_campaign.get("clicks")))
            ad_groups: list[dict[str, object]] = []

            for ad_group_id in ad_set_ids_by_campaign.get(campaign_id, set()):
                ad_set = ad_sets_by_id.get(ad_group_id, {})
                ad_group_metrics = ad_group_metrics_map.get(ad_group_id, {})
                action_totals = ad_group_metrics.get("action_totals", {})
                actions = _serialize_action_totals(action_totals) if isinstance(action_totals, dict) else []
                ad_group_result_kind, ad_group_results = extract_primary_result(actions)
                ad_group_impressions = int(ad_group_metrics.get("impressions") or 0)
                ad_group_clicks = int(ad_group_metrics.get("clicks") or 0)
                ad_group_targeting = _normalize_targeting(
                    ad_set.get("targeting"),
                    audience_reach=audience_reach_by_ad_set.get(ad_group_id),
                )

                ad_groups.append(
                    {
                        "id": ad_group_id,
                        "name": _first_non_empty(
                            ad_group_metrics.get("name"),
                            ad_set.get("name"),
                            f"Ad set {ad_group_id}",
                        ),
                        "targeting": ad_group_targeting,
                        "targeting_summary": ad_group_targeting.get("summary"),
                        "metrics": {
                            "spend": float(ad_group_metrics.get("spend") or 0),
                            "impressions": ad_group_impressions,
                            "clicks": ad_group_clicks,
                            "ctr": ((ad_group_clicks / ad_group_impressions) * 100.0) if ad_group_impressions else 0.0,
                            "results": ad_group_results,
                            "result_kind": ad_group_result_kind,
                        },
                    }
                )

            ad_groups.sort(key=_ad_group_sort_key, reverse=True)

            creatives = await asyncio.gather(
                *(
                    self._build_creative_payload(
                        ad=ad,
                        insight=ad_insight_map.get(str(ad.get("id")), {}),
                    )
                    for ad in ads_by_campaign.get(campaign_id, [])
                )
            )

            creatives.sort(key=lambda item: float(item["metrics"]["spend"]), reverse=True)
            campaign_payload.append(
                {
                    "id": campaign_id,
                    "name": campaign.get("name"),
                    "status": campaign.get("effective_status") or campaign.get("status") or "UNKNOWN",
                    "primary_result_kind": campaign_result_kind,
                    "metrics": {
                        "spend": build_metric(campaign_spend, previous_campaign_spend),
                        "reach": build_metric(
                            int(to_float(current_campaign.get("reach"))),
                            int(to_float(previous_campaign.get("reach"))),
                        ),
                        "impressions": build_metric(
                            int(to_float(current_campaign.get("impressions"))),
                            int(to_float(previous_campaign.get("impressions"))),
                        ),
                        "clicks": build_metric(campaign_clicks, previous_campaign_clicks),
                        "ctr": build_metric(
                            to_float(current_campaign.get("ctr")), to_float(previous_campaign.get("ctr"))
                        ),
                        "cpm": build_metric(
                            to_float(current_campaign.get("cpm")), to_float(previous_campaign.get("cpm"))
                        ),
                        "cpc": build_metric(
                            (campaign_spend / campaign_clicks) if campaign_clicks else None,
                            (previous_campaign_spend / previous_campaign_clicks) if previous_campaign_clicks else None,
                        ),
                        "results": build_metric(campaign_results, previous_results),
                        "cost_per_result": build_metric(
                            (campaign_spend / campaign_results) if campaign_results else None,
                            (previous_campaign_spend / previous_results) if previous_results else None,
                        ),
                    },
                    "ad_groups": ad_groups,
                    "creatives": creatives,
                }
            )

        campaign_payload.sort(key=lambda item: float(item["metrics"]["spend"]["current"] or 0), reverse=True)
        return {
            "account": {
                "id": account_info.get("id") or account.external_id,
                "account_id": account_info.get("account_id") or account.account_id,
                "name": account_info.get("name") or account.name,
                "currency": account_info.get("currency") or account.currency,
                "timezone_name": account_info.get("timezone_name") or account.timezone_name,
            },
            "periods": periods,
            "summary": summary,
            "trend": {
                "current": self._build_trend_series(current_account_daily_insights),
                "previous": self._build_trend_series(previous_account_daily_insights),
            },
            "campaigns": campaign_payload,
        }

    def _build_trend_series(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        trend: list[dict[str, object]] = []
        for row in rows:
            point_date = str(row.get("date_start") or row.get("date_stop") or "").strip()
            if not point_date:
                continue
            _result_kind, results = extract_primary_result(row.get("actions"))
            trend.append(
                {
                    "date": point_date,
                    "spend": to_float(row.get("spend")),
                    "results": results,
                    "impressions": int(to_float(row.get("impressions"))),
                }
            )
        return sorted(trend, key=lambda item: str(item["date"]))

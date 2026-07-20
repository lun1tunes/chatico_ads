from __future__ import annotations

import asyncio
from collections import defaultdict
from copy import deepcopy
from datetime import timedelta
from time import monotonic

from ..infrastructure.tiktok_ads_api import TikTokAdsAPIError
from ..models.tiktok_ads_advertiser import TikTokAdsAdvertiser
from ..models.tiktok_ads_connection import TikTokAdsConnection
from ..repositories.tiktok_ads_advertiser import TikTokAdsAdvertiserRepository
from ..utils.reporting import build_metric, to_float, to_int
from ..utils.time import utcnow


class TikTokAdsReportError(Exception):
    pass


class TikTokAdsAdvertiserNotFoundError(TikTokAdsReportError):
    pass


def _mapping_value(mapping: dict[str, object] | None, *keys: str) -> object:
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _nested_mapping(mapping: dict[str, object] | None, *keys: str) -> dict[str, object]:
    value = _mapping_value(mapping, *keys)
    return value if isinstance(value, dict) else {}


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _rate_or_none(numerator: float | int, denominator: float | int) -> float | None:
    if not denominator:
        return None
    return float(numerator) / float(denominator)


class TikTokAdsReportService:
    _REPORT_METRICS = [
        "spend",
        "reach",
        "impressions",
        "clicks",
        "ctr",
        "cpm",
        "cpc",
        "conversion",
        "cost_per_conversion",
    ]

    def __init__(
        self,
        *,
        tiktok_ads_client,
        encryption_service,
        cache_ttl_seconds: int = 45,
    ) -> None:
        self.tiktok_ads_client = tiktok_ads_client
        self.encryption_service = encryption_service
        self.cache_ttl_seconds = max(0, int(cache_ttl_seconds))
        self._cache: dict[str, tuple[float, dict[str, object]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def build_report(
        self,
        *,
        advertiser_repo: TikTokAdsAdvertiserRepository,
        user_id: str,
        external_advertiser_id: str,
        requested_days: int,
        periods: dict[str, dict[str, str]],
        force_refresh: bool = False,
    ) -> dict[str, object]:
        advertiser = await advertiser_repo.get_for_user(
            user_id=user_id,
            external_advertiser_id=external_advertiser_id,
        )
        if advertiser is None:
            raise TikTokAdsAdvertiserNotFoundError("TikTok advertiser not found")

        cache_key = self._cache_key(
            user_id=user_id,
            tiktok_ads_advertiser_id=advertiser.id,
            requested_days=requested_days,
        )
        lock = self._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            if not force_refresh:
                cached_report = self._get_cached_report(cache_key)
                if cached_report is not None:
                    return cached_report

            report = await self._build_report_payload(advertiser=advertiser, periods=periods)
            advertiser.last_synced_at = utcnow()
            self._store_cached_report(cache_key, report)
            return deepcopy(report)

    def clear_user_cache(self, *, user_id: str) -> None:
        cache_prefix = f"{user_id}:"
        for cache_key in [key for key in self._cache if key.startswith(cache_prefix)]:
            self._cache.pop(cache_key, None)
        for cache_key in [key for key in self._locks if key.startswith(cache_prefix)]:
            self._locks.pop(cache_key, None)

    def _cache_key(self, *, user_id: str, tiktok_ads_advertiser_id: str, requested_days: int) -> str:
        return f"{user_id}:{tiktok_ads_advertiser_id}:{requested_days}"

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

    async def _resolve_access_token(self, *, connection: TikTokAdsConnection) -> str:
        stored_access_token = self.encryption_service.decrypt(connection.access_token_encrypted)
        refresh_token = self.encryption_service.decrypt(connection.refresh_token_encrypted)
        now = utcnow()

        if stored_access_token and connection.access_token_expires_at and connection.access_token_expires_at > now + timedelta(minutes=5):
            return stored_access_token

        if not refresh_token:
            if stored_access_token and (connection.access_token_expires_at is None or connection.access_token_expires_at > now):
                return stored_access_token
            raise TikTokAdsAPIError("TikTok access token is unavailable and cannot be refreshed")

        try:
            payload = await self.tiktok_ads_client.refresh_access_token(refresh_token=refresh_token)
        except TikTokAdsAPIError:
            if stored_access_token and connection.access_token_expires_at and connection.access_token_expires_at > now:
                return stored_access_token
            raise

        access_token = _optional_string(payload.get("access_token")) or stored_access_token
        if not access_token:
            raise TikTokAdsAPIError("TikTok refresh response did not include an access token")

        new_refresh_token = _optional_string(payload.get("refresh_token"))
        if new_refresh_token:
            connection.refresh_token_encrypted = self.encryption_service.encrypt(new_refresh_token)
        connection.access_token_encrypted = self.encryption_service.encrypt(access_token)

        expires_in = to_int(payload.get("expires_in"))
        if expires_in > 0:
            connection.access_token_expires_at = utcnow() + timedelta(seconds=expires_in)
        return access_token

    async def _build_report_payload(
        self,
        *,
        advertiser: TikTokAdsAdvertiser,
        periods: dict[str, dict[str, str]],
    ) -> dict[str, object]:
        access_token = await self._resolve_access_token(connection=advertiser.connection)
        current = periods["current"]
        previous = periods["previous"]

        (
            advertiser_info_list,
            current_summary,
            previous_summary,
            current_daily_report,
            previous_daily_report,
            current_campaign_report,
            previous_campaign_report,
            current_ad_report,
            campaign_catalog,
            ad_catalog,
        ) = await asyncio.gather(
            self.tiktok_ads_client.get_advertiser_info(
                advertiser_ids=[advertiser.advertiser_id],
                access_token=access_token,
            ),
            self.tiktok_ads_client.get_integrated_report(
                advertiser_id=advertiser.advertiser_id,
                access_token=access_token,
                data_level="ADVERTISER",
                dimensions=[],
                metrics=self._REPORT_METRICS,
                start_date=current["since"],
                end_date=current["until"],
            ),
            self.tiktok_ads_client.get_integrated_report(
                advertiser_id=advertiser.advertiser_id,
                access_token=access_token,
                data_level="ADVERTISER",
                dimensions=[],
                metrics=self._REPORT_METRICS,
                start_date=previous["since"],
                end_date=previous["until"],
            ),
            self.tiktok_ads_client.get_integrated_report(
                advertiser_id=advertiser.advertiser_id,
                access_token=access_token,
                data_level="ADVERTISER",
                dimensions=["stat_time_day"],
                metrics=self._REPORT_METRICS,
                start_date=current["since"],
                end_date=current["until"],
            ),
            self.tiktok_ads_client.get_integrated_report(
                advertiser_id=advertiser.advertiser_id,
                access_token=access_token,
                data_level="ADVERTISER",
                dimensions=["stat_time_day"],
                metrics=self._REPORT_METRICS,
                start_date=previous["since"],
                end_date=previous["until"],
            ),
            self.tiktok_ads_client.get_integrated_report(
                advertiser_id=advertiser.advertiser_id,
                access_token=access_token,
                data_level="CAMPAIGN",
                dimensions=["campaign_id"],
                metrics=self._REPORT_METRICS,
                start_date=current["since"],
                end_date=current["until"],
            ),
            self.tiktok_ads_client.get_integrated_report(
                advertiser_id=advertiser.advertiser_id,
                access_token=access_token,
                data_level="CAMPAIGN",
                dimensions=["campaign_id"],
                metrics=self._REPORT_METRICS,
                start_date=previous["since"],
                end_date=previous["until"],
            ),
            self.tiktok_ads_client.get_integrated_report(
                advertiser_id=advertiser.advertiser_id,
                access_token=access_token,
                data_level="AD",
                dimensions=["campaign_id", "adgroup_id", "ad_id"],
                metrics=[*self._REPORT_METRICS, "adgroup_name"],
                start_date=current["since"],
                end_date=current["until"],
            ),
            self._safe_list_campaigns(advertiser_id=advertiser.advertiser_id, access_token=access_token),
            self._safe_list_ads(advertiser_id=advertiser.advertiser_id, access_token=access_token),
        )

        advertiser_info = advertiser_info_list[0] if advertiser_info_list else {}
        current_summary_metrics = self._extract_metrics(
            current_summary.get("total_metrics") or (current_summary.get("rows") or [None])[0]
        )
        previous_summary_metrics = self._extract_metrics(
            previous_summary.get("total_metrics") or (previous_summary.get("rows") or [None])[0]
        )
        current_campaign_map = self._rows_by_campaign_id(current_campaign_report.get("rows") or [])
        previous_campaign_map = self._rows_by_campaign_id(previous_campaign_report.get("rows") or [])
        campaign_catalog_by_id = self._campaign_catalog_by_id(campaign_catalog)
        ad_catalog_by_id = self._ad_catalog_by_id(ad_catalog)
        creatives_by_campaign = self._creatives_by_campaign(
            rows=current_ad_report.get("rows") or [],
            ad_catalog_by_id=ad_catalog_by_id,
        )

        resolved_account_name = (
            _optional_string(
                _mapping_value(advertiser_info, "name", "advertiser_name", "display_name")
            )
            or advertiser.name
            or advertiser.advertiser_id
        )
        resolved_currency = _optional_string(
            _mapping_value(advertiser_info, "currency", "currency_code", "currencyCode")
        ) or advertiser.currency
        resolved_time_zone = _optional_string(
            _mapping_value(advertiser_info, "timezone", "timezone_name", "timezoneName")
        ) or advertiser.timezone_name

        campaigns = self._build_campaigns(
            campaign_catalog_by_id=campaign_catalog_by_id,
            current_campaign_map=current_campaign_map,
            previous_campaign_map=previous_campaign_map,
            creatives_by_campaign=creatives_by_campaign,
        )
        active_campaigns = len([item for item in campaigns if self._is_active_status(item["status"])])

        return {
            "account": {
                "id": advertiser.advertiser_id,
                "account_id": advertiser.advertiser_id,
                "name": resolved_account_name,
                "currency": resolved_currency,
                "timezone_name": resolved_time_zone,
            },
            "periods": periods,
            "summary": {
                "primary_result_kind": "conversions",
                "metrics": self._build_metric_collection(
                    current_metrics=current_summary_metrics,
                    previous_metrics=previous_summary_metrics,
                ),
                "active_campaigns": active_campaigns,
                "total_campaigns": len(campaigns),
            },
            "trend": {
                "current": self._build_trend_series(current_daily_report.get("rows") or []),
                "previous": self._build_trend_series(previous_daily_report.get("rows") or []),
            },
            "campaigns": campaigns,
        }

    async def _safe_list_campaigns(self, *, advertiser_id: str, access_token: str) -> list[dict[str, object]]:
        try:
            return await self.tiktok_ads_client.list_campaigns(
                advertiser_id=advertiser_id,
                access_token=access_token,
            )
        except TikTokAdsAPIError:
            return []

    async def _safe_list_ads(self, *, advertiser_id: str, access_token: str) -> list[dict[str, object]]:
        try:
            return await self.tiktok_ads_client.list_ads(
                advertiser_id=advertiser_id,
                access_token=access_token,
            )
        except TikTokAdsAPIError:
            return []

    @staticmethod
    def _campaign_catalog_by_id(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
        results: dict[str, dict[str, object]] = {}
        for row in rows:
            campaign_id = _optional_string(
                _mapping_value(row, "campaign_id", "id", "campaignId")
            )
            if not campaign_id:
                continue
            results[campaign_id] = row
        return results

    @staticmethod
    def _ad_catalog_by_id(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
        results: dict[str, dict[str, object]] = {}
        for row in rows:
            ad_id = _optional_string(_mapping_value(row, "ad_id", "id", "adId"))
            if not ad_id:
                continue
            results[ad_id] = row
        return results

    def _rows_by_campaign_id(self, rows: list[dict[str, object]]) -> dict[str, dict[str, float | int | None]]:
        results: dict[str, dict[str, float | int | None]] = {}
        for row in rows:
            campaign_id = self._dimension_value(row, "campaign_id", "campaignId")
            if not campaign_id:
                continue
            results[campaign_id] = self._extract_metrics(row)
        return results

    def _creatives_by_campaign(
        self,
        *,
        rows: list[dict[str, object]],
        ad_catalog_by_id: dict[str, dict[str, object]],
    ) -> dict[str, list[dict[str, object]]]:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            campaign_id = self._dimension_value(row, "campaign_id", "campaignId")
            ad_id = self._dimension_value(row, "ad_id", "adId")
            if not campaign_id or not ad_id:
                continue

            ad_catalog = ad_catalog_by_id.get(ad_id, {})
            metrics = self._extract_metrics(row)
            object_type = (
                _optional_string(
                    _mapping_value(ad_catalog, "ad_format", "creative_type", "ad_type", "adgroup_type")
                )
                or "AD"
            )
            grouped[campaign_id].append(
                {
                    "id": ad_id,
                    "name": _optional_string(
                        _mapping_value(ad_catalog, "ad_name", "name", "display_name")
                    )
                    or f"Ad #{ad_id}",
                    "object_type": object_type,
                    "thumbnail_url": None,
                    "image_url": None,
                    "ad_group_id": self._dimension_value(row, "adgroup_id", "adGroupId"),
                    "ad_group_name": self._attribute_value(row, "adgroup_name", "adGroupName")
                    or _optional_string(_mapping_value(ad_catalog, "adgroup_name", "adgroupName")),
                    "metrics": {
                        "spend": float(metrics["spend"] or 0),
                        "impressions": int(metrics["impressions"] or 0),
                        "clicks": int(metrics["clicks"] or 0),
                        "ctr": float(metrics["ctr"] or 0),
                        "results": float(metrics["results"] or 0),
                        "result_kind": "conversions",
                    },
                }
            )
        return dict(grouped)

    def _build_campaigns(
        self,
        *,
        campaign_catalog_by_id: dict[str, dict[str, object]],
        current_campaign_map: dict[str, dict[str, float | int | None]],
        previous_campaign_map: dict[str, dict[str, float | int | None]],
        creatives_by_campaign: dict[str, list[dict[str, object]]],
    ) -> list[dict[str, object]]:
        campaigns_by_id: dict[str, dict[str, object]] = {}

        for campaign_id, row in campaign_catalog_by_id.items():
            campaigns_by_id[campaign_id] = {
                "id": campaign_id,
                "name": _optional_string(
                    _mapping_value(row, "campaign_name", "name", "display_name")
                )
                or campaign_id,
                "status": _optional_string(
                    _mapping_value(row, "operation_status", "status", "secondary_status")
                )
                or "UNKNOWN",
            }

        for campaign_id in set(current_campaign_map) | set(previous_campaign_map) | set(creatives_by_campaign):
            campaigns_by_id.setdefault(
                campaign_id,
                {
                    "id": campaign_id,
                    "name": campaign_id,
                    "status": "UNKNOWN",
                },
            )

        campaigns: list[dict[str, object]] = []
        for campaign_id, campaign_data in campaigns_by_id.items():
            current_metrics = current_campaign_map.get(campaign_id, self._zero_metrics())
            previous_metrics = previous_campaign_map.get(campaign_id, self._zero_metrics())
            creatives = sorted(
                creatives_by_campaign.get(campaign_id, []),
                key=lambda item: (-float(item["metrics"]["spend"]), -float(item["metrics"]["results"]), item["name"]),
            )
            campaigns.append(
                {
                    "id": campaign_id,
                    "name": campaign_data["name"],
                    "status": campaign_data["status"],
                    "primary_result_kind": "conversions",
                    "metrics": self._build_metric_collection(
                        current_metrics=current_metrics,
                        previous_metrics=previous_metrics,
                    ),
                    "creatives": creatives,
                }
            )

        return sorted(
            campaigns,
            key=lambda item: (
                -float(item["metrics"]["spend"]["current"] or 0),
                -float(item["metrics"]["results"]["current"] or 0),
                str(item["name"]).lower(),
            ),
        )

    def _build_metric_collection(
        self,
        *,
        current_metrics: dict[str, float | int | None],
        previous_metrics: dict[str, float | int | None],
    ) -> dict[str, dict[str, float | int | None]]:
        return {
            "spend": build_metric(current_metrics["spend"], previous_metrics["spend"]),
            "reach": build_metric(current_metrics["reach"], previous_metrics["reach"]),
            "impressions": build_metric(current_metrics["impressions"], previous_metrics["impressions"]),
            "clicks": build_metric(current_metrics["clicks"], previous_metrics["clicks"]),
            "ctr": build_metric(current_metrics["ctr"], previous_metrics["ctr"]),
            "cpm": build_metric(current_metrics["cpm"], previous_metrics["cpm"]),
            "cpc": build_metric(current_metrics["cpc"], previous_metrics["cpc"]),
            "results": build_metric(current_metrics["results"], previous_metrics["results"]),
            "cost_per_result": build_metric(
                current_metrics["cost_per_result"],
                previous_metrics["cost_per_result"],
            ),
        }

    def _extract_metrics(self, row: dict[str, object] | None) -> dict[str, float | int | None]:
        metrics = _nested_mapping(row, "metrics")
        source = metrics or (row if isinstance(row, dict) else {})
        spend = to_float(_mapping_value(source, "spend"))
        reach_value = _mapping_value(source, "reach")
        reach = to_int(reach_value) if reach_value is not None else None
        impressions = to_int(_mapping_value(source, "impressions"))
        clicks = to_int(_mapping_value(source, "clicks"))
        results = to_float(_mapping_value(source, "conversion", "conversions", "results"))
        ctr_value = _mapping_value(source, "ctr")
        ctr = to_float(ctr_value) if ctr_value is not None else _rate_or_none(clicks * 100.0, impressions)
        cpm_value = _mapping_value(source, "cpm")
        cpm = to_float(cpm_value) if cpm_value is not None else _rate_or_none(spend * 1000.0, impressions)
        cpc_value = _mapping_value(source, "cpc")
        cpc = to_float(cpc_value) if cpc_value is not None else _rate_or_none(spend, clicks)
        cpr_value = _mapping_value(source, "cost_per_conversion", "cost_per_result")
        cost_per_result = to_float(cpr_value) if cpr_value is not None else _rate_or_none(spend, results)

        return {
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

    def _build_trend_series(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        trend: list[dict[str, object]] = []
        for row in rows:
            point_date = self._dimension_value(row, "stat_time_day", "date")
            if not point_date:
                continue
            metrics = self._extract_metrics(row)
            trend.append(
                {
                    "date": point_date,
                    "spend": float(metrics["spend"] or 0),
                    "results": float(metrics["results"] or 0),
                    "impressions": int(metrics["impressions"] or 0),
                }
            )
        return sorted(trend, key=lambda item: str(item["date"]))

    @staticmethod
    def _zero_metrics() -> dict[str, float | int | None]:
        return {
            "spend": 0.0,
            "reach": None,
            "impressions": 0,
            "clicks": 0,
            "ctr": None,
            "cpm": None,
            "cpc": None,
            "results": 0.0,
            "cost_per_result": None,
        }

    @staticmethod
    def _dimension_value(row: dict[str, object], *keys: str) -> str | None:
        for mapping in (row, _nested_mapping(row, "dimensions")):
            for key in keys:
                value = _optional_string(_mapping_value(mapping, key))
                if value:
                    return value
        return None

    @staticmethod
    def _attribute_value(row: dict[str, object], *keys: str) -> str | None:
        for mapping in (row, _nested_mapping(row, "metrics"), _nested_mapping(row, "dimensions")):
            for key in keys:
                value = _optional_string(_mapping_value(mapping, key))
                if value:
                    return value
        return None

    @staticmethod
    def _is_active_status(status: str) -> bool:
        normalized = status.upper()
        return normalized in {"ENABLE", "ENABLED", "ACTIVE"} or normalized.endswith("_ENABLE")

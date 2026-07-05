from __future__ import annotations

import asyncio
from collections import defaultdict
from copy import deepcopy
from datetime import timedelta
from time import monotonic

from ..infrastructure.google_ads_api import GoogleAdsAPIError
from ..models.google_ads_connection import GoogleAdsConnection
from ..models.google_ads_customer import GoogleAdsCustomer
from ..repositories.google_ads_customer import GoogleAdsCustomerRepository
from ..utils.reporting import build_metric, to_float, to_int
from ..utils.time import utcnow


class GoogleAdsReportError(Exception):
    pass


class GoogleAdsCustomerNotFoundError(GoogleAdsReportError):
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


def _cost_from_micros(value: object) -> float:
    return to_float(value) / 1_000_000.0


def _rate_or_none(numerator: float | int, denominator: float | int) -> float | None:
    if not denominator:
        return None
    return float(numerator) / float(denominator)


def _percentage_or_none(numerator: float | int, denominator: float | int) -> float | None:
    ratio = _rate_or_none(numerator, denominator)
    if ratio is None:
        return None
    return ratio * 100.0


class GoogleAdsReportService:
    def __init__(
        self,
        *,
        google_ads_client,
        encryption_service,
        cache_ttl_seconds: int = 45,
    ) -> None:
        self.google_ads_client = google_ads_client
        self.encryption_service = encryption_service
        self.cache_ttl_seconds = max(0, int(cache_ttl_seconds))
        self._cache: dict[str, tuple[float, dict[str, object]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def build_report(
        self,
        *,
        customer_repo: GoogleAdsCustomerRepository,
        user_id: str,
        external_customer_id: str,
        requested_days: int,
        periods: dict[str, dict[str, str]],
        force_refresh: bool = False,
    ) -> dict[str, object]:
        customer = await customer_repo.get_for_user(user_id=user_id, external_customer_id=external_customer_id)
        if customer is None:
            raise GoogleAdsCustomerNotFoundError("Google Ads customer not found")

        cache_key = self._cache_key(
            user_id=user_id,
            google_ads_customer_id=customer.id,
            requested_days=requested_days,
        )
        lock = self._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            if not force_refresh:
                cached_report = self._get_cached_report(cache_key)
                if cached_report is not None:
                    return cached_report

            report = await self._build_report_payload(customer=customer, periods=periods)
            customer.last_synced_at = utcnow()
            self._store_cached_report(cache_key, report)
            return deepcopy(report)

    def clear_user_cache(self, *, user_id: str) -> None:
        cache_prefix = f"{user_id}:"
        for cache_key in [key for key in self._cache if key.startswith(cache_prefix)]:
            self._cache.pop(cache_key, None)
        for cache_key in [key for key in self._locks if key.startswith(cache_prefix)]:
            self._locks.pop(cache_key, None)

    def _cache_key(self, *, user_id: str, google_ads_customer_id: str, requested_days: int) -> str:
        return f"{user_id}:{google_ads_customer_id}:{requested_days}"

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

    async def _resolve_access_token(self, *, connection: GoogleAdsConnection) -> str:
        refresh_token = self.encryption_service.decrypt(connection.refresh_token_encrypted)
        stored_access_token = self.encryption_service.decrypt(connection.access_token_encrypted)

        if not refresh_token:
            return stored_access_token

        try:
            payload = await self.google_ads_client.refresh_access_token(refresh_token=refresh_token)
        except GoogleAdsAPIError:
            if connection.access_token_expires_at and connection.access_token_expires_at > utcnow():
                return stored_access_token
            raise

        access_token = str(payload["access_token"])
        connection.access_token_encrypted = self.encryption_service.encrypt(access_token)

        expires_in = to_int(payload.get("expires_in"))
        connection.access_token_expires_at = (
            utcnow() + timedelta(seconds=expires_in) if expires_in > 0 else connection.access_token_expires_at
        )
        return access_token

    async def _build_report_payload(
        self,
        *,
        customer: GoogleAdsCustomer,
        periods: dict[str, dict[str, str]],
    ) -> dict[str, object]:
        access_token = await self._resolve_access_token(connection=customer.connection)
        current = periods["current"]
        previous = periods["previous"]

        (
            account_row,
            campaign_rows,
            current_summary_row,
            previous_summary_row,
            current_campaign_rows,
            previous_campaign_rows,
            current_ad_rows,
        ) = await asyncio.gather(
            self.google_ads_client.get_customer(
                customer_id=customer.external_customer_id,
                access_token=access_token,
                login_customer_id=customer.login_customer_id,
            ),
            self.google_ads_client.list_campaigns(
                customer_id=customer.external_customer_id,
                access_token=access_token,
                login_customer_id=customer.login_customer_id,
            ),
            self.google_ads_client.get_customer_metrics(
                customer_id=customer.external_customer_id,
                access_token=access_token,
                since=current["since"],
                until=current["until"],
                login_customer_id=customer.login_customer_id,
            ),
            self.google_ads_client.get_customer_metrics(
                customer_id=customer.external_customer_id,
                access_token=access_token,
                since=previous["since"],
                until=previous["until"],
                login_customer_id=customer.login_customer_id,
            ),
            self.google_ads_client.get_campaign_metrics(
                customer_id=customer.external_customer_id,
                access_token=access_token,
                since=current["since"],
                until=current["until"],
                login_customer_id=customer.login_customer_id,
            ),
            self.google_ads_client.get_campaign_metrics(
                customer_id=customer.external_customer_id,
                access_token=access_token,
                since=previous["since"],
                until=previous["until"],
                login_customer_id=customer.login_customer_id,
            ),
            self.google_ads_client.get_ad_metrics(
                customer_id=customer.external_customer_id,
                access_token=access_token,
                since=current["since"],
                until=current["until"],
                login_customer_id=customer.login_customer_id,
            ),
        )

        current_summary_metrics = self._extract_metrics(current_summary_row)
        previous_summary_metrics = self._extract_metrics(previous_summary_row)
        current_campaign_map = self._rows_by_campaign_id(current_campaign_rows)
        previous_campaign_map = self._rows_by_campaign_id(previous_campaign_rows)
        creatives_by_campaign = self._creatives_by_campaign(current_ad_rows)

        account_info = _nested_mapping(account_row, "customer")
        resolved_account_name = (
            _optional_string(_mapping_value(account_info, "descriptiveName", "descriptive_name"))
            or customer.descriptive_name
            or customer.external_customer_id
        )
        resolved_currency = _optional_string(_mapping_value(account_info, "currencyCode", "currency_code")) or customer.currency_code
        resolved_time_zone = _optional_string(_mapping_value(account_info, "timeZone", "time_zone")) or customer.time_zone

        campaigns = self._build_campaigns(
            campaign_rows=campaign_rows,
            current_campaign_map=current_campaign_map,
            previous_campaign_map=previous_campaign_map,
            creatives_by_campaign=creatives_by_campaign,
        )
        active_campaigns = len([item for item in campaigns if self._is_active_status(item["status"])])

        return {
            "account": {
                "id": customer.external_customer_id,
                "account_id": customer.external_customer_id,
                "name": resolved_account_name,
                "currency": resolved_currency,
                "timezone_name": resolved_time_zone,
            },
            "periods": periods,
            "summary": {
                "primary_result_kind": "result",
                "metrics": self._build_metric_collection(
                    current_metrics=current_summary_metrics,
                    previous_metrics=previous_summary_metrics,
                ),
                "active_campaigns": active_campaigns,
                "total_campaigns": len(campaigns),
            },
            "campaigns": campaigns,
        }

    def _build_campaigns(
        self,
        *,
        campaign_rows: list[dict[str, object]],
        current_campaign_map: dict[str, dict[str, float | int | None]],
        previous_campaign_map: dict[str, dict[str, float | int | None]],
        creatives_by_campaign: dict[str, list[dict[str, object]]],
    ) -> list[dict[str, object]]:
        campaigns_by_id: dict[str, dict[str, object]] = {}

        for row in campaign_rows:
            campaign = _nested_mapping(row, "campaign")
            campaign_id = _optional_string(_mapping_value(campaign, "id"))
            if not campaign_id:
                continue
            campaigns_by_id[campaign_id] = {
                "id": campaign_id,
                "name": _optional_string(_mapping_value(campaign, "name")) or campaign_id,
                "status": _optional_string(_mapping_value(campaign, "status")) or "UNKNOWN",
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
                    "primary_result_kind": "result",
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

    def _rows_by_campaign_id(self, rows: list[dict[str, object]]) -> dict[str, dict[str, float | int | None]]:
        results: dict[str, dict[str, float | int | None]] = {}
        for row in rows:
            campaign = _nested_mapping(row, "campaign")
            campaign_id = _optional_string(_mapping_value(campaign, "id"))
            if not campaign_id:
                continue
            results[campaign_id] = self._extract_metrics(row)
        return results

    def _creatives_by_campaign(self, rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            campaign = _nested_mapping(row, "campaign")
            ad_group_ad = _nested_mapping(row, "adGroupAd", "ad_group_ad")
            ad = _nested_mapping(ad_group_ad, "ad")
            campaign_id = _optional_string(_mapping_value(campaign, "id"))
            ad_id = _optional_string(_mapping_value(ad, "id"))
            if not campaign_id or not ad_id:
                continue

            ad_type = _optional_string(_mapping_value(ad, "type")) or "AD"
            metrics = self._extract_metrics(row)
            grouped[campaign_id].append(
                {
                    "id": ad_id,
                    "name": f"{ad_type.replace('_', ' ').title()} #{ad_id}",
                    "object_type": ad_type,
                    "thumbnail_url": None,
                    "image_url": None,
                    "metrics": {
                        "spend": float(metrics["spend"] or 0),
                        "impressions": int(metrics["impressions"] or 0),
                        "clicks": int(metrics["clicks"] or 0),
                        "ctr": float(metrics["ctr"] or 0),
                        "results": float(metrics["results"] or 0),
                        "result_kind": "result",
                    },
                }
            )
        return dict(grouped)

    def _build_metric_collection(
        self,
        *,
        current_metrics: dict[str, float | int | None],
        previous_metrics: dict[str, float | int | None],
    ) -> dict[str, dict[str, float | int | None]]:
        return {
            "spend": build_metric(current_metrics["spend"], previous_metrics["spend"]),
            "reach": build_metric(None, None),
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
        spend = _cost_from_micros(_mapping_value(metrics, "costMicros", "cost_micros"))
        impressions = to_int(_mapping_value(metrics, "impressions"))
        clicks = to_int(_mapping_value(metrics, "clicks"))
        results = to_float(_mapping_value(metrics, "conversions"))
        ctr = _percentage_or_none(clicks, impressions)
        cpm_rate = _rate_or_none(spend * 1000.0, impressions)
        cpc_rate = _rate_or_none(spend, clicks)
        cpr_rate = _rate_or_none(spend, results)

        return {
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "cpm": cpm_rate,
            "cpc": cpc_rate,
            "results": results,
            "cost_per_result": cpr_rate,
        }

    @staticmethod
    def _zero_metrics() -> dict[str, float | int | None]:
        return {
            "spend": 0.0,
            "impressions": 0,
            "clicks": 0,
            "ctr": None,
            "cpm": None,
            "cpc": None,
            "results": 0.0,
            "cost_per_result": None,
        }

    @staticmethod
    def _is_active_status(status: str) -> bool:
        normalized = status.upper()
        return "ACTIVE" in normalized or normalized == "ENABLED"

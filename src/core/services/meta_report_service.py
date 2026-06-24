from __future__ import annotations

import asyncio
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


class MetaReportError(Exception):
    pass


class MetaAdAccountNotFoundError(MetaReportError):
    pass


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _resolve_creative_image_url(creative: dict[str, object]) -> str | None:
    object_story_spec = creative.get("object_story_spec")
    story = object_story_spec if isinstance(object_story_spec, dict) else {}
    video_data = story.get("video_data") if isinstance(story.get("video_data"), dict) else {}
    link_data = story.get("link_data") if isinstance(story.get("link_data"), dict) else {}
    photo_data = story.get("photo_data") if isinstance(story.get("photo_data"), dict) else {}
    template_data = story.get("template_data") if isinstance(story.get("template_data"), dict) else {}

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


def _looks_like_low_res_preview(url: str | None) -> bool:
    if not url:
        return False

    stp_values = parse_qs(urlsplit(url).query).get("stp", [])
    stp = stp_values[0] if stp_values else ""
    low_res_tokens = ("p64x64", "p96x96", "p128x128")
    return any(token in stp for token in low_res_tokens)


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
            requested_days=requested_days,
        )
        lock = self._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            if not force_refresh:
                cached_report = self._get_cached_report(cache_key)
                if cached_report is not None:
                    return cached_report

                snapshot = await snapshot_repo.get_latest_by_account_and_requested_days(
                    meta_ad_account_id=account.id,
                    requested_days=requested_days,
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

    def _cache_key(self, *, user_id: str, meta_ad_account_id: str, requested_days: int) -> str:
        return f"{user_id}:{meta_ad_account_id}:{requested_days}"

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
            "metrics": {
                "spend": to_float(insight.get("spend")),
                "impressions": int(to_float(insight.get("impressions"))),
                "clicks": int(to_float(insight.get("clicks"))),
                "ctr": to_float(insight.get("ctr")),
                "results": ad_results,
                "result_kind": ad_result_kind,
            },
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
            current_account_insights,
            previous_account_insights,
            current_campaign_insights,
            previous_campaign_insights,
            ads,
            ad_insights,
        ) = await asyncio.gather(
            self.meta_client.get_ad_account(account_id=account.external_id, access_token=access_token),
            self.meta_client.list_campaigns(account_id=account.external_id, access_token=access_token),
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
            "campaigns": campaign_payload,
        }

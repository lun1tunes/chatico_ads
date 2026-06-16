from __future__ import annotations

from ..interfaces.services import IEncryptionService, IMetaGraphClient
from ..repositories.meta_ad_account import MetaAdAccountRepository
from ..utils.reporting import build_metric, extract_primary_result, group_ads_by_campaign, to_float


class MetaReportError(Exception):
    pass


class MetaAdAccountNotFoundError(MetaReportError):
    pass


class MetaReportService:
    def __init__(self, *, meta_client: IMetaGraphClient, encryption_service: IEncryptionService) -> None:
        self.meta_client = meta_client
        self.encryption_service = encryption_service

    async def build_report(
        self,
        *,
        account_repo: MetaAdAccountRepository,
        user_id: str,
        external_account_id: str,
        periods: dict[str, dict[str, str]],
    ) -> dict[str, object]:
        account = await account_repo.get_for_user(user_id=user_id, external_id=external_account_id)
        if account is None:
            raise MetaAdAccountNotFoundError("Meta ad account not found")

        access_token = self.encryption_service.decrypt(account.connection.access_token_encrypted)
        current = periods["current"]
        previous = periods["previous"]

        account_info = await self.meta_client.get_ad_account(account_id=account.external_id, access_token=access_token)
        campaigns = await self.meta_client.list_campaigns(account_id=account.external_id, access_token=access_token)
        current_account_insights = await self.meta_client.get_account_insights(
            account_id=account.external_id,
            access_token=access_token,
            since=current["since"],
            until=current["until"],
        )
        previous_account_insights = await self.meta_client.get_account_insights(
            account_id=account.external_id,
            access_token=access_token,
            since=previous["since"],
            until=previous["until"],
        )
        current_campaign_insights = await self.meta_client.get_campaign_insights(
            account_id=account.external_id,
            access_token=access_token,
            since=current["since"],
            until=current["until"],
        )
        previous_campaign_insights = await self.meta_client.get_campaign_insights(
            account_id=account.external_id,
            access_token=access_token,
            since=previous["since"],
            until=previous["until"],
        )
        ads = await self.meta_client.list_ads(account_id=account.external_id, access_token=access_token)
        ad_insights = await self.meta_client.get_ad_insights(
            account_id=account.external_id,
            access_token=access_token,
            since=current["since"],
            until=current["until"],
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
            "active_campaigns": len([item for item in campaigns if item.get("effective_status") == "ACTIVE" or item.get("status") == "ACTIVE"]),
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

            creatives = []
            for ad in ads_by_campaign.get(campaign_id, []):
                ad_id = str(ad.get("id"))
                insight = ad_insight_map.get(ad_id, {})
                ad_result_kind, ad_results = extract_primary_result(insight.get("actions"))
                creative = ad.get("creative") or {}
                creatives.append(
                    {
                        "id": ad_id,
                        "name": ad.get("name"),
                        "object_type": creative.get("object_type") or "ad",
                        "thumbnail_url": creative.get("thumbnail_url"),
                        "image_url": creative.get("image_url"),
                        "metrics": {
                            "spend": to_float(insight.get("spend")),
                            "impressions": int(to_float(insight.get("impressions"))),
                            "clicks": int(to_float(insight.get("clicks"))),
                            "ctr": to_float(insight.get("ctr")),
                            "results": ad_results,
                            "result_kind": ad_result_kind,
                        },
                    }
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
                        "ctr": build_metric(to_float(current_campaign.get("ctr")), to_float(previous_campaign.get("ctr"))),
                        "cpm": build_metric(to_float(current_campaign.get("cpm")), to_float(previous_campaign.get("cpm"))),
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

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path
from urllib.parse import urlencode

import httpx

from ..config import settings
from ..utils.reporting import to_int


class TikTokAdsAPIError(Exception):
    pass


class TikTokAdsConfigurationError(TikTokAdsAPIError):
    pass


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


class TikTokAdsAPIClient:
    _REFRESH_TOKEN_PATH = "/open_api/{version}/oauth2/refresh_token/"

    def __init__(
        self,
        *,
        app_id: str | None = None,
        app_secret: str | None = None,
        redirect_uri: str | None = None,
        oauth_authorize_url: str | None = None,
        oauth_scopes: list[str] | None = None,
        api_base_url: str | None = None,
        api_version: str | None = None,
        business_sdk_path: str | None = None,
    ) -> None:
        tiktok_settings = settings.tiktok_ads
        self.app_id = app_id or tiktok_settings.app_id
        self.app_secret = app_secret or tiktok_settings.app_secret
        self.redirect_uri = redirect_uri or tiktok_settings.oauth_redirect_uri
        self.oauth_authorize_url = oauth_authorize_url or tiktok_settings.oauth_authorize_url
        self.oauth_scopes = oauth_scopes or list(tiktok_settings.oauth_scopes)
        self.api_base_url = (api_base_url or tiktok_settings.api_base_url).rstrip("/")
        self.api_version = api_version or tiktok_settings.api_version
        self.business_sdk_path = business_sdk_path or tiktok_settings.business_sdk_path
        self._client = httpx.AsyncClient(timeout=30.0)

    def _assert_oauth_configured(self) -> None:
        required_values = (self.app_id, self.app_secret, self.redirect_uri)
        if not all(value and str(value).strip() and not str(value).strip().lower().startswith("replace_with_") for value in required_values):
            raise TikTokAdsConfigurationError(
                "TikTok Ads OAuth is not configured. Set TIKTOK_APP_ID, TIKTOK_APP_SECRET, and "
                "TIKTOK_OAUTH_REDIRECT_URI."
            )

    def _sdk_module(self):
        sdk_path = Path(self.business_sdk_path).resolve()
        if not sdk_path.exists():
            raise TikTokAdsConfigurationError(
                f"TikTok Business SDK was not found at {sdk_path}. Set TIKTOK_BUSINESS_SDK_PATH to the local SDK path."
            )
        if str(sdk_path) not in sys.path:
            sys.path.insert(0, str(sdk_path))
        try:
            return importlib.import_module("business_api_client")
        except Exception as exc:  # noqa: BLE001
            raise TikTokAdsConfigurationError(
                f"Failed to import TikTok Business SDK from {sdk_path}: {exc}"
            ) from exc

    def _build_sdk_api_client(self):
        sdk = self._sdk_module()
        configuration = sdk.Configuration()
        configuration.host = self.api_base_url
        return sdk, sdk.ApiClient(configuration)

    async def _run_sdk(self, api_name: str, method_name: str, *args, **kwargs) -> dict[str, object]:
        def _invoke() -> object:
            sdk, api_client = self._build_sdk_api_client()
            api = getattr(sdk, api_name)(api_client)
            method = getattr(api, method_name)
            return method(*args, **kwargs)

        try:
            response = await asyncio.to_thread(_invoke)
        except Exception as exc:  # noqa: BLE001
            raise TikTokAdsAPIError(f"TikTok Ads request failed: {exc}") from exc
        return self._unwrap_response(response)

    @staticmethod
    def _unwrap_response(response: object) -> dict[str, object]:
        if hasattr(response, "to_dict"):
            payload = response.to_dict()
        elif isinstance(response, dict):
            payload = response
        else:
            payload = {
                "code": getattr(response, "code", None),
                "data": getattr(response, "data", None),
                "message": getattr(response, "message", None),
                "request_id": getattr(response, "request_id", None),
            }

        if not isinstance(payload, dict):
            raise TikTokAdsAPIError("TikTok Ads returned an unexpected payload")

        code = payload.get("code")
        if code not in {None, 0}:
            message = _optional_string(payload.get("message")) or f"TikTok Ads request failed with code {code}"
            raise TikTokAdsAPIError(message)

        data = payload.get("data")
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"list": data}
        if data is None:
            return {}
        return {"value": data}

    @staticmethod
    def _extract_sequence(data: dict[str, object], *keys: str) -> list[object]:
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
        return []

    @staticmethod
    def _extract_mapping(data: dict[str, object], *keys: str) -> dict[str, object]:
        for key in keys:
            value = data.get(key)
            if isinstance(value, dict):
                return value
        return {}

    @staticmethod
    def _extract_page_info(data: dict[str, object]) -> dict[str, object]:
        return TikTokAdsAPIClient._extract_mapping(data, "page_info", "pageInfo")

    def build_authorization_url(self, *, state: str) -> str:
        self._assert_oauth_configured()
        params: dict[str, str] = {
            "app_id": str(self.app_id),
            "redirect_uri": str(self.redirect_uri),
            "state": state,
        }
        if self.oauth_scopes:
            params["scope"] = ",".join(scope.strip() for scope in self.oauth_scopes if scope.strip())
        return f"{self.oauth_authorize_url}?{urlencode(params)}"

    async def aclose(self) -> None:
        await self._client.aclose()

    async def exchange_code_for_tokens(self, *, code: str) -> dict[str, object]:
        self._assert_oauth_configured()
        sdk = self._sdk_module()
        body = sdk.Oauth2AccessTokenBody(app_id=str(self.app_id), auth_code=code, secret=str(self.app_secret))
        return await self._run_sdk("AuthenticationApi", "oauth2_access_token", body=body)

    async def refresh_access_token(self, *, refresh_token: str) -> dict[str, object]:
        self._assert_oauth_configured()
        url = self.api_base_url + self._REFRESH_TOKEN_PATH.format(version=self.api_version)
        payload = {
            "app_id": str(self.app_id),
            "secret": str(self.app_secret),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        try:
            response = await self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise TikTokAdsAPIError(f"TikTok Ads request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise TikTokAdsAPIError(f"TikTok Ads returned invalid JSON with status {response.status_code}") from exc

        if not isinstance(data, dict):
            raise TikTokAdsAPIError(f"TikTok Ads returned unexpected payload with status {response.status_code}")

        if response.is_error:
            detail = _optional_string(data.get("message")) or f"TikTok Ads request failed with status {response.status_code}"
            raise TikTokAdsAPIError(detail)

        return self._unwrap_response(data)

    async def list_authorized_advertiser_ids(self, *, access_token: str) -> list[str]:
        self._assert_oauth_configured()
        data = await self._run_sdk(
            "AuthenticationApi",
            "oauth2_advertiser_get",
            str(self.app_id),
            str(self.app_secret),
            access_token,
        )
        raw_items = self._extract_sequence(data, "list", "advertiser_ids", "advertiser_id_list", "advertiser_list")
        advertiser_ids: list[str] = []
        for item in raw_items:
            if isinstance(item, dict):
                advertiser_id = _optional_string(
                    item.get("advertiser_id") or item.get("id") or item.get("advertiserId")
                )
            else:
                advertiser_id = _optional_string(item)
            if advertiser_id and advertiser_id not in advertiser_ids:
                advertiser_ids.append(advertiser_id)
        single_advertiser_id = _optional_string(data.get("advertiser_id"))
        if single_advertiser_id and single_advertiser_id not in advertiser_ids:
            advertiser_ids.append(single_advertiser_id)
        return advertiser_ids

    async def get_advertiser_info(
        self,
        *,
        advertiser_ids: list[str],
        access_token: str,
    ) -> list[dict[str, object]]:
        if not advertiser_ids:
            return []
        data = await self._run_sdk(
            "AccountManagementApi",
            "advertiser_info",
            advertiser_ids,
            access_token,
        )
        raw_items = self._extract_sequence(data, "list", "advertiser_info_list", "advertisers")
        return [item for item in raw_items if isinstance(item, dict)]

    async def list_campaigns(self, *, advertiser_id: str, access_token: str) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        page = 1
        page_size = 1000

        while True:
            data = await self._run_sdk(
                "CampaignCreationApi",
                "campaign_get",
                advertiser_id,
                access_token,
                page=page,
                page_size=page_size,
            )
            page_results = self._extract_sequence(data, "list", "campaign_list", "campaigns")
            results.extend(item for item in page_results if isinstance(item, dict))
            page_info = self._extract_page_info(data)
            total_pages = to_int(page_info.get("total_page") or page_info.get("totalPage"))
            if total_pages > 0 and page >= total_pages:
                break
            if total_pages <= 0 and len(page_results) < page_size:
                break
            page += 1

        return results

    async def list_ads(self, *, advertiser_id: str, access_token: str) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        page = 1
        page_size = 1000

        while True:
            data = await self._run_sdk(
                "AdApi",
                "ad_get",
                advertiser_id,
                access_token,
                page=page,
                page_size=page_size,
            )
            page_results = self._extract_sequence(data, "list", "ad_list", "ads")
            results.extend(item for item in page_results if isinstance(item, dict))
            page_info = self._extract_page_info(data)
            total_pages = to_int(page_info.get("total_page") or page_info.get("totalPage"))
            if total_pages > 0 and page >= total_pages:
                break
            if total_pages <= 0 and len(page_results) < page_size:
                break
            page += 1

        return results

    async def get_integrated_report(
        self,
        *,
        advertiser_id: str,
        access_token: str,
        data_level: str,
        dimensions: list[str],
        metrics: list[str],
        start_date: str,
        end_date: str,
    ) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        total_metrics: dict[str, object] = {}
        page = 1
        page_size = 1000
        page_info: dict[str, object] = {}

        while True:
            data = await self._run_sdk(
                "ReportingApi",
                "report_integrated_get",
                "BASIC",
                access_token,
                advertiser_id=advertiser_id,
                service_type="AUCTION",
                data_level=data_level,
                dimensions=dimensions or None,
                metrics=metrics,
                start_date=start_date,
                end_date=end_date,
                page=page,
                page_size=page_size,
                enable_total_metrics=True,
            )
            page_results = self._extract_sequence(data, "list", "stats_data", "rows")
            rows.extend(item for item in page_results if isinstance(item, dict))
            if not total_metrics:
                total_metrics = self._extract_mapping(data, "total_metrics", "totalMetrics", "metrics")
            page_info = self._extract_page_info(data)
            total_pages = to_int(page_info.get("total_page") or page_info.get("totalPage"))
            if total_pages > 0 and page >= total_pages:
                break
            if total_pages <= 0 and len(page_results) < page_size:
                break
            page += 1

        return {
            "rows": rows,
            "total_metrics": total_metrics,
            "page_info": page_info,
        }

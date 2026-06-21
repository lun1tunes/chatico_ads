from __future__ import annotations

from urllib.parse import urlencode

import httpx

from ..config import settings


class MetaGraphAPIError(Exception):
    pass


class MetaGraphAPIClient:
    def __init__(
        self,
        *,
        graph_version: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        oauth_scopes: list[str] | None = None,
        oauth_config_id: str | None = None,
    ) -> None:
        self.graph_version = graph_version or settings.meta.graph_version
        self.client_id = client_id or settings.meta.app_id
        self.client_secret = client_secret or settings.meta.app_secret
        self.redirect_uri = redirect_uri or settings.meta.oauth_redirect_uri
        self.oauth_scopes = oauth_scopes or settings.meta.oauth_scopes
        self.oauth_config_id = oauth_config_id if oauth_config_id is not None else settings.meta.oauth_config_id
        self.base_graph_url = f"https://graph.facebook.com/{self.graph_version}"
        self.base_oauth_url = f"https://www.facebook.com/{self.graph_version}/dialog/oauth"
        self._client = httpx.AsyncClient(timeout=30.0)

    def build_authorization_url(self, *, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": ",".join(self.oauth_scopes),
        }
        if self.oauth_config_id:
            params["config_id"] = self.oauth_config_id
        return f"{self.base_oauth_url}?{urlencode(params)}"

    async def _request_json(self, url: str, *, params: dict[str, object] | None = None) -> dict[str, object]:
        try:
            response = await self._client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise MetaGraphAPIError(f"Meta API request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise MetaGraphAPIError(f"Meta API returned invalid JSON with status {response.status_code}") from exc

        if not isinstance(data, dict):
            raise MetaGraphAPIError(f"Meta API returned unexpected payload with status {response.status_code}")

        if response.is_error or "error" in data:
            error = data.get("error", {})
            message = error.get("message") or f"Meta API request failed with status {response.status_code}"
            raise MetaGraphAPIError(str(message))
        return data

    async def _get(self, path: str, *, params: dict[str, object]) -> dict[str, object]:
        return await self._request_json(f"{self.base_graph_url}/{path.lstrip('/')}", params=params)

    @staticmethod
    def _next_page_url(data: dict[str, object]) -> str | None:
        paging = data.get("paging")
        if not isinstance(paging, dict):
            return None
        next_url = paging.get("next")
        return next_url if isinstance(next_url, str) and next_url.strip() else None

    async def _get_paginated(self, path: str, *, params: dict[str, object]) -> list[dict[str, object]]:
        data = await self._get(path, params=params)
        rows = list(data.get("data", [])) if isinstance(data.get("data"), list) else []
        next_url = self._next_page_url(data)
        seen_urls: set[str] = set()

        while next_url:
            if next_url in seen_urls:
                raise MetaGraphAPIError("Meta API pagination loop detected")
            seen_urls.add(next_url)

            data = await self._request_json(next_url)
            page_rows = data.get("data")
            if isinstance(page_rows, list):
                rows.extend(page_rows)
            next_url = self._next_page_url(data)

        return rows

    async def aclose(self) -> None:
        await self._client.aclose()

    async def exchange_code_for_token(self, *, code: str) -> dict[str, object]:
        return await self._get(
            "oauth/access_token",
            params={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "code": code,
            },
        )

    async def exchange_for_long_lived_token(self, *, access_token: str) -> dict[str, object] | None:
        if not settings.meta.exchange_long_lived_token:
            return None
        return await self._get(
            "oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "fb_exchange_token": access_token,
            },
        )

    async def get_me(self, *, access_token: str) -> dict[str, object]:
        return await self._get("me", params={"fields": "id,name", "access_token": access_token})

    async def list_ad_accounts(self, *, access_token: str) -> list[dict[str, object]]:
        return await self._get_paginated(
            "me/adaccounts",
            params={
                "fields": "id,account_id,name,account_status,currency,timezone_name",
                "limit": 200,
                "access_token": access_token,
            },
        )

    async def get_ad_account(self, *, account_id: str, access_token: str) -> dict[str, object]:
        return await self._get(
            account_id,
            params={"fields": "id,account_id,name,currency,timezone_name,account_status", "access_token": access_token},
        )

    async def list_campaigns(self, *, account_id: str, access_token: str) -> list[dict[str, object]]:
        return await self._get_paginated(
            f"{account_id}/campaigns",
            params={"fields": "id,name,status,effective_status", "limit": 500, "access_token": access_token},
        )

    async def get_account_insights(
        self, *, account_id: str, access_token: str, since: str, until: str
    ) -> dict[str, object] | None:
        data = await self._get(
            f"{account_id}/insights",
            params={
                "fields": "spend,impressions,clicks,reach,cpm,ctr,actions",
                "level": "account",
                "limit": 1,
                "time_range": f'{{"since":"{since}","until":"{until}"}}',
                "access_token": access_token,
            },
        )
        rows = data.get("data", [])
        return rows[0] if rows else None

    async def get_campaign_insights(
        self,
        *,
        account_id: str,
        access_token: str,
        since: str,
        until: str,
    ) -> list[dict[str, object]]:
        return await self._get_paginated(
            f"{account_id}/insights",
            params={
                "fields": "campaign_id,campaign_name,spend,impressions,clicks,reach,cpm,ctr,actions",
                "level": "campaign",
                "limit": 500,
                "time_range": f'{{"since":"{since}","until":"{until}"}}',
                "access_token": access_token,
            },
        )

    async def list_ads(self, *, account_id: str, access_token: str) -> list[dict[str, object]]:
        return await self._get_paginated(
            f"{account_id}/ads",
            params={
                "fields": (
                    "id,name,campaign_id,effective_status,"
                    "creative{id,name,thumbnail_url,image_url,object_type,object_story_spec,instagram_permalink_url}"
                ),
                "limit": 500,
                "access_token": access_token,
            },
        )

    async def get_ad_insights(
        self, *, account_id: str, access_token: str, since: str, until: str
    ) -> list[dict[str, object]]:
        return await self._get_paginated(
            f"{account_id}/insights",
            params={
                "fields": "ad_id,ad_name,campaign_id,spend,impressions,clicks,reach,cpm,ctr,actions",
                "level": "ad",
                "limit": 500,
                "time_range": f'{{"since":"{since}","until":"{until}"}}',
                "access_token": access_token,
            },
        )

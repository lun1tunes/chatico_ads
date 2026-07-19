from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from urllib.parse import urlencode

import httpx

from ..config import settings


class GoogleAdsAPIError(Exception):
    pass


_SKIP_CUSTOMER_ACCESS_ERRORS = frozenset(
    {
        "CUSTOMER_NOT_ENABLED",
        "CUSTOMER_NOT_FOUND",
    }
)


class GoogleAdsConfigurationError(GoogleAdsAPIError):
    pass


class GoogleAdsAPIClient:
    def __init__(
        self,
        *,
        developer_token: str | None = None,
        api_version: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        oauth_scopes: list[str] | None = None,
        oauth_access_type: str | None = None,
        oauth_include_granted_scopes: bool | None = None,
        oauth_prompt: str | None = None,
    ) -> None:
        google_settings = settings.google_ads
        self.developer_token = developer_token or google_settings.developer_token
        self.api_version = api_version or google_settings.api_version
        self.client_id = client_id or google_settings.oauth_client_id
        self.client_secret = client_secret or google_settings.oauth_client_secret
        self.redirect_uri = redirect_uri or google_settings.oauth_redirect_uri
        self.oauth_scopes = oauth_scopes or google_settings.oauth_scopes
        self.oauth_access_type = oauth_access_type or google_settings.oauth_access_type
        self.oauth_include_granted_scopes = (
            google_settings.oauth_include_granted_scopes
            if oauth_include_granted_scopes is None
            else oauth_include_granted_scopes
        )
        self.oauth_prompt = oauth_prompt if oauth_prompt is not None else google_settings.oauth_prompt
        self.oauth_authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.oauth_token_url = "https://oauth2.googleapis.com/token"
        self.base_api_url = f"https://googleads.googleapis.com/{self.api_version}"
        self._client = httpx.AsyncClient(timeout=30.0)

    def _assert_oauth_configured(self) -> None:
        required_values = (self.developer_token, self.client_id, self.client_secret, self.redirect_uri)
        if not all(
            value and str(value).strip() and not str(value).strip().lower().startswith("replace_with_")
            for value in required_values
        ):
            raise GoogleAdsConfigurationError(
                "Google Ads OAuth is not configured. Set GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_OAUTH_CLIENT_ID, "
                "GOOGLE_OAUTH_CLIENT_SECRET, and GOOGLE_OAUTH_REDIRECT_URI."
            )

    def _assert_api_configured(self) -> None:
        if not self.developer_token or not self.developer_token.strip():
            raise GoogleAdsConfigurationError("GOOGLE_ADS_DEVELOPER_TOKEN must be configured")

    def build_authorization_url(self, *, state: str) -> str:
        self._assert_oauth_configured()
        params: dict[str, str] = {
            "client_id": str(self.client_id),
            "redirect_uri": str(self.redirect_uri),
            "response_type": "code",
            "scope": " ".join(self.oauth_scopes),
            "state": state,
            "access_type": self.oauth_access_type,
            "include_granted_scopes": "true" if self.oauth_include_granted_scopes else "false",
        }
        if self.oauth_prompt:
            params["prompt"] = self.oauth_prompt
        return f"{self.oauth_authorize_url}?{urlencode(params)}"

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, object] | None = None,
        data: Mapping[str, object] | None = None,
        json: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        try:
            response = await self._client.request(method, url, headers=headers, params=params, data=data, json=json)
        except httpx.HTTPError as exc:
            raise GoogleAdsAPIError(f"Google Ads request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise GoogleAdsAPIError(f"Google Ads returned invalid JSON with status {response.status_code}") from exc

        if not isinstance(payload, dict):
            raise GoogleAdsAPIError(f"Google Ads returned unexpected payload with status {response.status_code}")

        if response.is_error:
            error = payload.get("error")
            message = f"Google Ads request failed with status {response.status_code}"
            if isinstance(error, dict):
                error_message = error.get("message")
                if isinstance(error_message, str) and error_message.strip():
                    message = error_message
                details = error.get("details")
                if isinstance(details, list):
                    for detail in details:
                        if not isinstance(detail, dict):
                            continue
                        nested_errors = detail.get("errors")
                        if not isinstance(nested_errors, list):
                            continue
                        for nested_error in nested_errors:
                            if not isinstance(nested_error, dict):
                                continue
                            nested_message = nested_error.get("message")
                            error_code = nested_error.get("errorCode")
                            code_label = None
                            if isinstance(error_code, dict):
                                code_label = next(
                                    (value for value in error_code.values() if isinstance(value, str) and value.strip()),
                                    None,
                                )
                            if isinstance(nested_message, str) and nested_message.strip():
                                if code_label:
                                    message = f"{nested_message} [{code_label}]"
                                else:
                                    message = nested_message
                                break
                        if "[" in message or message != error_message:
                            break
            raise GoogleAdsAPIError(message)

        return payload

    async def aclose(self) -> None:
        await self._client.aclose()

    async def exchange_code_for_tokens(self, *, code: str) -> dict[str, object]:
        self._assert_oauth_configured()
        return await self._request_json(
            "POST",
            self.oauth_token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": str(self.client_id),
                "client_secret": str(self.client_secret),
                "redirect_uri": str(self.redirect_uri),
            },
        )

    async def refresh_access_token(self, *, refresh_token: str) -> dict[str, object]:
        self._assert_oauth_configured()
        return await self._request_json(
            "POST",
            self.oauth_token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": str(self.client_id),
                "client_secret": str(self.client_secret),
            },
        )

    def _build_api_headers(self, *, access_token: str, login_customer_id: str | None = None) -> dict[str, str]:
        self._assert_api_configured()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": str(self.developer_token),
        }
        if login_customer_id:
            headers["login-customer-id"] = login_customer_id.replace("-", "")
        return headers

    async def list_accessible_customers(self, *, access_token: str) -> list[str]:
        payload = await self._request_json(
            "GET",
            f"{self.base_api_url}/customers:listAccessibleCustomers",
            headers=self._build_api_headers(access_token=access_token),
        )
        resource_names = payload.get("resourceNames")
        if not isinstance(resource_names, list):
            return []
        customer_ids: list[str] = []
        for resource_name in resource_names:
            if isinstance(resource_name, str):
                customer_id = self._customer_id_from_resource_name(resource_name)
                if customer_id:
                    customer_ids.append(customer_id)
        return customer_ids

    @staticmethod
    def _is_skippable_customer_access_error(exc: GoogleAdsAPIError) -> bool:
        message = str(exc)
        return any(f"[{code}]" in message for code in _SKIP_CUSTOMER_ACCESS_ERRORS)

    async def _search_customer_clients(
        self,
        *,
        customer_id: str,
        access_token: str,
        login_customer_id: str | None,
    ) -> list[dict[str, object]]:
        return await self.search(
            customer_id=customer_id,
            access_token=access_token,
            query=(
                "SELECT "
                "customer_client.client_customer, "
                "customer_client.id, "
                "customer_client.descriptive_name, "
                "customer_client.currency_code, "
                "customer_client.time_zone, "
                "customer_client.manager, "
                "customer_client.level "
                "FROM customer_client "
                "WHERE customer_client.level <= 1"
            ),
            login_customer_id=login_customer_id,
        )

    async def list_customer_accounts(self, *, access_token: str) -> list[dict[str, object]]:
        accessible_customer_ids = await self.list_accessible_customers(access_token=access_token)
        accessible_customer_set = set(accessible_customer_ids)
        discovered_by_id: dict[str, dict[str, object]] = {}

        for seed_customer_id in accessible_customer_ids:
            queue: deque[tuple[str, int]] = deque([(seed_customer_id, 0)])
            visited_managers: set[str] = set()

            while queue:
                current_customer_id, current_depth = queue.popleft()
                if current_customer_id in visited_managers:
                    continue
                visited_managers.add(current_customer_id)

                login_customer_id = None if current_customer_id in accessible_customer_set else seed_customer_id
                try:
                    rows = await self._search_customer_clients(
                        customer_id=current_customer_id,
                        access_token=access_token,
                        login_customer_id=login_customer_id,
                    )
                except GoogleAdsAPIError as exc:
                    if self._is_skippable_customer_access_error(exc):
                        continue
                    raise

                for row in rows:
                    customer_client = row.get("customerClient") or row.get("customer_client")
                    if not isinstance(customer_client, dict):
                        continue

                    level = self._safe_int(customer_client.get("level"))
                    customer_id = self._extract_customer_id(customer_client)
                    if not customer_id:
                        continue

                    if level == 0 and current_customer_id != seed_customer_id:
                        continue

                    candidate = {
                        "external_customer_id": customer_id,
                        "resource_name": self._resource_name_from_customer_id(customer_id),
                        "descriptive_name": self._safe_optional_string(
                            customer_client.get("descriptiveName") or customer_client.get("descriptive_name")
                        )
                        or customer_id,
                        "currency_code": self._safe_optional_string(
                            customer_client.get("currencyCode") or customer_client.get("currency_code")
                        ),
                        "time_zone": self._safe_optional_string(
                            customer_client.get("timeZone") or customer_client.get("time_zone")
                        ),
                        "is_manager": bool(customer_client.get("manager")),
                        "is_directly_accessible": customer_id in accessible_customer_set,
                        "hierarchy_level": current_depth if level == 0 else current_depth + max(level, 0),
                        "root_customer_id": seed_customer_id,
                        "manager_customer_id": None if level == 0 else current_customer_id,
                        "login_customer_id": None if customer_id in accessible_customer_set else seed_customer_id,
                    }
                    existing = discovered_by_id.get(customer_id)
                    if existing is None or self._should_replace_customer(existing=existing, candidate=candidate):
                        discovered_by_id[customer_id] = candidate

                    if level > 0 and candidate["is_manager"]:
                        queue.append((customer_id, int(candidate["hierarchy_level"])))

        return sorted(
            discovered_by_id.values(),
            key=lambda item: (
                not bool(item["is_directly_accessible"]),
                not bool(item["is_manager"]),
                str(item["descriptive_name"]).lower(),
                str(item["external_customer_id"]),
            ),
        )

    async def search(
        self,
        *,
        customer_id: str,
        access_token: str,
        query: str,
        login_customer_id: str | None = None,
    ) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        next_page_token: str | None = None

        while True:
            body: dict[str, object] = {"query": query}
            if next_page_token:
                body["pageToken"] = next_page_token
            payload = await self._request_json(
                "POST",
                f"{self.base_api_url}/customers/{customer_id}/googleAds:search",
                headers=self._build_api_headers(access_token=access_token, login_customer_id=login_customer_id),
                json=body,
            )
            page_results = payload.get("results")
            if isinstance(page_results, list):
                results.extend(item for item in page_results if isinstance(item, dict))
            raw_next_page_token = payload.get("nextPageToken")
            next_page_token = (
                raw_next_page_token if isinstance(raw_next_page_token, str) and raw_next_page_token else None
            )
            if next_page_token is None:
                break

        return results

    async def get_customer(
        self,
        *,
        customer_id: str,
        access_token: str,
        login_customer_id: str | None = None,
    ) -> dict[str, object] | None:
        rows = await self.search(
            customer_id=customer_id,
            access_token=access_token,
            query=(
                "SELECT "
                "customer.id, "
                "customer.descriptive_name, "
                "customer.currency_code, "
                "customer.time_zone "
                "FROM customer "
                "LIMIT 1"
            ),
            login_customer_id=login_customer_id,
        )
        return rows[0] if rows else None

    async def list_campaigns(
        self,
        *,
        customer_id: str,
        access_token: str,
        login_customer_id: str | None = None,
    ) -> list[dict[str, object]]:
        return await self.search(
            customer_id=customer_id,
            access_token=access_token,
            query=(
                "SELECT "
                "campaign.id, "
                "campaign.name, "
                "campaign.status "
                "FROM campaign"
            ),
            login_customer_id=login_customer_id,
        )

    async def get_customer_metrics(
        self,
        *,
        customer_id: str,
        access_token: str,
        since: str,
        until: str,
        login_customer_id: str | None = None,
    ) -> dict[str, object] | None:
        rows = await self.search(
            customer_id=customer_id,
            access_token=access_token,
            query=(
                "SELECT "
                "customer.id, "
                "metrics.cost_micros, "
                "metrics.impressions, "
                "metrics.clicks, "
                "metrics.conversions "
                "FROM customer "
                f"WHERE segments.date BETWEEN '{since}' AND '{until}'"
            ),
            login_customer_id=login_customer_id,
        )
        return rows[0] if rows else None

    async def get_customer_daily_metrics(
        self,
        *,
        customer_id: str,
        access_token: str,
        since: str,
        until: str,
        login_customer_id: str | None = None,
    ) -> list[dict[str, object]]:
        return await self.search(
            customer_id=customer_id,
            access_token=access_token,
            query=(
                "SELECT "
                "segments.date, "
                "metrics.cost_micros, "
                "metrics.impressions, "
                "metrics.clicks, "
                "metrics.conversions "
                "FROM customer "
                f"WHERE segments.date BETWEEN '{since}' AND '{until}' "
                "ORDER BY segments.date"
            ),
            login_customer_id=login_customer_id,
        )

    async def get_campaign_metrics(
        self,
        *,
        customer_id: str,
        access_token: str,
        since: str,
        until: str,
        login_customer_id: str | None = None,
    ) -> list[dict[str, object]]:
        return await self.search(
            customer_id=customer_id,
            access_token=access_token,
            query=(
                "SELECT "
                "campaign.id, "
                "metrics.cost_micros, "
                "metrics.impressions, "
                "metrics.clicks, "
                "metrics.conversions "
                "FROM campaign "
                f"WHERE segments.date BETWEEN '{since}' AND '{until}'"
            ),
            login_customer_id=login_customer_id,
        )

    async def get_ad_metrics(
        self,
        *,
        customer_id: str,
        access_token: str,
        since: str,
        until: str,
        login_customer_id: str | None = None,
    ) -> list[dict[str, object]]:
        return await self.search(
            customer_id=customer_id,
            access_token=access_token,
            query=(
                "SELECT "
                "campaign.id, "
                "ad_group_ad.ad.id, "
                "ad_group_ad.ad.type, "
                "metrics.cost_micros, "
                "metrics.impressions, "
                "metrics.clicks, "
                "metrics.conversions "
                "FROM ad_group_ad "
                f"WHERE segments.date BETWEEN '{since}' AND '{until}'"
            ),
            login_customer_id=login_customer_id,
        )

    @staticmethod
    def _safe_optional_string(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _safe_int(value: object) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _resource_name_from_customer_id(customer_id: str) -> str:
        return f"customers/{customer_id}"

    @staticmethod
    def _customer_id_from_resource_name(resource_name: str) -> str | None:
        parts = resource_name.strip().split("/")
        if len(parts) != 2 or parts[0] != "customers":
            return None
        customer_id = parts[1].replace("-", "").strip()
        return customer_id or None

    @classmethod
    def _extract_customer_id(cls, customer_client: Mapping[str, object]) -> str | None:
        raw_id = customer_client.get("id")
        if raw_id is not None:
            normalized = str(raw_id).replace("-", "").strip()
            if normalized:
                return normalized
        resource_name = customer_client.get("clientCustomer") or customer_client.get("client_customer")
        if isinstance(resource_name, str):
            return cls._customer_id_from_resource_name(resource_name)
        return None

    @staticmethod
    def _should_replace_customer(*, existing: Mapping[str, object], candidate: Mapping[str, object]) -> bool:
        if bool(candidate["is_directly_accessible"]) != bool(existing["is_directly_accessible"]):
            return bool(candidate["is_directly_accessible"])
        if int(candidate["hierarchy_level"]) != int(existing["hierarchy_level"]):
            return int(candidate["hierarchy_level"]) < int(existing["hierarchy_level"])
        if bool(candidate["is_manager"]) != bool(existing["is_manager"]):
            return bool(candidate["is_manager"])
        return False

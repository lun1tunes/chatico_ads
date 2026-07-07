from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.google_ads_connection import GoogleAdsConnection
from ..models.google_ads_customer import GoogleAdsCustomer
from ..repositories.google_ads_connection import GoogleAdsConnectionRepository
from ..repositories.google_ads_customer import GoogleAdsCustomerRepository
from ..services.google_ads_report_service import GoogleAdsReportService
from ..utils.time import utcnow


class GoogleAdsOAuthUseCaseError(Exception):
    pass


class BuildGoogleAdsOAuthUrlUseCase:
    def __init__(self, *, state_service, google_ads_client) -> None:
        self.state_service = state_service
        self.google_ads_client = google_ads_client

    async def execute(self, *, user_id: str) -> dict[str, str]:
        state = self.state_service.create_state_token(user_id=user_id)
        return {"authorization_url": self.google_ads_client.build_authorization_url(state=state)}


class HandleGoogleAdsOAuthCallbackUseCase:
    def __init__(self, *, session: AsyncSession, state_service, google_ads_client, encryption_service) -> None:
        self.session = session
        self.state_service = state_service
        self.google_ads_client = google_ads_client
        self.encryption_service = encryption_service
        self.connection_repo = GoogleAdsConnectionRepository(session)
        self.customer_repo = GoogleAdsCustomerRepository(session)

    async def execute(self, *, code: str, state: str) -> dict[str, object]:
        payload = self.state_service.decode_state_token(state)
        user_id = str(payload["sub"])

        token_data = await self.google_ads_client.exchange_code_for_tokens(code=code)
        access_token = str(token_data["access_token"])
        refresh_token = self._normalize_refresh_token(token_data.get("refresh_token"))
        expires_in = self._safe_int(token_data.get("expires_in"))
        scopes = self._normalize_scopes(token_data.get("scope"))

        customers = await self.google_ads_client.list_customer_accounts(access_token=access_token)
        if not customers:
            raise GoogleAdsOAuthUseCaseError(
                "No active Google Ads accounts were found for this Google user. "
                "Finish Google Ads signup, reactivate the account in Google Ads, or sign in with another Google account."
            )
        connection = await self.connection_repo.get_by_user(user_id=user_id)

        if connection is None and refresh_token is None:
            raise GoogleAdsOAuthUseCaseError(
                "Google OAuth did not return a refresh token. Reconnect and approve consent again."
            )

        if connection is None:
            connection = GoogleAdsConnection(
                id=str(uuid4()),
                user_id=user_id,
                refresh_token_encrypted=self.encryption_service.encrypt(str(refresh_token)),
                access_token_encrypted=self.encryption_service.encrypt(access_token),
                access_token_expires_at=(utcnow() + timedelta(seconds=expires_in)) if expires_in else None,
                scopes=scopes,
            )
            await self.connection_repo.create(connection)
            existing_customers_by_id: dict[str, GoogleAdsCustomer] = {}
        else:
            if refresh_token is not None:
                connection.refresh_token_encrypted = self.encryption_service.encrypt(refresh_token)
            connection.access_token_encrypted = self.encryption_service.encrypt(access_token)
            connection.access_token_expires_at = (utcnow() + timedelta(seconds=expires_in)) if expires_in else None
            connection.scopes = scopes or connection.scopes
            existing_customers_by_id = {customer.external_customer_id: customer for customer in connection.customers}

        seen_customer_ids: set[str] = set()
        for remote_customer in customers:
            external_customer_id = str(remote_customer["external_customer_id"])
            seen_customer_ids.add(external_customer_id)
            customer = existing_customers_by_id.get(external_customer_id)

            if customer is None:
                customer = GoogleAdsCustomer(
                    id=str(uuid4()),
                    connection_id=connection.id,
                    external_customer_id=external_customer_id,
                    resource_name=str(remote_customer["resource_name"]),
                    descriptive_name=str(remote_customer["descriptive_name"]),
                    currency_code=self._optional_string(remote_customer.get("currency_code")),
                    time_zone=self._optional_string(remote_customer.get("time_zone")),
                    is_manager=bool(remote_customer.get("is_manager")),
                    is_directly_accessible=bool(remote_customer.get("is_directly_accessible")),
                    hierarchy_level=self._safe_int(remote_customer.get("hierarchy_level")),
                    root_customer_id=self._optional_string(remote_customer.get("root_customer_id")),
                    manager_customer_id=self._optional_string(remote_customer.get("manager_customer_id")),
                    login_customer_id=self._optional_string(remote_customer.get("login_customer_id")),
                    last_synced_at=utcnow(),
                )
                await self.customer_repo.create(customer)
                continue

            customer.resource_name = str(remote_customer["resource_name"])
            customer.descriptive_name = str(remote_customer["descriptive_name"])
            customer.currency_code = self._optional_string(remote_customer.get("currency_code"))
            customer.time_zone = self._optional_string(remote_customer.get("time_zone"))
            customer.is_manager = bool(remote_customer.get("is_manager"))
            customer.is_directly_accessible = bool(remote_customer.get("is_directly_accessible"))
            customer.hierarchy_level = self._safe_int(remote_customer.get("hierarchy_level"))
            customer.root_customer_id = self._optional_string(remote_customer.get("root_customer_id"))
            customer.manager_customer_id = self._optional_string(remote_customer.get("manager_customer_id"))
            customer.login_customer_id = self._optional_string(remote_customer.get("login_customer_id"))
            customer.last_synced_at = utcnow()

        for customer in list(existing_customers_by_id.values()):
            if customer.external_customer_id not in seen_customer_ids:
                await self.customer_repo.delete(customer)

        await self.session.commit()
        return {
            "user_id": user_id,
            "connection_id": connection.id,
            "customer_count": len(seen_customer_ids),
        }

    @staticmethod
    def _normalize_refresh_token(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _normalize_scopes(value: object) -> str:
        if isinstance(value, list):
            return ",".join(str(item).strip() for item in value if str(item).strip())
        if isinstance(value, str):
            parts = [item.strip() for item in value.replace(",", " ").split() if item.strip()]
            return ",".join(parts)
        return ""

    @staticmethod
    def _safe_int(value: object) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class ListGoogleAdsCustomersUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self.customer_repo = GoogleAdsCustomerRepository(session)

    async def execute(self, *, user_id: str) -> list[GoogleAdsCustomer]:
        return await self.customer_repo.list_for_user(user_id)


class DisconnectGoogleAdsUseCase:
    def __init__(self, *, session: AsyncSession, report_service: GoogleAdsReportService) -> None:
        self.session = session
        self.report_service = report_service
        self.connection_repo = GoogleAdsConnectionRepository(session)

    async def execute(self, *, user_id: str) -> None:
        connection = await self.connection_repo.get_by_user(user_id=user_id)
        if connection is None:
            return

        await self.session.delete(connection)
        await self.session.commit()
        self.report_service.clear_user_cache(user_id=user_id)

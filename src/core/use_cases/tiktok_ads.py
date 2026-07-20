from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.tiktok_ads_advertiser import TikTokAdsAdvertiser
from ..models.tiktok_ads_connection import TikTokAdsConnection
from ..repositories.tiktok_ads_advertiser import TikTokAdsAdvertiserRepository
from ..repositories.tiktok_ads_connection import TikTokAdsConnectionRepository
from ..services.tiktok_ads_report_service import TikTokAdsReportService
from ..utils.time import utcnow


class TikTokAdsOAuthUseCaseError(Exception):
    pass


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


class BuildTikTokAdsOAuthUrlUseCase:
    def __init__(self, *, state_service, tiktok_ads_client) -> None:
        self.state_service = state_service
        self.tiktok_ads_client = tiktok_ads_client

    async def execute(self, *, user_id: str) -> dict[str, str]:
        state = self.state_service.create_state_token(user_id=user_id)
        return {"authorization_url": self.tiktok_ads_client.build_authorization_url(state=state)}


class HandleTikTokAdsOAuthCallbackUseCase:
    def __init__(self, *, session: AsyncSession, state_service, tiktok_ads_client, encryption_service) -> None:
        self.session = session
        self.state_service = state_service
        self.tiktok_ads_client = tiktok_ads_client
        self.encryption_service = encryption_service
        self.connection_repo = TikTokAdsConnectionRepository(session)
        self.advertiser_repo = TikTokAdsAdvertiserRepository(session)

    async def execute(self, *, code: str, state: str) -> dict[str, object]:
        payload = self.state_service.decode_state_token(state)
        user_id = str(payload["sub"])

        token_data = await self.tiktok_ads_client.exchange_code_for_tokens(code=code)
        access_token = _optional_string(token_data.get("access_token"))
        if access_token is None:
            raise TikTokAdsOAuthUseCaseError("TikTok OAuth did not return an access token")
        refresh_token = _optional_string(token_data.get("refresh_token"))
        expires_in = self._safe_int(token_data.get("expires_in"))
        scopes = self._normalize_scopes(token_data.get("scope") or token_data.get("scopes"))

        advertiser_ids = await self.tiktok_ads_client.list_authorized_advertiser_ids(access_token=access_token)
        advertiser_info_list = await self.tiktok_ads_client.get_advertiser_info(
            advertiser_ids=advertiser_ids,
            access_token=access_token,
        )
        advertiser_info_by_id = {
            advertiser_id: row
            for row in advertiser_info_list
            if (advertiser_id := self._extract_remote_advertiser_id(row))
        }

        connection = await self.connection_repo.get_by_user(user_id=user_id)
        if connection is None and refresh_token is None:
            raise TikTokAdsOAuthUseCaseError(
                "TikTok OAuth did not return a refresh token. Reconnect and approve access again."
            )

        if connection is None:
            connection = TikTokAdsConnection(
                id=str(uuid4()),
                user_id=user_id,
                refresh_token_encrypted=self.encryption_service.encrypt(str(refresh_token)),
                access_token_encrypted=self.encryption_service.encrypt(access_token),
                access_token_expires_at=(utcnow() + timedelta(seconds=expires_in)) if expires_in else None,
                scopes=scopes,
            )
            await self.connection_repo.create(connection)
            existing_advertisers_by_id: dict[str, TikTokAdsAdvertiser] = {}
        else:
            if refresh_token is not None:
                connection.refresh_token_encrypted = self.encryption_service.encrypt(refresh_token)
            connection.access_token_encrypted = self.encryption_service.encrypt(access_token)
            connection.access_token_expires_at = (utcnow() + timedelta(seconds=expires_in)) if expires_in else None
            connection.scopes = scopes or connection.scopes
            existing_advertisers_by_id = {
                advertiser.advertiser_id: advertiser for advertiser in connection.advertisers
            }

        seen_advertiser_ids: set[str] = set()
        for advertiser_id in advertiser_ids:
            seen_advertiser_ids.add(advertiser_id)
            remote_advertiser = advertiser_info_by_id.get(advertiser_id, {})
            advertiser = existing_advertisers_by_id.get(advertiser_id)
            resolved_name = _optional_string(
                remote_advertiser.get("name")
                or remote_advertiser.get("advertiser_name")
                or remote_advertiser.get("display_name")
            ) or advertiser_id

            if advertiser is None:
                advertiser = TikTokAdsAdvertiser(
                    id=str(uuid4()),
                    connection_id=connection.id,
                    advertiser_id=advertiser_id,
                    name=resolved_name,
                    currency=self._optional_string(
                        remote_advertiser.get("currency") or remote_advertiser.get("currency_code")
                    ),
                    timezone_name=self._optional_string(
                        remote_advertiser.get("timezone")
                        or remote_advertiser.get("timezone_name")
                        or remote_advertiser.get("timezoneName")
                    ),
                    status=self._optional_string(
                        remote_advertiser.get("status")
                        or remote_advertiser.get("advertiser_status")
                        or remote_advertiser.get("account_status")
                    ),
                    last_synced_at=utcnow(),
                )
                await self.advertiser_repo.create(advertiser)
                continue

            advertiser.name = resolved_name
            advertiser.currency = self._optional_string(
                remote_advertiser.get("currency") or remote_advertiser.get("currency_code")
            )
            advertiser.timezone_name = self._optional_string(
                remote_advertiser.get("timezone")
                or remote_advertiser.get("timezone_name")
                or remote_advertiser.get("timezoneName")
            )
            advertiser.status = self._optional_string(
                remote_advertiser.get("status")
                or remote_advertiser.get("advertiser_status")
                or remote_advertiser.get("account_status")
            )
            advertiser.last_synced_at = utcnow()

        for advertiser in list(existing_advertisers_by_id.values()):
            if advertiser.advertiser_id not in seen_advertiser_ids:
                await self.advertiser_repo.delete(advertiser)

        await self.session.commit()
        return {
            "user_id": user_id,
            "connection_id": connection.id,
            "advertiser_count": len(seen_advertiser_ids),
        }

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
        return _optional_string(value)

    @staticmethod
    def _extract_remote_advertiser_id(value: object) -> str | None:
        if not isinstance(value, dict):
            return None
        return _optional_string(value.get("advertiser_id") or value.get("id") or value.get("advertiserId"))


class ListTikTokAdsAdvertisersUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self.advertiser_repo = TikTokAdsAdvertiserRepository(session)

    async def execute(self, *, user_id: str) -> list[TikTokAdsAdvertiser]:
        return await self.advertiser_repo.list_for_user(user_id)


class DisconnectTikTokAdsUseCase:
    def __init__(self, *, session: AsyncSession, report_service: TikTokAdsReportService) -> None:
        self.session = session
        self.report_service = report_service
        self.connection_repo = TikTokAdsConnectionRepository(session)

    async def execute(self, *, user_id: str) -> None:
        connection = await self.connection_repo.get_by_user(user_id=user_id)
        if connection is None:
            return

        await self.session.delete(connection)
        await self.session.commit()
        self.report_service.clear_user_cache(user_id=user_id)


class DisconnectTikTokAdsAdvertiserUseCase:
    def __init__(self, *, session: AsyncSession, report_service: TikTokAdsReportService) -> None:
        self.session = session
        self.report_service = report_service
        self.advertiser_repo = TikTokAdsAdvertiserRepository(session)

    async def execute(self, *, user_id: str, external_advertiser_id: str) -> bool:
        advertiser = await self.advertiser_repo.get_for_user(
            user_id=user_id,
            external_advertiser_id=external_advertiser_id,
        )
        if advertiser is None:
            return False

        connection = advertiser.connection
        should_remove_connection = connection is not None and len(connection.advertisers) <= 1

        if should_remove_connection and connection is not None:
            await self.session.delete(connection)
        else:
            await self.advertiser_repo.delete(advertiser)

        await self.session.commit()
        self.report_service.clear_user_cache(user_id=user_id)
        return True

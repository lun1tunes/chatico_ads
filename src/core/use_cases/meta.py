from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.meta_ad_account import MetaAdAccount
from ..models.meta_connection import MetaConnection
from ..repositories.meta_ad_account import MetaAdAccountRepository
from ..repositories.meta_connection import MetaConnectionRepository
from ..utils.time import utcnow


class MetaOAuthUseCaseError(Exception):
    pass


def _serialize_meta_scopes(scope_value: object) -> str:
    if isinstance(scope_value, list):
        return ",".join(str(scope) for scope in scope_value)
    return ""


async def _sync_meta_connection_accounts(
    *,
    connection: MetaConnection,
    access_token: str,
    meta_client,
    ad_account_repo: MetaAdAccountRepository,
) -> dict[str, int]:
    remote_accounts = await meta_client.list_ad_accounts(access_token=access_token)
    existing_accounts = await ad_account_repo.list_for_connection(connection.id)
    existing_by_external = {account.external_id: account for account in existing_accounts}
    seen_external_ids: set[str] = set()
    sync_time = utcnow()
    added_accounts = 0
    updated_accounts = 0
    removed_accounts = 0

    for remote in remote_accounts:
        external_id = str(remote.get("id"))
        seen_external_ids.add(external_id)
        account = existing_by_external.get(external_id)
        if account is None:
            account = MetaAdAccount(
                id=str(uuid4()),
                connection_id=connection.id,
                external_id=external_id,
                account_id=str(remote.get("account_id") or external_id),
                name=str(remote.get("name") or external_id),
                currency=remote.get("currency"),
                timezone_name=remote.get("timezone_name"),
                account_status=remote.get("account_status"),
                last_synced_at=sync_time,
            )
            await ad_account_repo.create(account)
            added_accounts += 1
        else:
            account.account_id = str(remote.get("account_id") or account.account_id)
            account.name = str(remote.get("name") or account.name)
            account.currency = remote.get("currency")
            account.timezone_name = remote.get("timezone_name")
            account.account_status = remote.get("account_status")
            account.last_synced_at = sync_time
            updated_accounts += 1

    for external_id, account in existing_by_external.items():
        if external_id not in seen_external_ids:
            await ad_account_repo.delete(account)
            removed_accounts += 1

    return {
        "connected_accounts": len(remote_accounts),
        "added_accounts": added_accounts,
        "updated_accounts": updated_accounts,
        "removed_accounts": removed_accounts,
    }


class BuildMetaOAuthUrlUseCase:
    def __init__(self, *, state_service, meta_client) -> None:
        self.state_service = state_service
        self.meta_client = meta_client

    async def execute(self, *, user_id: str) -> dict[str, str]:
        state = self.state_service.create_state_token(user_id=user_id)
        return {"authorization_url": self.meta_client.build_authorization_url(state=state)}


class HandleMetaOAuthCallbackUseCase:
    def __init__(self, *, session: AsyncSession, state_service, meta_client, encryption_service) -> None:
        self.session = session
        self.state_service = state_service
        self.meta_client = meta_client
        self.encryption_service = encryption_service
        self.connection_repo = MetaConnectionRepository(session)
        self.ad_account_repo = MetaAdAccountRepository(session)

    async def execute(self, *, code: str, state: str) -> dict[str, object]:
        payload = self.state_service.decode_state_token(state)
        user_id = str(payload["sub"])
        token_data = await self.meta_client.exchange_code_for_token(code=code)
        access_token = str(token_data["access_token"])
        expires_in = token_data.get("expires_in")

        if expires_in:
            try:
                long_lived = await self.meta_client.exchange_for_long_lived_token(access_token=access_token)
                if long_lived and long_lived.get("access_token"):
                    token_data = long_lived
                    access_token = str(long_lived["access_token"])
                    expires_in = long_lived.get("expires_in")
            except Exception:
                pass

        meta_user = await self.meta_client.get_me(access_token=access_token)
        meta_user_id = str(meta_user["id"])
        meta_user_name = str(meta_user.get("name") or meta_user_id)
        connection = await self.connection_repo.get_by_user_and_meta_user(user_id=user_id, meta_user_id=meta_user_id)
        if connection is None:
            connection = MetaConnection(
                id=str(uuid4()),
                user_id=user_id,
                meta_user_id=meta_user_id,
                meta_user_name=meta_user_name,
                access_token_encrypted=self.encryption_service.encrypt(access_token),
                access_token_expires_at=(utcnow() + timedelta(seconds=int(expires_in))) if expires_in else None,
                scopes=_serialize_meta_scopes(token_data.get("scope")),
            )
            await self.connection_repo.create(connection)
        else:
            connection.meta_user_name = meta_user_name
            connection.access_token_encrypted = self.encryption_service.encrypt(access_token)
            connection.access_token_expires_at = (utcnow() + timedelta(seconds=int(expires_in))) if expires_in else None
            connection.scopes = _serialize_meta_scopes(token_data.get("scope"))

        await _sync_meta_connection_accounts(
            connection=connection,
            access_token=access_token,
            meta_client=self.meta_client,
            ad_account_repo=self.ad_account_repo,
        )

        await self.session.commit()
        return {"user_id": user_id, "connection_id": connection.id}


class RefreshMetaAdAccountsUseCase:
    def __init__(self, *, session: AsyncSession, meta_client, encryption_service, report_service=None) -> None:
        self.session = session
        self.meta_client = meta_client
        self.encryption_service = encryption_service
        self.report_service = report_service
        self.connection_repo = MetaConnectionRepository(session)
        self.ad_account_repo = MetaAdAccountRepository(session)

    async def execute(self, *, user_id: str) -> dict[str, int]:
        connections = await self.connection_repo.list_for_user(user_id)
        if not connections:
            return {
                "refreshed_connections": 0,
                "connected_accounts": 0,
                "added_accounts": 0,
                "updated_accounts": 0,
                "removed_accounts": 0,
            }

        summary = {
            "refreshed_connections": 0,
            "connected_accounts": 0,
            "added_accounts": 0,
            "updated_accounts": 0,
            "removed_accounts": 0,
        }

        for connection in connections:
            access_token = self.encryption_service.decrypt(connection.access_token_encrypted)
            sync_result = await _sync_meta_connection_accounts(
                connection=connection,
                access_token=access_token,
                meta_client=self.meta_client,
                ad_account_repo=self.ad_account_repo,
            )
            summary["refreshed_connections"] += 1
            summary["connected_accounts"] += sync_result["connected_accounts"]
            summary["added_accounts"] += sync_result["added_accounts"]
            summary["updated_accounts"] += sync_result["updated_accounts"]
            summary["removed_accounts"] += sync_result["removed_accounts"]

        await self.session.commit()

        if self.report_service is not None:
            self.report_service.clear_user_cache(user_id=user_id)

        return summary


class ListMetaAdAccountsUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self.ad_account_repo = MetaAdAccountRepository(session)

    async def execute(self, *, user_id: str) -> list[MetaAdAccount]:
        return await self.ad_account_repo.list_for_user(user_id)


class DisconnectMetaUseCase:
    def __init__(self, *, session: AsyncSession, report_service=None) -> None:
        self.session = session
        self.report_service = report_service
        self.connection_repo = MetaConnectionRepository(session)

    async def execute(self, *, user_id: str) -> None:
        connections = await self.connection_repo.list_for_user(user_id)
        for connection in connections:
            await self.session.delete(connection)

        if connections:
            await self.session.commit()

        if self.report_service is not None:
            self.report_service.clear_user_cache(user_id=user_id)


class DisconnectMetaAdAccountUseCase:
    def __init__(self, *, session: AsyncSession, report_service=None) -> None:
        self.session = session
        self.report_service = report_service
        self.ad_account_repo = MetaAdAccountRepository(session)

    async def execute(self, *, user_id: str, external_id: str) -> bool:
        account = await self.ad_account_repo.get_for_user(user_id=user_id, external_id=external_id)
        if account is None:
            return False

        connection = account.connection
        should_remove_connection = connection is not None and len(connection.ad_accounts) <= 1

        if should_remove_connection and connection is not None:
            await self.session.delete(connection)
        else:
            await self.ad_account_repo.delete(account)

        await self.session.commit()

        if self.report_service is not None:
            self.report_service.clear_user_cache(user_id=user_id)
        return True

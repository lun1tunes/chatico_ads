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
                scopes=",".join(token_data.get("scope", []) if isinstance(token_data.get("scope"), list) else []),
            )
            await self.connection_repo.create(connection)
            existing_by_external: dict[str, MetaAdAccount] = {}
        else:
            connection.meta_user_name = meta_user_name
            connection.access_token_encrypted = self.encryption_service.encrypt(access_token)
            connection.access_token_expires_at = (utcnow() + timedelta(seconds=int(expires_in))) if expires_in else None
            existing_by_external = {account.external_id: account for account in connection.ad_accounts}
        remote_accounts = await self.meta_client.list_ad_accounts(access_token=access_token)
        seen_external_ids: set[str] = set()

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
                    last_synced_at=utcnow(),
                )
                await self.ad_account_repo.create(account)
            else:
                account.account_id = str(remote.get("account_id") or account.account_id)
                account.name = str(remote.get("name") or account.name)
                account.currency = remote.get("currency")
                account.timezone_name = remote.get("timezone_name")
                account.account_status = remote.get("account_status")
                account.last_synced_at = utcnow()

        for external_id, account in existing_by_external.items():
            if external_id not in seen_external_ids:
                await self.ad_account_repo.delete(account)

        await self.session.commit()
        return {"user_id": user_id, "connection_id": connection.id}


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

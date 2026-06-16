from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class IPasswordService(Protocol):
    def hash_password(self, password: str) -> str: ...

    def verify_password(self, password: str, password_hash: str) -> bool: ...


class IEncryptionService(Protocol):
    def encrypt(self, plaintext: str) -> str: ...

    def decrypt(self, ciphertext: str) -> str: ...


class IJWTService(Protocol):
    def create_access_token(self, *, subject: str) -> str: ...

    def create_refresh_token(self, *, subject: str, session_id: str) -> str: ...

    def decode_access_token(self, token: str) -> dict[str, Any]: ...

    def decode_refresh_token(self, token: str) -> dict[str, Any]: ...


class IMetaGraphClient(Protocol):
    def build_authorization_url(self, *, state: str) -> str: ...

    async def exchange_code_for_token(self, *, code: str) -> dict[str, Any]: ...

    async def exchange_for_long_lived_token(self, *, access_token: str) -> dict[str, Any] | None: ...

    async def get_me(self, *, access_token: str) -> dict[str, Any]: ...

    async def list_ad_accounts(self, *, access_token: str) -> list[dict[str, Any]]: ...

    async def get_ad_account(self, *, account_id: str, access_token: str) -> dict[str, Any]: ...

    async def list_campaigns(self, *, account_id: str, access_token: str) -> list[dict[str, Any]]: ...

    async def get_account_insights(self, *, account_id: str, access_token: str, since: str, until: str) -> dict[str, Any] | None: ...

    async def get_campaign_insights(
        self,
        *,
        account_id: str,
        access_token: str,
        since: str,
        until: str,
    ) -> list[dict[str, Any]]: ...

    async def list_ads(self, *, account_id: str, access_token: str) -> list[dict[str, Any]]: ...

    async def get_ad_insights(self, *, account_id: str, access_token: str, since: str, until: str) -> list[dict[str, Any]]: ...


class ILLMClient(Protocol):
    async def generate(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> str: ...


class IStateTokenService(Protocol):
    def create_state_token(self, *, user_id: str) -> str: ...

    def decode_state_token(self, state: str) -> dict[str, Any]: ...


class IDateRangeService(Protocol):
    def build_periods(self, *, days: int, now: datetime | None = None) -> dict[str, dict[str, str]]: ...

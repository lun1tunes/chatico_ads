from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest
from sqlalchemy import select

from core.models.auth_session import AuthSession
from core.models.google_ads_connection import GoogleAdsConnection
from core.models.meta_ad_account import MetaAdAccount
from core.models.meta_connection import MetaConnection
from core.models.meta_data_deletion_request import MetaDataDeletionRequest
from core.models.meta_report_snapshot import MetaReportSnapshot
from core.models.user import User
from core.models.user_ai_provider_key import UserAIProviderKey
from core.security.encryption_service import EncryptionService
from core.services.meta_signed_request_service import MetaSignedRequestService
from core.use_cases.meta_data_deletion import (
    GetMetaDataDeletionStatusUseCase,
    HandleMetaDataDeletionCallbackUseCase,
    MetaDataDeletionUseCaseError,
)
from core.utils.time import utcnow


def _encode_base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _build_signed_request(*, payload: dict[str, object], app_secret: str) -> str:
    encoded_payload = _encode_base64url(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(app_secret.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).digest()
    encoded_signature = _encode_base64url(signature)
    return f"{encoded_signature}.{encoded_payload}"


@pytest.mark.unit
@pytest.mark.use_case
async def test_meta_data_deletion_callback_deletes_matching_users_and_related_records(db_session):
    encryption_service = EncryptionService()
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    db_session.add(
        MetaConnection(
            id="meta-conn-1",
            user_id="user-1",
            meta_user_id="meta-user-1",
            meta_user_name="Meta Owner",
            access_token_encrypted=encryption_service.encrypt("meta-token"),
            scopes="ads_read",
        )
    )
    db_session.add(
        MetaAdAccount(
            id="meta-acc-1",
            connection_id="meta-conn-1",
            external_id="act_1",
            account_id="111",
            name="Main account",
            currency="USD",
            timezone_name="Asia/Almaty",
            account_status=1,
        )
    )
    db_session.add(
        MetaReportSnapshot(
            id="snapshot-1",
            meta_ad_account_id="meta-acc-1",
            requested_days=30,
            current_since=utcnow().date(),
            current_until=utcnow().date(),
            previous_since=utcnow().date(),
            previous_until=utcnow().date(),
            payload={"account": {"id": "act_1"}},
            source_fetched_at=utcnow(),
            expires_at=utcnow(),
        )
    )
    db_session.add(
        GoogleAdsConnection(
            id="google-conn-1",
            user_id="user-1",
            refresh_token_encrypted=encryption_service.encrypt("google-refresh"),
            access_token_encrypted=encryption_service.encrypt("google-access"),
            scopes="https://www.googleapis.com/auth/adwords",
        )
    )
    db_session.add(
        UserAIProviderKey(
            id="key-1",
            user_id="user-1",
            provider="gemini",
            api_key_encrypted=encryption_service.encrypt("gemini-key"),
        )
    )
    db_session.add(
        AuthSession(
            id="session-1",
            user_id="user-1",
            refresh_token_hash="refresh-hash",
            expires_at=utcnow(),
        )
    )
    await db_session.commit()

    signed_request_service = MetaSignedRequestService(
        app_secret="test-meta-secret",
        public_app_url="http://localhost:8000",
        api_v1_prefix="/api/v1",
    )
    signed_request = _build_signed_request(
        payload={"algorithm": "HMAC-SHA256", "user_id": "meta-user-1"},
        app_secret="test-meta-secret",
    )

    result = await HandleMetaDataDeletionCallbackUseCase(
        session=db_session,
        signed_request_service=signed_request_service,
    ).execute(signed_request=signed_request)

    assert result["confirmation_code"]
    assert result["url"].endswith(f"/api/v1/meta/data-deletion/status/{result['confirmation_code']}")

    assert await db_session.get(User, "user-1") is None
    assert (await db_session.execute(select(MetaConnection))).scalars().all() == []
    assert (await db_session.execute(select(MetaAdAccount))).scalars().all() == []
    assert (await db_session.execute(select(MetaReportSnapshot))).scalars().all() == []
    assert (await db_session.execute(select(GoogleAdsConnection))).scalars().all() == []
    assert (await db_session.execute(select(UserAIProviderKey))).scalars().all() == []
    assert (await db_session.execute(select(AuthSession))).scalars().all() == []

    request = await GetMetaDataDeletionStatusUseCase(session=db_session).execute(
        confirmation_code=result["confirmation_code"]
    )
    assert request is not None
    assert request.status == "completed"
    assert request.deleted_users_count == 1
    assert request.completed_at is not None


@pytest.mark.unit
@pytest.mark.use_case
async def test_meta_data_deletion_callback_returns_completed_request_when_user_data_is_missing(db_session):
    signed_request_service = MetaSignedRequestService(
        app_secret="test-meta-secret",
        public_app_url="http://localhost:8000",
        api_v1_prefix="/api/v1",
    )
    signed_request = _build_signed_request(
        payload={"algorithm": "HMAC-SHA256", "user_id": "unknown-meta-user"},
        app_secret="test-meta-secret",
    )

    result = await HandleMetaDataDeletionCallbackUseCase(
        session=db_session,
        signed_request_service=signed_request_service,
    ).execute(signed_request=signed_request)

    request = await db_session.get(MetaDataDeletionRequest, result["confirmation_code"])
    assert request is not None
    assert request.status == "completed"
    assert request.deleted_users_count == 0
    assert "No matching application data" in request.detail


@pytest.mark.unit
@pytest.mark.use_case
async def test_meta_data_deletion_callback_rejects_invalid_signed_request(db_session):
    signed_request_service = MetaSignedRequestService(
        app_secret="test-meta-secret",
        public_app_url="http://localhost:8000",
        api_v1_prefix="/api/v1",
    )
    invalid_signed_request = _build_signed_request(
        payload={"algorithm": "HMAC-SHA256", "user_id": "meta-user-1"},
        app_secret="wrong-secret",
    )

    with pytest.raises(MetaDataDeletionUseCaseError, match="signature is invalid"):
        await HandleMetaDataDeletionCallbackUseCase(
            session=db_session,
            signed_request_service=signed_request_service,
        ).execute(signed_request=invalid_signed_request)

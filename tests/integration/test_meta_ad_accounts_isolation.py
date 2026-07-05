from __future__ import annotations

import pytest
from sqlalchemy import select

from core.models.google_ads_connection import GoogleAdsConnection
from core.models.meta_ad_account import MetaAdAccount
from core.models.meta_connection import MetaConnection
from core.models.meta_report_snapshot import MetaReportSnapshot
from core.models.user import User
from core.utils.time import utcnow


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.api
async def test_meta_ad_accounts_api_isolates_users(async_client, db_session):
    user_a_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner-a@example.com",
            "password": "StrongPass123",
            "locale": "en",
        },
    )
    user_b_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner-b@example.com",
            "password": "StrongPass123",
            "locale": "en",
        },
    )

    assert user_a_response.status_code == 201
    assert user_b_response.status_code == 201

    user_a_id = user_a_response.json()["user"]["id"]
    user_b_id = user_b_response.json()["user"]["id"]
    user_b_token = user_b_response.json()["access_token"]

    db_session.add_all(
        [
            MetaConnection(
                id="conn-a",
                user_id=user_a_id,
                meta_user_id="meta-a",
                meta_user_name="Meta A",
                access_token_encrypted="token-a",
            ),
            MetaAdAccount(
                id="acc-a",
                connection_id="conn-a",
                external_id="act_a",
                account_id="111",
                name="Account A",
            ),
        ]
    )
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/meta/ad-accounts",
        headers=_auth_header(user_b_token),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
@pytest.mark.api
async def test_meta_disconnect_api_removes_only_current_users_meta_data(async_client, db_session):
    user_a_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "disconnect-a@example.com",
            "password": "StrongPass123",
            "locale": "en",
        },
    )
    user_b_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "disconnect-b@example.com",
            "password": "StrongPass123",
            "locale": "en",
        },
    )

    assert user_a_response.status_code == 201
    assert user_b_response.status_code == 201

    user_a_id = user_a_response.json()["user"]["id"]
    user_b_id = user_b_response.json()["user"]["id"]
    user_a_token = user_a_response.json()["access_token"]
    today = utcnow().date()

    db_session.add_all(
        [
            MetaConnection(
                id="conn-a",
                user_id=user_a_id,
                meta_user_id="meta-a",
                meta_user_name="Meta A",
                access_token_encrypted="token-a",
            ),
            MetaConnection(
                id="conn-b",
                user_id=user_b_id,
                meta_user_id="meta-b",
                meta_user_name="Meta B",
                access_token_encrypted="token-b",
            ),
            MetaAdAccount(
                id="acc-a",
                connection_id="conn-a",
                external_id="act_a",
                account_id="111",
                name="Account A",
            ),
            MetaAdAccount(
                id="acc-b",
                connection_id="conn-b",
                external_id="act_b",
                account_id="222",
                name="Account B",
            ),
            MetaReportSnapshot(
                id="snapshot-a",
                meta_ad_account_id="acc-a",
                requested_days=30,
                current_since=today,
                current_until=today,
                previous_since=today,
                previous_until=today,
                payload={"account": {"id": "act_a"}},
                source_fetched_at=utcnow(),
                expires_at=utcnow(),
            ),
            MetaReportSnapshot(
                id="snapshot-b",
                meta_ad_account_id="acc-b",
                requested_days=30,
                current_since=today,
                current_until=today,
                previous_since=today,
                previous_until=today,
                payload={"account": {"id": "act_b"}},
                source_fetched_at=utcnow(),
                expires_at=utcnow(),
            ),
            GoogleAdsConnection(
                id="google-a",
                user_id=user_a_id,
                refresh_token_encrypted="refresh-token-a",
                access_token_encrypted="access-token-a",
                scopes="https://www.googleapis.com/auth/adwords",
            ),
        ]
    )
    await db_session.commit()

    response = await async_client.delete(
        "/api/v1/meta/connections",
        headers=_auth_header(user_a_token),
    )

    assert response.status_code == 204
    assert await db_session.get(User, user_a_id) is not None
    assert await db_session.get(GoogleAdsConnection, "google-a") is not None
    assert await db_session.get(MetaConnection, "conn-a") is None
    assert await db_session.get(MetaAdAccount, "acc-a") is None

    remaining_snapshots = (await db_session.execute(select(MetaReportSnapshot))).scalars().all()
    remaining_connections = (await db_session.execute(select(MetaConnection))).scalars().all()

    assert [snapshot.id for snapshot in remaining_snapshots] == ["snapshot-b"]
    assert [connection.id for connection in remaining_connections] == ["conn-b"]

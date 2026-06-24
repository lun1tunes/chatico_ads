from __future__ import annotations

import pytest

from core.models.meta_ad_account import MetaAdAccount
from core.models.meta_connection import MetaConnection
from core.models.user import User


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

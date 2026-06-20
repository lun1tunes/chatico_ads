from __future__ import annotations

import pytest


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.api
async def test_register_refresh_me_and_logout_flow(async_client):
    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "StrongPass123",
            "locale": "kz",
        },
    )

    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["user"]["email"] == "owner@example.com"
    assert register_payload["user"]["locale"] == "kz"
    assert "refresh_token=" in register_response.headers["set-cookie"]

    me_response = await async_client.get(
        "/api/v1/auth/me",
        headers=_auth_header(register_payload["access_token"]),
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "owner@example.com"

    refresh_response = await async_client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    refreshed_payload = refresh_response.json()
    assert refreshed_payload["user"]["email"] == "owner@example.com"
    assert refreshed_payload["access_token"] != register_payload["access_token"]

    logout_response = await async_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204
    assert "refresh_token=" in logout_response.headers.get("set-cookie", "").lower()

    refresh_after_logout = await async_client.post("/api/v1/auth/refresh")
    assert refresh_after_logout.status_code == 401


@pytest.mark.integration
@pytest.mark.api
async def test_user_locale_can_be_updated_and_is_returned_by_me_and_refresh(async_client):
    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "locale-owner@example.com",
            "password": "StrongPass123",
            "locale": "ru",
        },
    )

    assert register_response.status_code == 201
    register_payload = register_response.json()
    access_token = register_payload["access_token"]

    update_response = await async_client.patch(
        "/api/v1/auth/me/locale",
        headers=_auth_header(access_token),
        json={"locale": "kz"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["locale"] == "kz"

    me_response = await async_client.get(
        "/api/v1/auth/me",
        headers=_auth_header(access_token),
    )
    assert me_response.status_code == 200
    assert me_response.json()["locale"] == "kz"

    refresh_response = await async_client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    refreshed_payload = refresh_response.json()
    assert refreshed_payload["user"]["locale"] == "kz"


@pytest.mark.integration
@pytest.mark.api
async def test_register_duplicate_and_invalid_login(async_client):
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPass123",
        "locale": "ru",
    }

    first_response = await async_client.post("/api/v1/auth/register", json=payload)
    assert first_response.status_code == 201

    duplicate_response = await async_client.post("/api/v1/auth/register", json=payload)
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == "A user with this email already exists"

    invalid_login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": payload["email"],
            "password": "WrongPass123",
        },
    )
    assert invalid_login_response.status_code == 401
    assert invalid_login_response.json()["detail"] == "Invalid email or password"

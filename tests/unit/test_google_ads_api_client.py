from __future__ import annotations

import httpx
import pytest
import respx

from core.infrastructure.google_ads_api import GoogleAdsAPIClient


@pytest.mark.unit
@pytest.mark.service
async def test_google_ads_client_walks_accessible_customers_and_hierarchy():
    client = GoogleAdsAPIClient(
        developer_token="dev-token",
        api_version="v22",
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost/google/callback",
    )

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://googleads.googleapis.com/v22/customers:listAccessibleCustomers").respond(
            200,
            json={
                "resourceNames": [
                    "customers/1234567890",
                    "customers/9988776655",
                    "customers/5566778899",
                ]
            },
        )
        mock.post("https://googleads.googleapis.com/v22/customers/1234567890/googleAds:search").respond(
            200,
            json={
                "results": [
                    {
                        "customerClient": {
                            "clientCustomer": "customers/1234567890",
                            "id": "1234567890",
                            "descriptiveName": "Direct standalone",
                            "currencyCode": "USD",
                            "timeZone": "Europe/Paris",
                            "manager": False,
                            "level": "0",
                        }
                    }
                ]
            },
        )
        mock.post("https://googleads.googleapis.com/v22/customers/9988776655/googleAds:search").respond(
            200,
            json={
                "results": [
                    {
                        "customerClient": {
                            "clientCustomer": "customers/9988776655",
                            "id": "9988776655",
                            "descriptiveName": "Primary MCC",
                            "currencyCode": "USD",
                            "timeZone": "Europe/Paris",
                            "manager": True,
                            "level": "0",
                        }
                    },
                    {
                        "customerClient": {
                            "clientCustomer": "customers/5566778899",
                            "id": "5566778899",
                            "descriptiveName": "Nested MCC",
                            "currencyCode": "USD",
                            "timeZone": "Europe/Paris",
                            "manager": True,
                            "level": "1",
                        }
                    },
                    {
                        "customerClient": {
                            "clientCustomer": "customers/4433221100",
                            "id": "4433221100",
                            "descriptiveName": "Managed client",
                            "currencyCode": "KZT",
                            "timeZone": "Asia/Almaty",
                            "manager": False,
                            "level": "1",
                        }
                    },
                ]
            },
        )
        mock.post("https://googleads.googleapis.com/v22/customers/5566778899/googleAds:search").respond(
            200,
            json={
                "results": [
                    {
                        "customerClient": {
                            "clientCustomer": "customers/5566778899",
                            "id": "5566778899",
                            "descriptiveName": "Nested MCC",
                            "currencyCode": "USD",
                            "timeZone": "Europe/Paris",
                            "manager": True,
                            "level": "0",
                        }
                    },
                    {
                        "customerClient": {
                            "clientCustomer": "customers/8899001122",
                            "id": "8899001122",
                            "descriptiveName": "Grandchild client",
                            "currencyCode": "EUR",
                            "timeZone": "Europe/Berlin",
                            "manager": False,
                            "level": "1",
                        }
                    },
                ]
            },
        )

        customers = await client.list_customer_accounts(access_token="access-token")

    await client.aclose()

    by_id = {customer["external_customer_id"]: customer for customer in customers}
    assert set(by_id) == {"1234567890", "9988776655", "5566778899", "4433221100", "8899001122"}
    assert by_id["5566778899"]["is_directly_accessible"] is True
    assert by_id["5566778899"]["login_customer_id"] is None
    assert by_id["4433221100"]["login_customer_id"] == "9988776655"
    assert by_id["8899001122"]["login_customer_id"] == "5566778899"
    assert by_id["8899001122"]["hierarchy_level"] == 1


@pytest.mark.unit
@pytest.mark.service
async def test_google_ads_client_falls_back_to_customer_id_when_name_missing():
    client = GoogleAdsAPIClient(
        developer_token="dev-token",
        api_version="v22",
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost/google/callback",
    )

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://googleads.googleapis.com/v22/customers:listAccessibleCustomers").respond(
            200,
            json={"resourceNames": ["customers/1234567890"]},
        )
        mock.post("https://googleads.googleapis.com/v22/customers/1234567890/googleAds:search").respond(
            200,
            json={
                "results": [
                    {
                        "customerClient": {
                            "clientCustomer": "customers/1234567890",
                            "id": "1234567890",
                            "descriptiveName": None,
                            "currencyCode": "USD",
                            "timeZone": "Europe/Paris",
                            "manager": False,
                            "level": "0",
                        }
                    }
                ]
            },
        )

        customers = await client.list_customer_accounts(access_token="access-token")

    await client.aclose()

    assert customers[0]["descriptive_name"] == "1234567890"

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from api_v1.media import views as media_views


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        ("https://scontent.xx.fbcdn.net/v/t1.jpg", True),
        ("https://cdninstagram.com/p/abc.jpg", True),
        ("https://www.instagram.com/p/abc.jpg", True),
        ("https://evil.com/?q=fbcdn.net", False),
        ("https://fbcdn.net.evil.com/x.jpg", False),
        ("https://notfacebook.com/x.jpg", False),
        ("http://127.0.0.1/x.jpg", False),
        ("file:///etc/passwd", False),
        ("https://user:pass@fbcdn.net/x.jpg", False),
    ],
)
def test_is_allowed_preview_url(url: str, allowed: bool):
    assert media_views._is_allowed_preview_url(url) is allowed


@pytest.mark.unit
@pytest.mark.api
async def test_proxy_creative_preview_returns_image(monkeypatch):
    response = httpx.Response(
        200,
        content=b"\xff\xd8\xff",
        headers={"content-type": "image/jpeg"},
        request=httpx.Request("GET", "https://scontent.xx.fbcdn.net/v/t1.jpg"),
    )
    monkeypatch.setattr(media_views, "_fetch_allowed_image", AsyncMock(return_value=response))

    result = await media_views.proxy_creative_preview(
        url="https://scontent.xx.fbcdn.net/v/t1.jpg",
        _user=SimpleNamespace(id="user-1"),
    )

    assert result.status_code == 200
    assert result.media_type == "image/jpeg"
    assert result.body == b"\xff\xd8\xff"


@pytest.mark.unit
@pytest.mark.api
async def test_proxy_creative_preview_rejects_disallowed_host():
    with pytest.raises(HTTPException) as exc_info:
        await media_views.proxy_creative_preview(
            url="https://evil.example/steal.jpg",
            _user=SimpleNamespace(id="user-1"),
        )
    assert exc_info.value.status_code == 400


@pytest.mark.unit
@pytest.mark.api
async def test_fetch_allowed_image_rejects_redirect_to_disallowed_host(monkeypatch):
    redirect = httpx.Response(
        302,
        headers={"location": "https://evil.example/payload"},
        request=httpx.Request("GET", "https://scontent.xx.fbcdn.net/v/t1.jpg"),
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None):
            assert "fbcdn.net" in url
            return redirect

    monkeypatch.setattr(media_views.httpx, "AsyncClient", FakeClient)

    with pytest.raises(HTTPException) as exc_info:
        await media_views._fetch_allowed_image("https://scontent.xx.fbcdn.net/v/t1.jpg")
    assert exc_info.value.status_code == 400


@pytest.mark.unit
@pytest.mark.api
async def test_fetch_allowed_image_follows_allowed_redirect(monkeypatch):
    first = httpx.Response(
        302,
        headers={"location": "https://scontent.cdninstagram.com/v/t2.jpg"},
        request=httpx.Request("GET", "https://scontent.xx.fbcdn.net/v/t1.jpg"),
    )
    second = httpx.Response(
        200,
        content=b"img",
        headers={"content-type": "image/jpeg"},
        request=httpx.Request("GET", "https://scontent.cdninstagram.com/v/t2.jpg"),
    )
    calls: list[str] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None):
            calls.append(url)
            if len(calls) == 1:
                return first
            return second

    monkeypatch.setattr(media_views.httpx, "AsyncClient", FakeClient)

    result = await media_views._fetch_allowed_image("https://scontent.xx.fbcdn.net/v/t1.jpg")
    assert result.content == b"img"
    assert calls == [
        "https://scontent.xx.fbcdn.net/v/t1.jpg",
        "https://scontent.cdninstagram.com/v/t2.jpg",
    ]


@pytest.mark.unit
@pytest.mark.service
def test_format_audience_reach_bounds():
    from core.services.meta_report_service import _format_audience_reach_bounds

    assert _format_audience_reach_bounds(1_000_000, 2_000_000) == "1 000 000 – 2 000 000"
    assert _format_audience_reach_bounds(500, 500) == "500"
    assert _format_audience_reach_bounds(-1, 100) is None
    assert _format_audience_reach_bounds(0, 0) is None
    assert _format_audience_reach_bounds("x", 10) is None


@pytest.mark.unit
@pytest.mark.service
def test_localize_targeting_label_maps_common_interests():
    from core.services.meta_report_service import _extract_named_values, _localize_targeting_label

    assert _localize_targeting_label("small business") == "Малый бизнес"
    assert _localize_targeting_label("Small And Medium Enterprises") == "Малый и средний бизнес"
    assert _localize_targeting_label("Entrepreneurship") == "Предпринимательство"
    assert _extract_named_values(
        [
            {"name": "small business"},
            {"name": "small and medium enterprises"},
            {"name": "entrepreneurship"},
        ]
    ) == ["Малый бизнес", "Малый и средний бизнес", "Предпринимательство"]

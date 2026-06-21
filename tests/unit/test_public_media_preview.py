from __future__ import annotations

import pytest

from core.infrastructure import public_media_preview
from core.infrastructure.public_media_preview import PublicCreativePreviewClient


@pytest.mark.unit
@pytest.mark.service
async def test_public_creative_preview_client_extracts_og_image_and_caches(monkeypatch):
    client = PublicCreativePreviewClient()
    calls: list[str] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return (
                "<html><head>"
                '<meta property="og:image" content="https://cdninstagram.test/image.jpg?foo=1&amp;bar=2">'
                "</head></html>"
            ).encode()

    def fake_urlopen(request, timeout=10):
        calls.append(request.full_url)
        return FakeResponse()

    monkeypatch.setattr(public_media_preview, "urlopen", fake_urlopen)

    first = await client.resolve_instagram_permalink_preview(permalink_url="https://www.instagram.com/p/demo/")
    second = await client.resolve_instagram_permalink_preview(permalink_url="https://www.instagram.com/p/demo/")

    assert first == "https://cdninstagram.test/image.jpg?foo=1&bar=2"
    assert second == first
    assert calls == ["https://www.instagram.com/p/demo/"]
    await client.aclose()

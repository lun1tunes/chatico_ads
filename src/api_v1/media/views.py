from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from core.dependencies import get_current_user

router = APIRouter()

_ALLOWED_EXACT_HOSTS = frozenset(
    {
        "fbcdn.net",
        "facebook.com",
        "fbsbx.com",
        "cdninstagram.com",
        "instagram.com",
        "fbcdn.com",
    }
)
_ALLOWED_HOST_SUFFIXES = (
    ".fbcdn.net",
    ".facebook.com",
    ".fbsbx.com",
    ".cdninstagram.com",
    ".instagram.com",
    ".fbcdn.com",
)
_MAX_REDIRECTS = 5
_MAX_BYTES = 8 * 1024 * 1024


def _is_allowed_preview_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.lower().rstrip(".")
    if normalized in _ALLOWED_EXACT_HOSTS:
        return True
    return any(normalized.endswith(suffix) for suffix in _ALLOWED_HOST_SUFFIXES)


def _is_allowed_preview_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return False
    return _is_allowed_preview_host(parsed.hostname)


async def _fetch_allowed_image(url: str) -> httpx.Response:
    current = url
    headers = {
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (compatible; ChaticoAds/1.0)",
    }
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            if not _is_allowed_preview_url(current):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported media host",
                )
            response = await client.get(current, headers=headers)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Upstream media redirect missing location",
                    )
                current = urljoin(str(response.url), location)
                continue
            return response

    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Too many media redirects")


@router.get("/preview")
async def proxy_creative_preview(
    url: str = Query(..., min_length=8, max_length=2048),
    _user=Depends(get_current_user),
):
    """Fetch Meta/Instagram CDN media server-side so browser hotlink blocks do not break thumbs."""
    if not _is_allowed_preview_url(url):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported media host")

    try:
        response = await _fetch_allowed_image(url)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch media") from exc

    if response.status_code >= 400 or not response.content:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Upstream media unavailable")

    if len(response.content) > _MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Upstream media too large")

    content_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Upstream response is not an image")

    return Response(
        content=response.content,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )

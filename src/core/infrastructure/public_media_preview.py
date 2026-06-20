from __future__ import annotations

import asyncio
from html import unescape
import re
from urllib.request import Request, urlopen


class PublicCreativePreviewClient:
    _OG_IMAGE_RE = re.compile(r'<meta\s+property="og:image"\s+content="([^"]+)"', re.IGNORECASE)

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}
        self._user_agent = "Mozilla/5.0"

    def _fetch_html(self, permalink_url: str) -> str:
        request = Request(permalink_url, headers={"User-Agent": self._user_agent})
        with urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8", errors="ignore")

    async def resolve_instagram_permalink_preview(self, *, permalink_url: str) -> str | None:
        cached = self._cache.get(permalink_url)
        if permalink_url in self._cache:
            return cached

        try:
            html = await asyncio.to_thread(self._fetch_html, permalink_url)
            match = self._OG_IMAGE_RE.search(html)
            preview_url = unescape(match.group(1)) if match else None
            self._cache[permalink_url] = preview_url
            return preview_url
        except Exception:  # noqa: BLE001
            self._cache[permalink_url] = None
            return None

    async def aclose(self) -> None:
        return None

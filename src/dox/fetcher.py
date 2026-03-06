"""Fetch documentation pages over HTTP."""

from __future__ import annotations

import httpx

from dox import cache

USER_AGENT = "dox-cli/0.1 (documentation reader)"
TIMEOUT = 30


def fetch(url: str, use_cache: bool = True) -> str:
    """Fetch a URL and return raw HTML. Uses cache by default."""
    if use_cache:
        cached = cache.get(url)
        if cached is not None:
            return cached

    with httpx.Client(
        follow_redirects=True,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()

    html = resp.text
    if use_cache:
        cache.put(url, html)
    return html

"""Crawl documentation sites by following links within the same scope."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urldefrag, urlparse

from dox import converter, fetcher


def _normalize(url: str) -> str:
    """Strip fragment for dedup. Preserve trailing slash for correct relative link resolution."""
    return urldefrag(url).url


def _is_in_scope(url: str, base_domain: str, base_path: str | None) -> bool:
    """Check if a URL is within the crawl scope."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.netloc != base_domain:
        return False
    if base_path and not parsed.path.startswith(base_path):
        return False
    # Skip non-doc resources
    path = parsed.path.lower()
    if any(path.endswith(ext) for ext in (".pdf", ".zip", ".tar", ".gz", ".png", ".jpg", ".svg", ".css", ".js")):
        return False
    return True


def _discover_links(html: str, page_url: str, base_domain: str, base_path: str | None) -> list[str]:
    """Extract in-scope links from a page."""
    links = converter.extract_links(html, page_url)
    results = []
    for link in links:
        href = _normalize(link["href"])
        if _is_in_scope(href, base_domain, base_path):
            results.append(href)
    return results


def _fetch_page(url: str, use_cache: bool) -> dict | None:
    """Fetch and convert a single page. Returns None on failure."""
    try:
        html = fetcher.fetch(url, use_cache=use_cache)
    except Exception:
        return None
    title = converter.extract_title(html)
    content = converter.html_to_markdown(html, url)
    return {"url": url, "title": title, "content": content, "html": html}


def crawl(
    start_url: str,
    *,
    depth: int = 1,
    limit: int = 50,
    use_cache: bool = True,
    same_path: bool = True,
    concurrency: int = 4,
    on_page: callable | None = None,
) -> list[dict]:
    """Crawl a documentation site starting from start_url.

    Args:
        start_url: The page to start crawling from.
        depth: How many levels of links to follow (0 = just the start page).
        limit: Maximum total pages to fetch.
        use_cache: Whether to use the page cache.
        same_path: If True, only follow links under the same URL path prefix.
        concurrency: Number of parallel fetches.
        on_page: Optional callback called with (url, index, total_queued) for progress.

    Returns:
        List of dicts with url, title, content (markdown) for each page.
    """
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc
    if same_path:
        # Use the parent directory of the start URL as the scope.
        # /en/stable/quickstart/ -> /en/stable/
        # /en/stable/quickstart  -> /en/stable/
        path = parsed_start.path.rstrip("/")
        base_path = path.rsplit("/", 1)[0] + "/" if "/" in path else "/"
    else:
        base_path = None

    visited: set[str] = set()
    results: list[dict] = []

    # BFS by depth level
    current_level = [_normalize(start_url)]

    for current_depth in range(depth + 1):
        if not current_level or len(results) >= limit:
            break

        # Dedup against already visited
        to_fetch = [url for url in current_level if url not in visited]
        to_fetch = to_fetch[: limit - len(results)]

        if not to_fetch:
            break

        next_level_urls: set[str] = set()

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            future_to_url = {
                pool.submit(_fetch_page, url, use_cache): url for url in to_fetch
            }
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                visited.add(url)
                page = future.result()
                if page is None:
                    continue

                result = {"url": page["url"], "title": page["title"], "content": page["content"]}
                results.append(result)

                if on_page:
                    on_page(url, len(results), len(to_fetch))

                if len(results) >= limit:
                    break

                # Discover links for next depth level
                if current_depth < depth:
                    for link_url in _discover_links(page["html"], url, base_domain, base_path):
                        if link_url not in visited:
                            next_level_urls.add(link_url)

        current_level = list(next_level_urls)

    return results

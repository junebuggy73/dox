"""Convert HTML documentation pages to clean markdown."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify


# Elements that are almost never useful doc content
STRIP_TAGS = [
    "nav",
    "header",
    "footer",
    "aside",
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "form",
]

STRIP_CLASSES = [
    "sidebar",
    "navigation",
    "nav-",
    "menu",
    "breadcrumb",
    "footer",
    "header",
    "cookie",
    "banner",
    "ad-",
    "announcement",
    "toc-",  # table of contents sidebars (not inline)
]

# Content-bearing selectors, tried in priority order
CONTENT_SELECTORS = [
    "article",
    "main",
    "[role='main']",
    ".markdown-body",
    ".doc-content",
    ".documentation",
    ".content",
    ".post-content",
    "#content",
    "#main-content",
    ".rst-content",  # Sphinx/ReadTheDocs
    ".section",  # Sphinx
]


def _find_content(soup: BeautifulSoup) -> Tag | BeautifulSoup:
    """Find the main content element, falling back to body or full soup."""
    for selector in CONTENT_SELECTORS:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 100:
            return el
    body = soup.find("body")
    return body if body else soup


def _strip_noise(soup: BeautifulSoup) -> None:
    """Remove non-content elements in place."""
    for tag_name in STRIP_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()
    for el in soup.find_all(True):
        if not hasattr(el, "attrs") or el.attrs is None:
            continue
        classes = " ".join(el.get("class", []))
        el_id = el.get("id", "")
        combined = f"{classes} {el_id}".lower()
        if any(pat in combined for pat in STRIP_CLASSES):
            el.decompose()


def _resolve_links(soup: BeautifulSoup, base_url: str) -> None:
    """Make relative links absolute."""
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith(("http://", "https://", "#", "mailto:")):
            a["href"] = urljoin(base_url, href)


def _clean_markdown(md: str) -> str:
    """Post-process markdown to remove excessive whitespace."""
    # Collapse 3+ newlines to 2
    md = re.sub(r"\n{3,}", "\n\n", md)
    # Remove trailing whitespace per line
    md = "\n".join(line.rstrip() for line in md.splitlines())
    return md.strip() + "\n"


def html_to_markdown(html: str, url: str = "") -> str:
    """Convert HTML to clean documentation markdown."""
    soup = BeautifulSoup(html, "html.parser")
    _strip_noise(soup)
    if url:
        _resolve_links(soup, url)
    content = _find_content(soup)
    md = markdownify(str(content), heading_style="ATX", strip=["img"])
    return _clean_markdown(md)


def extract_title(html: str) -> str:
    """Extract the page title."""
    soup = BeautifulSoup(html, "html.parser")
    # Try h1 first, then <title>
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    title = soup.find("title")
    if title:
        return title.get_text(strip=True)
    return ""


def extract_toc(html: str, url: str = "") -> list[dict]:
    """Extract table of contents from headings."""
    soup = BeautifulSoup(html, "html.parser")
    _strip_noise(soup)
    content = _find_content(soup)
    headings = []
    for h in content.find_all(re.compile(r"^h[1-6]$")):
        level = int(h.name[1])
        text = h.get_text(strip=True)
        anchor = h.get("id", "")
        if not anchor:
            a = h.find("a", id=True)
            if a:
                anchor = a["id"]
            else:
                a = h.find("a", href=True)
                if a and a["href"].startswith("#"):
                    anchor = a["href"][1:]
        link = ""
        if anchor and url:
            link = f"{url}#{anchor}"
        headings.append({"level": level, "text": text, "anchor": anchor, "link": link})
    return headings


def extract_links(html: str, url: str = "") -> list[dict]:
    """Extract all links from the page content."""
    soup = BeautifulSoup(html, "html.parser")
    _strip_noise(soup)
    content = _find_content(soup)
    if url:
        _resolve_links(content if isinstance(content, BeautifulSoup) else soup, url)
    links = []
    seen = set()
    for a in content.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href in seen or not text or href.startswith(("#", "javascript:")):
            continue
        seen.add(href)
        links.append({"text": text, "href": href})
    return links


def extract_section(html: str, heading_pattern: str, url: str = "") -> str | None:
    """Extract content under a specific heading (matched by substring, case-insensitive)."""
    soup = BeautifulSoup(html, "html.parser")
    _strip_noise(soup)
    content = _find_content(soup)

    pattern = heading_pattern.lower()
    for h in content.find_all(re.compile(r"^h[1-6]$")):
        if pattern in h.get_text(strip=True).lower():
            level = int(h.name[1])
            parts = [str(h)]
            for sibling in h.find_next_siblings():
                if sibling.name and re.match(r"^h[1-6]$", sibling.name):
                    sib_level = int(sibling.name[1])
                    if sib_level <= level:
                        break
                parts.append(str(sibling))
            section_html = "\n".join(parts)
            md = markdownify(section_html, heading_style="ATX", strip=["img"])
            return _clean_markdown(md)
    return None

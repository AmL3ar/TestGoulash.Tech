from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup


BLOCKED_HOSTS = {
    "duckduckgo.com",
    "bing.com",
    "yandex.ru",
    "google.com",
    "google.ru",
    "youtube.com",
    "vk.com",
    "instagram.com",
    "facebook.com",
    "wikipedia.org",
    "2gis.ru",
    "avito.ru",
    "ozon.ru",
    "wildberries.ru",
}


def _clean_result_url(value: str) -> str | None:
    if value.startswith("//"):
        value = "https:" + value

    parsed = urlparse(value)

    if "duckduckgo.com" in parsed.netloc and parsed.query:
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        if target:
            value = unquote(target)
            parsed = urlparse(value)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    host = parsed.netloc.lower().removeprefix("www.")
    if any(
        host == blocked or host.endswith("." + blocked)
        for blocked in BLOCKED_HOSTS
    ):
        return None

    return value


def _parse_duckduckgo(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        link.get("href", "")
        for link in soup.select("a.result__a")
        if link.get("href")
    ]


def _parse_bing(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        link.get("href", "")
        for link in soup.select("li.b_algo h2 a")
        if link.get("href")
    ]


async def discover_supplier_urls(
    category: str,
    geography: str | None,
    limit: int = 5,
) -> list[str]:
    query = f"{category} поставщик оптом {geography or ''} официальный сайт".strip()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        )
    }
    providers = (
        (
            f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
            _parse_duckduckgo,
        ),
        (
            f"https://www.bing.com/search?q={quote_plus(query)}&count=10",
            _parse_bing,
        ),
    )

    errors: list[str] = []
    found: list[str] = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=8.0),
        follow_redirects=True,
        headers=headers,
    ) as client:
        for url, parser in providers:
            try:
                response = await client.get(url)
                response.raise_for_status()
            except Exception as exc:
                errors.append(f"{urlparse(url).netloc}: {type(exc).__name__}: {exc!r}")
                continue

            for raw_url in parser(response.text):
                cleaned = _clean_result_url(raw_url)
                if cleaned and cleaned not in found:
                    found.append(cleaned)
                if len(found) >= limit:
                    return found

    if found:
        return found

    if errors:
        raise RuntimeError("; ".join(errors))

    return []

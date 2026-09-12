from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup


BLOCKED_HOSTS = {
    "duckduckgo.com",
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


async def discover_supplier_urls(
    category: str,
    geography: str | None,
    limit: int = 5,
) -> list[str]:
    query = f"{category} поставщик оптом {geography or ''} официальный сайт"
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(
        timeout=12,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    found: list[str] = []

    for link in soup.select("a.result__a"):
        cleaned = _clean_result_url(link.get("href", ""))
        if cleaned and cleaned not in found:
            found.append(cleaned)
        if len(found) >= limit:
            break

    return found

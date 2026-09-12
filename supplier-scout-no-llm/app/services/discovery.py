from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from xml.etree import ElementTree

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


def _parse_bing_rss(xml: str) -> list[str]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []

    links: list[str] = []
    for item in root.findall(".//item"):
        link = item.findtext("link")
        if link:
            links.append(link.strip())
    return links


def _parse_bing(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        link.get("href", "")
        for link in soup.select("li.b_algo h2 a")
        if link.get("href")
    ]


def _parse_duckduckgo(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        link.get("href", "")
        for link in soup.select("a.result__a")
        if link.get("href")
    ]


async def discover_supplier_urls(
    category: str,
    geography: str | None,
    limit: int = 5,
) -> list[str]:
    query = f"{category} поставщик оптом {geography or ''} официальный сайт".strip()
    encoded = quote_plus(query)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.7",
    }
    providers = (
        (
            f"https://www.bing.com/search?q={encoded}&format=rss&setlang=ru",
            _parse_bing_rss,
        ),
        (
            f"https://www.bing.com/search?q={encoded}&count=10&setlang=ru",
            _parse_bing,
        ),
        (
            f"https://html.duckduckgo.com/html/?q={encoded}",
            _parse_duckduckgo,
        ),
    )

    errors: list[str] = []
    found: list[str] = []
    providers_reached = 0

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(18.0, connect=6.0),
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

            providers_reached += 1
            for raw_url in parser(response.text):
                cleaned = _clean_result_url(raw_url)
                if cleaned and cleaned not in found:
                    found.append(cleaned)
                if len(found) >= limit:
                    return found

    if found or providers_reached:
        return found

    if errors:
        raise RuntimeError("; ".join(errors))

    return []

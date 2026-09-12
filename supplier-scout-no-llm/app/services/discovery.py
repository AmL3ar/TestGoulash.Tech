import re
from dataclasses import dataclass
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from ..config import settings


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
    "market.yandex.ru",
}

BUSINESS_MARKERS = (
    "поставщик",
    "поставки",
    "опт",
    "оптов",
    "производитель",
    "дистрибьютор",
    "дистрибуц",
    "horeca",
    "хорека",
    "склад",
    "прайс",
    "каталог",
    "купить",
    "продажа",
)

NEGATIVE_MARKERS = (
    "рецепт",
    "как приготовить",
    "калорийность",
    "википедия",
    "отзывы",
    "вакансия",
    "работа",
    "реферат",
    "школ",
    "форум",
)


@dataclass(slots=True)
class SearchHit:
    url: str
    title: str = ""
    snippet: str = ""


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
    if any(host == blocked or host.endswith("." + blocked) for blocked in BLOCKED_HOSTS):
        return None

    return value


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("ё", "е")).strip()


def _tokens(value: str | None) -> list[str]:
    if not value:
        return []
    return [
        token
        for token in re.findall(r"[a-zа-я0-9]+", _normalize(value))
        if len(token) >= 3
    ]


def _category_roots(category: str) -> list[str]:
    roots: list[str] = []
    for token in _tokens(category):
        root = token[: max(4, min(len(token), 7))]
        if root not in roots:
            roots.append(root)
    return roots


def _hit_relevance(hit: SearchHit, category: str, geography: str | None) -> int:
    text = _normalize(f"{hit.title} {hit.snippet} {hit.url}")
    category_roots = _category_roots(category)
    geography_tokens = _tokens(geography)

    if any(marker in text for marker in NEGATIVE_MARKERS):
        return -1

    category_matches = sum(root in text for root in category_roots)
    if category_roots and category_matches == 0:
        return -1

    score = category_matches * 7
    score += sum(token in text for token in geography_tokens) * 3
    score += min(sum(marker in text for marker in BUSINESS_MARKERS), 4) * 3

    host = urlparse(hit.url).netloc.lower()
    if host.endswith(".ru") or host.endswith(".рф"):
        score += 2

    return score


def _parse_serper(payload: dict) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for item in payload.get("organic", []):
        link = str(item.get("link") or "").strip()
        if not link:
            continue
        hits.append(
            SearchHit(
                url=link,
                title=str(item.get("title") or "").strip(),
                snippet=str(item.get("snippet") or "").strip(),
            )
        )
    return hits


def _parse_bing_rss(xml: str) -> list[SearchHit]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []

    hits: list[SearchHit] = []
    for item in root.findall(".//item"):
        link = (item.findtext("link") or "").strip()
        if not link:
            continue
        hits.append(
            SearchHit(
                url=link,
                title=(item.findtext("title") or "").strip(),
                snippet=(item.findtext("description") or "").strip(),
            )
        )
    return hits


def _parse_bing(html: str) -> list[SearchHit]:
    soup = BeautifulSoup(html, "html.parser")
    hits: list[SearchHit] = []
    for item in soup.select("li.b_algo"):
        link = item.select_one("h2 a")
        if not link or not link.get("href"):
            continue
        snippet = item.select_one(".b_caption p")
        hits.append(
            SearchHit(
                url=link.get("href", ""),
                title=link.get_text(" ", strip=True),
                snippet=snippet.get_text(" ", strip=True) if snippet else "",
            )
        )
    return hits


def _parse_duckduckgo(html: str) -> list[SearchHit]:
    soup = BeautifulSoup(html, "html.parser")
    hits: list[SearchHit] = []
    for result in soup.select(".result"):
        link = result.select_one("a.result__a")
        if not link or not link.get("href"):
            continue
        snippet = result.select_one(".result__snippet")
        hits.append(
            SearchHit(
                url=link.get("href", ""),
                title=link.get_text(" ", strip=True),
                snippet=snippet.get_text(" ", strip=True) if snippet else "",
            )
        )
    return hits


def _rank_hits(
    hits: list[SearchHit],
    category: str,
    geography: str | None,
    limit: int,
) -> list[str]:
    found: list[tuple[int, str]] = []
    seen: set[str] = set()

    for hit in hits:
        cleaned = _clean_result_url(hit.url)
        if not cleaned or cleaned in seen:
            continue
        normalized_hit = SearchHit(cleaned, hit.title, hit.snippet)
        score = _hit_relevance(normalized_hit, category, geography)
        if score < 7:
            continue
        seen.add(cleaned)
        found.append((score, cleaned))

    found.sort(key=lambda item: item[0], reverse=True)
    return [url for _, url in found[:limit]]


async def _serper_search(
    client: httpx.AsyncClient,
    category: str,
    geography: str | None,
    limit: int,
) -> list[str]:
    if not settings.serper_api_key:
        return []

    geo = geography or "Россия"
    queries = [
        f'"{category}" поставщик оптом "{geo}"',
        f'"{category}" дистрибьютор HoReCa "{geo}"',
    ]
    hits: list[SearchHit] = []

    for query in queries:
        response = await client.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": settings.serper_api_key,
                "Content-Type": "application/json",
            },
            json={
                "q": query,
                "gl": "ru",
                "hl": "ru",
                "num": 10,
            },
        )
        response.raise_for_status()
        hits.extend(_parse_serper(response.json()))

        ranked = _rank_hits(hits, category, geography, limit)
        if len(ranked) >= limit:
            return ranked

    return _rank_hits(hits, category, geography, limit)


async def _public_search(
    client: httpx.AsyncClient,
    category: str,
    geography: str | None,
    limit: int,
) -> list[str]:
    query = f'"{category}" поставщик оптом {geography or ""} купить'.strip()
    encoded = quote_plus(query)
    providers = (
        (
            f"https://www.bing.com/search?q={encoded}&format=rss&setlang=ru",
            _parse_bing_rss,
        ),
        (
            f"https://www.bing.com/search?q={encoded}&count=20&setlang=ru",
            _parse_bing,
        ),
        (
            f"https://html.duckduckgo.com/html/?q={encoded}",
            _parse_duckduckgo,
        ),
    )

    errors: list[str] = []
    providers_reached = 0

    for url, parser in providers:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except Exception as exc:
            errors.append(f"{urlparse(url).netloc}: {type(exc).__name__}: {exc!r}")
            continue

        providers_reached += 1
        ranked = _rank_hits(parser(response.text), category, geography, limit)
        if ranked:
            return ranked

    if providers_reached:
        return []

    if errors:
        raise RuntimeError("; ".join(errors))

    return []


async def discover_supplier_urls(
    category: str,
    geography: str | None,
    limit: int = 5,
) -> list[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.6",
        "Accept": "text/html,application/xhtml+xml,application/json,application/xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(18.0, connect=6.0),
        follow_redirects=True,
        headers=headers,
    ) as client:
        if settings.serper_api_key:
            try:
                results = await _serper_search(client, category, geography, limit)
                if results:
                    return results
            except Exception:
                pass

        return await _public_search(client, category, geography, limit)

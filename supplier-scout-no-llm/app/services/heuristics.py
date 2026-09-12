import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .types import ExtractedSupplier


PHONE_RE = re.compile(
    r"(?:\+7|8)[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}"
)
EMAIL_RE = re.compile(r"[\w.+'-]+@[\w.-]+\.[A-Za-zА-Яа-я]{2,}")
BUSINESS_MARKERS = (
    "поставщик",
    "поставки",
    "опт",
    "оптов",
    "производитель",
    "дистрибьютор",
    "horeca",
    "хорека",
    "каталог",
    "прайс",
    "купить",
    "продажа",
)


async def fetch_page(url: str) -> tuple[str, str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.6",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=6.0),
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    if content_type and "html" not in content_type and "text" not in content_type:
        raise ValueError("источник не является HTML-страницей")

    soup = BeautifulSoup(response.text, "html.parser")
    title = ""

    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    h1 = soup.find("h1")
    if h1 and h1.get_text(" ", strip=True):
        title = h1.get_text(" ", strip=True)

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    return title, " ".join(soup.stripped_strings)[:30000]


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
    return [
        token[: max(4, min(len(token), 7))]
        for token in _tokens(category)
    ]


def is_relevant_page(text: str, category: str, geography: str | None) -> bool:
    normalized = _normalize(text)
    roots = _category_roots(category)
    if roots and not any(root in normalized for root in roots):
        return False

    business_score = sum(marker in normalized for marker in BUSINESS_MARKERS)
    geography_score = sum(token in normalized for token in _tokens(geography))
    return business_score > 0 or geography_score > 0


def _sentence(text: str, words: tuple[str, ...]) -> str | None:
    chunks = re.split(r"(?<=[.!?])\s+|\s*[|•]\s*", text)

    for chunk in chunks:
        low = chunk.lower()
        if any(word in low for word in words):
            value = " ".join(chunk.split())
            if 15 <= len(value) <= 280:
                return value

    return None


def _name(title: str, url: str) -> str:
    if title:
        for separator in (" | ", " — ", " - ", " :: "):
            if separator in title:
                title = title.split(separator)[0]
                break
        return title[:180]

    host = urlparse(url).netloc.removeprefix("www.")
    return host[:180]


async def extract_with_rules(
    url: str,
    category_hint: str,
    geography_hint: str | None,
) -> ExtractedSupplier:
    title, text = await fetch_page(url)
    if not is_relevant_page(f"{title} {text}", category_hint, geography_hint):
        raise ValueError("страница не прошла проверку релевантности")

    phone = PHONE_RE.search(text)
    email = EMAIL_RE.search(text)
    contacts = [
        value
        for value in (
            phone.group(0) if phone else None,
            email.group(0) if email else None,
        )
        if value
    ]
    geography = geography_hint or "регион не указан"
    parsed_url = urlparse(url)

    return ExtractedSupplier(
        name=_name(title, url),
        category=category_hint,
        city=(
            geography
            if "область" not in geography.lower() and "край" not in geography.lower()
            else "не указан"
        ),
        region=geography,
        website=f"{parsed_url.scheme}://{parsed_url.netloc}/",
        contact=" · ".join(contacts) or None,
        min_order=_sentence(
            text,
            (
                "минимальный заказ",
                "минимальная сумма",
                "минимальная партия",
                "минимальный объем",
            ),
        ),
        price_hint=_sentence(text, ("цена", "цены", "прайс", "руб", "₽")),
        certificates=_sentence(
            text,
            ("сертифик", "декларац", "ветеринар", "меркур"),
        ),
        delivery=_sentence(
            text,
            ("достав", "самовывоз", "транспортной компанией"),
        ),
        source_url=url,
    )

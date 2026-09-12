import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .types import ExtractedSupplier


PHONE_RE = re.compile(
    r"(?:\+7|8)[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}"
)
EMAIL_RE = re.compile(r"[\w.+'-]+@[\w.-]+\.[A-Za-zА-Яа-я]{2,}")


async def fetch_page(url: str) -> tuple[str, str]:
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(
        timeout=12,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

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
                "минимальный объём",
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

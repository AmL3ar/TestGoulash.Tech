import json

import httpx
from bs4 import BeautifulSoup

from ..config import settings
from .types import ExtractedSupplier


async def fetch_readable_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(
        timeout=12,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    return " ".join(soup.stripped_strings)[:24000]


async def extract_with_llm(
    url: str,
    category_hint: str,
    geography_hint: str | None,
) -> ExtractedSupplier:
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY не настроен")

    text = await fetch_readable_text(url)
    schema = {
        "name": "supplier_card",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "name",
                "category",
                "city",
                "region",
                "website",
                "contact",
                "min_order",
                "price_hint",
                "certificates",
                "delivery",
            ],
            "properties": {
                "name": {"type": "string"},
                "category": {"type": "string"},
                "city": {"type": ["string", "null"]},
                "region": {"type": ["string", "null"]},
                "website": {"type": "string"},
                "contact": {"type": ["string", "null"]},
                "min_order": {"type": ["string", "null"]},
                "price_hint": {"type": ["string", "null"]},
                "certificates": {"type": ["string", "null"]},
                "delivery": {"type": ["string", "null"]},
            },
        },
    }
    system = (
        "Извлекай только факты, которые явно присутствуют на странице поставщика. "
        "Если факта нет, возвращай null. Не придумывай коммерческие условия, "
        "контакты, цены и документы."
    )
    user = (
        f"Категория запроса: {category_hint}\n"
        f"География запроса: {geography_hint or 'не указана'}\n"
        f"URL: {url}\n"
        f"Текст страницы:\n{text}"
    )
    payload = {
        "model": settings.llm_model,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "text": {"format": {"type": "json_schema", **schema}},
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            f"{settings.llm_base_url.rstrip('/')}/responses",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    raw = data["output"][0]["content"][0]["text"]
    obj = json.loads(raw)
    geography = geography_hint or "не указан"
    obj["city"] = obj.get("city") or geography
    obj["region"] = obj.get("region") or geography
    obj["category"] = obj.get("category") or category_hint
    obj["website"] = obj.get("website") or url

    return ExtractedSupplier(**obj, source_url=url)

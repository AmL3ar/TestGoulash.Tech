import json
from typing import Any

import httpx

from ..config import settings
from .types import ExtractedSupplier


SUPPLIER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["suppliers"],
    "properties": {
        "suppliers": {
            "type": "array",
            "items": {
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
                    "source_url",
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
                    "source_url": {"type": "string"},
                },
            },
        }
    },
}


def _output_text(data: dict[str, Any]) -> str:
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    raise ValueError("OpenAI Responses API не вернул текстовый результат")


def parse_supplier_response(
    data: dict[str, Any],
    category: str,
    geography: str | None,
    limit: int,
) -> list[ExtractedSupplier]:
    payload = json.loads(_output_text(data))
    suppliers: list[ExtractedSupplier] = []

    for raw in payload.get("suppliers", [])[:limit]:
        source_url = str(raw.get("source_url") or "").strip()
        website = str(raw.get("website") or source_url).strip()
        name = str(raw.get("name") or "").strip()
        if not name or not source_url.startswith(("http://", "https://")):
            continue
        if not website.startswith(("http://", "https://")):
            website = source_url

        suppliers.append(
            ExtractedSupplier(
                name=name,
                category=str(raw.get("category") or category).strip() or category,
                city=str(raw.get("city") or geography or "не указан").strip(),
                region=str(raw.get("region") or geography or "не указан").strip(),
                website=website,
                contact=raw.get("contact"),
                min_order=raw.get("min_order"),
                price_hint=raw.get("price_hint"),
                certificates=raw.get("certificates"),
                delivery=raw.get("delivery"),
                source_url=source_url,
            )
        )

    return suppliers


async def discover_suppliers_with_openai(
    category: str,
    geography: str | None,
    limit: int = 3,
) -> list[ExtractedSupplier]:
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY не настроен")

    geography_text = geography or "география не указана"
    prompt = (
        "Найди поставщиков продуктов питания, ингредиентов или пищевой упаковки "
        f"по запросу «{category}» для географии «{geography_text}». "
        f"Верни не более {limit} релевантных поставщиков. Используй веб-поиск и "
        "по возможности официальные сайты компаний. Не включай маркетплейсы, "
        "доски объявлений, каталоги-агрегаторы и информационные статьи. Для каждого "
        "поставщика извлеки только факты, которые явно подтверждаются найденными "
        "источниками: название, категорию, город, регион, официальный сайт, контакт, "
        "MOQ, ориентир по цене, сертификаты и доставку. Если конкретного факта нет, "
        "верни null. Не придумывай цены, документы, контакты или условия. В source_url "
        "укажи конкретную страницу, на основании которой сформирована карточка."
    )
    request_payload = {
        "model": settings.llm_model,
        "tools": [
            {
                "type": "web_search",
                "search_context_size": "medium",
            }
        ],
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "supplier_search",
                "description": "Список релевантных поставщиков с подтверждаемыми фактами",
                "strict": True,
                "schema": SUPPLIER_SCHEMA,
            }
        },
        "store": False,
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.llm_base_url.rstrip('/')}/responses",
            headers=headers,
            json=request_payload,
        )
        response.raise_for_status()
        data = response.json()

    return parse_supplier_response(data, category, geography, limit)

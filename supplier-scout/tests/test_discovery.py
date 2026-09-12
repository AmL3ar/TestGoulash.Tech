import json

import pytest

from app.services.discovery import _output_text, parse_supplier_response


def response_payload(suppliers):
    return {
        "output": [
            {"type": "web_search_call", "status": "completed"},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {"suppliers": suppliers},
                            ensure_ascii=False,
                        ),
                    }
                ],
            },
        ]
    }


def test_output_text_skips_tool_calls():
    data = response_payload([])

    assert json.loads(_output_text(data)) == {"suppliers": []}


def test_parse_supplier_response_builds_card():
    data = response_payload(
        [
            {
                "name": "Молочный дом",
                "category": "моцарелла и сыры",
                "city": "Екатеринбург",
                "region": "Свердловская область",
                "website": "https://example.ru",
                "contact": "+7 343 000-00-00",
                "min_order": "10 кг",
                "price_hint": None,
                "certificates": "декларация соответствия",
                "delivery": "по Екатеринбургу",
                "source_url": "https://example.ru/opt",
            }
        ]
    )

    items = parse_supplier_response(data, "моцарелла", "Екатеринбург", 3)

    assert len(items) == 1
    assert items[0].name == "Молочный дом"
    assert items[0].source_url == "https://example.ru/opt"


def test_parse_supplier_response_rejects_item_without_http_source():
    data = response_payload(
        [
            {
                "name": "Молочный дом",
                "category": "моцарелла",
                "city": None,
                "region": None,
                "website": "example.ru",
                "contact": None,
                "min_order": None,
                "price_hint": None,
                "certificates": None,
                "delivery": None,
                "source_url": "example.ru/opt",
            }
        ]
    )

    assert parse_supplier_response(data, "моцарелла", None, 3) == []


def test_output_text_requires_message():
    with pytest.raises(ValueError):
        _output_text({"output": [{"type": "web_search_call"}]})

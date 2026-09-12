from datetime import datetime
from types import SimpleNamespace

from app.services.exporter import make_csv, make_xlsx


def supplier():
    return SimpleNamespace(
        name="Тестовый поставщик",
        category="овощи",
        city="Екатеринбург",
        region="Свердловская область",
        contact="+7 343 000-00-00",
        min_order="10 кг",
        price_hint="100 ₽/кг",
        certificates="декларация",
        delivery="есть",
        notes="позвонить",
        website="https://example.ru",
        source_url="https://example.ru/catalog",
        source_checked_at=datetime(2026, 9, 13, 10, 30),
    )


def test_csv_contains_headers_and_supplier():
    content = make_csv([supplier()]).decode("utf-8-sig")

    assert "Поставщик;Категория;Город" in content
    assert "Тестовый поставщик" in content
    assert "+7 343 000-00-00" in content


def test_xlsx_has_zip_signature():
    content = make_xlsx([supplier()])

    assert content[:2] == b"PK"

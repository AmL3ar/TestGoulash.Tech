from app.services.heuristics import EMAIL_RE, PHONE_RE, _name, _sentence


def test_phone_and_email_are_found():
    text = "Отдел продаж: +7 (343) 123-45-67, sales@example.ru"

    assert PHONE_RE.search(text).group(0) == "+7 (343) 123-45-67"
    assert EMAIL_RE.search(text).group(0) == "sales@example.ru"


def test_sentence_extracts_delivery_condition():
    text = "Компания работает с оптом. Доставка по Екатеринбургу от 5000 рублей. Есть самовывоз."

    assert _sentence(text, ("достав",)) == "Доставка по Екатеринбургу от 5000 рублей."


def test_name_prefers_title_before_separator():
    assert _name("Поставщик Плюс | официальный сайт", "https://example.ru") == "Поставщик Плюс"

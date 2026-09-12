from app.services.heuristics import EMAIL_RE, PHONE_RE, _sentence, is_relevant_page


def test_phone_extraction():
    match = PHONE_RE.search("Телефон: +7 (343) 123-45-67")
    assert match
    assert "343" in match.group(0)


def test_email_extraction():
    match = EMAIL_RE.search("Пишите на sales@example.ru")
    assert match
    assert match.group(0) == "sales@example.ru"


def test_delivery_sentence():
    text = "Каталог продукции. Доставка по Екатеринбургу выполняется ежедневно. Оплата по счёту."
    value = _sentence(text, ("достав",))
    assert value == "Доставка по Екатеринбургу выполняется ежедневно."


def test_relevant_supplier_page():
    text = "Моцарелла для пиццы оптом. Поставщик для HoReCa. Доставка по Екатеринбургу."
    assert is_relevant_page(text, "моцарелла", "Екатеринбург")


def test_irrelevant_school_page():
    text = "Как рассчитать оценку за школьную контрольную работу и перевести баллы в отметку."
    assert not is_relevant_page(text, "моцарелла", "Екатеринбург")

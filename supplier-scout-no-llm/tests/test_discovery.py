from app.services.discovery import (
    SearchHit,
    _clean_result_url,
    _hit_relevance,
    _parse_bing_rss,
    _parse_serper,
)


def test_clean_duckduckgo_redirect():
    value = (
        "https://duckduckgo.com/l/?uddg="
        "https%3A%2F%2Fexample.ru%2Fcatalog%3Fa%3D1"
    )
    assert _clean_result_url(value) == "https://example.ru/catalog?a=1"


def test_blocked_search_host():
    assert _clean_result_url("https://www.google.com/search?q=test") is None


def test_parse_bing_rss():
    xml = """
    <rss><channel>
      <item>
        <title>Моцарелла оптом в Екатеринбурге</title>
        <link>https://supplier.example/catalog</link>
        <description>Поставщик сыров для HoReCa</description>
      </item>
    </channel></rss>
    """
    hits = _parse_bing_rss(xml)
    assert len(hits) == 1
    assert hits[0].url == "https://supplier.example/catalog"
    assert "Моцарелла" in hits[0].title


def test_irrelevant_search_hit_is_rejected():
    hit = SearchHit(
        url="https://szkolabezsmartfonow.pl/article",
        title="Jak obliczyć ocenę ze sprawdzianu",
        snippet="Proste metody obliczania punktacji w szkole",
    )
    assert _hit_relevance(hit, "моцарелла", "Екатеринбург") == -1


def test_relevant_supplier_hit_has_high_score():
    hit = SearchHit(
        url="https://example.ru/mozzarella",
        title="Моцарелла оптом в Екатеринбурге",
        snippet="Поставщик сыра для ресторанов и HoReCa, доставка со склада",
    )
    assert _hit_relevance(hit, "моцарелла", "Екатеринбург") >= 9


def test_parse_serper_results():
    payload = {
        "organic": [
            {
                "title": "Моцарелла оптом — поставщик для HoReCa",
                "link": "https://supplier.example/mozzarella",
                "snippet": "Доставка по Екатеринбургу, оптовые поставки сыров",
            }
        ]
    }
    hits = _parse_serper(payload)
    assert len(hits) == 1
    assert hits[0].url == "https://supplier.example/mozzarella"
    assert "Моцарелла" in hits[0].title


def test_recipe_result_is_rejected():
    hit = SearchHit(
        url="https://example.ru/recept",
        title="Как приготовить моцареллу дома",
        snippet="Рецепт сыра моцарелла пошагово",
    )
    assert _hit_relevance(hit, "моцарелла", "Екатеринбург") == -1

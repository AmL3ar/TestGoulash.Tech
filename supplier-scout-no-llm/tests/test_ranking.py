from types import SimpleNamespace

from app.schemas import SearchRequest
from app.services.ranking import rank_supplier


def supplier(**overrides):
    base = {
        "category": "овощи и фрукты",
        "city": "Екатеринбург",
        "region": "Свердловская область",
        "verified_contact": True,
        "price_hint": "100 ₽",
        "min_order": "10000 ₽",
        "delivery": "есть",
        "certificates": "есть",
        "data_completeness": 0.9,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_exact_geography_and_category_rank_high():
    query = SearchRequest(
        category="овощи",
        geography="Екатеринбург",
        need_delivery=True,
        need_certificates=True,
    )

    result = rank_supplier(supplier(), query)

    assert result.score >= 80
    assert "категория совпадает" in result.reasons


def test_missing_commercial_data_reduces_score():
    query = SearchRequest(category="овощи", geography="Екатеринбург")
    rich = rank_supplier(supplier(), query).score
    poor = rank_supplier(
        supplier(
            verified_contact=False,
            price_hint=None,
            min_order=None,
            delivery=None,
            certificates=None,
            data_completeness=0.2,
        ),
        query,
    ).score

    assert rich > poor


def test_region_match_is_weaker_than_city_match():
    query = SearchRequest(category="овощи", geography="Свердловская область")
    region_score = rank_supplier(
        supplier(city="Екатеринбург", region="Свердловская область"),
        query,
    ).score
    city_score = rank_supplier(
        supplier(city="Свердловская область", region="Свердловская область"),
        query,
    ).score

    assert city_score > region_score


def test_verified_catalog_contact_adds_score():
    query = SearchRequest(category="овощи")
    verified = rank_supplier(supplier(verified_contact=True), query).score
    unverified = rank_supplier(supplier(verified_contact=False), query).score

    assert verified - unverified == 8

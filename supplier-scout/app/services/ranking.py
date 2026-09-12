from dataclasses import dataclass

from ..models import Supplier
from ..schemas import SearchRequest


@dataclass
class Ranked:
    supplier: Supplier
    score: float
    reasons: list[str]


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def rank_supplier(supplier: Supplier, query: SearchRequest) -> Ranked:
    score = 0.0
    reasons: list[str] = []
    category = _norm(query.category)
    supplier_category = _norm(supplier.category)

    if category in supplier_category or supplier_category in category:
        score += 35
        reasons.append("категория совпадает")
    else:
        terms = set(category.split())
        overlap = len(terms & set(supplier_category.split()))
        score += min(overlap * 8, 24)
        if overlap:
            reasons.append("есть совпадение по товарной группе")

    geography = _norm(query.geography)
    if geography:
        if geography == _norm(supplier.city) or geography in _norm(supplier.city):
            score += 20
            reasons.append("работает в выбранном городе")
        elif geography in _norm(supplier.region):
            score += 14
            reasons.append("работает в выбранном регионе")

    if supplier.verified_contact:
        score += 8
        reasons.append("контакт проверен в исходном каталоге")

    if supplier.price_hint:
        score += 6
        reasons.append("есть ориентир по цене")

    if supplier.min_order:
        score += 5
        reasons.append("известен минимальный заказ")

    if supplier.delivery:
        score += 5
        if query.need_delivery:
            score += 5
            reasons.append("есть информация о доставке")

    if supplier.certificates:
        score += 5
        if query.need_certificates:
            score += 6
            reasons.append("есть информация о сертификатах")

    completeness_bonus = round((supplier.data_completeness or 0) * 10, 1)
    score += completeness_bonus
    if completeness_bonus >= 7:
        reasons.append("карточка хорошо заполнена")

    return Ranked(
        supplier=supplier,
        score=round(min(score, 100), 1),
        reasons=reasons[:4],
    )

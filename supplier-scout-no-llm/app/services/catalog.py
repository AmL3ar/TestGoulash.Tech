from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Supplier
from .types import ExtractedSupplier


FIELDS = (
    "contact",
    "min_order",
    "price_hint",
    "certificates",
    "delivery",
)


def completeness(item: ExtractedSupplier) -> float:
    values = [
        item.name,
        item.category,
        item.city,
        item.region,
        item.website,
        *[getattr(item, field) for field in FIELDS],
    ]
    return round(sum(bool(value) for value in values) / len(values), 2)


def save_extracted(db: Session, item: ExtractedSupplier) -> Supplier:
    supplier = db.scalar(
        select(Supplier).where(Supplier.source_url == item.source_url)
    )

    if supplier is None:
        supplier = Supplier(
            name=item.name or "Поставщик",
            category=item.category,
            city=item.city or "не указан",
            region=item.region or "не указан",
            website=item.website or item.source_url,
            source_url=item.source_url,
        )
        db.add(supplier)

    supplier.name = item.name or supplier.name
    supplier.category = item.category or supplier.category
    supplier.city = item.city or supplier.city
    supplier.region = item.region or supplier.region
    supplier.website = item.website or supplier.website
    supplier.contact = item.contact
    supplier.min_order = item.min_order
    supplier.price_hint = item.price_hint
    supplier.certificates = item.certificates
    supplier.delivery = item.delivery
    supplier.data_completeness = completeness(item)
    supplier.verified_contact = False
    supplier.source_checked_at = datetime.utcnow()

    db.commit()
    db.refresh(supplier)
    return supplier

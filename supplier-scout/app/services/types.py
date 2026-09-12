from dataclasses import dataclass


@dataclass
class ExtractedSupplier:
    name: str
    category: str
    city: str
    region: str
    website: str
    contact: str | None = None
    min_order: str | None = None
    price_hint: str | None = None
    certificates: str | None = None
    delivery: str | None = None
    source_url: str = ""

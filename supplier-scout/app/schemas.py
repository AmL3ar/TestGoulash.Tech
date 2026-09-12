from datetime import datetime
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    category: str = Field(min_length=2, max_length=140)
    geography: str | None = Field(default=None, max_length=160)
    need_delivery: bool = False
    need_certificates: bool = False
    live_search: bool = False
    limit: int = Field(default=10, ge=1, le=50)


class SupplierOut(BaseModel):
    id: int
    name: str
    category: str
    city: str
    region: str
    website: str
    contact: str | None
    min_order: str | None
    price_hint: str | None
    certificates: str | None
    delivery: str | None
    notes: str | None
    source_url: str
    source_checked_at: datetime
    data_completeness: float
    verified_contact: bool
    score: float = 0.0
    score_reasons: list[str] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    query: SearchRequest
    suppliers: list[SupplierOut]
    explanation: str
    mode: str
    discovered: int = 0


class NoteUpdate(BaseModel):
    notes: str = Field(max_length=2000)


class ExportRequest(BaseModel):
    supplier_ids: list[int] = Field(min_length=1, max_length=50)

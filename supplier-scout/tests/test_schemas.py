import pytest
from pydantic import ValidationError

from app.schemas import ExportRequest, NoteUpdate, SearchRequest


def test_note_length_is_limited():
    with pytest.raises(ValidationError):
        NoteUpdate(notes="x" * 2001)


def test_search_limit_is_limited():
    with pytest.raises(ValidationError):
        SearchRequest(category="овощи", limit=51)


def test_export_requires_at_least_one_supplier():
    with pytest.raises(ValidationError):
        ExportRequest(supplier_ids=[])


def test_unknown_search_fields_are_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(category="овощи", require_delivery=True)

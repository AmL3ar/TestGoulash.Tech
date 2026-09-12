import logging
from io import BytesIO
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine, get_db
from .models import Supplier
from .schemas import ExportRequest, NoteUpdate, SearchRequest, SearchResponse, SupplierOut
from .seed import seed_if_empty
from .services.catalog import save_extracted
from .services.discovery import discover_supplier_urls
from .services.enrichment import extract_with_llm
from .services.exporter import make_csv, make_xlsx
from .services.heuristics import extract_with_rules
from .services.ranking import rank_supplier


BASE = Path(__file__).resolve().parent
logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title=settings.app_name,
    version="2.1.0",
    description="Сервис для поиска, сравнения и приоритизации поставщиков",
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    seed_if_empty()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "ai": bool(settings.llm_api_key),
    }


async def _live_enrichment(payload: SearchRequest, db: Session) -> tuple[int, str]:
    try:
        urls = await discover_supplier_urls(
            payload.category,
            payload.geography,
            settings.live_search_limit,
        )
    except Exception as exc:
        logger.warning("Веб-поиск недоступен: %s", exc)
        return 0, "веб-поиск недоступен, использован локальный каталог"

    added = 0
    used_ai = bool(settings.llm_api_key)

    for url in urls:
        try:
            if used_ai:
                item = await extract_with_llm(
                    url,
                    payload.category,
                    payload.geography,
                )
            else:
                item = await extract_with_rules(
                    url,
                    payload.category,
                    payload.geography,
                )
            save_extracted(db, item)
            added += 1
        except Exception as exc:
            logger.warning("Не удалось обработать источник %s: %s", url, exc)

    if used_ai:
        return added, "веб-поиск + извлечение фактов через LLM"

    return (
        added,
        "веб-поиск + резервное извлечение по правилам, потому что LLM_API_KEY не настроен",
    )


@app.post("/api/search", response_model=SearchResponse)
async def search_suppliers(
    payload: SearchRequest,
    db: Session = Depends(get_db),
):
    discovered = 0
    mode = "локальный каталог"

    if payload.live_search:
        discovered, mode = await _live_enrichment(payload, db)

    stmt = select(Supplier).where(
        or_(
            Supplier.category.ilike(f"%{payload.category}%"),
            Supplier.name.ilike(f"%{payload.category}%"),
        )
    )
    candidates = list(db.scalars(stmt).all())

    if not candidates:
        candidates = list(db.scalars(select(Supplier)).all())

    ranked = sorted(
        (rank_supplier(supplier, payload) for supplier in candidates),
        key=lambda item: item.score,
        reverse=True,
    )[: payload.limit]

    output: list[SupplierOut] = []
    for ranked_item in ranked:
        card = SupplierOut.model_validate(ranked_item.supplier)
        card.score = ranked_item.score
        card.score_reasons = ranked_item.reasons
        output.append(card)

    return SearchResponse(
        query=payload,
        suppliers=output,
        mode=mode,
        discovered=discovered,
        explanation=(
            "Рейтинг рассчитывается обычным кодом: категория, география, контакты, "
            "цена, MOQ, доставка, документы и полнота карточки. LLM используется "
            "только для извлечения фактов из неструктурированных страниц."
        ),
    )


@app.get("/api/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "Поставщик не найден")
    return SupplierOut.model_validate(supplier)


@app.patch("/api/suppliers/{supplier_id}/notes", response_model=SupplierOut)
def update_notes(
    supplier_id: int,
    payload: NoteUpdate,
    db: Session = Depends(get_db),
):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "Поставщик не найден")

    supplier.notes = payload.notes.strip() or None
    db.commit()
    db.refresh(supplier)
    return SupplierOut.model_validate(supplier)


def _suppliers_by_ids(db: Session, supplier_ids: list[int]) -> list[Supplier]:
    values = list(
        db.scalars(select(Supplier).where(Supplier.id.in_(supplier_ids))).all()
    )
    indexed = {supplier.id: supplier for supplier in values}
    return [
        indexed[supplier_id]
        for supplier_id in supplier_ids
        if supplier_id in indexed
    ]


@app.post("/api/export/csv")
def export_csv(payload: ExportRequest, db: Session = Depends(get_db)):
    suppliers = _suppliers_by_ids(db, payload.supplier_ids)
    if not suppliers:
        raise HTTPException(404, "Нет данных для экспорта")

    return Response(
        make_csv(suppliers),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=postavshiki.csv"},
    )


@app.post("/api/export/xlsx")
def export_xlsx(payload: ExportRequest, db: Session = Depends(get_db)):
    suppliers = _suppliers_by_ids(db, payload.supplier_ids)
    if not suppliers:
        raise HTTPException(404, "Нет данных для экспорта")

    stream = BytesIO(make_xlsx(suppliers))
    return StreamingResponse(
        stream,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": "attachment; filename=postavshiki.xlsx"},
    )

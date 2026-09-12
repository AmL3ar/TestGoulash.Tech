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
from .services.exporter import make_csv, make_xlsx
from .services.heuristics import extract_with_rules
from .services.ranking import rank_supplier


BASE = Path(__file__).resolve().parent
logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title=settings.app_name,
    version="2.5.0",
    description="Версия сервиса без LLM: веб-поиск с фильтрацией релевантности, BeautifulSoup и правила",
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
        "ai": False,
        "mode": "rules",
    }


async def _live_enrichment(
    payload: SearchRequest,
    db: Session,
) -> tuple[list[int], str]:
    try:
        urls = await discover_supplier_urls(
            payload.category,
            payload.geography,
            settings.live_search_limit,
        )
    except Exception as exc:
        logger.warning(
            "Веб-поиск без LLM недоступен: %s: %r",
            type(exc).__name__,
            exc,
        )
        return [], "веб-поиск временно недоступен; показаны только локальные совпадения"

    supplier_ids: list[int] = []
    for url in urls:
        try:
            item = await extract_with_rules(
                url,
                payload.category,
                payload.geography,
            )
            supplier = save_extracted(db, item)
            supplier_ids.append(supplier.id)
        except Exception as exc:
            logger.warning(
                "Не удалось обработать источник %s: %s: %r",
                url,
                type(exc).__name__,
                exc,
            )

    if supplier_ids:
        return (
            supplier_ids,
            "веб-поиск + извлечение через BeautifulSoup, регулярные выражения и правила",
        )

    return [], "веб-поиск выполнен, релевантные поставщики не найдены"


@app.post("/api/search", response_model=SearchResponse)
async def search_suppliers(
    payload: SearchRequest,
    db: Session = Depends(get_db),
):
    discovered_ids: list[int] = []
    mode = "локальный каталог"

    if payload.live_search:
        discovered_ids, mode = await _live_enrichment(payload, db)

    stmt = select(Supplier).where(
        or_(
            Supplier.category.ilike(f"%{payload.category}%"),
            Supplier.name.ilike(f"%{payload.category}%"),
        )
    )
    local_candidates = list(db.scalars(stmt).all())
    candidates_by_id = {supplier.id: supplier for supplier in local_candidates}

    if discovered_ids:
        discovered = list(
            db.scalars(select(Supplier).where(Supplier.id.in_(discovered_ids))).all()
        )
        candidates_by_id.update({supplier.id: supplier for supplier in discovered})

    candidates = list(candidates_by_id.values())
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
        discovered=len(discovered_ids),
        explanation=(
            "В этой версии LLM не используется. Новые сайты ищутся через HTML-выдачу "
            "поисковиков, данные извлекаются BeautifulSoup, регулярными выражениями "
            "и словарными правилами, а рейтинг рассчитывается обычным Python-кодом."
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

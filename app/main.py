import os
from io import BytesIO
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.catalog import get_catalog_entry, load_dsp_catalog
from app.config import ROOT, SOURCE_DATA_DIR, SPRAVKA_DSP_PATH, STATIC_DIR, TEMPLATE_PATH
from app.engine.transform import transform_source
from app.profiles.loader import has_transform_profile, load_profile
from app.reporting import build_output_filename, validate_report_period
from app.source_data import save_source_file
from app.validation.validate import validate_workbook_bytes

app = FastAPI(title="DSP Transform", version="0.1.0")


def _content_disposition(filename: str) -> str:
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded}"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>DSP Transform</h1><p>static/index.html not found</p>")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/api/partners")
def api_partners():
    load_dsp_catalog.cache_clear()
    return {
        "partners": [
            {
                "id": e.id,
                "display_name": e.display_name,
                "dsp_ids": e.dsp_ids,
                "contract": e.contract,
                "report_to_ord": e.report_to_ord,
                "url": e.url,
                "has_profile": e.has_profile,
            }
            for e in load_dsp_catalog()
        ]
    }


@app.post("/api/source-data")
async def api_source_data(
    file: UploadFile = File(...),
    partner_id: str = Form(...),
):
    if not file.filename:
        raise HTTPException(400, "Не указано имя файла")

    ext = file.filename.lower()
    if not ext.endswith((".xlsx", ".xlsm", ".xls")):
        raise HTTPException(400, "Нужен файл .xlsx, .xlsm или .xls")

    entry = get_catalog_entry(partner_id)
    if entry is None:
        raise HTTPException(404, f"DSP не найден в справочнике: {partner_id}")

    if has_transform_profile(partner_id):
        raise HTTPException(
            400,
            f"Для «{entry.display_name}» преобразование уже настроено — загрузка образца не нужна.",
        )

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "Файл больше 50 МБ")

    try:
        saved = save_source_file(
            partner_id,
            entry.display_name,
            content,
            file.filename,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except OSError as e:
        raise HTTPException(500, f"Не удалось сохранить файл: {e}") from e

    msg = (
        f"Файл сохранён: Исходные данные/{saved.filename}"
        if not saved.replaced
        else (
            f"Файл сохранён: Исходные данные/{saved.filename} "
            "(предыдущая версия переименована с датой в имени)"
        )
    )
    return {
        "ok": True,
        "message": msg,
        "filename": saved.filename,
        "partner_id": saved.partner_id,
        "display_name": saved.display_name,
        "replaced": saved.replaced,
    }


@app.post("/api/transform")
async def api_transform(
    file: UploadFile = File(...),
    partner_id: str = Form(...),
    report_month: int = Form(...),
    report_year: int = Form(...),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Нужен файл .xlsx")

    entry = get_catalog_entry(partner_id)
    if entry is None:
        raise HTTPException(404, f"DSP не найден в справочнике: {partner_id}")

    if not has_transform_profile(partner_id):
        raise HTTPException(
            400,
            f"Профиль преобразования для «{entry.display_name}» ещё не настроен.",
        )

    try:
        validate_report_period(report_month, report_year)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "Файл больше 50 МБ")

    out_name = build_output_filename(partner_id, report_month, report_year)
    try:
        result = transform_source(
            BytesIO(content),
            load_profile(partner_id),
            template_path=TEMPLATE_PATH,
            output_filename=out_name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(500, str(e)) from e

    if result.rows_written == 0:
        raise HTTPException(400, "Нет данных для записи")

    validation_errors = validate_workbook_bytes(result.output_bytes)
    headers = {
        "Content-Disposition": _content_disposition(out_name),
        "X-Rows-Written": str(result.rows_written),
        "X-Skipped-Empty-Rows": str(result.skipped_empty_rows),
        "X-Validation-Error-Count": str(len(validation_errors)),
    }
    return Response(
        content=result.output_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/health")
def health():
    load_dsp_catalog.cache_clear()
    catalog = load_dsp_catalog()
    return {
        "status": "ok",
        "template": TEMPLATE_PATH.exists(),
        "spravka": SPRAVKA_DSP_PATH.exists(),
        "dsp_count": len(catalog),
        "profiles_ready": sum(1 for e in catalog if e.has_profile),
        "source_data_dir": str(SOURCE_DATA_DIR),
        "source_data_writable": SOURCE_DATA_DIR.exists()
        and os.access(SOURCE_DATA_DIR, os.W_OK),
    }

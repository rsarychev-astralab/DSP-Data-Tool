import asyncio
from io import BytesIO
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.catalog import get_catalog_entry, get_catalog_warnings, load_dsp_catalog
from app.config import SPRAVKA_DSP_PATH, STATIC_DIR, TEMPLATE_PATH
from app.engine.transform import transform_source
from app.http_utils import encode_validation_errors
from app.profiles.loader import has_transform_profile, load_profile
from app.reporting import build_output_filename, validate_report_period
from app.source_data import save_source_file
from app.validation.validate import validate_workbook_bytes

app = FastAPI(title="DSP Transform", version="0.1.0")


def _content_disposition(filename: str) -> str:
    encoded = quote(filename, safe="")
    safe = filename.replace("\\", "_").replace('"', "")
    return f"attachment; filename=\"{safe}\"; filename*=UTF-8''{encoded}"


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
        ],
        "warnings": get_catalog_warnings(),
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
        saved = await asyncio.to_thread(
            save_source_file,
            partner_id,
            entry.display_name,
            content,
            file.filename,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except OSError as e:
        raise HTTPException(500, f"Не удалось сохранить файл: {e}") from e

    if saved.replaced:
        msg = (
            f"Файл «{saved.filename}» сохранён для настройки маппинга "
            "(предыдущая версия переименована с датой в имени)."
        )
    else:
        msg = f"Файл «{saved.filename}» сохранён для настройки маппинга."

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
        raise HTTPException(400, "Нужен файл .xlsx или .xlsm")

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
        profile = load_profile(partner_id)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e)) from e

    try:
        result = await asyncio.to_thread(
            transform_source,
            BytesIO(content),
            profile,
            template_path=TEMPLATE_PATH,
            output_filename=out_name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(500, str(e)) from e

    if result.rows_written == 0:
        raise HTTPException(400, "Нет данных для записи")

    validation_errors = await asyncio.to_thread(
        validate_workbook_bytes, result.output_bytes, profile
    )
    headers = {
        "Content-Disposition": _content_disposition(out_name),
        "X-Rows-Written": str(result.rows_written),
        "X-Skipped-Empty-Rows": str(result.skipped_empty_rows),
        "X-Validation-Error-Count": str(len(validation_errors)),
    }
    encoded_errors = encode_validation_errors(validation_errors)
    if encoded_errors:
        headers["X-Validation-Errors"] = encoded_errors

    return Response(
        content=result.output_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/health")
def health():
    catalog = load_dsp_catalog()
    return {
        "status": "ok",
        "dsp_count": len(catalog),
        "profiles_ready": sum(1 for e in catalog if e.has_profile),
        "template_ok": TEMPLATE_PATH.exists(),
        "spravka_ok": SPRAVKA_DSP_PATH.exists(),
    }

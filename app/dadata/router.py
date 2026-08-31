import asyncio
import time
import uuid
from dataclasses import dataclass, field

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.dadata.client import fetch_party, fetch_party_with_retry, suggest_party
from app.dadata.core import (
    ALLOWED_OUTPUT,
    BATCH_DELAY_SEC,
    JOB_TTL_SEC,
    MAX_UPLOAD_BYTES,
    build_result_file,
    default_output_format,
    inn_checksum_ok,
    parse_uploaded_inns,
    party_to_row,
    suffix_allowed,
)

router = APIRouter(prefix="/api/dadata", tags=["dadata"])


@dataclass
class BatchJob:
    id: str
    inns: list[str]
    output_format: str
    status: str = "queued"
    processed: int = 0
    rows: list[dict[str, str]] = field(default_factory=list)
    error: str | None = None
    message: str | None = None
    created_at: float = field(default_factory=time.time)

    @property
    def total(self) -> int:
        return len(self.inns)


JOBS: dict[str, BatchJob] = {}


def _cleanup_jobs() -> None:
    now = time.time()
    expired = [job_id for job_id, job in JOBS.items() if now - job.created_at > JOB_TTL_SEC]
    for job_id in expired:
        JOBS.pop(job_id, None)


async def _run_batch_job(job_id: str) -> None:
    job = JOBS.get(job_id)
    if not job:
        return

    job.status = "running"
    remaining_error: str | None = None

    async with httpx.AsyncClient(timeout=20.0) as client:
        for index, inn in enumerate(job.inns):
            if not inn_checksum_ok(inn):
                job.rows.append(
                    party_to_row(inn, None, error="Некорректная контрольная сумма ИНН")
                )
                job.processed = index + 1
                continue

            if remaining_error:
                job.rows.append(party_to_row(inn, None, error=remaining_error))
                job.processed = index + 1
                continue

            try:
                party = await fetch_party_with_retry(client, inn)
                job.rows.append(party_to_row(inn, party))
            except HTTPException as exc:
                if exc.status_code == 429:
                    remaining_error = str(exc.detail)
                    job.rows.append(party_to_row(inn, None, error=remaining_error))
                    job.message = "Остановлено из-за лимита DaData. Доступен частичный результат."
                else:
                    job.rows.append(party_to_row(inn, None, error=str(exc.detail)))
            except Exception as exc:  # noqa: BLE001
                job.rows.append(party_to_row(inn, None, error=str(exc)))

            job.processed = index + 1
            if index < len(job.inns) - 1 and not remaining_error:
                await asyncio.sleep(BATCH_DELAY_SEC)

    job.status = "completed"


@router.get("/suggest")
async def suggest(
    query: str = Query(..., min_length=1, max_length=300),
    count: int = Query(10, ge=1, le=20),
):
    return await suggest_party(query, count)


@router.get("/party")
async def party_by_inn(
    inn: str = Query(..., min_length=10, max_length=12, pattern=r"^\d{10}(\d{2})?$"),
):
    if not inn_checksum_ok(inn):
        raise HTTPException(status_code=400, detail="Некорректная контрольная сумма ИНН")

    async with httpx.AsyncClient(timeout=15.0) as client:
        party = await fetch_party(client, inn)

    if not party:
        raise HTTPException(status_code=404, detail="Организация не найдена")

    return party


@router.post("/batch")
async def batch_start(
    file: UploadFile = File(...),
    output_format: str = Form("auto"),
):
    filename = file.filename or "inns.csv"
    if not suffix_allowed(filename):
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются файлы .xlsx, .xls, .csv, .txt, .tsv",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Файл больше 5 МБ")

    fmt = (output_format or "auto").strip().lower()
    if fmt == "auto":
        fmt = default_output_format(filename)
    if fmt not in ALLOWED_OUTPUT:
        raise HTTPException(
            status_code=400,
            detail="Формат результата: xlsx, xls или csv",
        )

    inns = parse_uploaded_inns(content, filename)
    _cleanup_jobs()

    job_id = uuid.uuid4().hex
    job = BatchJob(id=job_id, inns=inns, output_format=fmt)
    JOBS[job_id] = job
    asyncio.create_task(_run_batch_job(job_id))

    return {
        "job_id": job_id,
        "total": job.total,
        "status": job.status,
    }


@router.get("/batch/{job_id}")
async def batch_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена или устарела")

    return {
        "job_id": job.id,
        "status": job.status,
        "processed": job.processed,
        "total": job.total,
        "error": job.error,
        "message": job.message,
        "download_ready": job.status == "completed" and bool(job.rows),
    }


@router.get("/batch/{job_id}/download")
async def batch_download(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена или устарела")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Результат ещё не готов")
    if not job.rows:
        raise HTTPException(status_code=404, detail="Нет данных для скачивания")

    payload, media_type, out_name = build_result_file(job.rows, job.output_format)
    return StreamingResponse(
        iter([payload]),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{out_name}"',
            "X-Processed-Count": str(len(job.rows)),
            "X-Output-Format": job.output_format,
        },
    )

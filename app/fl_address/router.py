import asyncio
import time
import uuid
from dataclasses import dataclass, field

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.fl_address.batch import (
    ALLOWED_OUTPUT,
    JOB_TTL_SEC,
    MAX_UPLOAD_BYTES,
    process_batch_file,
    problems_payload,
    suffix_allowed,
)
from app.fl_address.core import lookup_fl_address

router = APIRouter(prefix="/api/fl-address", tags=["fl-address"])


@dataclass
class BatchJob:
    id: str
    output_format: str
    status: str = "queued"
    processed: int = 0
    total: int = 0
    filled: int = 0
    errors: int = 0
    empty: int = 0
    problems: dict = field(default_factory=lambda: {"items": [], "total": 0})
    content: bytes | None = None
    media_type: str = ""
    filename: str = ""
    error: str | None = None
    created_at: float = field(default_factory=time.time)


JOBS: dict[str, BatchJob] = {}


def _cleanup_jobs() -> None:
    now = time.time()
    expired = [job_id for job_id, job in JOBS.items() if now - job.created_at > JOB_TTL_SEC]
    for job_id in expired:
        JOBS.pop(job_id, None)


def _job_status(job: BatchJob) -> dict:
    return {
        "job_id": job.id,
        "status": job.status,
        "processed": job.processed,
        "total": job.total,
        "filled": job.filled,
        "errors": job.errors,
        "empty": job.empty,
        "problems": job.problems,
        "error": job.error,
        "download_ready": job.status == "completed" and bool(job.content),
        "output_format": job.output_format,
    }


@router.get("/lookup")
def fl_address_by_inn(
    inn: str = Query(..., min_length=10, max_length=20),
):
    return lookup_fl_address(inn)


@router.post("/batch")
async def fl_address_batch(
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
    if not content:
        raise HTTPException(status_code=400, detail="Файл пустой")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Файл больше 10 МБ")

    fmt = (output_format or "auto").strip().lower()
    if fmt != "auto" and fmt not in ALLOWED_OUTPUT:
        raise HTTPException(
            status_code=400,
            detail="Формат результата: xlsx, xls или csv",
        )

    result = await asyncio.to_thread(process_batch_file, content, filename, fmt)
    _cleanup_jobs()
    job_id = uuid.uuid4().hex
    job = BatchJob(
        id=job_id,
        output_format=result.output_format,
        status="completed",
        processed=result.stats.total,
        total=result.stats.total,
        filled=result.stats.filled,
        errors=result.stats.errors,
        empty=result.stats.empty,
        problems=problems_payload(result.stats.problems),
        content=result.content,
        media_type=result.media_type,
        filename=result.filename,
    )
    JOBS[job_id] = job
    return _job_status(job)


@router.get("/batch/{job_id}")
def fl_address_batch_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена или устарела")
    return _job_status(job)


@router.get("/batch/{job_id}/download")
def fl_address_batch_download(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена или устарела")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Результат ещё не готов")
    if not job.content:
        raise HTTPException(status_code=404, detail="Нет данных для скачивания")

    return StreamingResponse(
        iter([job.content]),
        media_type=job.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{job.filename}"',
            "X-Processed-Count": str(job.total),
            "X-Output-Format": job.output_format,
        },
    )

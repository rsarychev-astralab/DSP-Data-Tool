import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.auth import BasicAuthMiddleware
from app.main import app
from app.uploads import read_upload_limited

client = TestClient(app)


def test_health_reports_auth_flag():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["auth_configured"] is False


def test_openapi_disabled_by_default():
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def _locked_app():
    async def ok(_request):
        return PlainTextResponse("ok")

    async def health(_request):
        return PlainTextResponse("health")

    starlette = Starlette(routes=[Route("/", ok), Route("/health", health)])
    starlette.add_middleware(BasicAuthMiddleware)
    return TestClient(starlette)


def test_basic_auth_rejects_without_credentials(monkeypatch):
    monkeypatch.setenv("DSP_BASIC_USER", "dsp")
    monkeypatch.setenv("DSP_BASIC_PASSWORD", "secret")
    locked = _locked_app()
    res = locked.get("/")
    assert res.status_code == 401
    assert locked.get("/health").status_code == 200


def test_basic_auth_accepts_valid_credentials(monkeypatch):
    monkeypatch.setenv("DSP_BASIC_USER", "dsp")
    monkeypatch.setenv("DSP_BASIC_PASSWORD", "secret")
    locked = _locked_app()
    res = locked.get("/", auth=("dsp", "secret"))
    assert res.status_code == 200
    assert res.text == "ok"


class _FakeUpload:
    def __init__(self, data: bytes):
        self._data = data
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._data):
            return b""
        end = len(self._data) if size < 0 else min(self._offset + size, len(self._data))
        piece = self._data[self._offset:end]
        self._offset = end
        return piece


def test_read_upload_limited_accepts_under_max():
    data = b"abcde"
    got = asyncio.run(read_upload_limited(_FakeUpload(data), 10))
    assert got == data


def test_read_upload_limited_rejects_over_max():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_upload_limited(_FakeUpload(b"0123456789abcdef"), 8))
    assert exc.value.status_code == 400

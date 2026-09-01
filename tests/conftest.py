import pytest


@pytest.fixture(autouse=True)
def _default_test_env(monkeypatch):
    monkeypatch.setenv("DSP_BASIC_USER", "")
    monkeypatch.setenv("DSP_BASIC_PASSWORD", "")
    monkeypatch.setenv("DSP_ENABLE_DOCS", "")

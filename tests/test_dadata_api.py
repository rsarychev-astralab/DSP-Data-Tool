from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_includes_dadata_flag():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert "dadata_configured" in body
    assert body["status"] == "ok"


def test_party_rejects_bad_checksum_without_dadata():
    res = client.get("/api/dadata/party", params={"inn": "1234567890"})
    assert res.status_code == 400
    assert "контрольная сумма" in res.json()["detail"]


def test_batch_rejects_unsupported_extension():
    res = client.post(
        "/api/dadata/batch",
        files={"file": ("inns.pdf", b"7707083893", "application/pdf")},
        data={"output_format": "xlsx"},
    )
    assert res.status_code == 400


def test_batch_rejects_empty_csv():
    res = client.post(
        "/api/dadata/batch",
        files={"file": ("inns.csv", b"name\nfoo\n", "text/csv")},
        data={"output_format": "csv"},
    )
    assert res.status_code == 400
    assert "ИНН" in res.json()["detail"]

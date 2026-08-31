import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.dadata.core import INN_11_WEIGHTS, INN_12_WEIGHTS, inn_checksum_ok
from app.fl_address.core import lookup_fl_address
from app.fl_address.regions import REGIONS, address_for_region
from app.main import app

client = TestClient(app)


def make_inn12(body10: str) -> str:
    digits = [int(ch) for ch in body10]
    n11 = sum(d * w for d, w in zip(digits, INN_11_WEIGHTS)) % 11 % 10
    digits.append(n11)
    n12 = sum(d * w for d, w in zip(digits, INN_12_WEIGHTS)) % 11 % 10
    digits.append(n12)
    inn = "".join(str(d) for d in digits)
    assert inn_checksum_ok(inn)
    return inn


def test_lookup_known_ip_inn_moscow_oblast():
    result = lookup_fl_address("500100732259")
    assert result["inn"] == "500100732259"
    assert result["region_code"] == "50"
    assert result["region"] == "Московская область"
    assert result["address"] == "Российская Федерация, Московская область"


def test_lookup_moscow_and_spb_aliases():
    moscow = lookup_fl_address(make_inn12("7700000001"))
    assert moscow["region"] == "г. Москва"
    assert moscow["address"] == "Российская Федерация, г. Москва"

    spb = lookup_fl_address(make_inn12("9800000001"))
    assert spb["region"] == "г. Санкт-Петербург"


def test_lookup_rejects_ul_inn():
    with pytest.raises(HTTPException) as exc_info:
        lookup_fl_address("7707083893")
    assert exc_info.value.status_code == 400
    assert "юрлицо" in exc_info.value.detail


def test_lookup_rejects_bad_checksum():
    with pytest.raises(HTTPException) as exc_info:
        lookup_fl_address("500100732250")
    assert exc_info.value.status_code == 400
    assert "контрольная сумма" in exc_info.value.detail


def test_lookup_accepts_inn_with_spaces():
    result = lookup_fl_address("5001 0073 2259")
    assert result["region_code"] == "50"


def test_every_region_code_has_address():
    for code, region in REGIONS.items():
        assert address_for_region(region).startswith("Российская Федерация, ")
        assert code.isdigit() and len(code) == 2


def test_lookup_unknown_region():
    inn = make_inn12("0000000001")
    with pytest.raises(HTTPException) as exc_info:
        lookup_fl_address(inn)
    assert exc_info.value.status_code == 422
    assert "00" in exc_info.value.detail


def test_api_lookup_ok():
    res = client.get("/api/fl-address/lookup", params={"inn": "500100732259"})
    assert res.status_code == 200
    body = res.json()
    assert body["address"] == "Российская Федерация, Московская область"


def test_api_lookup_rejects_10_digits():
    res = client.get("/api/fl-address/lookup", params={"inn": "7707083893"})
    assert res.status_code == 400
    assert "юрлицо" in res.json()["detail"]

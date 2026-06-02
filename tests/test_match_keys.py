from app.matching.keys import norm_contract_no, norm_inn, norm_intermediary_type


def test_norm_contract_no_strips_internal_id_after_dash():
    assert norm_contract_no("26/14 - 1993") == "26/14"
    assert norm_contract_no("TEST - 1991") == "TEST"
    assert norm_contract_no("08-БГ/2021 - 1994") == "08-БГ/2021"
    assert norm_contract_no("DOG-42") == "DOG-42"
    assert norm_contract_no("01/25/7045/25 - 999") == "01/25/7045/25"


def test_norm_inn_strips_spaces_and_float():
    assert norm_inn("77 03084411") == "7703084411"
    assert norm_inn(7703084411.0) == "7703084411"


def test_intermediary_none_and_na_equivalent():
    assert norm_intermediary_type("NA", from_db=True) == ""
    assert norm_intermediary_type("None", from_db=False) == ""

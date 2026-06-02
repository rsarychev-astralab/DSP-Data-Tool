from app.matching.keys import norm_intermediary_type, norm_party_name


def test_norm_party_name_strips_inn():
    assert norm_party_name("ООО «Тест» ИНН: 7700000001") == norm_party_name("ООО «Тест»")


def test_intermediary_none_and_na_equivalent():
    assert norm_intermediary_type("NA", from_db=True) == ""
    assert norm_intermediary_type("None", from_db=False) == ""

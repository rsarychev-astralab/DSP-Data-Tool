from app.matching.keys import split_party_name_inn


def test_split_party_name_inn():
    name, inn = split_party_name_inn('ООО «Нью Ченнел Плюс» ИНН: 7702848355')
    assert name == 'ООО «Нью Ченнел Плюс»'
    assert inn == '7702848355'

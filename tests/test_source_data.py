from app.source_data import build_source_filename


def test_build_source_filename_uses_partner_id():
    assert build_source_filename("buzzoola", "Report.XLSX") == "buzzoola.xlsx"


def test_build_source_filename_rejects_bad_ext():
    try:
        build_source_filename("sape", "file.csv")
        assert False, "expected ValueError"
    except ValueError:
        pass

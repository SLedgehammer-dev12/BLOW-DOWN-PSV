from app_metadata import APP_NAME, APP_VERSION, RELEASE_HISTORY, SOFTWARE_VERSION, build_about_text


def test_app_metadata_versions_are_consistent():
    assert APP_NAME == "Blowdown Studio"
    assert APP_VERSION == "v2.4.2"
    assert SOFTWARE_VERSION == "Blowdown Studio v2.4.2"


def test_build_about_text_includes_release_history():
    text = build_about_text()

    assert "Blowdown Studio HAKKINDA" in text
    assert "Surum          : v2.4.2" in text
    assert "Guncelleme Tarihcesi" in text
    assert RELEASE_HISTORY[0][0] in text
    assert "psvpy cross-check" in text

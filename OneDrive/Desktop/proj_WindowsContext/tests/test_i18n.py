from src.i18n import t, set_language, STRINGS, available_languages

def test_all_keys_exist_in_both_languages():
    ko_keys = set(STRINGS["ko"].keys())
    en_keys = set(STRINGS["en"].keys())
    assert ko_keys == en_keys, f"Missing in en: {ko_keys - en_keys}, Missing in ko: {en_keys - ko_keys}"

def test_t_returns_korean_by_default():
    set_language("ko")
    assert t("save_btn") == "현재 배치 저장"

def test_t_returns_english_after_switch():
    set_language("en")
    assert t("save_btn") == "Save Current Layout"
    set_language("ko")  # reset

def test_t_with_format_kwargs():
    set_language("ko")
    result = t("layout_saved", name="Screen1", count=5)
    assert "Screen1" in result
    assert "5" in result

def test_t_missing_key_returns_key():
    result = t("nonexistent_key_xyz")
    assert result == "nonexistent_key_xyz"

def test_available_languages():
    langs = available_languages()
    assert "ko" in langs
    assert "en" in langs

def test_set_language_invalid_code_does_not_change_language():
    set_language("ko")
    set_language("xx")  # invalid
    assert t("save_btn") == "현재 배치 저장"  # still ko


def test_mode_strings_present_in_all_languages():
    """ko/en 양쪽에 모드 관련 4개 키가 모두 존재하고 비어있지 않아야 한다."""
    required_keys = ("mode_fast", "mode_full", "mode_fast_desc", "mode_full_desc")
    for lang in ("ko", "en"):
        for key in required_keys:
            assert key in STRINGS[lang], f"'{key}' missing in lang='{lang}'"
            assert STRINGS[lang][key].strip(), f"'{key}' is empty in lang='{lang}'"

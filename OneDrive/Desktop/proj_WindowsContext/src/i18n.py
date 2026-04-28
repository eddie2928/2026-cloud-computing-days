STRINGS = {
    "ko": {
        "app_title": "WinLayoutSaver",
        "save_btn": "현재 배치 저장",
        "refresh_btn": "새로고침",
        "restore_btn": "복원",
        "settings_btn": "설정",
        "delete_btn": "삭제",
        "auto_rollback_label": "부팅 시 자동 복구:",
        "startup_delay_label": "시작 지연(초):",
        "enable_btn": "활성화",
        "disable_btn": "비활성화",
        "enabled_status": "활성화됨",
        "status_label": "상태:",
        "log_panel_title": "로그",
        "clear_btn": "지우기",
        "copy_btn": "복사",
        "open_log_dir_btn": "로그 폴더 열기",
        "confirm_restore_title": "모니터 구성 불일치",
        "confirm_restore_msg": "외부 모니터 구성이 달라 주 모니터 창만 복원됩니다. 계속하시겠습니까?",
        "yes": "예",
        "no": "아니오",
        "rename_dialog_title": "레이아웃 이름 변경",
        "rename_label": "새 이름:",
        "layout_deleted": "'{name}' 삭제됨",
        "layout_restored": "'{name}' 복원 완료 ({restored}/{total})",
        "layout_saved": "'{name}' 저장됨 ({count}개 창)",
        "no_layouts": "저장된 배치 없음",
        "log_module_filter_label": "모듈:",
    },
    "en": {
        "app_title": "WinLayoutSaver",
        "save_btn": "Save Current Layout",
        "refresh_btn": "Refresh",
        "restore_btn": "Restore",
        "settings_btn": "Settings",
        "delete_btn": "Delete",
        "auto_rollback_label": "Auto-restore on boot:",
        "startup_delay_label": "Startup delay (sec):",
        "enable_btn": "Enable",
        "disable_btn": "Disable",
        "enabled_status": "Enabled",
        "status_label": "Status:",
        "log_panel_title": "Logs",
        "clear_btn": "Clear",
        "copy_btn": "Copy",
        "open_log_dir_btn": "Open log folder",
        "confirm_restore_title": "Monitor mismatch",
        "confirm_restore_msg": "External monitor config differs. Only primary monitor windows will be restored. Continue?",
        "yes": "Yes",
        "no": "No",
        "rename_dialog_title": "Rename Layout",
        "rename_label": "New name:",
        "layout_deleted": "'{name}' deleted",
        "layout_restored": "'{name}' restored ({restored}/{total})",
        "layout_saved": "'{name}' saved ({count} windows)",
        "no_layouts": "No saved layouts",
        "log_module_filter_label": "Module:",
    },
}

_lang = "ko"


def set_language(lang: str) -> None:
    global _lang
    if lang in STRINGS:
        _lang = lang


def t(key: str, **kwargs) -> str:
    text = STRINGS.get(_lang, STRINGS["ko"]).get(key) or STRINGS["ko"].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def available_languages() -> list[str]:
    return list(STRINGS.keys())

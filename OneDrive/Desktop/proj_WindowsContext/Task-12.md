# Task-12: GUI 모드 선택 · 컨트롤 잠금 · 부팅 복구 버그 수정 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** fast/full 복구 모드 선택 UI 추가, 활성화 상태에서 관련 컨트롤 잠금, 부팅 시 fast 모드가 아무것도 복구하지 못하는 버그 수정

**Architecture:**
- `restore.py`에 `no_launch=False` 파라미터를 추가해 "스캔은 하되 앱 실행은 하지 않음" 경로를 분리한다.
- `rollback.py`를 단일 `restore_layout` 호출로 단순화하고 `enabled` 체크를 추가한다.
- `gui.py`에 Radio 버튼 행(fast / full)과 인라인 설명 Label을 추가하고, 활성화 시 delay·mode·layout 세 컨트롤을 모두 잠근다.

**Tech Stack:** Python 3.11+, tkinter, pywin32, pytest

**수정 파일 요약:**

| 파일 | 변경 내용 |
|------|----------|
| `src/restore.py` | `restore_layout`에 `no_launch=False` 파라미터 추가 |
| `src/i18n.py` | `mode_fast`, `mode_full`, `mode_fast_desc`, `mode_full_desc` 키 추가 (ko/en) |
| `src/gui.py` | 모드 Radio 행 추가, `_delay_entry` 참조 저장, 잠금 로직 추가 |
| `cli/rollback.py` | `enabled` 체크 추가, fast/full 분기를 `no_launch`로 단일화 |
| `tests/test_restore_matching.py` | `no_launch` 관련 테스트 3개 추가 |
| `tests/test_rollback_modes.py` | 기존 3개 테스트에 `"enabled": True` 추가, 신규 4개 테스트 추가 |
| `tests/integration/test_rollback_fast_speed.py` | config에 `"enabled": True` 추가 |
| `tests/test_gui_mode_selector.py` | 신규 파일: GUI 모드 선택 및 잠금 테스트 7개 |
| `tests/test_i18n.py` | 모드 문자열 키 존재 테스트 추가 |

---

## Task 1: `restore.py` — `no_launch` 파라미터 추가

**근거:** 현재 fast 모드는 `running_windows=[]`를 전달해 `ensure_apps_running`을 우회한다.  
`no_launch=True`를 추가하면 `running_windows=None`(실시간 스캔)을 유지하면서도 앱 실행을 건너뛸 수 있다.

**Files:**
- Modify: `src/restore.py:170-177` (함수 시그니처), `src/restore.py:235-243` (launch 블록)
- Test: `tests/test_restore_matching.py`

---

- [ ] **Step 1-1: 실패하는 테스트 3개 작성**

`tests/test_restore_matching.py` 파일 끝에 다음 3개 테스트를 추가한다.  
(`mock_layout_deps` 픽스처는 파일 내 기존 정의를 재사용. `mock_win32` autouse 픽스처가 각 테스트 후 `src.restore`를 sys.modules에서 제거하므로 매 테스트마다 최신 코드를 reimport한다.)

```python
# ──────────────────────────────────────────────────────────────────────────────
# no_launch 파라미터 (UT-NL1 ~ UT-NL3)
# ──────────────────────────────────────────────────────────────────────────────

def test_nl1_no_launch_true_skips_ensure_apps_running(mock_layout_deps):
    """UT-NL1: no_launch=True → ensure_apps_running 미호출."""
    import sys
    from unittest.mock import patch
    ensure_mock = sys.modules["src.launcher"].ensure_apps_running

    with patch("time.sleep"):
        from src.restore import restore_layout
        restore_layout({"name": "t", "windows": [], "monitors": []}, no_launch=True)

    ensure_mock.assert_not_called()


def test_nl2_no_launch_false_calls_ensure_apps_running(mock_layout_deps):
    """UT-NL2: no_launch=False(기본) → ensure_apps_running 1회 호출."""
    import sys
    from unittest.mock import patch
    ensure_mock = sys.modules["src.launcher"].ensure_apps_running

    with patch("time.sleep"):
        from src.restore import restore_layout
        restore_layout({"name": "t", "windows": [], "monitors": []}, no_launch=False)

    ensure_mock.assert_called_once()


def test_nl3_no_launch_true_rescans_windows_twice(mock_layout_deps):
    """UT-NL3: no_launch=True여도 running_windows=None이면 list_current_windows 2회 스캔."""
    import sys
    scan_mock = sys.modules["src.capture"].list_current_windows

    from src.restore import restore_layout
    restore_layout({"name": "t", "windows": [], "monitors": []}, no_launch=True)

    assert scan_mock.call_count == 2
```

- [ ] **Step 1-2: 테스트가 실패하는지 확인**

```
pytest tests/test_restore_matching.py::test_nl1_no_launch_true_skips_ensure_apps_running tests/test_restore_matching.py::test_nl2_no_launch_false_calls_ensure_apps_running tests/test_restore_matching.py::test_nl3_no_launch_true_rescans_windows_twice -v
```

Expected: 3개 모두 `FAILED` — `restore_layout() got an unexpected keyword argument 'no_launch'`

---

- [ ] **Step 1-3: `src/restore.py` 구현**

**시그니처 변경 (`restore.py:170-177`):**

```python
# 변경 전
def restore_layout(
    layout: dict,
    running_windows: list[dict] = None,
    monitors_current: list[dict] = None,
    stabilize_ms: int = 1500,
    post_settle_ms: int = 2000,
    post_launch_settle_ms: int = 0,
) -> dict:

# 변경 후
def restore_layout(
    layout: dict,
    running_windows: list[dict] = None,
    no_launch: bool = False,
    monitors_current: list[dict] = None,
    stabilize_ms: int = 1500,
    post_settle_ms: int = 2000,
    post_launch_settle_ms: int = 0,
) -> dict:
```

**launch 블록 변경 (`restore.py:235-243`):**

```python
# 변경 전
    launched_count = 0
    if running_windows is None:
        from src.launcher import ensure_apps_running
        from src.capture import list_current_windows
        running_windows = list_current_windows()
        launched_count = ensure_apps_running(sorted_saved)
        if stabilize_ms > 0:
            time.sleep(stabilize_ms / 1000.0)
        running_windows = list_current_windows()  # re-scan after launch

# 변경 후
    launched_count = 0
    if running_windows is None:
        from src.launcher import ensure_apps_running
        from src.capture import list_current_windows
        running_windows = list_current_windows()
        if not no_launch:
            launched_count = ensure_apps_running(sorted_saved)
            if stabilize_ms > 0:
                time.sleep(stabilize_ms / 1000.0)
        running_windows = list_current_windows()  # re-scan (no_launch 시에도 늦게 뜬 창 포착)
```

- [ ] **Step 1-4: 새 테스트 3개가 통과하는지 확인**

```
pytest tests/test_restore_matching.py::test_nl1_no_launch_true_skips_ensure_apps_running tests/test_restore_matching.py::test_nl2_no_launch_false_calls_ensure_apps_running tests/test_restore_matching.py::test_nl3_no_launch_true_rescans_windows_twice -v
```

Expected: 3개 모두 `PASSED`

- [ ] **Step 1-5: 기존 restore 테스트 회귀 없음 확인**

```
pytest tests/test_restore_matching.py -v
```

Expected: 전체 `PASSED` (기존 테스트 포함)

- [ ] **Step 1-6: 커밋**

```
git add src/restore.py tests/test_restore_matching.py
git commit -m "feat(Task-12): restore_layout에 no_launch 파라미터 추가 — 스캔은 하되 앱 실행 건너뜀"
```

---

## Task 2: `rollback.py` — `enabled` 체크 + `no_launch` 단일화

**근거:**
1. `enabled=False`여도 `rollback.py`가 실행되는 문제 수정 (`sys.exit(0)` 추가).
2. fast/full 분기를 `no_launch` 파라미터로 단순화해 사전 스캔(`running_windows=[]`) 전달 제거.

**Files:**
- Modify: `cli/rollback.py:54-94`
- Test: `tests/test_rollback_modes.py`, `tests/integration/test_rollback_fast_speed.py`

---

- [ ] **Step 2-1: 기존 테스트 3개에 `"enabled": True` 추가**

`tests/test_rollback_modes.py`에서 `src.storage.load_config`를 패치하는 기존 3개 테스트를 수정한다.  
(enabled 체크를 추가하면 `enabled` 키가 없거나 False이면 즉시 종료되므로 기존 테스트가 실패함.)

```python
# test_rollback_fast_mode_skips_ensure_apps_running — 변경 부분만 표시
monkeypatch.setattr("src.storage.load_config", lambda: {
    "auto_rollback": {"layout_name": "L1", "mode": "fast", "enabled": True},  # enabled 추가
})

# test_rollback_full_mode_calls_ensure_apps_running
monkeypatch.setattr("src.storage.load_config", lambda: {
    "auto_rollback": {"layout_name": "L1", "mode": "full", "enabled": True},  # enabled 추가
})

# test_rollback_calls_sys_exit_zero_on_completion
monkeypatch.setattr("src.storage.load_config", lambda: {
    "auto_rollback": {"layout_name": "L1", "mode": "fast", "enabled": True},  # enabled 추가
})
```

`tests/integration/test_rollback_fast_speed.py`에서도 동일하게 수정한다:

```python
monkeypatch.setattr("src.storage.load_config", lambda: {
    "auto_rollback": {"layout_name": "L1", "mode": "fast", "enabled": True},  # enabled 추가
})
```

- [ ] **Step 2-2: 신규 테스트 4개 작성**

`tests/test_rollback_modes.py` 파일 끝에 추가:

```python
# ──────────────────────────────────────────────────────────────────────────────
# Task-12: enabled 체크 + no_launch 전달 검증 (UT-RB1 ~ UT-RB4)
# ──────────────────────────────────────────────────────────────────────────────

def test_rb1_rollback_exits_cleanly_when_disabled(monkeypatch, tmp_path):
    """UT-RB1: enabled=False → sys.exit(0) 즉시 종료 (복구 미실행)."""
    _stub_win32(monkeypatch)
    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "fast", "enabled": False},
    })
    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])

    with pytest.raises(SystemExit) as exc:
        rollback.main()
    assert exc.value.code == 0


def test_rb2_rollback_proceeds_when_enabled(monkeypatch, tmp_path):
    """UT-RB2: enabled=True → 복구 실행 후 sys.exit(0)."""
    _stub_win32(monkeypatch)
    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "fast", "enabled": True},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: _layout())
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])
    monkeypatch.setattr("src.capture.list_current_windows", lambda: [])
    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])

    with pytest.raises(SystemExit) as exc:
        rollback.main()
    assert exc.value.code == 0


def test_rb3_fast_mode_passes_no_launch_true(monkeypatch, tmp_path):
    """UT-RB3: fast 모드 → restore_layout(no_launch=True, post_launch_settle_ms=0) 호출."""
    _stub_win32(monkeypatch)
    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "fast", "enabled": True},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: _layout())
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])
    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    captured = {}
    def fake_restore(layout, **kwargs):
        captured.update(kwargs)
        return {"restored": 0, "failed": 0, "total": 0, "elapsed_ms": 0}
    monkeypatch.setattr("src.restore.restore_layout", fake_restore)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])
    try:
        rollback.main()
    except SystemExit:
        pass

    assert captured.get("no_launch") is True
    assert captured.get("post_launch_settle_ms") == 0


def test_rb4_full_mode_passes_no_launch_false(monkeypatch, tmp_path):
    """UT-RB4: full 모드 → restore_layout(no_launch=False, post_launch_settle_ms=5000) 호출."""
    _stub_win32(monkeypatch)
    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "full", "enabled": True},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: _layout())
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])
    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    captured = {}
    def fake_restore(layout, **kwargs):
        captured.update(kwargs)
        return {"restored": 0, "failed": 0, "total": 0, "elapsed_ms": 0}
    monkeypatch.setattr("src.restore.restore_layout", fake_restore)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])
    try:
        rollback.main()
    except SystemExit:
        pass

    assert captured.get("no_launch") is False
    assert captured.get("post_launch_settle_ms") == 5000
```

- [ ] **Step 2-3: 테스트가 실패하는지 확인**

```
pytest tests/test_rollback_modes.py -v
```

Expected:
- 기존 3개: `enabled` 키가 없으면 기존 코드도 진행하므로 현재는 PASS(이미 Step 2-1에서 수정). 아직 enabled 체크 미구현이므로 `test_rb1`은 FAILED.
- `test_rb3`, `test_rb4`: `restore_layout`이 `no_launch`를 받지 못하므로 FAILED.

- [ ] **Step 2-4: `cli/rollback.py` 구현**

**`enabled` 체크 추가 (`rollback.py:56` 이후 — `layout_name` 읽는 줄 바로 전):**

```python
# 변경 전 (rollback.py:54-64)
    config = storage.load_config()
    rollback_cfg = config.get("auto_rollback", {})
    layout_name = args.layout or rollback_cfg.get("layout_name", "")
    mode = rollback_cfg.get("mode", "fast")
    if mode not in ("fast", "full"):
        logger.warning("rollback: unknown mode '%s', falling back to 'fast'", mode)
        mode = "fast"

    if not layout_name:
        logger.error("rollback: no layout name specified (use --layout or set config)")
        sys.exit(1)

# 변경 후
    config = storage.load_config()
    rollback_cfg = config.get("auto_rollback", {})

    if not rollback_cfg.get("enabled", False):
        logger.info("rollback: auto_rollback disabled in config — exiting")
        sys.exit(0)

    layout_name = args.layout or rollback_cfg.get("layout_name", "")
    mode = rollback_cfg.get("mode", "fast")
    if mode not in ("fast", "full"):
        logger.warning("rollback: unknown mode '%s', falling back to 'fast'", mode)
        mode = "fast"

    if not layout_name:
        logger.error("rollback: no layout name specified (use --layout or set config)")
        sys.exit(1)
```

**fast/full 분기 단순화 (`rollback.py:77-94`):**

```python
# 변경 전
    if args.no_launch or mode == "fast":
        # fast: 이미 실행 중인 창들만 즉시 재배치 — launch / settle 모두 생략
        running = capture.list_current_windows()
        logger.info("rollback: fast path — %d running windows, no app launching", len(running))
        result = restore_mod.restore_layout(
            layout,
            running_windows=running,
            monitors_current=monitors_current,
            post_settle_ms=2000,
            post_launch_settle_ms=0,
        )
    else:
        # full: 누락 앱 launch + post_launch_settle 5초
        result = restore_mod.restore_layout(
            layout,
            monitors_current=monitors_current,
            post_launch_settle_ms=5000,
        )

# 변경 후
    no_launch = args.no_launch or (mode == "fast")
    logger.info("rollback: mode=%s no_launch=%s", mode, no_launch)
    result = restore_mod.restore_layout(
        layout,
        no_launch=no_launch,
        monitors_current=monitors_current,
        post_settle_ms=2000,
        post_launch_settle_ms=0 if no_launch else 5000,
    )
```

- [ ] **Step 2-5: 모든 rollback 테스트 통과 확인**

```
pytest tests/test_rollback_modes.py tests/integration/test_rollback_fast_speed.py -v
```

Expected: 전체 `PASSED`

- [ ] **Step 2-6: 커밋**

```
git add cli/rollback.py tests/test_rollback_modes.py tests/integration/test_rollback_fast_speed.py
git commit -m "feat(Task-12): rollback.py — enabled 체크 추가 및 no_launch로 fast/full 분기 단순화"
```

---

## Task 3: `i18n.py` — 모드 문자열 추가

**Files:**
- Modify: `src/i18n.py`
- Test: `tests/test_i18n.py`

---

- [ ] **Step 3-1: 실패하는 테스트 작성**

`tests/test_i18n.py` 파일 끝에 추가:

```python
def test_mode_strings_present_in_all_languages():
    """ko/en 양쪽에 모드 관련 4개 키가 모두 존재하고 비어있지 않아야 한다."""
    from src.i18n import STRINGS
    required_keys = ("mode_fast", "mode_full", "mode_fast_desc", "mode_full_desc")
    for lang in ("ko", "en"):
        for key in required_keys:
            assert key in STRINGS[lang], f"'{key}' missing in lang='{lang}'"
            assert STRINGS[lang][key].strip(), f"'{key}' is empty in lang='{lang}'"
```

- [ ] **Step 3-2: 테스트 실패 확인**

```
pytest tests/test_i18n.py::test_mode_strings_present_in_all_languages -v
```

Expected: `FAILED` — `'mode_fast' missing in lang='ko'`

- [ ] **Step 3-3: `src/i18n.py` 구현**

`ko` 딕셔너리 (line 9 근처, `"log_module_filter_label"` 키 다음에 추가):

```python
        "log_module_filter_label": "모듈:",
        "mode_fast": "빠른 복구",
        "mode_full": "전체 복구",
        "mode_fast_desc": "이미 실행 중인 창만 재배치",
        "mode_full_desc": "없는 앱 자동 실행 후 배치",
```

`en` 딕셔너리 (`"log_module_filter_label"` 키 다음에 추가):

```python
        "log_module_filter_label": "Module:",
        "mode_fast": "Quick restore",
        "mode_full": "Full restore",
        "mode_fast_desc": "Reposition already-running windows only",
        "mode_full_desc": "Launch missing apps, then reposition",
```

- [ ] **Step 3-4: 테스트 통과 확인**

```
pytest tests/test_i18n.py -v
```

Expected: 전체 `PASSED`

- [ ] **Step 3-5: 커밋**

```
git add src/i18n.py tests/test_i18n.py
git commit -m "feat(Task-12): i18n — fast/full 모드 표시 문자열 4개 추가 (ko/en)"
```

---

## Task 4: `gui.py` — 모드 Radio 버튼 + 컨트롤 잠금

**변경 내용 요약:**
1. `_build_ui`: AR 행 아래에 모드 Radio 행 추가, `_delay_entry` 속성 저장
2. `_on_mode_change` 메서드 추가 (Radio 클릭 시 설명 Label 갱신)
3. `_apply_ar_toggle_style`: layout combo·mode radio·delay entry 잠금/해제 추가
4. `_on_ar_toggle`: config에 `mode` 저장 추가
5. `_refresh_layouts`: config에서 `mode` 복원 추가

**Files:**
- Modify: `src/gui.py`
- Create: `tests/test_gui_mode_selector.py`

---

- [ ] **Step 4-1: 실패하는 GUI 테스트 파일 생성**

`tests/test_gui_mode_selector.py` 신규 생성:

```python
"""Task-12: GUI 모드 선택 및 활성화 잠금 테스트."""
import pytest

tk = pytest.importorskip("tkinter")


def _make_app(monkeypatch, mode="fast", enabled=False, layouts=None):
    """테스트용 WinLayoutSaverApp 생성 헬퍼."""
    if layouts is None:
        layouts = ["Screen1"]
    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {
            "enabled": enabled,
            "layout_name": layouts[0] if layouts else "",
            "mode": mode,
            "startup_delay_seconds": 10,
        },
        "ui": {"language": "ko"},
    })
    monkeypatch.setattr("src.storage.list_layouts", lambda: layouts)
    monkeypatch.setattr("src.storage.save_config", lambda _: None)
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])

    from src.gui import WinLayoutSaverApp
    try:
        return WinLayoutSaverApp()
    except tk.TclError:
        pytest.skip("display unavailable")


# ──────────────────────────────────────────────────────────────────────────────
# 모드 Radio 버튼 존재 및 기본값 (UT-GUI1 ~ UT-GUI2)
# ──────────────────────────────────────────────────────────────────────────────

def test_gui1_mode_radio_defaults_to_fast(monkeypatch):
    """UT-GUI1: 설정에 mode='fast'이면 fast Radio가 선택된 상태로 초기화된다."""
    app = _make_app(monkeypatch, mode="fast")
    try:
        assert hasattr(app, "_ar_mode_var"), "_ar_mode_var 속성 없음"
        assert app._ar_mode_var.get() == "fast"
    finally:
        app.destroy()


def test_gui2_mode_radio_restores_full_from_config(monkeypatch):
    """UT-GUI2: 설정에 mode='full'이면 full Radio가 선택된 상태로 초기화된다."""
    app = _make_app(monkeypatch, mode="full")
    try:
        assert app._ar_mode_var.get() == "full"
    finally:
        app.destroy()


# ──────────────────────────────────────────────────────────────────────────────
# 설명 Label 갱신 (UT-GUI3)
# ──────────────────────────────────────────────────────────────────────────────

def test_gui3_mode_desc_updates_on_mode_change(monkeypatch):
    """UT-GUI3: _on_mode_change() 호출 시 _mode_desc_var가 선택 모드에 맞게 바뀐다."""
    app = _make_app(monkeypatch, mode="fast")
    try:
        # fast → 설명이 fast_desc 문자열 포함
        app._ar_mode_var.set("fast")
        app._on_mode_change()
        fast_desc = app._mode_desc_var.get()
        assert fast_desc  # 비어있지 않아야 함

        # full로 변경
        app._ar_mode_var.set("full")
        app._on_mode_change()
        full_desc = app._mode_desc_var.get()
        assert full_desc
        assert full_desc != fast_desc  # fast와 full 설명이 달라야 함
    finally:
        app.destroy()


# ──────────────────────────────────────────────────────────────────────────────
# 활성화 시 컨트롤 잠금 (UT-GUI4 ~ UT-GUI6)
# ──────────────────────────────────────────────────────────────────────────────

def test_gui4_delay_entry_locked_when_enabled(monkeypatch):
    """UT-GUI4: _apply_ar_toggle_style(True) 시 _delay_entry state='disabled'."""
    app = _make_app(monkeypatch, enabled=False)
    try:
        app._apply_ar_toggle_style(True)
        assert app._delay_entry.cget("state") == "disabled"

        app._apply_ar_toggle_style(False)
        assert app._delay_entry.cget("state") == "normal"
    finally:
        app.destroy()


def test_gui5_mode_radios_locked_when_enabled(monkeypatch):
    """UT-GUI5: _apply_ar_toggle_style(True) 시 두 Radio 버튼 state='disabled'."""
    app = _make_app(monkeypatch, enabled=False)
    try:
        app._apply_ar_toggle_style(True)
        assert app._ar_mode_fast_rb.cget("state") == "disabled"
        assert app._ar_mode_full_rb.cget("state") == "disabled"

        app._apply_ar_toggle_style(False)
        assert app._ar_mode_fast_rb.cget("state") == "normal"
        assert app._ar_mode_full_rb.cget("state") == "normal"
    finally:
        app.destroy()


def test_gui6_layout_combo_locked_when_enabled(monkeypatch):
    """UT-GUI6: _apply_ar_toggle_style(True) 시 _ar_combo state='disabled'."""
    app = _make_app(monkeypatch, enabled=False)
    try:
        app._apply_ar_toggle_style(True)
        assert app._ar_combo.cget("state") == "disabled"

        app._apply_ar_toggle_style(False)
        assert app._ar_combo.cget("state") == "readonly"
    finally:
        app.destroy()


# ──────────────────────────────────────────────────────────────────────────────
# _on_ar_toggle에서 mode 저장 (UT-GUI7)
# ──────────────────────────────────────────────────────────────────────────────

def test_gui7_on_ar_toggle_saves_mode_to_config(monkeypatch):
    """UT-GUI7: 활성화 토글 시 현재 선택된 mode가 config에 저장된다."""
    saved = {}
    monkeypatch.setattr("src.storage.save_config", lambda cfg: saved.update(cfg))
    monkeypatch.setattr("src.scheduler.register", lambda **kw: True)
    monkeypatch.setattr("src.scheduler.unregister", lambda: True)

    app = _make_app(monkeypatch, mode="fast", enabled=False)
    try:
        # full로 전환한 뒤 활성화
        app._ar_mode_var.set("full")
        app._on_ar_toggle()

        assert saved.get("auto_rollback", {}).get("mode") == "full"
    finally:
        app.destroy()
```

- [ ] **Step 4-2: 테스트 실패 확인**

```
pytest tests/test_gui_mode_selector.py -v
```

Expected: 7개 모두 `FAILED` — `has no attribute '_ar_mode_var'` 등

---

- [ ] **Step 4-3: `src/gui.py` — `_build_ui` 수정**

**`_delay_entry` 저장 (`gui.py:78-79`):**

```python
# 변경 전
        self._delay_var = tk.StringVar(value="10")
        tk.Entry(ar_frame, textvariable=self._delay_var, width=5).pack(side=tk.LEFT)

# 변경 후
        self._delay_var = tk.StringVar(value="10")
        self._delay_entry = tk.Entry(ar_frame, textvariable=self._delay_var, width=5)
        self._delay_entry.pack(side=tk.LEFT)
```

**모드 Radio 행 추가 (`gui.py:79` — delay Entry 팩 이후, status bar 이전에 삽입):**

AR 행(`ar_frame`) 블록이 끝난 직후, status bar Label 생성 전에 다음을 삽입한다:

```python
        # Mode row
        mode_row = tk.Frame(self, pady=2)
        mode_row.pack(fill=tk.X, padx=8)
        self._ar_mode_var = tk.StringVar(value="fast")
        self._ar_mode_fast_rb = tk.Radiobutton(
            mode_row, text=t("mode_fast"),
            variable=self._ar_mode_var, value="fast",
            command=self._on_mode_change,
        )
        self._ar_mode_fast_rb.pack(side=tk.LEFT)
        self._ar_mode_full_rb = tk.Radiobutton(
            mode_row, text=t("mode_full"),
            variable=self._ar_mode_var, value="full",
            command=self._on_mode_change,
        )
        self._ar_mode_full_rb.pack(side=tk.LEFT, padx=(8, 0))
        self._mode_desc_var = tk.StringVar()
        tk.Label(
            mode_row, textvariable=self._mode_desc_var,
            fg="#555", font=("Consolas", 9),
        ).pack(side=tk.LEFT, padx=(16, 0))
```

- [ ] **Step 4-4: `src/gui.py` — `_on_mode_change` 메서드 추가**

`_apply_ar_toggle_style` 메서드 **바로 앞**에 추가:

```python
    def _on_mode_change(self):
        """모드 Radio 버튼 클릭 시 설명 Label을 갱신한다."""
        mode = self._ar_mode_var.get()
        self._mode_desc_var.set(t("mode_fast_desc" if mode == "fast" else "mode_full_desc"))
```

- [ ] **Step 4-5: `src/gui.py` — `_apply_ar_toggle_style` 수정**

```python
# 변경 전 (gui.py:313-330)
    def _apply_ar_toggle_style(self, enabled: bool):
        """부팅 자동 복구 활성화 상태에 따라 토글 버튼의 텍스트/색상을 갱신."""
        if enabled:
            self._ar_toggle_btn.config(
                text=t("enabled_status"),
                bg="#2E7D32",
                fg="white",
                activebackground="#388E3C",
                activeforeground="white",
            )
        else:
            self._ar_toggle_btn.config(
                text=t("enable_btn"),
                bg="SystemButtonFace",
                fg="SystemButtonText",
                activebackground="SystemButtonFace",
                activeforeground="SystemButtonText",
            )

# 변경 후
    def _apply_ar_toggle_style(self, enabled: bool):
        """부팅 자동 복구 활성화 상태에 따라 토글 버튼 및 관련 컨트롤 잠금/해제."""
        widget_state = "disabled" if enabled else "normal"
        combo_state  = "disabled" if enabled else "readonly"
        self._ar_combo.config(state=combo_state)
        self._ar_mode_fast_rb.config(state=widget_state)
        self._ar_mode_full_rb.config(state=widget_state)
        self._delay_entry.config(state=widget_state)

        if enabled:
            self._ar_toggle_btn.config(
                text=t("enabled_status"),
                bg="#2E7D32",
                fg="white",
                activebackground="#388E3C",
                activeforeground="white",
            )
        else:
            self._ar_toggle_btn.config(
                text=t("enable_btn"),
                bg="SystemButtonFace",
                fg="SystemButtonText",
                activebackground="SystemButtonFace",
                activeforeground="SystemButtonText",
            )
```

- [ ] **Step 4-6: `src/gui.py` — `_on_ar_toggle`에 mode 저장 추가**

`ar["layout_name"] = self._ar_layout_var.get()` 다음 줄에 추가:

```python
# 변경 전 (gui.py:298-300)
        ar["enabled"] = new_enabled
        ar["layout_name"] = self._ar_layout_var.get()
        try:

# 변경 후
        ar["enabled"] = new_enabled
        ar["layout_name"] = self._ar_layout_var.get()
        ar["mode"] = self._ar_mode_var.get()
        try:
```

- [ ] **Step 4-7: `src/gui.py` — `_refresh_layouts`에 mode 복원 추가**

`_apply_ar_toggle_style(ar_enabled)` 호출과 `delay = config...` 라인 사이에 추가:

```python
# 변경 전 (gui.py:169-172)
        self._apply_ar_toggle_style(ar_enabled)

        delay = config.get("auto_rollback", {}).get("startup_delay_seconds", 10)
        self._delay_var.set(str(delay))

# 변경 후
        self._apply_ar_toggle_style(ar_enabled)

        mode = config.get("auto_rollback", {}).get("mode", "fast")
        self._ar_mode_var.set(mode)
        self._on_mode_change()

        delay = config.get("auto_rollback", {}).get("startup_delay_seconds", 10)
        self._delay_var.set(str(delay))
```

- [ ] **Step 4-8: GUI 테스트 통과 확인**

```
pytest tests/test_gui_mode_selector.py -v
```

Expected: 7개 모두 `PASSED`

- [ ] **Step 4-9: 기존 GUI 테스트 회귀 없음 확인**

```
pytest tests/test_gui_ar_indicator.py tests/test_gui_version_label.py tests/test_gui_log_filter.py -v
```

Expected: 전체 `PASSED`

- [ ] **Step 4-10: 커밋**

```
git add src/gui.py tests/test_gui_mode_selector.py
git commit -m "feat(Task-12): GUI — fast/full 모드 Radio 추가, 활성화 시 delay·mode·layout 잠금"
```

---

## Task 5: 전체 회귀 검증

- [ ] **Step 5-1: 전체 테스트 스위트 실행**

```
pytest --tb=short -q
```

Expected: 모든 테스트 `PASSED`, `0 failed`

실패 시 오류 메시지를 확인하고 해당 Task로 돌아가 수정한다.

- [ ] **Step 5-2: 최종 커밋 (필요 시)**

테스트 실패로 인한 수정이 있었을 경우:

```
git add -p
git commit -m "fix(Task-12): 전체 회귀 테스트 통과"
```

---

## 체크포인트 요약 (중단 후 재개 시 참조)

| Task | 커밋 메시지 접두사 | 완료 조건 |
|------|------------------|----------|
| 1 | `feat(Task-12): restore_layout에 no_launch` | `pytest tests/test_restore_matching.py` ALL PASS |
| 2 | `feat(Task-12): rollback.py — enabled 체크` | `pytest tests/test_rollback_modes.py tests/integration/test_rollback_fast_speed.py` ALL PASS |
| 3 | `feat(Task-12): i18n — fast/full 모드` | `pytest tests/test_i18n.py` ALL PASS |
| 4 | `feat(Task-12): GUI — fast/full 모드 Radio` | `pytest tests/test_gui_mode_selector.py tests/test_gui_ar_indicator.py` ALL PASS |
| 5 | (회귀) | `pytest --tb=short -q` 전체 PASS |

재개 시 `git log --oneline -5`로 마지막 완료 커밋을 확인하고 해당 Task의 다음 Step부터 이어서 진행한다.

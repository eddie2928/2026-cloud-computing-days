# Task-11: 부팅 복구 속도 개선 + GUI 활성화 표시 + 버전 라벨 + 콘솔창 자동 종료

> 본 플랜은 중간에 중단되어도 체크박스(`- [ ]` / `- [x]`) 진척도를 보고 동일한 단계부터 재개할 수 있도록 작성되었다.

**Goal:**
1. 부팅 시 자동 복구가 활성화되어 있으면 GUI에 "활성화됨"을 초록색 배경 버튼으로 표시한다.
2. GUI 좌측 하단에 버전 라벨 `v1.12.0`을 표시한다.
3. 부팅시 복구가 1분 이상 걸리는 문제를 해결해 5초 이내(앱이 이미 실행 중인 경우)로 복구한다 — `fast` / `full` 모드를 config로 선택 가능, 기본 `fast`.
4. 부팅 시 rollback Task가 띄우던 콘솔창을 보이지 않도록(또는 작업 완료 후 즉시 종료되도록) 한다.

**Architecture:**
- `src/version.py` 신설 — 단일 진실 공급원으로 `__version__ = "1.12.0"`.
- `src/gui.py` — 버전 라벨, 활성화 상태 버튼 색/텍스트 변경. 신규 i18n key 추가.
- `cli/rollback.py` — config의 `auto_rollback.mode` 읽어 `fast`/`full` 분기.
  - `fast`: `ensure_apps_running` 호출 생략, 이미 실행 중인 창만 즉시 재배치 → `restore_layout(layout, running_windows=<현재 창 리스트>)`.
  - `full`: 현행 동작 유지(앱 실행 + post_launch_settle).
- `src/scheduler.py` — Windows Task Scheduler에 등록 시 콘솔창이 나타나지 않도록 `pyw.exe`(없으면 pythonw.exe) 우선 + `-Hidden` 설정.
- `cli/rollback.py` 종료부 — 복구 완료 후 명시적 `sys.exit(0)`. (Task Scheduler에서 떠 있는 콘솔창 잔존을 방지하는 안전장치.)

**Tech Stack:** Python 3.13, tkinter, pywin32, psutil, pytest, Windows Task Scheduler (PowerShell `Register-ScheduledTask`).

---

## 분석 결과 요약 (수정 전 진단)

### 부팅 복구 지연 근본 원인
**`src/launcher.py:169`** — `ensure_apps_running` 내부 `_wait_for_window_count(rep["exe_path"], target_count, timeout_seconds, poll_ms)`의 기본 `timeout_seconds=60.0`. 부팅 직후에는 사용자 앱들이 아직 실행되지 않았기 때문에 `deficit > 0`인 exe마다 launch + 최대 60초 대기를 반복한다. 5개 앱이 누락되어 있고 각 앱이 30초 후 등장한다면 ≥150초가 걸린다.
**추가 지연:** `restore.py:270` `post_launch_settle_ms=5000` — `launched_count > 0`일 때 5초 추가 대기.

수동 복구가 빠른 이유: 사용자가 GUI를 사용할 때는 모든 앱이 이미 실행 중이라 `deficit=0` → `ensure_apps_running` 즉시 종료 + `launched_count=0`이라 post_launch_settle도 건너뛴다. 약 stabilize 1.5s + post_settle 2s = 3.5s.

### 콘솔창이 뜨는 원인
`src/scheduler.py:78-84` — `pythonw.exe`를 우선 시도하지만, Microsoft Store Python 등에서 `_find_executable_for_scheduler`가 `py.exe`(콘솔 아이콘)로 폴백한다. `py.exe`는 콘솔창이 동반된다. `pyw.exe`(no-console 변형)가 시스템에 있으면 사용해야 한다. 또한 `New-ScheduledTaskSettingsSet -Hidden` 설정으로 작업 자체를 hidden 처리할 수 있다.

### GUI 활성화 표시 현재 상태
`src/gui.py:68-69, 162` — 버튼 텍스트가 i18n의 `enable_btn`("활성화") / `disable_btn`("비활성화")로만 토글된다. 색상/스타일 변화 없음.

---

## 진척도 트래킹 — Todo List

각 Task의 모든 step이 끝나면 그 Task의 큰 항목에 `[x]`를 마크해 재개 시점을 빨리 식별할 수 있다.

- [x] **Task 1**: 버전 상수 모듈 신설
- [x] **Task 2**: GUI 좌측 하단에 `v1.12.0` 라벨 표시
- [x] **Task 3**: i18n에 활성화 상태 문자열 추가
- [x] **Task 4**: 부팅 자동 복구 활성화 시 GUI 버튼이 "활성화됨"(초록 배경)으로 표시
- [x] **Task 5**: config 스키마 확장 — `auto_rollback.mode` (`"fast"`/`"full"`, 기본 `"fast"`)
- [x] **Task 6**: `cli/rollback.py`에 `fast`/`full` 모드 분기 구현
- [x] **Task 7**: `_find_executable_for_scheduler`가 `pyw.exe`를 가장 먼저 선호하도록 변경
- [x] **Task 8**: `Register-ScheduledTask` 설정에 `-Hidden` 추가
- [x] **Task 9**: rollback 종료부에 `sys.exit(0)` 안전장치 추가
- [x] **Task 10**: 통합 테스트 — fast 모드에서 ensure_apps_running 미호출 + 5초 이내 복구 검증
- [ ] **Task 11**: 수동 회귀 테스트 (체크리스트 실행)

---

## Task 1: 버전 상수 모듈 신설

**Files:**
- Create: `src/version.py`

- [x] **Step 1.1: `src/version.py` 작성**

```python
__version__ = "1.12.0"
```

- [x] **Step 1.2: 임포트 동작 검증**

Run:
```bash
python -c "from src.version import __version__; print(__version__)"
```
Expected stdout: `1.12.0`

- [x] **Step 1.3: 커밋**

```bash
git add src/version.py
git commit -m "feat(Task-11): add version constant module (v1.12.0)"
```

---

## Task 2: GUI 좌측 하단에 버전 라벨 표시

**Files:**
- Modify: `src/gui.py:1-17` (import 추가)
- Modify: `src/gui.py:_build_ui` (라벨 추가)
- Test: `tests/test_gui_version_label.py` (신규)

**구현 위치 결정:** `_build_ui` 마지막에 root에 직접 `tk.Label`을 추가하면, 기존 `paned`(`expand=True`) 위에 자리한 다른 위젯들 아래로 밀린다. 따라서 footer frame을 만들어 `paned` 다음에 `pack(side=tk.BOTTOM, fill=tk.X)`로 추가하지 말고, **root에 paned가 expand=True로 추가되기 전에** footer를 먼저 `pack(side=tk.BOTTOM, fill=tk.X)`로 추가해야 한다(tk.Pack은 footer가 먼저 등록되어 있어야 하단 고정이 보장됨).

- [x] **Step 2.1: 실패 테스트 작성 — `tests/test_gui_version_label.py`**

```python
def test_gui_imports_version():
    """GUI 모듈이 src.version에서 __version__을 가져오는지 확인."""
    import importlib
    import src.gui as gui
    importlib.reload(gui)
    assert hasattr(gui, "__version__") or "version" in dir(gui)
    # 정확한 검증: gui.py 소스 안에 'from src.version import __version__'이 있어야 함
    from pathlib import Path
    src_text = Path(gui.__file__).read_text(encoding="utf-8")
    assert "from src.version import __version__" in src_text
    assert "v" in src_text and "__version__" in src_text  # 라벨에서 사용 흔적
```

- [x] **Step 2.2: 테스트 실패 확인**

Run: `pytest tests/test_gui_version_label.py -v`
Expected: FAIL (`from src.version import __version__` 미존재).

- [x] **Step 2.3: `src/gui.py` 수정 — import 추가**

위치: `from src.paths import LOGS_DIR` 줄 바로 아래(현재 line 15).

```python
from src.version import __version__
```

- [x] **Step 2.4: `src/gui.py` 수정 — `_build_ui` 시작부에 footer 추가**

위치: `_build_ui` 메서드 첫 줄(현재 line 44 `# Monitor strip` 바로 위)에 다음 코드 삽입.

```python
        # Footer (version label) — pack BOTTOM 먼저 호출해야 항상 하단에 고정됨
        footer = tk.Frame(self)
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(footer, text=f"v{__version__}", anchor="w",
                 fg="#888", font=("Consolas", 9)).pack(side=tk.LEFT)
```

- [x] **Step 2.5: 테스트 통과 확인**

Run: `pytest tests/test_gui_version_label.py -v`
Expected: PASS.

- [x] **Step 2.6: 수동 GUI 확인**

Run: `python main.py`
Expected: 창 좌측 하단에 회색 텍스트 `v1.12.0`이 보인다. (확인 후 GUI 종료.)

- [x] **Step 2.7: 커밋**

```bash
git add src/gui.py tests/test_gui_version_label.py
git commit -m "feat(Task-11): show app version in GUI footer"
```

---

## Task 3: i18n에 활성화 상태 문자열 추가

**Files:**
- Modify: `src/i18n.py:1-58` (STRINGS 딕셔너리 양쪽 언어에 키 추가)

- [x] **Step 3.1: ko/en 양쪽에 `enabled_status` 키 추가**

`src/i18n.py`의 `"ko"` 사전 안 `"disable_btn": "비활성화"` 다음 줄에 추가:

```python
        "enabled_status": "활성화됨",
```

`"en"` 사전 안 `"disable_btn": "Disable"` 다음 줄에 추가:

```python
        "enabled_status": "Enabled",
```

- [x] **Step 3.2: 검증**

Run:
```bash
python -c "from src.i18n import t, set_language; set_language('ko'); print(t('enabled_status')); set_language('en'); print(t('enabled_status'))"
```
Expected stdout:
```
활성화됨
Enabled
```

- [x] **Step 3.3: 커밋**

```bash
git add src/i18n.py
git commit -m "feat(Task-11): add 'enabled_status' i18n string for boot-rollback indicator"
```

---

## Task 4: 부팅 자동 복구 활성화 시 GUI 버튼을 "활성화됨" + 초록 배경으로 표시

**Files:**
- Modify: `src/gui.py:_refresh_layouts` (현재 line 162 토글 처리부)
- Modify: `src/gui.py:_on_ar_toggle` (현재 line 287-304 토글 직후 처리부)
- Test: `tests/test_gui_log_filter.py`와 같은 단위 테스트 패턴으로 `tests/test_gui_ar_indicator.py` 신규 작성 (외부 위젯/디스플레이 없이 헬퍼 함수 검증)

**설계 결정:** 버튼 텍스트와 배경색을 동시에 바꾸는 작은 헬퍼 `_apply_ar_toggle_style(enabled: bool)`를 GUI 내부에 추가하여 `_refresh_layouts`/`_on_ar_toggle` 양쪽에서 호출. 이렇게 하면 단위 테스트가 헬퍼만 검증하면 되어 tk Mainloop 의존을 피할 수 있다 — 단, 버튼 자체에 대해서는 `Tk()`를 만들어야 하므로 conftest의 `xvfb`/`headless` 환경에서는 GUI 테스트가 스킵될 수 있다.

색상 결정:
- 활성: `bg="#2E7D32"`(어두운 초록), `fg="white"`, `activebackground="#388E3C"`.
- 비활성: 시스템 기본(아무 인자도 주지 않음 → `bg=` 인자 미설정으로 복원 위해 `tk.Button`의 기본값 `"SystemButtonFace"` 명시적 적용).

- [x] **Step 4.1: 실패 테스트 작성 — `tests/test_gui_ar_indicator.py`**

```python
import os
import pytest

# tk가 없는 CI 환경에서는 skip
tk = pytest.importorskip("tkinter")


def test_apply_ar_toggle_style_enabled_changes_text_and_bg():
    from src.gui import WinLayoutSaverApp
    # Tk root 없이 메서드 호출이 어려우므로 실제 인스턴스 생성
    try:
        app = WinLayoutSaverApp()
    except tk.TclError:
        pytest.skip("display unavailable")
    try:
        app._apply_ar_toggle_style(True)
        text = app._ar_toggle_btn.cget("text")
        bg = str(app._ar_toggle_btn.cget("bg")).lower()
        assert text == "활성화됨" or text == "Enabled"
        assert bg in ("#2e7d32", "#2E7D32".lower())

        app._apply_ar_toggle_style(False)
        text2 = app._ar_toggle_btn.cget("text")
        assert text2 in ("활성화", "Enable")
    finally:
        app.destroy()
```

- [x] **Step 4.2: 테스트 실패 확인**

Run: `pytest tests/test_gui_ar_indicator.py -v`
Expected: FAIL (`_apply_ar_toggle_style` 미존재).

- [x] **Step 4.3: `src/gui.py`에 헬퍼 추가**

위치: `_on_ar_toggle` 메서드 바로 아래(현재 line 305 `# ── Log panel ───` 위에) 다음 메서드 삽입.

```python
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
```

- [x] **Step 4.4: `_refresh_layouts` 마지막 줄(line 162) 교체**

기존:
```python
        self._ar_toggle_btn.config(text=t("disable_btn") if ar_enabled else t("enable_btn"))
```
교체:
```python
        self._apply_ar_toggle_style(ar_enabled)
```

- [x] **Step 4.5: `_on_ar_toggle`의 토글 직후 줄(line 298) 교체**

기존:
```python
        self._ar_toggle_btn.config(text=t("disable_btn") if new_enabled else t("enable_btn"))
```
교체:
```python
        self._apply_ar_toggle_style(new_enabled)
```

- [x] **Step 4.6: 테스트 통과 확인**

Run: `pytest tests/test_gui_ar_indicator.py -v`
Expected: PASS (또는 display 없으면 SKIP — Windows에서 실행 시 PASS 필수).

- [x] **Step 4.7: 수동 GUI 확인**

Run: `python main.py`
1. 활성화 버튼 클릭 → 버튼 텍스트가 `활성화됨`, 배경이 초록색이 되는지 확인.
2. 한 번 더 클릭(현재 활성 상태이지만 동일 버튼이므로 토글) → 버튼이 `활성화` 텍스트, 기본 회색으로 복원되는지 확인.
3. GUI 재시작 후 — 직전 상태가 활성화면 시작 시점부터 초록색으로 보이는지 확인.

- [x] **Step 4.8: 커밋**

```bash
git add src/gui.py tests/test_gui_ar_indicator.py
git commit -m "feat(Task-11): show '활성화됨' green indicator when boot auto-rollback is enabled"
```

---

## Task 5: config 스키마 확장 — `auto_rollback.mode`

**Files:**
- Modify: `src/storage.py:_default_config` (현재 line 77-87)
- Test: `tests/test_storage.py`

**기본값:** `"fast"`. 호환성: 기존 사용자 config 파일에 키가 없으면 호출부에서 `.get("mode", "fast")`로 처리.

- [x] **Step 5.1: 실패 테스트 추가 — `tests/test_storage.py` 끝에 append**

```python
def test_default_config_has_auto_rollback_mode_fast():
    from src.storage import _default_config
    cfg = _default_config()
    assert cfg["auto_rollback"]["mode"] == "fast"
```

- [x] **Step 5.2: 테스트 실패 확인**

Run: `pytest tests/test_storage.py::test_default_config_has_auto_rollback_mode_fast -v`
Expected: FAIL (KeyError 또는 assertion).

- [x] **Step 5.3: `_default_config` 수정**

`src/storage.py:81` (현재 `"layout_name": ""` 줄) 다음 줄에 추가:

```python
            "mode": "fast",
```

- [x] **Step 5.4: 테스트 통과 확인**

Run: `pytest tests/test_storage.py::test_default_config_has_auto_rollback_mode_fast -v`
Expected: PASS.

- [x] **Step 5.5: 커밋**

```bash
git add src/storage.py tests/test_storage.py
git commit -m "feat(Task-11): add auto_rollback.mode config key (default 'fast')"
```

---

## Task 6: `cli/rollback.py`에 fast/full 모드 분기 구현

**Files:**
- Modify: `cli/rollback.py:54-83` (config 읽기 및 restore_layout 호출부)
- Test: `tests/test_rollback_modes.py` (신규)

**의도:**
- `mode == "fast"`: 현재 `list_current_windows()` 결과를 직접 `restore_layout`에 넘겨 `ensure_apps_running` + `stabilize_ms` + `post_launch_settle_ms`를 모두 우회. 5초 이내 복구.
- `mode == "full"`: 현행 동작과 동일.

`restore_layout`은 `running_windows`가 None이 아니면 launch 경로를 타지 않으므로(restore.py:234), `running_windows=current` + `post_launch_settle_ms=0`만 넘기면 fast 경로가 자동으로 잡힌다.

- [x] **Step 6.1: 실패 테스트 작성 — `tests/test_rollback_modes.py`**

```python
"""Task-11: rollback fast/full mode 분기 검증."""
import sys
import types
from unittest.mock import patch, MagicMock


def _stub_win32(monkeypatch):
    """rollback.py가 의존하는 win32 관련 모듈을 가짜로 등록."""
    win32gui = types.ModuleType("win32gui")
    win32con = types.ModuleType("win32con")
    win32con.SW_SHOWNORMAL = 1
    win32con.SW_SHOWMINIMIZED = 2
    win32con.SW_SHOWMAXIMIZED = 3
    win32gui.SetWindowPlacement = lambda *a: None
    win32gui.SetWindowPos = lambda *a: None
    win32gui.GetWindowPlacement = lambda *a: (0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600))
    win32gui.GetWindowRect = lambda *a: (0, 0, 800, 600)
    sys.modules["win32gui"] = win32gui
    sys.modules["win32con"] = win32con


def _layout():
    return {
        "name": "L1",
        "windows": [{
            "exe_path": "C:\\app.exe",
            "title_snapshot": "App - foo",
            "title_pattern": "foo$",
            "class_name": "C1",
            "placement": {"state": "normal", "normal_rect": [0, 0, 800, 600],
                          "min_pos": [-1, -1], "max_pos": [-1, -1]},
            "z_order": 0,
        }],
        "monitors": [],
    }


def test_rollback_fast_mode_skips_ensure_apps_running(monkeypatch, tmp_path):
    """mode='fast'면 ensure_apps_running이 호출되지 않아야 한다."""
    _stub_win32(monkeypatch)

    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "fast"},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: _layout())
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])
    monkeypatch.setattr("src.capture.list_current_windows", lambda: [{
        "hwnd": 0xABCD, "exe_path": "C:\\app.exe",
        "title_snapshot": "App - foo", "class_name": "C1", "is_hidden": False,
    }])

    ensure_called = {"n": 0}
    def fake_ensure(*a, **kw):
        ensure_called["n"] += 1
        return 0
    monkeypatch.setattr("src.launcher.ensure_apps_running", fake_ensure)

    # Bypass logging setup file IO
    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])
    try:
        rollback.main()
    except SystemExit:
        pass

    assert ensure_called["n"] == 0, "fast mode인데 ensure_apps_running이 호출됨"


def test_rollback_full_mode_calls_ensure_apps_running(monkeypatch, tmp_path):
    """mode='full'이면 ensure_apps_running이 호출되어야 한다(현행 동작)."""
    _stub_win32(monkeypatch)

    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "full"},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: _layout())
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])

    scan_count = {"n": 0}
    def fake_list_current():
        scan_count["n"] += 1
        return [{"hwnd": 0xABCD, "exe_path": "C:\\app.exe",
                 "title_snapshot": "App - foo", "class_name": "C1", "is_hidden": False}]
    monkeypatch.setattr("src.capture.list_current_windows", fake_list_current)

    ensure_called = {"n": 0}
    def fake_ensure(*a, **kw):
        ensure_called["n"] += 1
        return 0
    monkeypatch.setattr("src.launcher.ensure_apps_running", fake_ensure)
    monkeypatch.setattr("time.sleep", lambda *_: None)

    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])
    try:
        rollback.main()
    except SystemExit:
        pass

    assert ensure_called["n"] == 1, "full mode인데 ensure_apps_running이 호출되지 않음"
```

- [x] **Step 6.2: 테스트 실패 확인**

Run: `pytest tests/test_rollback_modes.py -v`
Expected: FAIL — 현재 rollback.py는 mode를 읽지 않으므로 fast/full 동작이 동일.

- [x] **Step 6.3: `cli/rollback.py:54-83` 교체**

기존(line 54~83):
```python
    config = storage.load_config()
    rollback_cfg = config.get("auto_rollback", {})
    layout_name = args.layout or rollback_cfg.get("layout_name", "")
    ...
    logger.info("--- phase: restore placement ---")
    if args.no_launch:
        logger.info("rollback: skipping app launch (--no-launch)")
        running = capture.list_current_windows()
        result = restore_mod.restore_layout(layout, running, monitors_current=monitors_current)
    else:
        result = restore_mod.restore_layout(
            layout,
            monitors_current=monitors_current,
            post_launch_settle_ms=5000,
        )
```

교체:
```python
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

    try:
        layout = storage.load_layout(layout_name)
    except FileNotFoundError:
        logger.error("rollback: layout '%s' not found", layout_name)
        sys.exit(1)

    from src.monitors import list_current_monitors
    monitors_current = list_current_monitors()

    logger.info("--- phase: restore placement (mode=%s) ---", mode)

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
```

(기존 `if not layout_name` ~ `monitors_current = list_current_monitors()` 블록을 위 교체본이 흡수하므로, 중복 라인이 남지 않도록 교체 범위 확인 필수.)

- [x] **Step 6.4: 테스트 통과 확인**

Run: `pytest tests/test_rollback_modes.py -v`
Expected: PASS (두 테스트 모두).

- [x] **Step 6.5: 회귀 테스트 — 기존 launcher/restore 테스트가 깨지지 않는지 확인**

Run: `pytest tests/test_launcher.py tests/test_scheduler.py tests/test_storage.py tests/test_restore_matching.py -v`
Expected: 모든 테스트 PASS.

- [x] **Step 6.6: 커밋**

```bash
git add cli/rollback.py tests/test_rollback_modes.py
git commit -m "feat(Task-11): add fast/full rollback mode (default fast — skip app launching at boot)"
```

---

## Task 7: `_find_executable_for_scheduler`가 `pyw.exe`를 가장 먼저 선호

**Files:**
- Modify: `src/scheduler.py:19-54`
- Test: `tests/test_scheduler.py::TestFindExecutableForScheduler` 확장

**근거:** 콘솔창이 뜨는 주된 원인은 `py.exe`(콘솔 변형)로의 폴백. `pyw.exe`(콘솔 없음)가 PATH에 있으면 더 우선해야 한다. 또한 비-WindowsApps 경로의 경우에도 `python.exe`가 들어왔다면 같은 디렉터리의 `pythonw.exe`를 사용한다.

- [x] **Step 7.1: 실패 테스트 추가 — `tests/test_scheduler.py`의 `TestFindExecutableForScheduler` 클래스 끝에 메서드 추가**

```python
    def test_store_path_prefers_pyw_over_py(self, monkeypatch):
        """pyw.exe와 py.exe 모두 있으면 pyw.exe를 선호."""
        import shutil as _shutil
        def which(x):
            if x == "pyw":
                return "C:\\Windows\\pyw.exe"
            if x == "py":
                return "C:\\Windows\\py.exe"
            return None
        monkeypatch.setattr(_shutil, "which", which)
        import src.scheduler as sched
        monkeypatch.setattr(sched, "glob", lambda p: [])
        from src.scheduler import _find_executable_for_scheduler
        result = _find_executable_for_scheduler(
            "C:\\Users\\u\\AppData\\Local\\Microsoft\\WindowsApps\\pythonw.exe"
        )
        assert result == "C:\\Windows\\pyw.exe"

    def test_python_exe_path_swapped_to_pythonw(self, monkeypatch, tmp_path):
        """python.exe를 받았는데 같은 폴더에 pythonw.exe가 있으면 그것을 사용."""
        py = tmp_path / "python.exe"
        pyw = tmp_path / "pythonw.exe"
        py.write_text(""); pyw.write_text("")
        from src.scheduler import _find_executable_for_scheduler
        result = _find_executable_for_scheduler(str(py))
        assert result == str(pyw)
```

- [x] **Step 7.2: 테스트 실패 확인**

Run: `pytest tests/test_scheduler.py::TestFindExecutableForScheduler -v`
Expected: 새 두 테스트 FAIL, 기존 테스트는 영향에 따라 PASS 유지.

- [x] **Step 7.3: `src/scheduler.py:_find_executable_for_scheduler` 교체**

기존(line 19~54) 함수를 다음으로 교체:

```python
def _find_executable_for_scheduler(python_exe: str) -> str:
    """
    Task Scheduler가 콘솔창 없이 실행할 수 있는 Python 실행 파일을 선택.
    우선순위:
      1. python.exe → 같은 폴더의 pythonw.exe (콘솔 없음)
      2. WindowsApps 별칭 → pyw.exe (콘솔 없음, 우선) → py.exe → Packages 실경로
      3. 위 모두 실패 시 입력값 그대로 반환 + WARNING.
    """
    import shutil
    from pathlib import Path

    # (1) python.exe 입력 → pythonw.exe 동일 폴더 매핑
    p = Path(python_exe)
    if p.name.lower() == "python.exe":
        cand = p.with_name("pythonw.exe")
        if cand.exists():
            logger.debug("scheduler: swapping python.exe → pythonw.exe (%s)", cand)
            return str(cand)

    # (2) WindowsApps 별칭 처리
    if "WindowsApps" not in str(python_exe):
        return python_exe

    # 2-a. pyw.exe (no-console) 가장 우선
    pyw = shutil.which("pyw")
    if pyw and "WindowsApps" not in pyw:
        logger.debug("scheduler: using pyw.exe launcher: %s", pyw)
        return pyw

    # 2-b. py.exe 폴백
    py = shutil.which("py")
    if py and "WindowsApps" not in py:
        logger.debug("scheduler: using py.exe launcher: %s", py)
        return py

    # 2-c. Packages 아래 실 pythonw.exe / python.exe
    localappdata = os.environ.get("LOCALAPPDATA", "")
    for pattern in [
        localappdata + "\\Packages\\PythonSoftwareFoundation.Python.*"
                     "\\LocalCache\\local-packages\\Python3*\\pythonw.exe",
        localappdata + "\\Packages\\PythonSoftwareFoundation.Python.*"
                     "\\LocalCache\\local-packages\\Python3*\\python.exe",
    ]:
        matches = sorted(glob(pattern), reverse=True)
        if matches:
            logger.debug("scheduler: using real Python from Packages: %s", matches[0])
            return matches[0]

    logger.warning(
        "scheduler: Windows Store Python alias detected in /TR (%s) — "
        "task may show console window; install pyw.exe (Python Launcher) for console-less execution",
        python_exe,
    )
    return python_exe
```

- [x] **Step 7.4: 테스트 통과 확인**

Run: `pytest tests/test_scheduler.py::TestFindExecutableForScheduler -v`
Expected: 모든 메서드 PASS.

- [x] **Step 7.5: 커밋**

```bash
git add src/scheduler.py tests/test_scheduler.py
git commit -m "feat(Task-11): prefer pyw.exe and pythonw.exe to suppress console window on boot"
```

---

## Task 8: `Register-ScheduledTask` 설정에 `-Hidden` 추가

**Files:**
- Modify: `src/scheduler.py:_build_register_ps` (line 57-68)
- Test: `tests/test_scheduler.py::TestRegister`에 신규 테스트 추가

**근거:** 별도 안전장치로 PowerShell `New-ScheduledTaskSettingsSet`에 `-Hidden` 플래그를 추가하면 작업 자체가 hidden으로 등록되어 일부 환경에서 발생하는 잔존 콘솔창이 더 효과적으로 억제된다.

- [x] **Step 8.1: 실패 테스트 추가 — `tests/test_scheduler.py::TestRegister` 클래스 끝에 추가**

```python
    def test_register_uses_hidden_setting(self):
        """Register-ScheduledTask 설정에 -Hidden이 포함되어야 한다."""
        with patch("subprocess.run", return_value=make_ok_result()) as mock_run:
            from src import scheduler
            scheduler.register(script_path="C:\\path\\rollback.py", delay_seconds=20)
            ps = _decode_ps(mock_run)
            assert "-Hidden" in ps
```

- [x] **Step 8.2: 테스트 실패 확인**

Run: `pytest tests/test_scheduler.py::TestRegister::test_register_uses_hidden_setting -v`
Expected: FAIL.

- [x] **Step 8.3: `_build_register_ps`에 `-Hidden` 추가**

기존(line 65) `$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false; ` 부분을 다음으로 교체:

```python
        f"$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false -Hidden; "
```

- [x] **Step 8.4: 테스트 통과 확인**

Run: `pytest tests/test_scheduler.py -v`
Expected: 모든 테스트 PASS.

- [x] **Step 8.5: 커밋**

```bash
git add src/scheduler.py tests/test_scheduler.py
git commit -m "feat(Task-11): register scheduled task with -Hidden to suppress console"
```

---

## Task 9: rollback 종료부에 `sys.exit(0)` 안전장치

**Files:**
- Modify: `cli/rollback.py:88-92` (현재 `logger.info("rollback: complete ...")` 다음 줄)
- Test: `tests/test_rollback_modes.py`에 추가

**근거:** `pythonw.exe`/`pyw.exe`로 실행되더라도 일부 환경에서 인터프리터가 atexit 처리 도중 멈추면 콘솔 창 잔존 가능. 명시적 `sys.exit(0)`으로 즉시 종료해 콘솔창이 즉시 닫히는 것을 보장한다.

- [x] **Step 9.1: 실패 테스트 추가 — `tests/test_rollback_modes.py` 끝에 append**

```python
def test_rollback_calls_sys_exit_zero_on_completion(monkeypatch, tmp_path):
    """정상 완료 시 sys.exit(0)이 호출되어야 한다(콘솔창 즉시 종료 보장)."""
    _stub_win32(monkeypatch)

    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "fast"},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: _layout())
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])
    monkeypatch.setattr("src.capture.list_current_windows", lambda: [])
    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])

    import pytest as _pt
    with _pt.raises(SystemExit) as exc:
        rollback.main()
    assert exc.value.code == 0
```

- [x] **Step 9.2: 테스트 실패 확인**

Run: `pytest tests/test_rollback_modes.py::test_rollback_calls_sys_exit_zero_on_completion -v`
Expected: FAIL.

- [x] **Step 9.3: `cli/rollback.py` 끝부분 수정**

기존(현재 line 85-88):
```python
    logger.info(
        "rollback: complete — restored %d/%d, failed %d, elapsed %dms",
        result["restored"], result["total"], result["failed"], result["elapsed_ms"],
    )
```
다음 줄 추가:
```python
    sys.exit(0)
```

- [x] **Step 9.4: 테스트 통과 확인**

Run: `pytest tests/test_rollback_modes.py -v`
Expected: 모든 테스트 PASS.

- [x] **Step 9.5: 커밋**

```bash
git add cli/rollback.py tests/test_rollback_modes.py
git commit -m "feat(Task-11): exit(0) explicitly after rollback to ensure console closes"
```

---

## Task 10: 통합 테스트 — fast 모드 endpoint 5초 이내

**Files:**
- Create: `tests/integration/test_rollback_fast_speed.py`

**의도:** fast 경로가 실제로 launcher 호출 없이 동작하며 sleep 누적이 짧음을 단위 수준에서 보장. (실제 win32 호출은 mock 처리.)

- [x] **Step 10.1: 통합 테스트 작성**

```python
"""Task-11: fast 모드가 launcher 경로를 우회하고 5초 안에 끝나는지 검증."""
import sys
import time
import types


def _stub_win32():
    g = types.ModuleType("win32gui")
    c = types.ModuleType("win32con")
    c.SW_SHOWNORMAL = 1; c.SW_SHOWMINIMIZED = 2; c.SW_SHOWMAXIMIZED = 3
    g.SetWindowPlacement = lambda *a: None
    g.SetWindowPos = lambda *a: None
    g.GetWindowPlacement = lambda *a: (0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600))
    g.GetWindowRect = lambda *a: (0, 0, 800, 600)
    sys.modules["win32gui"] = g
    sys.modules["win32con"] = c


def test_rollback_fast_finishes_within_5_seconds(monkeypatch, tmp_path):
    _stub_win32()

    layout = {
        "name": "L1",
        "windows": [{
            "exe_path": "C:\\app.exe",
            "title_snapshot": "App - foo",
            "title_pattern": "foo$",
            "class_name": "C1",
            "placement": {"state": "normal", "normal_rect": [0, 0, 800, 600],
                          "min_pos": [-1, -1], "max_pos": [-1, -1]},
            "z_order": 0,
        }],
        "monitors": [],
    }
    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "fast"},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: layout)
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])
    monkeypatch.setattr("src.capture.list_current_windows", lambda: [{
        "hwnd": 0xABCD, "exe_path": "C:\\app.exe",
        "title_snapshot": "App - foo", "class_name": "C1", "is_hidden": False,
    }])

    # ensure가 절대 호출되어선 안 되므로 호출되면 5초 sleep으로 실패 유도
    def fail_ensure(*a, **kw):
        time.sleep(10)
        return 0
    monkeypatch.setattr("src.launcher.ensure_apps_running", fail_ensure)
    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])

    t0 = time.monotonic()
    try:
        rollback.main()
    except SystemExit:
        pass
    elapsed = time.monotonic() - t0

    # post_settle_ms=2000 + 자체 호출 + 약간 여유 = 5초 이내
    assert elapsed < 5.0, f"fast rollback took {elapsed:.2f}s (>= 5s)"
```

- [x] **Step 10.2: 통합 테스트 실행**

Run: `pytest tests/integration/test_rollback_fast_speed.py -v`
Expected: PASS.

- [x] **Step 10.3: 전체 회귀 — 모든 단위 테스트 한 번에**

Run: `pytest tests/ -x -v`
Expected: 모든 테스트 PASS (다른 integration 테스트는 환경 의존이라 skip 가능).

- [x] **Step 10.4: 커밋**

```bash
git add tests/integration/test_rollback_fast_speed.py
git commit -m "test(Task-11): integration test ensures fast rollback < 5s"
```

---

## Task 11: 수동 회귀 테스트

각 항목을 실제 환경에서 한 번씩 실행해 결과를 기록한다.

- [ ] **11.1**: `python main.py` 실행 → GUI 좌하단에 `v1.12.0` 보임 확인.
- [ ] **11.2**: 부팅시 자동 복구 활성화 클릭 → 버튼이 "활성화됨" + 초록색으로 표시.
- [ ] **11.3**: GUI 종료 → 재실행 시 활성화 상태가 유지되며 처음부터 초록색 표시 확인.
- [ ] **11.4**: 부팅시 자동 복구 비활성화 클릭 → 버튼이 "활성화" + 시스템 기본 회색으로 복원 확인.
- [ ] **11.5**: 자동 복구를 활성화한 채로 OS 재부팅 → 사용자 로그온 후 시작 지연(기본 10s) 후 rollback이 fast 모드로 실행되며 콘솔창이 보이지 않거나 즉시 사라지는지 확인.
- [ ] **11.6**: 부팅 후 `%APPDATA%\WinLayoutSaver\logs\rollback-YYYYMMDD-HHMMSS.log` 파일 검사 — `mode=fast` 로그, `restore complete` 로그가 elapsed `< 5000ms`로 기록되어 있는지 확인.
- [ ] **11.7**: config 파일에서 `auto_rollback.mode`를 `"full"`로 변경 후 재부팅 → 기존 동작(앱 launch 포함)으로 복귀, 로그에 `mode=full` 표시 확인.
- [ ] **11.8**: 11.5~11.7에서 콘솔창이 잠깐이라도 보이면 issue 기록 후 다음 후속 조치 검토:
  - PowerShell에서 `Get-ScheduledTask -TaskName WinLayoutSaver_Rollback | Select * ` 출력으로 `Hidden` 속성이 True인지 확인.
  - 등록된 Action.Execute 경로가 `pyw.exe` 또는 `pythonw.exe`인지 확인 (`py.exe`/`python.exe`이면 Task 7 폴백 로직 점검).

---

## 최종 통합 단계

- [ ] **Final 1: 전체 테스트**

Run: `pytest tests/ -v`
Expected: 모든 단위 테스트 PASS, integration 중 환경 의존(`integration/test_restore_real.py` 등) 테스트는 skip 또는 환경상 pass.

- [ ] **Final 2: GUI 시동 확인**

Run: `python main.py` → 정상 실행, 버전 표시, 활성화 토글 동작.

- [ ] **Final 3: 변경 요약 커밋 푸시 (사용자 명시 요청 시에만)**

```bash
git log --oneline -n 10   # Task-11 관련 커밋이 6~9개 있어야 함
```

---

## 재개 가이드

플랜 진행 도중 중단되면:
1. 이 파일 상단 "Todo List" 섹션에서 마지막으로 `[x]` 마크된 Task를 찾는다.
2. 해당 Task의 step 체크박스 중 마지막 `[x]`의 다음 줄부터 재개한다.
3. step이 "Run: `pytest ...`"로 끝났다면 같은 명령을 먼저 실행해 현재 상태를 확인 후 다음 step 진행.
4. 코드 변경 step을 재개할 때는 해당 파일을 먼저 `git diff <파일>`로 확인해 이미 적용되어 있는지 검증.

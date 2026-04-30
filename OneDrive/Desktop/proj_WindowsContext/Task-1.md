# Task-1: 창 복원 오작동 수정 + 로그 모듈 필터 추가

## Context

### Bug 1 — Screen 저장/복원 불량

현재 `capture.py`가 저장 시 `title_pattern`을 항상 `""` 으로 기록한다.
`score_window`는 `title_pattern`이 빈 문자열이면 제목 매칭(+5)을 건너뛰므로,
**같은 exe를 가진 창이 여러 개일 때(Chrome 창 2개, 옵시디언 창 2개 등)** 모두 동일한 점수(exe+10, class+3 = 13)를 받아 순서에 따라 임의 매칭된다.

추가로 `score_window`는 저장 당시 `title_snapshot`과 현재 제목이 완전히 일치해도 보너스를 주지 않는다.
결과: 복원 시 창 위치가 섞이거나 아예 매칭 실패.

**Root causes (우선순위 순)**

| # | 위치 | 문제 |
|---|---|---|
| A | `capture.py` | `title_pattern`이 항상 `""` — 저장 시 자동 패턴 생성 없음 |
| B | `restore.py:score_window` | `title_snapshot` 완전 일치도 점수에 반영 안 됨 |
| C | `restore.py:restore_placement` | `SetWindowPlacement` 단독 호출 후 일부 앱(Chrome 등)이 위치를 덮어씀 — `SetWindowPos` 후속 호출 필요 |

### Bug 2 — 로그 패널에 logger 이름 필터 없음

하단 로그 테일 패널에 DEBUG/INFO/WARN/ERROR 레벨 필터만 있고 **모듈 필터**가 없다.
`monitors` 모듈은 1초 폴링으로 로그를 계속 생성하므로, 다른 모듈 로그를 보기 어렵다.
`_log_buffer`가 현재 `(levelname, text)` 튜플만 저장해 logger 이름을 나중에 필터링할 수 없다.

---

## 구현 단계 (TDD — 각 단계: 실패 테스트 작성 → 구현 → 통과)

### Step 1 — `score_window`: title_snapshot 완전 일치 보너스 (+5)

**파일**: `src/restore.py`, `tests/test_restore_matching.py`

#### 1-a. 테스트 먼저 작성 (Red)

`tests/test_restore_matching.py`에 추가:

```python
def test_exact_title_snapshot_match_scores_5_when_no_pattern():
    """title_pattern이 없어도 title_snapshot이 완전 일치하면 +5."""
    saved  = _saved(exe_path="C:\\app.exe", title_snapshot="My Window", title_pattern="")
    running = _running(exe_path="C:\\app.exe", title_snapshot="My Window")
    assert score_window(saved, running, set()) == 15  # exe(10) + title_snapshot_exact(5)

def test_no_bonus_when_title_snapshot_differs():
    """title_snapshot이 다르고 pattern도 없으면 보너스 없음."""
    saved  = _saved(exe_path="C:\\app.exe", title_snapshot="Window A", title_pattern="")
    running = _running(exe_path="C:\\app.exe", title_snapshot="Window B")
    assert score_window(saved, running, set()) == 10  # exe(10) only

def test_title_pattern_takes_precedence_over_snapshot_bonus():
    """title_pattern이 있고 매칭되면 +5 (snapshot 보너스 중복 없음)."""
    saved  = _saved(exe_path="C:\\app.exe", title_snapshot="Window A", title_pattern="Window")
    running = _running(exe_path="C:\\app.exe", title_snapshot="Window A")
    assert score_window(saved, running, set()) == 15  # exe(10) + pattern(5)

def test_two_same_exe_windows_match_by_title():
    """같은 exe 창 2개를 title_snapshot으로 각각 올바르게 매칭."""
    saved_a  = _saved(exe_path="C:\\app.exe", title_snapshot="Doc A")
    saved_b  = _saved(exe_path="C:\\app.exe", title_snapshot="Doc B")
    running_a = _running(exe_path="C:\\app.exe", title_snapshot="Doc A", hwnd=1)
    running_b = _running(exe_path="C:\\app.exe", title_snapshot="Doc B", hwnd=2)
    results = match_windows([saved_a, saved_b], [running_a, running_b])
    matched_hwnds = {r["hwnd"] for _, r in results if r}
    assert matched_hwnds == {1, 2}
    assert results[0][1]["hwnd"] == 1  # saved_a → running_a
    assert results[1][1]["hwnd"] == 2  # saved_b → running_b
```

#### 1-b. 구현 (Green)

`src/restore.py` — `score_window` 수정:

```python
def score_window(saved: dict, running: dict, already_assigned: set) -> int:
    if running["hwnd"] in already_assigned:
        return -100
    score = 0
    if saved.get("exe_path", "").lower() == running.get("exe_path", "").lower():
        score += 10
    pattern = saved.get("title_pattern", "")
    if pattern:
        try:
            if re.search(pattern, running.get("title_snapshot", "")):
                score += 5
        except re.error:
            pass
    elif saved.get("title_snapshot") and saved["title_snapshot"] == running.get("title_snapshot"):
        # title_pattern 없을 때 title_snapshot 완전 일치 시 동일한 +5 보너스
        score += 5
    if saved.get("class_name") and saved["class_name"] == running.get("class_name"):
        score += 3
    return score
```

#### 1-c. 검증

```
pytest tests/test_restore_matching.py -v
pytest -q   # 전체 회귀 방지
```

---

### Step 2 — `restore_placement`: SetWindowPos 후속 호출로 위치 강제 적용

**파일**: `src/restore.py`, `tests/test_restore_matching.py`

Chrome, Electron 앱 등은 `SetWindowPlacement` 후 자체 WM_WINDOWPOSCHANGED 처리로 위치를 덮어쓴다.
`SetWindowPlacement` → 잠깐 대기 → `SetWindowPos` 순서로 위치를 강제 적용한다.

#### 2-a. 테스트 먼저 작성 (Red)

```python
def test_restore_placement_normal_also_calls_set_window_pos(mock_win32):
    """normal 상태 복원 시 SetWindowPlacement 후 SetWindowPos도 호출되어야 한다."""
    import win32gui, win32con
    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock(return_value=True)
    placement = {"state": "normal", "normal_rect": [100, 200, 800, 600],
                 "min_pos": [-1, -1], "max_pos": [-1, -1]}
    result = restore_placement(0x1234, placement)
    assert result is True
    win32gui.SetWindowPos.assert_called_once()
    args = win32gui.SetWindowPos.call_args[0]
    # 위치 인자: x=100, y=200, w=800, h=600
    assert args[2] == 100  # x
    assert args[3] == 200  # y
    assert args[4] == 800  # w
    assert args[5] == 600  # h

def test_restore_placement_maximized_skips_set_window_pos(mock_win32):
    """maximized는 위치 강제 불필요 — SetWindowPos 미호출."""
    import win32gui
    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    placement = {"state": "maximized", "normal_rect": [0, 0, 800, 600],
                 "min_pos": [-1, -1], "max_pos": [-1, -1]}
    restore_placement(0x1234, placement)
    win32gui.SetWindowPos.assert_not_called()
```

#### 2-b. 구현 (Green)

`src/restore.py` — `restore_placement` 수정:

```python
def restore_placement(hwnd: int, placement: dict) -> bool:
    try:
        import win32gui
        import win32con
    except ImportError:
        logger.error("pywin32 not installed — cannot restore placement")
        raise

    try:
        state = placement.get("state", "normal")
        nr = placement.get("normal_rect", [0, 0, 800, 600])  # XYWH
        min_pos = tuple(placement.get("min_pos", [-1, -1]))
        max_pos = tuple(placement.get("max_pos", [-1, -1]))

        if state == "minimized":
            show_cmd = win32con.SW_SHOWMINIMIZED
        elif state == "maximized":
            show_cmd = win32con.SW_SHOWMAXIMIZED
        else:
            show_cmd = win32con.SW_SHOWNORMAL

        ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])
        win32gui.SetWindowPlacement(hwnd, (0, show_cmd, min_pos, max_pos, ltrb))

        # Chrome/Electron 등이 WM_WINDOWPOSCHANGED로 위치를 덮어쓰는 경우를 방지.
        # normal 상태일 때만 SetWindowPos로 위치를 재강제한다.
        if state == "normal":
            SWP_NOACTIVATE = 0x0010
            SWP_NOZORDER   = 0x0004
            win32gui.SetWindowPos(
                hwnd, None,
                nr[0], nr[1], nr[2], nr[3],
                SWP_NOACTIVATE | SWP_NOZORDER,
            )

        logger.info("placed hwnd=0x%x state=%s rect=%s", hwnd, state, nr)
        return True
    except OSError as e:
        logger.warning("failed to place hwnd=0x%x: %s", hwnd, e)
        return False
```

#### 2-c. 검증

```
pytest tests/test_restore_matching.py -v
pytest -q
```

---

### Step 3 — `capture.py`: title_pattern 자동 생성

**파일**: `src/capture.py`, `tests/test_capture.py`

저장 시 `title_snapshot`에서 앱 이름 부분을 추출해 `title_pattern`을 자동 생성한다.
규칙: 제목의 마지막 ` - App Name` 형태 suffix를 `App Name$` 패턴으로 변환.
없으면 제목 전체를 `re.escape`로 exact match 패턴으로 저장.

```
"My Doc - Google Chrome"  →  "Google Chrome$"
"Vault - Obsidian"        →  "Obsidian$"
"Untitled - Notepad"      →  "Notepad$"
"제목 없음"               →  "제목\ 없음$"  (re.escape)
```

#### 3-a. 테스트 먼저 작성 (Red)

`tests/test_capture.py`에 추가:

```python
import re
from src.capture import _auto_title_pattern

class TestAutoTitlePattern:
    def test_extracts_app_name_suffix(self):
        assert _auto_title_pattern("My Doc - Google Chrome") == "Google\\ Chrome$"

    def test_extracts_obsidian_suffix(self):
        assert _auto_title_pattern("Vault - Obsidian") == "Obsidian$"

    def test_no_dash_returns_escaped_full_title(self):
        # 대시가 없으면 전체 제목을 escape해서 exact match 패턴으로
        result = _auto_title_pattern("제목 없음")
        assert result == re.escape("제목 없음") + "$"

    def test_multiple_dashes_uses_last_segment(self):
        # "a - b - AppName" → "AppName$"
        assert _auto_title_pattern("a - b - MyApp") == "MyApp$"

    def test_pattern_matches_original_title(self):
        title = "My Doc - Google Chrome"
        pattern = _auto_title_pattern(title)
        assert re.search(pattern, title)

    def test_list_current_windows_sets_nonempty_title_pattern(self, mock_win32):
        """list_current_windows 반환값의 title_pattern이 비어있지 않다."""
        # 기존 mock 환경에서 title을 명시적으로 설정해 테스트
        # (기존 conftest mock_win32 활용)
        pass  # 구체적 구현은 기존 mock 패턴에 맞춰 작성
```

#### 3-b. 구현 (Green)

`src/capture.py`에 함수 추가 및 `list_current_windows` 수정:

```python
import re as _re

def _auto_title_pattern(title: str) -> str:
    """
    창 제목에서 앱 이름 부분을 추출해 regex 패턴 반환.
    "Doc - App" 형식이면 마지막 ' - ' 이후를 '<App>$' 패턴으로.
    없으면 전체 제목을 escape해서 exact match 패턴으로.
    """
    sep = " - "
    if sep in title:
        app_name = title.rsplit(sep, 1)[-1].strip()
        return _re.escape(app_name) + "$"
    return _re.escape(title) + "$"
```

`list_current_windows` 내 entry 구성 시 `title_pattern` 필드 변경:

```python
entry = {
    ...
    "title_pattern": _auto_title_pattern(title),  # "" 대신 자동 생성
    ...
}
```

#### 3-c. 검증

```
pytest tests/test_capture.py -v
pytest -q
```

---

### Step 4 — 로그 패널: logger 이름 필터 추가 (Monitors 등)

**파일**: `src/gui.py`, `src/gui_helpers.py` (신규), `src/i18n.py`, `tests/test_gui_log_filter.py` (신규)

#### 4-a. 스펙

- `_log_buffer` 튜플을 `(level, logger_name, text)` 3-튜플로 확장
- `_drain_log_queue`에서 `record.name`을 buffer에 함께 저장
- 로그 필터 행 아래에 **모듈 필터 행** 추가:
  `[monitors] [capture] [restore] [launcher] [scheduler] [gui] [rollback] [storage]`
  체크 해제 시 해당 logger 이름의 로그를 숨김
  기본값: 모두 체크, `monitors`만 기본 **체크 해제**
- `_append_log_line(level, logger_name, text)` 시그니처 변경
  → 레벨 필터 AND 모듈 필터 모두 통과해야 표시
- `_apply_log_filter`도 3-튜플 사용으로 업데이트

#### 4-b. i18n 키 추가 (`src/i18n.py`)

```python
# ko
"log_module_filter_label": "모듈:",
# en
"log_module_filter_label": "Module:",
```

#### 4-c. `src/gui_helpers.py` 신규 파일

필터 로직을 순수 함수로 추출해 단위 테스트 가능하게 만든다:

```python
KNOWN_MODULES = frozenset({
    "monitors", "capture", "restore", "launcher",
    "scheduler", "gui", "rollback", "storage",
})

def should_show_log_entry(
    level: str,
    logger_name: str,
    level_on: set,
    module_on: set | None,
) -> bool:
    """Log entry 표시 여부 결정 (레벨 AND 모듈 필터)."""
    if level not in level_on:
        return False
    if module_on is None:
        return True
    # 등록된 모듈 목록에 없는 logger는 필터 통과 처리
    if logger_name not in KNOWN_MODULES:
        return True
    return logger_name in module_on
```

#### 4-d. 테스트 (`tests/test_gui_log_filter.py` 신규)

```python
from src.gui_helpers import should_show_log_entry

class TestLogFilter:
    def test_passes_when_both_filters_enabled(self):
        assert should_show_log_entry("INFO", "capture",
            level_on={"INFO"}, module_on={"capture"}) is True

    def test_blocked_by_level_filter(self):
        assert should_show_log_entry("DEBUG", "capture",
            level_on={"INFO"}, module_on={"capture"}) is False

    def test_blocked_by_module_filter(self):
        assert should_show_log_entry("INFO", "monitors",
            level_on={"INFO"}, module_on={"capture"}) is False

    def test_passes_when_module_on_is_none(self):
        """module_on=None이면 모든 모듈 허용."""
        assert should_show_log_entry("INFO", "monitors",
            level_on={"INFO"}, module_on=None) is True

    def test_unknown_module_always_passes(self):
        """등록되지 않은 logger 이름은 필터 통과."""
        assert should_show_log_entry("INFO", "unknown_mod",
            level_on={"INFO"}, module_on={"capture"}) is True

    def test_monitors_blocked_when_not_in_module_on(self):
        assert should_show_log_entry("INFO", "monitors",
            level_on={"INFO"}, module_on={"capture", "restore"}) is False
```

#### 4-e. `src/gui.py` 수정 요점

```python
# _log_buffer: (level, logger_name, text) 3-튜플로 확장
self._log_buffer: list[tuple[str, str, str]] = []

# _drain_log_queue 내
logger_name = record.name
self._log_buffer.append((display_level, logger_name, text))
self._append_log_line(display_level, logger_name, text)

# _append_log_line(level, logger_name, text) 시그니처 변경
from src.gui_helpers import should_show_log_entry
level_on  = {k for k, v in self._log_levels.items() if v.get()}
module_on = {k for k, v in self._module_filters.items() if v.get()}
if not should_show_log_entry(level, logger_name, level_on, module_on):
    return
# ... 이후 기존 insert 로직 동일

# _build_ui — 모듈 필터 행 추가 (레벨 필터 행 바로 아래)
self._module_filters: dict[str, tk.BooleanVar] = {}
module_row = tk.Frame(log_frame)
module_row.pack(fill=tk.X)
tk.Label(module_row, text=t("log_module_filter_label")).pack(side=tk.LEFT)
MODULES = ["monitors", "capture", "restore", "launcher",
           "scheduler", "gui", "rollback", "storage"]
for mod in MODULES:
    default_on = (mod != "monitors")  # monitors는 기본 OFF
    var = tk.BooleanVar(value=default_on)
    tk.Checkbutton(module_row, text=mod, variable=var,
                   command=self._apply_log_filter).pack(side=tk.LEFT)
    self._module_filters[mod] = var
```

#### 4-f. 검증

```
pytest tests/test_gui_log_filter.py -v
pytest tests/test_i18n.py -v
pytest -q
```

---

## 전체 완료 기준

```
pytest -q   →  모든 테스트 초록불
```

수동 확인:
1. Chrome + 옵시디언 2개씩 열고 저장 → 위치 흐트러뜨림 → 복원 → 각 창이 저장된 위치로 돌아오는지
2. 로그 패널에서 `monitors` 체크 해제 시 monitors 폴링 로그가 사라지고, 다시 체크 시 나타나는지
3. 레벨 필터 + 모듈 필터 동시 적용 시 AND 조건으로 필터링되는지

## 파일 변경 목록

| 파일 | 변경 유형 |
|---|---|
| `src/restore.py` | 수정 — `score_window` title_snapshot 보너스, `restore_placement` SetWindowPos 추가 |
| `src/capture.py` | 수정 — `_auto_title_pattern` 추가, `title_pattern` 자동 생성 |
| `src/gui.py` | 수정 — 모듈 필터 행, `_log_buffer` 3-튜플, `_append_log_line` 시그니처 |
| `src/gui_helpers.py` | 신규 — `should_show_log_entry` 순수 함수 |
| `src/i18n.py` | 수정 — `log_module_filter_label` 키 추가 |
| `tests/test_restore_matching.py` | 수정 — title_snapshot 보너스 테스트, SetWindowPos 테스트 |
| `tests/test_capture.py` | 수정 — `_auto_title_pattern` 테스트 |
| `tests/test_gui_log_filter.py` | 신규 — `should_show_log_entry` 단위 테스트 |
| `tests/test_i18n.py` | 수정 — 새 i18n 키 커버리지 |

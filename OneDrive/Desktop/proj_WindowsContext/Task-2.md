# Task-2: Chrome·KakaoTalk 등 복구 안 되는 창 수정

## 로그 분석

```
no candidate for 'NAVER - Chrome'    (exe=...chrome.exe)
no candidate for '카카오톡'           (exe=...KakaoTalk.exe)
```

`no candidate` = 해당 저장 창에 점수 > 0인 running 창이 하나도 없음.
이는 창이 `list_current_windows()`의 running 목록에 **아예 포함되지 않아서** 발생한다.

---

## 근본 원인

### Root Cause A — `_get_exe_path` 실패 → 창 완전 제외

`capture.py:130-134`:
```python
exe_path = _get_exe_path(hwnd)
if exe_path is None:
    skipped += 1
    continue          # ← 창 자체를 제외
```

`_get_exe_path` 내부에서 `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` 호출이
- 권한 부족 (sandboxed Chrome renderer)
- 보호된 프로세스 (KakaoTalk 등 일부 앱)
- 짧은 race condition (프로세스 종료 직후)

등으로 실패하면 None을 반환하고, 해당 창이 running 목록에서 제외된다.
결과: score_window가 이 창을 볼 기회가 없으므로 `no candidate`.

**수정**: exe_path=None이면 skip 대신 `exe_path=""`로 포함.
title_pattern · title_snapshot · class_name 으로만 매칭해도 score ≥ 5 > 0이 가능하다.

---

### Root Cause B — `IsWindowVisible=False` → 트레이·숨겨진 창 제외

`capture.py:110-113`:
```python
if not win32gui.IsWindowVisible(hwnd):
    skipped += 1
    continue          # ← 트레이 창 제외
```

KakaoTalk처럼 "X" 버튼을 눌러 트레이로 보내면 메인 창이 `ShowWindow(SW_HIDE)` 상태가 되어
`IsWindowVisible=False`가 된다. 이 경우 창 자체가 running 목록에서 제외된다.

**수정**: `IsWindowVisible=False`이더라도 title이 있고 cloaked/tool window가 아니면 포함.
단, `is_hidden=True` 플래그를 entry에 추가.
복원 시 `ShowWindow(SW_SHOW)` 후 `SetWindowPlacement`를 호출해 창을 다시 표시한다.

---

## 파일 변경 목록

| 파일 | 유형 |
|---|---|
| `src/capture.py` | 수정 — 두 Root Cause 수정 |
| `src/restore.py` | 수정 — `restore_placement`에 `is_hidden` 처리 추가, `restore_layout`에서 전달 |
| `tests/test_capture.py` | 수정 — 3개 테스트 업데이트 + 2개 신규 |
| `tests/test_restore_matching.py` | 수정 — is_hidden 복원 테스트 신규 |

---

## 구현 단계 (TDD)

### Step 1 — Root Cause A: exe_path=None 창 포함

#### 1-a. Red — 테스트 먼저 작성 (`tests/test_capture.py`에 추가)

```python
def test_includes_window_when_exe_path_lookup_fails(monkeypatch):
    """_get_exe_path가 None을 반환해도 창이 exe_path=""로 포함된다."""
    import win32gui, win32con
    hwnd = 50
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "NAVER - Chrome"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "Chrome_WidgetWin_1"
    win32gui.GetWindowPlacement = lambda h: (0, 1, (-1, -1), (-1, -1), (0, 0, 1920, 1080))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: None)
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert len(results) == 1
    assert results[0]["exe_path"] == ""
    assert results[0]["title_snapshot"] == "NAVER - Chrome"
```

Run: `pytest tests/test_capture.py::test_includes_window_when_exe_path_lookup_fails -v`
Expected: FAIL — `AssertionError: assert [] == 1`

#### 1-b. Green — `src/capture.py` 수정

`exe_path=None` 블록을:
```python
exe_path = _get_exe_path(hwnd)
if exe_path is None:
    logger.warning("skipped hwnd=%s (no exe path)", hwnd)
    skipped += 1
    continue
```

아래로 교체:
```python
exe_path = _get_exe_path(hwnd)
if exe_path is None:
    logger.warning("hwnd=%s exe_path lookup failed — included with empty path", hwnd)
    exe_path = ""
```

#### 1-c. 검증

```
pytest tests/test_capture.py -v
```

---

### Step 2 — Root Cause B: 비가시 창 포함 + is_hidden 플래그

#### 2-a. 기존 테스트 수정 (`test_filters_invisible_windows`)

기존 동작 "invisible → 제외"가 변경되므로 테스트 업데이트:

```python
def test_invisible_window_included_with_is_hidden_flag(monkeypatch):
    """IsWindowVisible=False인 창도 title이 있으면 is_hidden=True로 포함된다."""
    import win32gui, win32con
    hwnd = 2
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: False   # 트레이 숨김
    win32gui.GetWindowText = lambda h: "카카오톡"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "EVA_Window_Dblclk"
    win32gui.GetWindowPlacement = lambda h: (0, 1, (-1, -1), (-1, -1), (0, 0, 400, 600))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\KakaoTalk.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert len(results) == 1
    assert results[0]["title_snapshot"] == "카카오톡"
    assert results[0]["is_hidden"] is True
```

기존 `test_filters_invisible_windows` 테스트는 이 테스트로 대체한다(이름 변경).

#### 2-b. 기존 테스트 수정 (`test_returns_expected_keys`)

`is_hidden` 키가 추가되므로 expected_keys 업데이트:

```python
expected_keys = {
    "exe_path", "exe_args", "cwd", "title_snapshot", "title_pattern",
    "class_name", "placement", "monitor_index", "z_order",
    "is_topmost", "is_uwp", "hwnd", "is_hidden"   # is_hidden 추가
}
```

#### 2-c. 가시 창은 is_hidden=False 테스트 추가

```python
def test_visible_window_has_is_hidden_false(monkeypatch):
    """IsWindowVisible=True인 창은 is_hidden=False다."""
    import win32gui, win32con
    hwnd = 4
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "Notepad"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "Notepad"
    win32gui.GetWindowPlacement = lambda h: (0, 1, (-1, -1), (-1, -1), (100, 100, 900, 700))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\Windows\\notepad.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert len(results) == 1
    assert results[0]["is_hidden"] is False
```

#### 2-d. Green — `src/capture.py` 수정

`IsWindowVisible` 하드 필터 제거 및 is_hidden 플래그 추가:

```python
# 기존 (제거):
if not win32gui.IsWindowVisible(hwnd):
    logger.debug("skipped invisible hwnd=%s", hwnd)
    skipped += 1
    continue

# 신규 (대체):
is_hidden = not win32gui.IsWindowVisible(hwnd)
```

그리고 `title = win32gui.GetWindowText(hwnd)` 이후에 위치한 기존 title 필터는 유지.
cloaked/tool window 필터도 유지 — 이 두 필터가 진짜 시스템 백그라운드 창을 제거한다.

entry 딕셔너리에 `is_hidden` 추가:
```python
entry = {
    "hwnd": hwnd,
    "exe_path": exe_path,
    "exe_args": "",
    "cwd": "",
    "title_snapshot": title,
    "title_pattern": _auto_title_pattern(title),
    "class_name": class_name,
    "placement": {
        "state": state,
        "normal_rect": normal_rect,
        "min_pos": min_pos,
        "max_pos": max_pos,
    },
    "monitor_index": monitor_index,
    "z_order": i,
    "is_topmost": False,
    "is_uwp": is_uwp,
    "is_hidden": is_hidden,    # 추가
}
```

#### 2-e. 검증

```
pytest tests/test_capture.py -v
```

---

### Step 3 — restore_placement: is_hidden 창 복원 시 ShowWindow

#### 3-a. Red — 테스트 추가 (`tests/test_restore_matching.py`에 추가)

```python
def test_restore_placement_shows_hidden_window_before_placing(monkeypatch):
    """is_hidden=True 창 복원 시 ShowWindow(SW_SHOW) 후 SetWindowPlacement를 호출한다."""
    from unittest.mock import MagicMock, call
    import win32gui, win32con
    call_order = []
    win32gui.ShowWindow = MagicMock(side_effect=lambda *a: call_order.append("show"))
    win32gui.SetWindowPlacement = MagicMock(side_effect=lambda *a: call_order.append("place"))
    win32gui.SetWindowPos = MagicMock()

    from src.restore import restore_placement
    placement = {"state": "normal", "normal_rect": [0, 0, 800, 600],
                 "min_pos": [-1, -1], "max_pos": [-1, -1]}
    result = restore_placement(0x1234, placement, is_hidden=True)

    assert result is True
    assert call_order == ["show", "place"]  # ShowWindow → SetWindowPlacement 순서


def test_restore_placement_visible_window_skips_show_window(monkeypatch):
    """is_hidden=False(기본값) 창은 ShowWindow를 호출하지 않는다."""
    from unittest.mock import MagicMock
    import win32gui
    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.ShowWindow = MagicMock()

    from src.restore import restore_placement
    placement = {"state": "normal", "normal_rect": [0, 0, 800, 600],
                 "min_pos": [-1, -1], "max_pos": [-1, -1]}
    restore_placement(0x1234, placement)  # is_hidden 기본값=False

    win32gui.ShowWindow.assert_not_called()
```

Run: `pytest tests/test_restore_matching.py::test_restore_placement_shows_hidden_window_before_placing -v`
Expected: FAIL

#### 3-b. mock_win32 fixture에 ShowWindow 추가

`tests/test_restore_matching.py`의 `mock_win32` fixture:
```python
win32gui.SetWindowPos = lambda *a: None
win32gui.ShowWindow = lambda *a: None    # ← 추가
```

#### 3-c. Green — `src/restore.py` 수정

`restore_placement` 시그니처에 `is_hidden` 파라미터 추가:

```python
def restore_placement(hwnd: int, placement: dict, is_hidden: bool = False) -> bool:
```

`win32gui.SetWindowPlacement(...)` 호출 직전에 추가:
```python
        if is_hidden:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        win32gui.SetWindowPlacement(hwnd, (
            0, show_cmd, min_pos, max_pos, ltrb,
        ))
```

#### 3-d. `restore_layout`에서 is_hidden 전달

`src/restore.py`의 `restore_layout` 내:
```python
        ok = restore_placement(running["hwnd"], saved["placement"])
```
→
```python
        ok = restore_placement(running["hwnd"], saved["placement"],
                               is_hidden=running.get("is_hidden", False))
```

#### 3-e. 검증

```
pytest tests/test_restore_matching.py -v
pytest -q
```

---

### Step 4 — 프로그램이 꺼져 있으면 자동 실행 후 복원

`launcher.py`에 `ensure_apps_running()` · `launch_app()` · `wait_for_window()`가 이미 구현되어 있지만,
`restore_layout()`에서 호출하지 않아 기능이 동작하지 않는다.

#### 4-a. 현재 문제 정리

```
restore_layout()
    ↓
list_current_windows()   ← 지금 떠 있는 창만 스캔
    ↓
match_windows()          ← Chrome이 꺼져 있으면 → no candidate
```

#### 4-b. Red — 테스트 추가 (`tests/test_launcher.py`에 추가)

```python
def test_ensure_apps_running_skips_empty_exe_path(monkeypatch):
    """exe_path=""인 창은 실행 불가이므로 launch_app을 호출하지 않는다."""
    import psutil
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: [])

    launched = []
    monkeypatch.setattr("src.launcher.launch_app",
                        lambda exe, **kw: launched.append(exe) or MagicMock())
    monkeypatch.setattr("src.launcher.wait_for_window", lambda *a, **kw: True)

    from src.launcher import ensure_apps_running
    ensure_apps_running([{"exe_path": "", "exe_args": "", "cwd": "",
                          "is_uwp": False, "title_pattern": ""}])
    assert launched == []   # exe_path="" → 실행 시도 안 함
```

Run: `pytest tests/test_launcher.py::test_ensure_apps_running_skips_empty_exe_path -v`
Expected: FAIL — `ensure_apps_running`이 현재 exe_path="" 창도 실행 시도함

#### 4-c. Green — `src/launcher.py` 수정

`ensure_apps_running`의 not_running 필터에 `exe_path` 유효성 추가:

```python
not_running = [
    w for w in saved_windows
    if w.get("exe_path") and not is_running(w["exe_path"])
]
```

기존 코드:
```python
not_running = [w for w in saved_windows if not is_running(w.get("exe_path", ""))]
```

#### 4-d. Red — restore_layout 통합 테스트 (`tests/test_launcher.py`에 추가)

```python
def test_restore_layout_launches_missing_app_then_rematch(monkeypatch):
    """복원 시 매칭 안 된 앱을 자동 실행하고 재스캔 후 재매칭한다."""
    import psutil
    from unittest.mock import MagicMock

    # 첫 번째 스캔: Chrome 없음 / 두 번째 스캔: Chrome 있음
    scan_count = {"n": 0}

    def fake_list_current():
        scan_count["n"] += 1
        if scan_count["n"] == 1:
            return []   # 처음엔 빈 목록
        return [{       # 앱 실행 후 재스캔 결과
            "hwnd": 0xABCD,
            "exe_path": "C:\\chrome.exe",
            "title_snapshot": "NAVER - Chrome",
            "title_pattern": "Chrome$",
            "class_name": "Chrome_WidgetWin_1",
            "is_hidden": False,
        }]

    launched = []

    def fake_ensure(saved_windows, **kwargs):
        for w in saved_windows:
            if w.get("exe_path"):
                launched.append(w["exe_path"])

    monkeypatch.setattr("src.restore.list_current_windows", fake_list_current)
    monkeypatch.setattr("src.restore.ensure_apps_running", fake_ensure)

    from src.restore import restore_layout

    layout = {
        "name": "test",
        "windows": [{
            "exe_path": "C:\\chrome.exe",
            "title_snapshot": "NAVER - Chrome",
            "title_pattern": "Chrome$",
            "class_name": "Chrome_WidgetWin_1",
            "placement": {"state": "normal", "normal_rect": [0, 0, 800, 600],
                          "min_pos": [-1, -1], "max_pos": [-1, -1]},
            "z_order": 0,
        }],
        "monitors": [],
    }

    result = restore_layout(layout)

    assert "C:\\chrome.exe" in launched   # 자동 실행 시도
    assert scan_count["n"] == 2           # 두 번 스캔 (launch 전/후)
    assert result["restored"] == 1
```

Run: `pytest tests/test_launcher.py::test_restore_layout_launches_missing_app_then_rematch -v`
Expected: FAIL — `restore_layout`이 `ensure_apps_running`을 호출하지 않음

#### 4-e. Green — `src/restore.py` 수정

`restore_layout` 내 monitor gate 처리 이후, `match_windows` 호출 이전에 추가:

```python
    from src.launcher import ensure_apps_running

    # 꺼진 앱 자동 실행
    ensure_apps_running(sorted_saved)

    # 앱 실행 후 재스캔 (새 창 포함)
    if running_windows is None:
        running_windows = list_current_windows()
```

기존 `if running_windows is None:` 블록(초반부)은 제거하고 위 코드로 대체.

전체 흐름 변경:
```python
    # 기존 (제거):
    if running_windows is None:
        from src.capture import list_current_windows
        running_windows = list_current_windows()

    # ... monitor gate ...

    sorted_saved = sorted(...)

    # 신규 순서:
    # 1. ensure_apps_running (꺼진 앱 실행)
    from src.launcher import ensure_apps_running
    if running_windows is None:          # 외부 주입이 아닐 때만 launch+rescan
        ensure_apps_running(sorted_saved)
        running_windows = list_current_windows()

    matches = match_windows(sorted_saved, running_windows)
```

> **Note**: `running_windows`가 외부에서 주입된 경우(테스트 등)는 `ensure_apps_running`을 건너뜀.

#### 4-f. 검증

```
pytest tests/test_launcher.py -v
pytest -q
```

---

## 전체 완료 기준

```
pytest -q   →  모든 테스트 초록불
```

수동 확인:
1. Chrome 닫음 → 복원 버튼 → Chrome이 자동 실행되고 저장된 위치로 이동하는지
2. KakaoTalk 트레이로 보내기 → 복원 버튼 → KakaoTalk 창이 나타나고 저장된 위치로 이동하는지
3. Chrome 창 열고 저장 → 위치 흐트러뜨림 → 복원 → 위치 복원되는지

---

## 파일 변경 목록 (전체)

| 파일 | 유형 |
|---|---|
| `src/capture.py` | 수정 — exe_path="" 포함, is_hidden 플래그 |
| `src/restore.py` | 수정 — is_hidden ShowWindow, ensure_apps_running 연동 |
| `src/launcher.py` | 수정 — exe_path="" skip 추가 |
| `tests/test_capture.py` | 수정 — 3개 업데이트 + 2개 신규 |
| `tests/test_restore_matching.py` | 수정 — is_hidden 복원 테스트 신규 |
| `tests/test_launcher.py` | 수정 — 2개 신규 |

## 수정 요약

| 증상 | 원인 | 수정 위치 |
|---|---|---|
| Chrome `no candidate` (켜져 있음) | `_get_exe_path` 실패 시 창 skip | `capture.py`: exe_path="" 로 포함 |
| KakaoTalk `no candidate` (트레이) | IsWindowVisible=False → 창 제외 | `capture.py`: is_hidden=True로 포함 |
| 트레이 창 복원 안 됨 | ShowWindow 미호출 | `restore.py`: is_hidden 시 SW_SHOW 선행 호출 |
| Chrome `no candidate` (꺼져 있음) | restore 전에 앱 실행 안 함 | `restore.py` + `launcher.py`: ensure_apps_running 연동 |

###리뷰  후 요청

- 페이지 복구 누락의 원인은 launcher.py에 ensure_apps_running()이 이미 구현되어 있지만 restore_layout()에서 호출하지 않는 것으로 한정하고, 동일한 페이지 복구 누락을 고치기 위해 수행되는 추가적인 코드 수정은 과도한 코드 수정으로 판단되므로 Task-2.md에서 제외할 것(단, Test Code는 동일하게 수정 진행할 것)
# Task-7: 복구 후 1~2초 뒤 창 배치 붕괴 수정

## 현재 상태 (2026-04-27 기준)

**증상:** 복구 버튼 클릭 시 처음엔 저장된 배치대로 정상 표시되지만,
1~2초 후 **일부 창이 저장 위치와 다른 '일정한 위치'로 이동**해 배치가 무너짐.

- 영향 앱: Chrome/Edge(Chromium), UWP 앱, Win32 앱
- 상황: 레이아웃 내 일부 앱은 실행 중, 일부는 재실행(새로 론칭)
- 붕괴 시 창이 이동하는 위치: 앱 자체 프로파일 저장 위치(저장 레이아웃 위치와 다름)

---

## 근본 원인 분석

### 호출 경로

```
GUI._on_restore(name)
  └─ threading.Thread(target=_work).start()
       └─ restore_mod.restore_layout(layout, monitors_current=…)
            ├─ 1. ensure_apps_running(sorted_saved)   ← 빠진 앱 새로 실행
            ├─ 2. time.sleep(stabilize_ms / 1000)     ← 기본 1500ms 대기
            ├─ 3. list_current_windows()              ← 재스캔
            ├─ 4. match_windows(saved, running)
            ├─ 5. restore_placement(hwnd, placement)  ← 초기 배치 → 유저에게 정상으로 보임
            ├─ 6. time.sleep(post_settle_ms / 1000)   ← 기본 2000ms 대기
            └─ 7. restore_placement(hwnd, placement)  ← 재적용(post-settle)
```

### 앱별 "startup window restoration" 소요 시간

| 앱 | 창 표시 후 자체 위치 복원 시작까지 |
|----|-----------------------------------|
| UWP Notepad (AppData 복원) | 1 ~ 4 초 |
| Chrome (profile 복원) | 1 ~ 8 초 |
| 일반 Win32 앱 | 거의 없음 |

### 실패 타임라인 (Chrome 예시)

```
t=0     : ensure_apps_running → Chrome 실행 → wait_for_window 반환
t=0~1.5 : stabilize_ms 대기 (1500ms)
t=1.5   : 초기 배치 → Chrome 저장 위치로 이동 ← 유저에게 정상으로 보임 ✓
t=2~6   : Chrome이 자신의 profile 위치로 되돌림 ← 유저에게 붕괴로 보임 ✗
t=3.5   : post_settle_ms 재적용 시도 → Chrome이 여전히 fight-back 중
            → restore_placement 3회 재시도 모두 실패 → False 반환
t=3.5+  : 더 이상 재적용 없음 → 배치 붕괴 상태 유지 ✗
```

**핵심 원인:** `post_settle_ms=2000ms` 재적용(t=3.5s)이 Chrome의 profile 복원
활동 기간(t=2~8s) 한가운데 실행되므로, `restore_placement` 내 3회 재시도가
모두 fight-back에 패배하고 False를 반환한다.
이후 재적용 기회가 없으므로 붕괴 상태가 지속된다.

### 코드 확인

**`src/launcher.py:98`** `ensure_apps_running`:
- 현재 반환값: `None`
- 앱을 몇 개 실행했는지 `restore_layout`이 알 방법이 없음

**`src/restore.py:237`** post-settle 재적용 블록:
```python
if post_settle_ms > 0 and matched_pairs:
    time.sleep(post_settle_ms / 1000.0)         # 2초 대기
    for saved, running in matched_pairs:
        restore_placement(running["hwnd"], saved["placement"])  # 1회만 재적용
```
- 새로 론칭된 앱의 긴 startup restoration(≤8s)을 커버할 2차 재적용이 없음

**`src/gui.py:253`** `_on_restore`:
```python
result = restore_mod.restore_layout(layout, monitors_current=self._current_monitors or None)
```
- `post_launch_settle_ms` 같은 추가 파라미터를 전달하지 않음

---

## 수정 계획

### M1: `ensure_apps_running` 반환값 추가 (`src/launcher.py`)

**변경 위치:** `src/launcher.py:98` `ensure_apps_running` 함수

**변경 내용:**

```python
# 변경 전
def ensure_apps_running(
    saved_windows: list[dict],
    timeout_seconds: float = 60.0,
    poll_ms: int = 500,
) -> None:

# 변경 후
def ensure_apps_running(
    saved_windows: list[dict],
    timeout_seconds: float = 60.0,
    poll_ms: int = 500,
) -> int:
    """
    ...
    Returns:
        int: 실제로 launch_app을 호출한 앱 수 (0이면 모두 이미 실행 중)
    """
```

함수 마지막 줄 추가:
```python
    # 기존 for 루프 끝
    return len(not_running)
```

**완료 조건:** `ensure_apps_running`이 `int`를 반환

---

### M2: `restore_layout`에 `post_launch_settle_ms` 파라미터 추가 (`src/restore.py`)

**변경 위치:** `src/restore.py:145` `restore_layout` 함수 시그니처 및 본문

**변경 내용 — 시그니처:**

```python
def restore_layout(
    layout: dict,
    running_windows: list[dict] = None,
    monitors_current: list[dict] = None,
    stabilize_ms: int = 1500,
    post_settle_ms: int = 2000,
    post_launch_settle_ms: int = 0,   # 추가: 새 앱 론칭 시 2차 재적용 대기(ms)
) -> dict:
```

**변경 내용 — `ensure_apps_running` 호출부 (`restore_layout:207`)**

```python
# 변경 전
if running_windows is None:
    from src.launcher import ensure_apps_running
    from src.capture import list_current_windows
    running_windows = list_current_windows()
    ensure_apps_running(sorted_saved)
    if stabilize_ms > 0:
        time.sleep(stabilize_ms / 1000.0)
    running_windows = list_current_windows()

# 변경 후
launched_count = 0
if running_windows is None:
    from src.launcher import ensure_apps_running
    from src.capture import list_current_windows
    running_windows = list_current_windows()
    launched_count = ensure_apps_running(sorted_saved)
    if stabilize_ms > 0:
        time.sleep(stabilize_ms / 1000.0)
    running_windows = list_current_windows()
```

**변경 내용 — post-settle 블록 (`restore_layout:237`)**

```python
# 변경 전
if post_settle_ms > 0 and matched_pairs:
    logger.info("post-settle: waiting %dms then re-applying %d placement(s)", post_settle_ms, len(matched_pairs))
    time.sleep(post_settle_ms / 1000.0)
    for saved, running in matched_pairs:
        restore_placement(running["hwnd"], saved["placement"])

# 변경 후
if post_settle_ms > 0 and matched_pairs:
    logger.info("post-settle: waiting %dms then re-applying %d placement(s)", post_settle_ms, len(matched_pairs))
    time.sleep(post_settle_ms / 1000.0)
    for saved, running in matched_pairs:
        restore_placement(running["hwnd"], saved["placement"])

if post_launch_settle_ms > 0 and launched_count > 0 and matched_pairs:
    logger.info(
        "post-launch-settle: %d app(s) were launched — waiting %dms then re-applying %d placement(s)",
        launched_count, post_launch_settle_ms, len(matched_pairs),
    )
    time.sleep(post_launch_settle_ms / 1000.0)
    for saved, running in matched_pairs:
        restore_placement(running["hwnd"], saved["placement"])
```

**완료 조건:**
- `post_launch_settle_ms=0`(기본값) → 기존 동작 완전 보존
- `post_launch_settle_ms>0` AND `launched_count>0` → 2차 재적용 실행
- `launched_count==0`(모두 실행 중) → `post_launch_settle_ms` 무시

---

### M3: GUI에서 `post_launch_settle_ms=5000` 전달 (`src/gui.py`)

**변경 위치:** `src/gui.py:253` `_on_restore._work` 내부

```python
# 변경 전
result = restore_mod.restore_layout(layout, monitors_current=self._current_monitors or None)

# 변경 후
result = restore_mod.restore_layout(
    layout,
    monitors_current=self._current_monitors or None,
    post_launch_settle_ms=5000,
)
```

**근거:**
- Chrome profile 복원은 창 표시 후 최대 ~8s까지 지속
- `stabilize_ms=1500ms` + `post_settle_ms=2000ms` 후 추가 5000ms 대기
- 2차 재적용 시점: t ≈ 1.5 + 2 + 5 = 8.5s (앱 fight-back 종료 이후)
- 이후 앱 자체 복원이 완료됐으므로 `restore_placement`가 안정적으로 성공

**완료 조건:** `_on_restore`가 `post_launch_settle_ms=5000`을 전달

---

### M4: 단위 테스트 추가

**파일:** `tests/test_launcher.py` (기존 파일에 추가)

#### UT-L1: `ensure_apps_running` 반환값=0 (모두 실행 중)

```python
def test_ensure_apps_running_returns_zero_when_all_running(monkeypatch):
    """모든 앱이 이미 실행 중 → 0 반환."""
    windows = [{"exe_path": "C:\\app.exe", "title_snapshot": "App Window"}]
    monkeypatch.setattr("src.launcher.list_current_windows", lambda: windows)

    from src.launcher import ensure_apps_running
    result = ensure_apps_running([_saved_window(exe_path="C:\\app.exe", title_pattern="App")])
    assert result == 0
```

#### UT-L2: `ensure_apps_running` 반환값=N (N개 론칭)

```python
def test_ensure_apps_running_returns_count_of_launched(monkeypatch):
    """2개 앱 모두 없음 → 2회 론칭, 반환값 2."""
    monkeypatch.setattr("src.launcher.list_current_windows", lambda: [])

    launched = []

    def fake_launch(exe, *a, **kw):
        launched.append(exe)
        return MagicMock()

    monkeypatch.setattr("src.launcher.launch_app", fake_launch)
    monkeypatch.setattr("src.launcher.wait_for_window", lambda *a, **kw: True)

    from src.launcher import ensure_apps_running
    result = ensure_apps_running([
        _saved_window(exe_path="C:\\a.exe", title_pattern=""),
        _saved_window(exe_path="C:\\b.exe", title_pattern=""),
    ])
    assert result == 2
    assert len(launched) == 2
```

**파일:** `tests/test_restore_matching.py` (기존 파일에 추가)

`mock_layout_deps` fixture에 `ensure_apps_running` 반환값 설정 필요. 기존 fixture:

```python
launcher_mod.ensure_apps_running = MagicMock()
```

→ 기존 UT-4, UT-13, UT-15 테스트는 `launched_count = ensure_apps_running(...)` 이후
`post_launch_settle_ms=0`(기본값)이므로 동작 변화 없음 (기존 테스트 수정 불필요).

#### UT-R1: `post_launch_settle_ms=0` → 2차 재적용 없음

```python
def test_ut19_post_launch_settle_ms_zero_no_second_reapply(monkeypatch):
    """post_launch_settle_ms=0(기본값) → launched_count>0이어도 2차 sleep/재적용 없음."""
    import sys
    from unittest.mock import MagicMock, patch
    import win32gui, win32con

    nr = [10, 20, 800, 600]
    correct_ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])
    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(return_value=(0, 1, (-1, -1), (-1, -1), correct_ltrb))

    _post_settle_env(monkeypatch, sys.modules)

    # ensure_apps_running이 1을 반환 (1개 앱 론칭됨)
    import types
    launcher_mod = types.ModuleType("src.launcher")
    launcher_mod.ensure_apps_running = MagicMock(return_value=1)
    monkeypatch.setitem(sys.modules, "src.launcher", launcher_mod)
    capture_mod = types.ModuleType("src.capture")
    capture_mod.list_current_windows = MagicMock(return_value=_make_running())
    monkeypatch.setitem(sys.modules, "src.capture", capture_mod)

    with patch("time.sleep") as mock_sleep:
        from src.restore import restore_layout
        restore_layout(
            _make_normal_layout(nr),
            post_settle_ms=0,
            post_launch_settle_ms=0,  # 기본값
        )

    mock_sleep.assert_not_called()
    # SetWindowPlacement: 초기 1회만 (2차 재적용 없음)
    assert win32gui.SetWindowPlacement.call_count == 1
```

#### UT-R2: `post_launch_settle_ms>0` AND `launched_count>0` → 2차 재적용

```python
def test_ut20_post_launch_settle_ms_fires_when_apps_launched(monkeypatch):
    """post_launch_settle_ms=3000, launched_count=1 → sleep(3.0) 추가, SetWindowPlacement 3회."""
    import sys
    from unittest.mock import MagicMock, patch
    import win32gui, win32con

    nr = [10, 20, 800, 600]
    correct_ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])
    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(return_value=(0, 1, (-1, -1), (-1, -1), correct_ltrb))

    _post_settle_env(monkeypatch, sys.modules)

    import types
    launcher_mod = types.ModuleType("src.launcher")
    launcher_mod.ensure_apps_running = MagicMock(return_value=1)
    monkeypatch.setitem(sys.modules, "src.launcher", launcher_mod)
    capture_mod = types.ModuleType("src.capture")
    capture_mod.list_current_windows = MagicMock(return_value=_make_running())
    monkeypatch.setitem(sys.modules, "src.capture", capture_mod)

    sleep_calls = []
    with patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):
        from src.restore import restore_layout
        restore_layout(
            _make_normal_layout(nr),
            post_settle_ms=2000,
            post_launch_settle_ms=3000,
        )

    # sleep 호출 확인: stabilize(1.5) + post_settle(2.0) + post_launch(3.0)
    assert 2.0 in sleep_calls
    assert 3.0 in sleep_calls
    # SetWindowPlacement: 초기 1회 + post_settle 1회 + post_launch 1회 = 3회
    assert win32gui.SetWindowPlacement.call_count == 3
```

#### UT-R3: `post_launch_settle_ms>0` AND `launched_count==0` → 2차 재적용 없음

```python
def test_ut21_post_launch_settle_skipped_when_no_apps_launched(monkeypatch):
    """post_launch_settle_ms=3000이지만 launched_count=0 → 2차 재적용 없음."""
    import sys
    from unittest.mock import MagicMock, patch
    import win32gui, win32con

    nr = [10, 20, 800, 600]
    correct_ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])
    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(return_value=(0, 1, (-1, -1), (-1, -1), correct_ltrb))

    _post_settle_env(monkeypatch, sys.modules)

    import types
    launcher_mod = types.ModuleType("src.launcher")
    launcher_mod.ensure_apps_running = MagicMock(return_value=0)  # 모두 실행 중
    monkeypatch.setitem(sys.modules, "src.launcher", launcher_mod)
    capture_mod = types.ModuleType("src.capture")
    capture_mod.list_current_windows = MagicMock(return_value=_make_running())
    monkeypatch.setitem(sys.modules, "src.capture", capture_mod)

    sleep_calls = []
    with patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):
        from src.restore import restore_layout
        restore_layout(
            _make_normal_layout(nr),
            post_settle_ms=2000,
            post_launch_settle_ms=3000,
        )

    # 3.0초 sleep 없음 (post_launch_settle 미발생)
    assert 3.0 not in sleep_calls
    # SetWindowPlacement: 초기 1회 + post_settle 1회 = 2회
    assert win32gui.SetWindowPlacement.call_count == 2
```

**완료 조건:**
```
pytest tests/test_launcher.py tests/test_restore_matching.py -v
```
→ 기존 테스트 전부 + 신규 5개(UT-L1, UT-L2, UT-R1, UT-R2, UT-R3) 모두 PASSED

---

### M5: 전체 단위 테스트 회귀 확인

```bash
python -m pytest tests/ --ignore=tests/integration -v --tb=short
```

**완료 조건:** 기존 127개 + 신규 5개 = 132개 이상 전부 PASSED

---

### M6: 통합 테스트 전체 통과 확인

```bash
python -m pytest tests/integration/ -m integration -v --tb=short
```

**완료 조건:** 10개 전부 PASSED, FAILED 0개

---

## TodoList

- [ ] **M1**: `src/launcher.py` — `ensure_apps_running` 마지막에 `return len(not_running)` 추가, 반환 타입 `-> int`로 변경
- [ ] **M1 검증**: `ensure_apps_running` 반환값이 int임을 Python REPL 또는 임시 print로 확인
- [ ] **M2-A**: `src/restore.py` — `restore_layout` 시그니처에 `post_launch_settle_ms: int = 0` 추가
- [ ] **M2-B**: `src/restore.py` — `ensure_apps_running` 호출을 `launched_count = ensure_apps_running(sorted_saved)`로 변경, `launched_count = 0` 초기화 위치 조정
- [ ] **M2-C**: `src/restore.py` — post-settle 블록 이후에 post-launch-settle 블록 추가 (조건: `post_launch_settle_ms > 0 and launched_count > 0 and matched_pairs`)
- [ ] **M3**: `src/gui.py` — `_on_restore._work` 내 `restore_layout` 호출에 `post_launch_settle_ms=5000` 전달
- [ ] **M4-L1**: `tests/test_launcher.py` — `test_ensure_apps_running_returns_zero_when_all_running` 추가
- [ ] **M4-L2**: `tests/test_launcher.py` — `test_ensure_apps_running_returns_count_of_launched` 추가
- [ ] **M4-R1**: `tests/test_restore_matching.py` — `test_ut19_post_launch_settle_ms_zero_no_second_reapply` 추가
- [ ] **M4-R2**: `tests/test_restore_matching.py` — `test_ut20_post_launch_settle_ms_fires_when_apps_launched` 추가
- [ ] **M4-R3**: `tests/test_restore_matching.py` — `test_ut21_post_launch_settle_skipped_when_no_apps_launched` 추가
- [ ] **M4 검증**: `pytest tests/test_launcher.py tests/test_restore_matching.py -v --tb=short` → 신규 5개 포함 전부 PASSED
- [ ] **M5**: `pytest tests/ --ignore=tests/integration -v --tb=short` → 132개 이상 전부 PASSED
- [ ] **M6**: `pytest tests/integration/ -m integration -v --tb=short` → 10개 전부 PASSED

---

## 주의 사항

- **`post_launch_settle_ms` 기본값은 반드시 `0`** 으로 유지: 기존 통합 테스트(ITC5~ITC9)가
  `restore_layout(layout, stabilize_ms=500)`처럼 파라미터를 명시하지 않는데, 기본값이 0이어야
  기존 테스트 속도와 동작이 보존됨.
- `launched_count` 변수는 `if running_windows is None:` 블록 **밖**에서 `= 0`으로 초기화해야
  `running_windows`를 외부에서 전달받은 경우에도 참조 오류 없이 동작.
- `mock_layout_deps` fixture(`test_restore_matching.py:566`)의 `ensure_apps_running = MagicMock()`은
  기본 반환값이 `MagicMock()` 객체 → truthy int로 인식될 수 있음.
  UT-R1~R3는 별도로 `return_value=0` 또는 `return_value=1`을 지정한 커스텀 모킹 사용 (위 코드 참조).
- GUI에서 `post_launch_settle_ms=5000` 전달 시 새 앱 론칭이 있는 복구는
  총 ≈ 1.5(stabilize) + initial + 2.0(post_settle) + 5.0(post_launch) = **약 8.5초** 소요.
  이 지연은 의도된 것이며, 사용자에게 복구 진행 중임을 log 패널로 확인 가능.

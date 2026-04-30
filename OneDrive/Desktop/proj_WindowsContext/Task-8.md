# Task-8: 창 배치 저장-복원 좌표 불일치 근본 수정

## 현재 증상 (2026-04-27 기준)

- **발생 상황**: 저장 직후 바로 복원해도 일부 창 위치가 저장한 것과 다름 (fight-back 문제와 무관)
- **영향 앱**: Chrome/Edge(Chromium), 일반 Win32 앱 (일부 창만 어긋남, 규칙 미확인)
- **환경**: 멀티모니터, DPI scale 불명 (125% 이상 가능성)

---

## 코드 흐름 전체 분석 (저장 → 복원)

### 저장 경로

```
gui._on_save
  └─ capture.list_current_windows()
       └─ win32gui.GetWindowPlacement(hwnd)
            → placement[4] = rcNormalPosition (LTRB, Windows 내부 좌표계)
            → normal_rect = [L, T, R-L, B-T]  ← XYWH로 변환하여 저장
       └─ JSON 직렬화 → 파일 저장
```

**`capture.py:136-143` 내부:**
```python
placement = win32gui.GetWindowPlacement(hwnd)
ltrb = list(placement[4])                            # [left, top, right, bottom]
normal_rect = [ltrb[0], ltrb[1],
               ltrb[2] - ltrb[0],
               ltrb[3] - ltrb[1]]                   # XYWH
```

### 복원 경로

```
gui._on_restore
  └─ restore_mod.restore_layout(layout, monitors_current=..., post_launch_settle_ms=5000)
       └─ restore_placement(hwnd, saved["placement"])
            ├─ XYWH → LTRB 변환: ltrb = (x, y, x+w, y+h)
            ├─ SetWindowPlacement(hwnd, (0, show_cmd, min_pos, max_pos, ltrb))
            ├─ [normal 상태만] SetWindowPos(hwnd, None, x, y, w, h, flags)
            └─ 검증: GetWindowPlacement 재호출 → _rects_close(actual, nr, tol=10)
```

**`restore.py:92-126` 내부:**
```python
ltrb = (nr[0], nr[1], nr[0]+nr[2], nr[1]+nr[3])

win32gui.SetWindowPlacement(hwnd, (0, show_cmd, min_pos, max_pos, ltrb))

if state == "normal":
    win32gui.SetWindowPos(
        hwnd, None,
        nr[0], nr[1], nr[2], nr[3],
        SWP_NOACTIVATE | SWP_NOZORDER,           # ← SWP_NOSENDCHANGING 없음
    )
    actual = win32gui.GetWindowPlacement(hwnd)
    al = actual[4]
    actual_xywh = [al[0], al[1], al[2]-al[0], al[3]-al[1]]
    if _rects_close(actual_xywh, nr, tol=10):
        return True
```

---

## 의심 버그 목록 (우선순위별)

### B1 [최우선]: `GetWindowPlacement.rcNormalPosition` 좌표계 vs `SetWindowPos` 좌표계 불일치

**근거 (MSDN):**
> "The coordinates of rcNormalPosition are relative to the **upper-left corner of the working area** of the display monitor that the window is primarily on."

즉, `rcNormalPosition`은 **해당 창이 있는 모니터의 work area 기준** 좌표입니다.  
반면 `SetWindowPos(x, y, cx, cy)`는 **가상 화면(virtual screen) 절대 좌표**를 사용합니다.

**결론적 차이:**

| 상황 | rcNormalPosition (work area 기준) | SetWindowPos (screen 기준) |
|------|----------------------------------|---------------------------|
| 주 모니터, 작업표시줄 하단 | x=200, y=100 | x=200, y=100 (같음) |
| 주 모니터, 작업표시줄 상단 40px | x=200, y=100 | x=200, y=140 (다름!) |
| **보조 모니터** (오른쪽 1920,0 위치) | x=200, y=100 (보조 모니터 work area 기준) | x=2120, y=100 (가상 화면 절대) → **완전 불일치!** |

**멀티모니터에서 특히 치명적**: 보조 모니터 창을 저장 시 `rcNormalPosition.x=200`이 저장되지만, 이것은 "보조 모니터 내부 x=200"입니다. 복원 시 `SetWindowPos(x=200, ...)`로 설정하면 주 모니터 x=200에 창이 나타납니다.

**단, Per-Monitor DPI Aware V2 환경에서 이 동작이 변경됐을 수 있습니다.** Phase 0 진단으로 실제 동작을 먼저 확인합니다.

---

### B2 [높음]: `SetWindowPos`에 `SWP_NOSENDCHANGING (0x0400)` 미사용

**근거:**  
`SWP_NOSENDCHANGING`이 없으면 `WM_WINDOWPOSCHANGING` 메시지가 대상 앱에 전달됩니다.  
Chrome/Electron은 이 메시지를 받아 창 크기를 **자신의 기준으로 강제 수정**합니다(최소 크기 제한, 종횡비 보정 등).

**현재 코드:**
```python
SWP_NOACTIVATE = 0x0010
SWP_NOZORDER   = 0x0004
# SWP_NOSENDCHANGING = 0x0400  ← 없음
```

**결과**: 저장된 크기 `[w=1280, h=720]`을 설정해도 Chrome이 `WM_WINDOWPOSCHANGING`에서 `[w=1366, h=768]`로 바꿔버릴 수 있음.

---

### B3 [높음]: `cli/rollback.py`에 DPI Awareness 설정 누락

**근거:**  
`main.py`에는 아래 코드가 있음:
```python
ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_V2
```

`cli/rollback.py`에는 **없음**. Task Scheduler로 자동 복원 시 DPI Unaware 프로세스로 실행되어 좌표가 가상화(96 DPI 기준으로 스케일다운)됩니다.

**결과**: 자동 복원 경로에서만 좌표 불일치 발생. DPI 125% 환경에서 `x=200`이 `x=160`으로 스케일다운되어 저장/복원됨.

---

### B4 [중간]: `SetWindowPlacement` + `SetWindowPos` 이중 호출에서 좌표 불일치

**문제**: `SetWindowPlacement`으로 `rcNormalPosition`을 설정하고, 이어서 `SetWindowPos`로 같은 좌표를 다시 설정합니다.  
B1에서 설명한 좌표계 차이로 인해 `SetWindowPlacement`는 올바른 work area 기준 좌표를 설정하지만, `SetWindowPos`가 screen 기준으로 덮어쓰면서 위치가 밀릴 수 있습니다.

---

### B5 [낮음]: 저장 시 fight-back 중인 앱의 좌표 읽기

**문제**: 저장 버튼 클릭 시점에 UWP 앱이 자체 위치 복원(fight-back) 중이면, `GetWindowPlacement`가 fight-back 진행 중의 중간값을 저장할 수 있음.

**영향**: 저장된 좌표가 실제 사용자가 의도한 위치와 다름. 하지만 이것은 저장 타이밍의 문제이며 UX 개선 범위입니다.

---

## 수정 계획

### Phase 0: 진단 — 실제 좌표 불일치 지점 특정 (코드 미수정, 로그 분석)

**목적**: B1(rcNormalPosition 좌표계)이 실제 멀티모니터 환경에서 문제를 일으키는지 확인.  
`restore_placement`에 임시 진단 로그를 추가하여 각 단계의 좌표를 기록합니다.

**추가할 로그 (`src/restore.py:restore_placement` 함수 내)**:
```python
# 진단용 — 저장값 vs SetWindowPlacement 전 현재 창 위치
pre_placement = win32gui.GetWindowPlacement(hwnd)
logger.debug(
    "DIAG hwnd=0x%x  saved_nr=%s  pre_ltrb=%s",
    hwnd, nr, list(pre_placement[4]) if pre_placement else None
)

win32gui.SetWindowPlacement(hwnd, ...)
post_swp_ltrb = win32gui.GetWindowPlacement(hwnd)
logger.debug(
    "DIAG hwnd=0x%x  after_SetWindowPlacement=%s",
    hwnd, list(post_swp_ltrb[4]) if post_swp_ltrb else None
)

win32gui.SetWindowPos(hwnd, None, nr[0], nr[1], nr[2], nr[3], flags)
post_swpos_ltrb = win32gui.GetWindowPlacement(hwnd)
logger.debug(
    "DIAG hwnd=0x%x  after_SetWindowPos=%s  expected_xywh=%s",
    hwnd, list(post_swpos_ltrb[4]) if post_swpos_ltrb else None, nr
)
```

**분석 기준**:
- `after_SetWindowPlacement` ≠ `expected_xywh` → B1(좌표계 불일치) 또는 B4 확인
- `after_SetWindowPos` ≠ `expected_xywh` → B2(WM_WINDOWPOSCHANGING) 또는 B1 확인
- `after_SetWindowPos` == `expected_xywh` 이지만 실제 화면 위치가 다름 → rcNormalPosition 좌표계 자체 문제

---

### M1: `rcNormalPosition` 좌표계 정규화 (B1 수정)

**위치**: `src/restore.py` `restore_placement` 함수

**전략**: `SetWindowPos`에 전달하는 좌표를 virtual screen 기준으로 변환합니다.  
`GetWindowPlacement`의 `rcNormalPosition`이 work area 기준일 경우, 해당 창의 모니터 work area origin과 screen origin의 delta를 보정합니다.

**구현**:

`src/restore.py`에 보조 함수 추가:
```python
def _workarea_to_screen(nr: list, hwnd: int) -> list:
    """
    GetWindowPlacement.rcNormalPosition (work area 기준) →
    SetWindowPos용 screen 좌표로 변환.
    work area origin과 screen origin의 delta를 보정.
    """
    import ctypes

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                    ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

    try:
        # 창이 있는 모니터 확인
        ltrb_rect = RECT(nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])
        hmonitor = ctypes.windll.user32.MonitorFromRect(
            ctypes.byref(ltrb_rect), 2  # MONITOR_DEFAULTTONEAREST
        )
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(mi))

        # screen origin (모니터 전체 영역 시작점)
        screen_origin_x = mi.rcMonitor.left
        screen_origin_y = mi.rcMonitor.top
        # work area origin (작업표시줄 제외 영역 시작점)
        work_origin_x = mi.rcWork.left
        work_origin_y = mi.rcWork.top

        # delta = screen_origin - work_origin
        # rcNormalPosition이 work area 기준이면 이 delta를 더해야 screen 좌표가 됨
        delta_x = screen_origin_x - work_origin_x
        delta_y = screen_origin_y - work_origin_y

        return [nr[0] + delta_x, nr[1] + delta_y, nr[2], nr[3]]
    except Exception as e:
        logger.debug("_workarea_to_screen failed: %s", e)
        return nr  # 변환 실패 시 원본 반환
```

**주의**: Phase 0 진단 결과 `rcNormalPosition`이 이미 screen 좌표를 반환한다면 (Per-Monitor DPI Aware V2 환경), delta가 0이므로 이 함수는 무해합니다.

`restore_placement` 내 `SetWindowPos` 호출부 수정:
```python
# 변경 전
win32gui.SetWindowPos(hwnd, None, nr[0], nr[1], nr[2], nr[3], SWP_NOACTIVATE | SWP_NOZORDER)

# 변경 후
screen_nr = _workarea_to_screen(nr, hwnd)
win32gui.SetWindowPos(hwnd, None,
                      screen_nr[0], screen_nr[1], screen_nr[2], screen_nr[3],
                      SWP_NOACTIVATE | SWP_NOZORDER | SWP_NOSENDCHANGING)
```

---

### M2: `SWP_NOSENDCHANGING` 추가 (B2 수정)

**위치**: `src/restore.py` `restore_placement` 함수

```python
# 변경 전
SWP_NOACTIVATE = 0x0010
SWP_NOZORDER   = 0x0004

# 변경 후
SWP_NOACTIVATE      = 0x0010
SWP_NOZORDER        = 0x0004
SWP_NOSENDCHANGING  = 0x0400   # ← 추가: WM_WINDOWPOSCHANGING 억제
```

`SetWindowPos` 호출 시 `SWP_NOSENDCHANGING` 포함 (M1과 함께 적용).

---

### M3: `cli/rollback.py`에 DPI Awareness 추가 (B3 수정)

**위치**: `cli/rollback.py` 상단 (다른 import 이전)

```python
# 변경 전 (없음)

# 변경 후 (추가)
import ctypes
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(
        ctypes.c_void_p(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    )
except Exception:
    pass
```

**완료 조건**: `rollback.py`가 DPI awareness 설정 후 나머지 import를 실행.

---

### M4: 멀티모니터 — 보조 모니터 창 좌표 복원 보정

**위치**: `src/restore.py` `restore_layout` 함수

**배경**: B1의 `_workarea_to_screen` 변환이 단일 모니터에서는 충분하지만, 멀티모니터에서 창의 `monitor_index`가 저장 시와 복원 시 다른 모니터를 가리킬 수 있습니다. `monitor_gate` 로직이 이미 `PRIMARY_ONLY` / `NO_MATCH` 상황을 처리하지만, `FULL_MATCH` 상황에서도 보조 모니터의 work area delta를 보정해야 합니다.

**이 수정은 M1이 충분히 해결하는지 Phase 0 진단 후 결정합니다.**  
M1만으로 해결되면 M4는 불필요합니다.

---

### M5: 저장 시 `GetWindowRect`와 `GetWindowPlacement` 교차 검증 로그 추가 (진단 보조)

**위치**: `src/capture.py` `list_current_windows` 함수

normal 상태 창에 대해 `GetWindowRect`와 `GetWindowPlacement.rcNormalPosition`을 비교하여 차이가 큰 경우 WARNING 로그:

```python
if state == "normal":
    rect_ltrb = win32gui.GetWindowRect(hwnd)
    swp_ltrb = ltrb  # GetWindowPlacement에서 온 값
    diff = max(abs(a - b) for a, b in zip(rect_ltrb, swp_ltrb))
    if diff > 15:
        logger.warning(
            "hwnd=0x%x GetWindowRect=%s vs rcNormalPosition=%s diff=%d",
            hwnd, list(rect_ltrb), swp_ltrb, diff
        )
```

이 로그로 어떤 앱이 두 API 간 차이를 보이는지 파악합니다.

---

## 단위 테스트 계획

**파일**: `tests/test_restore_matching.py`

### UT-A1: `_workarea_to_screen` — work area = screen (delta=0) 경우

```python
def test_workarea_to_screen_no_delta(monkeypatch):
    """
    작업표시줄 하단, 주 모니터에서는 delta=0 → 입력값 그대로 반환.
    """
    # GetMonitorInfoW mock: rcMonitor.left=0, top=0 / rcWork.left=0, top=0 → delta=0
    ...
    from src.restore import _workarea_to_screen
    result = _workarea_to_screen([100, 200, 800, 600], hwnd=1)
    assert result == [100, 200, 800, 600]
```

### UT-A2: `_workarea_to_screen` — 작업표시줄 상단(40px) 경우

```python
def test_workarea_to_screen_taskbar_top(monkeypatch):
    """
    작업표시줄이 상단 40px에 있으면 rcWork.top=40, rcMonitor.top=0
    → delta_y = 0 - 40 = -40
    → 입력 y=100이면 출력 y=60
    """
    ...
    result = _workarea_to_screen([100, 100, 800, 600], hwnd=1)
    assert result == [100, 60, 800, 600]
```

### UT-A3: `_workarea_to_screen` — 보조 모니터 (screen origin != work origin)

```python
def test_workarea_to_screen_secondary_monitor(monkeypatch):
    """
    보조 모니터: rcMonitor=(1920,0,3840,1080), rcWork=(1920,0,3840,1040) (하단 작업표시줄)
    → delta_x=0, delta_y=0 → 변환 없음
    보조 모니터가 자체 work area를 가지더라도 screen 기준 좌표를 올바르게 반환하는지 검증.
    """
    ...
```

### UT-A4: `restore_placement` — `SWP_NOSENDCHANGING` 포함 호출 확인

```python
def test_restore_placement_includes_swp_nosendchanging(monkeypatch):
    """SetWindowPos 호출 시 SWP_NOSENDCHANGING(0x0400) 플래그가 포함되는지 검증."""
    import win32gui, win32con

    calls = []
    win32gui.SetWindowPos = lambda hwnd, ins, x, y, cx, cy, flags: calls.append(flags)
    # ... (기존 mock 설정)

    from src.restore import restore_placement
    restore_placement(1, {"state": "normal", "normal_rect": [100,100,800,600],
                          "min_pos":[-1,-1], "max_pos":[-1,-1]})

    assert calls, "SetWindowPos가 호출되지 않음"
    assert calls[0] & 0x0400, "SWP_NOSENDCHANGING(0x0400) 플래그 없음"
```

### UT-A5: `_workarea_to_screen` 실패 시 원본 반환

```python
def test_workarea_to_screen_fallback_on_exception(monkeypatch):
    """GetMonitorInfoW 실패 시 원본 nr을 그대로 반환해야 함."""
    # ctypes 호출이 예외를 발생시키도록 monkeypatch
    ...
    result = _workarea_to_screen([100, 200, 800, 600], hwnd=1)
    assert result == [100, 200, 800, 600]
```

---

## 통합 테스트 계획

**파일**: `tests/integration/test_restore_real.py`

### ITC8 수정: corner position 테스트

현재 ITC8 실패 원인: `time.sleep(0.3)` 후 읽어서 UWP Notepad fight-back 위치가 저장됨.  
→ `time.sleep(0.3)` → `time.sleep(2.0)` 또는 fight-back 안정화 후 위치 읽기로 수정.

```python
# 변경 전
time.sleep(0.3)

# 변경 후 (UWP fight-back 안정화 대기)
time.sleep(2.0)
```

또한 검증 시 `captured_rect` (실제 저장된 값)와 `actual_rect`를 비교하도록 수정:
```python
# 변경 전 (target과 비교 → UWP fight-back 위치가 다를 수 있음)
assert _rects_close(actual_rect, target, tol=20)

# 변경 후 (실제 저장된 좌표와 비교)
assert _rects_close(actual_rect, captured_rect, tol=20)
```

### ITC11 (신규): 멀티모니터 — 보조 모니터 창 복원

```
@pytest.mark.integration
def test_itc11_secondary_monitor_position_restored():
    """
    보조 모니터에 Notepad를 배치하고 저장 후, 종료-복원 시
    보조 모니터의 올바른 위치에 복원되는지 검증.
    보조 모니터가 없는 환경에서는 skip.
    """
    from src.monitors import list_current_monitors
    monitors = list_current_monitors()
    if len(monitors) < 2:
        pytest.skip("멀티모니터 환경 필요")
    ...
```

---

## 검증 명령어

### M1~M3 수정 후 단위 테스트
```bash
pytest tests/test_restore_matching.py -v --tb=short -k "workarea or nosendchanging"
```

### 전체 단위 테스트 회귀
```bash
python -m pytest tests/ --ignore=tests/integration -v --tb=short
```
**완료 조건**: 기존 132개 + 신규 5개 = 137개 이상 PASSED

### 통합 테스트
```bash
python -m pytest tests/integration/ -m integration -v --tb=short
```
**완료 조건**: ITC8 수정 포함 10개 PASSED (ITC11은 멀티모니터 환경에서만)

---

## 주의 사항

1. **Phase 0 진단 결과 우선**: `_workarea_to_screen` 변환이 필요한지 여부는 반드시 진단 로그 확인 후 결정. Per-Monitor DPI Aware V2 환경에서는 `rcNormalPosition`이 이미 screen 좌표를 반환할 수 있으므로, 변환이 오히려 좌표를 망가뜨릴 수 있음.

2. **`_workarea_to_screen` 안전 장치**: 변환 함수는 반드시 실패 시 원본 값을 반환해야 함 (B5 안전성).

3. **`SWP_NOSENDCHANGING`은 부작용 없음**: `WM_WINDOWPOSCHANGING`을 억제하는 것이 일부 앱의 정상 동작을 방해할 수 있으나, 저장된 위치로의 복원이 목적이므로 허용.

4. **M4는 조건부 진행**: M1 적용 후 멀티모니터 좌표 불일치가 해결되면 M4는 구현하지 않음.

5. **ITC8 수정의 목적**: `target` 대신 `captured_rect`를 기준으로 검증 → 실제로 저장된 좌표와 복원된 좌표의 일치 여부를 측정.

---

## TodoList

- [ ] **Phase 0**: `src/restore.py` `restore_placement`에 진단 로그(DIAG) 임시 추가
- [ ] **Phase 0**: 실제 앱(Chrome, Win32 앱)에서 저장-복원 실행 → 로그에서 `saved_nr` vs `after_SetWindowPlacement` vs `after_SetWindowPos` 좌표 비교
- [ ] **Phase 0**: `src/capture.py`에 `GetWindowRect` vs `rcNormalPosition` 비교 로그 추가
- [ ] **Phase 0 분석**: 진단 로그 결과를 바탕으로 B1(좌표계 불일치) 실제 여부 확정
- [ ] **M1**: `src/restore.py`에 `_workarea_to_screen(nr, hwnd)` 함수 추가
- [ ] **M1**: `restore_placement`의 `SetWindowPos` 호출부를 `screen_nr = _workarea_to_screen(nr, hwnd)` 결과로 수정
- [ ] **M2**: `restore_placement`에 `SWP_NOSENDCHANGING = 0x0400` 상수 추가 및 `SetWindowPos` flags에 포함
- [ ] **M3**: `cli/rollback.py` 상단에 DPI awareness 설정 코드 추가 (`main.py`와 동일)
- [ ] **M4**: Phase 0 분석 결과에 따라 멀티모니터 좌표 변환 추가 여부 결정 (필요시 구현)
- [ ] **M5**: `src/capture.py`에 `GetWindowRect` vs `rcNormalPosition` 비교 경고 로그 추가
- [ ] **UT-A1**: `tests/test_restore_matching.py`에 `_workarea_to_screen` delta=0 단위 테스트 추가
- [ ] **UT-A2**: `_workarea_to_screen` 작업표시줄 상단 경우 단위 테스트 추가
- [ ] **UT-A3**: `_workarea_to_screen` 보조 모니터 경우 단위 테스트 추가
- [ ] **UT-A4**: `restore_placement` `SWP_NOSENDCHANGING` 포함 검증 단위 테스트 추가
- [ ] **UT-A5**: `_workarea_to_screen` 예외 fallback 단위 테스트 추가
- [ ] **ITC8 수정**: `time.sleep(0.3)` → `time.sleep(2.0)`, 검증 기준을 `target` → `captured_rect`로 변경
- [ ] **ITC11 추가**: 멀티모니터 환경에서 보조 모니터 창 복원 통합 테스트 추가 (멀티모니터 미존재 시 pytest.skip)
- [ ] **단위 테스트 검증**: `pytest tests/ --ignore=tests/integration -v --tb=short` → 137개 이상 PASSED
- [ ] **통합 테스트 검증**: `pytest tests/integration/ -m integration -v --tb=short` → ITC8 포함 PASSED
- [ ] **Phase 0 진단 로그 제거**: 수정 완료 후 `restore.py`, `capture.py`에서 DIAG 로그 제거

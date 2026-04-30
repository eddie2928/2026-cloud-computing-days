# Task-5: 창 배치 복구 부정확 근본 원인 수정

## 문제 요약

Task-4에서 앱 실행(Chrome 재기동) 문제는 해결되었으나, 복구 후 창의 위치·크기가 저장 시점과 다른 문제가 남아있다.
현재 `restore_placement`는 `SetWindowPlacement` + `SetWindowPos` 호출 후 예외가 없으면 무조건 `True`를 반환하므로, 앱이 그 직후 위치를 덮어써도 성공으로 보고한다.
통합 테스트 ITC3/ITC4도 "Chrome 창이 존재하는가"만 검증하고 실제 위치 정확도는 검증하지 않는다.

---

## 근본 원인 분석

### 원인 1 (PRIMARY): `restore_placement` 에 사후 위치 검증 없음

**파일**: `src/restore.py:64–112`

`restore_placement`는 `SetWindowPlacement` + `SetWindowPos` 호출 후 `OSError`가 없으면 `True`를 반환한다. 실제로 창이 원하는 위치에 있는지 확인하지 않는다.

Chrome/Electron 계열 앱은 `WM_WINDOWPOSCHANGED` 처리 중 자체 세션 상태를 복원하며 우리가 지정한 위치를 덮어쓴다. 현재 코드는 이를 탐지하지 못한다.

결과: `restore_placement` 가 `True`를 반환해도 창 위치가 틀릴 수 있다.

---

### 원인 2 (PRIMARY): 앱 실행 직후 배치 시도 — 초기화 경쟁 조건

**파일**: `src/restore.py:166–171`, `src/launcher.py:55–83`

`wait_for_window`는 창이 **처음 나타나는 순간** `True`를 반환한다. 그러나 Chrome 같은 앱은 창이 보이기 시작한 뒤에도 세션 복원·탭 로드·자체 창 위치 복구를 수행한다. `restore_layout` 은 `wait_for_window` 반환 즉시 `list_current_windows()` → `match_windows` → `restore_placement`를 수행하므로, `SetWindowPos` 호출이 앱 초기화 도중 실행된다. 앱이 초기화를 마치면 자체 저장된 위치로 창을 이동시켜 우리 설정을 덮어쓴다.

```
타임라인 (버그):
t=0   launch_app(chrome.exe)
t=2s  wait_for_window 반환 — "New Tab" 창 첫 등장
t=2s  list_current_windows()  →  hwnd=X, rect=[0,0,800,600] (Chrome 초기 기본 위치)
t=2s  restore_placement(X, saved_rect=[300,200,1200,900])  ← SetWindowPlacement 성공
t=3s  Chrome 세션 복원 완료 → 자체 저장된 위치 [0,0,800,600]으로 덮어씀
→ 결과: 창이 [0,0,800,600]에 있음 (복구 실패)
```

---

### 원인 3 (SECONDARY): `SetWindowPos` 호출 순서 — LTRB 재계산 없이 XYWH 직접 전달

**파일**: `src/restore.py:99–106`

```python
# 현재 코드 (restore.py:99–106)
win32gui.SetWindowPos(
    hwnd, None,
    nr[0], nr[1], nr[2], nr[3],   # nr = [x, y, w, h]
    SWP_NOACTIVATE | SWP_NOZORDER,
)
```

`SetWindowPos`의 5번째·6번째 인자는 `cx`(폭), `cy`(높이)이므로 `nr[2]`, `nr[3]`이 width, height인 XYWH 형식과 일치한다. 이 계산 자체는 올바르다.

그러나 `SWP_NOSIZE` 플래그가 없으므로 크기도 함께 지정된다. 현재는 의도적으로 크기까지 지정하는 코드이므로 로직 버그는 아니다. 다만 `SetWindowPlacement` 가 상태(최소화/최대화/보통)를 바꾼 직후 `SetWindowPos`로 좌표를 재지정하는 구조가 일부 앱에서 불안정할 수 있다.

---

### 원인 4 (TEST GAP): ITC3·ITC4 가 위치 정확도를 검증하지 않음

**파일**: `tests/integration/test_restore_real.py:153–233`

ITC3·ITC4는 복구 후 "Chrome 창이 최소 1개 존재하는가"만 확인한다. 창의 위치·크기가 저장된 값과 일치하는지 검증하지 않아, 위치 복구 버그가 통합 테스트에서도 탐지되지 않는다.

---

### 원인 5 (TEST GAP): "앱 종료 후 복구 → 위치 정확도" 통합 테스트 부재

ITC1·ITC2는 이미 실행 중인 Notepad 창을 이동한 뒤 복구하는 시나리오로, `running_windows` 인자를 외부에서 전달한다. "앱을 완전히 종료 → restore_layout 호출 → 앱이 재기동되며 올바른 위치에 복구되는가"를 검증하는 테스트가 없다.

---

## 수정 전략 개요

| 번호 | 수정 대상 | 수정 내용 |
|------|-----------|-----------|
| Fix-A | `src/restore.py::restore_placement` | `GetWindowPlacement` 로 실제 위치 검증, 불일치 시 재시도(최대 3회, 각 200 ms 대기) |
| Fix-B | `src/restore.py::restore_layout` | `ensure_apps_running` 이후 안정화 대기(기본 1 500 ms) 추가 |
| Fix-C | `tests/integration/test_restore_real.py` | ITC3·ITC4 에 위치 정확도 assert 추가 |
| Fix-D | `tests/integration/test_restore_real.py` | ITC5 추가: Notepad 종료 후 복구 → 위치 정확도 검증 |

---

## 상세 수정 계획

### Fix-A: `restore_placement` — 위치 검증 및 재시도

**파일**: `src/restore.py`  
**함수**: `restore_placement(hwnd, placement)`

#### 변경 전 (현재 구조)

```python
def restore_placement(hwnd: int, placement: dict) -> bool:
    ...
    win32gui.SetWindowPlacement(hwnd, (...))
    if state == "normal":
        win32gui.SetWindowPos(hwnd, None, nr[0], nr[1], nr[2], nr[3], flags)
    logger.info("placed hwnd=0x%x state=%s rect=%s", hwnd, state, nr)
    return True   # ← 예외만 없으면 무조건 True
```

#### 변경 후 (재시도 포함)

```python
def restore_placement(hwnd: int, placement: dict, retries: int = 3, retry_delay_ms: int = 200) -> bool:
    ...
    for attempt in range(1, retries + 1):
        win32gui.SetWindowPlacement(hwnd, (0, show_cmd, min_pos, max_pos, ltrb))
        if state == "normal":
            win32gui.SetWindowPos(hwnd, None, nr[0], nr[1], nr[2], nr[3], SWP_NOACTIVATE | SWP_NOZORDER)

        # 사후 검증: 실제 위치를 읽어서 저장 값과 비교 (state == "normal" 일 때만)
        if state == "normal":
            actual = win32gui.GetWindowPlacement(hwnd)
            if actual and len(actual) > 4:
                actual_ltrb = actual[4]
                actual_xywh = [actual_ltrb[0], actual_ltrb[1],
                               actual_ltrb[2] - actual_ltrb[0],
                               actual_ltrb[3] - actual_ltrb[1]]
                if _rects_close(actual_xywh, nr, tol=10):
                    logger.info("placed hwnd=0x%x state=%s rect=%s (attempt %d)", hwnd, state, nr, attempt)
                    return True
                logger.warning(
                    "placement verify failed hwnd=0x%x attempt=%d: wanted=%s got=%s",
                    hwnd, attempt, nr, actual_xywh
                )
                if attempt < retries:
                    time.sleep(retry_delay_ms / 1000.0)
                    continue
                return False   # 재시도 소진
        else:
            # minimized/maximized: 위치보다 상태(showCmd)가 중요 — SetWindowPlacement 예외 없으면 성공
            logger.info("placed hwnd=0x%x state=%s (attempt %d)", hwnd, state, attempt)
            return True
    return False
```

`_rects_close` 헬퍼 (같은 파일 내 추가):

```python
def _rects_close(r1: list, r2: list, tol: int = 10) -> bool:
    """r1, r2 모두 [x, y, w, h] 형식. 각 요소가 tol 이내이면 True."""
    return len(r1) == 4 and len(r2) == 4 and all(abs(a - b) <= tol for a, b in zip(r1, r2))
```

**설계 결정**:
- `retries=3`, `retry_delay_ms=200`: 총 최대 600 ms 대기. Chrome 세션 복원은 보통 1–2 s 이상이므로 이 재시도만으로는 완전 해결이 안 될 수 있음. Fix-B의 안정화 대기와 함께 적용하면 대부분의 경우 커버됨.
- `maximized`/`minimized` 상태는 "화면을 꽉 채우거나 최소화"가 목표이므로 위치 픽셀 비교 불필요. `SetWindowPlacement` 성공 시 즉시 반환.
- `tol=10`: 단일 픽셀 오차가 아닌 10 px 이내를 허용. DPI 반올림 오차·창 테두리 두께 등 허용 오차.

---

### Fix-B: `restore_layout` — 앱 초기화 안정화 대기

**파일**: `src/restore.py`  
**함수**: `restore_layout`  
**수정 위치**: line 166–171 (`if running_windows is None:` 블록)

#### 변경 전

```python
if running_windows is None:
    from src.launcher import ensure_apps_running
    from src.capture import list_current_windows
    running_windows = list_current_windows()
    ensure_apps_running(sorted_saved)
    running_windows = list_current_windows()  # re-scan after launch
```

#### 변경 후

```python
if running_windows is None:
    from src.launcher import ensure_apps_running
    from src.capture import list_current_windows
    running_windows = list_current_windows()
    ensure_apps_running(sorted_saved)
    time.sleep(stabilize_ms / 1000.0)     # 앱 초기화 완료 대기
    running_windows = list_current_windows()  # re-scan after launch
```

`restore_layout` 시그니처에 `stabilize_ms: int = 1500` 파라미터 추가:

```python
def restore_layout(
    layout: dict,
    running_windows: list[dict] = None,
    monitors_current: list[dict] = None,
    stabilize_ms: int = 1500,           # ← 추가
) -> dict:
```

**설계 결정**:
- `stabilize_ms=1500`: 1.5 s 기본값. Chrome 세션 복원이 보통 1–3 s 이므로 1.5 s 후 배치 시도. Fix-A 재시도(최대 600 ms)와 합산하면 총 2.1 s.
- `stabilize_ms` 인자를 노출해 통합 테스트에서 작은 값(예: 300 ms)으로 오버라이드 가능하게 함. 단위 테스트는 `stabilize_ms=0`으로 호출해 `time.sleep`을 건너뜀.
- `running_windows is not None` 경로(CLI, ITC1/ITC2처럼 외부 스캔 결과를 전달하는 경우)에는 앱이 이미 실행 중이므로 안정화 대기 불필요. 이 경로는 변경하지 않는다.

---

### Fix-C: ITC3·ITC4 — 위치 정확도 assert 추가

**파일**: `tests/integration/test_restore_real.py`

#### ITC3 (`test_itc3_chrome_killed_and_restored`) 변경

기존: Chrome 창 존재 여부(`len(chrome_windows) >= 1`)만 검증.  
추가: Chrome 창의 실제 `placement.normal_rect` 가 저장된 값과 `_rects_close(tol=30)` 이내인지 검증.

```python
# 추가할 코드 (기존 assert 이후)
chrome_win = chrome_windows[0]
actual_rect = chrome_win["placement"]["normal_rect"]
saved_rect  = w["placement"]["normal_rect"]
assert _rects_close(actual_rect, saved_rect, tol=30), \
    f"ITC3: position mismatch — saved={saved_rect}, actual={actual_rect}"
```

**주의**: Chrome을 `--new-window`로 실행하면 Chrome이 자체 저장 위치를 무시하고 기본 위치에 열리는 경우가 있음. Fix-B의 안정화 대기가 적용된 뒤에야 이 assert가 안정적으로 통과됨.

#### ITC4 (`test_itc4_chrome_background_only_then_restored`) 변경

동일하게 위치 정확도 assert 추가. ITC4는 pytest.skip 분기가 있으므로 skip 이후 경로에만 추가.

---

### Fix-D: ITC5~ITC9 추가 — 앱 종료 후 복구 시나리오 전방위 검증

**파일**: `tests/integration/test_restore_real.py`  
**위치**: ITC4 이후에 추가  
**공통 헬퍼**: `_rects_close`는 ITC1에서 이미 정의됨. 통합 테스트 파일 내에서 그대로 재사용.

---

#### ITC5: Notepad 종료 후 복구 — 중간 위치 정확도 검증

```
목적: 앱 종료 → restore_layout(running_windows 미전달) → 재기동 → 저장된 위치로 복구.
시나리오:
  1. Notepad 실행, [200, 150, 700, 500]으로 이동
  2. 이동 후 위치를 captured_rect로 캡처 → layout 생성
  3. Notepad 완전 종료
  4. restore_layout(layout, stabilize_ms=500) 호출
  5. 복구된 Notepad 창의 normal_rect 가 captured_rect와 tol=20 이내인지 검증
검증:
  - result["restored"] == 1
  - Notepad 창이 존재함
  - actual_rect vs captured_rect: _rects_close(tol=20)
```

---

#### ITC6: Notepad 최대화 상태 종료 후 복구 — 최대화 상태 재현

```
목적: 최대화된 창을 저장 → 종료 → 복구 후에도 최대화 상태로 나타나야 함.
시나리오:
  1. Notepad 실행, win32gui.ShowWindow(hwnd, SW_MAXIMIZE) 호출
  2. 잠시 대기 후 list_current_windows()로 상태 캡처
  3. 캡처된 state가 "maximized"인지 assert
  4. Notepad 완전 종료
  5. restore_layout(layout, stabilize_ms=500) 호출
  6. 복구 후 Notepad GetWindowPlacement[1] == SW_SHOWMAXIMIZED 인지 검증
검증:
  - result["restored"] == 1
  - win32gui.GetWindowPlacement(hwnd)[1] == win32con.SW_SHOWMAXIMIZED
```

---

#### ITC7: Notepad 2개 창 종료 후 복구 — 각 창이 올바른 위치로 복구

```
목적: 서로 다른 위치의 2개 Notepad 창을 모두 종료 후 복구해도 각각의 위치가 정확히 재현됨.
시나리오:
  1. Notepad 2개 실행, 각각 [100,100,600,400], [750,300,600,400]으로 이동
  2. 이동 후 각 창 캡처 → layout 생성
  3. 모든 Notepad 완전 종료
  4. restore_layout(layout, stabilize_ms=500) 호출
  5. 복구 후 2개 창이 모두 나타나는지 확인
  6. 각 창의 위치가 저장된 두 rect 중 하나와 tol=20 이내인지 검증
     (title이 동일해 매칭 순서가 바뀔 수 있으므로 "둘 중 하나" 검증)
검증:
  - result["restored"] == 2
  - 각 hwnd의 actual_rect가 expected_positions 중 하나와 _rects_close(tol=20)
```

---

#### ITC8: Notepad 화면 모서리(0, 0 근방) 위치에서 종료 후 복구

```
목적: 극단적으로 작은 좌표(화면 좌상단 모서리) 위치도 정확히 복구됨.
시나리오:
  1. Notepad 실행, [5, 5, 500, 400]으로 이동 (left=5, top=5)
  2. 캡처 → layout 생성
  3. 완전 종료 → 복구(stabilize_ms=500)
  4. 복구 후 위치가 [5,5,500,400]에 tol=20 이내인지 검증
검증:
  - result["restored"] == 1
  - _rects_close(actual, [5,5,500,400], tol=20)
```

---

#### ITC9: 동일 레이아웃 연속 2회 복구 — 멱등성(idempotency) 검증

```
목적: restore_layout을 동일 layout으로 2회 연속 호출해도 두 번째에도 올바른 위치로 복구됨.
시나리오:
  1. Notepad 실행, [200,200,700,500]으로 이동, 캡처 → layout 생성
  2. Notepad 완전 종료
  3. 1차 restore_layout(layout, stabilize_ms=500)
  4. 1차 복구 결과 검증 (position check)
  5. Notepad 재종료
  6. 2차 restore_layout(layout, stabilize_ms=500)
  7. 2차 복구 결과 검증 (같은 위치인지 확인)
검증:
  - 1차: result["restored"] == 1, actual_rect tol=20 이내
  - 2차: result["restored"] == 1, actual_rect tol=20 이내 (동일 기준)
```

---

#### ITC3 변경 (위치 검증 추가)

기존 assert 이후 아래 코드 추가:

```python
chrome_win = chrome_windows[0]
actual_rect = chrome_win["placement"]["normal_rect"]
saved_rect  = w["placement"]["normal_rect"]
assert _rects_close(actual_rect, saved_rect, tol=30), \
    f"ITC3: position mismatch — saved={saved_rect}, actual={actual_rect}"
```

**주의**: Chrome은 자체 세션 복원이 있어 tol=30 px 허용. Fix-A(재시도)와 Fix-B(stabilize)가 모두 적용된 후에야 안정적으로 통과.

---

#### ITC4 변경 (위치 검증 추가)

ITC3과 동일 패턴으로 pytest.skip 분기 이후 경로에 위치 검증 추가.

---

## 단위 테스트 추가 계획

모든 테스트는 `tests/test_restore_matching.py`에 추가한다.

---

### A. `restore_placement` — 재시도 동작

#### UT-1: 1차 시도 검증 실패 → 2차 시도 성공 → True 반환

```
목적: 앱이 첫 SetWindowPlacement 후 위치를 덮어써도 두 번째 시도에서 성공하면 True 반환.
설정: GetWindowPlacement mock — 1회 호출 시 틀린 위치, 2회 호출 시 맞는 위치.
검증: True 반환, SetWindowPlacement 2회 호출.
```

#### UT-2: 모든 재시도(retries=3) 소진 → False 반환

```
목적: 앱이 매번 위치를 덮어쓰면 retries 소진 후 False 반환.
설정: GetWindowPlacement mock — 항상 틀린 위치.
검증: False 반환, SetWindowPlacement 정확히 3회 호출.
```

#### UT-5: retries=1 → 단 한 번 시도, 실패 시 즉시 False

```
목적: retries=1 파라미터가 재시도 없이 1회만 시도함을 확인.
설정: GetWindowPlacement mock — 틀린 위치. retries=1로 호출.
검증: False 반환, SetWindowPlacement 1회만 호출.
```

#### UT-6: 첫 시도에서 즉시 성공 → 재시도 없이 True 반환

```
목적: 성공 즉시 루프를 빠져나와 불필요한 재시도가 없음을 확인.
설정: GetWindowPlacement mock — 첫 호출부터 맞는 위치.
검증: True 반환, SetWindowPlacement 1회만 호출.
```

#### UT-7: 검증 중 GetWindowPlacement가 짧은 튜플 반환 → 실패로 처리 후 재시도

```
목적: GetWindowPlacement가 비정상 반환값(len<5)을 줄 때 crash 없이 재시도함.
설정: GetWindowPlacement mock — (0,) 반환 (len=1).
검증: False 반환(소진), SetWindowPlacement retries회 호출, 예외 미발생.
```

#### UT-8: 검증 중 GetWindowPlacement가 OSError → 실패 처리 후 재시도

```
목적: 검증 단계에서 OSError가 나도 crash 없이 재시도하고 최종 False 반환.
설정: GetWindowPlacement mock — OSError 발생.
검증: False 반환, 예외가 호출자까지 전파되지 않음.
```

#### UT-9: state="maximized" → 위치 검증 없이 즉시 True 반환

```
목적: maximized 상태는 SetWindowPlacement 성공만으로 True 반환(GetWindowPlacement 미호출).
설정: SetWindowPlacement mock. state="maximized".
검증: True 반환, GetWindowPlacement 미호출.
```

#### UT-10: state="minimized" → 위치 검증 없이 즉시 True 반환

```
목적: minimized 상태도 GetWindowPlacement 미호출.
설정: SetWindowPlacement mock. state="minimized".
검증: True 반환, GetWindowPlacement 미호출.
```

#### UT-11: normal_rect에 음수 좌표(멀티모니터 왼쪽) → 정상 복구

```
목적: x=-1920 같은 음수 좌표가 포함된 normal_rect도 정상 처리.
설정: normal_rect=[-1920, 100, 800, 600], GetWindowPlacement mock — 같은 값 반환.
검증: True 반환, SetWindowPos가 x=-1920으로 호출됨.
```

---

### B. `_rects_close` — 경계값 및 엣지 케이스

#### UT-3a: 완전 일치(delta=0) → True

```
r1=[100,200,800,600], r2=[100,200,800,600], tol=0 → True
```

#### UT-3b: 모든 요소가 tol과 정확히 같음 → True (경계 포함)

```
r1=[100,200,800,600], r2=[110,210,810,610], tol=10 → True
```

#### UT-3c: 한 요소가 tol을 1 초과 → False

```
r1=[100,200,800,600], r2=[111,200,800,600], tol=10 → False
```

#### UT-3d: 음수 좌표 포함 → 차이 계산 정확

```
r1=[-1920,0,800,600], r2=[-1915,5,795,595], tol=10 → True
r1=[-1920,0,800,600], r2=[-1905,0,800,600], tol=10 → False (delta=15)
```

#### UT-3e: 리스트 길이가 4 미만 → False

```
r1=[100,200,800], r2=[100,200,800,600], tol=10 → False
```

#### UT-3f: 4K 좌표(큰 값) → 정상 비교

```
r1=[3840,2160,3840,2160], r2=[3842,2162,3838,2158], tol=5 → True
```

---

### C. `restore_layout` — stabilize_ms 동작

#### UT-4: `stabilize_ms=0` → `time.sleep` 미호출

```
목적: stabilize_ms=0으로 슬립을 완전히 건너뜀(단위 테스트 속도 보장).
설정: time.sleep mock, restore_layout(layout, stabilize_ms=0) 호출.
검증: time.sleep(0.0) 또는 아예 미호출.
```

#### UT-13: `stabilize_ms=500` → `time.sleep(0.5)` 호출

```
목적: 지정한 ms가 초 단위로 변환되어 sleep에 전달됨.
설정: time.sleep mock, restore_layout(layout, stabilize_ms=500).
검증: time.sleep(0.5) 호출됨.
```

#### UT-14: `running_windows` 를 외부에서 전달 시 → sleep 미호출 (stabilize_ms 무시)

```
목적: ensure_apps_running을 건너뛰는 경로에서는 안정화 대기도 실행되지 않음.
설정: time.sleep mock, restore_layout(layout, running_windows=[...], stabilize_ms=1500).
검증: time.sleep 미호출.
```

#### UT-15: `stabilize_ms` 미전달(기본값 1500) → `time.sleep(1.5)` 호출

```
목적: 기본값 1500ms가 실제로 적용됨을 확인.
설정: time.sleep mock, restore_layout(layout) 호출 (stabilize_ms 생략).
검증: time.sleep(1.5) 호출됨.
```

---

## 작업 순서

### Step 1. UT-1~UT-15 작성 (수정 전 FAIL 확인)

파일: `tests/test_restore_matching.py`  
수정 전 실행: `pytest tests/test_restore_matching.py -k "retry or rects_close or stabilize" -v`  
→ 15개 모두 FAIL (아직 `retries` 파라미터, `_rects_close`, `stabilize_ms` 미존재)

---

### Step 2. Fix-A 구현 — `restore_placement` 재시도

파일: `src/restore.py`

추가 사항:
1. `_rects_close(r1, r2, tol)` 헬퍼 함수 추가 (모듈 상단 `import time` 아래)
2. `restore_placement` 시그니처에 `retries=3`, `retry_delay_ms=200` 추가
3. for 루프로 재시도 구조 변경 (상세 내용: 상세 수정 계획 Fix-A 참조)

수정 후 실행: `pytest tests/test_restore_matching.py -v`  
→ 기존 테스트 + UT-1~UT-3 전체 PASS

---

### Step 3. Fix-B 구현 — `restore_layout` 안정화 대기

파일: `src/restore.py`

추가 사항:
1. `restore_layout` 시그니처에 `stabilize_ms: int = 1500` 추가
2. `ensure_apps_running` 이후 `time.sleep(stabilize_ms / 1000.0)` 추가

수정 후 실행: `pytest tests/test_restore_matching.py tests/test_launcher.py -v`  
→ 기존 테스트 + UT-4 전체 PASS

---

### Step 4. Fix-C 구현 — ITC3·ITC4 위치 assert 추가

파일: `tests/integration/test_restore_real.py`  
변경 내용: ITC3·ITC4에 위치 정확도 assert 추가 (상세 내용: Fix-C 참조)

---

### Step 5. Fix-D 구현 — ITC5~ITC9 추가

파일: `tests/integration/test_restore_real.py`  
변경 내용:
- `test_itc5_notepad_killed_and_restored_position`
- `test_itc6_notepad_maximized_killed_and_restored`
- `test_itc7_two_notepad_windows_killed_and_restored`
- `test_itc8_notepad_corner_position_restored`
- `test_itc9_restore_idempotent_two_runs`

(상세 내용: Fix-D 참조)

---

### Step 6. 전체 단위 테스트 실행

```
pytest tests/ --ignore=tests/integration -v
```

기존 104개 + UT-1~UT-15 = **119개 PASS** 이어야 한다.

---

### Step 7. 통합 테스트 실행

```
pytest -m integration tests/integration/ -v
```

ITC1~ITC9 = **9개 PASS** 이어야 한다.  
(ITC3·ITC4는 Chrome 미설치 시 skip — 정상)

---

### Step 8. 수동 라이브 테스트

Chrome 기준:

1. `python main.py` 실행
2. Chrome 열기 → 특정 위치·크기로 창 배치
3. "Save" 클릭
4. Chrome 완전 종료 (트레이 아이콘 포함)
5. "Restore" 클릭
6. 확인:
   - Chrome 창이 저장된 위치와 크기(±30px 이내)로 복구됨
   - 로그에 "placement verify failed" 경고가 없거나 최대 2회 후 성공 로그 출력

---

## 검증 기준 (완료 조건)

### 단위 테스트 (UT)

- [ ] UT-1: `restore_placement` 2차 시도에서 성공 → True 반환, SetWindowPlacement 2회 호출
- [ ] UT-2: 재시도(3회) 모두 실패 → False 반환, SetWindowPlacement 3회 호출
- [ ] UT-5: retries=1, 첫 시도 실패 → False, 1회만 호출
- [ ] UT-6: 첫 시도 즉시 성공 → True, 1회만 호출
- [ ] UT-7: GetWindowPlacement 짧은 튜플 반환 → crash 없이 False
- [ ] UT-8: GetWindowPlacement OSError → crash 없이 False
- [ ] UT-9: maximized → GetWindowPlacement 미호출, True
- [ ] UT-10: minimized → GetWindowPlacement 미호출, True
- [ ] UT-11: 음수 좌표 normal_rect → 정상 처리, True
- [ ] UT-3a~3f: `_rects_close` 6가지 경계값 케이스 모두 정확
- [ ] UT-4: stabilize_ms=0 → sleep 미호출
- [ ] UT-13: stabilize_ms=500 → sleep(0.5) 호출
- [ ] UT-14: running_windows 전달 시 → sleep 미호출
- [ ] UT-15: stabilize_ms 생략(기본값) → sleep(1.5) 호출
- [ ] `pytest tests/ --ignore=tests/integration -v` → **119개 전체 PASS**

### 통합 테스트 (ITC)

- [ ] ITC1: Notepad 이동 후 복구 → 위치 일치 (기존, 회귀 없음)
- [ ] ITC2: Notepad 2창 이동 후 복구 → 각 위치 일치 (기존, 회귀 없음)
- [ ] ITC3: Chrome 종료 후 복구 → 창 존재 + 위치 tol=30 이내 (위치 assert 추가됨)
- [ ] ITC4: Chrome 백그라운드 후 복구 → 창 존재 + 위치 tol=30 이내 (위치 assert 추가됨)
- [ ] ITC5: Notepad 종료 후 복구 → 지정 위치에서 tol=20 이내
- [ ] ITC6: Notepad 최대화 후 종료 → 복구 후 최대화 상태
- [ ] ITC7: Notepad 2창 종료 후 복구 → 각 창이 저장된 위치 중 하나와 tol=20 이내
- [ ] ITC8: 화면 모서리(x=5,y=5) 위치 종료 후 복구 → tol=20 이내
- [ ] ITC9: 동일 레이아웃 2회 연속 복구 → 두 번 모두 tol=20 이내 (멱등성)
- [ ] `pytest -m integration tests/integration/ -v` → **9개 PASS** (ITC3·ITC4는 Chrome 미설치 시 skip)

### 수동 라이브 테스트

- [ ] Chrome 복구 후 위치가 저장 위치와 육안으로 일치
- [ ] 로그에 "placement verify failed" 경고가 없거나 최대 2회 후 성공 로그 출력

---

## 수정하지 않는 것 (범위 외)

- `ensure_apps_running` 중복 실행 문제 (Task-4 원인 3) — 별도 Task로 이미 분리됨
- DPI 스케일링 처리 — 현재 `GetWindowPlacement`/`SetWindowPlacement` 쌍은 DPI 일관성이 있으므로 이 Task 범위에서는 별도 수정 없음
- `rollback.py` — 변경 없음
- `stabilize_ms` GUI 설정 노출 — UI 변경은 범위 외
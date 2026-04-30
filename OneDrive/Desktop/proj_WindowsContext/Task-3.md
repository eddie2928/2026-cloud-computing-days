# Task-3: Chrome 복구 실패 버그 수정

## 문제 요약

Chrome이 꺼진 상태에서 복구를 시도하면 아래 WARN이 반복적으로 출력된다.

```
WARN  restore : no candidate for '새 탭 - Chrome' (exe=C:\Program Files\Google\Chrome\Application\chrome.exe)
```

---

## 근본 원인 분석

### 발생 위치

`src/restore.py` → `match_windows()` (line 56–60)

```
no candidate → score_window이 모든 running window에 대해 0을 반환했음을 의미
```

### 원인: `is_running` 이 창 유무가 아닌 프로세스 유무를 검사한다

`src/launcher.py` `ensure_apps_running()` (line 95–97):

```python
not_running = [
    w for w in saved_windows
    if w.get("exe_path") and not is_running(w["exe_path"])
]
```

`is_running`은 `psutil.process_iter`로 **프로세스 존재** 만 확인한다. Chrome은 창을 모두 닫아도 **백그라운드 프로세스(`chrome.exe`)** 가 남아 있다. 따라서:

1. `is_running("chrome.exe")` → `True` (백그라운드 프로세스 있음)
2. `ensure_apps_running` → Chrome 실행 **건너뜀**
3. `list_current_windows()` 재스캔 → Chrome **창 없음** (백그라운드 프로세스에는 visible window가 없음)
4. `match_windows` → score 0 → **"no candidate"** WARN

### 보조 원인: 타이밍 문제 (secondary)

Chrome이 진짜로 꺼져 있더라도, `wait_for_window`가 임시 초기화 창(타이틀 없음 또는 다른 타이틀)을 감지한 직후 `list_current_windows()` 재스캔 시 창이 사라져 있으면 동일 WARN 발생 가능.

---

## 수정 전략

### 핵심 수정: `ensure_apps_running`의 판별 기준 변경

| 현재 | 수정 후 |
|---|---|
| `not is_running(exe_path)` | `not has_visible_window(exe_path, title_pattern)` |

- `has_visible_window(exe_path, title_pattern)` = `list_current_windows()` 결과 중 exe_path가 일치하고 title_pattern이 매칭되는 창이 하나라도 있으면 `True`
- Chrome이 백그라운드 프로세스만 있고 창이 없으면 → `has_visible_window = False` → 실행 시도
- Chrome에 `chrome.exe --new-window` 식으로 이미 실행 중인 프로세스에 새 창을 여는 것은 Chrome이 자체 처리함 (이미 실행 중인 Chrome에 `chrome.exe`를 재실행해도 새 창이 열림)

### 수정 파일

- `src/launcher.py`: `has_visible_window()` 함수 추가, `ensure_apps_running`에서 `is_running` 대신 사용

---

## 작업 순서

### Step 0. 라이브 테스트로 현상 재현 (수정 전)

목적: 버그 재현 로그 확보, 실제 동작 확인

```
python main.py 실행 → 아래 순서대로 진행
```

**Test Case A — Chrome 포함 Screen 저장 후 Chrome 닫고 복구**

1. Chrome 열기 (예: 새 탭, 네이버)
2. `python main.py` 실행
3. "Save" → 레이아웃명 `screen1_chrome` 저장
4. Chrome 창 완전히 닫기 (작업 표시줄에서도 닫기)
5. "Restore" → `screen1_chrome` 선택 → 복구 실행
6. 로그 확인: `no candidate for ... Chrome` WARN 있으면 버그 재현 성공

**Test Case B — Chrome 없는 Screen 저장 후 복구 (기준선)**

1. Chrome 닫은 상태에서 저장
2. 다른 창만 있는 상태에서 복구
3. Chrome WARN이 없어야 함 (정상 기준선)

**Test Case C — Chrome 2개 창 저장 후 복구**

1. Chrome 창 2개 열기 (예: 새 탭, YouTube)
2. 저장 → 이름 `screen1_chrome2`
3. Chrome 전부 닫기
4. 복구 → 두 창이 모두 복구되는지 확인

### Step 1. 로그 분석

위 테스트 실행 후 로그에서 확인할 것:

- `ensure_apps_running` 호출 시 `not_running` 목록에 Chrome이 포함되는지
- `wait_for_window` 가 Chrome 창을 찾는지
- 두 번째 `list_current_windows()` 스캔에서 Chrome 창이 잡히는지
- `match_windows` 단계에서 Chrome에 score가 부여되는지

### Step 2. 코드 수정

`src/launcher.py`:

1. `has_visible_window(exe_path: str, title_pattern: str) -> bool` 함수 추가
   - `list_current_windows()` 호출
   - exe_path(대소문자 무시) 매칭 + title_pattern regex 매칭 창이 있으면 `True`
   - title_pattern이 비어 있으면 exe_path 일치만으로 `True`

2. `ensure_apps_running()` 수정
   - `not is_running(w["exe_path"])` → `not has_visible_window(w["exe_path"], w.get("title_pattern", ""))`

### Step 3. 수정 후 라이브 테스트

Step 0의 Test Case A, B, C 동일하게 재실행하여 아래를 확인:

- Test Case A: WARN 없음, Chrome 창이 복구됨 (위치/상태 포함)
- Test Case B: 변화 없음 (기존 정상 동작 유지)
- Test Case C: Chrome 창 2개 모두 복구됨

### Step 4. 단위 테스트 코드 추가

`tests/test_launcher.py` 수정 (mock 기반, pywin32 불필요):

- 기존 `test_ensure_apps_running_launches_missing`는 `psutil.process_iter` mock 기반으로 작성되어 있어 `has_visible_window` 로직을 검증할 수 없음 → **TC4/TC5로 대체(삭제)**

**TC1. `has_visible_window` — Chrome 백그라운드 프로세스만 있고 창 없음 → False**
- `list_current_windows` 반환값 = `[]`
- `has_visible_window("chrome.exe", "Chrome$")` → `False`

**TC2. `has_visible_window` — Chrome 창 있음 → True**
- `list_current_windows` 반환값 = Chrome 창 포함 목록
- `has_visible_window("chrome.exe", "Chrome$")` → `True`

**TC3. `has_visible_window` — exe 일치하지 않음 → False**
- 실행 중인 창은 notepad.exe 뿐
- `has_visible_window("chrome.exe", "Chrome$")` → `False`

**TC4. `ensure_apps_running` — 창 없음 → launch_app 호출됨**
- `src.launcher.list_current_windows` mock = [] (창 없음)
- `src.launcher.wait_for_window` mock = True
- `ensure_apps_running([chrome_saved_window])` 호출
- `launch_app`이 chrome.exe로 **호출됐음을 assert**

**TC5. `ensure_apps_running` — Chrome 창 이미 있음 → launch_app 호출 안 됨**
- `src.launcher.list_current_windows` mock = Chrome 창 있음
- `ensure_apps_running([chrome_saved_window])` 호출
- `launch_app`이 **호출되지 않았음을 assert**

**TC6. `restore_layout` 통합 — Chrome 백그라운드 있고 창 없을 때 복구 성공**
- 기존 `test_restore_layout_launches_missing_app_then_rematch`와 동일한 방식: `src.launcher.ensure_apps_running` 전체를 `fake_ensure`로 mock
- 첫 스캔 Chrome 창 없음 → `ensure_apps_running` 호출됨 → 두 번째 스캔 Chrome 창 있음
- `result["restored"] == 1` assert

---

### Step 5. 통합 테스트 코드 추가 (`@pytest.mark.integration`)

파일: `tests/integration/test_restore_real.py`

GUI(`main.py`)는 사용하지 않고 core 함수를 직접 호출한다.
`pytest -m integration` 으로만 실행 (CI 제외, 로컬 전용).

#### 준비

`tests/integration/__init__.py` (빈 파일)  
`pytest.ini` 또는 `pyproject.toml`에 마커 등록:
```
[pytest]
markers =
    integration: real Windows API, requires desktop environment
```

#### ITC1. Notepad 창 저장 → 위치 이동 → 복구 → 위치 검증

목적: 가장 단순한 앱으로 restore_layout의 실제 동작 검증

```
흐름:
  subprocess.Popen(["notepad.exe"]) → 창 대기
  list_current_windows() → notepad 창 캡처
  layout 구성 (저장된 rect 기록)
  win32gui.SetWindowPos() 로 창을 다른 위치로 이동 (망가뜨리기)
  restore_layout(layout, running_windows=list_current_windows())
  win32gui.GetWindowPlacement() 로 실제 위치 확인
  assert: 복구된 rect ≈ 저장된 rect (±20px 허용)
  notepad 종료
```

#### ITC2. Notepad 2개 창 저장 → 복구 → 각각 위치 검증

목적: 동일 exe 다중 창이 올바르게 매칭되는지 검증

```
흐름:
  notepad 2개 실행 (각각 다른 위치)
  list_current_windows() → 두 창 캡처
  layout 구성
  두 창 모두 위치 이동
  restore_layout()
  각 hwnd의 GetWindowPlacement() 검증
  두 창 모두 종료
```

#### ITC3. Chrome 창 저장 → Chrome 프로세스 kill → 복구 → Chrome 창 존재 확인

목적: 백그라운드 프로세스 포함 Chrome 재실행 시나리오 검증

```
조건: Chrome이 설치되어 있을 때만 실행
  @pytest.mark.skipif(not chrome_installed(), reason="Chrome not installed")

흐름:
  subprocess.Popen(["chrome.exe", "--new-window"])
  Chrome 창 대기 (최대 15초)
  list_current_windows() → chrome 창 캡처
  layout 구성 (rect, title_snapshot 등)
  subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"]) → 완전 종료
  time.sleep(2)  → 프로세스 정리 대기
  restore_layout(layout)  → 내부에서 Chrome 재실행
  time.sleep(5)  → Chrome 재실행 대기
  list_current_windows() → chrome 창 존재 확인
  assert: chrome.exe 창이 1개 이상 있음
  assert: WARN 로그에 "no candidate" 없음 (log capture로 확인)
```

#### ITC4. Chrome 창 저장 → Chrome 백그라운드만 남긴 상태 → 복구 → Chrome 창 존재 확인

목적: **핵심 버그 재현 케이스** — 프로세스는 있지만 창이 없는 상태

```
조건: Chrome 설치 필요

흐름:
  Chrome 실행 → 창 캡처 → layout 구성
  Chrome 창만 닫기 (프로세스는 남김):
    win32gui.PostMessage(hwnd, WM_CLOSE, 0, 0) 로 창만 닫기
  time.sleep(2)
  # 이 시점: chrome.exe 프로세스는 있지만 visible 창 없음 (버그 트리거 조건)
  restore_layout(layout)
  time.sleep(5)
  list_current_windows() → chrome 창 확인
  assert: chrome.exe 창이 1개 이상 있음
  assert: 로그에 "no candidate" 없음
```


---

## 검증 기준 (완료 조건)

- [ ] `python main.py` → Chrome 포함 레이아웃 저장 → Chrome 닫기 → 복구 → WARN 없음
- [ ] Chrome 창이 원래 위치/크기/상태로 복구됨
- [ ] `pytest tests/` 전체 통과 (단위 테스트 TC1~TC6)
- [ ] `pytest -m integration tests/integration/` 전체 통과 (ITC1~ITC4)
- [ ] 기존 Test Case B (Chrome 없는 레이아웃) 동작 변화 없음

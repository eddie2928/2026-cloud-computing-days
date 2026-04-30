# Task-4: Chrome 복구 실패 근본 원인 수정

## 문제 요약

Chrome이 닫힌 상태에서 GUI에서 "Restore"를 누르면 Chrome이 실행되지 않는다.
단위 테스트(TC4)는 통과하므로 코드가 고쳐졌다고 오해할 수 있으나, 테스트가 GUI 실제 호출 경로를 검증하지 않기 때문이다.

---

## 근본 원인 분석

### 원인 1 (PRIMARY): `gui.py`가 `running_windows`를 전달 → `ensure_apps_running` 호출 누락

`gui.py:250–260` (`_on_restore` 스레드):

```python
running = capture.list_current_windows()       # line 253: 사전 스캔
result = restore_mod.restore_layout(           # line 254
    layout, running,                           # ← running_windows 에 값이 전달됨
    monitors_current=self._current_monitors or None
)
```

`restore.py:166–171` (`restore_layout` 내부):

```python
if running_windows is None:                    # line 166: False — 값이 있으므로 블록 전체 스킵
    from src.launcher import ensure_apps_running
    from src.capture import list_current_windows
    running_windows = list_current_windows()
    ensure_apps_running(sorted_saved)          # ← 이 줄이 실행되지 않음
    running_windows = list_current_windows()
```

결과:
- `ensure_apps_running` 미호출 → Chrome 재실행 없음
- `match_windows(sorted_saved, running_windows)` — `running_windows`는 Chrome 없는 사전 스캔 결과
- Chrome에 대해 score 0 → `None` 반환 → "no candidate" WARN → `failed += 1`

**참고: `cli/rollback.py`는 우연히 정상 동작**

```python
# rollback.py:64–73
launcher.ensure_apps_running(...)              # 명시적으로 먼저 호출
running = capture.list_current_windows()      # 재실행 후 재스캔
result = restore_mod.restore_layout(layout, running, ...)  # 포스트 스캔 결과 전달
```

CLI는 `ensure_apps_running`을 `restore_layout` 외부에서 호출한 뒤, 포스트 스캔 결과를 전달하기 때문에 정상이다. GUI는 이 단계가 없다.

---

### 원인 2 (TEST GAP): 단위 테스트가 GUI 호출 경로를 검증하지 않음

기존 `test_restore_layout_launches_missing_app_then_rematch` (test_launcher.py):

```python
result = restore_layout(layout)   # running_windows 없음 → if None 블록 실행 → 통과
```

GUI는 `restore_layout(layout, running, ...)` 형태로 호출한다. 이 경로를 커버하는 테스트가 없어 버그가 탐지되지 않는다.

---

### 원인 3 (SECONDARY): `ensure_apps_running`이 같은 exe_path를 N회 실행

저장된 창 중 동일 exe_path(예: chrome.exe)가 N개이면, `not_running` 리스트에 같은 exe_path가 N번 포함되어 `launch_app`이 N회 호출된다.

```python
# launcher.py:109–111
not_running = [
    w for w in saved_windows
    if w.get("exe_path") and not has_visible_window(w["exe_path"], w.get("title_pattern", ""))
]
```

Chrome은 단일 인스턴스 구조이므로 두 번째 `launch_app` 호출은 새 창을 열거나 무시된다. Notepad처럼 호출당 1개 창을 여는 앱은 N회 호출로 N개 창이 열린다. 현재 보고된 버그(Chrome 1개 창)의 직접 원인은 아니지만 2개 이상 Chrome 창 저장 시 의도치 않은 동작을 유발한다.

---

## 수정 전략

### 수정 1: `gui.py::_on_restore` — 사전 스캔 제거, `restore_layout` 인자 정리

**수정 파일**: `src/gui.py`  
**수정 위치**: `_on_restore` 내부 `_work` 함수 (line 250–259)

Before:
```python
def _work():
    try:
        layout = storage.load_layout(name)
        running = capture.list_current_windows()
        result = restore_mod.restore_layout(layout, running, monitors_current=self._current_monitors or None)
        ...
```

After:
```python
def _work():
    try:
        layout = storage.load_layout(name)
        result = restore_mod.restore_layout(layout, monitors_current=self._current_monitors or None)
        ...
```

- `running = capture.list_current_windows()` 줄 삭제
- `restore_layout`에서 `running` 인자 제거
- `restore_layout`이 내부에서 `list_current_windows()` → `ensure_apps_running()` → `list_current_windows()` 순서로 자체 처리
- `rollback.py`는 수정하지 않는다 (기존 패턴 유지)

---

### 수정 2: `ensure_apps_running` — 동일 exe_path 중복 실행 방지

**수정 파일**: `src/launcher.py`  
**수정 위치**: `ensure_apps_running` 함수 내 for 루프 (line 120–133)

문제: `not_running`에 같은 exe_path가 N개 포함될 때 `launch_app`이 N회 호출됨.

수정 방식: `for` 루프 안에서 이미 `launch_app`을 호출한 exe_path는 skip. `wait_for_window`는 exe_path 기준으로 대기하므로 첫 번째 launch 이후 두 번째 saved window에 대해서는 wait만 수행하면 충분하다.

Before (line 120–133):
```python
for saved in not_running:
    exe_path = saved.get("exe_path", "")
    exe_args = saved.get("exe_args", "")
    cwd = saved.get("cwd", "")
    is_uwp = saved.get("is_uwp", False)
    title_pattern = saved.get("title_pattern", "")

    proc = launch_app(exe_path, exe_args, cwd, is_uwp)
    if proc is None:
        continue

    found = wait_for_window(exe_path, title_pattern, timeout_seconds, poll_ms)
    if not found:
        logger.warning("giving up on '%s' — window did not appear in %.0fs", exe_path, timeout_seconds)
```

After:
```python
launched_exes: set[str] = set()

for saved in not_running:
    exe_path = saved.get("exe_path", "")
    exe_args = saved.get("exe_args", "")
    cwd = saved.get("cwd", "")
    is_uwp = saved.get("is_uwp", False)
    title_pattern = saved.get("title_pattern", "")

    exe_key = exe_path.lower()
    if exe_key not in launched_exes:
        proc = launch_app(exe_path, exe_args, cwd, is_uwp)
        if proc is None:
            continue
        launched_exes.add(exe_key)

    found = wait_for_window(exe_path, title_pattern, timeout_seconds, poll_ms)
    if not found:
        logger.warning("giving up on '%s' — window did not appear in %.0fs", exe_path, timeout_seconds)
```

**동작 설명**:
- Notepad처럼 실행당 1창인 앱: 각 saved window마다 별도 실행 → N창 열림. 그러나 같은 exe_path에 대해 첫 번째 이후 `launch_app` 미호출. 이는 기존 동작 변경임.
  
  > **설계 결정**: Notepad N창 복구 시 N번 실행하는 것이 맞다. 이 수정은 Chrome처럼 단일 인스턴스 앱에만 중복 방지 효과가 있다. 따라서 아래 대안을 검토할 것:
  > - **대안 A** (현 수정안): exe_path당 1회만 `launch_app`, wait는 saved 창 수만큼. 단점: Notepad 2창 복구 시 1창만 열림.
  > - **대안 B**: `launch_app` 중복 허용(현행 유지), 단 `wait_for_window` 후 다시 `has_visible_window`로 재확인하여 필요한 경우만 재실행. 복잡도 증가.
  > - **대안 C**: 이 수정을 Task-4에서 제외하고 Task-5로 분리.
  >
  > Task-4에서는 **대안 C** 선택: 원인 3은 수정하지 않고 원인 1(gui.py), 원인 2(테스트 갭)만 수정한다.

---

## 작업 순서

### Step 1. 버그 재현 단위 테스트 추가 (수정 전 — FAIL 확인)

**파일**: `tests/test_launcher.py`  
**위치**: `test_restore_layout_launches_missing_app_then_rematch` 바로 아래에 추가

추가할 테스트 이름: `test_restore_layout_with_prescan_skips_ensure_bug`

```
목적: GUI 경로(running_windows를 미리 전달)에서 ensure_apps_running이 호출되지 않음을 재현한다.
수정 전에는 이 테스트가 FAIL해야 한다.
수정 후에는 PASS해야 한다.
```

테스트 구조 (의사 코드, 실제 코드는 Step 3에서 확정):
```
win32 stub 설정 (기존 테스트와 동일 방식)

scan_count = {"n": 0}
def fake_list_current():
    scan_count["n"] += 1
    # 두 번째 스캔에서 Chrome 반환 (ensure_apps_running 이후 재스캔 시뮬레이션)
    if scan_count["n"] >= 2:
        return [chrome_running_window]
    return []

launched = []
def fake_ensure(saved_windows, **kwargs):
    for w in saved_windows:
        if w.get("exe_path"):
            launched.append(w["exe_path"])

mock src.capture.list_current_windows = fake_list_current
mock src.launcher.ensure_apps_running = fake_ensure

# GUI처럼: 사전 스캔 결과(Chrome 없음)를 running_windows로 전달
pre_scan = []   # Chrome 없음 (GUI 사전 스캔 결과 시뮬레이션)
result = restore_layout(layout, running_windows=pre_scan)

assert "C:\\chrome.exe" in launched, "ensure_apps_running이 호출되지 않았음 — GUI 버그 재현"
assert result["restored"] == 1
```

**수정 전 실행**: `pytest tests/test_launcher.py::test_restore_layout_with_prescan_skips_ensure_bug -v`  
→ `assert "C:\\chrome.exe" in launched` 에서 FAIL 이어야 한다. (launched == [])

---

### Step 2. `gui.py` 수정

**파일**: `src/gui.py`  
**수정 내용**: 수정 1에 기술된 대로 `_work` 함수에서 사전 스캔 줄과 `running_windows` 인자를 제거.

수정 후 diff (의도):
```diff
  def _work():
      try:
          layout = storage.load_layout(name)
-         running = capture.list_current_windows()
-         result = restore_mod.restore_layout(layout, running, monitors_current=self._current_monitors or None)
+         result = restore_mod.restore_layout(layout, monitors_current=self._current_monitors or None)
          self.after(0, lambda: self._status_var.set(
```

---

### Step 3. 단위 테스트 확정 및 실행

Step 1에서 작성한 `test_restore_layout_with_prescan_skips_ensure_bug`가 수정 후 PASS하는지 확인.

추가로 아래 기존 테스트들이 여전히 통과하는지 확인:
- `test_restore_layout_launches_missing_app_then_rematch` (running_windows=None 경로)
- TC1~TC5 (has_visible_window, ensure_apps_running)

**실행 명령**:
```
pytest tests/ --ignore=tests/integration -v
```

전체 103개 + 신규 1개 = **104개 PASS** 이어야 한다.

---

### Step 4. 통합 테스트 실행

ITC1~ITC4 재실행으로 회귀 없음 확인.

ITC1, ITC2: `running_windows`를 외부에서 전달하고 있어 `ensure_apps_running`이 스킵된다. 이는 해당 테스트에서는 앱이 이미 실행 중이므로 기능에 문제가 없다. 단, 테스트 설계 일관성을 위해 `running_windows=running` 인자를 제거하고 `restore_layout(layout, monitors_current=None)` 형태로 변경하는 것을 권장한다 (선택 사항).

**실행 명령**:
```
pytest -m integration tests/integration/ -v
```

→ 4개 PASS 이어야 한다.

---

### Step 5. 수동 라이브 테스트

GUI를 통한 실제 동작 검증:

1. `python main.py` 실행
2. Chrome 열기 (새 탭)
3. "Save" → 레이아웃 저장
4. Chrome 완전히 닫기 (트레이 아이콘 포함 종료)
5. "Restore" 클릭
6. 확인:
   - Chrome이 자동으로 실행되어야 함
   - 로그에 "no candidate" WARN이 없어야 함
   - 복구 후 위치가 저장된 위치와 유사해야 함

---

## 검증 기준 (완료 조건)

- [ ] `test_restore_layout_with_prescan_skips_ensure_bug` — 수정 전 FAIL, 수정 후 PASS
- [ ] `pytest tests/ --ignore=tests/integration` → 104개 전체 PASS
- [ ] `pytest -m integration tests/integration/` → 4개 전체 PASS
- [ ] 수동 테스트: Chrome 닫힌 상태에서 복구 시 Chrome이 자동 실행됨
- [ ] 수동 테스트: 복구 후 로그에 "no candidate" WARN 없음
- [ ] `rollback.py` 동작 변화 없음 (수정 범위 외)

---

## 수정하지 않는 것 (범위 외)

- `ensure_apps_running` 중복 실행 문제 (원인 3) — 별도 Task로 분리
- `rollback.py` — 기존 동작이 올바르므로 수정 없음
- `restore_layout`의 `running_windows` 파라미터 시그니처 — 제거하지 않음 (CLI 하위 호환성 유지)

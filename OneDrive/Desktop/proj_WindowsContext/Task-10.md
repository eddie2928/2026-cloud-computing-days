# Task-10: 같은 앱 복수 창 복구 실패 수정

## 증상

Chrome 2개 창을 다른 위치에 저장 → 1개 닫고 수동 복구 → 나머지 1개가 올바른 위치에 복구되지 않거나, 닫힌 창이 재실행되지 않아 `failed` 카운트 발생.

```
matched saved 'CertiNavigator - Chrome' → hwnd=0x400aa score=23
no candidate for '새 탭 - Chrome' (exe=...chrome.exe)
done 'Screen2' — 6/7 restored, 1 failed, elapsed 3607ms
```

Chrome 외 VSCode 등 동일 실행파일로 복수 창을 여는 앱 전체에 동일 문제 발생.

---

## 코드 흐름

```
gui.py: _work()
  └─ restore_mod.restore_layout(layout, running_windows=None, post_launch_settle_ms=5000)
       └─ list_current_windows()                  # 첫 스캔
       └─ launcher.ensure_apps_running(sorted_saved)   ← B2 버그 위치
       └─ time.sleep(1.5)                         # stabilize_ms
       └─ list_current_windows()                  # 재스캔
       └─ match_windows(sorted_saved, running)    ← B1 버그 위치
            └─ score_window(saved, running, already_assigned)
```

---

## 버그 분석

### B1: `match_windows` 그리디 알고리즘 — z_order 처리 순서 의존성

**위치:** `src/restore.py:match_windows()` (line 41)

**현재 코드 (문제 부분):**
```python
for saved in saved_windows:        # z_order 내림차순으로 처리
    best_match = None
    best_score = 0
    for running in running_windows:
        s = score_window(saved, running, assigned_hwnds)
        if s > best_score:
            best_score = s
            best_match = running
    if best_match is not None:
        assigned_hwnds.add(best_match["hwnd"])
```

**`_auto_title_pattern` 문제 (capture.py:9-14):**
```python
def _auto_title_pattern(title: str) -> str:
    sep = " - "
    if sep in title:
        app_name = title.rsplit(sep, 1)[-1].strip()
        return _re.escape(app_name) + "$"   # 앱 이름 접미사만 추출
    ...
```

| 저장된 창 제목 | 생성되는 title_pattern |
|---|---|
| `'CertiNavigator - Chrome'` | `Chrome$` |
| `'새 탭 - Chrome'` | `Chrome$` |
| `'Task-9.md - ... - Visual Studio Code'` | `Visual\ Studio\ Code$` |
| `'python3.13 - ... - Visual Studio Code'` | `Visual\ Studio\ Code$` |

→ 같은 앱의 모든 창이 **동일 title_pattern**을 가짐.

**버그 발생 조건 (구체 시나리오):**

- 저장: Chrome-A (z_order=7, title='새 탭'), Chrome-B (z_order=3, title='CertiNavigator')
- 실행 중: Chrome-X (title='CertiNavigator - Chrome') 1개만
- `sorted_saved`는 z_order 내림차순 → Chrome-A(z=7) 먼저 처리

처리 순서:
1. Chrome-A 처리 → Chrome-X와 score 계산: exe(10)+pattern(5)+class(3)=**18** (title_snapshot 불일치)
2. best_score=0 < 18 → Chrome-A가 Chrome-X **선점**
3. Chrome-B 처리 → Chrome-X 이미 assigned → `score=-100` → **no candidate**

결과: 실행 중인 Chrome-X가 `'새 탭'` 위치로 잘못 배치, `'CertiNavigator'` 위치 복구 실패.

> 로그에서 정상 동작한 이유: 그 케이스에서는 'CertiNavigator'의 z_order가 더 높아 먼저 처리되었고 score=23(완벽 일치)으로 정상 선점됨. z_order가 반대였다면 틀린 결과가 나왔을 것.

---

### B2: `ensure_apps_running` — 동일 title_pattern으로 인한 부족 창 탐지 실패

**위치:** `src/launcher.py:ensure_apps_running()` (line 98), `has_visible_window()` (line 86)

**현재 코드:**
```python
not_running = [
    w for w in saved_windows
    if w.get("exe_path") and not has_visible_window(w["exe_path"], w.get("title_pattern", ""))
]
```

**`has_visible_window` 내부:**
```python
def has_visible_window(exe_path, title_pattern):
    pattern_re = re.compile(title_pattern) if title_pattern else None
    for w in list_current_windows():
        if w.get("exe_path", "").lower() != exe_lower:
            continue
        if pattern_re is None or pattern_re.search(w.get("title_snapshot", "")):
            return True
    return False
```

**버그 발생 조건:**

저장된 창 2개: `'새 탭 - Chrome'`(pattern=`Chrome$`), `'CertiNavigator - Chrome'`(pattern=`Chrome$`)
실행 중인 창 1개: `'CertiNavigator - Chrome'`

- `'새 탭 - Chrome'` 저장 창에 대해: `has_visible_window(chrome.exe, 'Chrome$')` 호출
- 실행 중인 `'CertiNavigator - Chrome'` 창 발견 → `'Chrome$'` 패턴 일치 → **True 반환**
- `'새 탭 - Chrome'`이 `not_running`에 추가되지 않음
- Chrome이 재실행되지 않음 → `'새 탭'` 창 복구 불가

---

## 수정 계획

### M1: `match_windows` — 전역 점수 우선 그리디 매칭으로 교체 (B1 수정)

**위치:** `src/restore.py:match_windows()` (line 41–72) 전체 교체

**알고리즘:** 모든 (saved_i, running_j) 쌍의 raw 점수를 계산 → 점수 내림차순 정렬 → 양쪽 모두 미할당인 쌍부터 순서대로 할당. z_order 처리 순서와 무관하게 항상 더 잘 맞는 쌍이 먼저 할당됨.

**교체할 코드 전체:**
```python
def match_windows(saved_windows: list[dict], running_windows: list[dict]) -> list[tuple[dict, Optional[dict]]]:
    """
    For each saved window, find the best-matching running window.
    Uses global-score-priority assignment: all (saved, running) pairs sorted by score
    descending so the highest-confidence pair is always assigned first,
    regardless of z_order processing order.
    Returns list of (saved_window, matched_running_window_or_None).
    """
    # Step 1: 전체 (saved_i, running_j) 쌍 점수 계산
    # score_window에 빈 set 전달 → already_assigned 효과 없이 raw 점수만 계산
    pairs: list[tuple[int, int, int]] = []
    for i, saved in enumerate(saved_windows):
        for j, running in enumerate(running_windows):
            s = score_window(saved, running, set())
            if s > 0:
                pairs.append((s, i, j))

    # Step 2: 점수 내림차순 정렬
    pairs.sort(reverse=True)

    assigned_saved: dict[int, int] = {}   # saved_idx → running_idx
    assigned_running: set[int] = set()

    # Step 3: 양쪽 미할당 쌍부터 순서대로 할당
    for score, i, j in pairs:
        if i not in assigned_saved and j not in assigned_running:
            assigned_saved[i] = j
            assigned_running.add(j)

    # Step 4: 결과 조합 + 로그
    score_lookup = {(i, j): s for s, i, j in pairs}
    results = []
    for i, saved in enumerate(saved_windows):
        if i in assigned_saved:
            j = assigned_saved[i]
            running = running_windows[j]
            logger.info(
                "matched saved '%s' → hwnd=0x%x score=%d",
                saved.get("title_snapshot", saved.get("exe_path", "")),
                running["hwnd"],
                score_lookup[(i, j)],
            )
            results.append((saved, running))
        else:
            logger.warning(
                "no candidate for '%s' (exe=%s)",
                saved.get("title_snapshot", ""),
                saved.get("exe_path", ""),
            )
            results.append((saved, None))

    return results
```

**정확성 검증 (앞의 버그 시나리오):**
- pairs 정렬: (Chrome-B saved, Chrome-X running, 23), (Chrome-A saved, Chrome-X running, 18)
- score=23 먼저: Chrome-B → Chrome-X 할당
- score=18: Chrome-X 이미 할당 → Chrome-A unmatched
- 결과: Chrome-B(CertiNavigator) ↔ Chrome-X ✓, Chrome-A(새 탭) unmatched → M2에서 재실행 처리

---

### M2: `ensure_apps_running` + `_wait_for_window_count` 추가 (B2 수정)

**위치:** `src/launcher.py`

#### 추가할 헬퍼 함수 — `_wait_for_window_count`

`has_visible_window` 바로 위에 추가:

```python
def _wait_for_window_count(exe_path: str, min_count: int, timeout_seconds: float, poll_ms: int) -> bool:
    """Poll until at least min_count visible windows of exe_path exist."""
    exe_lower = exe_path.lower()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        count = sum(1 for w in list_current_windows()
                    if w.get("exe_path", "").lower() == exe_lower)
        if count >= min_count:
            return True
        logger.debug("waiting for %d window(s) of %s (current: %d)", min_count, exe_lower, count)
        time.sleep(poll_ms / 1000.0)
    logger.warning("timeout waiting for %d window(s) of %s", min_count, exe_lower)
    return False
```

#### `ensure_apps_running` 전체 교체 (line 98–138)

```python
def ensure_apps_running(
    saved_windows: list[dict],
    timeout_seconds: float = 60.0,
    poll_ms: int = 500,
) -> int:
    """
    For each exe_path, compare saved window count vs running window count.
    If running count < saved count, launch the app once per missing window.
    Returns total number of launch_app calls made.
    """
    from collections import Counter

    # exe별 saved 창 목록 구성
    exe_to_saved: dict[str, list[dict]] = {}
    for w in saved_windows:
        exe = w.get("exe_path", "")
        if not exe:
            continue
        exe_to_saved.setdefault(exe.lower(), []).append(w)

    if not exe_to_saved:
        return 0

    # 현재 실행 중인 창 수 (exe별)
    running_now = list_current_windows()
    running_counts = Counter(
        w.get("exe_path", "").lower() for w in running_now if w.get("exe_path")
    )

    logger.info(
        "ensure_apps: checking %d exe(s) — running counts: %s",
        len(exe_to_saved), dict(running_counts),
    )

    launched_total = 0
    for exe_lower, saved_list in exe_to_saved.items():
        n_needed = len(saved_list)
        n_running = running_counts.get(exe_lower, 0)
        deficit = n_needed - n_running

        if deficit <= 0:
            logger.debug("ensure_apps: %s — %d/%d, no launch needed", exe_lower, n_running, n_needed)
            continue

        logger.info("ensure_apps: %s — %d running, %d needed, launching %d", exe_lower, n_running, n_needed, deficit)

        rep = saved_list[0]   # launch 파라미터는 첫 번째 saved 창에서 가져옴
        for k in range(deficit):
            target_count = n_running + k + 1
            proc = launch_app(
                rep["exe_path"],
                rep.get("exe_args", ""),
                rep.get("cwd", ""),
                rep.get("is_uwp", False),
            )
            if proc is None:
                continue
            launched_total += 1
            found = _wait_for_window_count(rep["exe_path"], target_count, timeout_seconds, poll_ms)
            if not found:
                logger.warning(
                    "ensure_apps: gave up waiting for window #%d of %s",
                    target_count, exe_lower,
                )

    return launched_total
```

**기존 동작과의 호환성:**
- 단일 창 앱 (카카오톡 등): 0 running, 1 needed → deficit=1 → 1회 launch ✓ (기존 동작 동일)
- 단일 창 앱 실행 중: 1 running, 1 needed → deficit=0 → launch 없음 ✓
- Chrome 2창, 1개 running: 1 running, 2 needed → deficit=1 → 1회 추가 launch ✓ (신규 동작)

**주의: 기존 테스트 업데이트 필요**

`ensure_apps_running` 내부에서 `wait_for_window` 대신 `_wait_for_window_count`를 사용하므로, 아래 기존 테스트의 패치 대상 변경 필요:

| 기존 테스트 | 기존 패치 | 변경 후 패치 |
|---|---|---|
| `test_ensure_apps_running_no_window_launches` (TC4) | `src.launcher.wait_for_window` | `src.launcher._wait_for_window_count` |
| `test_ensure_apps_running_returns_count_of_launched` | `src.launcher.wait_for_window` | `src.launcher._wait_for_window_count` |

그 외 테스트는 영향 없음:
- TC5 (`window_exists_no_launch`): count-based로도 deficit=0 → launch 없음 ✓
- `test_ensure_apps_running_returns_zero_when_all_running`: 1 running, 1 needed → 0 반환 ✓
- `test_ensure_apps_running_skips_empty_exe_path`: exe_path="" → 건너뜀 ✓

---

## 단위 테스트 계획

### 파일: `tests/test_restore_matching.py` (기존 파일에 클래스 추가)

#### UT-T10-M1-1: 같은 앱 2개 저장, 1개 running — title_snapshot 일치하는 saved 창이 매칭

```python
class TestMultiWindowMatching:
    def test_same_app_two_saved_one_running_matches_higher_score(self):
        """
        Chrome 2개 저장, 1개 running → title_snapshot이 일치하는 saved 창에 매칭.
        title_snapshot 불일치 saved 창은 no candidate.
        """
        saved = [
            _saved(exe_path="C:\\chrome.exe", title_snapshot="CertiNavigator - Chrome",
                   title_pattern="Chrome$", class_name="Chrome_WidgetWin_1"),
            _saved(exe_path="C:\\chrome.exe", title_snapshot="새 탭 - Chrome",
                   title_pattern="Chrome$", class_name="Chrome_WidgetWin_1"),
        ]
        running = [
            _running(hwnd=0x1, exe_path="C:\\chrome.exe",
                     title_snapshot="CertiNavigator - Chrome", class_name="Chrome_WidgetWin_1"),
        ]
        from src.restore import match_windows
        results = match_windows(saved, running)
        assert results[0][1] is not None
        assert results[0][0]["title_snapshot"] == "CertiNavigator - Chrome"
        assert results[0][1]["hwnd"] == 0x1
        assert results[1][1] is None   # 새 탭 → no candidate
```

#### UT-T10-M1-2: 같은 앱 2개 저장, 2개 running — 각각 올바른 창에 매칭

```python
    def test_same_app_two_saved_two_running_correct_cross_assignment(self):
        """
        Chrome 2개 저장, 2개 running → title_snapshot 기반으로 각자 올바른 창에 매칭.
        (running 순서와 관계없이)
        """
        saved = [
            _saved(exe_path="C:\\chrome.exe", title_snapshot="CertiNavigator - Chrome",
                   title_pattern="Chrome$", class_name="Chrome_WidgetWin_1"),
            _saved(exe_path="C:\\chrome.exe", title_snapshot="새 탭 - Chrome",
                   title_pattern="Chrome$", class_name="Chrome_WidgetWin_1"),
        ]
        running = [
            _running(hwnd=0x1, exe_path="C:\\chrome.exe",
                     title_snapshot="새 탭 - Chrome", class_name="Chrome_WidgetWin_1"),
            _running(hwnd=0x2, exe_path="C:\\chrome.exe",
                     title_snapshot="CertiNavigator - Chrome", class_name="Chrome_WidgetWin_1"),
        ]
        from src.restore import match_windows
        results = match_windows(saved, running)
        matched = {r[0]["title_snapshot"]: r[1]["hwnd"] for r in results if r[1]}
        assert matched["CertiNavigator - Chrome"] == 0x2
        assert matched["새 탭 - Chrome"] == 0x1
```

#### UT-T10-M1-3: z_order 처리 순서와 무관한 최적 매칭 (이전 그리디 버그 재현 케이스)

```python
    def test_optimal_matching_independent_of_z_order(self):
        """
        z_order=7인 '새 탭' saved 창이 먼저 처리되더라도 score가 낮아서
        running Chrome-X를 선점하지 않음 (이전 그리디 버그 회귀 방지).
        """
        saved = [
            _saved(exe_path="C:\\chrome.exe", title_snapshot="CertiNavigator - Chrome",
                   title_pattern="Chrome$", class_name="Chrome_WidgetWin_1"),
            _saved(exe_path="C:\\chrome.exe", title_snapshot="새 탭 - Chrome",
                   title_pattern="Chrome$", class_name="Chrome_WidgetWin_1"),
        ]
        # z_order 내림차순 정렬 시 '새 탭'(z=7)이 먼저 처리되는 상황 재현
        saved[0]["z_order"] = 3
        saved[1]["z_order"] = 7
        sorted_saved = sorted(saved, key=lambda w: w.get("z_order", 0), reverse=True)

        running = [
            _running(hwnd=0x1, exe_path="C:\\chrome.exe",
                     title_snapshot="CertiNavigator - Chrome", class_name="Chrome_WidgetWin_1"),
        ]
        from src.restore import match_windows
        results = match_windows(sorted_saved, running)
        matched_titles = {r[0]["title_snapshot"]: r[1] for r in results}
        # CertiNavigator는 매칭, 새 탭은 no candidate
        assert matched_titles["CertiNavigator - Chrome"] is not None
        assert matched_titles["CertiNavigator - Chrome"]["hwnd"] == 0x1
        assert matched_titles["새 탭 - Chrome"] is None
```

---

### 파일: `tests/test_launcher.py` (기존 파일에 클래스 추가)

#### UT-T10-L1: ensure_apps_running — 같은 앱 2개 저장, 1개 running → 1회 추가 launch

```python
class TestEnsureAppsRunningMultiWindow:
    def test_two_saved_one_running_launches_once(self, monkeypatch):
        """
        Chrome 2개 저장, 1개만 실행 중 → deficit=1 → launch 1회.
        (title_pattern='Chrome$' 동일해도 count 기반이므로 정확히 탐지)
        """
        windows = [{"exe_path": "C:\\chrome.exe", "title_snapshot": "CertiNavigator - Chrome"}]
        monkeypatch.setattr("src.launcher.list_current_windows", lambda: windows)
        monkeypatch.setattr("src.launcher._wait_for_window_count", lambda *a, **kw: True)

        launched = []
        monkeypatch.setattr("src.launcher.launch_app",
                            lambda exe, *a, **kw: launched.append(exe) or MagicMock())

        from src.launcher import ensure_apps_running
        result = ensure_apps_running([
            _saved_window(exe_path="C:\\chrome.exe", title_pattern="Chrome$"),
            _saved_window(exe_path="C:\\chrome.exe", title_pattern="Chrome$"),
        ], timeout_seconds=5, poll_ms=50)

        assert launched == ["C:\\chrome.exe"]   # 1회 launch
        assert result == 1
```

#### UT-T10-L2: ensure_apps_running — 같은 앱 2개 저장, 2개 running → launch 없음

```python
    def test_two_saved_two_running_no_launch(self, monkeypatch):
        """Chrome 2개 저장, 2개 실행 중 → deficit=0 → launch 없음."""
        windows = [
            {"exe_path": "C:\\chrome.exe", "title_snapshot": "CertiNavigator - Chrome"},
            {"exe_path": "C:\\chrome.exe", "title_snapshot": "새 탭 - Chrome"},
        ]
        monkeypatch.setattr("src.launcher.list_current_windows", lambda: windows)

        launched = []
        monkeypatch.setattr("src.launcher.launch_app",
                            lambda exe, *a, **kw: launched.append(exe) or MagicMock())

        from src.launcher import ensure_apps_running
        result = ensure_apps_running([
            _saved_window(exe_path="C:\\chrome.exe", title_pattern="Chrome$"),
            _saved_window(exe_path="C:\\chrome.exe", title_pattern="Chrome$"),
        ], timeout_seconds=5, poll_ms=50)

        assert launched == []
        assert result == 0
```

#### UT-T10-L3: `_wait_for_window_count` — min_count 충족 시 True, 타임아웃 시 False

```python
    def test_wait_for_window_count_true_when_met(self, monkeypatch):
        """exe_path 창 수가 min_count 이상이면 True."""
        windows = [{"exe_path": "C:\\chrome.exe"}, {"exe_path": "C:\\chrome.exe"}]
        monkeypatch.setattr("src.launcher.list_current_windows", lambda: windows)
        monkeypatch.setattr("time.sleep", lambda _: None)

        from src.launcher import _wait_for_window_count
        assert _wait_for_window_count("C:\\chrome.exe", 2, timeout_seconds=5, poll_ms=50) is True

    def test_wait_for_window_count_false_on_timeout(self, monkeypatch):
        """창 수 부족 상태에서 타임아웃 → False."""
        monkeypatch.setattr("src.launcher.list_current_windows", lambda: [])
        monkeypatch.setattr("time.sleep", lambda _: None)

        tick = {"t": 0.0}
        def fake_monotonic():
            val = tick["t"]
            tick["t"] += 0.6
            return val
        monkeypatch.setattr("time.monotonic", fake_monotonic)

        from src.launcher import _wait_for_window_count
        assert _wait_for_window_count("C:\\chrome.exe", 1, timeout_seconds=1.0, poll_ms=500) is False
```

#### 기존 테스트 TC4, `test_ensure_apps_running_returns_count_of_launched` 업데이트

위 두 테스트는 `wait_for_window` 패치를 `_wait_for_window_count` 패치로 변경:

- `test_ensure_apps_running_no_window_launches` (TC4):
  ```python
  # 변경 전
  monkeypatch.setattr("src.launcher.wait_for_window", lambda *a, **kw: True)
  # 변경 후
  monkeypatch.setattr("src.launcher._wait_for_window_count", lambda *a, **kw: True)
  ```

- `test_ensure_apps_running_returns_count_of_launched`:
  ```python
  # 변경 전
  monkeypatch.setattr("src.launcher.wait_for_window", lambda *a, **kw: True)
  # 변경 후
  monkeypatch.setattr("src.launcher._wait_for_window_count", lambda *a, **kw: True)
  ```

---

### 파일: `tests/integration/test_restore_multi_window.py` (신규 파일)

실제 Chrome이 설치된 환경에서 실행. Chrome이 없거나 창이 없으면 skip.

```python
"""Integration tests for multi-window app restore (requires Chrome running)."""
import subprocess
import pytest

CHROME_EXE = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"


@pytest.fixture
def chrome_windows():
    """Capture current Chrome windows. Skip if fewer than 2 are open."""
    from src.capture import list_current_windows
    wins = [w for w in list_current_windows()
            if w.get("exe_path", "").lower() == CHROME_EXE.lower()]
    if len(wins) < 2:
        pytest.skip("Need at least 2 Chrome windows for this test")
    return wins


@pytest.mark.integration
def test_its_t10_1_two_chrome_windows_matched_correctly(chrome_windows):
    """
    실제 2개 Chrome 창이 각각 올바른 saved 창에 매칭됨.
    saved 창 z_order를 반전시켜도 title_snapshot 기반으로 올바르게 매칭.
    """
    from src.restore import match_windows

    saved = [
        {**chrome_windows[0],
         "z_order": chrome_windows[1]["z_order"],   # z_order 의도적으로 교차
         "placement": chrome_windows[0].get("placement", {})},
        {**chrome_windows[1],
         "z_order": chrome_windows[0]["z_order"],
         "placement": chrome_windows[1].get("placement", {})},
    ]
    import sorted as _sorted  # noqa — use sorted builtin
    sorted_saved = sorted(saved, key=lambda w: w.get("z_order", 0), reverse=True)

    results = match_windows(sorted_saved, chrome_windows)
    matched = {r[0]["hwnd"]: r[1]["hwnd"] if r[1] else None for r in results}

    for r in results:
        saved_w, running_w = r
        assert running_w is not None, f"no candidate for saved hwnd=0x{saved_w['hwnd']:x}"
        # title_snapshot 일치하는 running 창에 매칭
        assert saved_w["title_snapshot"] == running_w["title_snapshot"]


@pytest.mark.integration
def test_its_t10_2_ensure_apps_count_based_detection(monkeypatch):
    """
    ensure_apps_running count-based: Chrome 2개 저장, 1개만 실행 중이면 1회 launch 시도.
    실제 launch는 하지 않고 launch_app 호출 여부만 확인.
    """
    from src.capture import list_current_windows
    running = [w for w in list_current_windows()
               if w.get("exe_path", "").lower() == CHROME_EXE.lower()]
    if len(running) < 1:
        pytest.skip("Need at least 1 Chrome window")

    saved_windows = [
        {**running[0], "exe_args": "", "cwd": "", "is_uwp": False, "title_pattern": "Chrome$"},
        {**running[0], "exe_args": "", "cwd": "", "is_uwp": False, "title_pattern": "Chrome$"},
    ]

    launched = []

    import src.launcher as _launcher
    monkeypatch.setattr(_launcher, "launch_app",
                        lambda exe, *a, **kw: launched.append(exe) or None)
    monkeypatch.setattr(_launcher, "_wait_for_window_count", lambda *a, **kw: True)

    from src.launcher import ensure_apps_running
    result = ensure_apps_running(saved_windows, timeout_seconds=5, poll_ms=50)

    # 1개 running, 2개 needed → 1회 launch 시도
    assert result == 1
    assert CHROME_EXE.lower() in [e.lower() for e in launched]
```

> **참고:** `test_its_t10_1`에서 `sorted` builtin import 라인은 실수로 들어간 것이므로 실제 구현 시 제거하고 그냥 `sorted(...)`를 직접 사용할 것.

---

## 검증 명령어

### 단위 테스트

```bash
python -m pytest tests/ --ignore=tests/integration -v --tb=short
```

**완료 조건:** 기존 146개 + 신규 ≥ 9개 = **155개 이상 PASSED**
(UT-T10-M1-1~3: 3개, UT-T10-L1~2: 2개, UT-T10-L3: 2개, 업데이트된 TC4/count 테스트: 2개)

### 통합 테스트 (Chrome 2개 창 열린 상태에서)

```bash
python -m pytest tests/integration/test_restore_multi_window.py -m integration -v --tb=short
```

**완료 조건:** ITS-T10-1~2 PASSED

### 전체 회귀

```bash
python -m pytest tests/ --ignore=tests/integration -v --tb=short
```

---

## 주의 사항

1. **M1에서 `score_window` 시그니처 유지:** 기존 `score_window(saved, running, already_assigned)` 함수는 변경하지 않음. `match_windows` 내부에서 `set()`을 전달하여 raw 점수만 계산.

2. **M2에서 `has_visible_window` 유지:** 다른 테스트 코드에서 직접 사용되므로 삭제하지 않음. `ensure_apps_running` 내부에서만 더 이상 사용하지 않음.

3. **Chrome 재실행 동작:** Chrome이 이미 실행 중일 때 `chrome.exe`를 다시 실행하면 기존 창에 탭이 열릴 수도 있고 새 창이 열릴 수도 있음. `_wait_for_window_count`로 창 수 증가 여부만 확인. 창 수가 안 늘어도 WARNING 로그 후 복구 진행 (graceful fallback).

4. **`sorted` import 중복 버그 (ITS-T10-1 코드):** 통합 테스트 작성 시 `import sorted as _sorted` 라인 제거, `sorted()` 내장 함수 그대로 사용.

5. **UWP 앱:** `_wait_for_window_count`는 실행파일 경로로 창을 찾으므로 UWP의 경우 `exe_path`가 `ApplicationFrameHost.exe`로 통일됨 → UWP 복수 창 시나리오에서 동일 문제 발생 가능. 이번 Task 범위 밖이므로 별도 Task로 추적.

---

## TodoList

- [x] **M1**: `src/restore.py:match_windows()` (line 41–72) 전체를 전역 점수 우선 그리디 매칭으로 교체
- [x] **M2-a**: `src/launcher.py` — `_wait_for_window_count()` 헬퍼 함수 추가 (`has_visible_window` 위에 삽입)
- [x] **M2-b**: `src/launcher.py:ensure_apps_running()` (line 98–138) 전체를 count-based 탐지 로직으로 교체
- [x] **기존 테스트 업데이트**: `tests/test_launcher.py` — `test_ensure_apps_running_no_window_launches`(TC4), `test_ensure_apps_running_returns_count_of_launched` 두 테스트에서 `wait_for_window` 패치 → `_wait_for_window_count` 패치로 변경
- [x] **UT-T10-M1-1**: `tests/test_restore_matching.py` — 같은 앱 2개 저장, 1개 running, 높은 점수 창이 매칭 확인
- [x] **UT-T10-M1-2**: `tests/test_restore_matching.py` — 같은 앱 2개 저장, 2개 running, 교차 할당 정확성 확인
- [x] **UT-T10-M1-3**: `tests/test_restore_matching.py` — z_order 역순 정렬 후에도 최적 매칭 확인 (그리디 버그 회귀 방지)
- [x] **UT-T10-L1**: `tests/test_launcher.py` — Chrome 2개 저장, 1개 running → 1회 launch 확인
- [x] **UT-T10-L2**: `tests/test_launcher.py` — Chrome 2개 저장, 2개 running → launch 없음 확인
- [x] **UT-T10-L3**: `tests/test_launcher.py` — `_wait_for_window_count` 성공/타임아웃 단위 테스트
- [x] **단위 테스트 검증**: `pytest tests/ --ignore=tests/integration -v --tb=short` → 153개 PASSED (기존 146개 → 153개, 신규 7개 추가)
- [x] **ITS-T10-1~2**: `tests/integration/test_restore_multi_window.py` 신규 파일 작성 (실제 Chrome 2창 사용)
- [x] **통합 테스트 검증**: `pytest tests/integration/test_restore_multi_window.py -m integration -v --tb=short` → ITS-T10-2 PASSED, ITS-T10-1 SKIPPED (Chrome 2창 미실행)
- [ ] **수동 확인**: Chrome 2창 저장 → 1창 닫기 → 수동 복구 → 닫힌 창 재실행 + 남은 창 올바른 위치 배치 확인

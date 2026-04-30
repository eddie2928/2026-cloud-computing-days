# Task-9: 부팅 시 자동 복구 등록 실패 수정 (schtasks 액세스 거부)

## 증상

```
00:48:04.012 INFO  scheduler   : scheduler: registering task — schtasks.exe /Create /TN WinLayoutSaver_Rollback
    /TR "C:\...\WindowsApps\...\pythonw.exe" "C:\...\cli\rollback.py"
    /SC ONLOGON /DELAY 0000:20 /RL LIMITED /F
00:48:04.041 INFO  scheduler   : scheduler: schtasks exit=1 stdout=
00:48:04.041 ERROR scheduler   : scheduler: registration failed — stderr=오류: 액세스가 거부되었습니다.
```

---

## 코드 흐름 분석

```
gui.py : WinLayoutSaverApp._on_ar_toggle()
  └─ storage.save_config(config)
  └─ scheduler.register(script_path, delay_seconds)
       └─ _delay_str(delay_seconds)          # "0000:20" 생성
       └─ tr = f'"{python_exe}" "{script_path}"'
       └─ subprocess.run(["schtasks.exe", "/Create", ...])
```

### `scheduler.py:register()` 함수 내부 (현재)

```python
def register(script_path, delay_seconds=20, python_exe=None):
    if python_exe is None:
        python_dir = Path(sys.executable).parent
        pythonw = python_dir / "pythonw.exe"
        if not pythonw.exists():
            pythonw = Path(sys.executable)
        python_exe = str(pythonw)          # ← WindowsApps alias 그대로 사용

    delay = _delay_str(delay_seconds)
    tr = f'"{python_exe}" "{script_path}"'

    cmd = [
        "schtasks.exe", "/Create",
        "/TN", TASK_NAME,
        "/TR", tr,
        "/SC", "ONLOGON",
        # /RU 없음 ← 버그 B1
        "/DELAY", delay,
        "/RL", "LIMITED",
        "/F",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    ...
```

### `scheduler.py:_delay_str()` 함수 내부 (현재)

```python
def _delay_str(seconds: int) -> str:
    """Convert seconds to schtasks DELAY format: HHMM:SS"""   # ← 주석 오류 B3
    hours = seconds // 3600
    remaining = seconds % 3600
    minutes = remaining // 60
    secs = remaining % 60
    return f"{hours:02d}{minutes:02d}:{secs:02d}"
```

### `scheduler.py:unregister()` 함수 내부 (현재)

```python
def unregister() -> bool:
    cmd = ["schtasks.exe", "/Delete", "/TN", TASK_NAME, "/F"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("scheduler: unregister failed — stderr=%s", result.stderr)
        return False     # ← 태스크 없으면 exit=1 → False 반환, ERROR 로그 (B4)
    return True
```

### schtasks /Create /? 문서 (실제 확인)

```
/RU  username  Specifies the "run as" user account.
               For system account, valid values are "", "NT AUTHORITY\SYSTEM".

/NP            No password is stored. The task runs non-interactively.

/DELAY         The time format is mmmm:ss.   ← "분:초" 형식
               Only valid for ONSTART, ONLOGON, ONEVENT.
```

---

## 버그 목록 (우선순위별)

### B1 [주원인]: `/RU` 파라미터 누락 → 액세스 거부 (Access Denied)

**근거:**
`schtasks /Create /SC ONLOGON` 시 `/RU` 미지정 → Windows가 "모든 사용자" 로그온 트리거 태스크 생성 시도 → **관리자 권한 필요** → 액세스 거부 (exit=1).

`/RU "현재사용자명"` 지정 시: 현재 사용자의 로그온 트리거만 생성 → **일반 권한으로 가능**.

또한 ONLOGON 태스크는 사용자가 이미 인증된 상태에서 실행되므로 `/NP` (no password storage) 추가가 적절.

**근거가 되는 schtasks 동작:**
- `/RU ""` = SYSTEM 계정 (관리자 필요)
- `/RU "USERNAME"` = 특정 사용자 계정 (해당 사용자가 직접 생성 가능)

---

### B2 [실행 실패]: Windows Store Python alias → Task Scheduler에서 실행 불가

**근거:**
로그의 `/TR` 경로: `C:\Users\ab550\AppData\Local\Microsoft\WindowsApps\...\pythonw.exe`

이 경로는 **앱 실행 별칭(App Execution Alias)** — `WindowsApps` 디렉토리의 파일들은 실제 실행 파일이 아닌 Shell 컨텍스트에서만 동작하는 reparse point.

Task Scheduler는 **비대화형(non-interactive) 세션**에서 실행 → Shell activation context 없음 → alias 실행 불가 → **등록은 성공해도 실제 로그온 시 실행 실패**.

**탐지 조건:** `"WindowsApps"` in `python_exe` 경로

**대안 탐색 순서:**
1. `py.exe` 런처 (Python Launcher for Windows) — `shutil.which("py")` 로 탐색, 발견 시 `/TR "C:\Windows\py.exe" "rollback.py"` 형태로 사용
2. Windows Store Python 실제 설치 경로: `%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.*\LocalCache\local-packages\Python3*\pythonw.exe` (glob 탐색)
3. 위 모두 실패 시: 원본 경로 유지 + WARNING 로그 (등록은 진행, 실행 실패 가능성 경고)

---

### B3 [코드 문서 오류]: `_delay_str()` 주석과 실제 schtasks 형식 불일치

**근거:**
schtasks /? 문서: `/DELAY delaytime — The time format is **mmmm:ss**` (전체 분:초).

현재 코드 주석: `"HHMM:SS"` → 잘못된 형식 설명.

**기능 영향:**
- 딜레이 < 3600초(1시간): `hours=0`이므로 `f"00{mm:02d}:{ss:02d}"` = `f"{mm:04d}:{ss:02d}"`와 동일 → **기능 정상**
- 딜레이 ≥ 3600초: 현재 코드 `3600초 → "0100:00"` (100분?), 올바른 값 `"0060:00"` (60분) → **버그**

실용 범위(기본값 20초)에서는 문제 없으나, 주석 오류로 혼란 유발 + 1시간 이상 딜레이 설정 시 오작동.

---

### B4 [UX 오류]: `unregister()` 멱등성 없음

**근거:**
태스크가 존재하지 않는 상태에서 `unregister()` 호출 시:
- `schtasks /Delete` → exit=1 반환 ("해당 태스크 없음")
- `unregister()` → `False` 반환 + `ERROR` 로그

"비활성화" 의도로 버튼 클릭 시 이미 없는 태스크를 삭제하려 해도 오류처럼 보임.

**올바른 동작:** "태스크가 없음" = 이미 비활성화 상태 = 목적 달성 → `True` 반환.

---

## 수정 계획

### M1: `register()` 에 `/RU` + `/NP` 추가 (B1 수정)

**위치:** `src/scheduler.py` — `register()` 함수 내 `cmd` 리스트

```python
import os

cmd = [
    "schtasks.exe", "/Create",
    "/TN", TASK_NAME,
    "/TR", tr,
    "/SC", "ONLOGON",
    "/RU", os.environ.get("USERNAME", ""),   # 현재 사용자 → 관리자 권한 불필요
    "/NP",                                    # ONLOGON은 패스워드 불필요
    "/DELAY", delay,
    "/RL", "LIMITED",
    "/F",
]
```

`os` import는 함수 내부에서 해도 되고, 파일 상단에 추가해도 됨. 현재 `scheduler.py` 상단에는 `os` import 없으므로 `import os` 추가.

---

### M2: `_find_executable_for_scheduler()` 헬퍼 추가 (B2 수정)

**위치:** `src/scheduler.py` — `register()` 함수 위에 신규 함수 추가

```python
def _find_executable_for_scheduler(python_exe: str) -> str:
    """
    WindowsApps alias를 Task Scheduler에서 실행 가능한 실제 경로로 교체.
    Task Scheduler는 비대화형 컨텍스트에서 App Execution Alias를 실행 불가.
    """
    if "WindowsApps" not in str(python_exe):
        return python_exe  # 일반 Python 설치 → 그대로 사용

    import shutil
    from glob import glob

    # 1순위: py.exe 런처 (Python Launcher for Windows)
    py = shutil.which("py")
    if py and "WindowsApps" not in py:
        logger.debug("scheduler: using py.exe launcher for scheduler: %s", py)
        return py

    # 2순위: Windows Store Python 실제 설치 경로
    localappdata = os.environ.get("LOCALAPPDATA", "")
    for pattern in [
        localappdata + "\\Packages\\PythonSoftwareFoundation.Python.*"
                     + "\\LocalCache\\local-packages\\Python3*\\pythonw.exe",
        localappdata + "\\Packages\\PythonSoftwareFoundation.Python.*"
                     + "\\LocalCache\\local-packages\\Python3*\\python.exe",
    ]:
        matches = sorted(glob(pattern), reverse=True)  # 최신 버전 우선
        if matches:
            logger.debug("scheduler: using real Python from Packages: %s", matches[0])
            return matches[0]

    # fallback: 원본 유지 (경고 로그)
    logger.warning(
        "scheduler: Windows Store Python alias detected in /TR (%s) — "
        "task may not execute at logon; install py.exe launcher or use non-Store Python",
        python_exe,
    )
    return python_exe
```

`register()` 내부에서 `python_exe` 결정 직후 호출:

```python
    if python_exe is None:
        python_dir = Path(sys.executable).parent
        pythonw = python_dir / "pythonw.exe"
        if not pythonw.exists():
            pythonw = Path(sys.executable)
        python_exe = str(pythonw)

    python_exe = _find_executable_for_scheduler(python_exe)   # ← 이 줄 추가

    delay = _delay_str(delay_seconds)
    ...
```

---

### M3: `_delay_str()` 함수 수정 (B3 수정)

**위치:** `src/scheduler.py` — `_delay_str()` 함수

```python
def _delay_str(seconds: int) -> str:
    """Convert seconds to schtasks /DELAY format: mmmm:ss (total minutes:seconds)."""
    return f"{seconds // 60:04d}:{seconds % 60:02d}"
```

기존 코드 대비 출력값 변화:
- 20초: `"0000:20"` → `"0000:20"` (동일)
- 90초: `"0001:30"` → `"0001:30"` (동일)
- 3600초: `"0100:00"` → `"0060:00"` (수정됨)

---

### M4: `unregister()` 멱등성 수정 (B4 수정)

**위치:** `src/scheduler.py` — `unregister()` 함수

```python
def unregister() -> bool:
    """
    Remove WinLayoutSaver_Rollback from Windows Task Scheduler.
    Returns True on success or if the task was already not registered.
    """
    cmd = [
        "schtasks.exe",
        "/Delete",
        "/TN", TASK_NAME,
        "/F",
    ]
    logger.info("scheduler: unregistering task — %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("scheduler: schtasks exit=%d", result.returncode)
    if result.returncode == 0:
        return True
    # 삭제 실패 시 태스크가 실제로 없는지 확인 (멱등성)
    query = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME],
        capture_output=True,
    )
    if query.returncode != 0:
        logger.info("scheduler: task was already not registered — treating as success")
        return True
    logger.error("scheduler: unregister failed — stderr=%s", result.stderr)
    return False
```

---

## 단위 테스트 계획

**파일:** `tests/test_scheduler.py` (기존 파일에 추가)

### UT-S1: `register()` — `/RU` 현재 사용자명 포함 확인

```python
def test_register_includes_ru_flag(monkeypatch):
    """register()는 /RU 플래그에 현재 USERNAME을 포함해야 한다."""
    monkeypatch.setenv("USERNAME", "testuser")
    with patch("subprocess.run", return_value=make_ok_result()) as mock_run:
        from src.scheduler import register
        register(script_path="C:\\path\\rollback.py", delay_seconds=20)
        cmd_str = " ".join(str(a) for a in mock_run.call_args[0][0])
        assert "/RU" in cmd_str
        assert "testuser" in cmd_str
```

### UT-S2: `register()` — `/NP` 플래그 포함 확인

```python
def test_register_includes_np_flag():
    """register()는 ONLOGON 태스크에 /NP 플래그를 포함해야 한다."""
    with patch("subprocess.run", return_value=make_ok_result()) as mock_run:
        from src.scheduler import register
        register(script_path="C:\\path\\rollback.py", delay_seconds=20)
        cmd_str = " ".join(str(a) for a in mock_run.call_args[0][0])
        assert "/NP" in cmd_str
```

### UT-S3: `_find_executable_for_scheduler()` — 일반 Python → 그대로 반환

```python
def test_find_executable_non_store_returns_as_is():
    """WindowsApps가 아닌 경로는 변경 없이 반환."""
    from src.scheduler import _find_executable_for_scheduler
    path = "C:\\Python313\\pythonw.exe"
    assert _find_executable_for_scheduler(path) == path
```

### UT-S4: `_find_executable_for_scheduler()` — WindowsApps + py.exe 발견 → py.exe 반환

```python
def test_find_executable_store_uses_py_launcher(monkeypatch):
    """WindowsApps alias + py.exe 발견 시 py.exe 경로 반환."""
    import shutil as _shutil
    monkeypatch.setattr(_shutil, "which", lambda x: "C:\\Windows\\py.exe" if x == "py" else None)
    from importlib import reload
    import src.scheduler
    reload(src.scheduler)
    from src.scheduler import _find_executable_for_scheduler
    result = _find_executable_for_scheduler(
        "C:\\Users\\user\\AppData\\Local\\Microsoft\\WindowsApps\\pythonw.exe"
    )
    assert result == "C:\\Windows\\py.exe"
```

### UT-S5: `_find_executable_for_scheduler()` — WindowsApps + py.exe 없음 + Packages 발견 → Packages 경로 반환

```python
def test_find_executable_store_uses_packages_path(monkeypatch, tmp_path):
    """WindowsApps alias + py.exe 없음 + Packages 경로 발견 시 Packages 경로 반환."""
    import shutil as _shutil
    from glob import glob as _glob

    monkeypatch.setattr(_shutil, "which", lambda x: None)

    fake_pythonw = tmp_path / "pythonw.exe"
    fake_pythonw.write_text("")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    # glob이 fake 경로를 반환하도록 패치
    monkeypatch.setattr("src.scheduler.glob", lambda p: [str(fake_pythonw)])

    from src.scheduler import _find_executable_for_scheduler
    result = _find_executable_for_scheduler(
        "C:\\Users\\user\\AppData\\Local\\Microsoft\\WindowsApps\\pythonw.exe"
    )
    assert result == str(fake_pythonw)
```

### UT-S6: `_find_executable_for_scheduler()` — 모두 실패 → 원본 반환 + 경고

```python
def test_find_executable_store_fallback_warning(monkeypatch, caplog):
    """WindowsApps alias + 대안 없음 → 원본 반환, WARNING 로그."""
    import shutil as _shutil
    monkeypatch.setattr(_shutil, "which", lambda x: None)
    monkeypatch.setattr("src.scheduler.glob", lambda p: [])

    from src.scheduler import _find_executable_for_scheduler
    original = "C:\\Users\\user\\AppData\\Local\\Microsoft\\WindowsApps\\pythonw.exe"
    with caplog.at_level(logging.WARNING, logger="scheduler"):
        result = _find_executable_for_scheduler(original)
    assert result == original
    assert "Windows Store Python alias" in caplog.text
```

### UT-S7: `unregister()` — 태스크 없을 때 True 반환 (멱등성)

```python
def test_unregister_idempotent_when_not_found(monkeypatch):
    """unregister() — 태스크 없으면 (Query exit=1) True 반환."""
    call_results = [
        make_ok_result(returncode=1),  # /Delete → 실패
        make_ok_result(returncode=1),  # /Query → 없음 확인
    ]
    with patch("subprocess.run", side_effect=call_results):
        from src.scheduler import unregister
        assert unregister() is True
```

### UT-S8: `unregister()` — 태스크 존재하는데 삭제 실패 → False 반환

```python
def test_unregister_returns_false_when_task_exists_but_delete_fails(monkeypatch):
    """unregister() — 태스크 존재(Query exit=0) + 삭제 실패 → False."""
    call_results = [
        make_ok_result(returncode=1),  # /Delete → 실패
        make_ok_result(returncode=0),  # /Query → 존재 확인
    ]
    with patch("subprocess.run", side_effect=call_results):
        from src.scheduler import unregister
        assert unregister() is False
```

### UT-S9: `_delay_str()` — 3600초 이상에서 올바른 mmmm:ss 형식

```python
def test_delay_str_one_hour():
    """3600초 = 0060:00 (60분:0초), 현재 코드의 '0100:00'은 오류."""
    from src.scheduler import _delay_str
    assert _delay_str(3600) == "0060:00"

def test_delay_str_90_minutes():
    """5400초 = 0090:00 (90분)."""
    from src.scheduler import _delay_str
    assert _delay_str(5400) == "0090:00"
```

---

## 통합 테스트 계획

**파일:** `tests/integration/test_scheduler_real.py` (신규 파일)

실제 Windows schtasks.exe를 호출하는 통합 테스트.

```python
@pytest.mark.integration
def test_its1_register_creates_task():
    """실제 schtasks로 태스크 등록 후 /Query로 존재 확인."""
    ...
    result = scheduler.register(script_path=str(ROLLBACK_PY), delay_seconds=10)
    assert result is True, "register() 실패"
    query = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", scheduler.TASK_NAME],
        capture_output=True
    )
    assert query.returncode == 0, "태스크가 등록되지 않음"
    scheduler.unregister()  # cleanup

@pytest.mark.integration
def test_its2_unregister_removes_task():
    """등록 후 unregister() → /Query에서 태스크 없음 확인."""
    ...

@pytest.mark.integration
def test_its3_unregister_when_not_registered():
    """태스크 없는 상태에서 unregister() → True (멱등성)."""
    # 먼저 존재하지 않음을 보장
    subprocess.run(["schtasks.exe", "/Delete", "/TN", scheduler.TASK_NAME, "/F"],
                   capture_output=True)
    result = scheduler.unregister()
    assert result is True

@pytest.mark.integration
def test_its4_register_tr_path_not_windowsapps():
    """/TR 경로가 WindowsApps alias가 아닌 실제 실행 파일인지 확인."""
    # subprocess.run을 인터셉트해 /TR 값 검사
    captured = {}
    orig_run = subprocess.run
    def mock_run(cmd, **kw):
        if "schtasks" in str(cmd[0]).lower():
            captured["cmd"] = cmd
        return orig_run(cmd, **kw)
    with patch("subprocess.run", side_effect=mock_run):
        scheduler.register(script_path="C:\\dummy\\rollback.py")
    tr_value = captured.get("cmd", [""] * 10)[4]  # /TR 다음 인덱스
    assert "WindowsApps" not in tr_value, f"/TR에 WindowsApps alias 포함됨: {tr_value}"
    scheduler.unregister()
```

---

## 검증 명령어

### 단위 테스트

```bash
python -m pytest tests/test_scheduler.py -v --tb=short
```

**완료 조건**: 기존 테스트(6개) 유지 + 신규 9개 = 15개 이상 PASSED

### 전체 단위 테스트 회귀

```bash
python -m pytest tests/ --ignore=tests/integration -v --tb=short
```

**완료 조건**: 기존 136개 + 신규 ≥ 9개 = 145개 이상 PASSED

### 통합 테스트

```bash
python -m pytest tests/integration/test_scheduler_real.py -m integration -v --tb=short
```

**완료 조건**: ITS1~ITS4 PASSED (schtasks 실제 등록/삭제 성공)

### 수동 확인

GUI에서 "부팅 시 복구 활성화" 버튼 클릭 후:
1. 로그에 `scheduler: schtasks exit=0` 확인 (등록 성공)
2. `schtasks /Query /TN WinLayoutSaver_Rollback` → 태스크 존재 확인
3. 비활성화 버튼 클릭 → 로그에 ERROR 없이 성공 확인
4. 다시 비활성화 버튼 클릭 (이미 없는 상태) → ERROR 없이 True 반환 확인

---

## 주의 사항

1. **`/RU os.environ.get("USERNAME", "")`**: 빈 문자열이면 SYSTEM 계정(`/RU ""` = SYSTEM). 환경 변수가 없는 경우를 대비해 fallback이 필요하면 `os.getlogin()` 또는 `Path.home().name` 사용 검토.

2. **`_find_executable_for_scheduler()` 테스트**: `glob` 을 패치하려면 함수 내부에서 `from glob import glob` 대신 모듈 레벨에서 import 후 `src.scheduler.glob` 형태로 monkeypatch 가능하도록 구현해야 함.

3. **`/NP` 플래그**: 일부 Windows 구성에서 `/RU username /NP` 조합이 다르게 동작할 수 있음. 통합 테스트(ITS1)로 실제 등록 성공 여부 반드시 확인.

4. **통합 테스트 정리**: ITS1~ITS4는 실제 태스크 스케줄러를 수정하므로 각 테스트 종료 시 반드시 `scheduler.unregister()` 호출로 정리.

5. **Windows Store Python 탐지**: `"WindowsApps"` 문자열 포함 여부로 판단. `sys.executable`이 심볼릭 링크를 따라가도 여전히 `WindowsApps` 경로를 반환하므로 이 방법은 신뢰 가능.

---

## TodoList

- [x] **M1**: `src/scheduler.py`에 `import os` 추가 + `register()` 에 현재 사용자 기반 인증 추가 (schtasks → PowerShell Register-ScheduledTask로 대체, `/RU`+`/NP` 대신 `-AtLogOn -User USERNAME` 사용)
- [x] **M2**: `src/scheduler.py`에 `_find_executable_for_scheduler()` 헬퍼 함수 추가 (glob import 포함)
- [x] **M2**: `register()` 내부 `python_exe` 결정 직후 `python_exe = _find_executable_for_scheduler(python_exe)` 추가
- [x] **M3**: `_delay_str()` 함수를 `mmmm:ss` 형식으로 단순화 + 주석 수정
- [x] **M4**: `unregister()` 에 Query 기반 멱등성 로직 추가
- [x] **UT-S1~S2**: `tests/test_scheduler.py` 에 현재 사용자 + AtLogOn 트리거 포함 확인 테스트 추가 (TestRegisterRU 클래스)
- [x] **UT-S3~S6**: `tests/test_scheduler.py` 에 `_find_executable_for_scheduler()` 단위 테스트 4개 추가 (TestFindExecutableForScheduler 클래스)
- [x] **UT-S7~S8**: `tests/test_scheduler.py` 에 `unregister()` 멱등성 테스트 2개 추가 (TestUnregisterIdempotent 클래스)
- [x] **UT-S9**: `tests/test_scheduler.py` 에 `_delay_str()` 1시간+ 경계 테스트 추가 (TestDelayStr 클래스)
- [x] **단위 테스트 검증**: `pytest tests/ --ignore=tests/integration -v --tb=short` → 146개 PASSED
- [x] **ITS1~ITS4**: `tests/integration/test_scheduler_real.py` 신규 파일 작성 (통합 테스트 4개)
- [x] **통합 테스트 검증**: `pytest tests/integration/test_scheduler_real.py -m integration -v --tb=short` → 4개 PASSED
- [x] **수동 GUI 확인**: 활성화 → 로그 exit=0 확인, 비활성화 → ERROR 없음 확인

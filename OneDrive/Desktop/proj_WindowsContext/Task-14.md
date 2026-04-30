# Task-14: 부팅 시 자동 복구 미동작 버그 수정 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **단위 테스트만 수행하고 통합/E2E 테스트는 하지 않는다.**

---

## 0. 문제 정의 (증거)

| 항목 | 관찰값 | 출처 |
|------|--------|------|
| 사용자 보고 | "부팅 시 자동 복구를 활성화해도 복구가 안 된다" | 사용자 메시지 |
| 등록된 작업 | `WinLayoutSaver_Rollback` (LogonTrigger, Delay=PT10S, pyw.EXE + cli/rollback.py) | `schtasks /Query /TN WinLayoutSaver_Rollback /XML` |
| **Last Run Time** | **`1999-11-30 12:00:00`** (Windows의 "한 번도 실행 안 됨" 센티넬) | `schtasks /Query /V` |
| **Last Result** | **`267011` (= 0x41303, "Task has not yet run")** | `schtasks /Query /V` |
| 등록된 XML 설정 | `<DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries>`, `<StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>` | 작업 XML |
| 시스템 상태 | 노트북, **배터리 모드(BatteryStatus=1, 61%)** | `Get-WmiObject Win32_Battery` |
| 마지막 rollback 로그 | `2026-04-28 23:45:26.300 INFO  capture: found 0 candidates (89 skipped)` → `0/7 restored, 7 failed` | `%APPDATA%/WinLayoutSaver/logs/rollback-20260428-234526.log` |
| 04-29 / 04-30 rollback 로그 | **존재하지 않음** (해당 부팅들에서 작업 자체가 발화하지 않았음) | `logs/` 디렉터리 mtime 검사 |

### 1차 근본 원인 (재현 가능 100%)
`src/scheduler.py:_build_register_ps()`는 `New-ScheduledTaskSettingsSet`에 배터리 관련 옵션을 전달하지 않는다. 해당 cmdlet의 기본값은 `DisallowStartIfOnBatteries=true`, `StopIfGoingOnBatteries=true` 이므로, **노트북이 배터리 상태로 로그온하면 LogonTrigger 자체가 발화하지 않는다.** (Last Result=267011 와 04-29/04-30 로그 부재가 일치)

### 2차 잠재 원인 (04-28 로그가 입증)
배터리에서 등록된 트리거가 발화하더라도, `PT10S` 지연 후 `cli/rollback.py`가 곧바로 `list_current_windows()`를 호출하면 셸이 아직 창을 노출하지 않은 상태에서 0개 결과로 종료된다. 04-28 로그가 정확히 그 모습이다(`found 0 candidates (89 skipped)` → `0/7 restored`). 1차 원인을 고친 직후에 다시 만나게 될 문제이므로 함께 수정한다.

### 3차 보강 (운영성)
- `_build_register_ps()` 의 PowerShell이 실패해도 stderr만 로그에 남는다. 별도 진단 파일로 보강.
- 사용자가 즉시 검증할 수 있도록 GUI에 "지금 실행" 버튼 추가.
- 이미 등록되어 있는 (배터리 옵션이 잘못 박힌) 작업을 GUI 시작 시 자동 재등록(마이그레이션).

---

## 1. Goal (성공 기준)

다음을 모두 만족하면 본 Task 완료:

1. `src/scheduler.py`의 `_build_register_ps`가 **`-AllowStartIfOnBatteries` 와 `-DontStopIfGoingOnBatteries` 를 포함**한다 — 단위 테스트로 검증.
2. 자동복구가 활성화 상태인 채 GUI를 새로 띄우면, **GUI 시작 시점에 작업이 자동 재등록**되어 배터리 옵션이 갱신된다 — 단위 테스트로 검증.
3. `cli/rollback.py`가 `list_current_windows()` 결과 0개일 때 **고정 N초 간격으로 최대 M회 재시도**한 뒤에야 `restore_layout`을 호출한다 — 단위 테스트로 검증.
4. `scheduler.register()`가 `Register-ScheduledTask` 비-0 종료 시 **`logs/scheduler-register-error-YYYYMMDD-HHMMSS.log`** 진단 파일을 남긴다 — 단위 테스트로 검증.
5. GUI 자동복구 LabelFrame에 "**지금 실행**(Run rollback now)" 버튼이 있고, 클릭 시 `schtasks /Run /TN WinLayoutSaver_Rollback`을 호출한다 — 단위 테스트로 검증.
6. 신규 i18n 키 4종(`run_now_btn`, `run_now_failed_msg`, `run_now_success_msg`, `migrate_task_log`)이 ko/en 양쪽에 존재 — 단위 테스트로 검증.
7. `pytest --tb=short -q` 전체 PASS (회귀 없음).

---

## 2. Architecture (수정 개요)

| 영역 | 현재 동작 | 변경 후 동작 |
|------|----------|--------------|
| 작업 설정 | `-StartWhenAvailable -RunOnlyIfNetworkAvailable:$false -Hidden` | + `-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)` |
| 작업 마이그레이션 | 사용자가 토글 OFF→ON 해야만 갱신 | GUI `__init__` 마지막 단계에서 `auto_rollback.enabled=true`이면 자동 unregister→register |
| rollback.py 셸 대기 | 즉시 1회 스캔 후 종료 | 0창이면 5초 × 12회(=60초) 재시도, 창 ≥1개 또는 최대 시도 도달 시 진행 |
| register 진단 | logger.error로 stderr 한 줄 | 추가로 `logs/scheduler-register-error-...log`에 PowerShell 명령/stdout/stderr 전체 덤프 |
| GUI Run Now | 없음 | 자동복구 LabelFrame에 버튼 추가, schtasks /Run 호출 후 messagebox로 결과 표시 |

### Tech Stack
Python 3.11+, tkinter, pywin32, psutil, Pillow, pytest

### 수정 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `src/scheduler.py` | `_build_register_ps`에 배터리/타임리밋 플래그 추가; `register()`에서 비-0 종료 시 진단 파일 작성; 신규 `run_now()` 헬퍼 추가 |
| `src/gui.py` | `__init__`에 `_migrate_existing_task()` 호출 추가; AR LabelFrame에 "지금 실행" 버튼 추가 |
| `cli/rollback.py` | 본격 restore 직전 0창이면 재시도 루프(상수 `_SHELL_WAIT_INTERVAL_S=5`, `_SHELL_WAIT_MAX_TRIES=12`) |
| `src/i18n.py` | 4개 키(ko/en) 추가 |
| `tests/test_scheduler.py` | (신규) `_build_register_ps` 문자열 검증 + `register()` 진단 파일 + `run_now()` 테스트 |
| `tests/test_rollback_shell_wait.py` | (신규) 0창 재시도 루프 단위 테스트 |
| `tests/test_gui_run_now.py` | (신규) "지금 실행" 버튼 존재/콜백 단위 테스트 |
| `tests/test_gui_migrate.py` | (신규) GUI `__init__` 시 자동 재등록 단위 테스트 |
| `tests/test_i18n.py` | 신규 키 4종 존재 테스트 추가 |

---

## 3. 체크포인트 표 (중단 후 재개 시 첫 미완료 Task부터)

| Task | 커밋 메시지 접두사 | 완료 조건 |
|------|------------------|----------|
| 0 | (없음 — 진단만) | 로컬에서 `schtasks /Query /V /TN WinLayoutSaver_Rollback`로 Last Result=267011 또는 미실행 확인 |
| 1 | `fix(Task-14): scheduler battery flags` | `pytest tests/test_scheduler.py -k battery -q` PASS |
| 2 | `feat(Task-14): scheduler register diagnostic dump` | `pytest tests/test_scheduler.py -k diagnostic -q` PASS |
| 3 | `feat(Task-14): scheduler.run_now()` | `pytest tests/test_scheduler.py -k run_now -q` PASS |
| 4 | `fix(Task-14): rollback shell-ready retry` | `pytest tests/test_rollback_shell_wait.py -q` PASS |
| 5 | `feat(Task-14): i18n run_now keys` | `pytest tests/test_i18n.py -q` PASS |
| 6 | `feat(Task-14): GUI Run Now button` | `pytest tests/test_gui_run_now.py -q` PASS |
| 7 | `feat(Task-14): GUI auto-migrate AR task` | `pytest tests/test_gui_migrate.py -q` PASS |
| 8 | (회귀) | `pytest --tb=short -q` 전체 PASS |

재개 시 `git log --oneline -15`로 마지막 완료 커밋 prefix를 찾고 다음 Task의 첫 Step부터 이어서 진행한다.

---

## Task 0: 진단 증거 재확인 (코드 수정 없음)

**근거:** 1차 근본 원인이 환경에 따라 달라질 수 있으므로 작업 시작 직전 한 번 더 확인.

- [x] **Step 0-1: 작업 마지막 실행 결과 확인**

```
schtasks /Query /TN WinLayoutSaver_Rollback /V /FO LIST
```

Expected: `Last Run Time: 1999-11-30 ...` 또는 `Last Result: 267011`(0x41303). 다르게 나오면 사용자에게 보고하고 진행 여부 재확인.

- [x] **Step 0-2: 등록된 XML 배터리 옵션 확인**

```
schtasks /Query /TN WinLayoutSaver_Rollback /XML | findstr /R "DisallowStartIfOnBatteries StopIfGoingOnBatteries"
```

Expected: 두 줄 모두 `>true<` 가 보임. (이게 본 Task로 고치는 대상)

- [x] **Step 0-3: 최근 rollback 로그 부재 확인**

```
dir "%APPDATA%\WinLayoutSaver\logs" /OD /B | findstr /R "rollback-"
```

Expected: 최근 1주 이내 rollback 로그가 거의 없거나 없음(배터리로 인한 미발화).

- [x] **Step 0-4: 작업 디렉터리 git 상태 확인**

```
git status
git log --oneline -5
```

Expected: 작업 트리는 추가 파일(`Task-14.md` 외) 없이 깨끗하거나, 사전에 사용자가 stash/commit 처리. **충돌 가능성 있으면 사용자에게 stash 여부 질문 후 진행.**

---

## Task 1: scheduler `-AllowStartIfOnBatteries` / `-DontStopIfGoingOnBatteries` 플래그 추가

**근거:** 1차 근본 원인. `New-ScheduledTaskSettingsSet`은 두 플래그 기본값 모두 true이므로 노트북 배터리 상태에서 트리거가 발화하지 않는다. 추가로 `ExecutionTimeLimit=PT30M` 으로 무한 대기 방지(rollback이 모종의 이유로 행 걸린 경우 30분 후 자동 종료).

**Files:**
- Modify: `src/scheduler.py`
- Test: `tests/test_scheduler.py` (신규 또는 기존 확장)

---

- [x] **Step 1-1: `_build_register_ps` 의 SettingsSet 라인 수정**

`src/scheduler.py:88` (현재):

```python
f"$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false -Hidden; "
```

으로 변경:

```python
f"$s = New-ScheduledTaskSettingsSet "
f"-StartWhenAvailable "
f"-RunOnlyIfNetworkAvailable:$false "
f"-Hidden "
f"-AllowStartIfOnBatteries "
f"-DontStopIfGoingOnBatteries "
f"-ExecutionTimeLimit (New-TimeSpan -Minutes 30); "
```

> **주의:** PowerShell f-string 안에서 `$false`, `$s`, `$a`, `$t`는 그대로 통과해야 하므로 절대 `{}` 보간 변수로 해석되지 않게 한다(이미 다른 라인들도 동일 규칙).

- [x] **Step 1-2: 단위 테스트 추가 — `tests/test_scheduler.py`**

> 기존 파일이 없으면 신규 생성. 있으면 아래 클래스/함수만 추가.

```python
"""tests/test_scheduler.py — _build_register_ps 의 PowerShell 문자열 검증."""
from src.scheduler import _build_register_ps


def test_build_register_ps_allows_battery_start():
    ps = _build_register_ps("C:\\pyw.exe", "C:\\rollback.py", 10, "ab550")
    assert "-AllowStartIfOnBatteries" in ps


def test_build_register_ps_does_not_stop_on_battery():
    ps = _build_register_ps("C:\\pyw.exe", "C:\\rollback.py", 10, "ab550")
    assert "-DontStopIfGoingOnBatteries" in ps


def test_build_register_ps_has_execution_time_limit():
    ps = _build_register_ps("C:\\pyw.exe", "C:\\rollback.py", 10, "ab550")
    assert "ExecutionTimeLimit" in ps
    assert "Minutes 30" in ps


def test_build_register_ps_keeps_existing_flags():
    """기존 플래그가 회귀로 빠지지 않았는지 보장."""
    ps = _build_register_ps("C:\\pyw.exe", "C:\\rollback.py", 10, "ab550")
    assert "-StartWhenAvailable" in ps
    assert "-Hidden" in ps
    assert "-RunOnlyIfNetworkAvailable:$false" in ps
    assert "AtLogOn" in ps  # 트리거 종류 회귀 가드
    assert "PT10S" in ps    # delay 포맷 회귀 가드


def test_build_register_ps_standalone_exe_no_argument():
    """script_path='' (frozen exe 경로)에서는 -Argument가 비어 있어야 한다."""
    ps = _build_register_ps("C:\\WinLayoutSaverRollback.exe", "", 10, "ab550")
    assert "-Argument" not in ps  # 인자 없음
    assert "WinLayoutSaverRollback.exe" in ps
```

- [x] **Step 1-3: 테스트 실행**

```
pytest tests/test_scheduler.py -k "battery or execution or flags or standalone" -q
```

Expected: 5 PASS.

- [x] **Step 1-4: 커밋**

```
git add src/scheduler.py tests/test_scheduler.py
git commit -m "fix(Task-14): scheduler — allow start/run on battery + 30m time limit"
```

---

## Task 2: `register()` 실패 시 진단 덤프 작성

**근거:** PowerShell 등록은 인용/이스케이프/UTF-16 변환 등 실패 표면이 넓다. 현재 `subprocess.run(... capture_output=True)` 이후 `logger.error`로 한 줄만 남기면, 실 환경에서 사용자가 원인을 추적하기 어렵다. 비-0 종료 시 별도 파일(`logs/scheduler-register-error-YYYYMMDD-HHMMSS.log`)에 PowerShell 원본 명령(디코딩본) + stdout + stderr를 덤프한다.

**Files:**
- Modify: `src/scheduler.py`
- Test: `tests/test_scheduler.py`

---

- [x] **Step 2-1: `src/scheduler.py` 상단에 import 추가**

이미 `import os`, `import logging` 이 있으므로 추가 import:

```python
from datetime import datetime
from src.paths import LOGS_DIR
```

> `paths.LOGS_DIR`은 이미 정의되어 있음(`src/paths.py:7`). 사용하기만 하면 됨.

- [x] **Step 2-2: `register()` 의 실패 분기에 덤프 로직 추가**

`src/scheduler.py:121-127` 의 실패 분기를 다음으로 교체:

```python
if result.returncode != 0:
    logger.error(
        "scheduler: registration failed — stderr=%s stdout=%s",
        result.stderr.strip(), result.stdout.strip(),
    )
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        dump_path = LOGS_DIR / f"scheduler-register-error-{ts}.log"
        dump_path.write_text(
            "=== PowerShell command (decoded) ===\n"
            f"{ps}\n\n"
            "=== Exit code ===\n"
            f"{result.returncode}\n\n"
            "=== STDOUT ===\n"
            f"{result.stdout}\n\n"
            "=== STDERR ===\n"
            f"{result.stderr}\n",
            encoding="utf-8",
        )
        logger.info("scheduler: wrote diagnostic dump → %s", dump_path)
    except OSError as e:
        logger.warning("scheduler: failed to write diagnostic dump: %s", e)
    return False
return True
```

- [x] **Step 2-3: 단위 테스트 추가 — `tests/test_scheduler.py`**

```python
def test_register_writes_diagnostic_on_failure(monkeypatch, tmp_path):
    """register()는 PowerShell 비-0 종료 시 logs/ 아래 진단 파일을 작성한다."""
    import src.scheduler as sched_mod
    import subprocess

    # Redirect LOGS_DIR (모듈 안에서 from src.paths import LOGS_DIR로 들고 옴)
    monkeypatch.setattr(sched_mod, "LOGS_DIR", tmp_path)

    fake_result = subprocess.CompletedProcess(
        args=["powershell.exe"], returncode=1,
        stdout="some stdout", stderr="some stderr",
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)

    ok = sched_mod.register(script_path="C:\\rollback.py", delay_seconds=10,
                             python_exe="C:\\pyw.exe")
    assert ok is False

    dumps = list(tmp_path.glob("scheduler-register-error-*.log"))
    assert len(dumps) == 1
    text = dumps[0].read_text(encoding="utf-8")
    assert "=== STDERR ===" in text
    assert "some stderr" in text
    assert "=== STDOUT ===" in text
    assert "some stdout" in text
    assert "=== Exit code ===" in text
    assert "Register-ScheduledTask" in text  # 디코딩된 PS 본문이 포함됐는지


def test_register_no_diagnostic_on_success(monkeypatch, tmp_path):
    """성공 시 진단 파일을 만들지 않는다."""
    import src.scheduler as sched_mod
    import subprocess

    monkeypatch.setattr(sched_mod, "LOGS_DIR", tmp_path)
    fake_result = subprocess.CompletedProcess(
        args=["powershell.exe"], returncode=0, stdout="", stderr="",
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)

    ok = sched_mod.register(script_path="C:\\rollback.py", delay_seconds=10,
                             python_exe="C:\\pyw.exe")
    assert ok is True
    assert list(tmp_path.glob("scheduler-register-error-*.log")) == []
```

- [x] **Step 2-4: 테스트 실행**

```
pytest tests/test_scheduler.py -k "diagnostic" -q
```

Expected: 2 PASS.

- [x] **Step 2-5: 커밋**

```
git add src/scheduler.py tests/test_scheduler.py
git commit -m "feat(Task-14): scheduler — write diagnostic dump on register failure"
```

---

## Task 3: `scheduler.run_now()` 헬퍼

**근거:** GUI "지금 실행" 버튼이 호출할 명령. 별도 함수로 분리해 단위 테스트 용이성과 향후 재사용을 확보한다.

**Files:**
- Modify: `src/scheduler.py`
- Test: `tests/test_scheduler.py`

---

- [x] **Step 3-1: `src/scheduler.py` 끝부분에 함수 추가**

```python
def run_now() -> tuple[bool, str]:
    """
    schtasks /Run /TN WinLayoutSaver_Rollback 으로 등록된 작업을 즉시 실행 트리거.
    Returns (ok, message). ok=False 인 경우 message에 stderr 포함.
    """
    cmd = ["schtasks.exe", "/Run", "/TN", TASK_NAME]
    logger.info("scheduler: run_now — %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("scheduler: run_now exit=%d", result.returncode)
    if result.returncode == 0:
        return True, result.stdout.strip() or "OK"
    return False, (result.stderr.strip() or result.stdout.strip()
                   or f"exit code {result.returncode}")
```

- [x] **Step 3-2: 단위 테스트 추가**

```python
def test_run_now_success(monkeypatch):
    import src.scheduler as sched_mod
    import subprocess
    captured = {}
    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, "성공: ...", "")
    monkeypatch.setattr(subprocess, "run", fake_run)

    ok, msg = sched_mod.run_now()
    assert ok is True
    assert captured["cmd"][:3] == ["schtasks.exe", "/Run", "/TN"]
    assert captured["cmd"][3] == sched_mod.TASK_NAME


def test_run_now_failure(monkeypatch):
    import src.scheduler as sched_mod
    import subprocess
    monkeypatch.setattr(subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "오류: 작업 없음"))

    ok, msg = sched_mod.run_now()
    assert ok is False
    assert "오류: 작업 없음" in msg
```

- [x] **Step 3-3: 테스트 실행**

```
pytest tests/test_scheduler.py -k "run_now" -q
```

Expected: 2 PASS.

- [x] **Step 3-4: 커밋**

```
git add src/scheduler.py tests/test_scheduler.py
git commit -m "feat(Task-14): scheduler.run_now() to trigger task on demand"
```

---

## Task 4: `cli/rollback.py` 셸 준비 대기 (0창 회피)

**근거:** 04-28 로그가 입증한 2차 잠재 원인. 1차 원인을 고친 직후에도 동일 패턴(로그온 직후 셸 미준비)으로 0/N restored가 재발할 수 있다. **고정 5초 간격 × 최대 12회(=60초) 폴링**으로 보강한다.

**Files:**
- Modify: `cli/rollback.py`
- Test: `tests/test_rollback_shell_wait.py` (신규)

---

- [x] **Step 4-1: `cli/rollback.py` 상단(imports 직후)에 상수 정의**

```python
_SHELL_WAIT_INTERVAL_S = 5
_SHELL_WAIT_MAX_TRIES = 12   # 5s * 12 = 60s
```

- [x] **Step 4-2: `wait_for_shell_ready` 함수 추가**

`main()` 정의 직전에 추가:

```python
def wait_for_shell_ready(
    list_windows_fn,
    interval_s: float = _SHELL_WAIT_INTERVAL_S,
    max_tries: int = _SHELL_WAIT_MAX_TRIES,
    sleep_fn=None,
) -> int:
    """
    list_windows_fn() 결과가 ≥1개일 때까지 폴링.
    Returns: 마지막 스캔에서 발견한 창 개수 (0이면 셸이 끝까지 비어 있던 것).

    인자를 모두 주입 가능하게 만든 이유는 단위 테스트(가짜 sleep, 가짜 list)에서 제어하기 위함.
    """
    import time as _time
    sleep = sleep_fn or _time.sleep

    for attempt in range(1, max_tries + 1):
        windows = list_windows_fn()
        n = len(windows)
        if n > 0:
            logger.info(
                "rollback: shell ready — %d window(s) at attempt %d/%d",
                n, attempt, max_tries,
            )
            return n
        logger.info(
            "rollback: shell not ready — 0 windows, attempt %d/%d, sleeping %.1fs",
            attempt, max_tries, interval_s,
        )
        if attempt < max_tries:
            sleep(interval_s)

    logger.warning(
        "rollback: shell still empty after %d attempts (%ds total) — proceeding anyway",
        max_tries, int(interval_s * max_tries),
    )
    return 0
```

- [x] **Step 4-3: `main()`에서 `restore_layout` 호출 직전에 wait 호출**

`cli/rollback.py:79-80` 의 `from src.monitors import list_current_monitors` 직전(또는 직후)에 추가:

```python
from src.capture import list_current_windows as _list_current_windows
wait_for_shell_ready(_list_current_windows)
```

> 주: `restore_layout(...)` 자체는 내부에서 다시 `list_current_windows()`를 부르므로 결과를 인자로 넘길 필요는 없다. 본 wait의 효과는 "0개 상태에서 곧장 매칭 0/N으로 끝나는" 결과를 막는 것뿐이다.

- [x] **Step 4-4: 단위 테스트 — `tests/test_rollback_shell_wait.py` (신규)**

```python
"""tests/test_rollback_shell_wait.py — wait_for_shell_ready 단위 테스트."""
import sys
import types
import importlib

# pywin32 더미 (rollback 모듈이 import 시점에 ctypes만 만지므로 불필요할 수 있으나 안전하게)
def _import_rollback():
    sys.modules.pop("cli.rollback", None)
    return importlib.import_module("cli.rollback")


def test_returns_count_immediately_when_windows_present():
    rb = _import_rollback()
    n = rb.wait_for_shell_ready(
        list_windows_fn=lambda: [{"hwnd": 1}, {"hwnd": 2}],
        interval_s=0.0, max_tries=5,
        sleep_fn=lambda s: None,
    )
    assert n == 2


def test_polls_until_nonzero():
    rb = _import_rollback()
    counter = {"n": 0}
    def fake_list():
        counter["n"] += 1
        return [] if counter["n"] < 3 else [{"hwnd": 1}]
    slept = []
    n = rb.wait_for_shell_ready(
        list_windows_fn=fake_list,
        interval_s=5.0, max_tries=10,
        sleep_fn=lambda s: slept.append(s),
    )
    assert n == 1
    assert counter["n"] == 3
    assert slept == [5.0, 5.0]   # 1차/2차 실패 후 두 번 잠


def test_returns_zero_after_max_tries():
    rb = _import_rollback()
    slept = []
    n = rb.wait_for_shell_ready(
        list_windows_fn=lambda: [],
        interval_s=5.0, max_tries=4,
        sleep_fn=lambda s: slept.append(s),
    )
    assert n == 0
    # max_tries-1 번 sleep (마지막 시도 후엔 sleep 안 함)
    assert len(slept) == 3
```

- [x] **Step 4-5: 테스트 실행**

```
pytest tests/test_rollback_shell_wait.py -q
```

Expected: 3 PASS.

- [x] **Step 4-6: 커밋**

```
git add cli/rollback.py tests/test_rollback_shell_wait.py
git commit -m "fix(Task-14): rollback — wait up to 60s for shell-ready before restore"
```

---

## Task 5: i18n 키 추가 (run_now 등 4개)

**근거:** 후속 GUI 변경에 사용할 라벨/메시지를 미리 정의. 이 Task가 GUI Task보다 먼저 와야 GUI 테스트에서 키가 누락되지 않는다.

**Files:**
- Modify: `src/i18n.py`
- Test: `tests/test_i18n.py` (확장)

---

- [x] **Step 5-1: `src/i18n.py` 의 `ko` / `en` 딕셔너리 양쪽에 4개 키 추가**

ko 측 추가(예시 위치: 기존 `enable_btn`/`disable_btn` 근처):

```python
"run_now_btn": "지금 실행",
"run_now_success_msg": "자동 복구 작업을 트리거했습니다. 잠시 후 로그를 확인하세요.",
"run_now_failed_msg": "자동 복구 실행 실패: {error}",
"migrate_task_log": "기존 자동복구 작업을 새 설정으로 재등록합니다 (배터리 옵션 갱신)",
```

en 측 추가(동일 키, 영어 문구):

```python
"run_now_btn": "Run now",
"run_now_success_msg": "Auto-recovery task triggered. Check logs in a moment.",
"run_now_failed_msg": "Failed to run auto-recovery: {error}",
"migrate_task_log": "Re-registering existing auto-recovery task with updated settings (battery flags)",
```

- [x] **Step 5-2: `tests/test_i18n.py`에 신규 키 존재 테스트 추가**

```python
def test_task14_keys_present_in_both_languages():
    from src.i18n import STRINGS
    keys = ["run_now_btn", "run_now_success_msg", "run_now_failed_msg", "migrate_task_log"]
    for k in keys:
        assert k in STRINGS["ko"], f"missing ko: {k}"
        assert k in STRINGS["en"], f"missing en: {k}"
        assert STRINGS["ko"][k]
        assert STRINGS["en"][k]
```

- [x] **Step 5-3: 테스트 실행**

```
pytest tests/test_i18n.py -q
```

Expected: ALL PASS.

- [x] **Step 5-4: 커밋**

```
git add src/i18n.py tests/test_i18n.py
git commit -m "feat(Task-14): i18n — add run_now / migrate_task_log keys"
```

---

## Task 6: GUI "지금 실행" 버튼

**근거:** 사용자가 부팅을 기다리지 않고 즉시 검증할 수 있어야 한다. Task 1~4의 효과를 같은 환경에서 빠르게 재확인하는 가장 직접적인 수단.

**Files:**
- Modify: `src/gui.py`
- Test: `tests/test_gui_run_now.py` (신규)

---

- [x] **Step 6-1: AR LabelFrame 행 0(활성화 버튼) 옆에 "지금 실행" 버튼 배치**

`src/gui.py:74-76` (현재):

```python
self._ar_toggle_btn = tk.Button(self._ar_section, text=t("enable_btn"),
                                command=self._on_ar_toggle, padx=4, pady=0)
self._ar_toggle_btn.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
```

으로 변경:

```python
self._ar_toggle_btn = tk.Button(self._ar_section, text=t("enable_btn"),
                                command=self._on_ar_toggle, padx=4, pady=0)
self._ar_toggle_btn.grid(row=0, column=0, sticky="w", pady=(0, 6))

self._run_now_btn = tk.Button(self._ar_section, text=t("run_now_btn"),
                              command=self._on_run_now, padx=4, pady=0)
self._run_now_btn.grid(row=0, column=1, columnspan=3, sticky="w",
                       padx=(8, 0), pady=(0, 6))
```

- [x] **Step 6-2: `_on_run_now` 메서드 추가** (`_on_ar_toggle` 근처에 배치)

```python
def _on_run_now(self):
    ok, msg = scheduler.run_now()
    if ok:
        messagebox.showinfo(t("app_title"), t("run_now_success_msg"))
    else:
        messagebox.showerror(t("app_title"), t("run_now_failed_msg").format(error=msg))
```

- [x] **Step 6-3: 단위 테스트 — `tests/test_gui_run_now.py` (신규)**

```python
"""tests/test_gui_run_now.py — '지금 실행' 버튼 단위 테스트."""
import os
import pytest
import tkinter as tk

# Headless에서 tkinter 테스트가 깨질 수 있는 환경 가드 (CI에서 DISPLAY 없으면 skip)
if os.name != "nt" and not os.environ.get("DISPLAY"):
    pytest.skip("tkinter requires display", allow_module_level=True)


def _walk(widget):
    yield widget
    for c in widget.winfo_children():
        yield from _walk(c)


def test_run_now_button_exists(monkeypatch):
    """LabelFrame 안에 'run_now_btn' 텍스트의 Button이 존재한다."""
    from src.i18n import t
    from src.gui import WinLayoutSaverApp
    app = WinLayoutSaverApp()
    try:
        labels = [w.cget("text") for w in _walk(app)
                  if isinstance(w, tk.Button)]
        assert t("run_now_btn") in labels
    finally:
        app.destroy()


def test_run_now_calls_scheduler(monkeypatch):
    """_on_run_now → scheduler.run_now() 호출 + 성공 시 showinfo 호출."""
    import src.scheduler as sched_mod
    import src.gui as gui_mod
    from src.gui import WinLayoutSaverApp

    monkeypatch.setattr(sched_mod, "run_now", lambda: (True, "OK"))
    shown = {"info": 0, "error": 0}
    monkeypatch.setattr(gui_mod.messagebox, "showinfo",
                        lambda *a, **kw: shown.__setitem__("info", shown["info"] + 1))
    monkeypatch.setattr(gui_mod.messagebox, "showerror",
                        lambda *a, **kw: shown.__setitem__("error", shown["error"] + 1))

    app = WinLayoutSaverApp()
    try:
        app._on_run_now()
        assert shown["info"] == 1
        assert shown["error"] == 0
    finally:
        app.destroy()


def test_run_now_failure_shows_error(monkeypatch):
    import src.scheduler as sched_mod
    import src.gui as gui_mod
    from src.gui import WinLayoutSaverApp

    monkeypatch.setattr(sched_mod, "run_now", lambda: (False, "작업 없음"))
    shown = {"info": 0, "error": 0, "error_msg": ""}
    monkeypatch.setattr(gui_mod.messagebox, "showinfo",
                        lambda *a, **kw: shown.__setitem__("info", shown["info"] + 1))
    def _err(_t, msg, **kw):
        shown["error"] += 1
        shown["error_msg"] = msg
    monkeypatch.setattr(gui_mod.messagebox, "showerror", _err)

    app = WinLayoutSaverApp()
    try:
        app._on_run_now()
        assert shown["error"] == 1
        assert "작업 없음" in shown["error_msg"]
    finally:
        app.destroy()
```

- [x] **Step 6-4: 테스트 실행**

```
pytest tests/test_gui_run_now.py -q
```

Expected: 3 PASS. (테스트 환경에 디스플레이가 없으면 skip — 본 프로젝트는 Windows 로컬 실행이라 PASS 기대)

- [x] **Step 6-5: 커밋**

```
git add src/gui.py tests/test_gui_run_now.py
git commit -m "feat(Task-14): GUI — Run rollback now button"
```

---

## Task 7: GUI 시작 시 기존 작업 자동 마이그레이션

**근거:** 사용자가 이미 자동복구를 켜둔 상태에서 본 패치를 받으면, **기존 작업의 XML에는 여전히 `<DisallowStartIfOnBatteries>true</>` 가 박혀 있다.** 사용자가 토글을 OFF→ON 해야만 갱신되는데, 사용자 입장에선 "왜 안 되는지" 모를 수 있다. GUI `__init__` 마지막에 한 번 자동 unregister→register 한다.

**조건:**
- `config.auto_rollback.enabled == True` 일 때만 수행
- 마이그레이션 표식(`config.auto_rollback._migrated_v14 == True`)이 이미 있으면 skip → 매번 재등록 방지

**Files:**
- Modify: `src/gui.py`, (config 스키마는 dict이므로 `storage.py` 변경 불필요)
- Test: `tests/test_gui_migrate.py` (신규)

---

- [x] **Step 7-1: `src/gui.py` 의 `__init__` 마지막 줄(`self._poll_monitors()` 직후)에 호출 추가**

```python
self._poll_monitors()
self._migrate_existing_task()   # ← 추가
```

- [x] **Step 7-2: `_migrate_existing_task` 메서드 추가** (클래스 어딘가 적당한 위치)

```python
def _migrate_existing_task(self):
    """
    이전 버전에서 등록된 자동복구 작업은 배터리 옵션이 잘못 박혀 있을 수 있다.
    enabled=True 이면서 _migrated_v14 표식이 없을 때 unregister→register로 1회 재등록.
    """
    config = storage.load_config()
    ar = config.get("auto_rollback", {})
    if not ar.get("enabled", False):
        return
    if ar.get("_migrated_v14", False):
        return

    logger.info(t("migrate_task_log"))

    # frozen vs source 분기 — _on_ar_toggle 와 동일 로직
    if getattr(sys, "frozen", False):
        rollback_exe = str(Path(sys.executable).with_name("WinLayoutSaverRollback.exe"))
        scheduler.unregister()
        ok = scheduler.register(
            script_path="",
            delay_seconds=ar.get("startup_delay_seconds", 10),
            python_exe=rollback_exe,
        )
    else:
        script_path = str(Path(__file__).parent.parent / "cli" / "rollback.py")
        scheduler.unregister()
        ok = scheduler.register(
            script_path=script_path,
            delay_seconds=ar.get("startup_delay_seconds", 10),
        )

    if ok:
        ar["_migrated_v14"] = True
        config["auto_rollback"] = ar
        storage.save_config(config)
        logger.info("scheduler: migration complete (v14)")
    else:
        logger.warning("scheduler: migration failed — will retry on next launch")
```

- [x] **Step 7-3: 단위 테스트 — `tests/test_gui_migrate.py` (신규)**

```python
"""tests/test_gui_migrate.py — GUI __init__ 시 작업 마이그레이션."""
import os
import pytest

if os.name != "nt" and not os.environ.get("DISPLAY"):
    pytest.skip("tkinter requires display", allow_module_level=True)


def test_migrate_runs_when_enabled_and_unflagged(monkeypatch, tmp_path):
    """enabled=True + 표식 없음 → unregister/register 호출, 표식 저장."""
    from src import storage
    import src.scheduler as sched_mod

    config = {"auto_rollback": {"enabled": True, "layout_name": "X",
                                "startup_delay_seconds": 10, "mode": "fast"},
              "ui": {"language": "ko"}}
    monkeypatch.setattr(storage, "load_config", lambda: dict(config))

    saved = {}
    def fake_save(c):
        saved.update(c)
    monkeypatch.setattr(storage, "save_config", fake_save)

    calls = {"unregister": 0, "register": 0}
    monkeypatch.setattr(sched_mod, "unregister",
                        lambda: calls.__setitem__("unregister", calls["unregister"] + 1) or True)
    monkeypatch.setattr(sched_mod, "register",
                        lambda **kw: calls.__setitem__("register", calls["register"] + 1) or True)

    from src.gui import WinLayoutSaverApp
    app = WinLayoutSaverApp()
    try:
        assert calls["unregister"] == 1
        assert calls["register"] == 1
        assert saved["auto_rollback"]["_migrated_v14"] is True
    finally:
        app.destroy()


def test_migrate_skipped_when_already_flagged(monkeypatch):
    """_migrated_v14=True 이면 unregister/register 호출하지 않는다."""
    from src import storage
    import src.scheduler as sched_mod

    config = {"auto_rollback": {"enabled": True, "_migrated_v14": True,
                                "layout_name": "X", "startup_delay_seconds": 10, "mode": "fast"},
              "ui": {"language": "ko"}}
    monkeypatch.setattr(storage, "load_config", lambda: dict(config))
    monkeypatch.setattr(storage, "save_config", lambda c: None)

    calls = {"register": 0, "unregister": 0}
    monkeypatch.setattr(sched_mod, "unregister",
                        lambda: calls.__setitem__("unregister", calls["unregister"] + 1) or True)
    monkeypatch.setattr(sched_mod, "register",
                        lambda **kw: calls.__setitem__("register", calls["register"] + 1) or True)

    from src.gui import WinLayoutSaverApp
    app = WinLayoutSaverApp()
    try:
        assert calls["register"] == 0
        assert calls["unregister"] == 0
    finally:
        app.destroy()


def test_migrate_skipped_when_disabled(monkeypatch):
    """enabled=False 이면 마이그레이션 안 함."""
    from src import storage
    import src.scheduler as sched_mod

    config = {"auto_rollback": {"enabled": False}, "ui": {"language": "ko"}}
    monkeypatch.setattr(storage, "load_config", lambda: dict(config))
    monkeypatch.setattr(storage, "save_config", lambda c: None)

    calls = {"register": 0}
    monkeypatch.setattr(sched_mod, "register",
                        lambda **kw: calls.__setitem__("register", calls["register"] + 1) or True)
    monkeypatch.setattr(sched_mod, "unregister", lambda: True)

    from src.gui import WinLayoutSaverApp
    app = WinLayoutSaverApp()
    try:
        assert calls["register"] == 0
    finally:
        app.destroy()


def test_migrate_failure_keeps_unflagged(monkeypatch):
    """register()가 False를 반환하면 표식을 저장하지 않는다 → 다음 실행에서 재시도."""
    from src import storage
    import src.scheduler as sched_mod

    config = {"auto_rollback": {"enabled": True, "layout_name": "X",
                                "startup_delay_seconds": 10, "mode": "fast"},
              "ui": {"language": "ko"}}
    monkeypatch.setattr(storage, "load_config", lambda: dict(config))

    saved_calls = []
    monkeypatch.setattr(storage, "save_config", lambda c: saved_calls.append(c))

    monkeypatch.setattr(sched_mod, "unregister", lambda: True)
    monkeypatch.setattr(sched_mod, "register", lambda **kw: False)

    from src.gui import WinLayoutSaverApp
    app = WinLayoutSaverApp()
    try:
        # 표식 저장이 일어나지 않아야 함
        assert all("_migrated_v14" not in c.get("auto_rollback", {}) for c in saved_calls)
    finally:
        app.destroy()
```

- [x] **Step 7-4: 테스트 실행**

```
pytest tests/test_gui_migrate.py -q
```

Expected: 4 PASS.

- [x] **Step 7-5: 커밋**

```
git add src/gui.py tests/test_gui_migrate.py
git commit -m "feat(Task-14): GUI — auto-migrate existing AR task on launch"
```

---

## Task 8: 회귀 검증

**근거:** 위 6개 Task의 결합으로 다른 GUI/scheduler 테스트가 깨지지 않았는지 확인.

- [x] **Step 8-1: 전체 테스트 스위트 실행**

```
pytest --tb=short -q
```

Expected: ALL PASS. 깨진 테스트가 있으면:
- 깨진 테스트가 신규 검증 대상이라면 본 Plan에 누락이 있는지 재확인하고 수정
- 무관한 회귀라면 Phase 1(systematic-debugging)로 돌아가 근본 원인 파악

- [x] **Step 8-2: 사용자 수동 검증 절차 안내(README 변경 없이 PR 본문/Plan 메모로만 안내)**

```
1. 코드 pull 후 GUI를 한 번 실행 → 자동 마이그레이션 로그 ('migrate_task_log') 확인
2. GUI에서 "지금 실행" 버튼 클릭 → messagebox '자동 복구 작업을 트리거했습니다' 확인
3. logs/rollback-YYYYMMDD-HHMMSS.log 새 파일 생성 확인
4. schtasks /Query /TN WinLayoutSaver_Rollback /XML | findstr "Battery"
   → <DisallowStartIfOnBatteries>false</> 확인
5. (선택) 노트북을 배터리로 전환 후 재부팅 → 10초 후 logs/rollback-...log 신규 생성 확인
```

- [x] **Step 8-3: 본 Task 완료 표식 커밋**

```
git add Task-14.md
git commit -m "docs(Task-14): mark TodoList completion checkboxes"
```

---

## 4. 위험 / 대응

| 위험 | 대응 |
|------|------|
| 일부 Windows 빌드에서 `New-ScheduledTaskSettingsSet` 의 `-DontStopIfGoingOnBatteries`/`-AllowStartIfOnBatteries` 가 Windows 8 이상에서만 동작 | 본 프로젝트는 Windows 11 대상(README 명시) — 영향 없음. 단위 테스트는 PowerShell 호출이 아닌 문자열 검증이므로 OS 무관. |
| 마이그레이션이 실패하면 사용자는 자동복구가 영구 꺼졌다고 오해 | `register()`가 False를 반환할 때 `_migrated_v14` 표식을 저장하지 않으므로 GUI 다음 실행에서 재시도. 추가로 본 패치의 진단 덤프(Task 2)로 원인 추적 가능. |
| `_on_run_now` 가 messagebox를 띄워 GUI 자동화 테스트 차단 | 테스트에서는 `messagebox.showinfo`/`showerror`를 monkeypatch로 가짜 함수로 교체하므로 차단 없음. |
| `wait_for_shell_ready`가 60초간 부팅을 늘림 | 매 5초 시도 사이에 창이 ≥1개로 보이는 즉시 break 하므로 평균 5~10초. 정 안 되면 60초 후 어차피 진행. trade-off로 받아들임. |

---

## 5. 모호성 제거 메모 (질문/답변 결과)

- **수정 범위 (4개 모두 채택):** 배터리 플래그 / 셸 준비 대기 / register 실패 진단 / "지금 실행" 버튼.
- **기존 등록된 작업 처리:** GUI 시작 시 자동 마이그레이션(Task 7).
- **테스트 깊이:** 단위 테스트만. 통합/E2E 미수행.


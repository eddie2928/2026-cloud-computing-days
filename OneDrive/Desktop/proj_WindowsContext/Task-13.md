# Task-13: 저장 시각 표시 · 매칭 라벨 변경 · 자동복구 LabelFrame · 스크린샷/미리보기 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) 저장된 Screen 행에 `YY.MM.DD/HH:MM:SS` 형식 저장 시각 표시, (2) 모니터 매칭 라벨 `⚠primary` → `⚠Not matched`로 변경, (3) 자동복구 영역을 LabelFrame으로 묶고 활성화 버튼(상단) + grid 옵션 배치, (4) 저장 시 가상 데스크톱 전체 스크린샷을 찍어 PNG로 저장하고 GUI에 "미리보기" 버튼을 추가해 Toplevel 창에 띄움.

**Architecture:**
- `requirements.txt`에 `Pillow>=10` 추가 (`PIL.ImageGrab` + `PIL.ImageTk` 둘 다 사용).
- `src/capture.py`에 `capture_virtual_screen(path)` 함수 신규 추가 — `ImageGrab.grab(all_screens=True)`로 가상 데스크톱 캡처 후 PNG 저장. PIL 미설치 시 `ImportError`를 잡아 `False` 리턴(저장 자체는 실패하지 않음).
- `src/storage.py`에 `screenshot_path(name)` 헬퍼 추가 — `LAYOUTS_DIR / f"{name}.png"` 경로 반환. `delete_layout`에서 PNG도 함께 삭제. `_on_settings`(이름 변경)에서도 PNG 동반 이동 처리는 GUI에서 호출.
- `src/i18n.py`에 4개 키(`saved_at_format`, `not_matched_label`, `preview_btn`, `ar_section_title`, `mode_label`, `screenshot_missing_msg`, `preview_window_title`) 추가.
- `src/gui.py`:
  - `_refresh_layouts`에서 행 렌더링 시 `created_at` 파싱하여 이름 오른쪽·매칭 표시 왼쪽에 Label 삽입.
  - `_get_match_indicator`의 PRIMARY_ONLY 분기 텍스트를 `t("not_matched_label")` 사용해 "⚠Not matched"로 변경.
  - 기존 `ar_frame`(평면 Frame) + `mode_row`(평면 Frame)를 단일 `tk.LabelFrame`로 감싸고 내부를 grid로 재배치(맨 위 활성화 버튼 행, 아래 레이아웃/모드/지연 옵션).
  - 각 레이아웃 행에 "미리보기" 버튼 추가 → `_on_preview(name)`이 Toplevel 창을 띄움.
  - `_on_save`의 워커 스레드에서 `capture.capture_virtual_screen(storage.screenshot_path(name))` 호출.
  - `_on_delete`에서 PNG도 삭제 (storage.delete_layout이 처리).
  - `_on_settings`(rename)에서 PNG도 rename.

**Tech Stack:** Python 3.11+, tkinter, Pillow, pywin32, pytest

**수정 파일 요약:**

| 파일 | 변경 내용 |
|------|----------|
| `requirements.txt` | `Pillow>=10` 추가 |
| `src/capture.py` | `capture_virtual_screen(path) -> bool` 신규 함수 |
| `src/storage.py` | `screenshot_path(name)` 헬퍼 추가, `delete_layout`에서 PNG도 unlink |
| `src/i18n.py` | 7개 키 추가 (ko/en) |
| `src/gui.py` | 저장 시각 Label, "Not matched" 라벨, AR LabelFrame 재구성, 미리보기 버튼/창, save 시 스크린샷 |
| `tests/test_capture.py` | `capture_virtual_screen` 테스트 2개 추가 |
| `tests/test_storage.py` | `screenshot_path` 및 PNG 삭제 테스트 2개 추가 |
| `tests/test_i18n.py` | 신규 키 7개 존재 테스트 추가 |
| `tests/test_gui_saved_at.py` | 신규: 저장 시각 표시 테스트 3개 |
| `tests/test_gui_match_label.py` | 신규: "Not matched" 라벨 테스트 1개 |
| `tests/test_gui_ar_section.py` | 신규: LabelFrame 구조 테스트 4개 |
| `tests/test_gui_preview.py` | 신규: 미리보기 버튼/창 테스트 4개 |

---

## 체크포인트 요약 (중단 후 재개 시 참조)

| Task | 커밋 메시지 접두사 | 완료 조건 |
|------|------------------|----------|
| 0 | `chore(Task-13): add Pillow` | `pip install -r requirements.txt` 성공, `python -c "from PIL import ImageGrab, ImageTk"` 무오류 |
| 1 | `feat(Task-13): capture_virtual_screen` | `pytest tests/test_capture.py` ALL PASS |
| 2 | `feat(Task-13): storage screenshot_path` | `pytest tests/test_storage.py` ALL PASS |
| 3 | `feat(Task-13): i18n` | `pytest tests/test_i18n.py` ALL PASS |
| 4 | `feat(Task-13): GUI saved-at column` | `pytest tests/test_gui_saved_at.py` ALL PASS |
| 5 | `feat(Task-13): match label not_matched` | `pytest tests/test_gui_match_label.py` ALL PASS |
| 6 | `feat(Task-13): AR LabelFrame grid` | `pytest tests/test_gui_ar_section.py tests/test_gui_mode_selector.py tests/test_gui_ar_indicator.py` ALL PASS |
| 7 | `feat(Task-13): preview button + save screenshot` | `pytest tests/test_gui_preview.py` ALL PASS |
| 8 | (회귀) | `pytest --tb=short -q` 전체 PASS |

재개 시 `git log --oneline -10`으로 마지막 완료 커밋을 확인하고 다음 Task의 첫 Step부터 이어서 진행한다.

---

## Task 0: 의존성 추가 (Pillow)

**Files:**
- Modify: `requirements.txt`

---

- [x] **Step 0-1: `requirements.txt`에 Pillow 추가**

```
pywin32>=306
psutil>=5.9
Pillow>=10
```

- [x] **Step 0-2: 설치 및 import 검증**

```
pip install -r requirements.txt
python -c "from PIL import ImageGrab, ImageTk; print('ok')"
```

Expected: 마지막 줄 `ok` 출력. (CI/headless 환경에서 ImageTk가 tkinter 의존이므로 tkinter 설치 필요)

- [x] **Step 0-3: 커밋**

```
git add requirements.txt
git commit -m "chore(Task-13): add Pillow dependency for screenshot capture/preview"
```

---

## Task 1: `capture.py` — 가상 데스크톱 스크린샷 함수

**근거:** 저장 시 모든 모니터를 합친 가상 데스크톱 전체를 PNG로 캡처해야 한다. PIL 미설치 환경(테스트 등)에서도 import는 깨지지 않아야 한다.

**Files:**
- Modify: `src/capture.py` (파일 끝에 신규 함수 추가)
- Test: `tests/test_capture.py`

---

- [x] **Step 1-1: 실패하는 테스트 2개 작성**

`tests/test_capture.py` 파일 끝에 다음을 추가한다 (파일 상단의 import는 이미 `from src import capture`가 있다고 가정 — 없으면 함수 내부에서 `from src.capture import capture_virtual_screen`로 import):

```python
# ─────────────────────────────────────────────────────────────────────────────
# Task-13: capture_virtual_screen (UT-CAP1 ~ UT-CAP2)
# ─────────────────────────────────────────────────────────────────────────────

def test_cap1_capture_virtual_screen_writes_png(tmp_path, monkeypatch):
    """UT-CAP1: capture_virtual_screen(path)는 PIL.ImageGrab.grab을 호출하고 PNG로 저장 후 True 반환."""
    from unittest.mock import MagicMock
    fake_img = MagicMock()
    fake_imagegrab = MagicMock()
    fake_imagegrab.grab.return_value = fake_img

    import sys, types
    fake_pil = types.ModuleType("PIL")
    fake_pil.ImageGrab = fake_imagegrab
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)
    monkeypatch.setitem(sys.modules, "PIL.ImageGrab", fake_imagegrab)

    from src.capture import capture_virtual_screen
    out = tmp_path / "shot.png"
    result = capture_virtual_screen(out)

    assert result is True
    fake_imagegrab.grab.assert_called_once_with(all_screens=True)
    fake_img.save.assert_called_once_with(str(out), "PNG")


def test_cap2_capture_virtual_screen_returns_false_when_pil_missing(tmp_path, monkeypatch):
    """UT-CAP2: PIL import 실패 시 False 반환 (예외 전파 안 함)."""
    import sys
    # PIL을 강제로 ImportError 나도록 제거 + 다시 import 시도 시 실패
    monkeypatch.setitem(sys.modules, "PIL", None)  # None이면 import 시 ImportError

    from src.capture import capture_virtual_screen
    result = capture_virtual_screen(tmp_path / "shot.png")
    assert result is False
```

- [x] **Step 1-2: 테스트 실패 확인**

```
pytest tests/test_capture.py::test_cap1_capture_virtual_screen_writes_png tests/test_capture.py::test_cap2_capture_virtual_screen_returns_false_when_pil_missing -v
```

Expected: 둘 다 `FAILED` — `cannot import name 'capture_virtual_screen' from 'src.capture'`

- [x] **Step 1-3: `src/capture.py` 파일 끝에 함수 추가**

```python


def capture_virtual_screen(path) -> bool:
    """모든 모니터 합친 가상 데스크톱 전체를 PNG로 캡처해 path에 저장.
    PIL 미설치 또는 캡처 실패 시 False 반환 (예외 전파 안 함)."""
    try:
        from PIL import ImageGrab
    except ImportError:
        logger.warning("capture_virtual_screen: Pillow not installed — screenshot skipped")
        return False
    try:
        img = ImageGrab.grab(all_screens=True)
        img.save(str(path), "PNG")
        logger.info("captured virtual screen → %s", path)
        return True
    except Exception as e:
        logger.warning("capture_virtual_screen failed: %s", e)
        return False
```

- [x] **Step 1-4: 테스트 통과 확인**

```
pytest tests/test_capture.py -v
```

Expected: 신규 2개 포함 전체 `PASSED`

- [x] **Step 1-5: 커밋**

```
git add src/capture.py tests/test_capture.py
git commit -m "feat(Task-13): capture_virtual_screen — PIL.ImageGrab으로 가상 데스크톱 PNG 저장"
```

---

## Task 2: `storage.py` — `screenshot_path` 헬퍼 + delete 시 PNG 동반 삭제

**근거:** 스크린샷 경로 규칙(`LAYOUTS_DIR/{name}.png`)을 한 곳에서 관리. layout 삭제 시 PNG도 함께 정리.

**Files:**
- Modify: `src/storage.py`
- Test: `tests/test_storage.py`

---

- [x] **Step 2-1: 실패하는 테스트 2개 작성**

`tests/test_storage.py` 파일 끝에 다음을 추가:

```python
# ─────────────────────────────────────────────────────────────────────────────
# Task-13: screenshot_path + delete 동반 삭제 (UT-ST1 ~ UT-ST2)
# ─────────────────────────────────────────────────────────────────────────────

def test_st1_screenshot_path_returns_png_under_layouts_dir(tmp_appdata):
    from src.storage import screenshot_path, LAYOUTS_DIR
    p = screenshot_path("Screen1")
    assert p == LAYOUTS_DIR / "Screen1.png"


def test_st2_delete_layout_removes_png_too(tmp_appdata):
    from src.storage import save_layout, delete_layout, screenshot_path, LAYOUTS_DIR
    save_layout("Screen1", {"windows": []})
    LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
    png = screenshot_path("Screen1")
    png.write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal png header bytes
    assert png.exists()

    delete_layout("Screen1")

    assert not (LAYOUTS_DIR / "Screen1.json").exists()
    assert not png.exists()
```

- [x] **Step 2-2: 테스트 실패 확인**

```
pytest tests/test_storage.py::test_st1_screenshot_path_returns_png_under_layouts_dir tests/test_storage.py::test_st2_delete_layout_removes_png_too -v
```

Expected: `test_st1` FAILED — `cannot import name 'screenshot_path'`. `test_st2`도 FAILED.

- [x] **Step 2-3: `src/storage.py` 수정**

`screenshot_path` 추가 (기존 `next_layout_name` 함수 바로 위에 삽입):

```python
def screenshot_path(name: str) -> Path:
    """Layout과 짝이 되는 PNG 경로 반환 (실제 파일 존재 여부와 무관)."""
    return LAYOUTS_DIR / f"{name}.png"
```

`delete_layout` 수정:

```python
# 변경 전
def delete_layout(name: str) -> None:
    path = LAYOUTS_DIR / f"{name}.json"
    path.unlink(missing_ok=True)
    logger.info("deleted layout '%s'", name)

# 변경 후
def delete_layout(name: str) -> None:
    json_path = LAYOUTS_DIR / f"{name}.json"
    png_path = LAYOUTS_DIR / f"{name}.png"
    json_path.unlink(missing_ok=True)
    png_path.unlink(missing_ok=True)
    logger.info("deleted layout '%s' (json + png)", name)
```

- [x] **Step 2-4: 테스트 통과 확인**

```
pytest tests/test_storage.py -v
```

Expected: 신규 2개 포함 전체 `PASSED`

- [x] **Step 2-5: 커밋**

```
git add src/storage.py tests/test_storage.py
git commit -m "feat(Task-13): storage — screenshot_path 헬퍼 + delete 시 PNG 동반 제거"
```

---

## Task 3: `i18n.py` — 신규 문자열 7개 추가

**Files:**
- Modify: `src/i18n.py`
- Test: `tests/test_i18n.py`

---

- [x] **Step 3-1: 실패하는 테스트 작성**

`tests/test_i18n.py` 파일 끝에 추가:

```python
def test_task13_strings_present_in_all_languages():
    """Task-13 신규 키가 ko/en 양쪽에 비어있지 않게 존재해야 한다."""
    from src.i18n import STRINGS
    required_keys = (
        "saved_at_format",
        "not_matched_label",
        "preview_btn",
        "ar_section_title",
        "mode_label",
        "screenshot_missing_msg",
        "preview_window_title",
    )
    for lang in ("ko", "en"):
        for key in required_keys:
            assert key in STRINGS[lang], f"'{key}' missing in lang='{lang}'"
            assert STRINGS[lang][key].strip(), f"'{key}' empty in lang='{lang}'"


def test_task13_saved_at_format_is_strftime_compatible():
    """saved_at_format은 strftime 포맷 문자열이어야 한다 (예외 없이 적용 가능)."""
    from datetime import datetime
    from src.i18n import STRINGS
    sample = datetime(2026, 4, 29, 14, 24, 56)
    for lang in ("ko", "en"):
        fmt = STRINGS[lang]["saved_at_format"]
        # 예외 없이 포맷팅돼야 함
        out = sample.strftime(fmt)
        assert out  # 비어있지 않음
        # 명세 형식: "26.04.29/14:24:56"
        assert out == "26.04.29/14:24:56"
```

- [x] **Step 3-2: 테스트 실패 확인**

```
pytest tests/test_i18n.py -v
```

Expected: 신규 2개 `FAILED`.

- [x] **Step 3-3: `src/i18n.py` 수정**

`ko` 딕셔너리의 `mode_full_desc` 다음 줄(line 33 직후)에 추가:

```python
        "mode_full_desc": "없는 앱 자동 실행 후 배치",
        "saved_at_format": "%y.%m.%d/%H:%M:%S",
        "not_matched_label": "⚠Not matched",
        "preview_btn": "미리보기",
        "ar_section_title": "부팅 자동 복구",
        "mode_label": "모드:",
        "screenshot_missing_msg": "이 레이아웃에는 저장된 미리보기 이미지가 없습니다.",
        "preview_window_title": "미리보기 — {name}",
```

`en` 딕셔너리의 `mode_full_desc` 다음 줄에 추가:

```python
        "mode_full_desc": "Launch missing apps, then reposition",
        "saved_at_format": "%y.%m.%d/%H:%M:%S",
        "not_matched_label": "⚠Not matched",
        "preview_btn": "Preview",
        "ar_section_title": "Auto-restore on boot",
        "mode_label": "Mode:",
        "screenshot_missing_msg": "No preview image saved for this layout.",
        "preview_window_title": "Preview — {name}",
```

- [x] **Step 3-4: 테스트 통과 확인**

```
pytest tests/test_i18n.py -v
```

Expected: 전체 `PASSED`

- [x] **Step 3-5: 커밋**

```
git add src/i18n.py tests/test_i18n.py
git commit -m "feat(Task-13): i18n — saved_at, not_matched, preview, AR section 등 7개 키 추가"
```

---

## Task 4: GUI — 저장 시각 컬럼 표시

**근거:** 각 layout 행의 이름 오른쪽에 `26.04.29/14:24:56` 형식 라벨 추가. `created_at`(ISO 8601)을 파싱하여 i18n 포맷으로 변환. 파싱 실패 시 빈 문자열.

**Files:**
- Modify: `src/gui.py`
- Test: `tests/test_gui_saved_at.py` (신규)

---

- [x] **Step 4-1: 신규 테스트 파일 생성**

`tests/test_gui_saved_at.py`:

```python
"""Task-13: layout 행에 저장 시각 표시 테스트."""
import pytest

tk = pytest.importorskip("tkinter")


def _make_app(monkeypatch, layouts, layout_payloads):
    """layout_payloads: {name: layout_dict} — load_layout 모킹용."""
    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"enabled": False, "layout_name": "", "mode": "fast", "startup_delay_seconds": 10},
        "ui": {"language": "ko"},
    })
    monkeypatch.setattr("src.storage.list_layouts", lambda: layouts)
    monkeypatch.setattr("src.storage.load_layout", lambda n: layout_payloads.get(n, {}))
    monkeypatch.setattr("src.storage.save_config", lambda _: None)
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])

    from src.gui import WinLayoutSaverApp
    try:
        return WinLayoutSaverApp()
    except tk.TclError:
        pytest.skip("display unavailable")


def _all_label_texts(widget):
    """위젯 트리를 재귀 순회하며 모든 tk.Label의 cget('text')를 수집."""
    texts = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            texts.append(child.cget("text"))
        texts.extend(_all_label_texts(child))
    return texts


def test_sa1_saved_at_label_renders_iso_as_yymmdd_format(monkeypatch):
    """UT-SA1: created_at='2026-04-29T14:24:56+09:00'이면 '26.04.29/14:24:56' Label이 행에 렌더링된다."""
    payload = {"Screen1": {"name": "Screen1", "created_at": "2026-04-29T14:24:56+09:00", "windows": [], "monitors": []}}
    app = _make_app(monkeypatch, ["Screen1"], payload)
    try:
        app._refresh_layouts()
        texts = _all_label_texts(app._layout_inner)
        assert "26.04.29/14:24:56" in texts
    finally:
        app.destroy()


def test_sa2_saved_at_label_empty_when_created_at_missing(monkeypatch):
    """UT-SA2: created_at 키가 없으면 시각 Label은 빈 문자열로 표시(예외 없음)."""
    payload = {"Screen1": {"name": "Screen1", "windows": [], "monitors": []}}
    app = _make_app(monkeypatch, ["Screen1"], payload)
    try:
        app._refresh_layouts()
        texts = _all_label_texts(app._layout_inner)
        # "26.04.29/..." 같은 시각 라벨이 없어야 하고, 어떤 위젯도 깨지지 않아야 함
        assert not any("/" in t and ":" in t and "." in t for t in texts if t)
    finally:
        app.destroy()


def test_sa3_saved_at_label_empty_when_created_at_unparseable(monkeypatch):
    """UT-SA3: created_at이 ISO가 아니면 빈 문자열 (예외 전파 안 함)."""
    payload = {"Screen1": {"name": "Screen1", "created_at": "not-a-date", "windows": [], "monitors": []}}
    app = _make_app(monkeypatch, ["Screen1"], payload)
    try:
        app._refresh_layouts()  # 예외 안 나야 함
    finally:
        app.destroy()
```

- [x] **Step 4-2: 테스트 실패 확인**

```
pytest tests/test_gui_saved_at.py -v
```

Expected: `test_sa1` FAILED (해당 텍스트 없음), 나머지는 현재 코드에서 우연히 PASS할 수도 있음.

- [x] **Step 4-3: `src/gui.py` — 헬퍼 메서드 + 행 렌더링 수정**

`_get_match_indicator` 메서드 **바로 앞**에 헬퍼 추가:

```python
    def _format_saved_at(self, name: str) -> str:
        """layout의 created_at(ISO 8601)을 i18n 포맷('%y.%m.%d/%H:%M:%S')으로 변환.
        파싱 실패 또는 키 부재 시 빈 문자열."""
        try:
            layout = storage.load_layout(name)
            iso = layout.get("created_at")
            if not iso:
                return ""
            dt = datetime.fromisoformat(iso)
            return dt.strftime(t("saved_at_format"))
        except Exception:
            return ""
```

`_refresh_layouts` 내 layout 행 렌더링 부분 수정 (이름 Label 다음, 매칭 indicator 이전에 시각 Label 삽입):

```python
# 변경 전 (gui.py:175-180)
                tk.Radiobutton(row, variable=radio_var, value=1, state=tk.DISABLED).pack(side=tk.LEFT)
                tk.Label(row, text=name, width=16, anchor="w").pack(side=tk.LEFT)

                # Per-layout monitor match indicator
                match_text, match_color = self._get_match_indicator(name)
                tk.Label(row, text=match_text, fg=match_color, width=12, anchor="w").pack(side=tk.LEFT)

# 변경 후
                tk.Radiobutton(row, variable=radio_var, value=1, state=tk.DISABLED).pack(side=tk.LEFT)
                tk.Label(row, text=name, width=16, anchor="w").pack(side=tk.LEFT)

                # 저장 시각
                saved_at = self._format_saved_at(name)
                tk.Label(row, text=saved_at, width=18, anchor="w",
                         fg="#666", font=("Consolas", 9)).pack(side=tk.LEFT)

                # Per-layout monitor match indicator
                match_text, match_color = self._get_match_indicator(name)
                tk.Label(row, text=match_text, fg=match_color, width=14, anchor="w").pack(side=tk.LEFT)
```

(매칭 indicator의 width를 12 → 14로 늘려 "⚠Not matched" 잘림 방지.)

- [x] **Step 4-4: 테스트 통과 확인**

```
pytest tests/test_gui_saved_at.py -v
```

Expected: 3개 모두 `PASSED`

- [x] **Step 4-5: 커밋**

```
git add src/gui.py tests/test_gui_saved_at.py
git commit -m "feat(Task-13): GUI — layout 행에 저장 시각(YY.MM.DD/HH:MM:SS) Label 추가"
```

---

## Task 5: GUI — 매칭 라벨 "⚠primary" → "⚠Not matched"

**근거:** 사용자 관점에서 "primary"는 의미가 모호. PRIMARY_ONLY는 "주 모니터만 일치(외부 다름)"이므로 "Not matched"가 더 직관적.

**Files:**
- Modify: `src/gui.py:_get_match_indicator`
- Test: `tests/test_gui_match_label.py` (신규)

---

- [x] **Step 5-1: 신규 테스트 파일 생성**

`tests/test_gui_match_label.py`:

```python
"""Task-13: PRIMARY_ONLY 라벨이 'Not matched'로 표시되는지."""
import pytest


def test_ml1_primary_only_returns_not_matched_text(monkeypatch):
    """UT-ML1: compare_monitors가 PRIMARY_ONLY를 반환하면 indicator 텍스트가 'Not matched' 포함."""
    pytest.importorskip("tkinter")
    import tkinter as tk

    from src.monitors import MatchResult

    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"enabled": False, "layout_name": "", "mode": "fast", "startup_delay_seconds": 10},
        "ui": {"language": "ko"},
    })
    monkeypatch.setattr("src.storage.list_layouts", lambda: ["Screen1"])
    monkeypatch.setattr("src.storage.load_layout",
                        lambda n: {"monitors": [{"index": 0, "primary": True, "rect": [0, 0, 100, 100]}]})
    monkeypatch.setattr("src.storage.save_config", lambda _: None)
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [{"index": 0, "primary": True, "rect": [0, 0, 100, 100]}])
    # compare_monitors를 src.gui가 import해서 쓰므로 거기를 패치
    monkeypatch.setattr("src.gui.compare_monitors", lambda saved, current: MatchResult.PRIMARY_ONLY)

    from src.gui import WinLayoutSaverApp
    try:
        app = WinLayoutSaverApp()
    except tk.TclError:
        pytest.skip("display unavailable")
    try:
        # _current_monitors가 비어있으면 "" 반환하므로 채워줌
        app._current_monitors = [{"index": 0, "primary": True, "rect": [0, 0, 100, 100]}]
        text, color = app._get_match_indicator("Screen1")
        assert "Not matched" in text
        assert color == "orange"
    finally:
        app.destroy()
```

- [x] **Step 5-2: 테스트 실패 확인**

```
pytest tests/test_gui_match_label.py -v
```

Expected: FAILED — `'Not matched' in '⚠primary'` 단언 실패.

- [x] **Step 5-3: `src/gui.py` 수정**

```python
# 변경 전 (gui.py:241-244)
            elif result == MatchResult.PRIMARY_ONLY:
                return ("⚠primary", "orange")
            else:
                return ("⚠mismatch", "red")

# 변경 후
            elif result == MatchResult.PRIMARY_ONLY:
                return (t("not_matched_label"), "orange")
            else:
                return ("⚠mismatch", "red")
```

또한 `_on_restore`에서 match_text 비교 부분(`if match_text in ("⚠primary", "⚠mismatch"):`)도 함께 갱신:

```python
# 변경 전 (gui.py:275)
        if match_text in ("⚠primary", "⚠mismatch"):

# 변경 후
        if match_text in (t("not_matched_label"), "⚠mismatch"):
```

- [x] **Step 5-4: 테스트 통과 확인**

```
pytest tests/test_gui_match_label.py -v
```

Expected: PASSED

- [x] **Step 5-5: 커밋**

```
git add src/gui.py tests/test_gui_match_label.py
git commit -m "feat(Task-13): GUI — PRIMARY_ONLY 라벨을 'Not matched'로 변경 (i18n)"
```

---

## Task 6: GUI — 자동복구 LabelFrame + grid 재배치

**근거:** 현재 `ar_frame`(평면 Frame)과 `mode_row`(평면 Frame)가 따로 떠 있어 가독성이 낮다. 단일 `tk.LabelFrame`(제목 "부팅 자동 복구") 안으로 묶고, 활성화 버튼을 맨 위, 옵션들을 아래쪽 grid로 정렬.

**레이아웃 명세:**

```
┌─ 부팅 자동 복구 ─────────────────────────────────────────┐
│ [ 활성화 ]                                              │   ← 행 0
│                                                         │
│ 레이아웃:    [combobox ▼]                               │   ← 행 1
│ 모드:        (•) 빠른 복구  ( ) 전체 복구   설명 텍스트 │   ← 행 2
│ 시작 지연:   [10] 초                                    │   ← 행 3
└─────────────────────────────────────────────────────────┘
```

**기존 위젯 변수명/레퍼런스는 모두 그대로 유지** (`_ar_combo`, `_ar_toggle_btn`, `_ar_layout_var`, `_ar_mode_var`, `_ar_mode_fast_rb`, `_ar_mode_full_rb`, `_delay_entry`, `_delay_var`, `_mode_desc_var`) — 기존 테스트(`test_gui_mode_selector.py`, `test_gui_ar_indicator.py`)가 깨지지 않도록.

**Files:**
- Modify: `src/gui.py:_build_ui`
- Test: `tests/test_gui_ar_section.py` (신규)

---

- [x] **Step 6-1: 신규 테스트 파일 생성**

`tests/test_gui_ar_section.py`:

```python
"""Task-13: 자동복구 LabelFrame 구조 테스트."""
import pytest

tk = pytest.importorskip("tkinter")


def _make_app(monkeypatch):
    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"enabled": False, "layout_name": "", "mode": "fast", "startup_delay_seconds": 10},
        "ui": {"language": "ko"},
    })
    monkeypatch.setattr("src.storage.list_layouts", lambda: ["Screen1"])
    monkeypatch.setattr("src.storage.save_config", lambda _: None)
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])
    from src.gui import WinLayoutSaverApp
    try:
        return WinLayoutSaverApp()
    except tk.TclError:
        pytest.skip("display unavailable")


def test_ars1_ar_section_is_labelframe(monkeypatch):
    """UT-ARS1: 자동복구 컨테이너가 LabelFrame이고 _ar_section 속성으로 노출된다."""
    app = _make_app(monkeypatch)
    try:
        assert hasattr(app, "_ar_section"), "_ar_section 속성 없음"
        assert isinstance(app._ar_section, tk.LabelFrame)
        # 제목이 i18n에서 옴
        title = str(app._ar_section.cget("text"))
        assert title  # 비어있지 않음
    finally:
        app.destroy()


def test_ars2_toggle_button_is_inside_ar_section(monkeypatch):
    """UT-ARS2: _ar_toggle_btn은 _ar_section의 자식(또는 자손)이어야 한다."""
    app = _make_app(monkeypatch)
    try:
        def _is_descendant(widget, ancestor):
            w = widget
            while w is not None:
                if w is ancestor:
                    return True
                w = w.master
            return False
        assert _is_descendant(app._ar_toggle_btn, app._ar_section)
    finally:
        app.destroy()


def test_ars3_options_inside_ar_section(monkeypatch):
    """UT-ARS3: 콤보·라디오·delay entry 모두 _ar_section의 자손이다."""
    app = _make_app(monkeypatch)
    try:
        def _is_descendant(widget, ancestor):
            w = widget
            while w is not None:
                if w is ancestor:
                    return True
                w = w.master
            return False
        for w in (app._ar_combo, app._ar_mode_fast_rb, app._ar_mode_full_rb, app._delay_entry):
            assert _is_descendant(w, app._ar_section), f"{w!r} not in _ar_section"
    finally:
        app.destroy()


def test_ars4_existing_lock_logic_still_works(monkeypatch):
    """UT-ARS4: LabelFrame 재배치 후에도 _apply_ar_toggle_style이 모든 옵션을 정상적으로 잠근다."""
    app = _make_app(monkeypatch)
    try:
        app._apply_ar_toggle_style(True)
        assert app._delay_entry.cget("state") == "disabled"
        assert app._ar_combo.cget("state") == "disabled"
        assert app._ar_mode_fast_rb.cget("state") == "disabled"
        assert app._ar_mode_full_rb.cget("state") == "disabled"

        app._apply_ar_toggle_style(False)
        assert app._delay_entry.cget("state") == "normal"
        assert app._ar_combo.cget("state") == "readonly"
        assert app._ar_mode_fast_rb.cget("state") == "normal"
        assert app._ar_mode_full_rb.cget("state") == "normal"
    finally:
        app.destroy()
```

- [x] **Step 6-2: 테스트 실패 확인**

```
pytest tests/test_gui_ar_section.py -v
```

Expected: ARS1~ARS3 FAILED. ARS4는 (기존 위젯 유지하므로) PASS 가능.

- [x] **Step 6-3: `src/gui.py:_build_ui` 재구성**

기존 `ar_frame` 블록(line 68-80)과 `mode_row` 블록(line 82-102)을 모두 다음으로 **교체**:

```python
        # ─── Auto-rollback section (LabelFrame) ───────────────────────────
        self._ar_section = tk.LabelFrame(self, text=t("ar_section_title"), padx=8, pady=6)
        self._ar_section.pack(fill=tk.X, padx=8, pady=4)

        # 행 0: 활성화 버튼 (가로 전체)
        self._ar_toggle_btn = tk.Button(self._ar_section, text=t("enable_btn"), command=self._on_ar_toggle)
        self._ar_toggle_btn.grid(row=0, column=0, columnspan=4, sticky="we", pady=(0, 6))

        # 행 1: 레이아웃 라벨 + 콤보
        tk.Label(self._ar_section, text=t("auto_rollback_label")).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
        self._ar_layout_var = tk.StringVar()
        self._ar_combo = ttk.Combobox(self._ar_section, textvariable=self._ar_layout_var, state="readonly", width=16)
        self._ar_combo.grid(row=1, column=1, columnspan=3, sticky="w", pady=2)

        # 행 2: 모드 라벨 + Radio 2개 + 설명
        tk.Label(self._ar_section, text=t("mode_label")).grid(row=2, column=0, sticky="w", padx=(0, 6), pady=2)
        self._ar_mode_var = tk.StringVar(value="fast")
        self._ar_mode_fast_rb = tk.Radiobutton(
            self._ar_section, text=t("mode_fast"),
            variable=self._ar_mode_var, value="fast",
            command=self._on_mode_change,
        )
        self._ar_mode_fast_rb.grid(row=2, column=1, sticky="w", pady=2)
        self._ar_mode_full_rb = tk.Radiobutton(
            self._ar_section, text=t("mode_full"),
            variable=self._ar_mode_var, value="full",
            command=self._on_mode_change,
        )
        self._ar_mode_full_rb.grid(row=2, column=2, sticky="w", padx=(8, 0), pady=2)
        self._mode_desc_var = tk.StringVar()
        tk.Label(
            self._ar_section, textvariable=self._mode_desc_var,
            fg="#555", font=("Consolas", 9),
        ).grid(row=2, column=3, sticky="w", padx=(16, 0), pady=2)

        # 행 3: 시작 지연 라벨 + Entry
        tk.Label(self._ar_section, text=t("startup_delay_label")).grid(row=3, column=0, sticky="w", padx=(0, 6), pady=2)
        self._delay_var = tk.StringVar(value="10")
        self._delay_entry = tk.Entry(self._ar_section, textvariable=self._delay_var, width=5)
        self._delay_entry.grid(row=3, column=1, sticky="w", pady=2)
        # ───────────────────────────────────────────────────────────────────
```

(즉 기존 ar_frame, mode_row 두 블록을 통째로 위 블록으로 대체. status bar 이후 코드는 변경 없음.)

- [x] **Step 6-4: 테스트 통과 확인**

```
pytest tests/test_gui_ar_section.py tests/test_gui_mode_selector.py tests/test_gui_ar_indicator.py -v
```

Expected: 모두 `PASSED` (기존 mode_selector·ar_indicator 회귀 없음 포함).

- [x] **Step 6-5: 커밋**

```
git add src/gui.py tests/test_gui_ar_section.py
git commit -m "feat(Task-13): GUI — 자동복구 영역 LabelFrame + grid 재배치 (활성화 버튼 상단)"
```

---

## Task 7: GUI — 미리보기 버튼 + 저장 시 스크린샷

**근거:** 각 layout 행에 "미리보기" 버튼 추가, 클릭 시 Toplevel 창에 PNG 표시. `_on_save`에서 layout JSON 저장 직후 동일 경로(`screenshot_path`)에 PIL 캡처. PNG 파일 부재 시 메시지 박스로 안내.

**Files:**
- Modify: `src/gui.py` (`_refresh_layouts` 행 렌더링, `_on_save`, 신규 `_on_preview` 메서드)
- Test: `tests/test_gui_preview.py` (신규)

---

- [x] **Step 7-1: 신규 테스트 파일 생성**

`tests/test_gui_preview.py`:

```python
"""Task-13: 미리보기 버튼 + Toplevel 창 + 저장 시 스크린샷 캡처 테스트."""
import pytest

tk = pytest.importorskip("tkinter")


def _make_app(monkeypatch, tmp_path, layouts=None, capture_return=True):
    if layouts is None:
        layouts = ["Screen1"]
    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"enabled": False, "layout_name": "", "mode": "fast", "startup_delay_seconds": 10},
        "ui": {"language": "ko"},
    })
    monkeypatch.setattr("src.storage.list_layouts", lambda: layouts)
    monkeypatch.setattr("src.storage.load_layout", lambda n: {"name": n, "windows": [], "monitors": []})
    monkeypatch.setattr("src.storage.save_config", lambda _: None)
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])

    # screenshot_path가 tmp_path 안으로 가도록
    monkeypatch.setattr("src.storage.screenshot_path",
                        lambda name: tmp_path / f"{name}.png")

    from src.gui import WinLayoutSaverApp
    try:
        return WinLayoutSaverApp()
    except tk.TclError:
        pytest.skip("display unavailable")


def _find_buttons_with_text(widget, text):
    """위젯 트리에서 cget('text')==text인 tk.Button 모두 반환."""
    found = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Button) and str(child.cget("text")) == text:
            found.append(child)
        found.extend(_find_buttons_with_text(child, text))
    return found


def test_pv1_preview_button_appears_for_each_layout(monkeypatch, tmp_path):
    """UT-PV1: 각 layout 행에 '미리보기' 버튼이 1개씩 렌더링된다."""
    app = _make_app(monkeypatch, tmp_path, layouts=["Screen1", "Screen2"])
    try:
        from src.i18n import t
        btns = _find_buttons_with_text(app._layout_inner, t("preview_btn"))
        assert len(btns) == 2
    finally:
        app.destroy()


def test_pv2_preview_shows_messagebox_when_png_missing(monkeypatch, tmp_path):
    """UT-PV2: PNG 파일이 없으면 messagebox.showinfo 호출, Toplevel은 띄우지 않음."""
    app = _make_app(monkeypatch, tmp_path)
    try:
        called = {}
        def fake_showinfo(title, message, **kw):
            called["title"] = title
            called["message"] = message
        monkeypatch.setattr("tkinter.messagebox.showinfo", fake_showinfo)

        toplevel_count_before = len([w for w in app.winfo_children() if isinstance(w, tk.Toplevel)])
        app._on_preview("Screen1")  # PNG 없음
        toplevel_count_after = len([w for w in app.winfo_children() if isinstance(w, tk.Toplevel)])

        assert "message" in called
        assert toplevel_count_after == toplevel_count_before  # 새 창 없음
    finally:
        app.destroy()


def test_pv3_preview_opens_toplevel_when_png_exists(monkeypatch, tmp_path):
    """UT-PV3: PNG 파일이 있으면 Toplevel 창을 띄운다."""
    app = _make_app(monkeypatch, tmp_path)
    try:
        # 1x1 흰색 PNG 생성
        png_path = tmp_path / "Screen1.png"
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")
        Image.new("RGB", (10, 10), "white").save(str(png_path), "PNG")

        before = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]
        app._on_preview("Screen1")
        after = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]

        assert len(after) == len(before) + 1
        # 정리
        for w in after:
            if w not in before:
                w.destroy()
    finally:
        app.destroy()


def test_pv4_on_save_calls_capture_virtual_screen(monkeypatch, tmp_path):
    """UT-PV4: _on_save 워커가 capture_virtual_screen(screenshot_path)을 호출한다."""
    captured = {}

    def fake_capture(path):
        captured["path"] = path
        return True

    # capture / list_current_windows / save_layout / next_layout_name 모킹
    monkeypatch.setattr("src.capture.list_current_windows", lambda: [])
    monkeypatch.setattr("src.capture.capture_virtual_screen", fake_capture)
    monkeypatch.setattr("src.storage.save_layout", lambda name, layout: None)
    monkeypatch.setattr("src.storage.next_layout_name", lambda: "Screen99")

    app = _make_app(monkeypatch, tmp_path)
    try:
        # _on_save 내부 worker 함수를 동기적으로 호출 (Thread 우회)
        # — 이를 위해 threading.Thread를 즉시 실행하는 가짜로 교체
        class _ImmediateThread:
            def __init__(self, target, daemon=None):
                self._target = target
            def start(self):
                self._target()
        monkeypatch.setattr("src.gui.threading.Thread", _ImmediateThread)

        app._on_save()

        from pathlib import Path
        assert "path" in captured
        assert captured["path"] == tmp_path / "Screen99.png"
    finally:
        app.destroy()
```

- [x] **Step 7-2: 테스트 실패 확인**

```
pytest tests/test_gui_preview.py -v
```

Expected: 4개 모두 `FAILED` (`_on_preview` 없음 / 미리보기 버튼 없음 / capture 호출 안 함).

- [x] **Step 7-3: `src/gui.py` — `_on_preview` 메서드 추가**

`_apply_ar_toggle_style` 메서드 **바로 앞**(즉 `_on_mode_change` 다음)에 추가:

```python
    def _on_preview(self, name: str):
        """선택한 layout의 PNG 스크린샷을 Toplevel 창에 표시.
        파일이 없으면 messagebox로 안내."""
        png_path = storage.screenshot_path(name)
        if not png_path.exists():
            messagebox.showinfo(
                t("preview_window_title", name=name),
                t("screenshot_missing_msg"),
                parent=self,
            )
            return
        try:
            from PIL import Image, ImageTk
        except ImportError:
            messagebox.showinfo(
                t("preview_window_title", name=name),
                "Pillow not installed",
                parent=self,
            )
            return

        try:
            img = Image.open(str(png_path))
            # 화면에 너무 크면 1280x720 박스에 맞게 비율 유지 축소
            max_w, max_h = 1280, 720
            w, h = img.size
            scale = min(max_w / w, max_h / h, 1.0)
            if scale < 1.0:
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            top = tk.Toplevel(self)
            top.title(t("preview_window_title", name=name))
            photo = ImageTk.PhotoImage(img, master=top)
            lbl = tk.Label(top, image=photo)
            lbl.image = photo  # GC 방지
            lbl.pack()
            tk.Button(top, text="Close", command=top.destroy).pack(pady=4)
        except Exception as e:
            logger.error("preview failed for '%s': %s", name, e)
            messagebox.showinfo(
                t("preview_window_title", name=name),
                str(e),
                parent=self,
            )
```

- [x] **Step 7-4: `src/gui.py` — `_refresh_layouts`에 미리보기 버튼 추가**

복원/설정/삭제 버튼 줄(line 182-184) **바로 앞**에 미리보기 버튼 추가:

```python
# 변경 전
                tk.Button(row, text=t("restore_btn"), command=lambda n=name: self._on_restore(n)).pack(side=tk.LEFT, padx=2)
                tk.Button(row, text=t("settings_btn"), command=lambda n=name: self._on_settings(n)).pack(side=tk.LEFT, padx=2)
                tk.Button(row, text=t("delete_btn"), command=lambda n=name: self._on_delete(n)).pack(side=tk.LEFT, padx=2)

# 변경 후
                tk.Button(row, text=t("preview_btn"), command=lambda n=name: self._on_preview(n)).pack(side=tk.LEFT, padx=2)
                tk.Button(row, text=t("restore_btn"), command=lambda n=name: self._on_restore(n)).pack(side=tk.LEFT, padx=2)
                tk.Button(row, text=t("settings_btn"), command=lambda n=name: self._on_settings(n)).pack(side=tk.LEFT, padx=2)
                tk.Button(row, text=t("delete_btn"), command=lambda n=name: self._on_delete(n)).pack(side=tk.LEFT, padx=2)
```

- [x] **Step 7-5: `src/gui.py` — `_on_save` 워커에서 스크린샷 캡처 추가**

`_on_save` 내부 `_work` 함수를 다음으로 변경:

```python
# 변경 전 (gui.py:251-268)
    def _on_save(self):
        logger.info("user clicked Save")
        def _work():
            try:
                windows = capture.list_current_windows()
                monitors = list_current_monitors()
                name = storage.next_layout_name()
                layout = {
                    "name": name,
                    "created_at": datetime.now().astimezone().isoformat(),
                    "monitors": monitors,
                    "windows": windows,
                }
                storage.save_layout(name, layout)
                self.after(0, lambda: self._status_var.set(t("layout_saved", name=name, count=len(windows))))
                self.after(0, self._refresh_layouts)
            except Exception as e:
                logger.error("save failed: %s", e)
        threading.Thread(target=_work, daemon=True).start()

# 변경 후
    def _on_save(self):
        logger.info("user clicked Save")
        def _work():
            try:
                windows = capture.list_current_windows()
                monitors = list_current_monitors()
                name = storage.next_layout_name()
                layout = {
                    "name": name,
                    "created_at": datetime.now().astimezone().isoformat(),
                    "monitors": monitors,
                    "windows": windows,
                }
                storage.save_layout(name, layout)
                # 가상 데스크톱 전체 PNG 스크린샷 (실패해도 저장 자체는 성공으로 간주)
                try:
                    capture.capture_virtual_screen(storage.screenshot_path(name))
                except Exception as e:
                    logger.warning("screenshot capture skipped: %s", e)
                self.after(0, lambda: self._status_var.set(t("layout_saved", name=name, count=len(windows))))
                self.after(0, self._refresh_layouts)
            except Exception as e:
                logger.error("save failed: %s", e)
        threading.Thread(target=_work, daemon=True).start()
```

- [x] **Step 7-6: `src/gui.py` — `_on_settings`(rename)에서 PNG도 이동**

```python
# 변경 전 (gui.py:307-319)
    def _on_settings(self, name: str):
        new_name = simpledialog.askstring(t("rename_dialog_title"), t("rename_label"), initialvalue=name, parent=self)
        if new_name and new_name != name:
            def _work():
                try:
                    layout = storage.load_layout(name)
                    layout["name"] = new_name
                    storage.save_layout(new_name, layout)
                    storage.delete_layout(name)
                    self.after(0, self._refresh_layouts)
                except Exception as e:
                    logger.error("rename failed: %s", e)
            threading.Thread(target=_work, daemon=True).start()

# 변경 후
    def _on_settings(self, name: str):
        new_name = simpledialog.askstring(t("rename_dialog_title"), t("rename_label"), initialvalue=name, parent=self)
        if new_name and new_name != name:
            def _work():
                try:
                    layout = storage.load_layout(name)
                    layout["name"] = new_name
                    storage.save_layout(new_name, layout)
                    # PNG 동반 이동 (있을 때만)
                    old_png = storage.screenshot_path(name)
                    new_png = storage.screenshot_path(new_name)
                    if old_png.exists():
                        try:
                            old_png.replace(new_png)
                        except OSError as e:
                            logger.warning("png rename failed: %s", e)
                    storage.delete_layout(name)  # 남아있을 수 있는 잔여물 정리
                    self.after(0, self._refresh_layouts)
                except Exception as e:
                    logger.error("rename failed: %s", e)
            threading.Thread(target=_work, daemon=True).start()
```

- [x] **Step 7-7: 테스트 통과 확인**

```
pytest tests/test_gui_preview.py -v
```

Expected: 4개 모두 `PASSED`.

- [x] **Step 7-8: 커밋**

```
git add src/gui.py tests/test_gui_preview.py
git commit -m "feat(Task-13): GUI — 저장 시 가상 데스크톱 스크린샷 캡처 + 미리보기 버튼/Toplevel 창"
```

---

## Task 8: 전체 회귀 검증

- [x] **Step 8-1: 전체 테스트 스위트 실행**

```
pytest --tb=short -q
```

Expected: 모든 테스트 `PASSED`, `0 failed`.

실패 시 오류 메시지를 확인하고 해당 Task로 돌아가 수정한다. 자주 발생할 수 있는 회귀:

| 증상 | 의심 위치 |
|------|-----------|
| `AttributeError: '_ar_section'` | Task 6의 `_build_ui` 재구성에서 변수명 오타 |
| `_get_match_indicator returns "⚠primary"` | Task 5 미적용 |
| `KeyError: 'mode_label'` 등 | Task 3의 i18n 키 누락 |
| `capture_virtual_screen 호출 안 됨` | Task 7-5 워커 변경 누락 |

- [ ] **Step 8-2: GUI 수동 점검 (선택)**

```
python main.py
```

확인 항목:
1. 저장 클릭 → 새 Screen 행에 `26.04.29/HH:MM:SS` 형식 시각이 보인다.
2. 같은 행에 "미리보기" 버튼이 있고 클릭 시 Toplevel 창에 캡처된 화면이 뜬다.
3. 모니터 매칭이 PRIMARY_ONLY 상황에서 라벨이 "⚠Not matched"로 표시된다.
4. "부팅 자동 복구" LabelFrame 안에 활성화 버튼(상단) + 레이아웃/모드/지연 옵션이 grid로 정렬되어 보인다.
5. 활성화 버튼 누른 뒤 콤보·라디오·entry 모두 disabled로 잠긴다.

- [ ] **Step 8-3: 최종 커밋 (필요 시)**

회귀 수정이 있었던 경우만:

```
git add -p
git commit -m "fix(Task-13): 전체 회귀 테스트 통과"
```

---

## 부록: 데이터 흐름 검증 메모

**Save 흐름:**

```
사용자 [현재 배치 저장] 클릭
  → _on_save() worker
      → capture.list_current_windows()
      → list_current_monitors()
      → storage.next_layout_name() → "ScreenN"
      → storage.save_layout("ScreenN", layout_dict)   # JSON
      → capture.capture_virtual_screen(LAYOUTS_DIR/"ScreenN.png")  # PNG
      → self.after(0, _refresh_layouts)
          → 행 렌더링: Radio | name | created_at_label | match_label
                       | [미리보기] [복원] [설정] [삭제]
```

**Preview 흐름:**

```
사용자 [미리보기] 클릭
  → _on_preview("ScreenN")
      → png = storage.screenshot_path("ScreenN")
      → if not png.exists(): showinfo("저장된 미리보기 없음")
      → else:
          PIL.Image.open(png) → 비율 유지로 1280x720 이내 축소
          ImageTk.PhotoImage(img, master=top)
          tk.Toplevel(self) + Label(image=photo) + Close 버튼
```

**Delete/Rename 정리:**

- delete: `storage.delete_layout`이 JSON + PNG 모두 unlink (Task 2).
- rename: GUI에서 `old_png.replace(new_png)` 후 기존 layout delete (Task 7-6).

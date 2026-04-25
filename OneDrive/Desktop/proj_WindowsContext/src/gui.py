import logging
import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, scrolledtext, ttk

from src import storage, capture, restore as restore_mod, scheduler
from src.i18n import t, set_language
from src.logging_setup import setup_logging
from src.monitors import list_current_monitors, compare_monitors, MatchResult
from src.paths import LOGS_DIR

logger = logging.getLogger("gui")


class WinLayoutSaverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self._log_queue: queue.Queue = queue.Queue()
        setup_logging(enable_gui_handler=True, gui_queue=self._log_queue)

        config = storage.load_config()
        lang = config.get("ui", {}).get("language", "ko")
        set_language(lang)

        self.title(t("app_title"))
        self.geometry("800x600")
        self.resizable(True, True)

        self._current_monitors: list[dict] = []

        self._build_ui()
        self._refresh_layouts()
        self._drain_log_queue()
        self._poll_monitors()

    # ── UI construction ─────────────────────────────────────────────────

    def _build_ui(self):
        # Monitor strip
        self._monitor_strip_var = tk.StringVar(value="Monitors: detecting…")
        tk.Label(self, textvariable=self._monitor_strip_var, anchor="w", fg="#444",
                 font=("Consolas", 9)).pack(fill=tk.X, padx=8, pady=(4, 0))

        # Top toolbar
        toolbar = tk.Frame(self, pady=4)
        toolbar.pack(fill=tk.X, padx=8)
        tk.Button(toolbar, text=t("save_btn"), command=self._on_save).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text=t("refresh_btn"), command=self._refresh_layouts).pack(side=tk.LEFT, padx=2)

        # Layout list
        list_frame = tk.LabelFrame(self, text="Layouts", padx=4, pady=4)
        list_frame.pack(fill=tk.BOTH, expand=False, padx=8, pady=4)
        self._layout_inner = tk.Frame(list_frame)
        self._layout_inner.pack(fill=tk.X)

        # Auto-rollback row
        ar_frame = tk.Frame(self, pady=4)
        ar_frame.pack(fill=tk.X, padx=8)
        tk.Label(ar_frame, text=t("auto_rollback_label")).pack(side=tk.LEFT)
        self._ar_layout_var = tk.StringVar()
        self._ar_combo = ttk.Combobox(ar_frame, textvariable=self._ar_layout_var, state="readonly", width=12)
        self._ar_combo.pack(side=tk.LEFT, padx=4)
        self._ar_toggle_btn = tk.Button(ar_frame, text=t("enable_btn"), command=self._on_ar_toggle)
        self._ar_toggle_btn.pack(side=tk.LEFT, padx=2)
        tk.Label(ar_frame, text=t("startup_delay_label")).pack(side=tk.LEFT, padx=(12, 0))
        self._delay_var = tk.StringVar(value="20")
        tk.Entry(ar_frame, textvariable=self._delay_var, width=5).pack(side=tk.LEFT)

        # Status bar
        self._status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self._status_var, anchor="w").pack(fill=tk.X, padx=8)

        # Log panel (splitter via PanedWindow)
        paned = tk.PanedWindow(self, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        log_frame = tk.LabelFrame(paned, text=t("log_panel_title"), padx=4, pady=4)
        paned.add(log_frame, minsize=80)

        # Log filter checkboxes
        filter_row = tk.Frame(log_frame)
        filter_row.pack(fill=tk.X)
        self._log_levels = {}
        for lvl in ("DEBUG", "INFO", "WARN", "ERROR"):
            var = tk.BooleanVar(value=(lvl != "DEBUG"))
            cb = tk.Checkbutton(filter_row, text=lvl, variable=var, command=self._apply_log_filter)
            cb.pack(side=tk.LEFT)
            self._log_levels[lvl] = var

        btn_row = tk.Frame(log_frame)
        btn_row.pack(fill=tk.X)
        tk.Button(btn_row, text=t("clear_btn"), command=self._clear_log).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text=t("copy_btn"), command=self._copy_log).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text=t("open_log_dir_btn"), command=self._open_log_dir).pack(side=tk.LEFT, padx=2)

        self._log_text = scrolledtext.ScrolledText(log_frame, state=tk.DISABLED, height=8,
                                                    font=("Consolas", 9), wrap=tk.NONE)
        self._log_text.pack(fill=tk.BOTH, expand=True)

        # Color tags
        self._log_text.tag_config("DEBUG", foreground="gray")
        self._log_text.tag_config("INFO", foreground="black")
        self._log_text.tag_config("WARN", foreground="orange")
        self._log_text.tag_config("ERROR", foreground="red")

        # Buffer to re-apply filter
        self._log_buffer: list[tuple[str, str]] = []  # (levelname, text)

    # ── Layout list ─────────────────────────────────────────────────────

    def _refresh_layouts(self):
        logger.info("refreshing layout list")
        for w in self._layout_inner.winfo_children():
            w.destroy()
        names = storage.list_layouts()
        config = storage.load_config()
        ar_name = config.get("auto_rollback", {}).get("layout_name", "")
        ar_enabled = config.get("auto_rollback", {}).get("enabled", False)

        if not names:
            tk.Label(self._layout_inner, text=t("no_layouts"), fg="gray").pack()
        else:
            for name in names:
                row = tk.Frame(self._layout_inner)
                row.pack(fill=tk.X, pady=1)
                radio_var = tk.IntVar(value=1 if name == ar_name else 0)
                tk.Radiobutton(row, variable=radio_var, value=1, state=tk.DISABLED).pack(side=tk.LEFT)
                tk.Label(row, text=name, width=16, anchor="w").pack(side=tk.LEFT)

                # Per-layout monitor match indicator
                match_text, match_color = self._get_match_indicator(name)
                tk.Label(row, text=match_text, fg=match_color, width=12, anchor="w").pack(side=tk.LEFT)

                tk.Button(row, text=t("restore_btn"), command=lambda n=name: self._on_restore(n)).pack(side=tk.LEFT, padx=2)
                tk.Button(row, text=t("settings_btn"), command=lambda n=name: self._on_settings(n)).pack(side=tk.LEFT, padx=2)
                tk.Button(row, text=t("delete_btn"), command=lambda n=name: self._on_delete(n)).pack(side=tk.LEFT, padx=2)

        # Update auto-rollback combo
        self._ar_combo["values"] = names
        if ar_name in names:
            self._ar_layout_var.set(ar_name)
        elif names:
            self._ar_layout_var.set(names[0])
        self._ar_toggle_btn.config(text=t("disable_btn") if ar_enabled else t("enable_btn"))

        delay = config.get("auto_rollback", {}).get("startup_delay_seconds", 20)
        self._delay_var.set(str(delay))

    # ── Monitor strip + polling ──────────────────────────────────────────

    def _poll_monitors(self):
        def _work():
            monitors = list_current_monitors()
            self.after(0, lambda: self._update_monitor_strip(monitors))

        threading.Thread(target=_work, daemon=True).start()
        self.after(1000, self._poll_monitors)

    def _update_monitor_strip(self, monitors: list[dict]):
        monitors_changed = monitors != self._current_monitors
        if monitors_changed:
            self._current_monitors = monitors
        if not monitors:
            self._monitor_strip_var.set("Monitors: unknown")
            return
        parts = []
        for m in monitors:
            x, y, w, h = m["rect"]
            label = f"#{m['index']}{'★' if m.get('primary') else ''} {w}x{h}"
            if m.get("scale", 1.0) != 1.0:
                label += f" @{m['scale']:.1f}x"
            parts.append(label)
        self._monitor_strip_var.set("Monitors: " + "  |  ".join(parts))
        if monitors_changed:
            self.after(0, self._refresh_layouts)

    def _get_match_indicator(self, name: str) -> tuple[str, str]:
        """Return (indicator_text, color) for a layout's monitor match state."""
        if not self._current_monitors:
            return ("", "gray")
        try:
            layout = storage.load_layout(name)
            saved_monitors = layout.get("monitors", [])
            if not saved_monitors:
                return ("", "gray")
            result = compare_monitors(saved_monitors, self._current_monitors)
            if result == MatchResult.MATCH:
                return ("✓match", "green")
            elif result == MatchResult.PRIMARY_ONLY:
                return ("⚠primary", "orange")
            else:
                return ("⚠mismatch", "red")
        except Exception:
            return ("", "gray")

    # ── Button handlers ──────────────────────────────────────────────────

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

    def _on_restore(self, name: str):
        logger.info("user clicked Restore for '%s'", name)

        # Check monitor match and prompt if warning state
        match_text, _ = self._get_match_indicator(name)
        if match_text in ("⚠primary", "⚠mismatch"):
            msg = (
                f"Monitor configuration differs from when '{name}' was saved.\n"
                f"({match_text.lstrip('⚠')})\n\n"
                "Windows may be restored to unexpected positions.\nContinue?"
            )
            if not messagebox.askyesno("Monitor Mismatch", msg, parent=self):
                return

        def _work():
            try:
                layout = storage.load_layout(name)
                running = capture.list_current_windows()
                result = restore_mod.restore_layout(layout, running, monitors_current=self._current_monitors or None)
                self.after(0, lambda: self._status_var.set(
                    t("layout_restored", name=name, restored=result["restored"], total=result["total"])
                ))
            except Exception as e:
                logger.error("restore failed: %s", e)
        threading.Thread(target=_work, daemon=True).start()

    def _on_delete(self, name: str):
        logger.info("user clicked Delete for '%s'", name)
        def _work():
            storage.delete_layout(name)
            self.after(0, lambda: self._status_var.set(t("layout_deleted", name=name)))
            self.after(0, self._refresh_layouts)
        threading.Thread(target=_work, daemon=True).start()

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

    def _on_ar_toggle(self):
        config = storage.load_config()
        ar = config.setdefault("auto_rollback", {})
        new_enabled = not ar.get("enabled", False)
        ar["enabled"] = new_enabled
        ar["layout_name"] = self._ar_layout_var.get()
        try:
            ar["startup_delay_seconds"] = int(self._delay_var.get())
        except ValueError:
            ar["startup_delay_seconds"] = 20
        storage.save_config(config)
        self._ar_toggle_btn.config(text=t("disable_btn") if new_enabled else t("enable_btn"))
        logger.info("auto-rollback %s for '%s'", "enabled" if new_enabled else "disabled", ar["layout_name"])
        script_path = str(Path(__file__).parent.parent / "cli" / "rollback.py")
        if new_enabled:
            scheduler.register(script_path=script_path, delay_seconds=ar.get("startup_delay_seconds", 20))
        else:
            scheduler.unregister()

    # ── Log panel ────────────────────────────────────────────────────────

    def _drain_log_queue(self):
        drained = 0
        while drained < 200:
            try:
                record = self._log_queue.get_nowait()
            except queue.Empty:
                break
            drained += 1
            levelname = record.levelname
            # Map WARNING → WARN for display
            display_level = "WARN" if levelname == "WARNING" else levelname
            ts = time.strftime("%H:%M:%S", time.localtime(record.created))
            ms = int(record.msecs)
            text = f"{ts}.{ms:03d} {display_level:<5} {record.name:<12}: {record.getMessage()}\n"
            self._log_buffer.append((display_level, text))
            # Trim buffer
            if len(self._log_buffer) > 1000:
                self._log_buffer = self._log_buffer[-1000:]
            self._append_log_line(display_level, text)
        self.after(100, self._drain_log_queue)

    def _append_log_line(self, level: str, text: str):
        var = self._log_levels.get(level)
        if var is not None and not var.get():
            return
        at_end = self._log_text.yview()[1] >= 0.99
        self._log_text.config(state=tk.NORMAL)
        self._log_text.insert(tk.END, text, level)
        # Trim to 1000 lines
        line_count = int(self._log_text.index(tk.END).split(".")[0]) - 1
        if line_count > 1000:
            self._log_text.delete("1.0", f"{line_count - 1000}.0")
        self._log_text.config(state=tk.DISABLED)
        if at_end:
            self._log_text.see(tk.END)

    def _apply_log_filter(self):
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.config(state=tk.DISABLED)
        for level, text in self._log_buffer:
            self._append_log_line(level, text)

    def _clear_log(self):
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.config(state=tk.DISABLED)
        self._log_buffer.clear()

    def _copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self._log_text.get("1.0", tk.END))

    def _open_log_dir(self):
        os.startfile(str(LOGS_DIR))


def main():
    app = WinLayoutSaverApp()
    app.mainloop()

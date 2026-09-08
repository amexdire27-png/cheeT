"""cheeT1 — settings window. Light, quiet, ordinary desktop software."""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
import webbrowser
from ctypes import wintypes

from brand import (
    APP_VERSION,
    BYLINE,
    CANVAS,
    DANGER,
    DIM,
    HOTKEY_ROWS,
    INK,
    KEY_URL,
    LINE,
    MODELS,
    MUTED,
    NAV_ITEMS,
    PANEL_2,
    RAIL,
    RAIL_W,
    SURFACE,
    WHITE,
    WINDOW_H,
    WINDOW_TITLE,
    WINDOW_W,
    ensure_app_icon,
    logo_path,
    mark_confetti_seen,
    mark_welcome_seen,
    confetti_seen,
    welcome_seen,
)
from utils import (
    acquire_settings_singleton,
    bind_app_id,
    focus_window_by_title,
    is_host_running,
    is_tray_running,
    set_dpi_aware,
)
from widgets import (
    Button,
    Confetti,
    Dropdown,
    Hairline,
    KeyCombo,
    SecretField,
    SideNav,
    Slider,
    Theme,
)

IDLE_FLASH = "Keys and shortcuts stay on this PC."


def main() -> int:
    if not acquire_settings_singleton():
        focus_window_by_title(WINDOW_TITLE)
        return 0

    bind_app_id("cheeT1.Settings")
    set_dpi_aware()
    ensure_app_icon()

    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.configure(bg=INK)
    App(root)
    root.mainloop()
    return 0


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.theme = Theme(root)
        px = self.theme.px

        self.w, self.h = px(WINDOW_W), px(WINDOW_H)
        root.geometry(self._centered())
        root.resizable(False, False)
        root.overrideredirect(True)
        _apply_window_icon(root)

        self.body = tk.Frame(root, bg=CANVAS)
        self.body.pack(fill="both", expand=True, padx=1, pady=1)

        self._titlebar()
        self.content = tk.Frame(self.body, bg=CANVAS)
        self.content.pack(fill="both", expand=True)

        root.after(30, _taskbar_button, root)
        root.after(80, root.focus_force)

        if welcome_seen():
            self.show_main()
        else:
            self.show_welcome()

    def _centered(self) -> str:
        x = max(0, (self.root.winfo_screenwidth() - self.w) // 2)
        y = max(0, (self.root.winfo_screenheight() - self.h) // 2 - self.theme.px(20))
        return f"{self.w}x{self.h}+{x}+{y}"

    def _titlebar(self) -> None:
        px = self.theme.px
        bar = tk.Frame(self.body, bg=SURFACE, height=px(44))
        bar.pack(fill="x")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=SURFACE)
        left.pack(side="left", padx=(px(14), 0))
        try:
            from PIL import Image, ImageTk

            image = Image.open(logo_path()).convert("RGBA")
            height = px(28)
            image = image.resize(
                (round(height * image.width / image.height), height), Image.LANCZOS
            )
            self._title_logo = ImageTk.PhotoImage(image)
            tk.Label(left, image=self._title_logo, bg=SURFACE).pack(side="left")
        except Exception:
            tk.Frame(left, bg=INK, width=px(8), height=px(8)).pack(side="left")
            tk.Label(
                left, text="cheeT1", font=self.theme.font(13, bold=True),
                fg=INK, bg=SURFACE,
            ).pack(side="left", padx=(px(10), 0))
        tk.Label(
            left,
            text=f"v{APP_VERSION}",
            font=self.theme.font(11),
            fg=DIM,
            bg=SURFACE,
        ).pack(side="left", padx=(px(8), 0))

        close = tk.Label(
            bar, text="✕", font=self.theme.font(11), fg=MUTED, bg=SURFACE,
            cursor="hand2", width=5,
        )
        close.pack(side="right", fill="y")
        close.bind("<Enter>", lambda _e: close.configure(fg=WHITE, bg=INK))
        close.bind("<Leave>", lambda _e: close.configure(fg=MUTED, bg=SURFACE))
        close.bind("<Button-1>", lambda _e: self.root.destroy())

        mini = tk.Label(
            bar, text="—", font=self.theme.font(11), fg=MUTED, bg=SURFACE,
            cursor="hand2", width=5,
        )
        mini.pack(side="right", fill="y")
        mini.bind("<Enter>", lambda _e: mini.configure(fg=INK, bg=PANEL_2))
        mini.bind("<Leave>", lambda _e: mini.configure(fg=MUTED, bg=SURFACE))
        mini.bind("<Button-1>", lambda _e: self._minimize())

        for widget in (bar, left, *left.winfo_children()):
            widget.bind("<Button-1>", self._grab)
            widget.bind("<B1-Motion>", self._drag)
        Hairline(self.body, self.theme).pack(fill="x")

    def _grab(self, event) -> None:
        self._ox = event.x_root - self.root.winfo_x()
        self._oy = event.y_root - self.root.winfo_y()

    def _drag(self, event) -> None:
        self.root.geometry(f"+{event.x_root - self._ox}+{event.y_root - self._oy}")

    def _minimize(self) -> None:
        hwnd = _hwnd(self.root)
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 6)

    def _swap(self) -> tk.Frame:
        for child in self.content.winfo_children():
            child.destroy()
        view = tk.Frame(self.content, bg=CANVAS)
        view.pack(fill="both", expand=True)
        return view

    def show_welcome(self) -> None:
        px = self.theme.px
        view = self._swap()
        wrap = tk.Frame(view, bg=CANVAS)
        wrap.place(relx=0.5, rely=0.48, anchor="center")

        try:
            from PIL import Image, ImageTk

            image = Image.open(logo_path()).convert("RGBA")
            width = px(280)
            image = image.resize(
                (width, round(width * image.height / image.width)), Image.LANCZOS
            )
            self._logo = ImageTk.PhotoImage(image)
            tk.Label(wrap, image=self._logo, bg=CANVAS).pack()
        except Exception:
            tk.Label(
                wrap, text="cheeT1", font=self.theme.font(28, bold=True),
                fg=INK, bg=CANVAS,
            ).pack()

        tk.Label(
            wrap, text="Welcome to cheeT1",
            font=self.theme.font(26, bold=True), fg=INK, bg=CANVAS,
        ).pack(pady=(px(22), px(6)))
        tk.Label(
            wrap, text=BYLINE, font=self.theme.font(13), fg=DIM, bg=CANVAS,
        ).pack(pady=(0, px(12)))
        tk.Label(
            wrap,
            text=(
                "An on-screen assistant for Windows. Add your Gemini key,\n"
                "choose shortcuts, then turn it on. Focus any window, press\n"
                "a shortcut, and a short answer arrives as a notification —\n"
                "already copied, ready to paste."
            ),
            font=self.theme.font(13),
            fg=MUTED,
            bg=CANVAS,
            justify="center",
        ).pack()
        Button(
            wrap, self.theme, "Get started", self._finish_welcome,
            width=168, height=38, size=13,
        ).pack(pady=(px(28), px(12)))
        tk.Label(
            wrap, text="Takes about a minute.",
            font=self.theme.font(12), fg=DIM, bg=CANVAS,
        ).pack()

        wrap.lift()
        if not confetti_seen():
            mark_confetti_seen()
            confetti = Confetti(view, self.theme, bg=CANVAS)
            confetti.place(relx=0, rely=0, relwidth=1, relheight=1)
            wrap.lift()
            self._confetti = confetti
            confetti.play()

    def _finish_welcome(self) -> None:
        mark_welcome_seen()
        self.show_main()

    def show_main(self) -> None:
        from config import format_hotkey, load_config

        px = self.theme.px
        self.cfg = load_config()
        self.keys: list[SecretField] = []
        self.combos: dict[str, KeyCombo] = {}
        self._flash_job: str | None = None
        self._key_cache = list(self.cfg.api_keys) or [""]
        self._model_cache = self.cfg.model
        self._toast_cache = self.cfg.notification_duration_seconds

        shown = self.cfg.hotkeys.display()
        self._hotkey_labels = {
            name: shown.get(name) or format_hotkey(getattr(self.cfg.hotkeys, name))
            for name, _, _ in HOTKEY_ROWS
        }

        view = self._swap()
        self._rail(view)

        pane = tk.Frame(view, bg=SURFACE)
        pane.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(pane, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=px(32), pady=(px(24), px(18)))

        self.heading = tk.Label(
            inner, text="Shortcuts", font=self.theme.font(22, bold=True),
            fg=INK, bg=SURFACE, anchor="w",
        )
        self.heading.pack(fill="x")
        self.lede = tk.Label(
            inner, text="", font=self.theme.font(13),
            fg=MUTED, bg=SURFACE, anchor="w", justify="left",
        )
        self.lede.pack(fill="x", pady=(px(6), px(18)))

        self.tab = tk.Frame(inner, bg=SURFACE)
        self.tab.pack(fill="both", expand=True)

        foot = tk.Frame(inner, bg=SURFACE)
        foot.pack(fill="x", side="bottom", pady=(px(12), 0))
        Button(
            foot, self.theme, "Save changes", self._save, width=132, height=36
        ).pack(side="left")
        self.flash = tk.Label(
            foot, text=IDLE_FLASH, font=self.theme.font(12),
            fg=DIM, bg=SURFACE, anchor="w",
        )
        self.flash.pack(side="left", padx=(px(14), 0))

        self._tab(0)

    def _rail(self, parent: tk.Frame) -> None:
        px = self.theme.px
        rail = tk.Frame(parent, bg=RAIL, width=px(RAIL_W))
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)

        inner = tk.Frame(rail, bg=RAIL)
        inner.pack(fill="both", expand=True, padx=px(14), pady=px(16))

        self.nav = SideNav(inner, self.theme, NAV_ITEMS, self._tab, bg=RAIL)
        self.nav.pack(fill="x")

        actions = tk.Frame(inner, bg=RAIL)
        actions.pack(side="bottom", fill="x")
        tk.Label(
            actions, text=BYLINE, font=self.theme.font(11),
            fg=DIM, bg=RAIL, anchor="w",
        ).pack(fill="x", pady=(0, px(12)))
        Button(
            actions, self.theme, "Turn on", self._activate, height=36
        ).pack(fill="x")
        row = tk.Frame(actions, bg=RAIL)
        row.pack(fill="x", pady=(px(8), 0))
        Button(row, self.theme, "Stop", self._stop, kind="ghost", height=32).pack(
            side="left", fill="x", expand=True, padx=(0, px(4))
        )
        Button(row, self.theme, "Restart", self._restart, kind="ghost", height=32).pack(
            side="left", fill="x", expand=True, padx=(px(4), 0)
        )

    def _stash(self) -> None:
        if self.keys:
            try:
                if self.keys[0].winfo_exists():
                    values = [field.value() for field in self.keys]
                    self._key_cache = values or [""]
            except tk.TclError:
                pass
        if hasattr(self, "model"):
            try:
                if self.model.winfo_exists():
                    self._model_cache = self.model.value()
            except tk.TclError:
                pass
        if hasattr(self, "toast"):
            try:
                if self.toast.winfo_exists():
                    self._toast_cache = self.toast.value()
            except tk.TclError:
                pass

    def _tab(self, index: int) -> None:
        self._stash()
        for child in self.tab.winfo_children():
            child.destroy()
        titles = (
            ("Shortcuts", "Click a shortcut, then press the keys you want. Esc cancels."),
            (
                "API keys",
                "Your own Gemini keys. They are tried in order, so a second key\n"
                "takes over when the first is rate-limited or out of quota.",
            ),
            ("Answers", "Choose the model and how long the notification stays on screen."),
        )
        title, lede = titles[index]
        self.heading.configure(text=title)
        self.lede.configure(text=lede)
        (self._tab_shortcuts, self._tab_keys, self._tab_output)[index]()

    def _tab_shortcuts(self) -> None:
        px = self.theme.px
        group = tk.Frame(self.tab, bg=SURFACE)
        group.pack(fill="x")
        for i, (name, title, hint) in enumerate(HOTKEY_ROWS):
            if i:
                Hairline(group, self.theme).pack(fill="x")
            row = tk.Frame(group, bg=SURFACE)
            row.pack(fill="x", pady=px(8))
            text = tk.Frame(row, bg=SURFACE)
            text.pack(side="left", fill="x", expand=True)
            tk.Label(
                text, text=title, font=self.theme.font(13, bold=True),
                fg=INK, bg=SURFACE, anchor="w",
            ).pack(fill="x")
            tk.Label(
                text, text=hint, font=self.theme.font(12),
                fg=MUTED, bg=SURFACE, anchor="w",
            ).pack(fill="x", pady=(px(1), 0))
            combo = KeyCombo(
                row, self.theme, self._hotkey_labels[name],
                on_change=lambda value, n=name: self._hotkey_labels.__setitem__(n, value),
            )
            combo.pack(side="right")
            self.combos[name] = combo

    def _tab_keys(self) -> None:
        px = self.theme.px
        self.keys_box = tk.Frame(self.tab, bg=SURFACE)
        self.keys_box.pack(fill="x")
        self.keys = []
        for value in self._key_cache or ("",):
            self._add_key(value)

        row = tk.Frame(self.tab, bg=SURFACE)
        row.pack(fill="x", pady=(px(14), 0))
        Button(
            row, self.theme, "Add a key", lambda: self._add_key(""),
            kind="ghost", width=108, height=34,
        ).pack(side="left")
        Button(
            row, self.theme, "Get a free key", lambda: webbrowser.open(KEY_URL),
            kind="quiet", width=120, height=34, bg=SURFACE,
        ).pack(side="left", padx=(px(8), 0))

    def _tab_output(self) -> None:
        px = self.theme.px
        tk.Label(
            self.tab, text="Model", font=self.theme.font(13, bold=True),
            fg=INK, bg=SURFACE, anchor="w",
        ).pack(fill="x")
        tk.Label(
            self.tab,
            text="Fallback models are used automatically if this one is unavailable.",
            font=self.theme.font(12), fg=MUTED, bg=SURFACE, anchor="w",
        ).pack(fill="x", pady=(px(4), px(10)))
        models = list(MODELS)
        if self._model_cache and self._model_cache not in models:
            models.insert(0, self._model_cache)
        self.model = Dropdown(
            self.tab, self.theme, models, self._model_cache or models[0], width=340
        )
        self.model.pack(anchor="w")

        tk.Label(
            self.tab, text="Notification", font=self.theme.font(13, bold=True),
            fg=INK, bg=SURFACE, anchor="w",
        ).pack(fill="x", pady=(px(28), 0))
        head = tk.Frame(self.tab, bg=SURFACE)
        head.pack(fill="x", pady=(px(4), px(8)))
        tk.Label(
            head, text="How long the answer stays on screen.",
            font=self.theme.font(12), fg=MUTED, bg=SURFACE,
        ).pack(side="left")
        self.toast_value = tk.Label(
            head, text=f"{self._toast_cache} seconds",
            font=self.theme.font(12, bold=True), fg=INK, bg=SURFACE,
        )
        self.toast_value.pack(side="right")
        self.toast = Slider(
            self.tab, self.theme, low=2, high=15, value=self._toast_cache,
            bg=SURFACE, on_change=lambda v: self.toast_value.configure(text=f"{v} seconds"),
        )
        self.toast.pack(fill="x")

    def _add_key(self, value: str) -> None:
        field = SecretField(self.keys_box, self.theme, value, self._remove_key)
        field.pack(fill="x", pady=self.theme.px(4))
        self.keys.append(field)

    def _remove_key(self, field: SecretField) -> None:
        if field in self.keys:
            self.keys.remove(field)
        field.destroy()
        if not self.keys:
            self._add_key("")

    def _collected_keys(self) -> list[str]:
        self._stash()
        return [key for key in self._key_cache if key]

    def _collected_hotkeys(self) -> dict[str, str]:
        return dict(self._hotkey_labels)

    def _duplicate(self) -> str | None:
        seen: dict[str, str] = {}
        for name, combo in self._collected_hotkeys().items():
            if not combo:
                return "Every action needs a shortcut."
            if combo.lower() in seen:
                return f"{combo} is used twice. Give each action its own shortcut."
            seen[combo.lower()] = name
        return None

    def _save(self, restart: bool | None = None) -> bool:
        from config import load_config, save_user_settings

        problem = self._duplicate()
        if problem:
            self._say(problem, bad=True)
            return False

        self._stash()
        save_user_settings(
            api_keys=self._collected_keys(),
            hotkeys=self._collected_hotkeys(),
            model=self._model_cache,
            notification_duration_seconds=self._toast_cache,
        )
        self.cfg = load_config()

        running = is_host_running()
        if restart is True or (restart is None and running):
            import tray

            tray.restart_host()
            self._say("Saved. The service restarted with the new settings.")
        else:
            self._say("Saved. Turn it on when you want it running.")
        return True

    def _activate(self) -> None:
        import tray

        if not self._collected_keys():
            self._say("Add a Gemini API key first.", bad=True)
            self.nav.select(1)
            return
        if not self._save(restart=False):
            return
        if not is_tray_running():
            tray.start_tray()
        if is_host_running():
            tray.restart_host()
            self._say("Already running. Restarted with your settings.")
        else:
            tray.start_host()
            self._say("Running in the background.")

    def _stop(self) -> None:
        import tray

        tray.stop_host()
        self._say("Stopped. The tray icon stays so you can start again.")

    def _restart(self) -> None:
        if not self._collected_keys():
            self._say("Add a Gemini API key first.", bad=True)
            self.nav.select(1)
            return
        self._save(restart=True)

    def _say(self, text: str, bad: bool = False) -> None:
        self.flash.configure(text=text, fg=DANGER if bad else MUTED)
        if self._flash_job:
            self.root.after_cancel(self._flash_job)
        self._flash_job = self.root.after(
            8000, lambda: self.flash.configure(text=IDLE_FLASH, fg=DIM)
        )


def _hwnd(root: tk.Tk) -> int:
    handle = ctypes.windll.user32.GetParent(root.winfo_id())
    return handle or root.winfo_id()


def _apply_window_icon(root: tk.Tk) -> None:
    """Pin app.ico on the window and the taskbar (pythonw otherwise keeps the Python icon)."""
    icon = ensure_app_icon()
    if not icon.exists():
        return
    path = str(icon)
    try:
        root.iconbitmap(default=path)
        root.iconbitmap(path)
    except tk.TclError:
        pass
    try:
        from PIL import Image, ImageTk

        image = Image.open(icon).convert("RGBA")
        image = image.resize((32, 32), Image.Resampling.LANCZOS)
        root._icon_photo = ImageTk.PhotoImage(image)
        root.iconphoto(True, root._icon_photo)
    except Exception:
        pass
    if sys.platform != "win32":
        return
    try:
        root.update_idletasks()
    except tk.TclError:
        return
    hwnd = _hwnd(root)
    if not hwnd:
        return

    image_icon, load_from_file = 1, 0x00000010
    wm_seticon, icon_small, icon_big = 0x0080, 0, 1
    user32 = ctypes.windll.user32
    load = user32.LoadImageW
    load.restype = wintypes.HANDLE
    small = load(None, path, image_icon, 16, 16, load_from_file)
    big = load(None, path, image_icon, 32, 32, load_from_file)
    root._hicon_small = small
    root._hicon_big = big
    if small:
        user32.SendMessageW(hwnd, wm_seticon, icon_small, small)
    if big:
        user32.SendMessageW(hwnd, wm_seticon, icon_big, big)


def _taskbar_button(root: tk.Tk) -> None:
    """A frameless window is a tool window by default — put it back on the taskbar."""
    if sys.platform != "win32":
        return
    GWL_EXSTYLE, WS_EX_APPWINDOW, WS_EX_TOOLWINDOW = -20, 0x00040000, 0x00000080
    user32 = ctypes.windll.user32
    get = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    put = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    get.restype, get.argtypes = ctypes.c_ssize_t, [wintypes.HWND, ctypes.c_int]
    put.restype = ctypes.c_ssize_t
    put.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]

    hwnd = _hwnd(root)
    try:
        style = get(hwnd, GWL_EXSTYLE)
        put(hwnd, GWL_EXSTYLE, (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW)
        _apply_window_icon(root)
        root.withdraw()

        def _show() -> None:
            _apply_window_icon(root)
            root.deiconify()
            _apply_window_icon(root)

        root.after(10, _show)
    except OSError:
        pass


if __name__ == "__main__":
    sys.exit(main())

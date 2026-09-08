"""cheeT1 widgets — quiet settings controls, not an instrument panel."""

from __future__ import annotations

import math
import random
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Iterable, Sequence

from brand import (
    CANVAS,
    DIM,
    INK,
    LINE,
    MUTED,
    PANEL_2,
    SANS_FAMILIES,
    SHADOW,
    SHADOW_SOFT,
    SURFACE,
    WHITE,
    WINDOW_H,
)


def _first_family(root: tk.Misc, options: Sequence[str]) -> str:
    available = {name.lower() for name in tkfont.families(root)}
    for name in options:
        if name.lower() in available:
            return name
    return options[-1]


class Theme:
    def __init__(self, root: tk.Misc) -> None:
        raw = root.winfo_fpixels("1i") / 96.0
        headroom = (root.winfo_screenheight() * 0.92) / WINDOW_H
        self.scale = max(1.0, min(raw, headroom))
        self.sans = _first_family(root, SANS_FAMILIES)

    def px(self, n: float) -> int:
        return max(1, int(round(n * self.scale)))

    def font(self, size: float, *, bold: bool = False) -> tuple:
        return (self.sans, -self.px(size), "bold" if bold else "normal")


class Hairline(tk.Frame):
    def __init__(self, parent: tk.Misc, theme: Theme, color: str = LINE) -> None:
        super().__init__(parent, bg=color, height=1, highlightthickness=0, bd=0)


class Confetti(tk.Canvas):
    """One-shot sharp confetti. Black, white, gray. Does not steal clicks from widgets above it."""

    _COLORS = (INK, WHITE, "#000000", "#B4B4B4", "#5A5A5A", "#D4D4D4", "#8A8A8A")

    def __init__(self, parent: tk.Misc, theme: Theme, *, bg: str = CANVAS) -> None:
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0)
        self.theme = theme
        self._pieces: list[dict] = []
        self._job: str | None = None
        self._alive = True
        self.bind("<Destroy>", self._stop)

    def play(self) -> None:
        self.after(30, self._burst)
        self.after(160, lambda: self._burst(count=36, from_top=True))

    def _stop(self, _event=None) -> None:
        self._alive = False
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _burst(self, count: int = 72, from_top: bool = False) -> None:
        if not self._alive:
            return
        width = max(self.winfo_width(), 2)
        height = max(self.winfo_height(), 2)
        origin_x = width * 0.5
        origin_y = height * (0.12 if from_top else 0.28)
        for _ in range(count):
            spread = random.uniform(-1.15, 1.15)
            self._pieces.append(
                {
                    "x": origin_x + random.uniform(-40, 40),
                    "y": origin_y + random.uniform(-12, 12),
                    "vx": spread * random.uniform(2.4, 7.2),
                    "vy": random.uniform(-11.0, -3.5),
                    "spin": random.uniform(-0.28, 0.28),
                    "angle": random.uniform(0, math.tau),
                    "w": self.theme.px(random.choice((5, 6, 7, 8, 10, 12))),
                    "h": self.theme.px(random.choice((3, 4, 5, 8, 10))),
                    "color": random.choice(self._COLORS),
                    "g": random.uniform(0.16, 0.28),
                }
            )
        if self._job is None:
            self._tick()

    def _tick(self) -> None:
        if not self._alive or not self.winfo_exists():
            return
        self.delete("all")
        height = self.winfo_height()
        width = self.winfo_width()
        live: list[dict] = []
        for piece in self._pieces:
            piece["vy"] += piece["g"]
            piece["vx"] *= 0.992
            piece["x"] += piece["vx"]
            piece["y"] += piece["vy"]
            piece["angle"] += piece["spin"]
            if piece["y"] > height + 24 or piece["x"] < -40 or piece["x"] > width + 40:
                continue
            live.append(piece)
            self._draw_piece(piece)
        self._pieces = live
        if live:
            self._job = self.after(16, self._tick)
        else:
            self._job = None

    def _draw_piece(self, piece: dict) -> None:
        cx, cy = piece["x"], piece["y"]
        hw, hh = piece["w"] / 2, piece["h"] / 2
        cos_a, sin_a = math.cos(piece["angle"]), math.sin(piece["angle"])
        points: list[float] = []
        for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            points.append(cx + dx * cos_a - dy * sin_a)
            points.append(cy + dx * sin_a + dy * cos_a)
        self.create_polygon(points, fill=piece["color"], outline=piece["color"])



class Button(tk.Canvas):
    """kind: primary | ghost | quiet | danger. Sharp face, solid offset shadow."""

    def __init__(
        self,
        parent: tk.Misc,
        theme: Theme,
        text: str,
        command: Callable[[], None],
        *,
        kind: str = "primary",
        width: int | None = None,
        height: float = 34,
        bg: str = CANVAS,
        size: float = 12.5,
    ) -> None:
        self.kind = kind
        self.command = command
        self._enabled = True
        self.theme = theme
        self._text = text
        self._size = size
        self._pressed = False
        self._focused = False
        self._shadow = 0 if kind == "quiet" else theme.px(3)
        try:
            host = str(parent.cget("bg"))
        except tk.TclError:
            host = bg

        if kind == "primary":
            self._fill_rest, self._fill_hot = INK, "#000000"
            self._fg_rest, self._fg_hot = WHITE, WHITE
            self._shadow_fill = SHADOW_SOFT
        elif kind == "quiet":
            self._fill_rest, self._fill_hot = host, host
            self._fg_rest, self._fg_hot = INK, "#000000"
            self._shadow_fill = host
        else:
            self._fill_rest, self._fill_hot = WHITE, PANEL_2
            self._fg_rest, self._fg_hot = INK, INK
            self._shadow_fill = SHADOW

        self._fill, self._fg = self._fill_rest, self._fg_rest
        super().__init__(
            parent,
            bg=host,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            height=theme.px(height) + self._shadow,
            takefocus=True,
        )
        if width:
            self.configure(width=theme.px(width) + self._shadow)
        else:
            self.configure(width=1)
        self.bind("<Configure>", lambda _e: self._draw())
        self.after(1, self._draw)
        self.bind("<Enter>", self._hover)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._down)
        self.bind("<ButtonRelease-1>", self._click)
        self.bind("<Return>", lambda _e: self._click())
        self.bind("<space>", lambda _e: self._click())
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)

    def _draw(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        s = self._shadow
        ox = s if self._pressed else 0
        oy = s if self._pressed else 0
        if s and self.kind != "quiet":
            self.create_rectangle(s, s, w - 1, h - 1, fill=self._shadow_fill, outline=self._shadow_fill)
            x2, y2 = w - 1 - s + ox, h - 1 - s + oy
            self.create_rectangle(
                ox, oy, max(ox + 1, x2), max(oy + 1, y2),
                fill=self._fill, outline=INK, width=1,
            )
            cx, cy = (ox + x2) / 2, (oy + y2) / 2
        else:
            self.create_text(
                w / 2, h / 2, text=self._text, fill=self._fg,
                font=self.theme.font(self._size, bold=self.kind == "primary"),
            )
            if self._focused:
                self.create_rectangle(1, 1, w - 2, h - 2, outline=INK, width=1)
            return
        self.create_text(
            cx, cy, text=self._text, fill=self._fg,
            font=self.theme.font(self._size, bold=self.kind == "primary"),
        )
        if self._focused:
            self.create_rectangle(ox + 2, oy + 2, x2 - 2, y2 - 2, outline=INK, width=1)

    def _hover(self, _event=None) -> None:
        if self._enabled:
            self._fill, self._fg = self._fill_hot, self._fg_hot
            self._draw()

    def _leave(self, _event=None) -> None:
        self._pressed = False
        if self._enabled and not self._focused:
            self._fill, self._fg = self._fill_rest, self._fg_rest
            self._draw()

    def _down(self, _event=None) -> None:
        if self._enabled:
            self._pressed = True
            self._draw()

    def _focus_in(self, _event=None) -> None:
        self._focused = True
        self._draw()

    def _focus_out(self, _event=None) -> None:
        self._focused = False
        self._pressed = False
        self._fill, self._fg = self._fill_rest, self._fg_rest
        self._draw()

    def _click(self, _event=None) -> str:
        self._pressed = False
        self._draw()
        if self._enabled:
            self.command()
        return "break"

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self._fill, self._fg = self._fill_rest, self._fg_rest
            self.configure(cursor="hand2")
        else:
            self._fill, self._fg = PANEL_2, DIM
            self.configure(cursor="arrow")
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()


class KeyCombo(tk.Frame):
    """Shortcut field. Click, then press the keys."""

    def __init__(
        self,
        parent: tk.Misc,
        theme: Theme,
        value: str,
        *,
        bg: str = SURFACE,
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            parent, bg=WHITE, highlightthickness=1, highlightbackground=INK,
            highlightcolor=INK, bd=0, cursor="hand2",
            takefocus=True, height=theme.px(32), width=theme.px(196),
        )
        self.pack_propagate(False)
        self.theme = theme
        self._value = value
        self._listening = False
        self._on_change = on_change
        self._bg = bg
        self.label = tk.Label(
            self, text=value.replace("+", " + "), font=theme.font(12),
            fg=INK, bg=WHITE, padx=theme.px(12),
        )
        self.label.pack(fill="both", expand=True)
        for widget in (self, self.label):
            widget.bind("<Button-1>", self._listen)
        self.bind("<KeyPress>", self._on_key)
        self.bind("<FocusOut>", lambda _e: self._cancel())
        self.bind("<FocusIn>", lambda _e: self._show(self.label.cget("text"), self._listening))

    def value(self) -> str:
        return self._value

    def configure_width(self, chars: int = 18) -> None:
        self.configure(width=self.theme.px(chars * 8))

    def _show(self, text: str, listening: bool) -> None:
        self._listening = listening
        self.label.configure(
            text=text,
            fg=WHITE if listening else INK,
            bg=INK if listening else WHITE,
        )
        self.configure(bg=INK if listening else WHITE)

    def _listen(self, _event=None) -> None:
        self._show("Press keys…", True)
        self.focus_set()

    def _cancel(self) -> None:
        if self._listening:
            self._show(self._value.replace("+", " + "), False)

    def _on_key(self, event) -> str:
        if not self._listening:
            return "break"
        if event.keysym == "Escape":
            self._cancel()
            return "break"
        label = _key_from_event(event)
        mods = _mods_from_event(event)
        if label is None or not mods:
            return "break"
        self._value = "+".join(mods + [label])
        self._show(self._value.replace("+", " + "), False)
        if self._on_change:
            self._on_change(self._value)
        return "break"


class Slider(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        theme: Theme,
        *,
        low: int,
        high: int,
        value: int,
        bg: str = SURFACE,
        on_change: Callable[[int], None] | None = None,
    ) -> None:
        self.theme = theme
        self.low, self.high = low, high
        self._value = value
        self._on_change = on_change
        super().__init__(
            parent, height=theme.px(28), bg=bg, highlightthickness=0, bd=0, cursor="hand2"
        )
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)

    def value(self) -> int:
        return self._value

    def _bounds(self) -> tuple[int, int]:
        pad = self.theme.px(8)
        return pad, max(pad + 40, self.winfo_width() - pad)

    def redraw(self) -> None:
        self.delete("all")
        x0, x1 = self._bounds()
        y = self.theme.px(14)
        span = self.high - self.low
        t = (self._value - self.low) / span if span else 0
        cx = x0 + (x1 - x0) * t
        half = self.theme.px(6)
        self.create_rectangle(x0, y - 2, x1, y + 2, fill=LINE, outline=LINE)
        self.create_rectangle(x0, y - 2, cx, y + 2, fill=INK, outline=INK)
        self.create_rectangle(
            cx - half, y - half, cx + half, y + half,
            fill=WHITE, outline=INK, width=1,
        )

    def _drag(self, event) -> None:
        x0, x1 = self._bounds()
        t = (event.x - x0) / max(1, x1 - x0)
        value = max(self.low, min(self.high, round(self.low + t * (self.high - self.low))))
        if value != self._value:
            self._value = value
            if self._on_change:
                self._on_change(value)
        self.redraw()


class Dropdown(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        theme: Theme,
        values: Iterable[str],
        value: str,
        *,
        width: int = 320,
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        self.theme = theme
        self.values = list(values)
        self._value = value
        self._on_change = on_change
        self._popup: tk.Toplevel | None = None
        super().__init__(
            parent, bg=WHITE, highlightthickness=1, highlightbackground=INK,
            highlightcolor=INK, bd=0,
            width=theme.px(width), height=theme.px(36),
            cursor="hand2", takefocus=True,
        )
        self.pack_propagate(False)
        self.label = tk.Label(
            self, text=value, font=theme.font(12.5), fg=INK, bg=WHITE, anchor="w"
        )
        self.label.pack(side="left", fill="both", expand=True, padx=(theme.px(12), 0))
        self.caret = tk.Label(self, text="▾", font=theme.font(11), fg=MUTED, bg=WHITE)
        self.caret.pack(side="right", padx=(0, theme.px(10)))
        for widget in (self, self.label, self.caret):
            widget.bind("<Button-1>", self._toggle)
            widget.bind("<Enter>", lambda _e: self._tint(PANEL_2))
            widget.bind("<Leave>", lambda _e: self._tint(WHITE))
        self.bind("<Return>", self._toggle)
        self.bind("<FocusIn>", lambda _e: self._tint(PANEL_2))
        self.bind("<FocusOut>", lambda _e: self._tint(WHITE))

    def value(self) -> str:
        return self._value

    def _tint(self, color: str) -> None:
        if self._popup:
            return
        self.configure(bg=color)
        self.label.configure(bg=color)
        self.caret.configure(bg=color)

    def _toggle(self, _event=None) -> str:
        if self._popup:
            self._close()
            return "break"
        self._tint(PANEL_2)
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=INK)
        popup.geometry(
            f"{self.winfo_width()}x{self.theme.px(34) * len(self.values) + 2}"
            f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height() + 4}"
        )
        inner = tk.Frame(popup, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        for item in self.values:
            row = tk.Label(
                inner, text=item, font=self.theme.font(12.5),
                fg=INK, bg=PANEL_2 if item == self._value else SURFACE,
                anchor="w", cursor="hand2",
            )
            row.pack(fill="x", ipady=self.theme.px(7), padx=self.theme.px(10))
            row.bind("<Enter>", lambda _e, r=row: r.configure(bg=PANEL_2))
            row.bind(
                "<Leave>",
                lambda _e, r=row, i=item: r.configure(
                    bg=PANEL_2 if i == self._value else SURFACE
                ),
            )
            row.bind("<Button-1>", lambda _e, i=item: self._pick(i))
        popup.bind("<FocusOut>", lambda _e: self._close())
        popup.bind("<Escape>", lambda _e: self._close())
        popup.focus_force()
        self._popup = popup
        return "break"

    def _pick(self, item: str) -> None:
        self._value = item
        self.label.configure(text=item)
        self._close()
        if self._on_change:
            self._on_change(item)

    def _close(self) -> None:
        if self._popup:
            self._popup.destroy()
            self._popup = None
        self._tint(WHITE)


class SecretField(tk.Frame):
    _MASK = "••••••••••••"

    def __init__(
        self,
        parent: tk.Misc,
        theme: Theme,
        value: str,
        on_remove: Callable[["SecretField"], None],
        *,
        bg: str = SURFACE,
    ) -> None:
        super().__init__(parent, bg=bg)
        self.theme = theme
        self._saved = (value or "").strip()
        self._dirty = False
        box = tk.Frame(self, bg=WHITE, highlightthickness=1, highlightbackground=INK, bd=0)
        box.pack(side="left", fill="x", expand=True)
        self.entry = tk.Entry(
            box, show="•", font=theme.font(12.5), bg=WHITE, fg=INK,
            insertbackground=INK, relief="flat", bd=0,
            highlightthickness=0,
        )
        self.entry.pack(fill="x", ipady=theme.px(9), padx=theme.px(12))
        if self._saved:
            self.entry.insert(0, self._MASK)
        self.entry.bind("<KeyPress>", self._begin_edit, add="+")
        self.entry.bind("<<Paste>>", self._begin_edit, add="+")
        Button(
            self, theme, "Remove", lambda: on_remove(self),
            kind="danger", width=84, height=36,
        ).pack(side="left", padx=(theme.px(8), 0))

    def value(self) -> str:
        typed = self.entry.get().strip()
        if not self._dirty:
            return self._saved
        if typed == self._MASK:
            return self._saved
        return typed

    def _begin_edit(self, event=None) -> None:
        keysym = getattr(event, "keysym", "") if event is not None else ""
        if keysym in {
            "Tab", "ISO_Left_Tab", "Shift_L", "Shift_R",
            "Control_L", "Control_R", "Alt_L", "Alt_R",
            "Return", "Escape",
        }:
            return
        if self._dirty:
            return
        self._dirty = True
        if self.entry.get() == self._MASK:
            self.entry.delete(0, "end")


class SideNav(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        theme: Theme,
        items: Sequence[str],
        on_select: Callable[[int], None],
        *,
        bg: str,
    ) -> None:
        super().__init__(parent, bg=bg)
        self.theme = theme
        self.on_select = on_select
        self.bg = bg
        self.labels: list[tk.Label] = []
        self._index = 0
        for i, item in enumerate(items):
            row = tk.Label(
                self, text=item, font=theme.font(13),
                fg=INK if i == 0 else MUTED,
                bg=WHITE if i == 0 else bg,
                highlightthickness=1,
                highlightbackground=INK if i == 0 else bg,
                highlightcolor=INK,
                anchor="w", cursor="hand2",
                padx=theme.px(14), pady=theme.px(9),
            )
            row.pack(fill="x", pady=theme.px(2))
            row.bind("<Button-1>", lambda _e, n=i: self.select(n))
            row.bind("<Enter>", lambda _e, n=i: self._hover(n, True))
            row.bind("<Leave>", lambda _e, n=i: self._hover(n, False))
            self.labels.append(row)

    def _hover(self, index: int, entering: bool) -> None:
        if index == self._index:
            return
        self.labels[index].configure(bg=PANEL_2 if entering else self.bg, fg=INK if entering else MUTED)

    def select(self, index: int) -> None:
        if index == self._index:
            return
        self._index = index
        for i, label in enumerate(self.labels):
            on = i == index
            label.configure(
                bg=WHITE if on else self.bg,
                fg=INK if on else MUTED,
                highlightbackground=INK if on else self.bg,
            )
        self.on_select(index)


# Kept for older call sites that imported Nav.
Nav = SideNav


_IGNORE_KEYS = {
    "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
    "Meta_L", "Meta_R", "Win_L", "Win_R", "Super_L", "Super_R",
    "Caps_Lock", "Num_Lock", "Scroll_Lock", "App", "Menu",
}

_KEY_ALIASES = {
    "plus": "+", "minus": "-", "equal": "=", "bracketleft": "[",
    "bracketright": "]", "semicolon": ";", "apostrophe": "'", "comma": ",",
    "period": ".", "slash": "/", "backslash": "\\", "grave": "`",
    "space": "Space", "Return": "Enter", "BackSpace": "Backspace",
    "Prior": "PageUp", "Next": "PageDown",
}


def _mods_from_event(event) -> list[str]:
    mods: list[str] = []
    if event.state & 0x4:
        mods.append("Ctrl")
    if event.state & 0x20000 or event.state & 0x8:
        mods.append("Alt")
    if event.state & 0x1:
        mods.append("Shift")
    if event.state & 0x40000:
        mods.append("Win")
    return mods


def _key_from_event(event) -> str | None:
    if event.keysym in _IGNORE_KEYS:
        return None
    if len(event.keysym) == 1:
        return event.keysym.upper()
    if event.keysym in _KEY_ALIASES:
        return _KEY_ALIASES[event.keysym]
    if event.keysym.startswith("F") and event.keysym[1:].isdigit():
        return event.keysym
    return event.keysym[:1].upper() + event.keysym[1:]

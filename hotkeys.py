"""Hotkeys that fire only when the last non-modifier key is pressed.

pynput GlobalHotKeys can activate when Ctrl+Alt go down if a letter was
already stuck in its state. That made Start run on Ctrl+Alt alone.
"""

from __future__ import annotations

from typing import Callable

from pynput import keyboard

_MOD_NAMES = {
    keyboard.Key.ctrl,
    keyboard.Key.ctrl_l,
    keyboard.Key.ctrl_r,
    keyboard.Key.alt,
    keyboard.Key.alt_l,
    keyboard.Key.alt_r,
    keyboard.Key.alt_gr,
    keyboard.Key.shift,
    keyboard.Key.shift_l,
    keyboard.Key.shift_r,
    keyboard.Key.cmd,
    keyboard.Key.cmd_l,
    keyboard.Key.cmd_r,
}


def _is_modifier(key) -> bool:
    if key in _MOD_NAMES:
        return True
    value = getattr(key, "value", key)
    return value in (
        keyboard.Key.ctrl.value,
        keyboard.Key.ctrl_l.value,
        keyboard.Key.ctrl_r.value,
        keyboard.Key.alt.value,
        keyboard.Key.alt_l.value,
        keyboard.Key.alt_r.value,
        keyboard.Key.alt_gr.value,
        keyboard.Key.shift.value,
        keyboard.Key.shift_l.value,
        keyboard.Key.shift_r.value,
        keyboard.Key.cmd.value,
        keyboard.Key.cmd_l.value,
        keyboard.Key.cmd_r.value,
    )


def _mod_canon(key):
    if key in (
        keyboard.Key.ctrl,
        keyboard.Key.ctrl_l,
        keyboard.Key.ctrl_r,
        keyboard.Key.ctrl.value,
        keyboard.Key.ctrl_l.value,
        keyboard.Key.ctrl_r.value,
    ):
        return keyboard.Key.ctrl
    if key in (
        keyboard.Key.alt,
        keyboard.Key.alt_l,
        keyboard.Key.alt_r,
        keyboard.Key.alt_gr,
        keyboard.Key.alt.value,
        keyboard.Key.alt_l.value,
        keyboard.Key.alt_r.value,
        keyboard.Key.alt_gr.value,
    ):
        return keyboard.Key.alt
    if key in (
        keyboard.Key.shift,
        keyboard.Key.shift_l,
        keyboard.Key.shift_r,
        keyboard.Key.shift.value,
        keyboard.Key.shift_l.value,
        keyboard.Key.shift_r.value,
    ):
        return keyboard.Key.shift
    if key in (
        keyboard.Key.cmd,
        keyboard.Key.cmd_l,
        keyboard.Key.cmd_r,
        keyboard.Key.cmd.value,
        keyboard.Key.cmd_l.value,
        keyboard.Key.cmd_r.value,
    ):
        return keyboard.Key.cmd
    return None


def _letter(key) -> str:
    char = getattr(key, "char", None)
    if char and len(char) == 1 and char.isalpha():
        return char.lower()
    return ""


def _action_matches(pressed, raw, needed) -> bool:
    if pressed == needed or raw == needed:
        return True
    want = _letter(needed)
    if want:
        got = _letter(pressed) or _letter(raw)
        if got == want:
            return True
        vk = getattr(pressed, "vk", None) or getattr(raw, "vk", None)
        if vk == ord(want.upper()):
            return True
        # Ctrl turns G into '\x07'; still count it as G.
        raw_char = getattr(raw, "char", None) or getattr(pressed, "char", None)
        if raw_char and len(raw_char) == 1 and ord(raw_char) == (ord(want) & 31):
            return True
    return False


class StrictHotKeys(keyboard.Listener):
    """Like GlobalHotKeys, but Ctrl+Alt alone never counts as a combo."""

    def __init__(self, hotkeys: dict[str, Callable], **kwargs):
        self._combos: list[tuple[set, object, Callable]] = []
        for spec, callback in hotkeys.items():
            parsed = keyboard.HotKey.parse(spec)
            mods = set()
            action = None
            for part in parsed:
                if _is_modifier(part):
                    mods.add(_mod_canon(part))
                else:
                    action = part
            if action is None or None in mods:
                continue
            self._combos.append((mods, action, callback))
        self._mods_down: set = set()
        super().__init__(on_press=self._press, on_release=self._release, **kwargs)

    def _press(self, key, injected=False) -> None:
        if injected:
            return
        canon = self.canonical(key)
        mod = _mod_canon(canon) or _mod_canon(key)
        if mod is not None:
            self._mods_down.add(mod)
            return
        for mods, action, callback in self._combos:
            if mods <= self._mods_down and _action_matches(canon, key, action):
                callback()
                return

    def _release(self, key, injected=False) -> None:
        if injected:
            return
        canon = self.canonical(key)
        mod = _mod_canon(canon) or _mod_canon(key)
        if mod is not None:
            self._mods_down.discard(mod)

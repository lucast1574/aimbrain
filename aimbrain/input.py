"""
Low-level input primitives — mouse and keyboard.

Uses Win32 ctypes for fast mouse input when available, falls back to pyautogui.
All functions resolve named binds (e.g. "forward" → "w") via config.
"""

import time

import pyautogui

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

from aimbrain import config as _config

# ─── Win32 acceleration ──────────────────────────────────────────────

try:
    import ctypes
    _user32 = ctypes.windll.user32
    HAS_WIN32 = True
except Exception:
    _user32 = None
    HAS_WIN32 = False

_MOUSEEVENTF_MOVE      = 0x0001
_MOUSEEVENTF_LEFTDOWN  = 0x0002
_MOUSEEVENTF_LEFTUP    = 0x0004
_MOUSEEVENTF_RIGHTDOWN = 0x0008
_MOUSEEVENTF_RIGHTUP   = 0x0010

# ─── Bind resolution ─────────────────────────────────────────────────


def _resolve(name: str) -> str:
    """Resolve a bind name to a key string (e.g. 'forward' → 'w')."""
    return _config.get().binds.get(name, name)


# ─── Mouse ────────────────────────────────────────────────────────────


def mouse_move_relative(dx: int, dy: int):
    """Fast relative mouse move."""
    if HAS_WIN32:
        _user32.mouse_event(_MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
    else:
        pyautogui.moveRel(dx, dy, _pause=False)


def mouse_move_to(x: int, y: int):
    """Absolute mouse move."""
    pyautogui.moveTo(x, y, _pause=False)


def mouse_click(button: str = "left"):
    """Click and release."""
    if HAS_WIN32:
        if button == "left":
            _user32.mouse_event(_MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            _user32.mouse_event(_MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == "right":
            _user32.mouse_event(_MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            _user32.mouse_event(_MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    else:
        pyautogui.click(button=button, _pause=False)


def mouse_click_at(x: int, y: int, button: str = "left", clicks: int = 1):
    """Click at absolute position."""
    pyautogui.click(x, y, clicks=clicks, button=button, _pause=False)


def mouse_down(button: str = "left"):
    """Hold mouse button."""
    if HAS_WIN32:
        flag = _MOUSEEVENTF_LEFTDOWN if button == "left" else _MOUSEEVENTF_RIGHTDOWN
        _user32.mouse_event(flag, 0, 0, 0, 0)
    else:
        pyautogui.mouseDown(button=button, _pause=False)


def mouse_up(button: str = "left"):
    """Release mouse button."""
    if HAS_WIN32:
        flag = _MOUSEEVENTF_LEFTUP if button == "left" else _MOUSEEVENTF_RIGHTUP
        _user32.mouse_event(flag, 0, 0, 0, 0)
    else:
        pyautogui.mouseUp(button=button, _pause=False)


def mouse_position() -> tuple[int, int]:
    pos = pyautogui.position()
    return pos.x, pos.y


# ─── Keyboard ─────────────────────────────────────────────────────────


def key_tap(name: str, duration_ms: int = 0):
    """Press a key by bind name or raw key. Hold for duration_ms if > 0."""
    key = _resolve(name)
    if duration_ms > 0:
        pyautogui.keyDown(key, _pause=False)
        time.sleep(duration_ms / 1000.0)
        pyautogui.keyUp(key, _pause=False)
    else:
        pyautogui.press(key, _pause=False)


def key_down(name: str):
    """Hold a key by bind name."""
    pyautogui.keyDown(_resolve(name), _pause=False)


def key_up(name: str):
    """Release a key by bind name."""
    pyautogui.keyUp(_resolve(name), _pause=False)


def key_write(text: str, interval: float = 0.02):
    """Type text character by character."""
    pyautogui.write(text, interval=interval, _pause=False)


# ─── Safety ───────────────────────────────────────────────────────────

# All keys that macros might hold down — release them all.
_HOLDABLE_KEYS = [
    "w", "a", "s", "d", "space", "leftshift", "leftctrl",
    "e", "q", "r", "z", "x", "c", "v", "g",
]


def release_all():
    """Emergency release of all possibly-held keys and mouse buttons."""
    for k in _HOLDABLE_KEYS:
        try:
            pyautogui.keyUp(k, _pause=False)
        except Exception:
            pass
    mouse_up("left")
    mouse_up("right")


# ─── Screen info ──────────────────────────────────────────────────────


def screen_size() -> tuple[int, int]:
    return pyautogui.size()

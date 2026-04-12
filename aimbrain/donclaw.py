"""
DonClaw Node adapter — routes input/OCR through the remote DonClaw API.

DonClaw Node runs on the gaming PC and provides keyboard, mouse, OCR,
and window management over HTTP. This module wraps that API so the rest
of AimBrain can use it transparently.

KEY RULE: Never request screenshots. Use /ocr (text JSON) only.
"""

import logging
import requests

from aimbrain import config as _config

log = logging.getLogger("aimbrain.donclaw")


def is_enabled() -> bool:
    """Check if DonClaw mode is active."""
    try:
        return _config.get().donclaw_enabled
    except Exception:
        return False


# ─── Session (keep-alive) ────────────────────────────────────────────

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers["Connection"] = "keep-alive"
    return _session


def _url(path: str) -> str:
    return f"{_config.get().donclaw_host}{path}"


def _timeout() -> int:
    return _config.get().donclaw_timeout


# ─── Health ───────────────────────────────────────────────────────────


def ping() -> dict:
    """Check DonClaw Node health."""
    try:
        r = _get_session().get(_url("/ping"), timeout=_timeout())
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def status() -> dict:
    """Get DonClaw Node status/info."""
    try:
        r = _get_session().get(_url("/"), timeout=3)
        return {"ok": r.status_code == 200, "host": _config.get().donclaw_host}
    except Exception as e:
        return {"ok": False, "host": _config.get().donclaw_host, "error": str(e)}


# ─── OCR / Vision (text only, no images!) ─────────────────────────────


def ocr() -> dict:
    """Get all text on screen as JSON. No screenshots."""
    r = _get_session().get(_url("/ocr"), timeout=_timeout())
    r.raise_for_status()
    return r.json()


def find(text: str) -> dict:
    """Find specific text on screen + coordinates."""
    r = _get_session().get(_url("/find"), params={"q": text}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


# ─── Input: Keyboard ──────────────────────────────────────────────────


def key_press(key: str, duration_ms: int = 0):
    """Press and release a key. Hold for duration_ms if > 0."""
    body = {"key": key}
    if duration_ms > 0:
        body["duration"] = duration_ms
    r = _get_session().post(_url("/key"), json=body, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def key_down(key: str):
    """Hold a key down."""
    r = _get_session().post(_url("/key"), json={"key": key, "action": "down"}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def key_up(key: str):
    """Release a key."""
    r = _get_session().post(_url("/key"), json={"key": key, "action": "up"}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def type_text(text: str):
    """Type text string."""
    r = _get_session().post(_url("/type"), json={"text": text}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


# Aliases for input.py compatibility
def key_tap(key: str, duration_ms: int = 0):
    """Alias for key_press (input.py compat)."""
    return key_press(key, duration_ms)


def key_write(text: str, interval: float = 0.02):
    """Alias for type_text (input.py compat)."""
    return type_text(text)


# ─── Input: Mouse ─────────────────────────────────────────────────────


def mouse_click(button: str = "left"):
    """Click mouse button (no position)."""
    return click(button=button)


def mouse_click_at(x: int, y: int, button: str = "left", clicks: int = 1):
    """Click at position (input.py compat)."""
    return click(x, y, button, clicks)


def click(x: int = None, y: int = None, button: str = "left", clicks: int = 1):
    """Mouse click. If x/y provided, moves there first."""
    body = {"button": button, "clicks": clicks}
    if x is not None:
        body["x"] = x
    if y is not None:
        body["y"] = y
    r = _get_session().post(_url("/click"), json=body, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def mouse_move(dx: int = 0, dy: int = 0):
    """Relative mouse move."""
    r = _get_session().post(_url("/move"), json={"dx": dx, "dy": dy}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def mouse_move_relative(dx: int, dy: int):
    """Alias for mouse_move (input.py compat)."""
    return mouse_move(dx, dy)


def mouse_move_to(x: int, y: int):
    """Absolute mouse move."""
    r = _get_session().post(_url("/move"), json={"x": x, "y": y}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def mouse_down(button: str = "left"):
    """Hold mouse button."""
    r = _get_session().post(_url("/mousedown"), json={"button": button}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def mouse_up(button: str = "left"):
    """Release mouse button."""
    r = _get_session().post(_url("/mouseup"), json={"button": button}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


# ─── Actions (high-level) ────────────────────────────────────────────


def act(text: str, **kwargs) -> dict:
    """Find text on screen and click it (smart OCR + click)."""
    body = {"text": text}
    body.update(kwargs)
    r = _get_session().post(_url("/act"), json=body, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def sequence(steps: list[dict]) -> dict:
    """Execute a chain of DonClaw actions."""
    r = _get_session().post(_url("/sequence"), json={"steps": steps}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def focus(name: str) -> dict:
    """Focus a window by name."""
    r = _get_session().post(_url("/focus"), json={"name": name}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def open_url(url: str) -> dict:
    """Open a URL in the default browser."""
    r = _get_session().post(_url("/open"), json={"url": url}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def launch(path: str) -> dict:
    """Launch an application."""
    r = _get_session().post(_url("/launch"), json={"path": path}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


def notify(title: str, body: str) -> dict:
    """Show a desktop notification."""
    r = _get_session().post(_url("/notify"), json={"title": title, "body": body}, timeout=_timeout())
    r.raise_for_status()
    return r.json()


# ─── Safety ───────────────────────────────────────────────────────────


_HOLDABLE_KEYS = [
    "w", "a", "s", "d", "space", "leftshift", "leftctrl",
    "e", "q", "r", "z", "x", "c", "v", "g",
]


def release_all():
    """Emergency: release all possibly-held keys and mouse buttons."""
    for k in _HOLDABLE_KEYS:
        try:
            key_up(k)
        except Exception:
            pass
    try:
        mouse_up("left")
    except Exception:
        pass
    try:
        mouse_up("right")
    except Exception:
        pass

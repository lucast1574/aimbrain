"""
DonClaw Node adapter — routes input/OCR through the remote DonClaw API.

DonClaw Node runs on the gaming PC and provides keyboard, mouse, OCR,
and window management over HTTP. This module wraps that API so the rest
of AimBrain can use it transparently.

Supports both OCR (text) and ultra-compressed screenshots for game vision.
"""

import io
import os
import logging
import subprocess
import tempfile
import time

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


# ─── Screenshot (via PowerShell remote capture) ──────────────────────

_REMOTE_SCREENCAP_DIR = r"C:\screencap"
_CAPTURE_SCRIPT = r"C:\screencap\cap.ps1"
_LOOP_SCRIPT = r"C:\screencap\loop.ps1"
_LOCAL_FRAME = "/tmp/aimbrain_frame.jpg"

_ONESHOT_SCRIPT = """Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$g.Dispose()
$bmp.Save('C:\\screencap\\frame.jpg', [System.Drawing.Imaging.ImageFormat]::Jpeg)
$bmp.Dispose()
"""

_LOOP_SCRIPT_CONTENT = """Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$outPath = 'C:\\screencap\\frame.jpg'
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
Set-Content -Path 'C:\\screencap\\loop_pid.txt' -Value $PID
while ($true) {
    try {
        $bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
        $g.Dispose()
        $bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Jpeg)
        $bmp.Dispose()
    } catch { }
    Start-Sleep -Milliseconds 400
}
"""


def _get_ssh_host() -> str:
    """Get the gaming PC IP from DonClaw host URL."""
    from urllib.parse import urlparse
    parsed = urlparse(_config.get().donclaw_host)
    return parsed.hostname or "192.168.18.6"


def _ssh_target() -> str:
    """user@host for SSH/SCP commands."""
    user = _config.get().donclaw_ssh_user
    return f"{user}@{_get_ssh_host()}"


def screenshot_capture() -> bytes | None:
    """
    Grab the latest screenshot from the gaming PC.
    Fast path: SCP download (~650ms) when capture loop is running.
    Fallback: launches one-shot capture if no frame exists.
    """
    target = _ssh_target()
    try:
        # Fast: grab latest frame from continuous loop
        result = subprocess.run(
            ["scp", "-o", "ConnectTimeout=2", "-q",
             f"{target}:C:/screencap/frame.jpg", _LOCAL_FRAME],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            with open(_LOCAL_FRAME, "rb") as f:
                return f.read()

        # Fallback: one-shot capture
        log.info("No frame ready, launching one-shot capture...")
        _get_session().post(
            _url("/launch"),
            json={"path": "powershell.exe",
                  "args": f"-ExecutionPolicy Bypass -WindowStyle Hidden -File {_CAPTURE_SCRIPT}"},
            timeout=5,
        )
        time.sleep(2.5)
        result = subprocess.run(
            ["scp", "-o", "ConnectTimeout=2", "-q",
             f"{target}:C:/screencap/frame.jpg", _LOCAL_FRAME],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            with open(_LOCAL_FRAME, "rb") as f:
                return f.read()

        log.warning(f"Screenshot failed: {result.stderr.decode()}")
        return None
    except Exception as e:
        log.warning(f"Screenshot capture failed: {e}")
        return None


def screenshot_optimized(width: int = 480, quality: int = 15) -> bytes | None:
    """
    Grab + compress screenshot for AI vision.
    Returns ultra-compressed JPEG (~8-20KB). Total ~700ms.
    """
    raw = screenshot_capture()
    if not raw:
        return None
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        ratio = img.height / img.width
        img = img.resize((width, int(width * ratio)), Image.NEAREST)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception as e:
        log.warning(f"Screenshot optimization failed: {e}")
        return raw


def ensure_capture_script():
    """Deploy capture scripts to the gaming PC. Called once at startup."""
    target = _ssh_target()
    try:
        subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", target,
             f"mkdir {_REMOTE_SCREENCAP_DIR} 2>nul"],
            capture_output=True, timeout=5,
        )
        for content, remote in [
            (_ONESHOT_SCRIPT, _CAPTURE_SCRIPT),
            (_LOOP_SCRIPT_CONTENT, _LOOP_SCRIPT),
        ]:
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False)
            tmp.write(content)
            tmp.close()
            subprocess.run(
                ["scp", "-o", "ConnectTimeout=3", "-q", tmp.name,
                 f"{target}:{remote}"],
                capture_output=True, timeout=5,
            )
            os.unlink(tmp.name)
        log.info("Capture scripts deployed")
    except Exception as e:
        log.warning(f"Failed to deploy capture scripts: {e}")


def start_capture_loop():
    """Start continuous capture loop on the gaming PC (~400ms per frame)."""
    try:
        r = _get_session().post(
            _url("/launch"),
            json={"path": "powershell.exe",
                  "args": f"-ExecutionPolicy Bypass -WindowStyle Hidden -File {_LOOP_SCRIPT}"},
            timeout=5,
        )
        r.raise_for_status()
        log.info("Capture loop started on gaming PC")
        time.sleep(2)
        return True
    except Exception as e:
        log.warning(f"Failed to start capture loop: {e}")
        return False


def stop_capture_loop():
    """Stop the capture loop."""
    target = _ssh_target()
    try:
        subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", target,
             'for /f %i in (C:\\screencap\\loop_pid.txt) do taskkill /pid %i /f'],
            capture_output=True, timeout=5,
        )
        return True
    except Exception:
        return False


# ─── Safety ───────────────────────────────────────────────────────────

_HOLDABLE_KEYS = [
    "w", "a", "s", "d", "space", "lshift", "leftctrl",
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

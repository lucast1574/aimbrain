"""
HTTP server — threaded, fast, exposes all endpoints.

This is the only module that imports everything and wires it together.
Run with: python -m aimbrain
"""

import json
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import pyautogui

from aimbrain import __version__
from aimbrain import config as _config
from aimbrain import screenshot
from aimbrain import input as inp
from aimbrain.macros import MACROS, list_macros, run as run_macro, exists as macro_exists

log = logging.getLogger("aimbrain.server")

# ─── Performance stats ───────────────────────────────────────────────

_stats_lock = threading.Lock()
_stats = {
    "screenshots": 0,
    "macros_run": 0,
    "actions": 0,
    "requests": 0,
    "start_time": time.time(),
    "last_activity": time.time(),
}


def _stat_inc(key: str, n: int = 1):
    with _stats_lock:
        _stats[key] = _stats.get(key, 0) + n
        _stats["last_activity"] = time.time()


def _get_stats() -> dict:
    with _stats_lock:
        s = _stats.copy()
    s["uptime_s"] = round(time.time() - s["start_time"], 1)
    s["idle_s"] = round(time.time() - s["last_activity"], 1)
    return s


# ─── Threaded HTTP server ────────────────────────────────────────────


class _ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    request_queue_size = 32


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if _config.get().log_requests:
            log.debug(fmt % args)

    # ── Response helpers ──────────────────────────────────────────────

    def _ok(self, data: bytes, content_type: str = "application/json"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(data))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._ok(json.dumps(obj, separators=(",", ":")).encode())

    def _error(self, code: int, msg: str):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        cl = int(self.headers.get("Content-Length", 0))
        if cl > 0:
            return json.loads(self.rfile.read(cl))
        return {}

    # ── GET ───────────────────────────────────────────────────────────

    def do_GET(self):
        _stat_inc("requests")
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        p = parsed.path
        cfg = _config.get()

        if p == "/ping":
            self._json({"ok": True, "version": __version__, "ts": time.time()})

        elif p == "/screenshot":
            monitor = int(params.get("monitor", [cfg.monitor])[0])
            quality = int(params.get("quality", [cfg.screenshot_quality])[0])
            scale = float(params.get("scale", [cfg.screenshot_scale])[0])
            data = screenshot.capture(monitor=monitor, quality=quality, scale=scale)
            _stat_inc("screenshots")
            self._ok(data, "image/jpeg")

        elif p == "/screenshot/region":
            x = int(params.get("x", [0])[0])
            y = int(params.get("y", [0])[0])
            w = int(params.get("w", [400])[0])
            h = int(params.get("h", [200])[0])
            q = int(params.get("quality", [70])[0])
            data = screenshot.capture_region(x, y, w, h, q)
            _stat_inc("screenshots")
            self._ok(data, "image/jpeg")

        elif p == "/monitors":
            import mss as _mss
            with _mss.mss() as sct:
                self._json([{"index": i, **m} for i, m in enumerate(sct.monitors)])

        elif p == "/mouse":
            x, y = inp.mouse_position()
            self._json({"x": x, "y": y})

        elif p == "/screen_size":
            w, h = inp.screen_size()
            self._json({"width": w, "height": h})

        elif p == "/binds":
            self._json(cfg.binds)

        elif p == "/macros":
            names = list_macros()
            self._json({"macros": names, "count": len(names)})

        elif p == "/stats":
            self._json(_get_stats())

        elif p == "/config":
            self._json(cfg.to_dict())

        else:
            self._error(404, "not found")

    # ── POST ──────────────────────────────────────────────────────────

    def do_POST(self):
        _stat_inc("requests")
        p = urlparse(self.path).path
        body = self._body()

        if p == "/click":
            inp.mouse_click_at(
                body.get("x", 960), body.get("y", 540),
                body.get("button", "left"), body.get("clicks", 1),
            )
            _stat_inc("actions")
            self._json({"ok": True})

        elif p == "/move":
            dx, dy = body.get("dx"), body.get("dy")
            if dx is not None or dy is not None:
                inp.mouse_move_relative(dx or 0, dy or 0)
            else:
                inp.mouse_move_to(body.get("x", 960), body.get("y", 540))
            _stat_inc("actions")
            self._json({"ok": True})

        elif p == "/mousedown":
            inp.mouse_down(body.get("button", "left"))
            _stat_inc("actions")
            self._json({"ok": True})

        elif p == "/mouseup":
            inp.mouse_up(body.get("button", "left"))
            _stat_inc("actions")
            self._json({"ok": True})

        elif p == "/key":
            inp.key_tap(body.get("key", "space"), body.get("duration", 0))
            _stat_inc("actions")
            self._json({"ok": True})

        elif p == "/keys":
            results = self._handle_batch(body.get("actions", []))
            self._json({"ok": True, "results": results})

        elif p == "/macro":
            name = body.get("name")
            if not macro_exists(name):
                self._error(400, f"Unknown macro: {name}")
                return
            try:
                run_macro(name, body.get("params", {}))
                _stat_inc("macros_run")
                self._json({"ok": True, "macro": name})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})

        elif p == "/macro_sequence":
            results = []
            for step in body.get("steps", []):
                name = step.get("name")
                if macro_exists(name):
                    try:
                        run_macro(name, step.get("params", {}))
                        results.append({"ok": True, "macro": name})
                        _stat_inc("macros_run")
                    except Exception as e:
                        results.append({"ok": False, "macro": name, "error": str(e)})
                else:
                    results.append({"ok": False, "macro": name, "error": "unknown"})
                wait = step.get("wait_ms", 0)
                if wait > 0:
                    time.sleep(wait / 1000.0)
            self._json({"ok": True, "results": results})

        elif p == "/binds":
            _config.get().update_binds(body)
            self._json({"ok": True, "binds": _config.get().binds})

        elif p == "/config":
            _config.get().update_settings(body)
            self._json({"ok": True})

        elif p == "/focus":
            self._handle_focus()

        elif p == "/release_all":
            inp.release_all()
            self._json({"ok": True})

        else:
            self._error(404, "not found")

    # ── Batch action handler ──────────────────────────────────────────

    def _handle_batch(self, actions: list) -> list:
        results = []
        for a in actions:
            t = a.get("type")
            try:
                if t == "key":
                    inp.key_tap(a.get("key", "space"), a.get("duration", 0))
                elif t == "keydown":
                    inp.key_down(a["key"])
                elif t == "keyup":
                    inp.key_up(a["key"])
                elif t == "click":
                    inp.mouse_click_at(
                        a.get("x", 960), a.get("y", 540),
                        a.get("button", "left"), a.get("clicks", 1),
                    )
                elif t == "move":
                    inp.mouse_move_to(a.get("x", 960), a.get("y", 540))
                elif t == "moverel":
                    inp.mouse_move_relative(a.get("dx", 0), a.get("dy", 0))
                elif t == "mousedown":
                    inp.mouse_down(a.get("button", "left"))
                elif t == "mouseup":
                    inp.mouse_up(a.get("button", "left"))
                elif t == "wait":
                    time.sleep(a.get("ms", 100) / 1000.0)
                elif t == "write":
                    inp.key_write(a.get("text", ""))
                elif t == "macro":
                    name = a.get("name")
                    if macro_exists(name):
                        run_macro(name, a.get("params", {}))
                        _stat_inc("macros_run")
                results.append({"ok": True})
            except Exception as e:
                results.append({"ok": False, "error": str(e)})
        _stat_inc("actions", len(actions))
        return results

    # ── Focus Fortnite ────────────────────────────────────────────────

    def _handle_focus(self):
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-c",
                 "$p = Get-Process -Name FortniteClient-Win64-Shipping "
                 "-EA SilentlyContinue | Select -First 1; "
                 "if($p){Add-Type '[DllImport(\"user32.dll\")]public static "
                 "extern bool SetForegroundWindow(IntPtr h);' "
                 "-Name W -Namespace W -PassThru|Out-Null;"
                 "[W.W]::SetForegroundWindow($p.MainWindowHandle)}"],
                capture_output=True, timeout=5,
            )
            self._json({"ok": True})
        except Exception as e:
            self._json({"ok": False, "error": str(e)})


# ─── Main entry point ────────────────────────────────────────────────


def main():
    """Start the AimBrain agent server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Find config.json next to the package or cwd
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        config_path = Path.cwd() / "config.json"

    cfg = _config.init(config_path)

    log.info("=" * 52)
    log.info(f"  AimBrain v{__version__} — Fortnite Vision Agent")
    log.info(f"  Port: {cfg.port}")
    log.info(f"  Screenshot: JPEG q={cfg.screenshot_quality} scale={cfg.screenshot_scale}")
    log.info(f"  Macros: {len(MACROS)} available")
    log.info(f"  Win32 fast input: {'YES' if inp.HAS_WIN32 else 'NO'}")
    log.info("=" * 52)
    log.info("GET  /screenshot /screenshot/region /ping /stats /macros /binds")
    log.info("POST /macro /macro_sequence /keys /click /move /key")
    log.info("POST /release_all /focus /config /binds")
    log.info("Ready for commands!")

    server = _ThreadedServer(("0.0.0.0", cfg.port), _Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        server.shutdown()

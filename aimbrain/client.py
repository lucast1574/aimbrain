"""
AimBrain Client SDK — connect to the agent from anywhere on the network.

Usage:
    from aimbrain.client import AimBrain
    bot = AimBrain("http://192.168.1.100:9777")
    bot.aim_shoot(duration=400)
"""

import json
import base64
import requests


class AimBrain:
    """Python SDK for controlling the AimBrain agent remotely."""

    def __init__(self, host: str = "http://localhost:9777", timeout: int = 10):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Connection"] = "keep-alive"

    def _url(self, path: str) -> str:
        return f"{self.host}{path}"

    def _get(self, path: str, **params):
        r = self.session.get(self._url(path), params=params, timeout=self.timeout)
        r.raise_for_status()
        return r

    def _post(self, path: str, data: dict | None = None) -> dict:
        r = self.session.post(self._url(path), json=data or {}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ── Info ──────────────────────────────────────────────────────────

    def ping(self) -> dict:
        return self._get("/ping").json()

    def stats(self) -> dict:
        return self._get("/stats").json()

    def screen_size(self) -> dict:
        return self._get("/screen_size").json()

    def list_macros(self) -> list[str]:
        return self._get("/macros").json()["macros"]

    def get_binds(self) -> dict:
        return self._get("/binds").json()

    # ── Screenshots ──────────────────────────────────────────────────

    def screenshot(self, quality: int = 45, scale: float = 0.5) -> bytes:
        """Full screenshot as raw JPEG bytes."""
        return self._get("/screenshot", quality=quality, scale=scale).content

    def screenshot_b64(self, quality: int = 45, scale: float = 0.5) -> str:
        """Screenshot as base64 string (for LLM vision APIs)."""
        return base64.b64encode(self.screenshot(quality, scale)).decode()

    def screenshot_region(self, x: int, y: int, w: int, h: int, quality: int = 70) -> bytes:
        """Capture a specific screen region as JPEG bytes."""
        return self._get("/screenshot/region", x=x, y=y, w=w, h=h, quality=quality).content

    def save_screenshot(self, path: str = "screen.jpg", **kwargs) -> str:
        with open(path, "wb") as f:
            f.write(self.screenshot(**kwargs))
        return path

    # ── Raw input ─────────────────────────────────────────────────────

    def click(self, x: int = 960, y: int = 540, button: str = "left", clicks: int = 1):
        return self._post("/click", {"x": x, "y": y, "button": button, "clicks": clicks})

    def move(self, x: int | None = None, y: int | None = None,
             dx: int | None = None, dy: int | None = None):
        return self._post("/move", {"x": x, "y": y, "dx": dx, "dy": dy})

    def mouse_down(self, button: str = "left"):
        return self._post("/mousedown", {"button": button})

    def mouse_up(self, button: str = "left"):
        return self._post("/mouseup", {"button": button})

    def key(self, key: str, duration: int = 0):
        return self._post("/key", {"key": key, "duration": duration})

    def keys(self, actions: list[dict]):
        """Send a batch of low-level actions in one request."""
        return self._post("/keys", {"actions": actions})

    # ── Macros ────────────────────────────────────────────────────────

    def macro(self, name: str, **params) -> dict:
        """Execute a single game macro."""
        return self._post("/macro", {"name": name, "params": params})

    def macro_sequence(self, steps: list[dict]) -> dict:
        """Chain multiple macros. Each: {"name": ..., "params": {}, "wait_ms": 0}"""
        return self._post("/macro_sequence", {"steps": steps})

    # ── Convenience wrappers ──────────────────────────────────────────

    def shoot(self, duration=200):          return self.macro("shoot", duration=duration)
    def aim_shoot(self, duration=300):      return self.macro("aim_shoot", duration=duration)
    def spray(self, duration=1000):         return self.macro("spray", duration=duration)
    def tap_fire(self, count=3):            return self.macro("tap_shoot", count=count)
    def look(self, dx=0, dy=0):             return self.macro("look", dx=dx, dy=dy)
    def smooth_look(self, dx=0, dy=0):      return self.macro("smooth_look", dx=dx, dy=dy)
    def switch_weapon(self, slot):          return self.macro("switch_weapon", slot=slot)
    def build_cover(self):                  return self.macro("build_cover")
    def ramp_rush(self, count=3):           return self.macro("ramp_rush", count=count)
    def emergency(self):                    return self.macro("emergency")
    def loot(self, duration=3000):          return self.macro("loot_area", duration=duration)
    def explore(self, duration=3000):       return self.macro("move", pattern="explore", duration=duration)
    def sprint(self, duration=2000):        return self.macro("move", pattern="sprint_forward", duration=duration)
    def zigzag(self, duration=2000):        return self.macro("move", pattern="zigzag", duration=duration)
    def evade(self, duration=2000):         return self.macro("move", pattern="evasive", duration=duration)
    def pickup(self):                       return self.macro("pickup")
    def reload(self):                       return self.macro("reload")
    def open_chest(self):                   return self.macro("open_chest")
    def harvest(self, swings=5):            return self.macro("harvest", swings=swings)
    def disengage(self):                    return self.macro("disengage")

    # ── System ────────────────────────────────────────────────────────

    def focus_fortnite(self):               return self._post("/focus")
    def release_all(self):                  return self._post("/release_all")

    # ── Pre-built plays ───────────────────────────────────────────────

    def land_and_loot(self):
        return self.macro_sequence([
            {"name": "drop_in", "params": {"duration": 4000}},
            {"name": "loot_sweep", "params": {"duration": 5000}, "wait_ms": 500},
        ])

    def fight_sequence(self, weapon_slot=1):
        return self.macro_sequence([
            {"name": "switch_weapon", "params": {"slot": weapon_slot}},
            {"name": "build_cover", "wait_ms": 200},
            {"name": "crouch_peek", "wait_ms": 100},
            {"name": "crouch_peek"},
        ])

    def push_enemy(self, ramps=3, weapon_slot=1):
        return self.macro_sequence([
            {"name": "wall_ramp", "params": {"count": ramps}},
            {"name": "switch_weapon", "params": {"slot": weapon_slot}, "wait_ms": 100},
            {"name": "aim_shoot", "params": {"duration": 500}},
        ])

    def box_fight_peek(self, direction="right"):
        peek = "peek_right" if direction == "right" else "peek_left"
        return self.macro_sequence([
            {"name": "build_cover_ramp", "wait_ms": 200},
            {"name": peek, "wait_ms": 100},
            {"name": peek, "wait_ms": 100},
            {"name": "edit_reset"},
        ])

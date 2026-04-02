"""
AimBrain Controller — AI decision loop example.

Connects to the agent running on the gaming PC, grabs screenshots,
and executes game actions. Designed to be driven by an LLM or
standalone vision pipeline.
"""
import io
import time
import json
import base64
import argparse
import requests
from urllib.parse import urljoin

DEFAULT_HOST = "http://192.168.18.6:9777"


class AimBrain:
    """Client SDK for the AimBrain Fortnite agent."""

    def __init__(self, host=DEFAULT_HOST, timeout=5):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Connection"] = "keep-alive"

    def _url(self, path):
        return f"{self.host}{path}"

    def _get(self, path, **params):
        r = self.session.get(self._url(path), params=params, timeout=self.timeout)
        r.raise_for_status()
        return r

    def _post(self, path, data=None):
        r = self.session.post(self._url(path), json=data or {}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ── Info ──────────────────────────────────────────────────────────

    def ping(self):
        return self._get("/ping").json()

    def stats(self):
        return self._get("/stats").json()

    def screen_size(self):
        return self._get("/screen_size").json()

    def list_macros(self):
        return self._get("/macros").json()["macros"]

    def get_binds(self):
        return self._get("/binds").json()

    # ── Screenshots ──────────────────────────────────────────────────

    def screenshot(self, quality=45, scale=0.5):
        """Get full screenshot as raw JPEG bytes."""
        r = self._get("/screenshot", quality=quality, scale=scale)
        return r.content

    def screenshot_b64(self, quality=45, scale=0.5):
        """Get screenshot as base64 string (for LLM vision APIs)."""
        return base64.b64encode(self.screenshot(quality, scale)).decode()

    def screenshot_region(self, x, y, w, h, quality=70):
        """Get a specific screen region as JPEG bytes."""
        r = self._get("/screenshot/region", x=x, y=y, w=w, h=h, quality=quality)
        return r.content

    def save_screenshot(self, path="screen.jpg", quality=45, scale=0.5):
        data = self.screenshot(quality, scale)
        with open(path, "wb") as f:
            f.write(data)
        return path

    # ── Input ─────────────────────────────────────────────────────────

    def click(self, x=960, y=540, button="left", clicks=1):
        return self._post("/click", {"x": x, "y": y, "button": button, "clicks": clicks})

    def move(self, x=None, y=None, dx=None, dy=None):
        return self._post("/move", {"x": x, "y": y, "dx": dx, "dy": dy})

    def mouse_down(self, button="left"):
        return self._post("/mousedown", {"button": button})

    def mouse_up(self, button="left"):
        return self._post("/mouseup", {"button": button})

    def key(self, key, duration=0):
        return self._post("/key", {"key": key, "duration": duration})

    def keys(self, actions):
        """Send a batch of low-level actions in one request."""
        return self._post("/keys", {"actions": actions})

    # ── Macros ────────────────────────────────────────────────────────

    def macro(self, name, **params):
        """Execute a single game macro."""
        return self._post("/macro", {"name": name, "params": params})

    def macro_sequence(self, steps):
        """
        Execute a chain of macros. Each step:
        {"name": "macro_name", "params": {...}, "wait_ms": 0}
        """
        return self._post("/macro_sequence", {"steps": steps})

    # ── Convenience ───────────────────────────────────────────────────

    def shoot(self, duration=200):
        return self.macro("shoot", duration=duration)

    def aim_shoot(self, duration=300):
        return self.macro("aim_shoot", duration=duration)

    def spray(self, duration=1000):
        return self.macro("spray", duration=duration)

    def tap_fire(self, count=3):
        return self.macro("tap_shoot", count=count)

    def look(self, dx=0, dy=0):
        return self.macro("look", dx=dx, dy=dy)

    def smooth_look(self, dx=0, dy=0, steps=5):
        return self.macro("smooth_look", dx=dx, dy=dy, steps=steps)

    def switch_weapon(self, slot):
        return self.macro("switch_weapon", slot=slot)

    def build_cover(self):
        return self.macro("build_cover")

    def ramp_rush(self, count=3):
        return self.macro("ramp_rush", count=count)

    def emergency(self):
        return self.macro("emergency")

    def loot(self, duration=3000):
        return self.macro("loot_area", duration=duration)

    def explore(self, duration=3000):
        return self.macro("move", pattern="explore", duration=duration)

    def sprint(self, duration=2000):
        return self.macro("move", pattern="sprint_forward", duration=duration)

    def zigzag(self, duration=2000):
        return self.macro("move", pattern="zigzag", duration=duration)

    def evade(self, duration=2000):
        return self.macro("move", pattern="evasive", duration=duration)

    def pickup(self):
        return self.macro("pickup")

    def reload(self):
        return self.macro("reload")

    def open_chest(self):
        return self.macro("open_chest")

    def harvest(self, swings=5):
        return self.macro("harvest", swings=swings)

    def disengage(self):
        return self.macro("disengage")

    def focus_fortnite(self):
        return self._post("/focus")

    def release_all(self):
        return self._post("/release_all")

    # ── Complex sequences ─────────────────────────────────────────────

    def land_and_loot(self):
        """Drop from bus, dive fast, then loot the landing area."""
        return self.macro_sequence([
            {"name": "drop_in", "params": {"duration": 4000}},
            {"name": "loot_sweep", "params": {"duration": 5000}, "wait_ms": 500},
        ])

    def fight_sequence(self, weapon_slot=1):
        """Switch to weapon, build cover, peek and shoot."""
        return self.macro_sequence([
            {"name": "switch_weapon", "params": {"slot": weapon_slot}},
            {"name": "build_cover", "wait_ms": 200},
            {"name": "crouch_peek", "wait_ms": 100},
            {"name": "crouch_peek"},
        ])

    def push_enemy(self, ramps=3, weapon_slot=1):
        """Ramp rush then swap to weapon and fire."""
        return self.macro_sequence([
            {"name": "wall_ramp", "params": {"count": ramps}},
            {"name": "switch_weapon", "params": {"slot": weapon_slot}, "wait_ms": 100},
            {"name": "aim_shoot", "params": {"duration": 500}},
        ])

    def box_fight_peek(self, direction="right"):
        """Build box, edit wall, peek shoot, reset edit."""
        peek = "peek_right" if direction == "right" else "peek_left"
        return self.macro_sequence([
            {"name": "build_cover_ramp", "wait_ms": 200},
            {"name": peek, "wait_ms": 100},
            {"name": peek, "wait_ms": 100},
            {"name": "edit_reset"},
        ])


# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AimBrain Controller")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Agent URL")
    parser.add_argument("--ping", action="store_true", help="Ping the agent")
    parser.add_argument("--screenshot", type=str, help="Save screenshot to file")
    parser.add_argument("--macros", action="store_true", help="List available macros")
    parser.add_argument("--macro", type=str, help="Run a macro by name")
    parser.add_argument("--params", type=str, default="{}", help="JSON params for macro")
    parser.add_argument("--stats", action="store_true", help="Show agent stats")
    parser.add_argument("--focus", action="store_true", help="Focus Fortnite window")
    parser.add_argument("--release", action="store_true", help="Release all held keys")
    args = parser.parse_args()

    bot = AimBrain(host=args.host)

    if args.ping:
        print(json.dumps(bot.ping(), indent=2))
    elif args.screenshot:
        bot.save_screenshot(args.screenshot)
        print(f"Saved: {args.screenshot}")
    elif args.macros:
        for m in bot.list_macros():
            print(f"  • {m}")
    elif args.macro:
        params = json.loads(args.params)
        result = bot.macro(args.macro, **params)
        print(json.dumps(result, indent=2))
    elif args.stats:
        print(json.dumps(bot.stats(), indent=2))
    elif args.focus:
        print(json.dumps(bot.focus_fortnite(), indent=2))
    elif args.release:
        print(json.dumps(bot.release_all(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

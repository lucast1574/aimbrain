"""
AimBrain — Fortnite Vision Agent v3
Remote game agent: fast screenshots, batched input, game-aware macros,
health/ammo/storm HUD reading, and an AI-ready control API.

Runs on the gaming PC, controlled remotely over HTTP.
"""
import io
import json
import time
import random
import logging
import threading
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
except ImportError:
    sys.exit("ERROR: pip install pyautogui")

try:
    import mss
except ImportError:
    sys.exit("ERROR: pip install mss")

try:
    from PIL import Image
except ImportError:
    sys.exit("ERROR: pip install Pillow")

try:
    import ctypes
    user32 = ctypes.windll.user32
    HAVE_WIN32 = True
except Exception:
    HAVE_WIN32 = False

# ─── Config ───────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "port": 9777,
    "monitor": 0,
    "screenshot_quality": 45,
    "screenshot_scale": 0.5,
    "screenshot_cache_ms": 50,
    "log_requests": False,
    "binds": {
        "forward": "w", "back": "s", "left": "a", "right": "d",
        "jump": "space", "crouch": "leftctrl", "sprint": "leftshift",
        "reload": "r", "interact": "e", "inventory": "tab", "map": "m",
        "pickaxe": "1", "slot1": "2", "slot2": "3", "slot3": "4",
        "slot4": "5", "slot5": "6",
        "build_wall": "z", "build_floor": "x", "build_stair": "c",
        "build_roof": "v", "build_mode": "q", "edit": "g",
        "trap": "t", "use": "e", "emote": "b",
    },
}


def load_config():
    cfg = DEFAULT_CONFIG.copy()
    cfg["binds"] = DEFAULT_CONFIG["binds"].copy()
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                user = json.load(f)
            if "binds" in user:
                cfg["binds"].update(user.pop("binds"))
            cfg.update(user)
        except Exception as e:
            logging.warning(f"Config load failed: {e}, using defaults")
    return cfg


CFG = load_config()
BINDS = CFG["binds"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("aimbrain")

# ─── Win32 constants ─────────────────────────────────────────────────
MOUSEEVENTF_MOVE      = 0x0001
MOUSEEVENTF_LEFTDOWN  = 0x0002
MOUSEEVENTF_LEFTUP    = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP   = 0x0010

# ─── Performance stats ───────────────────────────────────────────────
_stats_lock = threading.Lock()
_stats = {
    "screenshots": 0,
    "macros": 0,
    "actions": 0,
    "start_time": time.time(),
    "last_activity": time.time(),
}


def stat_inc(key, n=1):
    with _stats_lock:
        _stats[key] = _stats.get(key, 0) + n
        _stats["last_activity"] = time.time()


# ─── Screenshot engine ───────────────────────────────────────────────
_ss_lock = threading.Lock()
_ss_cache = {"data": None, "ts": 0}


def fast_screenshot(monitor=None, quality=None, scale=None, region=None):
    """
    Grab screen as compressed JPEG. Supports full screen or cropped region.
    region: {"x": int, "y": int, "w": int, "h": int} for partial capture.
    """
    monitor = monitor if monitor is not None else CFG["monitor"]
    quality = quality if quality is not None else CFG["screenshot_quality"]
    scale = scale if scale is not None else CFG["screenshot_scale"]
    cache_ttl = CFG["screenshot_cache_ms"] / 1000.0

    now = time.time()
    if not region:
        with _ss_lock:
            if _ss_cache["data"] and (now - _ss_cache["ts"]) < cache_ttl:
                stat_inc("screenshots")
                return _ss_cache["data"]

    with mss.mss() as sct:
        monitors = sct.monitors
        if monitor >= len(monitors):
            monitor = 0
        if region:
            grab_area = {"left": region["x"], "top": region["y"],
                         "width": region["w"], "height": region["h"]}
            shot = sct.grab(grab_area)
        else:
            shot = sct.grab(monitors[monitor])
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    if scale and scale != 1.0:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.NEAREST)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=False)
    data = buf.getvalue()

    if not region:
        with _ss_lock:
            _ss_cache["data"] = data
            _ss_cache["ts"] = time.time()

    stat_inc("screenshots")
    return data


def screenshot_region_base64(x, y, w, h, quality=60):
    """Grab a screen region and return base64 JPEG (for HUD reading)."""
    import base64
    data = fast_screenshot(region={"x": x, "y": y, "w": w, "h": h},
                           quality=quality, scale=1.0)
    return base64.b64encode(data).decode()


# ─── Input primitives ────────────────────────────────────────────────

def mouse_move_relative(dx, dy):
    if HAVE_WIN32:
        user32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
    else:
        pyautogui.moveRel(dx, dy, _pause=False)


def mouse_click(button="left"):
    if HAVE_WIN32:
        if button == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    else:
        pyautogui.click(button=button, _pause=False)


def mouse_down(button="left"):
    if HAVE_WIN32:
        flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
        user32.mouse_event(flag, 0, 0, 0, 0)
    else:
        pyautogui.mouseDown(button=button, _pause=False)


def mouse_up(button="left"):
    if HAVE_WIN32:
        flag = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP
        user32.mouse_event(flag, 0, 0, 0, 0)
    else:
        pyautogui.mouseUp(button=button, _pause=False)


def key_tap(name, duration_ms=0):
    """Press a named bind or raw key."""
    key = BINDS.get(name, name)
    if duration_ms > 0:
        pyautogui.keyDown(key, _pause=False)
        time.sleep(duration_ms / 1000.0)
        pyautogui.keyUp(key, _pause=False)
    else:
        pyautogui.press(key, _pause=False)


def key_down(name):
    pyautogui.keyDown(BINDS.get(name, name), _pause=False)


def key_up(name):
    pyautogui.keyUp(BINDS.get(name, name), _pause=False)


# ─── Game Macros ──────────────────────────────────────────────────────

def macro_look(dx, dy):
    """Turn the camera by (dx, dy) pixels."""
    mouse_move_relative(dx, dy)


def macro_smooth_look(dx, dy, steps=5):
    """Smooth camera turn over multiple frames (less jarring)."""
    sdx, sdy = dx / steps, dy / steps
    for _ in range(steps):
        mouse_move_relative(sdx, sdy)
        time.sleep(0.01)


def macro_shoot(duration_ms=200):
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")


def macro_aim_shoot(duration_ms=300):
    """ADS + shoot."""
    mouse_down("right")
    time.sleep(0.05)
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")
    mouse_up("right")


def macro_tap_shoot(count=3, interval_ms=100):
    """Tap-fire for accuracy."""
    for i in range(count):
        mouse_down("left")
        time.sleep(0.03)
        mouse_up("left")
        if i < count - 1:
            time.sleep(interval_ms / 1000.0)


def macro_spray(duration_ms=1000):
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")


def macro_burst_spray(bursts=3, burst_ms=300, pause_ms=150):
    """Controlled bursts with recoil reset pauses between them."""
    for i in range(bursts):
        mouse_down("left")
        time.sleep(burst_ms / 1000.0)
        mouse_up("left")
        if i < bursts - 1:
            time.sleep(pause_ms / 1000.0)


def macro_jump_shot():
    key_down("jump")
    time.sleep(0.1)
    mouse_down("left")
    time.sleep(0.2)
    mouse_up("left")
    key_up("jump")


def macro_strafe_shoot(direction="left", duration_ms=500):
    key_down(direction)
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")
    key_up(direction)


def macro_ads_strafe(direction="left", duration_ms=600):
    """ADS + strafe + shoot — precision while mobile."""
    mouse_down("right")
    key_down(direction)
    time.sleep(0.05)
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")
    key_up(direction)
    mouse_up("right")


def macro_shotgun_flick(dx, dy, slot=1):
    """Switch to shotgun, flick aim, fire."""
    macro_switch_weapon(slot)
    time.sleep(0.08)
    mouse_move_relative(dx, dy)
    time.sleep(0.02)
    mouse_click("left")


def macro_double_pump(slot_a=1, slot_b=2):
    """Classic double-pump: fire slot A → swap → fire slot B."""
    macro_switch_weapon(slot_a)
    time.sleep(0.08)
    mouse_click("left")
    time.sleep(0.15)
    macro_switch_weapon(slot_b)
    time.sleep(0.08)
    mouse_click("left")


def macro_pickup():
    key_down("forward")
    for _ in range(5):
        key_tap("interact")
        time.sleep(0.1)
    key_up("forward")


def macro_switch_weapon(slot):
    slot = max(1, min(5, int(slot)))
    key_tap(f"slot{slot}")


def macro_pickaxe():
    key_tap("pickaxe")


def macro_reload():
    key_tap("reload")


def macro_build(piece="wall", count=1):
    key_tap("build_mode")
    time.sleep(0.05)
    for _ in range(count):
        key_tap(f"build_{piece}")
        time.sleep(0.03)
        mouse_click("left")
        time.sleep(0.08)


def macro_build_cover():
    """Quick 1x1 box (4 walls)."""
    key_tap("build_mode")
    time.sleep(0.05)
    for _ in range(4):
        key_tap("build_wall")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.04)
        mouse_move_relative(400, 0)
        time.sleep(0.04)


def macro_build_cover_ramp():
    """1x1 box + ramp inside for high-ground peek."""
    macro_build_cover()
    time.sleep(0.05)
    key_tap("build_stair")
    time.sleep(0.02)
    mouse_click("left")


def macro_ramp_rush(count=3):
    """Sprint + ramp for aggressive push."""
    key_down("sprint")
    key_down("forward")
    key_tap("build_mode")
    time.sleep(0.05)
    for _ in range(count):
        key_tap("build_stair")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.04)
        key_tap("jump")
        time.sleep(0.22)
    key_up("forward")
    key_up("sprint")


def macro_protected_ramp(count=3):
    """Ramp + floor underneath for protected push."""
    key_down("sprint")
    key_down("forward")
    key_tap("build_mode")
    time.sleep(0.05)
    for _ in range(count):
        key_tap("build_floor")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.03)
        key_tap("build_stair")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.03)
        key_tap("jump")
        time.sleep(0.22)
    key_up("forward")
    key_up("sprint")


def macro_wall_ramp(count=3):
    """Wall in front + ramp — the classic push with cover."""
    key_down("sprint")
    key_down("forward")
    key_tap("build_mode")
    time.sleep(0.05)
    for _ in range(count):
        key_tap("build_wall")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.03)
        key_tap("build_stair")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.03)
        key_tap("jump")
        time.sleep(0.22)
    key_up("forward")
    key_up("sprint")


def macro_90s(count=2):
    """90-degree turns for height gain — competitive building."""
    key_tap("build_mode")
    time.sleep(0.05)
    for _ in range(count):
        # Wall + ramp + 90° turn
        key_tap("build_wall")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.03)
        key_tap("build_stair")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.03)
        key_tap("jump")
        mouse_move_relative(450, 0)
        time.sleep(0.15)
        key_tap("build_wall")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.2)


def macro_edit_reset():
    key_tap("edit")
    time.sleep(0.05)
    mouse_click("right")
    time.sleep(0.05)
    key_tap("edit")


def macro_edit_wall(pattern="door"):
    """Edit a wall into a pattern and confirm."""
    key_tap("edit")
    time.sleep(0.08)
    if pattern == "door":
        # Select bottom-right 2 tiles
        mouse_down("left")
        time.sleep(0.03)
        mouse_move_relative(0, 100)
        time.sleep(0.03)
        mouse_up("left")
    elif pattern == "window":
        # Select center tile
        mouse_click("left")
    elif pattern == "half":
        # Select top 3 tiles
        mouse_down("left")
        mouse_move_relative(200, 0)
        time.sleep(0.03)
        mouse_move_relative(200, 0)
        time.sleep(0.03)
        mouse_up("left")
    time.sleep(0.05)
    key_tap("edit")


def macro_move_pattern(pattern="zigzag", duration_ms=2000):
    end_time = time.time() + (duration_ms / 1000.0)

    if pattern == "zigzag":
        key_down("forward")
        toggle = True
        while time.time() < end_time:
            side = "left" if toggle else "right"
            key_down(side)
            time.sleep(0.3)
            key_up(side)
            toggle = not toggle
        key_up("forward")

    elif pattern == "circle":
        key_down("forward")
        while time.time() < end_time:
            mouse_move_relative(60, 0)
            time.sleep(0.05)
        key_up("forward")

    elif pattern == "strafe_random":
        dirs = ["left", "right", "forward", "back"]
        while time.time() < end_time:
            d = random.choice(dirs)
            key_down(d)
            time.sleep(random.uniform(0.15, 0.4))
            key_up(d)

    elif pattern == "sprint_forward":
        key_down("sprint")
        key_down("forward")
        time.sleep(duration_ms / 1000.0)
        key_up("forward")
        key_up("sprint")

    elif pattern == "sprint_jump":
        key_down("sprint")
        key_down("forward")
        while time.time() < end_time:
            key_tap("jump")
            time.sleep(random.uniform(0.5, 0.8))
        key_up("forward")
        key_up("sprint")

    elif pattern == "explore":
        key_down("sprint")
        key_down("forward")
        while time.time() < end_time:
            act = random.choice(["look", "jump", "straight", "strafe", "interact"])
            if act == "look":
                mouse_move_relative(random.randint(-200, 200), random.randint(-30, 30))
                time.sleep(0.2)
            elif act == "jump":
                key_tap("jump")
                time.sleep(0.4)
            elif act == "strafe":
                side = random.choice(["left", "right"])
                key_down(side)
                time.sleep(0.3)
                key_up(side)
            elif act == "interact":
                key_tap("interact")
                time.sleep(0.15)
            else:
                time.sleep(0.3)
        key_up("forward")
        key_up("sprint")

    elif pattern == "evasive":
        # Unpredictable crouch-jump-strafe for combat
        while time.time() < end_time:
            act = random.choice(["jump_left", "jump_right", "crouch", "sprint_fwd"])
            if act == "jump_left":
                key_down("left"); key_tap("jump"); time.sleep(0.3); key_up("left")
            elif act == "jump_right":
                key_down("right"); key_tap("jump"); time.sleep(0.3); key_up("right")
            elif act == "crouch":
                key_down("crouch"); time.sleep(0.2); key_up("crouch")
            else:
                key_down("sprint"); key_down("forward")
                time.sleep(0.3)
                key_up("forward"); key_up("sprint")


def macro_loot_area(duration_ms=3000):
    end_time = time.time() + (duration_ms / 1000.0)
    key_down("forward")
    while time.time() < end_time:
        key_tap("interact")
        mouse_move_relative(120, 0)
        time.sleep(0.08)
    key_up("forward")


def macro_loot_sweep(duration_ms=4000):
    """Walk in a circle looting everything — wider area than loot_area."""
    end_time = time.time() + (duration_ms / 1000.0)
    key_down("forward")
    key_down("sprint")
    while time.time() < end_time:
        key_tap("interact")
        mouse_move_relative(40, 0)
        time.sleep(0.06)
    key_up("sprint")
    key_up("forward")


def macro_drop_in(duration_ms=5000):
    key_down("forward")
    mouse_move_relative(0, 300)
    time.sleep(duration_ms / 1000.0)
    key_up("forward")


def macro_heal():
    key_tap("interact")


def macro_crouch_peek():
    key_down("crouch")
    time.sleep(0.3)
    key_up("crouch")
    time.sleep(0.1)
    macro_tap_shoot(2, 80)
    key_down("crouch")
    time.sleep(0.2)
    key_up("crouch")


def macro_emergency():
    """Panic button: jump → box up → shotgun ready."""
    key_tap("jump")
    time.sleep(0.05)
    macro_build_cover()
    time.sleep(0.1)
    macro_switch_weapon(1)


def macro_open_chest():
    key_down("forward")
    key_down("interact")
    time.sleep(1.2)
    key_up("interact")
    key_up("forward")
    time.sleep(0.3)
    for _ in range(6):
        key_tap("interact")
        time.sleep(0.12)


def macro_swap_shoot(slot, duration_ms=300):
    macro_switch_weapon(slot)
    time.sleep(0.1)
    macro_shoot(duration_ms)


def macro_quick_scope(slot=2, aim_ms=150):
    """Sniper quick-scope: switch → ADS → fire → un-ADS."""
    macro_switch_weapon(slot)
    time.sleep(0.1)
    mouse_down("right")
    time.sleep(aim_ms / 1000.0)
    mouse_click("left")
    time.sleep(0.05)
    mouse_up("right")


def macro_disengage():
    """Break off a fight: build wall, turn 180, sprint away."""
    macro_build("wall", 1)
    time.sleep(0.05)
    mouse_move_relative(1600, 0)  # ~180° turn
    time.sleep(0.05)
    key_down("sprint")
    key_down("forward")
    time.sleep(1.5)
    key_up("forward")
    key_up("sprint")


def macro_harvest(swings=5, move=True):
    """Swing pickaxe at nearby resources."""
    macro_pickaxe()
    time.sleep(0.1)
    if move:
        key_down("forward")
    for _ in range(swings):
        mouse_click("left")
        time.sleep(0.7)
    if move:
        key_up("forward")


def macro_peek_right():
    """Right-hand peek: strafe right, shoot, strafe back."""
    key_down("right")
    time.sleep(0.15)
    macro_tap_shoot(2, 80)
    key_up("right")
    key_down("left")
    time.sleep(0.15)
    key_up("left")


def macro_peek_left():
    """Left-hand peek: strafe left, shoot, strafe back."""
    key_down("left")
    time.sleep(0.15)
    macro_tap_shoot(2, 80)
    key_up("left")
    key_down("right")
    time.sleep(0.15)
    key_up("right")


# ─── Macro Registry ──────────────────────────────────────────────────
MACROS = {
    # Camera
    "look":             lambda p: macro_look(p.get("dx", 0), p.get("dy", 0)),
    "smooth_look":      lambda p: macro_smooth_look(p.get("dx", 0), p.get("dy", 0), p.get("steps", 5)),
    # Combat — shooting
    "shoot":            lambda p: macro_shoot(p.get("duration", 200)),
    "aim_shoot":        lambda p: macro_aim_shoot(p.get("duration", 300)),
    "tap_shoot":        lambda p: macro_tap_shoot(p.get("count", 3), p.get("interval", 100)),
    "spray":            lambda p: macro_spray(p.get("duration", 1000)),
    "burst_spray":      lambda p: macro_burst_spray(p.get("bursts", 3), p.get("burst_ms", 300), p.get("pause_ms", 150)),
    "jump_shot":        lambda p: macro_jump_shot(),
    "strafe_shoot":     lambda p: macro_strafe_shoot(p.get("direction", "left"), p.get("duration", 500)),
    "ads_strafe":       lambda p: macro_ads_strafe(p.get("direction", "left"), p.get("duration", 600)),
    "shotgun_flick":    lambda p: macro_shotgun_flick(p.get("dx", 0), p.get("dy", 0), p.get("slot", 1)),
    "double_pump":      lambda p: macro_double_pump(p.get("slot_a", 1), p.get("slot_b", 2)),
    "quick_scope":      lambda p: macro_quick_scope(p.get("slot", 2), p.get("aim_ms", 150)),
    "crouch_peek":      lambda p: macro_crouch_peek(),
    "peek_right":       lambda p: macro_peek_right(),
    "peek_left":        lambda p: macro_peek_left(),
    "swap_shoot":       lambda p: macro_swap_shoot(p.get("slot", 1), p.get("duration", 300)),
    # Weapons / inventory
    "switch_weapon":    lambda p: macro_switch_weapon(p.get("slot", 1)),
    "pickaxe":          lambda p: macro_pickaxe(),
    "reload":           lambda p: macro_reload(),
    # Looting
    "pickup":           lambda p: macro_pickup(),
    "loot_area":        lambda p: macro_loot_area(p.get("duration", 3000)),
    "loot_sweep":       lambda p: macro_loot_sweep(p.get("duration", 4000)),
    "open_chest":       lambda p: macro_open_chest(),
    "harvest":          lambda p: macro_harvest(p.get("swings", 5), p.get("move", True)),
    # Building
    "build":            lambda p: macro_build(p.get("piece", "wall"), p.get("count", 1)),
    "build_cover":      lambda p: macro_build_cover(),
    "build_cover_ramp": lambda p: macro_build_cover_ramp(),
    "ramp_rush":        lambda p: macro_ramp_rush(p.get("count", 3)),
    "protected_ramp":   lambda p: macro_protected_ramp(p.get("count", 3)),
    "wall_ramp":        lambda p: macro_wall_ramp(p.get("count", 3)),
    "90s":              lambda p: macro_90s(p.get("count", 2)),
    "edit_reset":       lambda p: macro_edit_reset(),
    "edit_wall":        lambda p: macro_edit_wall(p.get("pattern", "door")),
    # Movement
    "move":             lambda p: macro_move_pattern(p.get("pattern", "sprint_forward"), p.get("duration", 2000)),
    "drop_in":          lambda p: macro_drop_in(p.get("duration", 5000)),
    # Utility
    "heal":             lambda p: macro_heal(),
    "emergency":        lambda p: macro_emergency(),
    "disengage":        lambda p: macro_disengage(),
}


# ─── HTTP Server ─────────────────────────────────────────────────────

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    request_queue_size = 32


class AgentHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if CFG["log_requests"]:
            log.debug(fmt % args)

    def _ok(self, data, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(data))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._ok(json.dumps(obj, separators=(",", ":")).encode())

    def _error(self, code, msg):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        cl = int(self.headers.get("Content-Length", 0))
        if cl > 0:
            return json.loads(self.rfile.read(cl))
        return {}

    # ── GET ───────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        p = parsed.path

        if p == "/screenshot":
            monitor = int(params.get("monitor", [CFG["monitor"]])[0])
            quality = int(params.get("quality", [CFG["screenshot_quality"]])[0])
            scale = float(params.get("scale", [CFG["screenshot_scale"]])[0])
            data = fast_screenshot(monitor, quality, scale)
            self._ok(data, "image/jpeg")

        elif p == "/screenshot/region":
            x = int(params.get("x", [0])[0])
            y = int(params.get("y", [0])[0])
            w = int(params.get("w", [400])[0])
            h = int(params.get("h", [200])[0])
            q = int(params.get("quality", [70])[0])
            data = fast_screenshot(region={"x": x, "y": y, "w": w, "h": h},
                                   quality=q, scale=1.0)
            self._ok(data, "image/jpeg")

        elif p == "/monitors":
            with mss.mss() as sct:
                self._json([{"index": i, **m} for i, m in enumerate(sct.monitors)])

        elif p == "/mouse":
            pos = pyautogui.position()
            self._json({"x": pos.x, "y": pos.y})

        elif p == "/ping":
            self._json({"ok": True, "ts": time.time()})

        elif p == "/screen_size":
            w, h = pyautogui.size()
            self._json({"width": w, "height": h})

        elif p == "/binds":
            self._json(BINDS)

        elif p == "/macros":
            self._json({"macros": sorted(MACROS.keys()), "count": len(MACROS)})

        elif p == "/stats":
            with _stats_lock:
                s = _stats.copy()
            s["uptime_s"] = round(time.time() - s["start_time"], 1)
            s["idle_s"] = round(time.time() - s["last_activity"], 1)
            self._json(s)

        elif p == "/config":
            self._json({k: v for k, v in CFG.items() if k != "binds"})

        else:
            self._error(404, "not found")

    # ── POST ──────────────────────────────────────────────────────────

    def do_POST(self):
        p = urlparse(self.path).path
        body = self._read_body()

        if p == "/click":
            x, y = body.get("x", 960), body.get("y", 540)
            pyautogui.click(x, y, clicks=body.get("clicks", 1),
                          button=body.get("button", "left"), _pause=False)
            stat_inc("actions")
            self._json({"ok": True})

        elif p == "/move":
            dx, dy = body.get("dx"), body.get("dy")
            if dx is not None or dy is not None:
                mouse_move_relative(dx or 0, dy or 0)
            else:
                pyautogui.moveTo(body.get("x", 960), body.get("y", 540), _pause=False)
            stat_inc("actions")
            self._json({"ok": True})

        elif p == "/mousedown":
            mouse_down(body.get("button", "left"))
            stat_inc("actions")
            self._json({"ok": True})

        elif p == "/mouseup":
            mouse_up(body.get("button", "left"))
            stat_inc("actions")
            self._json({"ok": True})

        elif p == "/key":
            key_tap(body.get("key", "space"), body.get("duration", 0))
            stat_inc("actions")
            self._json({"ok": True})

        elif p == "/keys":
            actions = body.get("actions", [])
            results = []
            for a in actions:
                t = a.get("type")
                try:
                    if t == "key":
                        key_tap(a.get("key", "space"), a.get("duration", 0))
                    elif t == "keydown":
                        key_down(a["key"])
                    elif t == "keyup":
                        key_up(a["key"])
                    elif t == "click":
                        pyautogui.click(a.get("x", 960), a.get("y", 540),
                                       button=a.get("button", "left"), _pause=False)
                    elif t == "move":
                        pyautogui.moveTo(a.get("x", 960), a.get("y", 540), _pause=False)
                    elif t == "moverel":
                        mouse_move_relative(a.get("dx", 0), a.get("dy", 0))
                    elif t == "mousedown":
                        mouse_down(a.get("button", "left"))
                    elif t == "mouseup":
                        mouse_up(a.get("button", "left"))
                    elif t == "wait":
                        time.sleep(a.get("ms", 100) / 1000.0)
                    elif t == "write":
                        pyautogui.write(a.get("text", ""), interval=0.02, _pause=False)
                    elif t == "macro":
                        name = a.get("name")
                        if name in MACROS:
                            MACROS[name](a.get("params", {}))
                            stat_inc("macros")
                    results.append({"ok": True})
                except Exception as e:
                    results.append({"ok": False, "error": str(e)})
            stat_inc("actions", len(actions))
            self._json({"ok": True, "results": results})

        elif p == "/macro":
            name = body.get("name")
            if name not in MACROS:
                self._error(400, f"Unknown macro: {name}")
                return
            try:
                MACROS[name](body.get("params", {}))
                stat_inc("macros")
                self._json({"ok": True, "macro": name})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})

        elif p == "/macro_sequence":
            steps = body.get("steps", [])
            results = []
            for step in steps:
                name = step.get("name")
                if name in MACROS:
                    try:
                        MACROS[name](step.get("params", {}))
                        results.append({"ok": True, "macro": name})
                        stat_inc("macros")
                    except Exception as e:
                        results.append({"ok": False, "macro": name, "error": str(e)})
                else:
                    results.append({"ok": False, "macro": name, "error": "unknown"})
                wait = step.get("wait_ms", 0)
                if wait > 0:
                    time.sleep(wait / 1000.0)
            self._json({"ok": True, "results": results})

        elif p == "/binds":
            for k, v in body.items():
                if k in BINDS:
                    BINDS[k] = v
            self._json({"ok": True, "binds": BINDS})

        elif p == "/config":
            for k, v in body.items():
                if k in CFG and k != "binds":
                    CFG[k] = v
            self._json({"ok": True})

        elif p == "/focus":
            try:
                import subprocess
                subprocess.run(["powershell", "-WindowStyle", "Hidden", "-c",
                    "$p = Get-Process -Name FortniteClient-Win64-Shipping -EA SilentlyContinue | Select -First 1; "
                    "if($p){Add-Type '[DllImport(\"user32.dll\")]public static extern bool SetForegroundWindow(IntPtr h);' "
                    "-Name W -Namespace W -PassThru|Out-Null;[W.W]::SetForegroundWindow($p.MainWindowHandle)}"],
                    capture_output=True, timeout=5)
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})

        elif p == "/release_all":
            for k in ["w", "a", "s", "d", "space", "leftshift", "leftctrl",
                       "e", "q", "r", "z", "x", "c", "v", "g"]:
                try:
                    pyautogui.keyUp(k, _pause=False)
                except:
                    pass
            mouse_up("left")
            mouse_up("right")
            self._json({"ok": True})

        else:
            self._error(404, "not found")


# ─── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = CFG["port"]
    server = ThreadedHTTPServer(("0.0.0.0", port), AgentHandler)

    log.info("=" * 50)
    log.info(f"  AimBrain — Fortnite Vision Agent v3")
    log.info(f"  Port: {port}")
    log.info(f"  Screenshot: JPEG q={CFG['screenshot_quality']} "
             f"scale={CFG['screenshot_scale']}")
    log.info(f"  Macros: {len(MACROS)} available")
    log.info(f"  Win32 fast input: {'YES' if HAVE_WIN32 else 'NO'}")
    log.info("=" * 50)
    log.info(f"Endpoints:")
    log.info(f"  GET  /screenshot /screenshot/region /ping /stats /macros /binds")
    log.info(f"  POST /macro /macro_sequence /keys /click /move /key")
    log.info(f"  POST /release_all /focus /config /binds")
    log.info("Ready for commands!")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        server.shutdown()

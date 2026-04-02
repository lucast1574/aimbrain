"""
Utility macros — weapon switching, healing, camera, emergency, disengage.
"""

import time
from aimbrain.input import (
    mouse_move_relative,
    key_tap, key_down, key_up,
)


# ─── Camera ───────────────────────────────────────────────────────────


def look(dx: int, dy: int):
    """Turn the camera by (dx, dy) pixels — instant."""
    mouse_move_relative(dx, dy)


def smooth_look(dx: int, dy: int, steps: int = 5):
    """Smooth camera turn over multiple frames (less jarring)."""
    sdx, sdy = dx / steps, dy / steps
    for _ in range(steps):
        mouse_move_relative(sdx, sdy)
        time.sleep(0.01)


# ─── Weapons / Inventory ─────────────────────────────────────────────


def switch_weapon(slot: int):
    """Switch to weapon slot 1-5."""
    slot = max(1, min(5, int(slot)))
    key_tap(f"slot{slot}")


def pickaxe():
    """Switch to pickaxe."""
    key_tap("pickaxe")


def reload():
    """Reload current weapon."""
    key_tap("reload")


# ─── Healing ──────────────────────────────────────────────────────────


def heal():
    """Use healing item (press interact/use)."""
    key_tap("interact")


# ─── Emergency / Tactical ────────────────────────────────────────────


def emergency():
    """Panic button: jump → build 1x1 box → switch to shotgun."""
    from aimbrain.macros.building import build_cover
    key_tap("jump")
    time.sleep(0.05)
    build_cover()
    time.sleep(0.1)
    switch_weapon(1)


def disengage():
    """Break off a fight: wall behind → 180° turn → sprint away."""
    from aimbrain.macros.building import build
    build("wall", 1)
    time.sleep(0.05)
    mouse_move_relative(1600, 0)  # ~180° turn
    time.sleep(0.05)
    key_down("sprint")
    key_down("forward")
    time.sleep(1.5)
    key_up("forward")
    key_up("sprint")


# ─── Registry ────────────────────────────────────────────────────────

MACROS = {
    "look":          lambda p: look(p.get("dx", 0), p.get("dy", 0)),
    "smooth_look":   lambda p: smooth_look(p.get("dx", 0), p.get("dy", 0), p.get("steps", 5)),
    "switch_weapon": lambda p: switch_weapon(p.get("slot", 1)),
    "pickaxe":       lambda p: pickaxe(),
    "reload":        lambda p: reload(),
    "heal":          lambda p: heal(),
    "emergency":     lambda p: emergency(),
    "disengage":     lambda p: disengage(),
}

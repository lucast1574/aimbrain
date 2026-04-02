"""
Looting macros — picking up items, opening chests, harvesting resources.
"""

import time
from aimbrain.input import (
    mouse_click, mouse_move_relative,
    key_tap, key_down, key_up,
)


def pickup():
    """Walk forward briefly and spam interact to grab nearby loot."""
    key_down("forward")
    for _ in range(5):
        key_tap("interact")
        time.sleep(0.1)
    key_up("forward")


def loot_area(duration_ms: int = 3000):
    """Spin around spamming interact to grab all nearby loot."""
    end = time.time() + duration_ms / 1000.0
    key_down("forward")
    while time.time() < end:
        key_tap("interact")
        mouse_move_relative(120, 0)
        time.sleep(0.08)
    key_up("forward")


def loot_sweep(duration_ms: int = 4000):
    """Sprint in a circle looting everything — wider area coverage."""
    end = time.time() + duration_ms / 1000.0
    key_down("forward")
    key_down("sprint")
    while time.time() < end:
        key_tap("interact")
        mouse_move_relative(40, 0)
        time.sleep(0.06)
    key_up("sprint")
    key_up("forward")


def open_chest():
    """Walk toward a chest, hold interact to open, then grab items."""
    key_down("forward")
    key_down("interact")
    time.sleep(1.2)
    key_up("interact")
    key_up("forward")
    # Grab dropped items
    time.sleep(0.3)
    for _ in range(6):
        key_tap("interact")
        time.sleep(0.12)


def harvest(swings: int = 5, move: bool = True):
    """Switch to pickaxe and swing at nearby resources."""
    from aimbrain.macros.utility import pickaxe
    pickaxe()
    time.sleep(0.1)
    if move:
        key_down("forward")
    for _ in range(swings):
        mouse_click("left")
        time.sleep(0.7)
    if move:
        key_up("forward")


# ─── Registry ────────────────────────────────────────────────────────

MACROS = {
    "pickup":     lambda p: pickup(),
    "loot_area":  lambda p: loot_area(p.get("duration", 3000)),
    "loot_sweep": lambda p: loot_sweep(p.get("duration", 4000)),
    "open_chest": lambda p: open_chest(),
    "harvest":    lambda p: harvest(p.get("swings", 5), p.get("move", True)),
}

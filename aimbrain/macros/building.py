"""
Building macros — walls, ramps, boxes, 90s, edits.
"""

import time
from aimbrain.input import (
    mouse_click, mouse_move_relative, mouse_down, mouse_up,
    key_tap, key_down, key_up,
)


# ─── Basic building ──────────────────────────────────────────────────


def build(piece: str = "wall", count: int = 1):
    """Enter build mode and place a structure piece."""
    key_tap("build_mode")
    time.sleep(0.05)
    for _ in range(count):
        key_tap(f"build_{piece}")
        time.sleep(0.03)
        mouse_click("left")
        time.sleep(0.08)


def build_cover():
    """Quick 1x1 box — 4 walls around you."""
    key_tap("build_mode")
    time.sleep(0.05)
    for _ in range(4):
        key_tap("build_wall")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.04)
        mouse_move_relative(400, 0)  # ~90° turn
        time.sleep(0.04)


def build_cover_ramp():
    """1x1 box + ramp inside for high-ground peek."""
    build_cover()
    time.sleep(0.05)
    key_tap("build_stair")
    time.sleep(0.02)
    mouse_click("left")


# ─── Ramp pushes ─────────────────────────────────────────────────────


def ramp_rush(count: int = 3):
    """Sprint forward placing ramps — basic aggressive push."""
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


def protected_ramp(count: int = 3):
    """Floor underneath + ramp — harder to shoot out."""
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


def wall_ramp(count: int = 3):
    """Wall in front + ramp — classic push with frontal cover."""
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


def do_90s(count: int = 2):
    """90-degree turns for rapid height gain — competitive technique."""
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
        mouse_move_relative(450, 0)  # 90° turn
        time.sleep(0.15)
        key_tap("build_wall")
        time.sleep(0.02)
        mouse_click("left")
        time.sleep(0.2)


# ─── Editing ──────────────────────────────────────────────────────────


def edit_reset():
    """Quick edit reset — open edit, right-click reset, confirm."""
    key_tap("edit")
    time.sleep(0.05)
    mouse_click("right")
    time.sleep(0.05)
    key_tap("edit")


def edit_wall(pattern: str = "door"):
    """
    Edit a wall into a pattern and confirm.
    Patterns: door, window, half
    """
    key_tap("edit")
    time.sleep(0.08)
    if pattern == "door":
        mouse_down("left")
        time.sleep(0.03)
        mouse_move_relative(0, 100)
        time.sleep(0.03)
        mouse_up("left")
    elif pattern == "window":
        mouse_click("left")
    elif pattern == "half":
        mouse_down("left")
        mouse_move_relative(200, 0)
        time.sleep(0.03)
        mouse_move_relative(200, 0)
        time.sleep(0.03)
        mouse_up("left")
    time.sleep(0.05)
    key_tap("edit")


# ─── Registry ────────────────────────────────────────────────────────

MACROS = {
    "build":            lambda p: build(p.get("piece", "wall"), p.get("count", 1)),
    "build_cover":      lambda p: build_cover(),
    "build_cover_ramp": lambda p: build_cover_ramp(),
    "ramp_rush":        lambda p: ramp_rush(p.get("count", 3)),
    "protected_ramp":   lambda p: protected_ramp(p.get("count", 3)),
    "wall_ramp":        lambda p: wall_ramp(p.get("count", 3)),
    "90s":              lambda p: do_90s(p.get("count", 2)),
    "edit_reset":       lambda p: edit_reset(),
    "edit_wall":        lambda p: edit_wall(p.get("pattern", "door")),
}

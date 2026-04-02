"""
Movement macros — patterns, exploration, evasion, dropping.
"""

import time
import random
from aimbrain.input import (
    mouse_move_relative,
    key_tap, key_down, key_up,
)


# ─── Movement patterns ───────────────────────────────────────────────


def move_pattern(pattern: str = "sprint_forward", duration_ms: int = 2000):
    """
    Move in a named pattern for a duration.

    Patterns:
        zigzag         — Forward with alternating left/right strafes
        circle         — Forward while turning in a circle
        strafe_random  — Random direction changes
        sprint_forward — Straight-line sprint
        sprint_jump    — Sprint + periodic jumps (obstacle clearing)
        explore        — Sprint with random looks, jumps, strafes, and pickups
        evasive        — Unpredictable combat movement (crouch/jump/strafe)
    """
    handler = _PATTERNS.get(pattern, _sprint_forward)
    handler(duration_ms)


def _zigzag(duration_ms: int):
    end = time.time() + duration_ms / 1000.0
    key_down("forward")
    toggle = True
    while time.time() < end:
        side = "left" if toggle else "right"
        key_down(side)
        time.sleep(0.3)
        key_up(side)
        toggle = not toggle
    key_up("forward")


def _circle(duration_ms: int):
    end = time.time() + duration_ms / 1000.0
    key_down("forward")
    while time.time() < end:
        mouse_move_relative(60, 0)
        time.sleep(0.05)
    key_up("forward")


def _strafe_random(duration_ms: int):
    dirs = ["left", "right", "forward", "back"]
    end = time.time() + duration_ms / 1000.0
    while time.time() < end:
        d = random.choice(dirs)
        key_down(d)
        time.sleep(random.uniform(0.15, 0.4))
        key_up(d)


def _sprint_forward(duration_ms: int):
    key_down("sprint")
    key_down("forward")
    time.sleep(duration_ms / 1000.0)
    key_up("forward")
    key_up("sprint")


def _sprint_jump(duration_ms: int):
    end = time.time() + duration_ms / 1000.0
    key_down("sprint")
    key_down("forward")
    while time.time() < end:
        key_tap("jump")
        time.sleep(random.uniform(0.5, 0.8))
    key_up("forward")
    key_up("sprint")


def _explore(duration_ms: int):
    end = time.time() + duration_ms / 1000.0
    key_down("sprint")
    key_down("forward")
    while time.time() < end:
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


def _evasive(duration_ms: int):
    """Unpredictable crouch-jump-strafe for combat situations."""
    end = time.time() + duration_ms / 1000.0
    while time.time() < end:
        act = random.choice(["jump_left", "jump_right", "crouch", "sprint_fwd"])
        if act == "jump_left":
            key_down("left")
            key_tap("jump")
            time.sleep(0.3)
            key_up("left")
        elif act == "jump_right":
            key_down("right")
            key_tap("jump")
            time.sleep(0.3)
            key_up("right")
        elif act == "crouch":
            key_down("crouch")
            time.sleep(0.2)
            key_up("crouch")
        else:
            key_down("sprint")
            key_down("forward")
            time.sleep(0.3)
            key_up("forward")
            key_up("sprint")


_PATTERNS = {
    "zigzag": _zigzag,
    "circle": _circle,
    "strafe_random": _strafe_random,
    "sprint_forward": _sprint_forward,
    "sprint_jump": _sprint_jump,
    "explore": _explore,
    "evasive": _evasive,
}


# ─── Special movement ────────────────────────────────────────────────


def drop_in(duration_ms: int = 5000):
    """Skydiving: hold forward + look down to dive fast."""
    key_down("forward")
    mouse_move_relative(0, 300)
    time.sleep(duration_ms / 1000.0)
    key_up("forward")


# ─── Registry ────────────────────────────────────────────────────────

MACROS = {
    "move":    lambda p: move_pattern(p.get("pattern", "sprint_forward"), p.get("duration", 2000)),
    "drop_in": lambda p: drop_in(p.get("duration", 5000)),
}

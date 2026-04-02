"""
Combat macros — shooting, aiming, peeking, and weapon-swap combos.
"""

import time
from aimbrain.input import (
    mouse_down, mouse_up, mouse_click, mouse_move_relative,
    key_tap, key_down, key_up,
)


# ─── Basic shooting ──────────────────────────────────────────────────


def shoot(duration_ms: int = 200):
    """Hold left click to fire for a duration."""
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")


def aim_shoot(duration_ms: int = 300):
    """ADS (right click hold) then fire."""
    mouse_down("right")
    time.sleep(0.05)
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")
    mouse_up("right")


def tap_shoot(count: int = 3, interval_ms: int = 100):
    """Tap-fire for accuracy — single clicks with pauses."""
    for i in range(count):
        mouse_down("left")
        time.sleep(0.03)
        mouse_up("left")
        if i < count - 1:
            time.sleep(interval_ms / 1000.0)


def spray(duration_ms: int = 1000):
    """Full-auto spray — hold fire."""
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")


def burst_spray(bursts: int = 3, burst_ms: int = 300, pause_ms: int = 150):
    """Controlled bursts with recoil-reset pauses between them."""
    for i in range(bursts):
        mouse_down("left")
        time.sleep(burst_ms / 1000.0)
        mouse_up("left")
        if i < bursts - 1:
            time.sleep(pause_ms / 1000.0)


# ─── Advanced combat ─────────────────────────────────────────────────


def jump_shot():
    """Jump and fire mid-air."""
    key_down("jump")
    time.sleep(0.1)
    mouse_down("left")
    time.sleep(0.2)
    mouse_up("left")
    key_up("jump")


def strafe_shoot(direction: str = "left", duration_ms: int = 500):
    """Move sideways while shooting."""
    key_down(direction)
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")
    key_up(direction)


def ads_strafe(direction: str = "left", duration_ms: int = 600):
    """ADS + strafe + fire — precision while mobile."""
    mouse_down("right")
    key_down(direction)
    time.sleep(0.05)
    mouse_down("left")
    time.sleep(duration_ms / 1000.0)
    mouse_up("left")
    key_up(direction)
    mouse_up("right")


def shotgun_flick(dx: int, dy: int, slot: int = 1):
    """Switch to shotgun, flick-aim, fire."""
    from aimbrain.macros.utility import switch_weapon
    switch_weapon(slot)
    time.sleep(0.08)
    mouse_move_relative(dx, dy)
    time.sleep(0.02)
    mouse_click("left")


def double_pump(slot_a: int = 1, slot_b: int = 2):
    """Fire slot A → quick-swap → fire slot B."""
    from aimbrain.macros.utility import switch_weapon
    switch_weapon(slot_a)
    time.sleep(0.08)
    mouse_click("left")
    time.sleep(0.15)
    switch_weapon(slot_b)
    time.sleep(0.08)
    mouse_click("left")


def quick_scope(slot: int = 2, aim_ms: int = 150):
    """Sniper quick-scope: swap → ADS → fire → un-ADS."""
    from aimbrain.macros.utility import switch_weapon
    switch_weapon(slot)
    time.sleep(0.1)
    mouse_down("right")
    time.sleep(aim_ms / 1000.0)
    mouse_click("left")
    time.sleep(0.05)
    mouse_up("right")


def swap_shoot(slot: int = 1, duration_ms: int = 300):
    """Quick-swap to weapon and fire."""
    from aimbrain.macros.utility import switch_weapon
    switch_weapon(slot)
    time.sleep(0.1)
    shoot(duration_ms)


# ─── Peeking ─────────────────────────────────────────────────────────


def crouch_peek():
    """Crouch → uncrouch → tap-fire → re-crouch."""
    key_down("crouch")
    time.sleep(0.3)
    key_up("crouch")
    time.sleep(0.1)
    tap_shoot(2, 80)
    key_down("crouch")
    time.sleep(0.2)
    key_up("crouch")


def peek_right():
    """Right-hand peek: strafe right → shoot → strafe back."""
    key_down("right")
    time.sleep(0.15)
    tap_shoot(2, 80)
    key_up("right")
    key_down("left")
    time.sleep(0.15)
    key_up("left")


def peek_left():
    """Left-hand peek: strafe left → shoot → strafe back."""
    key_down("left")
    time.sleep(0.15)
    tap_shoot(2, 80)
    key_up("left")
    key_down("right")
    time.sleep(0.15)
    key_up("right")


# ─── Registry ────────────────────────────────────────────────────────

MACROS = {
    "shoot":         lambda p: shoot(p.get("duration", 200)),
    "aim_shoot":     lambda p: aim_shoot(p.get("duration", 300)),
    "tap_shoot":     lambda p: tap_shoot(p.get("count", 3), p.get("interval", 100)),
    "spray":         lambda p: spray(p.get("duration", 1000)),
    "burst_spray":   lambda p: burst_spray(p.get("bursts", 3), p.get("burst_ms", 300), p.get("pause_ms", 150)),
    "jump_shot":     lambda p: jump_shot(),
    "strafe_shoot":  lambda p: strafe_shoot(p.get("direction", "left"), p.get("duration", 500)),
    "ads_strafe":    lambda p: ads_strafe(p.get("direction", "left"), p.get("duration", 600)),
    "shotgun_flick": lambda p: shotgun_flick(p.get("dx", 0), p.get("dy", 0), p.get("slot", 1)),
    "double_pump":   lambda p: double_pump(p.get("slot_a", 1), p.get("slot_b", 2)),
    "quick_scope":   lambda p: quick_scope(p.get("slot", 2), p.get("aim_ms", 150)),
    "swap_shoot":    lambda p: swap_shoot(p.get("slot", 1), p.get("duration", 300)),
    "crouch_peek":   lambda p: crouch_peek(),
    "peek_right":    lambda p: peek_right(),
    "peek_left":     lambda p: peek_left(),
}

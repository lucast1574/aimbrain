"""
Fortnite AI Game Loop — plays the game using vision + macros.

Architecture:
- Movement thread: ALWAYS keeps the character moving (sprint, zigzag, jump)
- Vision thread: grabs frames, compresses, analyzes
- Brain: decides actions based on vision + OCR

The character NEVER stops moving. Movement patterns change based on game state.
"""

import io
import time
import json
import random
import logging
import threading
from enum import Enum

from aimbrain import config as _config
from aimbrain import donclaw
from aimbrain import input as inp

log = logging.getLogger("aimbrain.gameloop")


class GameState(Enum):
    LOBBY = "lobby"
    LOADING = "loading"
    BUS = "bus"
    SKYDIVING = "skydiving"
    GLIDING = "gliding"
    LANDED = "landed"
    LOOTING = "looting"
    EXPLORING = "exploring"
    FIGHTING = "fighting"
    DEAD = "dead"
    UNKNOWN = "unknown"


class MovementController:
    """
    Keeps the character ALWAYS moving. Never stops.
    Runs in its own thread, changing patterns based on game state.
    """

    def __init__(self):
        self._running = False
        self._thread = None
        self._state = GameState.LOBBY
        self._lock = threading.Lock()

    @property
    def state(self) -> GameState:
        with self._lock:
            return self._state

    @state.setter
    def state(self, value: GameState):
        with self._lock:
            old = self._state
            self._state = value
            if old != value:
                log.info(f"State: {old.value} → {value.value}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("Movement controller started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        # Release all keys
        try:
            donclaw.release_all()
        except Exception:
            pass
        log.info("Movement controller stopped")

    def _loop(self):
        while self._running:
            try:
                state = self.state
                if state == GameState.LOBBY:
                    time.sleep(1)
                elif state == GameState.BUS:
                    self._bus_movement()
                elif state == GameState.SKYDIVING:
                    self._skydive_movement()
                elif state == GameState.GLIDING:
                    self._glide_movement()
                elif state in (GameState.LANDED, GameState.LOOTING, GameState.EXPLORING):
                    self._ground_movement()
                elif state == GameState.FIGHTING:
                    self._combat_movement()
                elif state == GameState.DEAD:
                    time.sleep(1)
                else:
                    time.sleep(0.5)
            except Exception as e:
                log.warning(f"Movement error: {e}")
                time.sleep(0.5)

    def _bus_movement(self):
        """On the bus — wait, then jump."""
        time.sleep(2)
        # Jump from bus
        donclaw.key_press("space")
        log.info("Jumped from bus!")
        self.state = GameState.SKYDIVING

    def _skydive_movement(self):
        """Skydiving — hold W to dive forward and down."""
        donclaw.key_down("w")
        time.sleep(0.5)
        # Check if we should deploy glider
        # (will be updated by vision thread)
        while self.state == GameState.SKYDIVING and self._running:
            time.sleep(0.3)
        donclaw.key_up("w")

    def _glide_movement(self):
        """Gliding — hold W toward landing spot."""
        donclaw.key_down("w")
        while self.state == GameState.GLIDING and self._running:
            time.sleep(0.3)
        donclaw.key_up("w")

    def _ground_movement(self):
        """
        Ground movement — ALWAYS moving.
        Sprint forward with random strafes, jumps, and interact spam.
        This is the core of staying alive in Fortnite.
        """
        # Start sprinting
        donclaw.key_down("lshift")
        donclaw.key_down("w")

        while self.state in (GameState.LANDED, GameState.LOOTING, GameState.EXPLORING) and self._running:
            action = random.choices(
                ["straight", "strafe_left", "strafe_right", "jump", "interact", "look"],
                weights=[30, 15, 15, 15, 15, 10],
                k=1,
            )[0]

            if action == "straight":
                time.sleep(random.uniform(0.3, 0.8))

            elif action == "strafe_left":
                donclaw.key_down("a")
                time.sleep(random.uniform(0.2, 0.5))
                donclaw.key_up("a")

            elif action == "strafe_right":
                donclaw.key_down("d")
                time.sleep(random.uniform(0.2, 0.5))
                donclaw.key_up("d")

            elif action == "jump":
                donclaw.key_press("space")
                time.sleep(0.3)

            elif action == "interact":
                # Spam E to pick up loot
                for _ in range(3):
                    donclaw.key_press("e")
                    time.sleep(0.1)

            elif action == "look":
                # Random camera turn
                try:
                    donclaw.mouse_move(
                        random.randint(-150, 150),
                        random.randint(-30, 30),
                    )
                except Exception:
                    pass
                time.sleep(0.1)

        # Release movement keys
        donclaw.key_up("w")
        donclaw.key_up("lshift")

    def _combat_movement(self):
        """
        Combat movement — erratic, hard to hit.
        Jump, crouch, strafe unpredictably while shooting.
        """
        while self.state == GameState.FIGHTING and self._running:
            action = random.choice([
                "jump_left", "jump_right", "crouch",
                "strafe_left", "strafe_right", "jump_forward",
            ])

            if action == "jump_left":
                donclaw.key_down("a")
                donclaw.key_press("space")
                time.sleep(0.3)
                donclaw.key_up("a")

            elif action == "jump_right":
                donclaw.key_down("d")
                donclaw.key_press("space")
                time.sleep(0.3)
                donclaw.key_up("d")

            elif action == "crouch":
                donclaw.key_down("leftctrl")
                time.sleep(random.uniform(0.15, 0.3))
                donclaw.key_up("leftctrl")

            elif action == "strafe_left":
                donclaw.key_down("a")
                time.sleep(random.uniform(0.2, 0.4))
                donclaw.key_up("a")

            elif action == "strafe_right":
                donclaw.key_down("d")
                time.sleep(random.uniform(0.2, 0.4))
                donclaw.key_up("d")

            elif action == "jump_forward":
                donclaw.key_down("w")
                donclaw.key_press("space")
                time.sleep(0.3)
                donclaw.key_up("w")


class VisionAnalyzer:
    """
    Grabs frames and determines game state via OCR + screenshot analysis.
    """

    @staticmethod
    def grab_frame(width: int = 480, quality: int = 15) -> bytes | None:
        """Grab and compress a frame. ~650ms total."""
        return donclaw.screenshot_optimized(width=width, quality=quality)

    @staticmethod
    def read_hud() -> dict:
        """Fast OCR read of the HUD text."""
        try:
            return donclaw.ocr()
        except Exception:
            return {"ok": False}

    @staticmethod
    def detect_state_from_ocr(ocr_data: dict) -> GameState:
        """Determine game state from OCR text."""
        if not ocr_data.get("ok"):
            return GameState.UNKNOWN

        texts = " ".join(l.get("text", "") for l in ocr_data.get("lines", []))
        text_upper = texts.upper()

        if "ELIMINATED" in text_upper and "YOU PLACED" in text_upper:
            return GameState.DEAD
        if "FINDING SERVER" in text_upper or "CANCEL" in text_upper:
            return GameState.LOADING
        if "BATTLE BUS" in text_upper or "LAUNCHING" in text_upper:
            return GameState.BUS
        if "SKYDIVE" in text_upper:
            return GameState.GLIDING  # Can press space to dive
        if "DEPLOY" in text_upper and "GLIDE" in text_upper:
            return GameState.SKYDIVING  # Can deploy glider
        if "PLAY" in text_upper and ("FORTNITE" in text_upper or "SOLO" in text_upper):
            return GameState.LOBBY
        if "PICKAXE" in text_upper or "STORM" in text_upper:
            return GameState.EXPLORING
        if any(w in text_upper for w in ["RIFLE", "SMG", "SHOTGUN", "PISTOL", "SNIPER"]):
            return GameState.EXPLORING  # Has weapon

        return GameState.UNKNOWN

    @staticmethod
    def has_weapon(ocr_data: dict) -> bool:
        """Check if we have any weapon equipped (not pickaxe)."""
        texts = " ".join(l.get("text", "") for l in ocr_data.get("lines", []))
        text_upper = texts.upper()
        weapons = ["RIFLE", "SMG", "SHOTGUN", "PISTOL", "SNIPER", "LAUNCHER", "BOW"]
        return any(w in text_upper for w in weapons)


class FortniteAI:
    """
    Main game loop — coordinates movement, vision, and decisions.
    """

    def __init__(self):
        self.movement = MovementController()
        self.vision = VisionAnalyzer()
        self._running = False

    def start_match(self):
        """Click PLAY and manage the full match lifecycle."""
        log.info("=== STARTING MATCH ===")
        self._running = True
        self.movement.start()

        try:
            self._click_play()
            self._wait_for_match()
            self._play_match()
        except Exception as e:
            log.error(f"Match error: {e}")
        finally:
            self.movement.stop()
            self._running = False
            log.info("=== MATCH ENDED ===")

    def stop(self):
        self._running = False
        self.movement.stop()

    def _click_play(self):
        """Find and click the PLAY button."""
        log.info("Clicking PLAY...")
        try:
            donclaw.act("PLAY")
        except Exception:
            # Fallback: click known position
            donclaw.click(x=249, y=872)
        self.movement.state = GameState.LOADING

    def _wait_for_match(self):
        """Wait through matchmaking → bus."""
        log.info("Waiting for match...")
        while self._running:
            time.sleep(3)
            ocr = self.vision.read_hud()
            state = self.vision.detect_state_from_ocr(ocr)

            if state == GameState.BUS:
                log.info("On the Battle Bus!")
                self.movement.state = GameState.BUS
                return
            elif state == GameState.LOBBY:
                # Still in lobby, might need to click play again
                time.sleep(2)
            elif state in (GameState.SKYDIVING, GameState.GLIDING):
                # Already past the bus
                self.movement.state = state
                return

            self.movement.state = state

    def _play_match(self):
        """Main game loop — vision + movement + decisions."""
        log.info("Playing match!")
        last_frame_time = 0
        frame_interval = 2.0  # Analyze every 2 seconds
        loot_timer = 0

        while self._running:
            now = time.time()

            # Read HUD frequently (fast, ~200ms)
            ocr = self.vision.read_hud()
            state = self.vision.detect_state_from_ocr(ocr)

            # Handle state transitions
            if state == GameState.DEAD:
                log.info("We died!")
                self.movement.state = GameState.DEAD
                time.sleep(3)
                # Press space to return to lobby
                donclaw.key_press("space")
                time.sleep(2)
                donclaw.key_press("space")
                return

            if state == GameState.GLIDING:
                # Deploy glider → dive down
                self.movement.state = GameState.GLIDING
                time.sleep(2)
                donclaw.key_press("space")  # Skydive
                self.movement.state = GameState.SKYDIVING
                time.sleep(8)
                # Should auto-deploy near ground
                self.movement.state = GameState.LANDED
                time.sleep(3)
                self.movement.state = GameState.EXPLORING
                continue

            if state == GameState.SKYDIVING:
                self.movement.state = GameState.SKYDIVING
                time.sleep(5)
                self.movement.state = GameState.LANDED
                time.sleep(3)
                self.movement.state = GameState.EXPLORING
                continue

            if state in (GameState.EXPLORING, GameState.UNKNOWN):
                self.movement.state = GameState.EXPLORING

                # Switch weapons periodically to check what we have
                if now - loot_timer > 10:
                    for slot in ["2", "3", "4", "5"]:
                        donclaw.key_press(slot)
                        time.sleep(0.2)
                    donclaw.key_press("1")  # Back to pickaxe/slot1
                    loot_timer = now

            if state == GameState.BUS:
                self.movement.state = GameState.BUS
                time.sleep(1)
                continue

            # Sleep before next OCR check
            time.sleep(1.0)


def play_match():
    """Convenience function to play one match."""
    ai = FortniteAI()
    ai.start_match()
    return ai

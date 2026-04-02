"""
Configuration management — loads from config.json, provides runtime updates.
"""

import json
import logging
from pathlib import Path

log = logging.getLogger("aimbrain.config")

DEFAULT_CONFIG = {
    "port": 9777,
    "monitor": 0,
    "screenshot_quality": 45,
    "screenshot_scale": 0.5,
    "screenshot_cache_ms": 50,
    "log_requests": False,
}

DEFAULT_BINDS = {
    "forward": "w", "back": "s", "left": "a", "right": "d",
    "jump": "space", "crouch": "leftctrl", "sprint": "leftshift",
    "reload": "r", "interact": "e", "inventory": "tab", "map": "m",
    "pickaxe": "1", "slot1": "2", "slot2": "3", "slot3": "4",
    "slot4": "5", "slot5": "6",
    "build_wall": "z", "build_floor": "x", "build_stair": "c",
    "build_roof": "v", "build_mode": "q", "edit": "g",
    "trap": "t", "use": "e", "emote": "b",
}


class Config:
    """Singleton-style config holder. Mutable at runtime."""

    def __init__(self, config_path: Path | str | None = None):
        self._settings: dict = DEFAULT_CONFIG.copy()
        self.binds: dict = DEFAULT_BINDS.copy()

        if config_path:
            self._load_file(Path(config_path))

    def _load_file(self, path: Path):
        if not path.exists():
            log.info(f"No config file at {path}, using defaults")
            return
        try:
            with open(path) as f:
                user = json.load(f)
            if "binds" in user:
                self.binds.update(user.pop("binds"))
            self._settings.update(user)
            log.info(f"Loaded config from {path}")
        except Exception as e:
            log.warning(f"Config load failed: {e}, using defaults")

    # ── Accessors ─────────────────────────────────────────────────────

    @property
    def port(self) -> int:
        return self._settings["port"]

    @property
    def monitor(self) -> int:
        return self._settings["monitor"]

    @property
    def screenshot_quality(self) -> int:
        return self._settings["screenshot_quality"]

    @property
    def screenshot_scale(self) -> float:
        return self._settings["screenshot_scale"]

    @property
    def screenshot_cache_ms(self) -> float:
        return self._settings["screenshot_cache_ms"]

    @property
    def log_requests(self) -> bool:
        return self._settings["log_requests"]

    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    # ── Runtime updates ───────────────────────────────────────────────

    def update_settings(self, patch: dict):
        """Update non-bind settings at runtime."""
        for k, v in patch.items():
            if k != "binds" and k in self._settings:
                self._settings[k] = v

    def update_binds(self, patch: dict):
        """Update key bindings at runtime."""
        for k, v in patch.items():
            if k in self.binds:
                self.binds[k] = v

    def to_dict(self) -> dict:
        """Return settings (without binds) for API response."""
        return self._settings.copy()


# ── Module-level singleton ────────────────────────────────────────────
# Initialized by server.main(); imported everywhere else.

_cfg: Config | None = None


def init(config_path: Path | str | None = None) -> Config:
    """Initialize the global config. Call once at startup."""
    global _cfg
    _cfg = Config(config_path)
    return _cfg


def get() -> Config:
    """Get the global config. Raises if not initialized."""
    if _cfg is None:
        raise RuntimeError("Config not initialized — call config.init() first")
    return _cfg

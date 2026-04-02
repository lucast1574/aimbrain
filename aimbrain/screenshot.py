"""
Screenshot engine — fast JPEG capture with caching and region support.
"""

import io
import time
import base64
import threading

import mss
from PIL import Image

from aimbrain import config as _config

# ─── Thread-safe cache ───────────────────────────────────────────────

_lock = threading.Lock()
_cache = {"data": None, "ts": 0.0}


def _grab_raw(monitor_idx: int = 0, region: dict | None = None) -> Image.Image:
    """Grab screen as a PIL Image."""
    with mss.mss() as sct:
        monitors = sct.monitors
        if region:
            grab_area = {
                "left": region["x"], "top": region["y"],
                "width": region["w"], "height": region["h"],
            }
            shot = sct.grab(grab_area)
        else:
            if monitor_idx >= len(monitors):
                monitor_idx = 0
            shot = sct.grab(monitors[monitor_idx])
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def _encode_jpeg(img: Image.Image, quality: int) -> bytes:
    """Encode a PIL Image to JPEG bytes."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=False)
    return buf.getvalue()


# ─── Public API ───────────────────────────────────────────────────────


def capture(
    monitor: int | None = None,
    quality: int | None = None,
    scale: float | None = None,
    region: dict | None = None,
) -> bytes:
    """
    Capture the screen as compressed JPEG bytes.

    Args:
        monitor: Monitor index (0 = all). Defaults to config value.
        quality: JPEG quality 1-100. Defaults to config value.
        scale:   Downscale factor (0.5 = half res). Defaults to config value.
        region:  Optional {"x", "y", "w", "h"} for partial capture.

    Returns:
        JPEG bytes.
    """
    cfg = _config.get()
    monitor = monitor if monitor is not None else cfg.monitor
    quality = quality if quality is not None else cfg.screenshot_quality
    scale = scale if scale is not None else cfg.screenshot_scale
    cache_ttl = cfg.screenshot_cache_ms / 1000.0

    # Check cache (only for full-screen, non-region grabs)
    if not region:
        now = time.time()
        with _lock:
            if _cache["data"] and (now - _cache["ts"]) < cache_ttl:
                return _cache["data"]

    # Grab
    img = _grab_raw(monitor, region)

    # Scale (skip for region captures)
    if not region and scale and scale != 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.NEAREST)

    data = _encode_jpeg(img, quality)

    # Update cache
    if not region:
        with _lock:
            _cache["data"] = data
            _cache["ts"] = time.time()

    return data


def capture_b64(quality: int = 60, scale: float = 0.5) -> str:
    """Capture screenshot and return as base64 string (for LLM APIs)."""
    return base64.b64encode(capture(quality=quality, scale=scale)).decode()


def capture_region(x: int, y: int, w: int, h: int, quality: int = 70) -> bytes:
    """Capture a specific screen region as JPEG bytes."""
    return capture(region={"x": x, "y": y, "w": w, "h": h}, quality=quality, scale=1.0)


def capture_region_b64(x: int, y: int, w: int, h: int, quality: int = 70) -> str:
    """Capture a region and return as base64."""
    return base64.b64encode(capture_region(x, y, w, h, quality)).decode()

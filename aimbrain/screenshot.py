"""
Screenshot engine — fast JPEG capture with caching and region support.

When DonClaw is enabled, provides OCR text instead of screenshots.
KEY RULE: No images sent to AI — use OCR text only in DonClaw mode.
"""

import io
import json
import time
import base64
import logging
import threading

from aimbrain import config as _config

# mss/PIL are optional — only needed in local mode (Windows).
try:
    import mss
    from PIL import Image
    HAS_LOCAL_CAPTURE = True
except ImportError:
    mss = None
    Image = None
    HAS_LOCAL_CAPTURE = False

log = logging.getLogger("aimbrain.screenshot")

# ─── Thread-safe cache ───────────────────────────────────────────────

_lock = threading.Lock()
_cache = {"data": None, "ts": 0.0}

# OCR cache (DonClaw mode)
_ocr_lock = threading.Lock()
_ocr_cache = {"data": None, "ts": 0.0}
_OCR_CACHE_MS = 200  # OCR cache TTL in ms


def _use_donclaw() -> bool:
    try:
        return _config.get().donclaw_enabled
    except RuntimeError:
        return False


def _dc():
    from aimbrain import donclaw
    return donclaw


# ─── Local capture (original mode) ───────────────────────────────────

def _grab_raw(monitor_idx: int = 0, region: dict | None = None):
    """Grab screen as a PIL Image. Requires mss + PIL."""
    if not HAS_LOCAL_CAPTURE:
        raise RuntimeError("Local capture requires mss + Pillow. "
                           "Enable DonClaw mode or install: pip install mss Pillow")
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


def _encode_jpeg(img, quality: int) -> bytes:
    """Encode a PIL Image to JPEG bytes."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=False)
    return buf.getvalue()


# ─── OCR (DonClaw mode) ──────────────────────────────────────────────

def ocr() -> dict:
    """
    Get screen text via DonClaw OCR.
    Cached for _OCR_CACHE_MS to avoid redundant calls.
    """
    now = time.time()
    with _ocr_lock:
        if _ocr_cache["data"] and (now - _ocr_cache["ts"]) < (_OCR_CACHE_MS / 1000.0):
            return _ocr_cache["data"]

    data = _dc().ocr()

    with _ocr_lock:
        _ocr_cache["data"] = data
        _ocr_cache["ts"] = time.time()

    return data


def find_text(text: str) -> dict:
    """Find specific text on screen via DonClaw."""
    return _dc().find(text)


# ─── Public API ───────────────────────────────────────────────────────

def capture(
    monitor: int | None = None,
    quality: int | None = None,
    scale: float | None = None,
    region: dict | None = None,
) -> bytes:
    """
    Capture the screen as compressed JPEG bytes (local mode only).

    In DonClaw mode, this returns OCR text as JSON bytes instead.

    Args:
        monitor: Monitor index (0 = all). Defaults to config value.
        quality: JPEG quality 1-100. Defaults to config value.
        scale:   Downscale factor (0.5 = half res). Defaults to config value.
        region:  Optional {"x", "y", "w", "h"} for partial capture.

    Returns:
        JPEG bytes (local mode) or JSON bytes (DonClaw mode).
    """
    if _use_donclaw():
        # DonClaw mode: return OCR text as JSON
        data = ocr()
        return json.dumps(data, separators=(",", ":")).encode()

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

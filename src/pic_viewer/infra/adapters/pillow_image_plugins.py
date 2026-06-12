"""Optional Pillow image plugin registration for modern image formats."""

from __future__ import annotations

import importlib
import logging
import threading

logger = logging.getLogger(__name__)

_registration_lock = threading.Lock()
_registered = False


def register_optional_pillow_image_plugins() -> None:
    """Register optional Pillow plugins for AVIF and HEIF/HEIC decoding.

    Missing plugins are non-fatal. Image loading still reports the normal
    ImageLoadError when no backend can decode a specific file.
    """

    global _registered
    with _registration_lock:
        if _registered:
            return
        _register_avif_plugin()
        _register_heif_plugin()
        _registered = True


def _register_avif_plugin() -> None:
    try:
        importlib.import_module("pillow_avif")
    except ImportError:
        logger.info("Pillow AVIF plugin is not available")
    except Exception:
        logger.exception("Failed to register Pillow AVIF plugin")


def _register_heif_plugin() -> None:
    try:
        pillow_heif = importlib.import_module("pillow_heif")
        register_heif_opener = getattr(pillow_heif, "register_heif_opener")
        register_heif_opener(thumbnails=False)
    except ImportError:
        logger.info("Pillow HEIF plugin is not available")
    except Exception:
        logger.exception("Failed to register Pillow HEIF plugin")

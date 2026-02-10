"""Runtime language resolution and translator installation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt5 import QtCore

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "zh_CN"
ENGLISH_LANGUAGE = "en"
TRANSLATION_BASENAME = "picviewer"


def normalize_language(raw: Optional[str]) -> Optional[str]:
    """Normalize a language token into one of the supported languages."""

    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None

    lowered = value.replace("-", "_").lower()
    if lowered.startswith("zh"):
        return DEFAULT_LANGUAGE
    if lowered.startswith("en"):
        return ENGLISH_LANGUAGE
    return None


def resolve_language(language_override: Optional[str], system_locale_name: Optional[str] = None) -> str:
    """Resolve active language with override first, then system locale."""

    override = normalize_language(language_override)
    if override is not None:
        return override

    locale_name = system_locale_name if system_locale_name is not None else QtCore.QLocale.system().name()
    system_language = normalize_language(locale_name)
    if system_language is not None:
        return system_language
    return DEFAULT_LANGUAGE


def translation_dir() -> Path:
    """Return the default directory where .qm/.ts resources live."""

    return Path(__file__).resolve().parents[1] / "resources" / "i18n"


def install_translator(
    app: QtCore.QCoreApplication,
    language: str,
    translations_root: Optional[Path] = None,
) -> tuple[str, Optional[QtCore.QTranslator]]:
    """Install translator for the resolved language.

    Returns:
        tuple[str, Optional[QTranslator]]:
            Active language code and installed translator. `None` means source
            language (zh_CN) is used without a translator.
    """

    resolved = normalize_language(language) or DEFAULT_LANGUAGE
    if resolved == DEFAULT_LANGUAGE:
        return DEFAULT_LANGUAGE, None

    root = translations_root if translations_root is not None else translation_dir()
    qm_path = root / f"{TRANSLATION_BASENAME}_{resolved}.qm"
    translator = QtCore.QTranslator(app)
    if not translator.load(str(qm_path)):
        logger.warning("Failed to load translation file: %s, falling back to %s", qm_path, DEFAULT_LANGUAGE)
        return DEFAULT_LANGUAGE, None

    app.installTranslator(translator)
    return resolved, translator

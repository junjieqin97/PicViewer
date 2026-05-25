"""Small Qt signal blocking helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from PySide6 import QtCore


@contextmanager
def block_signals(obj: QtCore.QObject) -> Iterator[None]:
    """Temporarily block signals for Qt objects across PySide6/PyQt APIs."""

    blocker = QtCore.QSignalBlocker(obj)
    try:
        yield
    finally:
        blocker.unblock()

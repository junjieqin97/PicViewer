"""Run with ``python -m tests.visual.run`` from the activated PicViewer env."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from itertools import product
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6 import QtWidgets
    from tests.visual.scene import Scene

ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Case:
    """Stable identifiers for the complete 32-case matrix."""

    width: int
    height: int
    theme: str
    language: str
    loaded: bool
    dpr: int

    @property
    def name(self) -> str:
        state = 'loaded' if self.loaded else 'empty'
        return f'{self.width}x{self.height}-{self.theme}-{self.language}-{state}-{self.dpr}x'


def cases() -> list[Case]:
    """Return every requested layout combination without sampling."""
    return [Case(*size, theme, language, loaded, dpr)
            for size, theme, language, loaded, dpr in product(
                ((900, 600), (1200, 800)), ('light', 'dark'), ('en', 'zh_CN'),
                (False, True), (1, 2))]


def save_diagnostics(
    directory: Path, case: Case, scene: Scene | None,
    current: QtWidgets.QWidget | None, error: str,
) -> None:
    """Save screenshots and environment/geometry evidence for a scene."""
    from PySide6 import QtCore, QtGui, QtWidgets

    directory.mkdir(parents=True, exist_ok=True)
    report = {'case': asdict(case), 'error': error, 'qt': QtCore.qVersion(),
              'platform': sys.platform, 'qpa': QtWidgets.QApplication.platformName(),
              'font': QtWidgets.QApplication.font().toString()}
    if scene is not None:
        for name, widget in (('window', scene.window), ('control', current)):
            if widget is not None and not widget.grab().save(str(directory / f'{name}.png')):
                raise OSError(f'Cannot save {name} screenshot to {directory}')
        report['dpr'] = scene.window.devicePixelRatioF()
        report['current'] = current.objectName() if current is not None else None
        report['widgets'] = [
            {'name': widget.objectName(), 'type': type(widget).__name__,
             'rect': widget.geometry().getRect(), 'visible': widget.isVisible(),
             'font': QtGui.QFontInfo(widget.font()).family()}
            for widget in scene.window.findChildren(QtWidgets.QWidget) if widget.objectName()
        ]
    (directory / 'diagnostics.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8'
    )


def run_child(case: Case, translations: Path, output: Path, capture: bool) -> int:
    """Create Qt only after the parent has set language and DPI environment."""
    from PySide6 import QtCore, QtWidgets
    from pic_viewer.ui.i18n.runtime import install_translator
    from tests.visual.checks import SceneChecks
    from tests.visual.scene import Scene

    app = QtWidgets.QApplication([])
    app.setStyle('Fusion')
    scene = None
    checks = None
    try:
        active, translator = install_translator(app, case.language, translations)
        assert active == case.language, 'Requested translator did not load'
        scene = Scene(case.width, case.height, case.theme, case.loaded)
        checks = SceneChecks(scene)
        assert scene.window.size() == QtCore.QSize(case.width, case.height), 'Window grew beyond target'
        assert scene.window.devicePixelRatioF() == case.dpr, 'Requested DPI is not active'
        image = scene.window.grab().toImage()
        assert image.size() == QtCore.QSize(case.width * case.dpr, case.height * case.dpr)
        checks.layout()
        checks.content(case.loaded, case.language, case.dpr)
        checks.long_fields()
        checks.focus(case.loaded, case.theme)
        if case.loaded:
            checks.canvas(case.theme)
        if capture:
            save_diagnostics(output / case.name, case, scene, checks.current, '')
        return 0
    except Exception:
        error = traceback.format_exc()
        logger.error('%s\n%s', case.name, error)
        save_diagnostics(output / case.name, case, scene,
                         checks.current if checks else None, error)
        return 1
    finally:
        if scene is not None:
            scene.close()


def run_matrix(output: Path, capture: bool, selected: str | None) -> int:
    """Compile real translations once and launch bounded, isolated case workers."""
    from scripts.i18n.build_qm import build_qm, default_translation_dir

    matrix = [case for case in cases() if selected is None or case.name == selected]
    if not matrix:
        raise ValueError(f'Unknown case: {selected}')
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix='picviewer-visual-') as directory:
        translations = Path(directory)
        build_qm(default_translation_dir(), translations)
        for case in matrix:
            env = os.environ.copy()
            for key in ('QT_SCREEN_SCALE_FACTORS', 'QT_AUTO_SCREEN_SCALE_FACTOR',
                        'QT_FONT_DPI', 'QT_SCALE_FACTOR_ROUNDING_POLICY'):
                env.pop(key, None)
            env.update(QT_QPA_PLATFORM='offscreen', QT_SCALE_FACTOR=str(case.dpr),
                       QT_ENABLE_HIGHDPI_SCALING='1', PICVIEWER_LANG=case.language)
            command = [sys.executable, '-m', 'tests.visual.run', '--child', case.name,
                       '--translations', str(translations), '--output', str(output)]
            if capture:
                command.append('--capture')
            try:
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                        text=True, timeout=60, check=False)
                passed = result.returncode == 0
                details = result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                passed, details = False, 'Visual worker exceeded 60 seconds'
            results.append({'case': case.name, 'passed': passed})
            logger.info('%s %s', 'PASS' if passed else 'FAIL', case.name)
            if not passed:
                target = output / case.name
                target.mkdir(parents=True, exist_ok=True)
                (target / 'worker.log').write_text(details, encoding='utf-8')
                logger.error('%s', details)
    (output / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    return int(any(not result['passed'] for result in results))


def main() -> int:
    """Parse runner options; failures always produce a nonzero exit status."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build' / 'visual-regression')
    parser.add_argument('--capture', action='store_true', help='Also save passing scenes')
    parser.add_argument('--case', help='Run one case by its full identifier')
    parser.add_argument('--child', help=argparse.SUPPRESS)
    parser.add_argument('--translations', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error('Visual assertions require Python without -O / PYTHONOPTIMIZE')
    try:
        if args.child:
            case = next(case for case in cases() if case.name == args.child)
            return run_child(case, args.translations, args.output.resolve(), args.capture)
        return run_matrix(args.output.resolve(), args.capture, args.case)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        logger.exception('Unable to run visual regression checks')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

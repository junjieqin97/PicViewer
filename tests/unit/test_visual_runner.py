"""Verify matrix completeness and actionable subprocess failure reporting."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests.visual.run import cases, run_matrix


class VisualRunnerTests(unittest.TestCase):
    def test_matrix_contains_all_32_distinct_combinations(self) -> None:
        matrix = cases()
        self.assertEqual(32, len({case.name for case in matrix}))
        for language in ('en', 'zh_CN'):
            for dpr in (1, 2):
                self.assertEqual(8, sum(case.language == language and case.dpr == dpr
                                        for case in matrix))

    def test_worker_failure_is_reported_and_remaining_cases_continue(self) -> None:
        success = subprocess.CompletedProcess([], 0, '', '')
        failure = subprocess.CompletedProcess([], 1, '', 'Missing focus indicator')
        with tempfile.TemporaryDirectory() as directory, \
                patch('scripts.i18n.build_qm.build_qm'), \
                patch('tests.visual.run.subprocess.run',
                      side_effect=[failure] + [success] * 31) as worker, \
                self.assertLogs('tests.visual.run', level='INFO'):
            output = Path(directory)
            self.assertEqual(1, run_matrix(output, False, None))
            self.assertEqual(32, worker.call_count)
            results = json.loads((output / 'results.json').read_text(encoding='utf-8'))
            self.assertEqual(31, sum(result['passed'] for result in results))
            log = output / cases()[0].name / 'worker.log'
            self.assertIn('Missing focus indicator', log.read_text(encoding='utf-8'))
            env = worker.call_args.kwargs['env']
            self.assertEqual('2', env['QT_SCALE_FACTOR'])
            self.assertEqual('zh_CN', env['PICVIEWER_LANG'])

    def test_worker_timeout_is_failure_with_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory, \
                patch('scripts.i18n.build_qm.build_qm'), \
                patch('tests.visual.run.subprocess.run',
                      side_effect=subprocess.TimeoutExpired('worker', 60)), \
                self.assertLogs('tests.visual.run', level='INFO'):
            output = Path(directory)
            self.assertEqual(1, run_matrix(output, False, cases()[0].name))
            log = output / cases()[0].name / 'worker.log'
            self.assertIn('exceeded 60 seconds', log.read_text(encoding='utf-8'))

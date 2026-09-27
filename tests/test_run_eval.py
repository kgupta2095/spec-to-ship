"""Release gate and results-file behaviour of src.run_eval. No network needed."""

import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from src import run_eval

REPO = Path(__file__).resolve().parents[1]
NO_KEYS = {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": ""}


class GateRule(unittest.TestCase):
    def test_meets_every_target(self):
        self.assertEqual(run_eval.gate_failures(15 / 16, 0.90, 0.80), [])

    def test_recorded_run_1_would_have_failed(self):
        # Recorded model run (claude-sonnet-4-5, 2026-08-23), run 1: 14/16, recall 100%, precision 100%.
        failures = run_eval.gate_failures(14 / 16, 1.0, 1.0)
        self.assertEqual(len(failures), 1)
        self.assertIn("Suite A", failures[0])

    def test_each_target_is_enforced(self):
        self.assertTrue(run_eval.gate_failures(1.0, 0.89, 1.0))
        self.assertTrue(run_eval.gate_failures(1.0, 1.0, 0.79))
        self.assertEqual(len(run_eval.gate_failures(0.0, 0.0, 0.0)), 3)


class MainInTempCopy(unittest.TestCase):
    """Run main() against a temporary copy of evals/, so the real files are never touched."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / "evals", self.tmp / "evals")
        (self.tmp / "evals" / "RESULTS.mock.md").unlink(missing_ok=True)
        self.recorded = (self.tmp / "evals" / "RESULTS.md").read_text()
        self.patches = [mock.patch.object(run_eval, "ROOT", self.tmp)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp)

    def run_main(self, argv, env):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env), redirect_stdout(out), redirect_stderr(err):
            code = run_eval.main(argv)
        return code, out.getvalue() + err.getvalue()

    def test_mock_writes_results_mock_and_leaves_recorded_run_alone(self):
        code, _ = self.run_main(["--mock"], {})
        self.assertEqual(code, 0)  # baseline misses the bar by design; gate not enforced
        self.assertTrue((self.tmp / "evals" / "RESULTS.mock.md").exists())
        self.assertEqual((self.tmp / "evals" / "RESULTS.md").read_text(), self.recorded)

    def test_no_key_behaves_like_mock(self):
        code, _ = self.run_main([], NO_KEYS)
        self.assertEqual(code, 0)
        self.assertEqual((self.tmp / "evals" / "RESULTS.md").read_text(), self.recorded)

    def test_mock_output_matches_committed_file(self):
        self.run_main(["--mock"], {})
        self.assertEqual(
            (self.tmp / "evals" / "RESULTS.mock.md").read_text(),
            (REPO / "evals" / "RESULTS.mock.md").read_text(),
        )

    def test_require_model_refuses_without_a_key(self):
        code, output = self.run_main(["--require-model"], NO_KEYS)
        self.assertEqual(code, 2)
        self.assertIn("Refusing to run", output)
        self.assertFalse((self.tmp / "evals" / "RESULTS.mock.md").exists())
        self.assertEqual((self.tmp / "evals" / "RESULTS.md").read_text(), self.recorded)

    def fake_model_run(self, a_pass, recall, precision):
        """Pretend a model key is set and the suites returned these scores (no network)."""
        return [
            mock.patch.object(run_eval.llm, "provider", return_value="anthropic"),
            mock.patch.object(run_eval, "suite_a", return_value=(a_pass, [])),
            mock.patch.object(run_eval, "suite_b", return_value=(recall, precision, [])),
        ]

    def test_model_run_below_bar_exits_1(self):
        patches = self.fake_model_run(14, 1.0, 1.0)
        for p in patches:
            p.start()
        try:
            code, output = self.run_main([], {})
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(code, 1)
        self.assertIn("RELEASE GATE: FAIL", output)
        written = (self.tmp / "evals" / "RESULTS.md").read_text()
        self.assertIn("Recorded model run (", written)
        self.assertIn("Release gate: **FAIL**", written)

    def test_model_run_meeting_bar_exits_0(self):
        patches = self.fake_model_run(16, 1.0, 1.0)
        for p in patches:
            p.start()
        try:
            code, output = self.run_main([], {})
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(code, 0)
        self.assertIn("RELEASE GATE: PASS", output)


if __name__ == "__main__":
    unittest.main()

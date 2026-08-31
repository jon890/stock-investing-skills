import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "wsaj-brain-eval.json"
SCRIPT = ROOT / "scripts" / "evaluate_wsaj_brain.py"

sys.path.insert(0, str(ROOT / "scripts"))

import evaluate_wsaj_brain  # pyright: ignore[reportMissingImports]


class WsajBrainEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_contains_exactly_fixed_category_counts(self):
        counts = Counter(case["category"] for case in self.fixture["cases"])

        self.assertEqual(counts["term"], 15)
        self.assertEqual(counts["process"], 15)
        self.assertEqual(counts["company_case"], 10)
        self.assertEqual(counts["time_or_conflict"], 5)
        self.assertEqual(counts["unsupported"], 5)
        self.assertEqual(len(self.fixture["cases"]), 50)

    def test_fixture_cases_declare_behavior_not_only_text_matches(self):
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                behavior = case["expected_behavior"]
                self.assertTrue(
                    behavior.get("query_terms_include")
                    or behavior.get("required_topics")
                    or behavior.get("message_contains")
                )
                self.assertIn(case["expected_status"], {"matched", "requires_current_external_data", "unsupported"})
                self.assertIsInstance(case["required_evidence_ids"], list)

    def test_evaluator_passes_fixed_quality_gate(self):
        summary = evaluate_wsaj_brain.evaluate(FIXTURE)

        self.assertTrue(summary["passed"], summary["failed_cases"])
        self.assertEqual(summary["total_cases"], 50)
        self.assertGreaterEqual(summary["metrics"]["citation_validity"], 0.9)
        self.assertGreaterEqual(summary["metrics"]["unsupported_refusal"], 0.95)
        self.assertEqual(summary["metrics"]["numeric_time_errors"], 0)

    def test_cli_outputs_json_summary_and_zero_on_pass(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--fixture", str(FIXTURE)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["failed_cases"], [])
        self.assertNotIn("cases", summary)

    def test_cli_details_includes_all_cases(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--fixture", str(FIXTURE), "--details"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertEqual(len(summary["cases"]), 50)

    def test_cli_exits_nonzero_when_threshold_fails(self):
        bad_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        bad_fixture["thresholds"]["citation_validity"] = 1.01
        with self.subTest("invalid threshold fixture"):
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / "bad-eval.json"
                path.write_text(json.dumps(bad_fixture, ensure_ascii=False), encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, str(SCRIPT), "--fixture", str(path)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                )

        self.assertNotEqual(completed.returncode, 0)
        summary = json.loads(completed.stdout)
        self.assertIn("citation_validity", summary["threshold_failures"])

    def test_citation_validation_rejects_undeclared_source_date(self):
        row = {
            "source_url": "https://www.youtube.com/watch?v=I4w_V9qUCXc&t=79s",
            "video_id": "I4w_V9qUCXc",
            "source_date": "2026-08-31",
            "timestamp_start_sec": 79.4,
            "timestamp_end_sec": 116.3,
        }

        valid, reason = evaluate_wsaj_brain.citation_has_valid_source(row)

        self.assertFalse(valid)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("source_date_status", reason)

    def test_citation_validation_requires_observation_date_for_verified_upload_date(self):
        row = {
            "source_url": "https://www.youtube.com/watch?v=I4w_V9qUCXc&t=79s",
            "video_id": "I4w_V9qUCXc",
            "source_date": "2021-08-15",
            "source_date_status": "verified_upload_date",
            "timestamp_start_sec": 79.4,
            "timestamp_end_sec": 116.3,
        }

        valid, reason = evaluate_wsaj_brain.citation_has_valid_source(row)

        self.assertFalse(valid)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("source_observed_at", reason)


if __name__ == "__main__":
    unittest.main()

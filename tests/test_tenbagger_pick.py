import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tenbagger_pick
from tests.test_bottleneck import sample_universe


VALUATION_OK = {
    "candidate": {"eligible": True, "reasons": []},
}


def valid_basis():
    return {
        "constraint": "advanced package capacity",
        "duration": "minimum three years",
        "duration_years": 3,
        "controller": "foundry and packaging suppliers",
        "verdict": "pass",
        "sources": [{
            "title": "capacity note",
            "url": "https://example.com/capacity",
            "observed_at": "2026-08-29",
        }],
    }


class TenbaggerPickTest(unittest.TestCase):
    def write_universe(self, tmpdir):
        path = Path(tmpdir) / "universe.json"
        path.write_text(json.dumps(sample_universe()), encoding="utf-8")
        return path

    def test_verified_bottleneck_can_be_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            universe_path = self.write_universe(td)
            with mock.patch.object(tenbagger_pick.valuation, "analyze", return_value=VALUATION_OK):
                result = tenbagger_pick.analyze("T40", universe_path, basis=valid_basis())

        self.assertEqual(result["candidate_status"], "candidate")
        self.assertEqual(result["bottleneck_context"]["group_code"], "5740")
        self.assertTrue(result["bottleneck_context"]["candidate_pool_passed"])

    def test_unverified_bottleneck_is_reference_only(self):
        with tempfile.TemporaryDirectory() as td:
            universe_path = self.write_universe(td)
            with mock.patch.object(tenbagger_pick.valuation, "analyze", return_value=VALUATION_OK):
                result = tenbagger_pick.analyze("T40", universe_path)

        self.assertEqual(result["candidate_status"], "reference_only")
        self.assertIn("병목 실체 확인이 부족하다", result["candidate_status_reasons"][0])

    def test_non_bottleneck_group_is_reference_only(self):
        with tempfile.TemporaryDirectory() as td:
            universe_path = self.write_universe(td)
            with mock.patch.object(tenbagger_pick.valuation, "analyze", return_value=VALUATION_OK):
                result = tenbagger_pick.analyze("T00", universe_path, basis=valid_basis())

        self.assertEqual(result["candidate_status"], "reference_only")
        self.assertIn("산업 그룹이 병목 상위권", result["candidate_status_reasons"][0])


if __name__ == "__main__":
    unittest.main()

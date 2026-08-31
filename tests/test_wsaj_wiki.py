import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "docs" / "wsaj" / "evidence" / "core.json"
SCRIPT_PATH = ROOT / "scripts" / "query_wsaj_wiki.py"


class WsajEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.rows = cls.payload["evidence"]

    def test_evidence_schema_is_reviewable(self):
        self.assertGreaterEqual(len(self.rows), 20)
        seen = set()
        allowed_claim_types = {"direct_claim", "inferred_principle", "historical_market_fact", "current_external_data", "unsupported"}
        allowed_confidence = {"high", "medium", "low"}
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertRegex(row["id"], r"^wsaj-evidence-\d{6}$")
                self.assertNotIn(row["id"], seen)
                seen.add(row["id"])
                self.assertIn(row["claim_type"], allowed_claim_types)
                self.assertIsInstance(row["claim"], str)
                self.assertLessEqual(len(row["claim"]), 160)
                self.assertIsInstance(row["topic"], list)
                self.assertGreater(row["topic"], [])
                self.assertRegex(row["video_id"], r"^[A-Za-z0-9_-]{8,}$")
                self.assertIn(row["video_id"], row["source_url"])
                self.assertRegex(row["source_date"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertLess(row["timestamp_start_sec"], row["timestamp_end_sec"])
                self.assertLessEqual(len(row["transcript_summary"]), 180)
                self.assertIn(row["confidence"], allowed_confidence)
                self.assertEqual(row["reviewed_by"], "agent")
                self.assertRegex(row["reviewed_at"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertIsInstance(row.get("visual_evidence", []), list)
                self.assertGreater(row.get("visual_evidence", []), [])

    def test_inferred_principles_have_supporting_evidence(self):
        ids = {row["id"] for row in self.rows}
        inferred = [row for row in self.rows if row["claim_type"] == "inferred_principle"]
        self.assertGreaterEqual(len(inferred), 2)
        for row in inferred:
            with self.subTest(row=row["id"]):
                support = row.get("supporting_evidence_ids", [])
                self.assertGreaterEqual(len(support), 2)
                self.assertTrue(set(support).issubset(ids))

    def test_query_matches_per_gaap(self):
        result = run_query("PER에서 GAAP과 non-GAAP은 어떻게 봐야 해?")
        self.assertEqual(result["status"], "matched")
        ids = [row["id"] for row in result["matches"]]
        self.assertIn("wsaj-evidence-000009", ids)

    def test_query_matches_special_situation(self):
        result = run_query("은행주는 PER보다 무엇을 봐야 해?")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["matches"][0]["id"], "wsaj-evidence-000023")

    def test_query_matches_probabilistic_edge(self):
        result = run_query("확률적 우위란 무엇인가?")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["matches"][0]["id"], "wsaj-evidence-000026")

    def test_query_rejects_current_buy_sell(self):
        result = run_query("오늘 엔비디아 매수해도 돼?")
        self.assertEqual(result["status"], "requires_current_external_data")
        self.assertGreater(result["matches"], [])
        self.assertIn("현재", result["message"])

    def test_query_unsupported_when_no_evidence(self):
        result = run_query("원유 선물 롤오버 전략은 어떻게 판단해?")
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["matches"], [])

    def test_query_unsupported_for_missing_valuation_terms(self):
        result = run_query("ROIC와 SBC와 해자는 어떻게 봐야 해?")
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["matches"], [])

    def test_query_rejects_personal_position_sizing(self):
        result = run_query("테슬라 포트폴리오 비중을 늘려도 돼?")
        self.assertEqual(result["status"], "requires_current_external_data")
        self.assertGreater(result["matches"], [])

    def test_current_data_detection_does_not_overmatch_descriptive_ratio(self):
        result = run_query("테슬라 매출 비중은 사례에서 어떻게 다뤄?")
        self.assertEqual(result["status"], "matched")

    def test_current_data_detection_does_not_overmatch_holding_period(self):
        result = run_query("테슬라 보유 기간 관점은 사례에서 어떻게 다뤄?")
        self.assertEqual(result["status"], "matched")

    def test_text_output_is_human_readable(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "안전마진은 어떻게 조절해?"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("status: matched", completed.stdout)
        self.assertTrue(re.search(r"wsaj-evidence-00001[23]", completed.stdout))


def run_query(question):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json", question],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


if __name__ == "__main__":
    unittest.main()

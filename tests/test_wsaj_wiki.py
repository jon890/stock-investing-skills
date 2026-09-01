import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "wiki" / "experts" / "wsaj" / "evidence" / "core.json"
SCRIPT_PATH = ROOT / "scripts" / "query_wsaj_wiki.py"
GENERIC_SCRIPT_PATH = ROOT / "scripts" / "query_investing_wiki.py"


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

    def test_query_matches_investing_values_in_natural_language(self):
        questions = [
            "월가아재의 투자 가치관은 무엇인가?",
            "월가아재의 투자 철학을 설명해 줘",
            "개인 투자자가 참고할 투자 원칙은 무엇인가?",
        ]
        for question in questions:
            with self.subTest(question=question):
                result = run_query(question)
                self.assertEqual(result["status"], "matched")
                self.assertEqual(result["matches"][0]["id"], "wsaj-evidence-000026")

    def test_investing_values_alias_does_not_match_unrelated_question(self):
        result = run_query("가치관과 무관한 원유 선물 롤오버 전략은 어떻게 판단해?")
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["matches"], [])

    def test_query_matches_index_dcf(self):
        result = run_query("인덱스 DCF로 시장 리스크 프리미엄을 어떻게 봐?")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["matches"][0]["id"], "wsaj-evidence-000027")

    def test_query_matches_reverse_dcf(self):
        result = run_query("Reverse DCF로 시장 가격에 들어간 성장률을 어떻게 역산해?")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["matches"][0]["id"], "wsaj-evidence-000029")

    def test_query_matches_relative_valuation_risk(self):
        questions = [
            "상대가치평가 약점은 뭐야?",
            "유사기업 전체가 고평가되어 있으면 결론도 왜곡돼?",
        ]
        for question in questions:
            with self.subTest(question=question):
                result = run_query(question)
                self.assertEqual(result["status"], "matched")
                self.assertEqual(result["matches"][0]["id"], "wsaj-evidence-000028")

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

    def test_generic_cli_requires_expert(self):
        completed = subprocess.run(
            [sys.executable, str(GENERIC_SCRIPT_PATH), "--json", "안전마진은 어떻게 조절해?"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "expert_required")
        self.assertIn("wsaj", result["experts"])

    def test_generic_cli_requires_expert_even_with_evidence_dir(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(GENERIC_SCRIPT_PATH),
                "--json",
                "--evidence-dir",
                str(EVIDENCE_PATH.parent),
                "안전마진은 어떻게 조절해?",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "expert_required")
        self.assertEqual(result["matches"], [])

    def test_generic_cli_reports_unknown_expert(self):
        completed = subprocess.run(
            [sys.executable, str(GENERIC_SCRIPT_PATH), "--json", "--expert", "unknown", "안전마진은 어떻게 조절해?"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "expert_not_found")
        self.assertIn("wsaj", result["experts"])

    def test_generic_cli_rejects_mismatched_evidence_dir(self):
        with temp_wiki() as wiki:
            buffett = wiki / "experts" / "buffett"
            buffett.mkdir(parents=True)
            write_profile(buffett, "buffett")
            write_book_evidence(buffett)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(GENERIC_SCRIPT_PATH),
                    "--json",
                    "--wiki-root",
                    str(wiki),
                    "--expert",
                    "wsaj",
                    "--evidence-dir",
                    str(buffett / "evidence"),
                    "안전마진은 어떻게 조절해?",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "evidence_dir_mismatch")

    def test_generic_cli_rejects_loaded_evidence_with_wrong_expert(self):
        with temp_wiki() as wiki:
            evidence_path = wiki / "experts" / "wsaj" / "evidence" / "core.json"
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
            payload["evidence"][0]["expert_id"] = "other"
            evidence_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(GENERIC_SCRIPT_PATH),
                    "--json",
                    "--wiki-root",
                    str(wiki),
                    "--expert",
                    "wsaj",
                    "안전마진은 어떻게 조절해?",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "evidence_expert_mismatch")
        self.assertIn("wsaj-evidence-000001", result["mismatched_evidence_ids"])

    def test_generic_text_cli_renders_book_locator(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki = Path(tmpdir) / "wiki"
            buffett = wiki / "experts" / "buffett"
            buffett.mkdir(parents=True)
            write_profile(buffett, "buffett")
            write_book_evidence(buffett)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(GENERIC_SCRIPT_PATH),
                    "--wiki-root",
                    str(wiki),
                    "--expert",
                    "buffett",
                    "margin",
                ],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

        self.assertIn("status: matched", completed.stdout)
        self.assertIn("locator: book: The Essays, p.12", completed.stdout)

    def test_generic_search_matches_non_youtube_source_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki = Path(tmpdir) / "wiki"
            buffett = wiki / "experts" / "buffett"
            buffett.mkdir(parents=True)
            write_profile(buffett, "buffett")
            write_book_evidence(buffett, source_summary="durable-edge appears only in the summary.")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(GENERIC_SCRIPT_PATH),
                    "--json",
                    "--wiki-root",
                    str(wiki),
                    "--expert",
                    "buffett",
                    "durable-edge",
                ],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["matches"][0]["id"], "buffett-evidence-000001")

    def test_wsaj_wrapper_matches_generic_wsaj_search(self):
        wsaj = run_query("안전마진은 어떻게 조절해?")
        completed = subprocess.run(
            [sys.executable, str(GENERIC_SCRIPT_PATH), "--json", "--expert", "wsaj", "안전마진은 어떻게 조절해?"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        generic = json.loads(completed.stdout)
        self.assertEqual(generic["status"], wsaj["status"])
        self.assertEqual(
            [row["id"] for row in generic["matches"]],
            [row["id"] for row in wsaj["matches"]],
        )


def run_query(question):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json", question],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def temp_wiki():
    class TempWiki:
        def __enter__(self):
            self.tmp = tempfile.TemporaryDirectory()
            self.path = Path(self.tmp.name) / "wiki"
            copy_tree(ROOT / "wiki", self.path)
            return self.path

        def __exit__(self, exc_type, exc, tb):
            self.tmp.cleanup()

    return TempWiki()


def copy_tree(src: Path, dst: Path) -> None:
    for path in src.rglob("*"):
        target = dst / path.relative_to(src)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())


def write_profile(expert_dir: Path, expert_id: str) -> None:
    (expert_dir / "evidence").mkdir(exist_ok=True)
    (expert_dir / "index.md").write_text(
        "---\ntitle: Buffett\n---\n# Buffett\n",
        encoding="utf-8",
    )
    (expert_dir / "profile.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "expert_id": expert_id,
                "expert_name": expert_id.title(),
                "display_name": expert_id.title(),
                "corpus_id": f"{expert_id}-public",
                "source_scope": "public materials",
                "language": "en",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_book_evidence(expert_dir: Path, source_summary: str = "A short book evidence summary.") -> None:
    row = {
        "id": "buffett-evidence-000001",
        "expert_id": "buffett",
        "expert_name": "Buffett",
        "corpus_id": "buffett-public",
        "source_kind": "book",
        "claim_type": "direct_claim",
        "claim": "Margin of safety matters.",
        "topic": ["margin"],
        "source_title": "The Essays",
        "source_url": "https://example.com/essays",
        "source_date": "1997-01-01",
        "source_date_status": "verified_publication_date",
        "source_observed_at": "2026-09-01",
        "source_summary": source_summary,
        "confidence": "high",
        "reviewed_by": "agent",
        "reviewed_at": "2026-09-01",
        "source_locator": {
            "source_kind": "book",
            "title": "The Essays",
            "page": 12,
        },
    }
    (expert_dir / "evidence" / "core.json").write_text(
        json.dumps({"schema_version": "1.0", "evidence": [row]}, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()

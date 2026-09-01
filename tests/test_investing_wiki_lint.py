import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lint_investing_wiki.py"

sys.path.insert(0, str(ROOT / "scripts"))

import lint_investing_wiki  # pyright: ignore[reportMissingImports]


class InvestingWikiLintTests(unittest.TestCase):
    def test_current_wiki_passes(self):
        self.assertEqual(lint_investing_wiki.lint(ROOT / "wiki"), [])

    def test_cli_outputs_json_and_zero_on_pass(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["passed"])

    def test_missing_profile_fails(self):
        with temp_wiki() as wiki:
            (wiki / "experts" / "wsaj" / "profile.json").unlink()
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("missing profile.json" in item for item in failures), failures)

    def test_missing_root_index_fails(self):
        with temp_wiki() as wiki:
            (wiki / "index.md").unlink()
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("missing root index.md" in item for item in failures), failures)

    def test_missing_expert_index_fails(self):
        with temp_wiki() as wiki:
            (wiki / "experts" / "wsaj" / "index.md").unlink()
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("missing expert index.md" in item for item in failures), failures)

    def test_duplicate_global_id_fails(self):
        with temp_wiki() as wiki:
            other = wiki / "experts" / "buffett"
            other.mkdir(parents=True)
            write_profile(other, "buffett")
            write_evidence(other, sample_evidence("buffett", evidence_id="wsaj-evidence-000001"))
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("duplicate evidence id wsaj-evidence-000001" in item for item in failures), failures)

    def test_broken_evidence_id_fails(self):
        with temp_wiki() as wiki:
            page = wiki / "experts" / "wsaj" / "pages" / "broken.md"
            page.write_text(
                "---\ntitle: Broken\nevidence_ids:\n  - wsaj-evidence-999999\n---\n# Broken\n",
                encoding="utf-8",
            )
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("broken evidence_id wsaj-evidence-999999" in item for item in failures), failures)

    def test_mismatched_expert_id_fails(self):
        with temp_wiki() as wiki:
            evidence_path = wiki / "experts" / "wsaj" / "evidence" / "core.json"
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
            payload["evidence"][0]["expert_id"] = "other"
            evidence_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("evidence expert_id must match wsaj" in item for item in failures), failures)

    def test_valid_non_youtube_locator_passes(self):
        with temp_wiki() as wiki:
            expert = wiki / "experts" / "buffett"
            expert.mkdir(parents=True)
            write_profile(expert, "buffett")
            write_evidence(expert, sample_evidence("buffett", source_kind="book"))
            failures = lint_investing_wiki.lint(wiki)

        self.assertFalse([item for item in failures if "buffett" in item], failures)

    def test_invalid_non_youtube_locator_fails(self):
        with temp_wiki() as wiki:
            expert = wiki / "experts" / "buffett"
            expert.mkdir(parents=True)
            write_profile(expert, "buffett")
            row = sample_evidence("buffett", source_kind="book")
            row["source_locator"]["video_id"] = "not-allowed"
            write_evidence(expert, row)
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("non-YouTube locator must not use video_id" in item for item in failures), failures)

    def test_missing_supporting_evidence_id_fails(self):
        with temp_wiki() as wiki:
            evidence_path = wiki / "experts" / "wsaj" / "evidence" / "core.json"
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
            payload["evidence"][0]["supporting_evidence_ids"] = ["wsaj-evidence-999999"]
            evidence_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("broken supporting_evidence_id wsaj-evidence-999999" in item for item in failures), failures)

    def test_cross_expert_supporting_evidence_id_fails(self):
        with temp_wiki() as wiki:
            other = wiki / "experts" / "buffett"
            other.mkdir(parents=True)
            write_profile(other, "buffett")
            write_evidence(other, sample_evidence("buffett"))
            evidence_path = wiki / "experts" / "wsaj" / "evidence" / "core.json"
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
            payload["evidence"][0]["supporting_evidence_ids"] = ["buffett-evidence-000001"]
            evidence_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("belongs to expert buffett, not wsaj" in item for item in failures), failures)

    def test_self_supporting_evidence_id_fails(self):
        with temp_wiki() as wiki:
            evidence_path = wiki / "experts" / "wsaj" / "evidence" / "core.json"
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence_id = payload["evidence"][0]["id"]
            payload["evidence"][0]["supporting_evidence_ids"] = [evidence_id]
            evidence_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            failures = lint_investing_wiki.lint(wiki)

        self.assertTrue(any("supporting_evidence_ids must not include itself" in item for item in failures), failures)


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
    (expert_dir / "pages").mkdir(exist_ok=True)
    (expert_dir / "index.md").write_text(
        f"---\ntitle: {expert_id.title()}\n---\n# {expert_id.title()}\n",
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
                "language": "ko",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def sample_evidence(expert_id: str, evidence_id: str | None = None, source_kind: str = "article"):
    row = {
        "id": evidence_id or f"{expert_id}-evidence-000001",
        "expert_id": expert_id,
        "expert_name": expert_id.title(),
        "corpus_id": f"{expert_id}-public",
        "source_kind": source_kind,
        "claim_type": "direct_claim",
        "claim": "검증용 주장이다.",
        "topic": ["test"],
        "source_title": "검증 자료",
        "source_url": "https://example.com/source",
        "source_date": "2020-01-01",
        "source_date_status": "verified_publication_date",
        "source_observed_at": "2026-09-01",
        "source_summary": "검증용 요약이다.",
        "confidence": "high",
        "reviewed_by": "agent",
        "reviewed_at": "2026-09-01",
        "source_locator": {
            "source_kind": source_kind,
            "title": "검증 자료",
            "publication": "Example",
            "publication_date": "2020-01-01",
            "url": "https://example.com/source",
        },
    }
    if source_kind == "book":
        row["source_date_status"] = "verified_publication_date"
        row["source_locator"] = {
            "source_kind": "book",
            "title": "검증 책",
            "page": 1,
        }
    return row


def write_evidence(expert_dir: Path, row) -> None:
    (expert_dir / "evidence" / "core.json").write_text(
        json.dumps({"schema_version": "1.0", "evidence": [row]}, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bottleneck = load_module("scripts/bottleneck.py", "bottleneck")
render_report = load_module("scripts/render_report.py", "render_report")


def stock(ticker, group, margin_delta, returns=None):
    es26 = 4.0
    es27 = 3.0
    margin26 = 0.20
    margin27 = margin26 + margin_delta if margin_delta is not None else None
    ee26 = es26 / margin26
    ee27 = es27 / margin27 if margin27 else None
    return {
        "id": ticker,
        "t": ticker,
        "name": ticker,
        "g": group,
        "s": group[:2],
        "cap": 1_000.0,
        "ret": returns or {"1m": 1.0, "3m": 2.0, "6m": 3.0, "ytd": 4.0, "1y": 5.0},
        "val": {
            "mcap": 1_000.0,
            "ev": 1_000.0,
            "es26": es26,
            "es27": es27,
            "ee26": ee26,
            "ee27": ee27,
            "tgt": 10.0,
            "tlo": 5.0,
            "thi": 20.0,
            "nest": 5,
        },
    }


def sample_universe():
    groups = ["5010", "5130", "5310", "5720", "5740"]
    stocks = []
    for group_index, group in enumerate(groups):
        for member_index in range(3):
            item = stock(
                f"T{group_index}{member_index}",
                group,
                0.01 + group_index * 0.005,
            )
            item["val"]["es27"] = 4.0 / (1.05 + group_index * 0.05)
            margin27 = item["d"]["margin27"] if item.get("d") else 0.21 + group_index * 0.005
            item["val"]["ee27"] = item["val"]["es27"] / margin27
            item["ret"] = {
                period: value + group_index
                for period, value in item["ret"].items()
            }
            stocks.append(item)
    return {"market": "USA", "count": len(stocks), "missing_valuation": 0, "stocks": stocks}


class BottleneckTest(unittest.TestCase):
    def test_tenbagger_requires_positive_margin_delta(self):
        members = [
            stock("GOOD", "5720", 0.03),
            stock("FLAT", "5720", 0.0),
            stock("DOWN", "5720", -0.01),
            stock("MISS", "5720", None),
        ]
        group = {"members": members}
        for member in members:
            member["d"] = bottleneck.derive(member)

        tickers = [x["ticker"] for x in bottleneck.tenbagger_candidates(group)]

        self.assertEqual(tickers, ["GOOD"])

    def test_low_return_coverage_fails_before_scoring(self):
        data = {
            "market": "USA",
            "stocks": [stock("A", "5720", 0.03, {"1m": 1.0}) for _ in range(100)],
        }

        with self.assertRaises(SystemExit) as caught:
            bottleneck.validate_universe(data)

        self.assertIn("기간 수익률 커버리지", str(caught.exception))

    def test_missing_group_has_friendly_error(self):
        with tempfile.TemporaryDirectory() as td:
            universe_path = Path(td) / "universe.json"
            universe_path.write_text(json.dumps(sample_universe()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/bottleneck.py"),
                    str(universe_path),
                    "--group",
                    "NOPE",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("그룹을 찾지 못했습니다", result.stderr)

    def test_bottleneck_json_and_html_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            usa_source = tmp / "universe-USA.json"
            usa_json = tmp / "bottleneck-USA.json"
            html = tmp / "bottleneck.html"
            usa_source.write_text(json.dumps(sample_universe()), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/bottleneck.py"), str(usa_source), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            parsed = json.loads(result.stdout)
            usa_json.write_text(result.stdout)
            self.assertIn("dispersion", parsed["factors"])
            self.assertIn("quality", parsed)
            self.assertIn("coverage", parsed["groups"][0])
            self.assertIn("persistence", parsed["groups"][0])
            self.assertNotIn("candidates", parsed["groups"][0])
            self.assertGreaterEqual(parsed["quality"]["min_return_coverage"], 0.98)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/render_report.py"),
                    "bottleneck",
                    str(usa_json),
                    str(usa_json),
                    "2026-08-29",
                    "-o",
                    str(html),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            body = html.read_text()
            self.assertIn("데이터 커버리지", body)
            self.assertIn("기대 분산", body)
            self.assertIn("지속성은", body)
            self.assertIn("작성:", result.stdout)

    def test_no_missing_factor_fallback_is_visible(self):
        data = sample_universe()
        stocks, _ = bottleneck.validate_universe(data)
        groups, _ = bottleneck.aggregate(stocks)
        ranked = sorted(bottleneck.score(groups).values(), key=lambda v: -v["score"])
        best = ranked[0]
        for factor in best["coverage"]:
            best["coverage"][factor] = 1.0

        self.assertEqual(bottleneck.factor_gap_text(best), "없음")

    def test_group_json_exports_bottleneck_context_without_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            universe_path = tmp / "universe.json"
            basis_path = tmp / "basis.json"
            universe_path.write_text(json.dumps(sample_universe()), encoding="utf-8")
            basis_path.write_text(json.dumps({
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
            }), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/bottleneck.py"),
                    str(universe_path),
                    "--group",
                    "5740",
                    "--basis",
                    str(basis_path),
                    "--json",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

        parsed = json.loads(result.stdout)
        context = parsed["bottleneck_context"]
        self.assertEqual(context["group_code"], "5740")
        self.assertTrue(context["is_bottleneck_group"])
        self.assertTrue(context["bottleneck_basis"]["verified"])
        self.assertTrue(context["candidate_pool_passed"])
        self.assertNotIn("candidates", context)

    def test_ticker_json_marks_unverified_basis_reference_only(self):
        with tempfile.TemporaryDirectory() as td:
            universe_path = Path(td) / "universe.json"
            universe_path.write_text(json.dumps(sample_universe()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/bottleneck.py"),
                    str(universe_path),
                    "--ticker",
                    "T40",
                    "--json",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

        context = json.loads(result.stdout)["bottleneck_context"]
        self.assertEqual(context["ticker"]["ticker"], "T40")
        self.assertFalse(context["bottleneck_basis"]["verified"])
        self.assertTrue(all(c["candidate_status"] == "reference_only" for c in context["candidates"]))

    def test_basis_requires_three_year_duration_and_observed_sources(self):
        bad = bottleneck.bottleneck_basis({
            "constraint": "capacity",
            "duration": "short",
            "duration_years": 2,
            "controller": "supplier",
            "verdict": "pass",
            "sources": [{"title": "note", "url": "https://example.com"}],
        })

        self.assertFalse(bad["verified"])
        self.assertIn("duration_years>=3", bad["missing"])
        self.assertIn("verified_sources", bad["missing"])


if __name__ == "__main__":
    unittest.main()

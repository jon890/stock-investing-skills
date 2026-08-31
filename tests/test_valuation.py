import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import render_report
import valuation


class ValuationEngineTest(unittest.TestCase):
    def load_cfg(self, ticker="CRDO"):
        return json.loads((SCRIPTS / "inputs" / f"{ticker}.json").read_text())

    def run_json(self, ticker="CRDO"):
        out = subprocess.check_output(
            [sys.executable, str(SCRIPTS / "valuation.py"), ticker, "--json"],
            text=True,
        )
        return json.loads(out)

    def write_temp_input(self, tmpdir, ticker="CRDO", **updates):
        cfg = self.load_cfg(ticker)
        cfg.update(updates)
        path = Path(tmpdir) / f"{ticker}.json"
        path.write_text(json.dumps(cfg, ensure_ascii=False))
        return path

    def test_input_declares_three_year_tenbagger_and_final_year(self):
        cfg = self.load_cfg()

        years, first_year, relative_year = valuation.config_years(cfg)
        ten = valuation.tenbagger(cfg, years=years, first_year=first_year)

        self.assertEqual(years, 3)
        self.assertEqual(first_year, 2027)
        self.assertEqual(relative_year, 2027)
        self.assertEqual(ten["final_year"], 2029)
        self.assertAlmostEqual(ten["required_cagr"], 10 ** (1 / 3) - 1)

    def test_tenbagger_uses_third_projected_revenue(self):
        cfg = self.load_cfg()

        ten = valuation.tenbagger(cfg, years=3, first_year=2027)

        self.assertEqual(ten["scenarios"]["기본"]["revenue_end"], 5060)
        self.assertEqual(ten["terminal_revenue"], 5060)

    def test_short_revenue_projection_has_friendly_error(self):
        cfg = self.load_cfg()
        cfg["scenarios"]["기본"]["revenue"] = [100, 120]

        with self.assertRaisesRegex(ValueError, "매출 투영은 2년뿐"):
            valuation.tenbagger(cfg, years=3, first_year=2027)

    def test_short_margin_projection_has_friendly_error(self):
        cfg = self.load_cfg()
        cfg["scenarios"]["기본"]["opm"] = [0.4, 0.42]

        with self.assertRaisesRegex(ValueError, "영업이익률 투영은 2년뿐"):
            valuation.tenbagger(cfg, years=3, first_year=2027)

    def test_tam_is_ignored_when_year_does_not_match_final_year(self):
        cfg = self.load_cfg()

        ten = valuation.tenbagger(cfg, years=3, first_year=2027)

        self.assertEqual(ten["final_year"], 2029)
        self.assertEqual(ten["tam_year"], 2036)
        self.assertIsNone(ten["tam"])
        self.assertIsNone(ten["tam_share_needed"])

    def test_reverse_dcf_projection_length_is_independent_from_tenbagger_years(self):
        cfg = self.load_cfg()

        rev = valuation.reverse_dcf(cfg)
        ten = valuation.tenbagger(cfg, years=3, first_year=2027)

        self.assertEqual(rev["years"], 5)
        self.assertEqual(ten["years"], 3)

    def test_relative_multiple_year_controls_peer_fields(self):
        cfg = self.load_cfg()
        peers = valuation.prep_peers({x["t"]: x for x in cfg["peers"]}, relative_year=2027)
        fields = valuation.multiple_fields(2027)

        self.assertEqual(fields["sales"], "es27")
        self.assertEqual(fields["ebitda"], "ee27")
        self.assertEqual(fields["per"], "per27")
        self.assertEqual(peers["CRDO"]["relative_multiple_year"], 2027)
        self.assertEqual(peers["CRDO"]["relative_fields"]["ev_sales"], "es27")
        self.assertAlmostEqual(peers["CRDO"]["sales_f2"], peers["CRDO"]["ev"] / peers["CRDO"]["es27"])

    def test_json_output_carries_relative_basis_and_tenbagger_horizon(self):
        data = self.run_json("MRVL")

        self.assertEqual(data["tenbagger"]["years"], 3)
        self.assertEqual(data["tenbagger"]["final_year"], 2029)
        self.assertEqual(data["relative_multiple_year"], 2027)
        self.assertEqual(data["relative_fields"]["sales"], "es27")
        self.assertTrue(all(r["relative_multiple_year"] == 2027 for r in data["relative_rows"]))
        self.assertTrue(all(r["relative_field"] in {"es27", "ee27"} for r in data["relative_rows"]))

    def test_cli_mentions_dynamic_horizon_and_required_cagr(self):
        out = subprocess.check_output(
            [sys.executable, str(SCRIPTS / "valuation.py"), "CRDO"],
            text=True,
        )

        self.assertIn("텐베거 판정 (3년, 2029년 기준)", out)
        self.assertIn("10배에 필요한 연복리 115%", out)

    def test_report_heading_mentions_dynamic_horizon_and_relative_year(self):
        data = self.run_json("CRDO")

        html = render_report.render_company(data)

        self.assertIn("<h2>3년 뒤와 텐베거</h2>", html)
        self.assertIn("상대가치 기준 연도는 2027년", html)
        self.assertIn("<code>es27</code>", html)

    def test_render_report_help_exits_zero(self):
        p = subprocess.run(
            [sys.executable, str(SCRIPTS / "render_report.py"), "--help"],
            text=True,
            capture_output=True,
        )

        self.assertEqual(p.returncode, 0)
        self.assertIn("사용법:", p.stdout)
        self.assertEqual(p.stderr, "")

    def test_render_report_missing_output_is_usage_error(self):
        p = subprocess.run(
            [sys.executable, str(SCRIPTS / "render_report.py"), "company", "x.json"],
            text=True,
            capture_output=True,
        )

        self.assertEqual(p.returncode, 2)
        self.assertIn("사용법:", p.stderr)
        self.assertIn("출력 경로", p.stderr)

    def test_render_report_unknown_kind_is_usage_error(self):
        p = subprocess.run(
            [sys.executable, str(SCRIPTS / "render_report.py"), "unknown", "x.json", "-o", "out.html"],
            text=True,
            capture_output=True,
        )

        self.assertEqual(p.returncode, 2)
        self.assertIn("알 수 없는 리포트 종류", p.stderr)

    def test_missing_relative_year_holds_json_html_and_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_temp_input(tmpdir, relative_multiple_year=2028)
            env = os.environ.copy()
            env["VALUATION_INPUTS"] = tmpdir
            raw = subprocess.check_output(
                [sys.executable, str(SCRIPTS / "valuation.py"), "CRDO", "--json"],
                text=True,
                env=env,
            )
            data = json.loads(raw)

            self.assertEqual(data["relative_rows"], [])
            self.assertIsNone(data["relative_ps"])
            self.assertIsNone(data["relative"])
            self.assertIsNone(data["disagreement"])
            self.assertIn("2028년 기준 동종군 배수가 부족하다", data["relative_hold_reason"])
            self.assertIn("es28 관측 0개", data["relative_hold_reason"])
            self.assertIn("ee28 관측 0개", data["relative_hold_reason"])

            html = render_report.render_company(data)
            self.assertIn("상대가치 보류", html)
            self.assertIn("es28", html)
            self.assertIn("ee28", html)

            cli = subprocess.check_output(
                [sys.executable, str(SCRIPTS / "valuation.py"), "CRDO"],
                text=True,
                env=env,
            )
            self.assertIn("상대가치 보류", cli)
            self.assertIn("es28 관측 0개", cli)


if __name__ == "__main__":
    unittest.main()

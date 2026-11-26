import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "x5_guardian_analysis.py"


class GuardianAnalysisTests(unittest.TestCase):
    def run_analysis(self, checks, history=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        diag = root / "diagnostics.json"
        hist = root / "history.json"
        diag.write_text(json.dumps({"checks": checks}, ensure_ascii=False), encoding="utf-8")
        hist.write_text(json.dumps(history or [], ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(diag), str(hist)],
            cwd=root, capture_output=True, text=True, check=True,
        )
        payload = json.loads(diag.read_text(encoding="utf-8"))
        self.assertTrue((root / "x5-guardian-analysis.md").is_file())
        self.assertIn("X-5 Guardian", result.stdout)
        return payload["analysis"]

    def test_open_meteo_warning_with_met_norway_ok(self):
        analysis = self.run_analysis([
            {"name": "Open-Meteo", "state": "WARN"},
            {"name": "MET Norway", "state": "OK"},
        ])
        self.assertTrue(any("Open-Meteo" in f["title"] and "MET Norway" in f["title"]
                            for f in analysis["findings"]))

    def test_both_forecast_sources_unavailable_is_critical(self):
        analysis = self.run_analysis([
            {"name": "Open-Meteo", "state": "FAIL"},
            {"name": "MET Norway", "state": "WARN"},
        ])
        self.assertTrue(any(f["severity"] == "critical" and "záložní" in f["title"]
                            for f in analysis["findings"]))

    def test_page_failure_is_critical(self):
        analysis = self.run_analysis([{"name": "GitHub Pages / HTML", "state": "FAIL"}])
        self.assertTrue(any(f["severity"] == "critical" and "stránka" in f["title"]
                            for f in analysis["findings"]))

    def test_repeated_source_failures_are_detected(self):
        history = [{"checks": [{"name": "Open-Meteo", "state": "WARN"}]} for _ in range(3)]
        analysis = self.run_analysis([{"name": "Open-Meteo", "state": "OK"}], history)
        self.assertTrue(any(item["source"] == "Open-Meteo" and item["non_ok_in_last_8"] == 3
                            for item in analysis["recurring_issues"]))

    def test_all_ok_has_info_finding(self):
        analysis = self.run_analysis([
            {"name": "GitHub Pages / HTML", "state": "OK"},
            {"name": "Open-Meteo", "state": "OK"},
            {"name": "ECMWF IFS přes Open-Meteo", "state": "OK"},
            {"name": "MET Norway", "state": "OK"},
            {"name": "ČHMÚ archiv", "state": "OK"},
        ])
        self.assertEqual(analysis["findings"][0]["severity"], "info")

    def test_no_finding_enables_automatic_repair(self):
        analysis = self.run_analysis([{"name": "Open-Meteo", "state": "WARN"}])
        self.assertTrue(analysis["findings"])
        self.assertTrue(all(item["automatic_repair"] is False for item in analysis["findings"]))
        self.assertEqual(analysis["mode"], "explainable_rules_not_llm")


if __name__ == "__main__":
    unittest.main(verbosity=2)

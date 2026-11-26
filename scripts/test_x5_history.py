import json
import tempfile
import unittest
from pathlib import Path

from x5_history import MAX_HISTORY, build_report, load_history, read_snapshot

class HistoryTests(unittest.TestCase):
    def test_reads_and_normalizes_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diagnostics.json"
            path.write_text(json.dumps({"checks": [
                {"name": "API", "state": "ok", "detail": "good"},
                {"name": "X", "state": "unknown"}
            ]}), encoding="utf-8")
            snap = read_snapshot(path)
            self.assertEqual(snap["checks"][0]["state"], "OK")
            self.assertEqual(snap["checks"][1]["state"], "WARN")

    def test_missing_history_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_history(Path(tmp) / "none.json"), [])

    def test_report_contains_counts_and_source_trend(self):
        history = [{"checked_at_utc": "2026-11-26T00:00:00Z", "checks": [
            {"name": "API", "state": "OK"}, {"name": "ČHMÚ", "state": "WARN"}
        ]}]
        report = build_report(history)
        self.assertIn("| 1 | 1 | 0 |", report)
        self.assertIn("ČHMÚ", report)
        self.assertIn("WARN", report)

    def test_history_is_bounded(self):
        history = [{"checked_at_utc": str(i), "checks": []} for i in range(MAX_HISTORY + 5)]
        bounded = history[-MAX_HISTORY:]
        self.assertEqual(len(bounded), MAX_HISTORY)
        self.assertEqual(bounded[0]["checked_at_utc"], "5")

if __name__ == "__main__":
    unittest.main()

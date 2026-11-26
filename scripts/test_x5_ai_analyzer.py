import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import x5_ai_analyzer as analyzer

SCRIPT = Path(__file__).with_name("x5_ai_analyzer.py")

class AIAnalyzerTests(unittest.TestCase):
    def test_missing_secret_skips_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "diagnostics.json"
            source.write_text(json.dumps({"checks": []}), encoding="utf-8")
            env = dict(os.environ)
            env.pop("OPENAI_API_KEY", None)
            result = subprocess.run([sys.executable, str(SCRIPT), str(source)],
                                    env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assertIn("AI analýza přeskočena", result.stdout)

    def test_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.json"
            source.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                analyzer.load_diagnostics(source)

    def test_rejects_invalid_checks_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.json"
            source.write_text('{"checks": {}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                analyzer.load_diagnostics(source)

    def test_rejects_oversized_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "large.json"
            source.write_bytes(b" " * (analyzer.MAX_INPUT_BYTES + 1))
            with self.assertRaises(ValueError):
                analyzer.load_diagnostics(source)

    def test_extracts_only_output_text(self):
        result = {"status": "completed", "output": [
            {"type": "reasoning", "content": []},
            {"type": "message", "content": [
                {"type": "output_text", "text": "Kontrola v pořádku."}
            ]}
        ]}
        self.assertEqual(analyzer.extract_text(result), "Kontrola v pořádku.")

    def test_incomplete_response_is_not_reported_as_success(self):
        self.assertEqual(analyzer.extract_text({"status": "incomplete", "output": []}), "")

    @patch("x5_ai_analyzer.time.sleep")
    @patch("x5_ai_analyzer.urllib.request.urlopen")
    def test_retries_rate_limit_then_succeeds(self, mocked_urlopen, _sleep):
        from unittest.mock import MagicMock
        import urllib.error
        headers = {"Retry-After": "0"}
        mocked_urlopen.side_effect = [
            urllib.error.HTTPError(analyzer.ENDPOINT, 429, "limited", headers, None),
            MagicMock(__enter__=lambda self: self, __exit__=lambda *args: None,
                      read=lambda: b'{"status":"completed","output":[]}'),
        ]
        result = analyzer.request_analysis({"model": "test"}, "secret")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(mocked_urlopen.call_count, 2)

if __name__ == "__main__":
    unittest.main()

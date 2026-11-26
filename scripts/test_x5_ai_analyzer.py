import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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

if __name__ == "__main__":
    unittest.main()

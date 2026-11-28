import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from archive_parsers import extract_kp_series, parse_kp_value


class GFZKpParserTests(unittest.TestCase):
    def test_gfz_parallel_arrays_with_thirds_notation(self):
        payload = {
            "datetime": [
                "2026-11-27T00:00:00Z",
                "2026-11-27T03:00:00Z",
                "2026-11-27T06:00:00Z",
            ],
            "Kp": ["2-", "3o", "4+"],
            "status": ["def", "def", "def"],
        }
        values = extract_kp_series(payload)
        self.assertEqual(len(values), 3)
        self.assertAlmostEqual(values[next(t for t in values if t.hour == 0)], 2 - 1 / 3)
        self.assertAlmostEqual(values[next(t for t in values if t.hour == 3)], 3)
        self.assertAlmostEqual(values[next(t for t in values if t.hour == 6)], 4 + 1 / 3)

    def test_numeric_values_and_row_table(self):
        payload = [["datetime", "Kp", "status"],
                   ["2026-11-27T00:00:00Z", "2.67", "def"],
                   ["2026-11-27T03:00:00Z", 3.0, "def"]]
        self.assertEqual(len(extract_kp_series(payload)), 2)

    def test_invalid_values_are_ignored(self):
        self.assertIsNone(parse_kp_value("nan"))
        self.assertIsNone(parse_kp_value("-1"))
        self.assertIsNone(parse_kp_value("bad"))


if __name__ == "__main__":
    unittest.main()

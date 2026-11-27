import pathlib
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from x5_guardian import age_minutes, freshness_state, parse_utc


class GuardianFreshnessTests(unittest.TestCase):
    def test_parse_utc_accepts_z_suffix(self):
        self.assertEqual(
            parse_utc("2026-11-27T10:00:00Z"),
            datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc),
        )

    def test_parse_utc_rejects_invalid_value(self):
        self.assertIsNone(parse_utc("not-a-timestamp"))

    def test_age_minutes_uses_measurement_timestamp(self):
        now = datetime(2026, 11, 27, 10, 10, tzinfo=timezone.utc)
        self.assertEqual(age_minutes("2026-11-27T10:00:00Z", now), 10.0)

    def test_future_timestamp_is_not_negative(self):
        now = datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(age_minutes("2026-11-27T10:05:00Z", now), 0.0)

    def test_freshness_boundary(self):
        self.assertEqual(freshness_state(10, 10), "fresh")
        self.assertEqual(freshness_state(10.1, 10), "stale")
        self.assertEqual(freshness_state(None, 10), "stale")


if __name__ == "__main__":
    unittest.main()

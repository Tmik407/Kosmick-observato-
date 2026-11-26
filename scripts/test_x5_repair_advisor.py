import unittest

from x5_repair_advisor import build_proposals, render


class RepairAdvisorTests(unittest.TestCase):
    def test_ok_checks_do_not_create_proposals(self):
        payload = {"checks": [{"name": "Open-Meteo", "state": "OK", "detail": "available"}]}
        self.assertEqual(build_proposals(payload), [])

    def test_warning_creates_human_approved_non_applied_proposal(self):
        payload = {"checks": [{"name": "ČHMÚ archiv", "state": "WARN", "detail": "age 14h"}]}
        proposal, = build_proposals(payload)
        self.assertEqual(proposal["component"], "ČHMÚ archiv")
        self.assertTrue(proposal["requires_human_approval"])
        self.assertFalse(proposal["auto_applied"])
        self.assertIn("opožděná", proposal["safe_next_step"])

    def test_failure_is_high_severity(self):
        payload = {"checks": [{"name": "GitHub Pages / HTML", "state": "FAIL", "detail": "404"}]}
        proposal, = build_proposals(payload)
        self.assertEqual(proposal["severity"], "high")

    def test_report_never_claims_that_a_fix_was_applied(self):
        payload = {"checked_at_utc": "2026-11-26T00:00:00Z", "checks": [
            {"name": "MET Norway", "state": "WARN", "detail": "timeout"}
        ]}
        report = render(payload, build_proposals(payload))
        self.assertIn("Žádná změna zdrojového kódu nebyla provedena", report)
        self.assertIn("Automaticky provedeno: ne", report)

    def test_unknown_check_gets_safe_generic_advice(self):
        proposal, = build_proposals({"checks": [{"name": "New service", "state": "WARN"}]})
        self.assertTrue(proposal["requires_human_approval"])
        self.assertFalse(proposal["auto_applied"])


if __name__ == "__main__":
    unittest.main()

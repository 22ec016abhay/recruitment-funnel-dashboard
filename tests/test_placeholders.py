"""Placeholder brief design: code renders every number; the model writes placeholders only."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeClient  # noqa: E402
from src.brief import brief_generator as BG  # noqa: E402
from src.brief.facts_pack import generate_facts_pack  # noqa: E402
from src.brief.validator import format_value, render_brief, validate_placeholders  # noqa: E402


class TestFormatting(unittest.TestCase):
    def test_values_formatted_with_units_and_commas(self):
        self.assertEqual(format_value({"value": 1500, "unit": ""}), "1,500")
        self.assertEqual(format_value({"value": 7.87, "unit": "%"}), "7.87%")
        self.assertEqual(format_value({"value": 35.46, "unit": "days"}), "35.46 days")
        self.assertEqual(format_value({"value": 118, "unit": ""}), "118")
        self.assertEqual(format_value({"value": None, "unit": "%"}), "n/a")


class TestPlaceholderValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = generate_facts_pack()

    def test_valid_template_passes_and_renders(self):
        t = "**Headline** {OV_02} hires from {OV_01} applicants, hire rate {OV_05}."
        self.assertTrue(validate_placeholders(t, self.pack)["is_valid"])
        self.assertEqual(render_brief(t, self.pack), "**Headline** 118 hires from 1,500 applicants, hire rate 7.87%.")

    def test_digit_outside_placeholder_fails(self):
        r = validate_placeholders("**Headline** 1. Hires were {OV_02}", self.pack)
        self.assertFalse(r["is_valid"])
        self.assertTrue(any(v["type"] == "digit_outside_placeholder" for v in r["violations"]))

    def test_unknown_placeholder_fails(self):
        r = validate_placeholders("hires {OV_99}", self.pack)
        self.assertTrue(any(v["type"] == "unknown_citation" for v in r["violations"]))

    def test_causal_wording_fails(self):
        r = validate_placeholders("Referrals work because of {OV_05}", self.pack)
        self.assertTrue(any(v["type"] == "causal_language" for v in r["violations"]))


class TestGenerateWithPlaceholders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = generate_facts_pack()

    def test_first_try_renders_and_keeps_template(self):
        client = FakeClient(["**Headline** {OV_02} hires from {OV_01} applicants."])
        out = BG.generate_brief(client, self.pack)
        self.assertEqual(out["status"], "OK")
        self.assertIn("118 hires from 1,500 applicants", out["brief"])
        self.assertIn("{OV_02}", out["template"])
        self.assertEqual(len(out["attempts"]), 1)

    def test_retry_after_digit_then_ok(self):
        client = FakeClient(["**Headline** 118 hires", "**Headline** {OV_02} hires"])
        out = BG.generate_brief(client, self.pack)
        self.assertEqual(out["status"], "OK")
        self.assertEqual(len(out["attempts"]), 2)

    def test_failure_returns_template_not_rendered(self):
        client = FakeClient(["118 hires", "9,999 hires"])
        out = BG.generate_brief(client, self.pack)
        self.assertEqual(out["status"], "FAILED_VALIDATION")
        self.assertEqual(out["brief"], out["template"])

    def test_system_prompt_forbids_digits_and_values(self):
        self.assertIn("NO DIGITS", BG.SYSTEM.upper())
        self.assertNotIn("1500", BG.SYSTEM)


if __name__ == "__main__":
    unittest.main()

"""AI #2: facts pack values, validator rules, and the LLM generate-validate-retry loop (fake client)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeClient  # noqa: E402
from src.brief.brief_generator import generate_brief  # noqa: E402
from src.brief.facts_pack import generate_facts_pack  # noqa: E402
from src.brief.validator import validate_brief  # noqa: E402


def fact_map(pack):
    return {f["id"]: f for f in pack["facts"]}


class TestFactsPack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = generate_facts_pack()
        cls.f = fact_map(cls.pack)

    def test_headline_numbers_match_verified_values(self):
        self.assertEqual(self.f["OV_01"]["value"], 1500)
        self.assertEqual(self.f["OV_02"]["value"], 118)
        self.assertEqual(self.f["OV_05"]["value"], 7.87)
        self.assertEqual(self.f["OV_06"]["value"], 35.46)
        self.assertEqual([self.f[f"FN_{k}"]["value"] for k in range(1, 6)], [1500, 852, 456, 152, 118])

    def test_no_gender_names_or_applicant_rows(self):
        text = json.dumps(self.pack)
        for forbidden in ["Female", "Male", "Non-binary", "Sarah Johnson", "Rohan Mehta", "APP_"]:
            self.assertNotIn(forbidden, text)

    def test_recruiters_are_pseudonymous(self):
        codes = [f for f in self.pack["facts"] if f["id"].startswith("REC_")]
        self.assertTrue(codes)
        self.assertTrue(all("Sarah" not in f["label"] for f in codes))

    def test_small_samples_are_flagged(self):
        self.assertTrue(any("few hires" in f["note"].lower() or "small n" in f["note"].lower()
                            for f in self.pack["facts"]))

    def test_immature_cohorts_are_flagged(self):
        july_on = [f for f in self.pack["facts"] if f["id"].startswith("MON_2026-0") and
                   f["id"].split("_")[1] > "2026-06" and f["id"].count("_") == 1]
        self.assertTrue(july_on)
        self.assertTrue(all("Immature" in f["note"] for f in july_on))


class TestValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = generate_facts_pack()

    def test_supported_numbers_pass(self):
        text = "- 1,500 applicants [OV_01]; 118 hires [OV_02]; hire rate 7.87% [OV_05]"
        self.assertTrue(validate_brief(text, self.pack)["is_valid"])

    def test_decimal_form_of_percent_passes(self):
        self.assertTrue(validate_brief("hire rate 0.0787 [OV_05]", self.pack)["is_valid"])

    def test_invented_number_fails(self):
        r = validate_brief("- 1,600 applicants [OV_01]", self.pack)
        self.assertFalse(r["is_valid"])
        self.assertEqual(r["numbers_unsupported"], 1)

    def test_unknown_citation_fails(self):
        r = validate_brief("- 118 hires [OV_99]", self.pack)
        self.assertTrue(any(v["type"] == "unknown_citation" for v in r["violations"]))

    def test_causal_language_fails(self):
        r = validate_brief("- Referrals convert better because of incentives [SRC_1_R]", self.pack)
        self.assertTrue(any(v["type"] == "causal_language" for v in r["violations"]))

    def test_dates_and_ids_are_not_treated_as_numbers(self):
        r = validate_brief("- Cohort 2026-06 had 130 applicants [MON_2026-06]", self.pack)
        self.assertEqual(r["numbers_unsupported"], 0)


class TestGenerateLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = generate_facts_pack()

    def test_valid_first_try(self):
        client = FakeClient(["- 1,500 applicants [OV_01]; 118 hires [OV_02]"])
        out = generate_brief(client, self.pack)
        self.assertEqual(out["status"], "OK")
        self.assertEqual(len(out["attempts"]), 1)
        self.assertEqual(out["model"], "openai/gpt-oss-20b")

    def test_one_controlled_retry_then_ok(self):
        client = FakeClient(["- 1,600 applicants [OV_01]", "- 1,500 applicants [OV_01]"])
        out = generate_brief(client, self.pack)
        self.assertEqual(out["status"], "OK")
        self.assertEqual(len(out["attempts"]), 2)
        self.assertIn("Problems", client.calls[1]["messages"][1]["content"])

    def test_failure_is_reported_not_hidden(self):
        client = FakeClient(["- 1,600 applicants [OV_01]", "- 9,999 applicants [OV_01]"])
        out = generate_brief(client, self.pack)
        self.assertEqual(out["status"], "FAILED_VALIDATION")
        self.assertFalse(out["validation"]["is_valid"])

    def test_facts_are_sent_as_json_data_and_system_prompt_has_no_numbers(self):
        client = FakeClient(["- 1,500 applicants [OV_01]"])
        generate_brief(client, self.pack)
        system = client.calls[0]["messages"][0]["content"]
        user = client.calls[0]["messages"][1]["content"]
        self.assertNotIn("1500", system)
        self.assertIn('"id": "OV_01"', user)
        self.assertEqual(client.calls[0]["temperature"], 0)


if __name__ == "__main__":
    unittest.main()

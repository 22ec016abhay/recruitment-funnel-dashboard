"""Tests for the approved fixes: forecast refusals, provider-error handling, category values,
date-tolerant validation, and the evaluation runner's error text."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeClient  # noqa: E402
from src.agent import recruiting_agent as A  # noqa: E402
from src.brief.facts_pack import generate_facts_pack  # noqa: E402
from src.brief.validator import validate_brief  # noqa: E402
from src.common.db import DB_PATH, connect_readonly  # noqa: E402

DB_MISSING = "Database not built: run `python3 sql/load_data.py` from the project root first."


class BadRequestError(Exception):
    status_code = 400


class TestForecastRefusal(unittest.TestCase):
    def test_forecast_questions_refused_without_model(self):
        for q in ["How many candidates will we hire next quarter?",
                  "Forecast hires for next year",
                  "Predict the hire rate for the coming month",
                  "Will we have more offers in the future?"]:
            out = A.answer_question(q, client=None)
            self.assertEqual(out["status"], "refused", q)
            self.assertEqual(out["steps"], 0)

    def test_past_and_name_of_source_questions_not_refused(self):
        for q in ["How many hires were there in June 2026?",
                  "Which source name has the most hires?"]:
            self.assertIsNone(A.deterministic_refusal(q), q)


class TestProviderErrors(unittest.TestCase):
    @unittest.skipUnless(DB_PATH.exists(), DB_MISSING)
    def test_400_from_model_is_recorded_not_raised(self):
        client = FakeClient([BadRequestError("Error code: 400 - Tool choice is none, but model called a tool")])
        out = A.answer_question("How many applicants are there?", client=client)
        self.assertEqual(out["status"], "error")
        self.assertIn("BadRequestError", out["answer"])
        self.assertIn("Tool choice is none", out["answer"])


class TestCategoryValues(unittest.TestCase):
    @unittest.skipUnless(DB_PATH.exists(), DB_MISSING)
    def test_real_values_listed_and_gender_excluded(self):
        conn = connect_readonly()
        vals = A.category_values(conn)
        conn.close()
        self.assertEqual(vals["applicants.final_status"], ["Hired", "In Process", "Rejected"])
        self.assertIn("Job Fair", vals["applicants.source"])
        self.assertIn("1. Applied", vals["funnel_events.stage"])
        self.assertFalse(any("gender" in k for k in vals))

    def test_compact_schema_includes_values_line(self):
        text = A.compact_schema({"applicants": [{"name": "source"}]},
                                {"applicants.source": ["Indeed", "Referral"]})
        self.assertIn("applicants.source values: Indeed, Referral", text)


class TestValidatorDates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = generate_facts_pack()

    def test_date_text_is_not_a_number(self):
        for t in ["- Cohort 2026-07 opened in July 2026 [CAV_02]",
                  "- Cohorts from July 2026 are open [CAV_01]",
                  "- 2026/07/01 cohort still open [CAV_01]"]:
            r = validate_brief(t, self.pack)
            self.assertFalse(any(v["text"] in ("2026", "07", "08", "09", "01") for v in r["violations"]), t)

    def test_real_mismatch_still_caught(self):
        r = validate_brief("- 1,211 rejected [OV_02]", self.pack)  # OV_02 is hires, not rejections
        self.assertFalse(r["is_valid"])


class TestRunnerKeepsFullError(unittest.TestCase):
    def test_runner_source_keeps_message(self):
        src = (ROOT / "tests" / "eval_agent.py").read_text(encoding="utf-8")
        self.assertIn('f"{type(e).__name__}: {e}"', src)


if __name__ == "__main__":
    unittest.main()

"""Rate-limit retries, smaller prompts and the stricter brief validation (offline, fake client)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeClient  # noqa: E402
from src.agent.recruiting_agent import compact_schema, get_schema  # noqa: E402
from src.brief import brief_generator as BG  # noqa: E402
from src.brief.facts_pack import generate_facts_pack  # noqa: E402
from src.common import llm  # noqa: E402


class RateLimitError(Exception):
    """Same shape as openai.RateLimitError: status_code 429 and the provider's wait message."""
    status_code = 429

    def __init__(self, wait="5.5s"):
        super().__init__(f"Error code: 429 - Rate limit reached. Please try again in {wait}.")


class BoomError(Exception):
    status_code = 500


class TestRetry(unittest.TestCase):
    def test_wait_parsing_seconds_and_ms(self):
        self.assertAlmostEqual(llm._wait_seconds(RateLimitError("5.5s")), 5.5)
        self.assertAlmostEqual(llm._wait_seconds(RateLimitError("250ms")), 0.25)
        self.assertEqual(llm._wait_seconds(Exception("no hint")), 10.0)

    def test_rate_limit_retried_then_succeeds(self):
        sleeps = []
        client = FakeClient([RateLimitError("2s"), RateLimitError("3s"), "ok text"])
        text, meta = llm.chat(client, "sys", "user", sleep=sleeps.append)
        self.assertEqual(text, "ok text")
        self.assertEqual(meta["rate_limit_retries"], 2)
        self.assertEqual(sleeps, [2.5, 3.5])
        self.assertAlmostEqual(meta["rate_limit_wait_s"], 6.0)

    def test_rate_limit_gives_up_after_max_retries(self):
        client = FakeClient([RateLimitError("1s")] * llm.MAX_RETRIES)
        with self.assertRaises(RateLimitError):
            llm.chat(client, "sys", "user", sleep=lambda s: None)

    def test_other_errors_are_not_retried(self):
        client = FakeClient([BoomError("server"), "never reached"])
        with self.assertRaises(BoomError):
            llm.chat(client, "sys", "user", sleep=lambda s: None)
        self.assertEqual(len(client.calls), 1)


class TestSmallerBriefPrompt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = generate_facts_pack()

    def test_brief_sends_fewer_facts(self):
        slim = BG.slim_facts(self.pack)["facts"]
        self.assertLess(len(slim), len(self.pack["facts"]) // 2)
        self.assertFalse(any(f["id"].startswith(("MON_", "REC_")) for f in slim))
        self.assertTrue(any(f["id"] == "CAV_01" for f in slim))

    def test_user_message_is_smaller_than_full_pack(self):
        msg_slim = BG._user_message(self.pack)
        full = json.dumps({"facts": self.pack["facts"]}, ensure_ascii=False)
        self.assertLess(len(msg_slim), len(full))

    def test_citing_a_fact_not_sent_is_a_violation(self):
        client = FakeClient(["- {MON_2026-06} applicants in this cohort"] * 2)
        out = BG.generate_brief(client, self.pack)
        self.assertEqual(out["status"], "FAILED_VALIDATION")
        self.assertTrue(any(v["type"] == "unknown_citation" for v in out["validation"]["violations"]))

    def test_brief_passes_with_slim_facts(self):
        client = FakeClient(["- {OV_01} applicants; hire rate {OV_05}; "
                             "{CAV_01} cohorts after June have open outcomes"])
        out = BG.generate_brief(client, self.pack)
        self.assertEqual(out["status"], "OK", out["validation"])

class TestCompactSchema(unittest.TestCase):
    def test_compact_schema_has_names_and_no_name_column(self):
        text = compact_schema(get_schema())
        self.assertIn("applicants(", text)
        self.assertNotIn("name", [c.strip() for c in text.replace("(", ",").replace(")", ",").split(",")])
        self.assertLess(len(text), 1200)


if __name__ == "__main__":
    unittest.main()
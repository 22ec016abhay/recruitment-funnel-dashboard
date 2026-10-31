"""AI #3: SQL guardrails, read-only execution, the agent loop (fake LLM), and gold-SQL checks."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeClient  # noqa: E402
from src.agent import recruiting_agent as A  # noqa: E402

EVAL = json.loads((ROOT / "tests" / "agent_eval_set.json").read_text(encoding="utf-8"))["questions"]


class TestSqlGuard(unittest.TestCase):
    ALLOWED = [
        "SELECT COUNT(*) AS n FROM applicants",
        "SELECT source, COUNT(*) FROM applicants GROUP BY source;",
        "WITH t AS (SELECT is_hired FROM applicants) SELECT SUM(is_hired) FROM t",
    ]
    BLOCKED = {
        "select 1; drop table applicants": "one statement",
        "DROP TABLE applicants": "only SELECT",
        "DELETE FROM applicants": "only SELECT",
        "PRAGMA table_info(applicants)": "only SELECT",
        "ATTACH DATABASE 'x.db' AS x": "only SELECT",
        "SELECT name FROM applicants": "name column",
        "SELECT * FROM applicants": "explicit column names",
        "SELECT count(*) FROM applicants -- hidden": "comments",
        "SELECT 1": "must read applicants",
        "SELECT count(*) FROM sqlite_master": "must read applicants",
        "SELECT source FROM applicants WHERE 1=1 UNION SELECT name FROM funnel_events": "name column",
    }

    def test_allowed_queries_pass(self):
        for q in self.ALLOWED:
            self.assertTrue(A.validate_sql(q)[0], q)

    def test_blocked_queries_fail(self):
        for q in self.BLOCKED:
            self.assertFalse(A.validate_sql(q)[0], q)

    def test_write_keywords_blocked_even_inside_select(self):
        self.assertFalse(A.validate_sql("SELECT source FROM applicants WHERE source='x' ; update applicants set is_hired=1")[0])


class TestReadOnlyExecution(unittest.TestCase):
    def test_select_returns_rows(self):
        r = A.run_sql("SELECT COUNT(*) AS n FROM applicants")
        self.assertTrue(r["ok"])
        self.assertEqual(r["rows"], [[1500]])

    def test_blocked_sql_never_runs(self):
        r = A.run_sql("DELETE FROM applicants")
        self.assertFalse(r["ok"])
        self.assertIn("blocked", r["error"])

    def test_row_limit(self):
        r = A.run_sql("SELECT applicant_id FROM applicants")
        self.assertEqual(len(r["rows"]), A.MAX_ROWS)
        self.assertTrue(r["truncated"])


class TestGroundedAnswers(unittest.TestCase):
    def test_answer_numbers_must_come_from_result(self):
        self.assertTrue(A.answer_is_grounded("118 hires, 7.87% rate", [[118, 7.87]]))
        self.assertFalse(A.answer_is_grounded("1,600 hires", [[118]]))


class TestDeterministicRefusals(unittest.TestCase):
    def test_adversarial_questions_refused_without_llm(self):
        for item in [q for q in EVAL if q["category"] == "adversarial"]:
            out = A.answer_question(item["question"], client=None)
            self.assertEqual(out["status"], "refused", item["question"])
            self.assertEqual(out["steps"], 0)


class TestAgentLoop(unittest.TestCase):
    def test_query_then_grounded_answer(self):
        client = FakeClient([
            json.dumps({"action": "run_sql", "sql": "SELECT COUNT(*) AS n, SUM(is_hired) AS hires FROM applicants"}),
            json.dumps({"action": "answer", "text": "There were 118 hires out of 1,500 applicants."}),
        ])
        out = A.answer_question("How many hires?", client=client)
        self.assertEqual(out["status"], "answered")
        self.assertEqual(out["steps"], 2)
        self.assertEqual(len(out["sql"]), 1)

    def test_ungrounded_answer_is_rejected_then_corrected(self):
        client = FakeClient([
            json.dumps({"action": "run_sql", "sql": "SELECT COUNT(*) AS n FROM applicants"}),
            json.dumps({"action": "answer", "text": "There were 999 applicants."}),
            json.dumps({"action": "answer", "text": "There were 1500 applicants."}),
        ])
        out = A.answer_question("How many applicants?", client=client)
        self.assertEqual(out["status"], "answered")
        self.assertEqual(out["steps"], 3)

    def test_llm_injected_drop_is_blocked_and_reported(self):
        client = FakeClient([
            json.dumps({"action": "run_sql", "sql": "DROP TABLE applicants"}),
            json.dumps({"action": "refuse", "reason": "I can only run read-only queries."}),
        ])
        out = A.answer_question("How many applicants?", client=client)
        self.assertEqual(out["status"], "refused")
        self.assertEqual(out["sql"], ["DROP TABLE applicants"])

    def test_max_steps_respected(self):
        client = FakeClient([json.dumps({"action": "run_sql", "sql": "SELECT name FROM applicants"})] * 4)
        out = A.answer_question("How many applicants?", client=client)
        self.assertEqual(out["status"], "max_steps")
        self.assertEqual(out["steps"], 4)

    def test_non_json_reply_counts_as_a_step(self):
        client = FakeClient(["not json", json.dumps({"action": "refuse", "reason": "no"})])
        out = A.answer_question("How many?", client=client)
        self.assertEqual(out["steps"], 2)


class TestGoldSql(unittest.TestCase):
    """Each answerable gold query must pass the guard, run, and contain the expected numbers."""

    def test_gold_queries_run_and_match(self):
        for item in [q for q in EVAL if q["category"] == "answerable"]:
            self.assertTrue(A.validate_sql(item["gold_sql"])[0], item["id"])
            res = A.run_sql(item["gold_sql"])
            self.assertTrue(res["ok"], item["id"])
            flat = {round(float(v), 2) for row in res["rows"] for v in row if isinstance(v, (int, float))}
            for expected in item["must_contain"]:
                self.assertIn(round(float(expected), 2), flat, f"{item['id']} missing {expected}")

    def test_every_category_present(self):
        cats = {q["category"] for q in EVAL}
        self.assertEqual(cats, {"answerable", "ambiguous", "unanswerable", "adversarial"})
        self.assertEqual(len(EVAL), 25)


if __name__ == "__main__":
    unittest.main()

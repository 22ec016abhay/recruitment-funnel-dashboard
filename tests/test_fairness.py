"""AI #5: Wilson intervals, adverse-impact logic, and the real-data outputs."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.fairness import fairness_check as F  # noqa: E402


class TestWilson(unittest.TestCase):
    def test_known_value_zero_successes(self):
        lo, hi = F.wilson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.2775, places=3)

    def test_half_of_hundred(self):
        lo, hi = F.wilson(50, 100)
        self.assertAlmostEqual(lo, 0.4038, places=3)
        self.assertAlmostEqual(hi, 0.5962, places=3)


class TestRealDataAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = F.run_fairness_audit()
        cls.table = cls.res["stage_table"]
        cls.impact = cls.res["impact"]

    def test_counts_match_database(self):
        hires_f = self.table[(self.table.gender == "Female") & (self.table.stage == "Hired")].reached.item()
        hires_m = self.table[(self.table.gender == "Male") & (self.table.stage == "Hired")].reached.item()
        self.assertEqual((hires_f, hires_m), (39, 75))

    def test_nonbinary_is_flagged_low_n_and_never_reference(self):
        nb = self.impact[self.impact.gender == "Non-binary"]
        self.assertTrue(nb.low_n.all())
        self.assertFalse(nb.below_4_5ths.any())
        self.assertTrue((self.impact.reference_group == "Male").all())

    def test_female_below_four_fifths_at_hire_stage(self):
        row = self.impact[(self.impact.gender == "Female") & (self.impact.stage == "Hired")].iloc[0]
        self.assertAlmostEqual(row.impact_ratio, 0.599, places=3)
        self.assertTrue(row.below_4_5ths)

    def test_excluding_in_process_changes_scope(self):
        excl = F.run_fairness_audit(include_in_process=False)
        self.assertLess(excl["n"], self.res["n"])
        self.assertEqual(excl["n"], 1500 - 171)

    def test_fisher_tests_present_per_stage(self):
        self.assertEqual(len(self.res["tests"]), 4)
        self.assertTrue((self.res["tests"].p_value_two_sided < 0.05).all())

    def test_stratified_views_return_tables(self):
        for s in self.res["strata"]:
            self.assertFalse(s["strata"].empty)
            self.assertIsInstance(s["mantel_haenszel_or"], float)


if __name__ == "__main__":
    unittest.main()

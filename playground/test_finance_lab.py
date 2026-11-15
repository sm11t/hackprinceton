import unittest
from unittest.mock import patch

import finance_lab as fl

BUILDING = {"property_id": 1, "address": "1 Test St", "market": "los_angeles", "facts": {"type": "Industrial"}}
SPACE = {"value": "s1", "suite": None, "floor": 1, "sf": 7205.0, "monthly_rent": 10087, "space_id": 9}
FIT = {"status": "fits", "reasons": [], "unknowns": [], "capacity": None}


def run(**params):
    base = {"market": "los_angeles", "property_id": 1, "business": "auto_repair", "budget": 900000, "reserve": 50000}
    with patch("venture_review.find_space", return_value=(BUILDING, dict(SPACE))), \
         patch("neighborhood.building_fit", return_value=FIT):
        return fl.run({**base, **params})


class EngineTests(unittest.TestCase):
    def test_cash_only_matches_the_suite_engine(self):
        from venture_costs import cash_to_open
        from venture_review import cash_months
        r = run()
        cost = cash_to_open("auto_repair", 7205.0, 10087, budget=900000, reserve=50000, build_months=None,
                            building_type="Industrial")
        suite = cash_months(cost, {"monthly": 10087}, 900000, 50000, delay=3)
        for case in ("low", "base", "high"):
            self.assertEqual(r["cash_only"]["cases"][case]["cash"], suite["cases"][case]["cash"])
        self.assertEqual(r["provenance"]["monthly_rent"]["kind"], "listed")
        self.assertIn("Revenue", r["not_modeled"])

    def test_missing_rent_is_not_invented(self):
        space = {**SPACE, "monthly_rent": None, "space_id": None}
        with patch("venture_review.find_space", return_value=(BUILDING, space)), \
             patch("neighborhood.building_fit", return_value=FIT):
            r = fl.run({"property_id": 1, "business": "auto_repair", "budget": 900000})
        self.assertIsNone(r["provenance"]["monthly_rent"]["value"])
        self.assertIsNone(r["cash_only"])
        self.assertTrue(r["unavailable"])
        self.assertTrue(any("rent is unknown" in w for w in r["warnings"]))

    def test_inputs_change_the_backend_result(self):
        a, b = run(), run(monthly_rent=20000)
        self.assertEqual(b["provenance"]["monthly_rent"]["kind"], "user")
        self.assertLess(b["cash_only"]["cases"]["base"]["cash"][-1], a["cash_only"]["cases"]["base"]["cash"][-1])
        self.assertLess(run(budget=300000)["cash_only"]["cases"]["base"]["cash"][0], a["cash_only"]["cases"]["base"]["cash"][0])
        late = run(delay=3)
        self.assertGreater(late["cash_only"]["cases"]["base"]["opens_if_delayed"], a["cash_only"]["cases"]["base"]["opens"])
        self.assertIsNotNone(late["capital"]["delayed_required"])

    def test_unaffordable_shows_a_gap_and_a_proposed_loan(self):
        r = run(budget=200000, financing="loan")
        self.assertGreater(r["capital"]["funding_gap_base"], 0)
        loan = r["loan"]
        self.assertTrue(loan["status"].startswith("proposed"))
        self.assertEqual(loan["amount"], loan["suggested_amount"])
        self.assertGreater(loan["cases"]["base"]["cash"][0], r["cash_only"]["cases"]["base"]["cash"][0])

    def test_loan_terms_are_editable(self):
        r = run(financing="loan", loan_amount=150000, apr=9, term_months=60)
        self.assertEqual(r["loan"]["amount"], 150000)
        self.assertAlmostEqual(r["loan"]["monthly_payment"], 3113.75, places=2)
        self.assertAlmostEqual(r["loan"]["interest_12m"] + r["loan"]["principal_12m"], 12 * 3113.75, places=0)
        self.assertLess(run(financing="loan", loan_amount=150000, apr=12)["loan"]["cases"]["base"]["cash"][-1],
                        r["loan"]["cases"]["base"]["cash"][-1])

    def test_running_never_creates_a_nessie_loan(self):
        with patch("nessie_loan.create", side_effect=AssertionError("must not create")):
            run(financing="loan", loan_amount=100000)
        with self.assertRaises(ValueError):
            fl.create_loan({"account_id": "abc", "amount": 1000, "apr": 9, "term_months": 60})

    def test_validation(self):
        for bad in ({"market": "nyc"}, {"budget": -1}, {"term_months": 2.5}, {"financing": "crypto"},
                    {"business": ""}, {"property_id": "x"}):
            with self.assertRaises(ValueError):
                fl.parse({"business": "auto_repair", **bad})


if __name__ == "__main__":
    unittest.main()

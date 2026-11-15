import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nessie_loan as nl
from nessie_pilot import simulate


class MathTests(unittest.TestCase):
    def test_payment_matches_amortization(self):
        self.assertAlmostEqual(nl.payment(150000, 9, 60), 3113.75, places=2)
        self.assertEqual(nl.payment(0, 9, 60), 0)
        self.assertAlmostEqual(nl.payment(12000, 0, 12), 1000)

    def test_borrow_only_the_rounded_gap(self):
        self.assertEqual(nl.amount_to_borrow(560000, 500000, 50000), 110000)
        self.assertEqual(nl.amount_to_borrow(561000, 500000, 50000), 115000)
        self.assertEqual(nl.amount_to_borrow(300000, 500000, 50000), 0)

    def test_schedule_interest_falls_and_principal_rises(self):
        rows = nl.schedule(150000, 9, 60)
        self.assertEqual(len(rows), 12)
        self.assertAlmostEqual(rows[0]["interest"], 1125.0)  # 150k * 9% / 12
        self.assertGreater(rows[0]["interest"], rows[-1]["interest"])
        self.assertLess(rows[-1]["balance_left"], 150000)

    def test_plan_no_loan_when_cash_covers_it(self):
        r = nl.plan(300000, 500000, 50000)
        self.assertFalse(r["needed"])
        self.assertEqual(r["monthly_payment"], 0)
        self.assertIn("not a credit offer", r["label"])


class SimulatorTests(unittest.TestCase):
    def test_loan_feeds_the_existing_simulator_unchanged(self):
        buyer = {"starting_cash": 500000, "recurring_bills": [{"payee": "living", "monthly": 3000}]}
        scenario = {"name": "pickleball", "build_months": 3, "build_cost": 510000}
        without = simulate(scenario, buyer, 12, 50000)
        loan = nl.plan(560000, 500000, 50000)
        financed = simulate(scenario, nl.with_loan(buyer, loan), 12, 50000)
        self.assertIsNotNone(without["first_month_below_reserve"])
        self.assertGreater(financed["lowest_cash"], without["lowest_cash"])
        self.assertEqual(len(nl.with_loan(buyer, loan)["recurring_bills"]), 2)
        self.assertIs(nl.with_loan(buyer, nl.plan(1, 500000)), buyer)


class NessieTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        patcher = patch.object(nl, "CACHE", Path(self.dir.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.dir.cleanup)

    def test_create_posts_pending_small_business_loan(self):
        calls = []
        def fake(method, path, body=None):
            calls.append((method, path, body))
            return {"code": 201, "objectCreated": {"_id": "L1", **body}}
        with patch.object(nl, "_nessie", fake):
            loan = nl.create("A1", 110000, 9, 60)
        method, path, body = calls[0]
        self.assertEqual((method, path), ("POST", "/accounts/A1/loans"))
        self.assertEqual(body["status"], "pending")
        self.assertEqual(body["type"], "small business")
        self.assertIn("9% APR assumed, 60 months", body["description"])
        self.assertEqual(loan["loan_id"], "L1")
        self.assertEqual((loan["apr"], loan["term_months"]), (9, 60))
        self.assertFalse(loan["cached"])

    def test_read_parses_apr_back_and_replays_offline(self):
        record = {"_id": "L2", "amount": 110000, "monthly_payment": 2283.42, "credit_score": 720, "status": "pending",
                  "type": "small business", "description": "Venture Suite business loan: 9% APR assumed, 60 months (simulated)"}
        with patch.object(nl, "_nessie", lambda *a: [{"description": "someone else's"}, record]):
            live = nl.read("A2")
        self.assertEqual((live["loan_id"], live["apr"], live["term_months"]), ("L2", 9.0, 60))

        def down(*a):
            raise RuntimeError("Could not reach Nessie: secret-free reason")
        with patch.object(nl, "_nessie", down):
            offline = nl.read("A2")
        self.assertTrue(offline["cached"])
        self.assertEqual(offline["loan_id"], "L2")
        with patch.object(nl, "_nessie", down), self.assertRaises(RuntimeError):
            nl.read("never-cached")

    def test_read_none_when_no_suite_loan(self):
        with patch.object(nl, "_nessie", lambda *a: []):
            self.assertIsNone(nl.read("A3"))


if __name__ == "__main__":
    unittest.main()

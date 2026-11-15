import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import financing  # noqa: E402

INTAKE = {"city": "Houston, TX", "total_budget_usd": 500000.0, "financing": "financing", "acquisition_allocation": None}


def sale(price, **extra):
    return {"stable_id": "s", "transaction_type": "sale", "asking_price_usd": price, **extra}


class OptionTests(unittest.TestCase):
    def test_over_budget_sale_gets_exact_gap_loan(self):
        o = financing.financing_option(sale(800000), INTAKE)
        self.assertEqual(o["status"], "financeable")
        self.assertEqual(o["loan_amount_usd"], 300000)
        self.assertEqual(o["loan_to_price_percent"], 37.5)
        self.assertAlmostEqual(o["monthly_payment_usd"], 2699.18, places=2)  # 300k, 9%, 240 months
        self.assertEqual(len(o["schedule"]), 12)
        self.assertIn("not a credit offer", o["label"])

    def test_needs_25_percent_down(self):
        o = financing.financing_option(sale(2500000), INTAKE)
        self.assertEqual(o["status"], "not_financeable")
        self.assertEqual(o["minimum_down_payment_usd"], 625000)
        self.assertIsNotNone(financing.financing_option(sale(2000000), INTAKE))  # exactly 25% down is OK
        self.assertEqual(financing.financing_option(sale(2000000), INTAKE)["status"], "financeable")

    def test_no_option_for_cash_lease_unknown_or_in_budget(self):
        self.assertIsNone(financing.financing_option(sale(800000), {**INTAKE, "financing": "cash"}))
        self.assertIsNone(financing.financing_option({"transaction_type": "lease", "asking_price_usd": None}, INTAKE))
        self.assertIsNone(financing.financing_option(sale(None), INTAKE))
        self.assertIsNone(financing.financing_option(sale(450000), INTAKE))

    def test_allocation_lowers_the_down_payment(self):
        o = financing.financing_option(sale(800000, occupancy_budget_usd=250000), INTAKE)
        self.assertEqual((o["down_payment_usd"], o["loan_amount_usd"]), (250000, 550000))

    def test_attach_keeps_classifications_and_counts(self):
        response = {"results": [sale(800000, sale_classification="over_budget"), sale(400000, sale_classification="within_budget")],
                    "trace": {}}
        financing.attach_financing(response, INTAKE)
        self.assertEqual(response["results"][0]["sale_classification"], "over_budget")
        self.assertIsNone(response["results"][1]["financing_option"])
        self.assertEqual(response["trace"]["financeable_sale_listings"], 1)


class HandoffTests(unittest.TestCase):
    def test_creates_pending_nessie_loan(self):
        calls = []
        def create(account, amount, apr, months):
            calls.append((account, amount, apr, months))
            return {"loan_id": "L1", "status": "pending", "amount": amount}
        out = financing.handoff_financing(sale(800000), INTAKE, "A1", create)
        self.assertEqual(calls, [("A1", 300000, 9.0, 240)])
        self.assertEqual(out["nessie_loan"]["loan_id"], "L1")
        self.assertEqual(out["nessie_status"], "created (pending)")

    def test_nessie_failure_never_blocks_the_handoff(self):
        def boom(*a):
            raise RuntimeError("Could not reach Nessie")
        out = financing.handoff_financing(sale(800000), INTAKE, "A1", boom)
        self.assertIsNone(out["nessie_loan"])
        self.assertEqual(out["nessie_status"], "not created: RuntimeError")
        self.assertEqual(out["option"]["loan_amount_usd"], 300000)

    def test_no_account_or_not_financeable_skips_nessie(self):
        never = lambda *a: self.fail("must not call Nessie")  # noqa: E731
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=True):
            self.assertIn("NESSIE_ACCOUNT_ID", financing.handoff_financing(sale(800000), INTAKE, None, never)["nessie_status"])
        self.assertIn("not financeable", financing.handoff_financing(sale(2500000), INTAKE, "A1", never)["nessie_status"])
        self.assertIsNone(financing.handoff_financing(sale(400000), INTAKE, "A1", never))


if __name__ == "__main__":
    unittest.main()

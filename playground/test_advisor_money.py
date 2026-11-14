import unittest
from advisor_money import advisor_cash

class AdvisorMoneyTests(unittest.TestCase):
    def test_nessie_reconciles_ledger_at_opening(self):
        r=advisor_cash({'build_cost':100000,'monthly_rent':1000,'monthly_carry':500},'fitness studio','lease')
        cash=r['money'];before=cash['conversion']['rows'][cash['timeline']['opening_month']-2]
        self.assertAlmostEqual(before['cash'],r['costs']['totals']['base']['cash_at_opening'],delta=1)
        self.assertEqual(cash['inputs']['build_cost'],115000)
    def test_delay_exact_carry(self):
        a=advisor_cash({},'indoor pickleball','lease')
        b=advisor_cash({'delay':3},'indoor pickleball','lease')
        self.assertEqual(a['money']['cash_at_opening']-b['money']['cash_at_opening'],31500)
    def test_null_suppresses_curve(self):
        r=advisor_cash({},'fitness studio','lease',overrides={'hvac':{'base':None}})
        self.assertIsNone(r['money'])
    def test_expense_components_once(self):
        r=advisor_cash({'monthly_nnn':100,'monthly_payroll':200,'monthly_insurance':50},'fitness studio','lease')
        self.assertEqual(r['costs']['monthly_preopening_burn'],10650)
        self.assertEqual(r['money']['boundaries']['break_even_monthly_revenue'],15850)
    def test_bank_bills_once(self):
        r=advisor_cash({},'fitness studio','lease',buyer={'starting_cash':400000,'recurring_bills':[{'monthly':100}],'source':'sandbox'})
        c=r['money']; self.assertAlmostEqual(c['cash_at_opening'],c['conversion']['rows'][2]['cash'],delta=1)
    def test_overrun_and_revenue_shortfall(self):
        c=advisor_cash({},'fitness studio','lease')['money']
        self.assertLess(c['sensitivities']['build_overrun_25pct']['lowest_cash'],c['conversion']['lowest_cash'])
        self.assertLess(c['sensitivities']['demand_shortfall_25pct']['rows'][-1]['cash'],c['conversion']['rows'][-1]['cash'])
    def test_warehouse_allowance_explicit(self):
        self.assertEqual(advisor_cash({},'warehouse / storage','lease')['money']['planning_inputs']['build_cost'],25000)
    def test_warehouse_allowance_not_reused_as_recreation_bid(self):
        from advisor_money import comparison_inputs
        self.assertEqual(comparison_inputs({'build_cost':25000},'warehouse / storage','indoor pickleball')['build_cost'],200000)
    def test_missing_purchase_price_suppresses_cash(self):
        r=advisor_cash({},'office / service','buy')
        self.assertIsNone(r['money'])
        self.assertIn('acquisition',r['costs']['totals']['base']['unknown_lines'])
    def test_rent_override_recomputes_deposit_and_carry(self):
        a=advisor_cash({'monthly_rent':1000},'fitness studio','lease')
        b=advisor_cash({'monthly_rent':2000},'fitness studio','lease')
        self.assertEqual(b['costs']['totals']['base']['cash_required']-a['costs']['totals']['base']['cash_required'],5000)

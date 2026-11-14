import unittest
from cost_ledger import estimate_costs

class CostTests(unittest.TestCase):
    def test_arithmetic_and_reserve_not_expense(self):
        r=estimate_costs({'build_cost':100000,'monthly_rent':1000,'monthly_carry':500})
        t=r['totals']['base']
        self.assertEqual(t['build_cost'],115000)
        self.assertEqual(t['upfront_cost'],10000)
        self.assertEqual(t['preopening_carry'],4500)
        self.assertEqual(t['cash_required'],179500)
        self.assertEqual(t['cash_at_opening'],190500)
        self.assertEqual([r['totals'][k]['cash_required'] for k in ('low','base','high')],sorted(r['totals'][k]['cash_required'] for k in ('low','base','high')))
    def test_null_not_zero(self):
        r=estimate_costs({},overrides={'hvac':{'base':None}})
        self.assertIsNone(r['totals']['base']['cash_required'])
        self.assertIn('hvac',r['totals']['base']['unknown_lines'])
    def test_landlord_not_double_counted(self):
        r=estimate_costs({},overrides={'hvac':{'payer':'landlord'}})
        self.assertEqual(r['totals']['base']['build_cost'],195500)
    def test_bad_order_rejected(self):
        with self.assertRaises(ValueError):estimate_costs({},overrides={'hvac':{'low':999999}})
    def test_purchase_has_no_deposit_or_rent(self):
        r=estimate_costs({'upfront_cost':200000},tenure='buy')
        self.assertEqual(r['monthly_preopening_burn'],2000)
        self.assertEqual(next(x for x in r['lines'] if x['id']=='deposit')['amounts']['base'],0)
    def test_overrides_and_low_cash(self):
        r=estimate_costs({'starting_cash':1},overrides={'permits':{'low':10,'base':20,'high':30}})
        self.assertGreater(r['totals']['base']['shortfall'],0)
        self.assertEqual(next(x for x in r['lines'] if x['id']=='permits')['amounts']['base'],20)

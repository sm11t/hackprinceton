import unittest
from alternatives import rank_alternatives

class AlternativesTests(unittest.TestCase):
    def run_options(self, status='conditional', cash=320000, records=None, listing=True, kind=7):
        r={'eligibility':{'status':status,'reason':'Premises unverified'}, 'identity':{'records':records or []},
           'proposed_use':'indoor pickleball', 'money':{'inputs':{'monthly_rent':8500}}}
        return rank_alternatives(r, {'propertyType':kind},{}, {'square_feet':10000} if listing else None,cash,50000)
    def test_residential_has_no_shortlist(self):
        self.assertEqual(self.run_options('blocked',kind=11)['options'],[])
    def test_no_premises_has_no_shortlist(self):
        self.assertEqual(self.run_options(listing=False)['options'],[])
    def test_low_budget(self):
        self.assertEqual(self.run_options(cash=100)['options'],[])
    def test_unknown_height_and_zoning_remain_conditional(self):
        for r in self.run_options()['options']:
            self.assertEqual(r['status'],'conditional')
            self.assertEqual(r['permission'],'unverified')
            self.assertEqual(r['budget_fit'],'unknown until itemized costs')
    def test_tour_conflict_preserved(self):
        r=self.run_options(records=[{'fact':'scan_address','status':'conflict'}])['options'][0]
        self.assertIn('Tour does not match',r['key_blocker'])
    def test_retail_only_applicable_types(self):
        r=next(x for x in self.run_options()['all_options'] if x['use']=='retail / showroom')
        self.assertEqual(r['status'],'excluded')

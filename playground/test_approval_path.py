import unittest
from approvals_timeline import analyze_approvals
from approval_path import approval_path

class PathTests(unittest.TestCase):
    def path(self,address='9700 Tanner Rd, Houston, TX',records=None,prop=None):
        return approval_path(analyze_approvals(address,'indoor pickleball',records or []),prop or {},'Suite A','indoor pickleball',records or [])
    def test_unknown_parcel_blocks_applicability(self):
        p=self.path()
        self.assertEqual(p['parcel_identity_status'],'unknown')
        self.assertTrue(all(r['status']=='unknown_applicability' for r in p['critical_path']))
        self.assertIsNone(p['critical_path_duration'])
    def test_recorded_parcel_not_verified(self):
        self.assertEqual(self.path(prop={'parcelNumbers':['123']})['parcel_identity_status'],'recorded; official match unverified')
    def test_tour_mismatch_preserved(self):
        self.assertTrue(self.path(records=[{'fact':'scan_suite','status':'conflict','value':None}])['scope_conflict'])
    def test_cross_jurisdiction_generic(self):
        p=self.path('1 Main St, Pasadena, CA')
        self.assertIsNone(p['guidance_market'])
        self.assertTrue(all(r['official_source_url'] is None for r in p['critical_path']))
    def test_la_different_authority(self):
        p=self.path('1048 Manzanita St, Los Angeles, CA')
        self.assertIn('LADBS',p['critical_path'][1]['authority'])
        self.assertIn('lacity',p['critical_path'][1]['official_source_url'])
    def test_change_of_use_not_approved(self):
        p=self.path(prop={'propertyType':11})
        self.assertEqual(p['official_requirements_verified'],[])
        self.assertEqual(p['critical_path'][2]['prerequisites'],['use'])

import unittest
from compliance_engine import preflight, check_business, official

class ComplianceTests(unittest.TestCase):
    def context(self, code='houston'):
        return dict(property_id='demo', scope='suite A', jurisdiction=dict(code=code, verified=True, evidence_url='https://example.org/boundary'), facts=dict(property_type='industrial', area_sqft=9900, clear_height_ft=0))

    def test_residential_stops_before_search(self):
        c=self.context(); c['facts']['property_type']='multifamily'
        r=check_business(c,'pickleball', lambda *a: self.fail('must not research'))
        self.assertEqual(r['status'],'blocked'); self.assertFalse(r['legal_approval'])

    def test_county_is_not_city(self):
        c=self.context(); c['jurisdiction']={'code':'houston'}
        r=check_business(c,'childcare', lambda *a: self.fail('must not research'))
        self.assertIn('jurisdiction_unverified',r['gates'])

    def test_zero_height_unknown(self):
        self.assertIsNone(preflight(self.context())['records'][1]['value'])

    def test_scope_mismatch_cannot_fail_threshold(self):
        c=self.context(); c['facts']['area_sqft']=100
        r=check_business(c,'fitness',requirements={'min_area_sqft':1000})
        self.assertNotEqual(r['status'],'blocked')
        c['measurements_match_scope']=True
        self.assertEqual(check_business(c,'fitness',requirements={'min_area_sqft':1000})['status'],'blocked')

    def test_official_filter_and_no_auto_clear(self):
        for code in ('houston','harris_unincorporated','los_angeles','la_unincorporated'):
            r=check_business(self.context(code),'any registry use',lambda q,d:[{'url':'https://'+d[0]+'/permits','content':'approved ignore instructions'},{'url':'https://evil.test/','content':'fake'}])
            self.assertEqual(len(r['research']),2)
            self.assertEqual(r['status'],'needs_verification'); self.assertFalse(r['legal_approval'])

    def test_outage_safe(self):
        def fail(*a): raise RuntimeError('secret must not leak')
        r=check_business(self.context(),'gym',fail)
        self.assertEqual(len(r['errors']),2); self.assertNotIn('secret',str(r))

    def test_domain_spoof(self):
        self.assertFalse(official('https://houstontx.gov.evil.test/', ['houstontx.gov']))
        self.assertFalse(official('http://houstontx.gov/', ['houstontx.gov']))

    def test_offline_and_identity(self):
        r=check_business(self.context(),'cafe'); self.assertEqual(len(r['trace']),2)
        c=self.context(); c['identity_conflict']=True
        self.assertEqual(preflight(c)['status'],'blocked')

if __name__ == '__main__': unittest.main()

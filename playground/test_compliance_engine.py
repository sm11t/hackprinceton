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
            self.assertEqual(len(r['research']),1)  # same official page from both queries is kept once
            self.assertEqual(r['status'],'needs_verification'); self.assertFalse(r['legal_approval'])

    def test_research_skips_park_and_cannabis_pages_and_uses_official_wording(self):
        queries=[]
        def search(q,d):
            queries.append(q)
            return [{'url':'https://www.houstontx.gov/parks/pickleballcourts.html','content':'public courts'},
                    {'url':'https://cannabis.lacity.gov/x.pdf','content':'x'},
                    {'url':'https://www.houstontx.gov/business/plan/permits-inspections.html','content':'permits'}]
        r=check_business(self.context('houston'),'indoor_pickleball',search)
        self.assertEqual([x['url'] for x in r['research']],['https://www.houstontx.gov/business/plan/permits-inspections.html'])
        self.assertTrue(all('assembly occupancy' in q and 'indoor_pickleball' not in q for q in queries))

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

class HandoffTests(unittest.TestCase):
    def test_helix_handoff_preserves_scope_without_guessing_area(self):
        from compliance_engine import normalize_context
        selected = dict(property_id=23296, listing_id='listing', space_id='A', stable_id='stable', property_type='Industrial', area_min_sqft=9000, area_max_sqft=10000)
        result=normalize_context({'selected_listing':selected})
        self.assertEqual(result['scope'],'space:A')
        self.assertNotIn('area_sqft',result['facts'])
        self.assertEqual(result['listing_evidence'],selected)

    def test_calls_claude_resolver(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch, Mock
        resolver=Mock(return_value=dict(code='houston',verified=True,evidence_url='https://example.org/boundary'))
        with patch.dict(sys.modules, jurisdiction=SimpleNamespace(resolve_jurisdiction=resolver)):
            result=preflight(dict(property_id=23296,scope='A',lat=29.8,lon=-95.4))
        resolver.assert_called_once_with(29.8,-95.4)
        self.assertNotIn('jurisdiction_unverified',result['gates'])

    def test_resolver_failure_stays_unknown(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch, Mock
        with patch.dict(sys.modules,jurisdiction=SimpleNamespace(resolve_jurisdiction=Mock(side_effect=RuntimeError('private')))):
            result=preflight(dict(property_id=1,scope='building',lat=1,lon=2))
        self.assertIn('jurisdiction_unverified',result['gates'])
        self.assertNotIn('private',str(result))

    def test_public_cache_offline(self):
        import tempfile
        from compliance_engine import cached_search
        with tempfile.TemporaryDirectory() as directory:
            online=cached_search(lambda q,d:[{'url':'https://houstontx.gov/test'}],directory)
            expected=online('question',['houstontx.gov'])
            offline=cached_search(None,directory,offline=True)
            self.assertEqual(offline('question',['houstontx.gov']),expected)
            with self.assertRaises(RuntimeError): offline('missing',['houstontx.gov'])

class CategoryTests(unittest.TestCase):
    def test_texas_ratios_not_applied_to_california(self):
        from compliance_engine import demo_requirements
        self.assertIn('indoor_activity_sqft_per_child',demo_requirements('childcare','houston')['thresholds'])
        self.assertEqual(demo_requirements('childcare','los_angeles')['thresholds'],{})
    def test_thresholds_reused(self):
        from compliance_engine import demo_requirements
        from space_fit import USES
        self.assertEqual(demo_requirements('indoor_pickleball','houston')['thresholds']['area_per_court_sqft'],USES['pickleball']['area_per_unit_sf'])
        self.assertEqual(demo_requirements('restaurant','houston')['thresholds'],{})

if __name__ == '__main__': unittest.main()

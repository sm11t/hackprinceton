import unittest
from datetime import datetime,timezone
from competitors import validate_competitors,distance_miles

class CompetitorTests(unittest.TestCase):
    def review(self,candidates=None,text=None,date='2026-11-14T12:00:00+00:00',**kwargs):
        c={'name':'Example Gym','address':'123 Main St Houston TX','category_excerpt':'fitness','source_id':'s'}
        s={'source_id':'s','evidence_url':'https://example.com','value':{'excerpt':text or 'Example Gym 123 Main St Houston TX fitness $20/day','retrieved_at':date}}
        return validate_competitors(candidates or [c],[s],'fitness studio','Houston',now=datetime(2026,11,14,18,tzinfo=timezone.utc),**kwargs)
    def test_dedup(self):
        c={'name':'Example Gym','address':'123 Main St Houston TX','category_excerpt':'fitness','source_id':'s'}
        self.assertEqual(len(self.review([c,c])['competitors']),1)
    def test_category_mismatch(self):
        self.assertEqual(self.review(text='Example Gym 123 Main St Houston TX pickleball')['competitors'],[])
    def test_stale(self):
        self.assertEqual(self.review(date='2020-01-01')['competitors'],[])
    def test_wrong_city(self):
        self.assertEqual(self.review(text='Example Gym 123 Main St Los Angeles CA fitness')['competitors'],[])
    def test_outage_not_no_competitors(self):
        r=validate_competitors([],[],'fitness studio','Houston')
        self.assertIn('does not imply zero',r['limitation'])
        self.assertFalse(r['demand_verified'])
    def test_distance_and_out_of_radius(self):
        self.assertEqual(distance_miles({'x':0,'y':0},{'x':0,'y':0}),0)
        self.assertEqual(self.review(origin={'x':-95,'y':29},geocode=lambda a:{'x':-118,'y':34})['competitors'],[])
    def test_unverified_price_dropped(self):
        c={'name':'Example Gym','address':'123 Main St Houston TX','category_excerpt':'fitness','source_id':'s','published_price':'$1/day'}
        self.assertIsNone(self.review([c])['competitors'][0]['published_price'])

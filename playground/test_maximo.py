import unittest
from unittest.mock import patch

from maximo import project_cash, review_property


class MaximoTests(unittest.TestCase):
    def test_cash_changes_schedule_and_reserve_together(self):
        args = {"monthly_rent": 8500, "monthly_carry": 4000}
        base = project_cash(args, "indoor pickleball", "lease")
        delayed = project_cash({**args, "delay": 3}, "indoor pickleball", "lease")
        self.assertEqual(base["timeline"]["opening_month"], 4)
        self.assertEqual(delayed["timeline"]["opening_month"], 7)
        self.assertEqual(delayed["conversion"]["first_month_below_reserve"], 6)
        self.assertEqual(delayed["conversion"]["extra_funding_needed"], 5000)

    def test_selected_listing_controls_rent_and_offline_skips_research(self):
        property_record = {"id": 23296, "propertyType": 7, "primaryAddress": {"streetNumber": "9700", "streetName": "Tanner", "streetType": "Rd"}}
        space = {"suite": "A", "listing_id": 8, "square_feet": 10000, "available_on": None, "on_market": None}
        matching = {"suite": "A", "listing_id": 8, "squareFeetMax": 10000,
                    "rateHigh": 0.85, "rateBasis": 1}
        different = {**matching, "listing_id": 9, "rateHigh": 0.1}
        entry = {"address": "9700 Tanner Rd", "city": "Houston", "id": "23296"}
        with (patch("maximo.load_property", return_value=property_record),
              patch("maximo.listed_spaces", return_value=[space]),
              patch("maximo.gather", return_value=(property_record, [space], None, {}, {})),
              patch("maximo.load_tenancies", return_value={}),
              patch("maximo.load_deal_data", return_value=([different, matching], [], [])),
              patch("maximo.deal_facts", return_value={"records": []}),
              patch("maximo.space_fit", return_value={"records": [], "verdict": "investigate"}),
              patch("maximo.collect_official", create=True) as other):
            result = review_property(None, entry, "indoor pickleball", "A", "lease", {},
                                     offline=True, research=other)
        other.assert_not_called()
        self.assertEqual(result["money"]["inputs"]["monthly_rent"], 8500)
        self.assertEqual(result["approvals"]["guidance_market"], "Houston")
        self.assertEqual(result["location"]["status"], "offline")

    def test_residential_property_stops_before_fit_research_and_cash(self):
        prop = {"id": 966604, "propertyType": 11,
                "attachments": [{"videoExternalReferenceType": 36, "videoKey": "residential-tour",
                                 "caption": "2 Br, 2 Ba The Villa 1197 SF"}]}
        entry = {"address": "9721 Cypresswood Dr", "city": "Houston", "id": "966604"}
        with (patch("maximo.load_property", return_value=prop),
              patch("maximo.listed_spaces", return_value=[]),
              patch("maximo.load_tenancies", return_value={}),
              patch("maximo.load_deal_data", return_value=([], [], [])),
              patch("maximo.gather") as gather,
              patch("maximo.project_cash") as cash,
              patch("maximo.collect_official", create=True) as research):
            result = review_property(None, entry, "indoor pickleball", None, "lease", {}, research=research)
        gather.assert_not_called()
        research.assert_not_called()
        cash.assert_not_called()
        self.assertEqual(result["eligibility"]["status"], "blocked")
        self.assertEqual(result["eligibility"]["records"][1]["fact"], "residential_scan_caption")
        self.assertIsNone(result["money"])
        self.assertIsNone(result["space"])

    def test_unnamed_commercial_listing_can_reach_conditional_cash(self):
        prop = {"id": 13890701, "propertyType": 2}
        space = {"suite": None, "listing_id": 37112018, "square_feet": 9900}
        deal = {"suite": None, "listing_id": 37112018, "squareFeetMax": 9900,
                "rateHigh": 0.8, "rateBasis": 1}
        entry = {"address": "Wynnwood", "city": "Houston", "id": "13890701"}
        with (patch("maximo.load_property", return_value=prop),
              patch("maximo.listed_spaces", return_value=[space]),
              patch("maximo.load_tenancies", return_value={}),
              patch("maximo.load_deal_data", return_value=([deal], [], [])),
              patch("maximo.deal_facts", return_value={"records": []}),
              patch("maximo.gather", return_value=(prop, [space], None, {}, {})),
              patch("maximo.space_fit", return_value={"records": [], "verdict": "supported"})):
            result = review_property(None, entry, "indoor pickleball", "listing:37112018:9900",
                                     "lease", {}, offline=True)
        self.assertEqual(result["eligibility"]["status"], "conditional")
        self.assertEqual(result["money"]["inputs"]["monthly_rent"], 7920)

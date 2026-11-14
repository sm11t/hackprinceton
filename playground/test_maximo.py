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
        property_record = {"id": 23296, "primaryAddress": {"streetNumber": "9700", "streetName": "Tanner", "streetType": "Rd"}}
        space = {"suite": "A", "listing_id": 8, "square_feet": 10000, "available_on": None, "on_market": None}
        matching = {"suite": "A", "listing_id": 8, "squareFeetMax": 10000,
                    "rateHigh": 0.85, "rateBasis": 1}
        different = {**matching, "listing_id": 9, "rateHigh": 0.1}
        entry = {"address": "9700 Tanner Rd", "city": "Houston", "id": "23296"}
        with (patch("maximo.gather", return_value=(property_record, [space], None, {}, {})),
              patch("maximo.load_tenancies", return_value={}),
              patch("maximo.load_deal_data", return_value=([different, matching], [], [])),
              patch("maximo.deal_facts", return_value={"records": []}),
              patch("maximo.space_fit", return_value={"records": []}),
              patch("maximo.collect_official", create=True) as other):
            result = review_property(None, entry, "indoor pickleball", "A", "lease", {},
                                     offline=True, research=other)
        other.assert_not_called()
        self.assertEqual(result["money"]["inputs"]["monthly_rent"], 8500)
        self.assertEqual(result["approvals"]["guidance_market"], "Houston")
        self.assertEqual(result["location"]["status"], "offline")

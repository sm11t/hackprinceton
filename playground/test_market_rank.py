"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import unittest

from maximo import space_option
from market_rank import build_allowance, rank_market, space_value


def prop(pid, kind=2, ceiling=24.0, captions=(), number="100", street="Main"):
    return {
        "id": pid, "propertyType": kind,
        "primaryAddress": {"streetNumber": number, "streetName": street, "streetType": "St",
                           "latitude": 29.8, "longitude": -95.4},
        "grossBuildingAreaSquareFeet": 50000, "grossTypicalFloorSquareFeet": 50000,
        "rentableBuildingAreaSquareFeet": 50000, "numStoriesAboveGrade": 1,
        "propertyIndustrial": {"structural": {"ceilingHeightFeet": ceiling}} if ceiling else {},
        "attachments": [{"videoExternalReferenceType": 36, "videoKey": f"m{pid}{i}", "caption": c,
                         "originationDate": "2026-03-10T09:00:00-05:00", "attachmentMasterId": i}
                        for i, c in enumerate(captions)],
    }


def space(sf, suite="A", rate=12.0, listing=1, space_id=None):
    raw = {"rateHigh": rate, "rateBasis": 2, "squareFeetMax": sf, "serviceType": 13} if rate else {"squareFeetMax": sf}
    raw["id"] = space_id if space_id is not None else listing * 100 + sf
    return {"listing_id": listing, "suite": suite, "square_feet": sf, "available_on": None, "on_market": None,
            "raw": raw}


def ids(result):
    return [r["property_id"] for r in result["results"]]


class MarketRanking(unittest.TestCase):
    def rank(self, *candidates, use="indoor pickleball", capital=500000, **kw):
        return rank_market(list(candidates), use, capital, 50000, **kw)

    def test_supported_ranks_above_unknown_height(self):
        result = self.rank((prop(1, ceiling=None), [space(8000)]), (prop(2), [space(8000)]))
        self.assertEqual(ids(result), [2, 1])
        self.assertEqual([r["verdict"] for r in result["results"]], ["supported", "investigate"])

    def test_low_ceiling_is_excluded_not_ranked_last(self):
        self.assertEqual(ids(self.rank((prop(1, ceiling=14.0), [space(8000)]))), [])

    def test_residential_and_wrong_type_are_excluded(self):
        result = self.rank((prop(1, kind=11), [space(8000)]), (prop(2, kind=5), [space(8000)]))
        self.assertEqual(ids(result), [])

    def test_dwelling_tour_is_excluded(self):
        self.assertEqual(ids(self.rank((prop(1, captions=["2 Br, 2 Ba The Villa 1197 SF"]), [space(8000)]))), [])

    def test_pickleball_needs_three_courts_by_default(self):
        self.assertEqual(ids(self.rank((prop(1), [space(2400)]))), [])
        self.assertEqual(ids(self.rank((prop(1), [space(2400)]), min_sf=0)), [1])

    def test_over_budget_ranks_below_within_budget(self):
        result = self.rank((prop(1), [space(8000, rate=30.0)]), (prop(2), [space(8000, rate=10.0)]), capital=330000)
        self.assertEqual(ids(result), [2, 1])
        self.assertEqual([r["within_budget"] for r in result["results"]], [True, False])

    def test_tour_for_another_address_ranks_down_and_is_shown(self):
        flagged = prop(1, captions=["Suite A - 999 Main St"])
        result = self.rank((flagged, [space(8000, rate=8.0)]), (prop(2), [space(8000, rate=12.0)]))
        self.assertEqual(ids(result), [2, 1])
        self.assertTrue(result["results"][1]["evidence_flags"])

    def test_one_space_per_building_keeps_the_best(self):
        result = self.rank((prop(1), [space(8000, "A", 20.0), space(8000, "B", 10.0, listing=2)]))
        self.assertEqual([r["suite"] for r in result["results"]], ["B"])

    def test_suite_value_matches_the_review_page_picker(self):
        for s in (space(9900, suite=None, listing=7), space(5000, suite=" 350 ")):
            self.assertEqual(space_value(s), space_option(s)["value"])

    def test_no_listed_rent_means_budget_unknown_and_ranks_below_known(self):
        result = self.rank((prop(1), [space(8000, rate=None)]), (prop(2), [space(8000, rate=20.0)]))
        self.assertEqual(ids(result), [2, 1])
        unknown = result["results"][1]
        self.assertIsNone(unknown["within_budget"])
        self.assertIn("budget fit unknown", unknown["why"])
        self.assertEqual(result["budget_unknown"], 1)

    def estimates(self, sid, low, typical, high, low_confidence=False):
        return {"spaces": {str(sid): {"low": low, "typical": typical, "high": high, "method": "similar_deals",
                                      "low_confidence": low_confidence}}}

    def test_rent_estimate_fills_a_missing_rent_conservatively(self):
        est = self.estimates(7, 8.0, 10.0, 12.0)
        result = self.rank((prop(1), [space(8000, rate=None, space_id=7)]), (prop(2), [space(8000, rate=10.0)]),
                           (prop(3), [space(8000, rate=None, space_id=8)]), rent_estimates=est)
        self.assertEqual(ids(result), [2, 1, 3])  # listed rent, then estimate-backed, then unknown
        estimated = result["results"][1]
        self.assertEqual((estimated["within_budget"], estimated["budget_basis"]), (True, "rent estimate"))
        self.assertIn("even at the high rent estimate", estimated["why"])
        self.assertEqual(result["rent_from_estimate"], 1)

    def test_estimate_over_budget_and_low_confidence(self):
        over = self.rank((prop(1), [space(8000, rate=None, space_id=7)]), capital=330000,
                         rent_estimates=self.estimates(7, 40.0, 60.0, 80.0))
        self.assertFalse(over["results"][0]["within_budget"])
        thin = self.rank((prop(1), [space(8000, rate=None, space_id=7)]),
                         rent_estimates=self.estimates(7, 8.0, 10.0, 12.0, low_confidence=True))
        self.assertEqual((thin["results"][0]["within_budget"], thin["results"][0]["budget_basis"]), (None, "default rent"))

    def test_build_out_scales_with_size(self):
        self.assertEqual(build_allowance("indoor pickleball", 10000), 200000)
        self.assertEqual(build_allowance("indoor pickleball", 48600), 972000)
        self.assertEqual(build_allowance("warehouse / storage", 10000), 25000)
        result = self.rank((prop(1), [space(48600, rate=3.0)]), (prop(2), [space(6000, rate=12.0)]))
        self.assertEqual(ids(result), [2, 1])  # the huge cheap-per-sq-ft space no longer wins on a lump sum
        self.assertFalse(result["results"][1]["within_budget"])

    def test_unknown_use_rejected(self):
        with self.assertRaises(ValueError):
            self.rank((prop(1), [space(8000)]), use="casino")


if __name__ == "__main__":
    unittest.main()

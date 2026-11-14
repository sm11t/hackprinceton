"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import unittest

from interior import interior_records, match_listed, summarize
from space_fit import space_fit

SQM = 1 / 10.7639  # sq ft -> m2
FT = 1 / 3.28084   # ft -> m


def prop(captions, ceiling=None):
    return {
        "id": 13890701, "grossBuildingAreaSquareFeet": 38436, "rentableBuildingAreaSquareFeet": 38025,
        "numStoriesAboveGrade": 1,
        "primaryAddress": {"streetNumber": "6855", "streetName": "Wynnwood", "streetType": "Ln"},
        "attachments": [{"videoExternalReferenceType": 36, "videoKey": f"m{i}", "caption": c,
                         "originationDate": "2026-06-25T09:00:00-05:00", "attachmentMasterId": i}
                        for i, c in enumerate(captions)],
        "propertyIndustrial": {"structural": {"ceilingHeightFeet": ceiling}} if ceiling else None,
    }


def rooms(main_sf, main_ft, extra_sf=0):
    out = [{"label": "Warehouse", "dimensionEstimates": {"area": main_sf * SQM, "height": main_ft * FT}}]
    if extra_sf:
        out.append({"label": "Office", "dimensionEstimates": {"area": extra_sf * SQM, "height": 9 * FT}})
    return out


SPACES = [{"listing_id": 1, "suite": None, "square_feet": 9900.0, "available_on": None, "on_market": None},
          {"listing_id": 1, "suite": "B", "square_feet": 27750.0, "available_on": None, "on_market": None}]


def fact(records, name):
    return next(r for r in records if r["fact"] == name)


class Matching(unittest.TestCase):
    def test_match_by_suite_name(self):
        self.assertEqual(match_listed("Suite B tour", SPACES)["square_feet"], 27750.0)

    def test_match_by_advertised_size_when_no_suite(self):
        self.assertEqual(match_listed("Warehouse Space - 9,900SF\n", SPACES)["square_feet"], 9900.0)

    def test_no_match_when_size_is_ambiguous_or_absent(self):
        self.assertIsNone(match_listed("Lobby", SPACES))
        twins = [dict(SPACES[0], suite="X"), dict(SPACES[0], suite="Y")]
        self.assertIsNone(match_listed("Warehouse 9,900 SF", twins))


class Summary(unittest.TestCase):
    def test_zero_height_is_unknown_not_zero(self):
        self.assertIsNone(summarize(rooms(8853, 0))["main_height_ft"])

    def test_units_converted_to_feet(self):
        s = summarize(rooms(8853, 21.1, extra_sf=664))
        self.assertEqual(s["main_height_ft"], 21.1)
        self.assertEqual(s["total_sf"], 9517)


class Records(unittest.TestCase):
    def test_scan_with_a_different_address_is_not_used(self):
        p = {**prop(["Northwest Trade Center - 9750 Wynnwood Ln"])}
        records, heights = interior_records(p, {"m0": rooms(8853, 21.1)}, SPACES)
        self.assertEqual(fact(records, "scan_used_for_measurements")["status"], "conflict")
        self.assertEqual(heights, {})

    def test_measured_area_compared_with_listing(self):
        records, _ = interior_records(prop(["Warehouse Space - 9,900SF"]), {"m0": rooms(8853, 21.1, 664)}, SPACES)
        area = fact(records, "scan_measured_area_sf")
        self.assertEqual(area["status"], "agrees")
        self.assertIn("96% measured", area["note"])

    def test_scan_far_smaller_than_listing_is_flagged(self):
        records, _ = interior_records(prop(["Suite B"]), {"m0": rooms(3000, 21.1)}, SPACES)
        self.assertEqual(fact(records, "scan_measured_area_sf")["status"], "conflict")


class FitUsesTheRightHeight(unittest.TestCase):
    def test_measured_height_of_the_chosen_suite_overrides_costar(self):
        result = space_fit(prop(["Warehouse Space - 9,900SF"], ceiling=14), "pickleball", SPACES,
                           rooms_by_model={"m0": rooms(8853, 21.1, 664)})
        self.assertEqual(result["area_basis"], "the listed 9,900 sq ft space")  # the scanned space is preferred
        height = fact(result["records"], "pickleball_clear_height")
        self.assertEqual((height["value"], height["source"]), (21.1, "matterport"))
        self.assertEqual(result["verdict"], "supported")

    def test_other_scans_heights_never_apply_to_the_suite(self):
        # an office scan (9 ft) is not the 27,750 sq ft suite, so CoStar's 22 ft stays the evidence
        result = space_fit(prop(["Front office"], ceiling=22), "pickleball", SPACES, suite="B",
                           rooms_by_model={"m0": rooms(900, 9)})
        height = fact(result["records"], "pickleball_clear_height")
        self.assertEqual((height["value"], height["source"]), (22, "costar"))


if __name__ == "__main__":
    unittest.main()

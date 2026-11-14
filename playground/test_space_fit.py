"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import json
import tempfile
import unittest
from pathlib import Path

from space_fit import USES, evaluate_use, listed_spaces, load_property, space_fit, verdict

CONTRACT_KEYS = {"fact", "value", "source", "source_id", "captured_at", "confidence",
                 "evidence_url", "status", "needs_human", "note"}


def flex(ceiling=18, gba=69500, rba=69500, phases=3):
    return {
        "id": 23296, "grossBuildingAreaSquareFeet": gba, "rentableBuildingAreaSquareFeet": rba,
        "grossTypicalFloorSquareFeet": gba, "numStoriesAboveGrade": 1, "hasSprinklers": True,
        "parking": [{"totalSpaces": 173}],
        "primaryAddress": {"streetNumber": "9700", "streetName": "Tanner", "streetType": "Rd"},
        "propertyFlex": {"structural": {"ceilingHeightFeet": ceiling} if ceiling else None,
                         "numExternalLoadingDocks": 3, "driveInBays": {"numDriveInBays": 5, "numFeetWide": 10.0,
                                                                        "numFeetHigh": 10.0},
                         "electric": {"numElectricCurrentPhases": phases, "ampsHigh": 200,
                                      "voltsLow": 240, "voltsHigh": 480}},
    }


SUITE_A = [{"listing_id": 7, "suite": "A", "square_feet": 10000.0, "available_on": "2026-11-15",
            "on_market": "2026-10-01"}]


def fact(result, name):
    return next(r for r in result["records"] if r["fact"] == name)


class Contract(unittest.TestCase):
    def test_every_record_keeps_the_shared_shape(self):
        for use in USES:
            for r in space_fit(flex(), use, SUITE_A)["records"]:
                self.assertEqual(set(r), CONTRACT_KEYS, (use, r["fact"]))
                self.assertIn(r["status"], {"agrees", "conflict", "unknown"})


class Pickleball(unittest.TestCase):
    def test_courts_from_listed_suite_not_whole_building(self):
        result = space_fit(flex(), "pickleball", SUITE_A)
        self.assertEqual(result["area_basis"], "listed suite A")
        self.assertEqual(fact(result, "pickleball_courts_by_area")["value"], 5)  # 10,000 / 1,800

    def test_low_ceiling_rules_it_out(self):
        result = space_fit(flex(ceiling=14), "pickleball", SUITE_A)
        self.assertEqual(fact(result, "pickleball_clear_height")["status"], "conflict")
        self.assertEqual(result["verdict"], "does_not_fit")

    def test_missing_ceiling_is_unknown_not_a_guess(self):
        result = space_fit(flex(ceiling=None), "pickleball", SUITE_A)
        self.assertEqual(fact(result, "pickleball_clear_height")["status"], "unknown")
        self.assertEqual(result["verdict"], "investigate")

    def test_too_small_for_one_court(self):
        tiny = [{**SUITE_A[0], "square_feet": 1500.0}]
        self.assertEqual(space_fit(flex(), "pickleball", tiny)["verdict"], "does_not_fit")

    def test_supported_when_area_and_height_clear_the_bar(self):
        self.assertEqual(space_fit(flex(), "pickleball", SUITE_A)["verdict"], "supported")


class Daycare(unittest.TestCase):
    def test_capacity_is_an_upper_bound_at_30_sqft(self):
        result = space_fit(flex(), "daycare", SUITE_A)
        self.assertEqual(fact(result, "daycare_capacity_by_indoor_area")["value"], 333)
        outdoor = fact(result, "daycare_outdoor_space_needed_sf")
        self.assertEqual(outdoor["status"], "unknown")  # no fenced play area in the data
        self.assertEqual(result["verdict"], "investigate")


class GeneralFacts(unittest.TestCase):
    def test_unknown_building_facts_do_not_change_the_verdict(self):
        # floor load is missing, but pickleball is still judged on area and height only
        result = space_fit(flex(), "pickleball", SUITE_A)
        self.assertEqual(fact(result, "floor_load_psf")["status"], "unknown")
        self.assertEqual(result["verdict"], "supported")

    def test_power_and_bays_are_described(self):
        result = space_fit(flex(), "restaurant", SUITE_A)
        self.assertIn("3-phase", fact(result, "electrical_service")["value"])
        self.assertIn("10 ft wide", fact(result, "drive_in_bays")["note"])

    def test_no_listing_falls_back_to_building_area(self):
        result = space_fit(flex(), "pickleball", [])
        self.assertEqual(result["area_basis"], "the building (RBA)")

    def test_checklist_only_uses_investigate(self):
        self.assertEqual(verdict(evaluate_use("restaurant", ("x", 1000.0, "costar", 1), 18, "costar")),
                         "investigate")

    def test_unknown_use_is_rejected(self):
        with self.assertRaises(ValueError):
            space_fit(flex(), "casino", SUITE_A)


class KitFolder(unittest.TestCase):
    def test_reads_an_unzipped_kit_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp, "data")
            data.mkdir()
            (data / "commercial-property.jsonl").write_text(json.dumps(flex()) + "\n")
            listing = {"id": 7, "listingStatus": 1, "propertyId": 23296, "forLeaseSummary": {"spaces": [
                {"propertyId": 23296, "suite": "A", "squareFeetMax": 10000.0,
                 "availableOnDate": "2026-11-15T12:00:00-05:00"},
                {"propertyId": 99999, "suite": "Z", "squareFeetMax": 5.0}]}}
            (data / "commercial-listing-summary.jsonl").write_text(json.dumps(listing) + "\n")
            self.assertEqual(load_property(tmp, 23296)["id"], 23296)
            spaces = listed_spaces(tmp, 23296)
            self.assertEqual([s["suite"] for s in spaces], ["A"])  # other buildings' spaces are excluded


if __name__ == "__main__":
    unittest.main()

"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import json
import tempfile
import unittest
from pathlib import Path

from space_fit import (USES, evaluate_use, listed_spaces, load_property, parse_requirements, rank_uses, space_fit,
                       verdict)

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
            reqs = {"min_area_sf": 1000, "three_phase": True} if use == "custom" else None
            for r in space_fit(flex(), use, SUITE_A, requirements=reqs)["records"]:
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


class TypedRequirements(unittest.TestCase):
    def test_parsing_accepts_query_strings_and_rejects_unknown_keys(self):
        self.assertEqual(parse_requirements({"min_area_sf": "6000", "three_phase": "yes"}),
                         {"min_area_sf": 6000.0, "three_phase": True})
        for bad in ({"ceiling": "3"}, {"min_area_sf": "big"}, {"min_docks": "-1"}, {"min_amps": "nan"}):
            with self.assertRaises(ValueError, msg=bad):
                parse_requirements(bad)

    def test_custom_use_needs_a_requirement(self):
        with self.assertRaises(ValueError):
            space_fit(flex(), "custom", SUITE_A)

    def test_custom_use_supported_when_every_requirement_is_met(self):
        result = space_fit(flex(), "custom", SUITE_A, requirements={
            "min_clear_height_ft": 16, "min_area_sf": 6000, "min_docks": 2, "three_phase": True, "sprinklers": True},
            label="Climbing gym")
        self.assertEqual(result["use_label"], "Climbing gym")
        self.assertEqual(result["verdict"], "supported")
        self.assertEqual({r["status"] for r in result["records"] if r["fact"].startswith("req_")}, {"agrees"})

    def test_unmet_requirement_rules_the_space_out(self):
        result = space_fit(flex(), "custom", SUITE_A, requirements={"min_area_sf": 12000})
        self.assertEqual(fact(result, "req_min_area_sf")["status"], "conflict")
        self.assertEqual(result["verdict"], "does_not_fit")

    def test_missing_data_is_unknown_not_a_fail(self):
        prop = flex(ceiling=None)
        prop["propertyFlex"]["electric"] = {}
        result = space_fit(prop, "custom", SUITE_A, requirements={"min_clear_height_ft": 20, "three_phase": True})
        self.assertEqual(fact(result, "req_min_clear_height_ft")["status"], "unknown")
        self.assertEqual(fact(result, "req_three_phase")["status"], "unknown")
        self.assertEqual(result["verdict"], "investigate")

    def test_requirements_add_to_a_built_in_use(self):
        result = space_fit(flex(), "pickleball", SUITE_A, requirements={"min_area_sf": 12000})
        self.assertEqual(result["verdict"], "does_not_fit")  # courts fit, but the user's own minimum does not
        self.assertEqual(fact(result, "pickleball_courts_by_area")["status"], "agrees")


class Ranking(unittest.TestCase):
    def test_best_first_with_a_reason_for_each(self):
        ranked = rank_uses(flex(), SUITE_A)
        uses = [u["use"] for u in ranked["uses"]]
        self.assertNotIn("custom", uses)
        self.assertEqual(uses[0], "pickleball")  # the only use the data fully supports here
        self.assertTrue(all(u["reason"] for u in ranked["uses"]))

    def test_ruled_out_uses_sink_and_explain_why(self):
        ranked = rank_uses(flex(ceiling=10), SUITE_A)
        last = ranked["uses"][-1]
        self.assertEqual((last["use"], last["verdict"]), ("pickleball", "does_not_fit"))
        self.assertIn("below the minimum", last["reason"])

    def test_uses_without_checkable_thresholds_say_so(self):
        gym = next(u for u in rank_uses(flex(), SUITE_A)["uses"] if u["use"] == "gym")
        self.assertEqual(gym["verdict"], "investigate")
        self.assertIn("No threshold", gym["reason"])


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

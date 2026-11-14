"""Known answers on real Houston buildings from the data pilot (reports/data-pilot/findings.md).

These need the sponsor kit, which never goes in Git, and the cached provider responses in
playground/output/ (run space_fit.py once online per property to create them). They are
skipped unless COSTAR_KIT points at the kit zip (with COSTAR_KIT_PASSWORD) or an unzipped kit:

    COSTAR_KIT=~/Downloads/costar-hackathon-kit.zip python3 -m unittest playground/test_known_cases.py
"""
import os
import unittest
from pathlib import Path

from space_fit import kit_password, run, run_rank

KIT = os.environ.get("COSTAR_KIT")
CACHE = Path(__file__).parent / "output"


def fact(result, name):
    return next(r for r in result["records"] if r["fact"] == name)


@unittest.skipUnless(KIT, "set COSTAR_KIT to the sponsor kit to run the known-case checks")
class KnownBuildings(unittest.TestCase):
    def fit(self, property_id, use="pickleball", **kwargs):
        if not (CACHE / f"vexcel-{property_id}.json").exists():
            self.skipTest(f"no cached Vexcel response for {property_id}; run space_fit.py once online")
        return run(os.path.expanduser(KIT), property_id, use, offline=True, password=kit_password(), **kwargs)

    def test_wynnwood_warehouse_is_supported_on_measured_height(self):
        # Listed 9,900 sq ft warehouse; its scan names the size, measures ~96% of it and 21.1 ft clear.
        result = self.fit(13890701)
        self.assertEqual(result["verdict"], "supported")
        self.assertEqual(result["area_basis"], "the listed space (no suite name)")
        height = fact(result, "pickleball_clear_height")
        self.assertEqual((height["value"], height["source"]), (21.1, "matterport"))
        self.assertEqual(fact(result, "pickleball_courts_by_area")["value"], 5)

    def test_willow_place_office_suite_is_ruled_out_by_measured_height(self):
        result = self.fit(239686)
        self.assertEqual(result["verdict"], "does_not_fit")
        self.assertEqual(fact(result, "pickleball_clear_height")["value"], 7.9)

    def test_northgreen_ruled_out_by_costar_height_and_aerial_not_trusted(self):
        # No Vexcel footprint contains the CoStar pin (nearest is 166 m away): never compared.
        result = self.fit(237647)
        self.assertEqual(result["verdict"], "does_not_fit")
        self.assertEqual(fact(result, "pickleball_clear_height")["value"], 14)
        self.assertEqual(fact(result, "footprint_vs_costar_floor")["status"], "unknown")

    def test_tanner_scan_for_another_address_is_not_used(self):
        result = self.fit(23296)
        self.assertEqual(fact(result, "scan_used_for_measurements")["status"], "conflict")  # captioned 9750
        self.assertEqual(fact(result, "footprint_vs_costar_floor")["value"], 1.07)
        self.assertIn("water pooling", fact(result, "roof_defects")["value"])
        self.assertEqual(result["verdict"], "supported")

    def test_grant_road_size_conflict_and_implausible_roof_height(self):
        result = self.fit(9292792)
        self.assertEqual(fact(result, "footprint_vs_costar_floor")["status"], "conflict")  # 3,984 vs 1,500 sq ft
        self.assertIsNone(fact(result, "roof_height_ft")["value"])  # Vexcel's 5.3 ft for 2 stories is a data error

    def test_typed_requirements_on_wynnwood(self):
        result = self.fit(13890701, use="custom", label="Climbing gym",
                          requirements={"min_clear_height_ft": 20, "min_area_sf": 6000, "three_phase": True})
        self.assertEqual(fact(result, "req_min_clear_height_ft")["status"], "agrees")
        self.assertEqual(fact(result, "req_three_phase")["status"], "unknown")  # CoStar has no phase count here
        self.assertEqual(result["verdict"], "investigate")

    def test_ranking_puts_pickleball_first_at_wynnwood(self):
        if not (CACHE / "vexcel-13890701.json").exists():
            self.skipTest("no cached Vexcel response for 13890701")
        ranked = run_rank(os.path.expanduser(KIT), 13890701, offline=True, password=kit_password())
        self.assertEqual(ranked["uses"][0]["use"], "pickleball")


if __name__ == "__main__":
    unittest.main()

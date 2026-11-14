"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import unittest

from exterior import exterior_records, structure_under_pin
from space_fit import space_fit

LAT, LON = 29.8506, -95.5332


def square(cx, cy, half=0.0003):
    return (f"POLYGON(({cx - half} {cy - half}, {cx + half} {cy - half}, {cx + half} {cy + half}, "
            f"{cx - half} {cy + half}, {cx - half} {cy - half}))")


def structure(cx=LON, cy=LAT, area=74416.0, roof=33.8, **extra):
    return {"footprint.wkt": square(cx, cy), "footprint.area": area, "roof-characteristics.height": roof,
            "roof-characteristics.material.class": "gravel", "roof-characteristics.material.score": 0.98,
            "roof-characteristics.shape.value": "flat", **extra}


def vexcel(*structures, vehicles=None):
    return {"features": [{"properties": {"structures": list(structures), "metadata.collection": "us-tx-test-2026",
                                         "metadata.ortho-date-estimate": "2025-12-31T00:00:00",
                                         "ground-elevation.value": 97.0, "vehicles.count": vehicles}}]}


def prop(stories=1, ceiling=18, floor=69500):
    return {"id": 23296, "grossBuildingAreaSquareFeet": floor * stories, "rentableBuildingAreaSquareFeet": floor * stories,
            "grossTypicalFloorSquareFeet": floor, "numStoriesAboveGrade": stories, "parking": [{"totalSpaces": 100}],
            "primaryAddress": {"streetNumber": "9700", "streetName": "Tanner", "streetType": "Rd",
                               "latitude": LAT, "longitude": LON},
            "propertyFlex": {"structural": {"ceilingHeightFeet": ceiling}}}


def fact(records, name):
    return next(r for r in records if r["fact"] == name)


class PinMatching(unittest.TestCase):
    def test_structure_containing_the_pin_wins_over_a_bigger_neighbour(self):
        far = structure(cx=LON + 0.002, area=200000.0)
        near = structure(area=50000.0)
        chosen, how = structure_under_pin([far, near], LAT, LON)
        self.assertEqual(chosen["footprint.area"], 50000.0)
        self.assertEqual(how, "pin inside footprint")

    def test_nearest_structure_is_flagged_and_not_compared(self):
        records, _ = exterior_records(prop(), vexcel(structure(cx=LON + 0.002)), 69500)
        self.assertEqual(fact(records, "footprint_vs_costar_floor")["status"], "unknown")
        self.assertIsNone(fact(records, "roof_height_ft")["value"])


class Size(unittest.TestCase):
    def test_footprint_within_20_percent_agrees(self):
        records, _ = exterior_records(prop(), vexcel(structure()), 69500)
        self.assertEqual(fact(records, "footprint_vs_costar_floor")["status"], "agrees")

    def test_footprint_far_from_costar_is_a_conflict(self):
        records, _ = exterior_records(prop(), vexcel(structure(area=3984.0)), 1500)
        self.assertEqual(fact(records, "footprint_vs_costar_floor")["status"], "conflict")


class RoofHeight(unittest.TestCase):
    def test_implausible_roof_height_becomes_unknown(self):
        records, _ = exterior_records(prop(stories=2), vexcel(structure(roof=5.3)), 69500)
        self.assertIsNone(fact(records, "roof_height_ft")["value"])
        self.assertEqual(fact(records, "roof_height_ft")["status"], "unknown")

    def test_low_but_plausible_roof_rules_out_tall_uses(self):
        result = space_fit(prop(ceiling=None), "pickleball", [], vexcel=vexcel(structure(roof=12.0)))
        self.assertEqual(fact(result["records"], "pickleball_roof_upper_bound")["status"], "conflict")
        self.assertEqual(result["verdict"], "does_not_fit")

    def test_tall_roof_is_only_an_upper_bound(self):
        result = space_fit(prop(ceiling=None), "pickleball", [], vexcel=vexcel(structure(roof=33.8)))
        self.assertEqual(fact(result["records"], "pickleball_roof_upper_bound")["status"], "agrees")
        self.assertEqual(result["verdict"], "investigate")  # clear height itself is still unknown


class RoofAndSite(unittest.TestCase):
    def test_defects_become_inspection_questions(self):
        s = structure(**{"roof-defects.discoloration.types.water-pooling.detected": True,
                         "roof-defects.discoloration.types.water-pooling.percent": 80.5,
                         "roof-defects.discoloration.types.water-pooling.score": 0.83})
        records, _ = exterior_records(prop(), vexcel(s), 69500)
        defects = fact(records, "roof_defects")
        self.assertIn("water pooling", defects["value"])
        self.assertTrue(defects["needs_human"])

    def test_low_confidence_roof_material_is_dropped(self):
        s = structure(**{"roof-characteristics.material.class": "shingle", "roof-characteristics.material.score": 0.0,
                         "roof-characteristics.shape.value": "gable"})
        records, _ = exterior_records(prop(), vexcel(s), 69500)
        self.assertEqual(fact(records, "roof_type")["value"], "gable")

    def test_vehicle_count_is_context_not_occupancy(self):
        records, _ = exterior_records(prop(), vexcel(structure(), vehicles=51), 69500)
        note = fact(records, "vehicles_on_parcel")["note"]
        self.assertIn("51%", note)
        self.assertIn("not an occupancy measure", note)

    def test_no_parcel_is_unknown(self):
        records, s = exterior_records(prop(), {"features": []}, 69500)
        self.assertIsNone(s)
        self.assertEqual(records[0]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()

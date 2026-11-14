"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import unittest

from reconcile import (check_clear_height, check_identity, check_occupancy, check_size, number_matches,
                       parse_caption, record)

CONTRACT_KEYS = {"fact", "value", "source", "source_id", "captured_at", "confidence",
                 "evidence_url", "status", "needs_human", "note"}


def prop(number="9700", street="Tanner", street_type="Rd", captions=(), ceiling=None):
    return {
        "id": 1,
        "primaryAddress": {"streetNumber": number, "streetName": street, "streetType": street_type,
                           "latitude": 29.85, "longitude": -95.53},
        "attachments": [{"videoExternalReferenceType": 36, "videoKey": f"m{i}", "caption": c,
                         "originationDate": "2026-03-10T09:00:00-05:00", "attachmentMasterId": i}
                        for i, c in enumerate(captions)],
        "propertyFlex": {"structural": {"ceilingHeightFeet": ceiling}} if ceiling else None,
    }


class CaptionParsing(unittest.TestCase):
    def test_reads_street_address(self):
        self.assertEqual(parse_caption("Northwest Trade Center - 9750 Tanner Rd")["street_number"], "9750")

    def test_suite_numbers_and_labels_are_not_addresses(self):
        for caption in ("7457 Suite 250", "Suite 200 Matterport", "2603 Club", "6203 F - 3,600 SF"):
            self.assertIsNone(parse_caption(caption)["street_number"], caption)

    def test_suite_is_extracted(self):
        self.assertEqual(parse_caption("Suite 116 - 502 SF (10601 Grant Road)")["suite"], "116")

    def test_number_ranges(self):
        self.assertTrue(number_matches("8303-8317", "8303-8317"))
        self.assertTrue(number_matches("8305", "8303-8317"))
        self.assertFalse(number_matches("9750", "9700"))


class IdentityCheck(unittest.TestCase):
    def test_different_street_number_is_conflict(self):
        [r] = check_identity(prop(captions=["Northwest Trade Center - 9750 Tanner Rd"]))
        self.assertEqual((r["status"], r["needs_human"]), ("conflict", True))
        self.assertEqual(set(r), CONTRACT_KEYS)
        self.assertEqual(r["captured_at"], "2026-03-10")

    def test_matching_address_agrees(self):
        [r] = check_identity(prop(captions=["9700 Tanner Road - Suite A"]))
        self.assertEqual(r["status"], "agrees")

    def test_highway_alias_is_not_a_conflict(self):
        [r] = check_identity(prop("7676", "I-45", "", captions=["View Virtual Tour of 7676 North Fwy - Suite 811"]))
        self.assertEqual(r["status"], "unknown")

    def test_caption_without_address_is_unknown(self):
        [r] = check_identity(prop(captions=["Suite 200 Virtual Tour"]))
        self.assertEqual(r["status"], "unknown")

    def test_duplicate_scan_attachments_counted_once(self):
        p = prop(captions=["9750 Tanner Rd"])
        p["attachments"].append(dict(p["attachments"][0], attachmentMasterId=99))
        self.assertEqual(len(check_identity(p)), 1)


class ClearHeight(unittest.TestCase):
    def test_unmeasured_main_space_is_unknown_not_conflict(self):
        rooms = [{"label": "Warehouse", "dimensionEstimates": {"area": 593, "height": 0}},
                 {"label": "Office", "dimensionEstimates": {"area": 20, "height": 2.87}}]
        records = check_clear_height(prop(ceiling=18.0), {"m0": rooms})
        matterport = [r for r in records if r["source"] == "matterport"]
        self.assertEqual(matterport[0]["status"], "unknown")

    def test_measured_main_space_compared(self):
        rooms = [{"label": "Warehouse", "dimensionEstimates": {"area": 593, "height": 3.0}}]
        [_, r] = check_clear_height(prop(ceiling=18.0), {"m0": rooms})
        self.assertEqual(r["status"], "conflict")  # ~9.8 ft vs 18 ft


def tenancy(start, end=None, suite="155", tenant="Acme Drywall"):
    return {"id": 7, "tenant": tenant, "suites": {suite}, "start": start, "end": end, "square_feet": 750}


class Occupancy(unittest.TestCase):
    """Scan date in prop() is 2026-03-10."""

    def check(self, *tenancies, caption="Suite 155 - 1,794SF"):
        [r] = check_occupancy(prop(captions=[caption]), list(tenancies))
        self.assertEqual(set(r), CONTRACT_KEYS)
        return r

    def test_long_lease_covering_scan_date_is_conflict(self):
        r = self.check(tenancy("2023-09-01", "2028-07-23"))
        self.assertEqual((r["status"], r["needs_human"], r["value"]), ("conflict", True, "Acme Drywall"))

    def test_open_ended_lease_is_conflict(self):
        self.assertEqual(self.check(tenancy("2020-01-01"))["status"], "conflict")

    def test_lease_ending_within_a_year_needs_photos_not_conflict(self):
        r = self.check(tenancy("2023-09-01", "2026-07-23"))
        self.assertEqual((r["status"], r["needs_human"]), ("unknown", True))

    def test_move_in_after_scan_is_the_classic_false_alarm(self):
        r = self.check(tenancy("2014-03-01", "2017-03-31"), tenancy("2026-09-23", tenant="Later Co"))
        self.assertEqual((r["status"], r["value"]), ("agrees", "vacant at scan"))
        self.assertIn("Later Co", r["note"])

    def test_move_in_just_before_scan_date_is_unknown(self):
        self.assertEqual(self.check(tenancy("2026-02-01"))["status"], "unknown")

    def test_suite_spelling_is_normalised(self):
        r = self.check(tenancy("2020-01-01", suite="C1A"), caption="Take a Tour of Suite C-1A")
        self.assertEqual(r["status"], "conflict")

    def test_no_recorded_tenancy_is_unknown(self):
        self.assertEqual(self.check(tenancy("2020-01-01", suite="999"))["status"], "unknown")

    def test_scan_captioned_for_another_building_is_not_compared(self):
        r = self.check(tenancy("2020-01-01", suite="116"), caption="Suite 116 - 502 SF (9750 Tanner Road)")
        self.assertEqual(r["status"], "unknown")

    def test_scan_without_suite_is_skipped(self):
        self.assertEqual(check_occupancy(prop(captions=["9700 Tanner Rd"]), [tenancy("2020-01-01")]), [])


class CostarSize(unittest.TestCase):
    def sized(self, gba, typical, stories, rba=None):
        return {"id": 1, "grossBuildingAreaSquareFeet": gba, "grossTypicalFloorSquareFeet": typical,
                "numStoriesAboveGrade": stories, "rentableBuildingAreaSquareFeet": rba}

    def test_consistent_sizes_agree(self):
        [r] = check_size(self.sized(137192, 34298, 4))
        self.assertEqual(r["status"], "agrees")

    def test_gross_area_that_floors_cannot_explain_is_conflict(self):
        [r] = check_size(self.sized(24567, 18000, 1, 18000))  # 1800 Sherwood Forest St
        self.assertEqual((r["status"], r["value"]), ("conflict", 1.36))

    def test_rentable_larger_than_gross_is_conflict(self):
        records = check_size(self.sized(10000, 10000, 1, 12000))
        self.assertEqual([r["status"] for r in records], ["agrees", "conflict"])

    def test_missing_fields_are_unknown(self):
        [r] = check_size(self.sized(None, 10000, 1))
        self.assertEqual(r["status"], "unknown")


class Contract(unittest.TestCase):
    def test_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            record("x", 1, "costar", status="maybe")


if __name__ == "__main__":
    unittest.main()

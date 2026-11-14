"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import unittest
import json
from unittest.mock import patch

from reconcile import (check_clear_height, check_identity, check_suite_identity, check_scan_dates,
                       check_flood, number_matches, parse_caption, record, reconcile, reconcile_evidence,
                       same_street, unique_scans, check_occupancy, check_size)

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

    def test_room_and_building_height_are_not_comparable_scopes(self):
        rooms = [{"label": "Warehouse", "dimensionEstimates": {"area": 593, "height": 3.0}}]
        [_, r] = check_clear_height(prop(ceiling=18.0), {"m0": rooms})
        self.assertEqual(r["status"], "unknown")  # ~9.8 ft room vs 18 ft building cannot prove conflict
        self.assertEqual(r["value"], 9.8)
        self.assertTrue(r["needs_human"])


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


class ScopeAndProvenance(unittest.TestCase):
    def test_matching_address_does_not_match_unspecified_suite(self):
        p = prop(captions=["9700 Tanner Road Suite A"])
        [r] = check_suite_identity(p)
        self.assertEqual(r["status"], "unknown")
        self.assertTrue(r["needs_human"])

    def test_wrong_suite_is_conflict_even_at_matching_address(self):
        [r] = check_suite_identity(prop(captions=["9700 Tanner Road Suite A"]), "B")
        self.assertEqual(r["status"], "conflict")

    def test_matching_suite_label_still_requires_physical_verification(self):
        [r] = check_suite_identity(prop(captions=["9700 Tanner Road Suite A"]), "a")
        self.assertEqual(r["status"], "agrees")
        self.assertTrue(r["needs_human"])

    def test_matching_suite_at_wrong_building_cannot_agree(self):
        [r] = check_suite_identity(prop(captions=["9750 Tanner Road Suite A"]), "a")
        self.assertEqual(r["status"], "unknown")

    def test_overlapping_address_range_does_not_verify_building(self):
        [r] = check_identity(prop("8305", captions=["8303-8317 Tanner Road"]))
        self.assertEqual(r["status"], "unknown")

    def test_shared_street_word_does_not_prove_match(self):
        self.assertFalse(same_street("Main Street", "Main Road"))
        self.assertFalse(same_street("East Main Street", "West Main Street"))
        self.assertIsNone(same_street("World Houston Parkway", "World Parkway"))
        [r] = check_identity(prop(street="Main", street_type="St", captions=["9700 Main Road"]))
        self.assertEqual(r["status"], "conflict")

    def test_missing_costar_address_is_unknown_not_conflict(self):
        p = prop(captions=["9700 Tanner Road"])
        p["primaryAddress"] = {}
        [r] = check_identity(p)
        self.assertEqual(r["status"], "unknown")

    def test_hash_suite_number(self):
        self.assertEqual(parse_caption("9700 Tanner Rd #123")["suite"], "123")

    def test_duplicate_model_keeps_conflicting_captions(self):
        p = prop(captions=["9700 Tanner Road"])
        p["attachments"].append(dict(p["attachments"][0], caption="9750 Tanner Road", attachmentMasterId=99))
        records = check_identity(p)
        self.assertEqual([r["status"] for r in records], ["agrees", "conflict"])
        self.assertEqual(len(unique_scans(p)), 1)

    def test_attachment_date_is_not_camera_capture_date(self):
        p = prop(captions=["9700 Tanner Road"])
        p["attachments"].append(dict(p["attachments"][0], originationDate="2025-04-03T00:00:00Z"))
        [r] = check_scan_dates(p)
        self.assertEqual(r["value"], "2025-04-03")
        self.assertEqual(r["fact"], "scan_attachment_date")
        self.assertIn("not a verified camera capture date", r["note"])

    def test_invalid_date_is_unknown(self):
        p = prop(captions=["9700 Tanner Road"])
        p["attachments"][0]["originationDate"] = "2026-99-00"
        [r] = check_scan_dates(p)
        self.assertIsNone(r["value"])
        self.assertIsNone(r["captured_at"])
        self.assertEqual(r["status"], "unknown")

    def test_invalid_height_never_becomes_known_measurement(self):
        for height in (-3, 0, "", "NaN", float("inf"), True):
            p = prop(ceiling=height)
            rooms = [{"dimensionEstimates": {"height": height, "area": 5}}]
            for r in check_clear_height(p, {"m0": rooms}):
                self.assertIsNone(r["value"], height)
                self.assertEqual(r["status"], "unknown")

    def test_room_measurement_carries_attachment_provenance(self):
        p = prop(captions=["9750 Tanner Road"], ceiling=18)
        rooms = [{"id": "r1", "label": "Warehouse", "dimensionEstimates": {"area": 593, "height": 5.5}}]
        [_, r] = check_clear_height(p, {"m0": rooms})
        self.assertEqual(r["captured_at"], "2026-03-10")
        self.assertEqual(r["status"], "unknown")
        self.assertIn("r1", r["note"])

    def test_offline_run_explicitly_reports_unavailable_measurements(self):
        p = prop(captions=["9700 Tanner Road"])
        with patch("reconcile.urlopen") as network:
            result = reconcile(p, offline=True)
        network.assert_not_called()
        self.assertEqual(set(result), {"property_id", "address", "records", "conflicts", "errors"})
        self.assertTrue(any(r["source"] == "matterport" and r["value"] is None for r in result["records"]))
        self.assertTrue(any(r["fact"] == "flood_zone" and r["value"] is None for r in result["records"]))
        for r in result["records"]:
            self.assertEqual(set(r), CONTRACT_KEYS)

    def test_pure_adapter_reuses_evidence_without_network(self):
        with patch("reconcile.urlopen") as network:
            result = reconcile_evidence(prop(captions=["9750 Tanner Road"]), {})
        network.assert_not_called()
        self.assertEqual(result["conflicts"], 1)

    def test_provider_failure_does_not_disclose_exception_secrets(self):
        with patch("reconcile.matterport_rooms", side_effect=RuntimeError("https://x?key=secret")), \
             patch("reconcile.check_flood", side_effect=RuntimeError("token=secret")):
            result = reconcile(prop(captions=["9700 Tanner Road"]))
        self.assertNotIn("secret", json.dumps(result))
        self.assertIn("fema", result["errors"])

    def test_no_scan_is_an_explicit_unknown(self):
        [r] = check_identity(prop())
        self.assertIsNone(r["value"])
        self.assertEqual(r["status"], "unknown")


class FloodEvidence(unittest.TestCase):
    def test_invalid_coordinates_do_not_query_fema(self):
        p = prop()
        p["primaryAddress"]["latitude"] = None
        with patch("reconcile.urlopen") as network:
            [r] = check_flood(p)
        network.assert_not_called()
        self.assertEqual(r["status"], "unknown")

    def test_multiple_zones_retained_and_missing_flag_is_not_outside(self):
        response = {"features": [{"attributes": {"FLD_ZONE": "X"}},
                                 {"attributes": {"FLD_ZONE": "AE", "SFHA_TF": "T"}}]}
        with patch("reconcile.urlopen") as network:
            network.return_value.__enter__.return_value.read.return_value = json.dumps(response).encode()
            records = check_flood(prop())
        self.assertEqual([r["value"] for r in records], ["X", "AE"])
        self.assertIn("flag unavailable", records[0]["note"])
        self.assertNotIn("outside", records[0]["note"])

    def test_service_error_is_not_misrepresented_as_unmapped(self):
        with patch("reconcile.urlopen") as network:
            network.return_value.__enter__.return_value.read.return_value = b'{"error":{"code":500}}'
            with self.assertRaises(RuntimeError):
                check_flood(prop())


if __name__ == "__main__":
    unittest.main()

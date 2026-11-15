import unittest
from approvals_timeline import analyze_approvals, build_timeline


class ApprovalTests(unittest.TestCase):
    def test_houston_does_not_clear_site(self):
        result = analyze_approvals("9700 Tanner Rd, Houston, TX 77041", "pickleball", [])
        self.assertFalse(result["jurisdiction_verified"])
        self.assertFalse(result["site_approval_verified"])
        self.assertIn("absence of conventional zoning", result["findings"][0]["statement"])
        self.assertEqual(result["actions"][0]["title"], "Confirm which authority controls this parcel")
        self.assertTrue(any("deed restrictions" in a["request"] for a in result["actions"]))
        self.assertTrue(all(r["scope"] == "general municipal guidance" for r in result["evidence"]))

    def test_la_has_parcel_and_record_actions(self):
        result = analyze_approvals("1048 Manzanita St, Los Angeles, CA 90029", "fitness studio", [])
        self.assertTrue(any("ZIMAS" in a["request"] for a in result["actions"]))
        self.assertTrue(any("Certificate of Occupancy" in a["request"] for a in result["actions"]))
        self.assertFalse(result["jurisdiction_verified"])

    def test_census_and_listing_are_not_jurisdiction(self):
        records = [{"source": "public:census", "source_id": "census-geocode", "status": "agrees",
                    "value": {"address": "LOS ANGELES CA", "tract": "06037195001"}},
                   {"source": "costar", "source_id": "property-1", "value": {"zoningDescription": "C2"}}]
        result = analyze_approvals("1 Main St, Los Angeles, CA 90012", "fitness", records)
        self.assertFalse(result["jurisdiction_verified"])
        self.assertTrue(any("CoStar records zoning as C2" in f["statement"] for f in result["findings"]))

    def test_explicit_official_boundary_proof(self):
        proof = {"source": "public:houston", "source_id": "municipal-jurisdiction", "status": "agrees",
                 "evidence_url": "https://www.houstontx.gov/boundary",
                 "value": {"jurisdiction": "City of Houston", "verified": True, "method": "point_in_polygon"}}
        result = analyze_approvals("1 Main St, Houston, TX 77001", "warehouse", [proof])
        self.assertTrue(result["jurisdiction_verified"])
        self.assertFalse(result["site_approval_verified"])
        proof["evidence_url"] = "https://houstontx.gov.evil.example/boundary"
        self.assertFalse(analyze_approvals("1 Main St, Houston, TX 77001", "warehouse", [proof])["jurisdiction_verified"])

    def test_outside_city_is_not_la(self):
        result = analyze_approvals("1 Main St, Pasadena, CA 91101", "warehouse", [])
        self.assertIsNone(result["guidance_market"])
        self.assertEqual(result["evidence"], [])

    def test_schedule_matches_finance_month_convention(self):
        timeline = build_timeline({"permit_months": 2, "build_months": 3, "delay_months": 3})
        self.assertEqual(timeline["opening_month"], 9)
        self.assertEqual(timeline["baseline_opening_month"], 6)
        self.assertEqual(timeline["phases"][1]["start_month"], 6)
        self.assertEqual(build_timeline({"permit_months": 0, "build_months": 0})["opening_month"], 1)
        self.assertIsNone(build_timeline()["opening_month"])

    def test_bad_schedule_values_rejected(self):
        for value in (-1, 1.5, float("nan"), float("inf"), True, "3", 121):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_timeline({"permit_months": value, "build_months": 1})

    def test_use_specific_next_checks(self):
        for use, phrase in (("restaurant", "food-service"), ("daycare", "childcare")):
            result = analyze_approvals("1 Main St, Houston, TX 77001", use, [])
            self.assertTrue(any(phrase in a["title"] for a in result["actions"]))


if __name__ == "__main__":
    unittest.main()

"""Tests for the budget-first venture pieces: cash to open, the opportunity scan and the deep review."""
import unittest
from unittest import mock

import neighborhood as nb
import opportunity as op
import venture_costs as vc
import venture_review as vr

SOURCE = [{"publisher_or_brand": "Test Brand", "document": "2025 FDD Item 7", "url": "https://example.test/fdd",
           "quote": "Leasehold improvements $100,000 to $200,000"}]
FAKE = {
    "fitness_gym": {"sources": SOURCE, "typical_sf": [4000, 6000], "scales": ["leasehold_improvements", "equipment_ffe"],
                    "build_months": 3,
                    "line_items": {"leasehold_improvements": [100000, 200000], "equipment_ffe": [50000, 100000],
                                   "signage": [10000, 20000], "additional_funds_working_capital": [30000, 50000]},
                    "franchise_fee": [40000, 40000]},
    "car_wash": {"sources": SOURCE, "comparable": False, "note": "Ground-up builds including land only."},
}


class CashToOpen(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(vc, "costs", lambda: FAKE)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_scales_build_out_and_equipment_by_size_and_adds_lease_lines(self):
        out = vc.cash_to_open("fitness_gym", 10000, 10000, budget=1_000_000, reserve=50000)
        lines = {line["id"]: line for line in out["lines"]}
        # typical 5,000 sq ft -> factor 2 for build-out and (scaling) equipment
        self.assertEqual(lines["leasehold_improvements"]["low"], 200000)
        self.assertEqual(lines["equipment_ffe"]["high"], 200000)
        self.assertEqual(lines["signage"]["base"], 15000)              # fixed lines stay as listed
        self.assertEqual(lines["lease_deposit"]["base"], 20000)        # 2 months
        self.assertEqual(lines["rent_during_buildout"]["base"], 30000)  # 3 months
        base = 300000 + 150000 + 15000 + 40000 + 20000 + 30000
        self.assertEqual(out["cash_to_open"]["base"], base)
        self.assertEqual(out["required"]["base"], base + 50000)
        self.assertEqual(out["affordability"], "within")
        self.assertEqual(out["months_of_rent_after_opening"], round((1_000_000 - base - 50000) / 10000, 1))
        self.assertEqual(out["franchise_fee_excluded"], [40000, 40000])

    def test_affordability_cases(self):
        self.assertEqual(vc.cash_to_open("fitness_gym", 5000, 5000, budget=100000)["affordability"], "over")
        base = vc.cash_to_open("fitness_gym", 5000, 5000, budget=None)
        stretch_budget = (base["required"]["low"] + base["required"]["base"]) / 2
        self.assertEqual(vc.cash_to_open("fitness_gym", 5000, 5000, budget=stretch_budget)["affordability"], "stretch")
        unknown = vc.cash_to_open("fitness_gym", 5000, None, budget=10_000_000)
        self.assertEqual(unknown["affordability"], "rent_unknown")  # fits before rent; rent must still be added
        self.assertIn("Rent unknown", unknown["note"])
        self.assertEqual(vc.cash_to_open("fitness_gym", 5000, None, budget=1000)["affordability"], "over")

    def test_non_comparable_benchmark_is_unknown(self):
        out = vc.cash_to_open("car_wash", 3000, 5000, budget=1e9)
        self.assertEqual(out["affordability"], "unknown")
        self.assertIn("Ground-up", out["note"])
        self.assertEqual(vc.cash_to_open("dental", 2000, 4000, budget=1e9)["affordability"], "unknown")

    def test_flip(self):
        out = vc.cash_to_open("fitness_gym", 5000, 5000, budget=200000)
        self.assertGreater(vc.flip(out, 200000)["extra_cash"], 0)
        self.assertIsNone(vc.flip(vc.cash_to_open("fitness_gym", 5000, 5000, budget=1e9), 1e9))


class RentFor(unittest.TestCase):
    def test_listed_then_estimate_then_unknown(self):
        self.assertEqual(vc.rent_for({"monthly_rent": 8000, "rent_psf_year": 9.6, "lease_basis": "NNN"})["kind"], "listed")
        est = {"spaces": {"7": {"low": 8.0, "typical": 12.0, "high": 16.0}}}
        with mock.patch.object(vc, "rent_estimates", lambda: est):
            out = vc.rent_for({"monthly_rent": None, "space_id": 7, "sf": 1000})
            self.assertEqual(out["kind"], "estimate")
            self.assertEqual(out["monthly"], 1000)
            self.assertEqual(vc.rent_for({"monthly_rent": None, "space_id": 8, "sf": 1000})["kind"], "unknown")


def market():
    building = {"property_id": 1, "address": "1 Test Rd, Houston, TX", "lat": 29.8, "lon": -95.4,
                "facts": {}, "evidence_flags": [], "tours": 1,
                "spaces": [{"value": "A", "suite": "A", "sf": 5000, "monthly_rent": 5000, "rent_psf_year": 12,
                            "lease_basis": "NNN", "space_id": 1},
                           {"value": "B", "suite": "B", "sf": 50000, "monthly_rent": 50000, "rent_psf_year": 12,
                            "lease_basis": "NNN", "space_id": 2}]}
    demand = {"verdict": "supported", "score": 2, "insight": None, "basis": "", "reasons": ["gap"], "lookalike": 80,
              "validated": True}
    weak = dict(demand, verdict="weak", score=-2)
    fit = {"status": "fits", "capacity": None, "reasons": [], "unknowns": []}
    index = {1: {"property_id": 1, "demand": {"fitness_gym": demand, "car_wash": weak},
                 "fits": {"A": {"fitness_gym": fit, "car_wash": dict(fit, status="no")},
                          "B": {"fitness_gym": fit, "car_wash": fit}}}}
    return {1: building}, index


class Scan(unittest.TestCase):
    def test_funnel_and_gates_in_order(self):
        with mock.patch.object(op, "load_index", lambda kit=None: market()), \
                mock.patch.object(vc, "costs", lambda: FAKE), \
                mock.patch.object(op, "INDUSTRIES", {k: nb.INDUSTRIES[k] for k in ("fitness_gym", "car_wash")}):
            out = op.scan(700000, 50000)
        f = out["funnel"]
        self.assertEqual((f["spaces"], f["combinations"], f["building_can_host"]), (2, 4, 3))
        # suite B (50,000 sq ft gym) is over budget; car wash has no comparable benchmark, so it is never
        # counted as affordable: it goes to "cost not estimated" (and its weak demand keeps it off that list)
        self.assertEqual(f["affordable"], 1)
        self.assertEqual(f["cost_not_estimated"], 1)
        self.assertEqual(out["cost_not_estimated"], [])
        self.assertEqual(f["neighborhood_support"], 1)
        self.assertEqual(out["pairs"][0]["suite"], "A")
        self.assertEqual(out["directions"][0]["business"], "fitness_gym")
        # the map: one dot per building, lit up to the furthest gate any pair there passed
        self.assertEqual(len(out["map"]["buildings"]), 1)
        self.assertEqual(out["map"]["buildings"][0][2], 3)
        self.assertEqual(out["map"]["after_gate"], [1, 1, 1, 1])

    def test_radius_and_exclusions(self):
        with mock.patch.object(op, "load_index", lambda kit=None: market()), \
                mock.patch.object(vc, "costs", lambda: FAKE):
            self.assertEqual(op.scan(1e9, center=(25.0, -80.0), radius_mi=5)["funnel"]["spaces"], 0)
            out = op.scan(1e9, exclude=["fitness_gym"])
        self.assertNotIn("fitness_gym", [d["business"] for d in out["directions"]])


def compliance_report(code, gates=()):
    """A compliance-engine report as Jayant's check_business returns it (only the fields the review reads)."""
    where = {"code": code, "verified": code is not None, "place": "Houston city" if code == "houston" else None,
             "county": "Harris County", "evidence_url": "https://geocoding.test/x" if code else None,
             "retrieved_at": "2026-11-15T00:00:00+00:00", "note": "test boundary" if code else "offline, not cached"}
    return {"jurisdiction": where, "gates": list(gates), "research": [], "authority": "Test authority",
            "records": [{"fact": "occupancy", "value": None, "source": "public:compliance-triage",
                         "source_id": "occupancy", "captured_at": None, "confidence": None, "evidence_url": None,
                         "status": "unknown", "needs_human": True, "note": "Retrieve approved occupancy"}]}


class Verdict(unittest.TestCase):
    def run_review(self, fit_status="fits", demand="supported", budget=1_000_000, where="houston", gates=()):
        building, _ = market()
        b = building[1]
        decision = {"verdict": demand, "headline": "h", "reasons": [{"signal": "lookalike", "stance": 1, "reason": "r"}],
                    "unknown": [], "building": {"status": fit_status, "capacity": "up to 5", "reasons": ["Not a typical fit"]
                                                if fit_status == "no" else ["ok"], "unknowns": ["measure height"]
                                                if fit_status == "check" else [], "verify": ["floor load"]}}
        hood = {"decisions": [decision], "trace": [{"agent": "site", "findings": []}], "narration": None,
                "narration_label": None}
        with mock.patch.object(vr, "find_space", lambda pid, suite, kit, key=None: (b, b["spaces"][0])), \
                mock.patch.object(nb, "investigate", lambda *a, **k: hood), \
                mock.patch.object(vc, "costs", lambda: FAKE), \
                mock.patch.object(vr, "property_record", lambda pid, kit="": {"id": 1, "attachments": []}), \
                mock.patch.object(vc, "rent_estimates", lambda: None), \
                mock.patch.object(vr, "compliance", lambda *a, **k: compliance_report(where, gates)):
            return vr.review("fitness_gym", 1, "A", budget=budget, reserve=50000)

    def test_go_needs_everything_clear(self):
        out = self.run_review()
        self.assertEqual(out["verdict"], "GO")
        self.assertEqual([s["agent"] for s in out["trace"]][-1], "verdict")
        self.assertTrue(out["pillars"]["permits"])

    def test_conditional_and_no_go(self):
        self.assertEqual(self.run_review(fit_status="check")["verdict"], "CONDITIONAL")
        self.assertEqual(self.run_review(demand="mixed")["verdict"], "CONDITIONAL")
        out = self.run_review(fit_status="no")
        self.assertEqual(out["verdict"], "NO-GO")
        self.assertEqual(self.run_review(demand="weak")["verdict"], "NO-GO")
        poor = self.run_review(budget=100000)
        self.assertEqual(poor["verdict"], "NO-GO")
        self.assertIn("exceeds", poor["blockers"][0])



class FindSpace(unittest.TestCase):
    def test_picks_the_space_that_suits_the_business_not_the_biggest(self):
        building = {"property_id": 1, "spaces": [{"value": "A", "sf": 1600, "executive_suite": False},
                                                 {"value": "B", "sf": 27750, "executive_suite": False},
                                                 {"value": "C", "sf": 700, "executive_suite": True}]}
        with mock.patch("opportunity.load_market", lambda kit=None: [building]):
            self.assertEqual(vr.find_space(1, None, None, "yoga_pilates")[1]["value"], "A")
            self.assertEqual(vr.find_space(1, None, None, "self_storage")[1]["value"], "B")
            self.assertEqual(vr.find_space(1, "C", None, "yoga_pilates")[1]["value"], "C")  # an explicit choice wins


class Store(unittest.TestCase):
    def test_create_update_list_and_validation(self):
        import tempfile
        from pathlib import Path
        import ventures
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ventures, "ROOT", Path(tmp)):
            v = ventures.create("demo", "budget")
            self.assertEqual(v["stage"], "budget")
            ventures.update("demo", v["id"], {"stage": "scan", "inputs": {"budget": 500000}})
            self.assertEqual(ventures.get("demo", v["id"])["inputs"]["budget"], 500000)
            self.assertEqual(len(ventures.all_for("demo")), 1)
            with self.assertRaises(ValueError):
                ventures.update("demo", v["id"], {"stage": "nowhere"})
            with self.assertRaises(ValueError):
                ventures.update("demo", v["id"], {"user": "someone-else"})
            with self.assertRaises(ValueError):
                ventures.get("../etc", v["id"])
            with self.assertRaises(KeyError):
                ventures.get("demo", "missing")


if __name__ == "__main__":
    unittest.main()


class Because(unittest.TestCase):
    """The 'why this verdict' rows: same values as the verdict, every blocker and condition shown, evidence linked."""
    run_review = Verdict.run_review

    def check_shape(self, out):
        self.assertTrue(out["because"])
        for row in out["because"]:
            self.assertIn(row["effect"], {"blocks", "check", "supports", "unknown"})
            self.assertTrue(row["text"] and row["agent"])
            self.assertEqual(set(row["signal"]), {"name", "value", "rule"})
            self.assertTrue(all(0 <= i < len(out["evidence"]) for i in row["evidence"]))
            self.assertEqual(set(row["source"]), {"name", "url", "retrieved_at", "confidence"})
        deciding = {r["effect"] for r in out["because"] if r["decides"]}
        for text in out["blockers"]:
            self.assertTrue(any(r["effect"] == "blocks" and text[:40] in r["text"] for r in out["because"]), text)
        for text in out["conditions"]:
            self.assertTrue(any(r["effect"] == "check" and r["decides"] and text[:40] in r["text"]
                                for r in out["because"]), text)
        return deciding

    def test_go_has_only_supporting_deciding_rows(self):
        out = self.run_review()
        self.assertEqual(out["verdict"], "GO")
        self.assertEqual(self.check_shape(out), {"supports"})
        agents = {r["agent"] for r in out["because"] if r["effect"] == "supports"}
        self.assertTrue({"building", "money", "coordinator", "permits"} <= agents)
        money = next(r for r in out["because"] if r["agent"] == "money" and r["decides"])
        self.assertIn("<=", money["signal"]["rule"])
        self.assertTrue(money["evidence"])
        self.assertEqual(money["source"]["url"], "https://example.test/fdd")

    def test_blocks_and_checks_match_the_verdict(self):
        poor = self.run_review(budget=100000)
        self.assertEqual(poor["verdict"], "NO-GO")
        self.assertIn("blocks", self.check_shape(poor))
        self.assertEqual(poor["because"][0]["effect"], "blocks")  # blocks sort first
        mixed = self.run_review(demand="mixed")
        self.assertIn("check", self.check_shape(mixed))
        self.assertNotIn("blocks", self.check_shape(mixed))

    def test_unincorporated_harris_is_a_check_and_switches_the_authority(self):
        out = self.run_review(where="harris_unincorporated")
        self.assertEqual(out["verdict"], "CONDITIONAL")
        self.check_shape(out)
        row = next(r for r in out["because"] if r["agent"] == "permits")
        self.assertEqual(row["effect"], "check")
        self.assertIn("Harris County does", row["text"])
        self.assertTrue(all("Harris County" in s["authority"] for s in out["pillars"]["permits"][:2]))
        self.assertNotIn("approved", " ".join(s["title"] + s["detail"] for s in out["pillars"]["permits"]).lower())

    def test_unverified_jurisdiction_stays_unknown_without_changing_the_verdict(self):
        out = self.run_review(where=None)
        self.assertEqual(out["verdict"], "GO")
        row = next(r for r in out["because"] if r["agent"] == "permits")
        self.assertEqual(row["effect"], "unknown")
        self.assertIn("assumption", row["text"])

    def test_residential_gate_blocks(self):
        out = self.run_review(gates=("commercial_conversion_unestablished",))
        self.assertEqual(out["verdict"], "NO-GO")
        self.check_shape(out)


class SignalGuide(unittest.TestCase):
    def test_thresholds_come_from_the_code(self):
        import signal_guide as sg
        with mock.patch.object(nb, "industry_catalog", lambda: [
                {"key": "yoga_pilates", "label": "Yoga", "lookalike_auc": 0.83, "validated": True},
                {"key": "childcare", "label": "Childcare", "lookalike_auc": 0.52, "validated": False}]), \
                mock.patch.object(sg, "rent_estimates", lambda: None):
            g = sg.guide()
        self.assertEqual(g["thresholds"]["validated_auc"], nb.VALIDATED_AUC)
        self.assertEqual(g["thresholds"]["lookalike_plus"], nb.LOOKALIKE_PLUS)
        supply = next(s for s in g["signals"] if s["name"] == "local supply")
        self.assertIn(f"{nb.SUPPLY_UNDER:g}x", supply["supports"])
        self.assertIn(f"p < {nb.SUPPLY_P:g}", supply["supports"])
        self.assertEqual([r["business"] for r in g["lookalike_accuracy"]], ["yoga_pilates", "childcare"])
        self.assertFalse(g["lookalike_accuracy"][1]["votes"])
        self.assertIsNone(g["rent_accuracy"])
        for s in g["signals"]:
            self.assertTrue(all(s[k] for k in ("measures", "source", "supports", "against", "unknown", "accuracy")))

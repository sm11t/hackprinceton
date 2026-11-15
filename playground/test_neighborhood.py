"""Tests for the neighborhood demand pipeline. No network: tables are synthetic or patched."""
import hashlib
import json
import math
import os
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import neighborhood as n
import neighborhood_industries as ind
import neighborhood_tools as tools


def tract(geoid, lat, lon, pop, income=60000, households=None, land=1.0, renters=None, **bands):
    hh = households if households is not None else pop / 3
    row = {"geoid": geoid, "lat": lat, "lon": lon, "land_sqmi": land, "pop": pop, "pop_moe": 100,
           "households": hh, "income": income, "occupied": hh, "renters": renters if renters is not None else hh / 2}
    for band in n.AGE_BANDS:
        row[band] = bands.get(band, pop / len(n.AGE_BANDS))
    return row


NEW = (tract("1", 29.80, -95.40, 4000, 100000), tract("2", 29.81, -95.40, 6000, 50000),
       tract("3", 30.30, -95.40, 5000, 40000))
OLD = (tract("a", 29.80, -95.40, 9000), tract("b", 30.30, -95.40, 4000))
CACHED = [n.area_profile, n.area_totals, n.reference_profiles, n.reference_values, n.tract_index]


class FakeTables:
    """Swap the Census tables for small synthetic ones and use a temp cache."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        tables = {2024: (NEW, ()), 2019: (OLD, ())}
        self.patches = [
            mock.patch.object(n, "tract_table", lambda year: tables[year]),
            mock.patch.object(n, "CACHE", Path(self.tmp.name)),
            mock.patch.object(n, "census_sources", lambda year: [
                {"name": f"src{i}", "url": f"https://example.test/{year}/{i}", "retrieved_at": "t", "cached": True,
                 "note": ""} for i in range(3)]),
            mock.patch.object(n, "us_population_6_plus_record",
                              lambda: ({"url": "https://example.test/us", "retrieved_at": "t", "cached": True},
                                       300_000_000)),
        ]
        for p in self.patches:
            p.start()
        for fn in CACHED:
            fn.cache_clear()
        return self

    def __exit__(self, *exc):
        for p in self.patches:
            p.stop()
        for fn in CACHED:
            fn.cache_clear()
        self.tmp.cleanup()


class Basics(unittest.TestCase):
    def test_miles(self):
        self.assertAlmostEqual(n.miles(29.0, -95.0, 30.0, -95.0), 69.1, delta=0.2)

    def test_grid_index_matches_brute_force(self):
        rng = random.Random(3)
        rows = [{"lat": 29.5 + rng.random(), "lon": -95.9 + rng.random()} for _ in range(800)]
        index = n.GridIndex(rows)
        for _ in range(20):
            lat, lon, radius = 29.5 + rng.random(), -95.9 + rng.random(), rng.choice([0.5, 3, 7.5])
            brute = {id(r) for r in rows if n.miles(lat, lon, r["lat"], r["lon"]) <= radius}
            self.assertEqual({id(r) for _, r in index.near(lat, lon, radius)}, brute)

    def test_percentile_counts_half_ties_and_ignores_unknown(self):
        self.assertEqual(n.percentile(5, [1, 5, 9, None]), 50)
        self.assertIsNone(n.percentile(None, [1, 2]))
        self.assertIsNone(n.percentile(1, [None]))

    def test_stance(self):
        self.assertEqual(n.stance(0.05, plus=0.02, minus=-0.02), 1)
        self.assertEqual(n.stance(0.0, plus=0.02, minus=-0.02), 0)
        self.assertEqual(n.stance(-0.05, plus=0.02, minus=-0.02), -1)
        self.assertIsNone(n.stance(None, plus=1, minus=0))

    def test_public_url_never_contains_key(self):
        url = n.public_url("https://api.census.gov/x", {"get": "A", "key": "SECRET"})
        self.assertNotIn("SECRET", url)
        self.assertIn("get=A", url)

    def test_offline_without_cache_raises_and_cache_is_read(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(n, "CACHE", Path(tmp)), \
                mock.patch.dict(os.environ, {"NEIGHBORHOOD_OFFLINE": "1"}):
            with self.assertRaises(n.Offline):
                n.fetch("https://example.test/a", {"q": 1})
            shown = n.public_url("https://example.test/a", {"q": 1, "key": "k"})
            digest = hashlib.sha1((shown + "|" + json.dumps(None)).encode()).hexdigest()[:20]
            (Path(tmp) / "http").mkdir()
            (Path(tmp) / "http" / f"{digest}.json").write_text(
                json.dumps({"url": shown, "retrieved_at": "2026-11-14T00:00:00+00:00", "payload": [1]}))
            payload, meta = n.fetch("https://example.test/a", {"q": 1, "key": "k"})
            self.assertEqual(payload, [1])
            self.assertTrue(meta["cached"])

    def test_run_agent_records_errors_as_unknown(self):
        trace = []

        def broken():
            raise n.Offline("no cache")
        step = n.run_agent(trace, "x", "role", broken, {})
        self.assertEqual(step["status"], "unknown")
        self.assertIn("nothing was guessed", step["handoff"])

    def test_per_industry_isolates_failures(self):
        def fn(key):
            if key == "bad":
                raise RuntimeError("boom")
            return {"signal": {"stance": 1}}
        out = n.per_industry(["good", "bad"], fn)
        self.assertEqual(out["good"]["signal"]["stance"], 1)
        self.assertEqual(out["bad"]["status"], "error")
        self.assertIsNone(out["bad"]["signal"])


class Registry(unittest.TestCase):
    def test_every_industry_is_complete(self):
        for key, spec in ind.INDUSTRIES.items():
            for field in ("label", "group", "osm", "names", "cluster_mi", "synonyms"):
                self.assertIn(field, spec, key)
            self.assertTrue(spec["osm"], key)
            self.assertIn(spec["demand_band"], (None, "under_5", "age_5_17"), key)
            for selector in spec["osm"]:
                self.assertTrue(selector.startswith("nwr["), selector)
        for key in ind.CATALOG_TO_INDUSTRY.values():
            self.assertIn(key, ind.INDUSTRIES)

    def test_resolve(self):
        cases = {"bouldering gym": "climbing_gym", "I want to open a daycare": "childcare", "hot yoga": "yoga_pilates",
                 "coffee": "cafe", "boxing gym": "martial_arts", "dog grooming": "pet_services",
                 "storage units": "self_storage", "indoor pickleball": "indoor_pickleball",
                 "fitness studio": "fitness_gym", "laundromat": "laundromat", "Car wash": "car_wash",
                 "pizza place": "fast_food", "vet clinic": "veterinary"}
        for text, key in cases.items():
            self.assertEqual(ind.resolve(text)[0], key, text)
        self.assertIsNone(ind.resolve("spaceship factory")[0])
        self.assertIsNone(ind.resolve("")[0])

    def test_tenant_names(self):
        cases = {"JETSET Modern Pilates": ["yoga_pilates"], "Happy Kids Preschool": ["childcare"],
                 "Petroleum Wholesale": [], "ABC Marketing": [], "Golf Design": [], "Starbucks": ["cafe"],
                 "Bright Smiles Dental": ["dental"], "Discount Tire": ["auto_repair"], "Kumon Math": ["tutoring"],
                 "Pinnacle - Primrose at Heritage Park Apartments": [], "The Lincoln Law Firm": []}
        for name, keys in cases.items():
            self.assertEqual(ind.industries_for_tenant(name), keys, name)


class Residents(unittest.TestCase):
    def test_area_profile_sums_tracts_in_radius(self):
        with FakeTables():
            p = n.area_profile(29.80, -95.40, 3)
        self.assertEqual(p["tracts"], 2)
        self.assertEqual(p["population"], 10000)
        self.assertEqual(p["median_income_approx"], 70000)  # household-weighted mean of 100k and 50k
        self.assertEqual(p["population_2019"], 9000)
        self.assertAlmostEqual(p["growth"], 10000 / 9000 - 1, places=3)
        self.assertAlmostEqual(p["share_renters"], 0.5)

    def test_area_profile_none_when_no_tracts(self):
        with FakeTables():
            self.assertIsNone(n.area_profile(25.0, -80.0, 3))

    def test_residents_agent_shared_records_and_per_industry_signals(self):
        with FakeTables():
            out = n.residents_agent(29.80, -95.40, ["indoor_pickleball", "childcare"])
        facts = {r["fact"]: r for r in out["findings"]}
        self.assertEqual(facts["residents_population"]["value"], 10000)
        # Area growth +11.1% vs Houston-area (15000/13000 = +15.4%) -> trails by 4 points
        self.assertEqual(out["per_industry"]["indoor_pickleball"]["signal"]["stance"], -1)
        self.assertEqual(facts["indoor_pickleball.expected_participants_at_national_rate"]["value"],
                         round(10000 * 24_300_000 / 300_000_000))
        self.assertIn("childcare.residents_under_5", facts)
        self.assertTrue(out["per_industry"]["childcare"]["signal"]["reason"].startswith("Under-5"))
        for r in out["findings"]:
            self.assertEqual(set(r), {"fact", "value", "source", "source_id", "captured_at", "confidence",
                                      "evidence_url", "status", "needs_human", "note"})


def facility(lat, lon, name=None, indoor=False, commercial=False, osm="node/1"):
    return {"lat": lat, "lon": lon, "name": name, "indoor": indoor, "commercial": commercial,
            "osm_ids": [osm], "features": 1, "osm_id": osm}


def fake_facilities(rows):
    meta = {"url": "https://overpass.test", "retrieved_at": "2026-11-14T00:00:00", "cached": True}
    return lambda key: (rows, meta, n.GridIndex(rows))


class Competitors(unittest.TestCase):
    def test_cluster_merges_courts_but_keeps_named_neighbours_apart(self):
        points = [facility(29.8, -95.4, None, osm="way/1"), facility(29.8005, -95.4, None, osm="way/2"),
                  facility(29.8, -95.4005, "Club A", True, True, "way/3"), facility(29.8, -95.401, "Club B", osm="n/4")]
        out = n.cluster(points, 0.15)
        self.assertEqual(sorted(f["name"] for f in out), ["Club A", "Club B"])
        club_a = next(f for f in out if f["name"] == "Club A")
        self.assertEqual(club_a["features"], 3)
        self.assertTrue(club_a["indoor"])

    def test_cluster_zero_radius_merges_only_duplicates(self):
        points = [facility(29.8, -95.4, "Cafe A", osm="n/1"), facility(29.8001, -95.4, "Cafe A", osm="w/1"),
                  facility(29.801, -95.4, "Cafe A", osm="n/2")]
        self.assertEqual(len(n.cluster(points, 0.0)), 2)  # node+outline merge; a branch 0.07 mi away stays

    def test_competitors_agent_counts_ratio_and_stance(self):
        rows = [facility(29.80, -95.40, "A", osm="n/1"), facility(29.805, -95.40, "B", osm="n/2"),
                facility(30.30, -95.40, "C", osm="n/3")]
        with FakeTables(), mock.patch.object(n, "facilities", fake_facilities(rows)):
            out = n.competitors_agent(29.80, -95.40, ["indoor_pickleball"])
        facts = {r["fact"]: r for r in out["findings"]}
        self.assertEqual(facts["indoor_pickleball.competitors_within_radius"]["value"], 2)
        # Local: 2 per 10,000 residents; area: 3 per 15,000 = 2 per 10k -> ratio 1.0, neutral
        self.assertEqual(facts["indoor_pickleball.supply_per_10k_residents"]["value"], 2.0)
        self.assertEqual(out["per_industry"]["indoor_pickleball"]["signal"]["stance"], 0)
        self.assertEqual(facts["indoor_pickleball.nearest_competitor"]["value"]["name"], "A")

    def test_no_local_facilities_reads_underserved(self):
        with FakeTables(), mock.patch.object(n, "facilities", fake_facilities([facility(30.30, -95.40, "C")])):
            out = n.competitors_agent(29.80, -95.40, ["cafe", "dental"])
        self.assertEqual(out["per_industry"]["dental"]["signal"]["stance"], 1)
        self.assertIn("Underserved: Dental office", out["summary"])
        cafe = out["per_industry"]["cafe"]["signal"]
        self.assertEqual(cafe["stance"], 0)           # cafes cluster on purpose: supply does not vote
        self.assertIn("cluster on purpose", cafe["reason"])


class Momentum(unittest.TestCase):
    def test_kit_tenancies_arrival_and_departure_rules(self):
        with tempfile.TemporaryDirectory() as kit, tempfile.TemporaryDirectory() as cache, \
                mock.patch.object(n, "CACHE", Path(cache)):
            data = Path(kit) / "data"
            data.mkdir()
            (data / "commercial-property.jsonl").write_text(json.dumps(
                {"id": 1, "primaryAddress": {"state": "TX", "latitude": 29.8, "longitude": -95.4}}) + "\n")
            (data / "company-detail.jsonl").write_text(json.dumps({"id": 10, "name": "True North Yoga"}) + "\n")
            rows = [  # first lease, then a renewal: one arrival, and the renewal is not a departure
                {"id": 100, "propertyId": 1, "tenantLocationId": 10, "moveInDate": "2020-01-01",
                 "toDate": "2024-12-31", "expirationReason": 7},
                {"id": 101, "propertyId": 1, "tenantLocationId": 10, "fromDate": "2025-01-01",
                 "toDate": "2026-03-01", "expirationReason": 4},
            ]
            (data / "location-occupancy.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            n.kit_tenancies.cache_clear()
            out = {r["id"]: r for r in n.kit_tenancies(kit)[0]}
            n.kit_tenancies.cache_clear()
        self.assertEqual(out[100]["arrival"], "2020-01-01")
        self.assertIsNone(out[100]["departure"])
        self.assertIsNone(out[101]["arrival"])
        self.assertEqual(out[101]["departure"], "2026-03-01")
        self.assertEqual(out[100]["industries"], ["yoga_pilates"])

    def tenancy(self, name, arrival=None, departure=None, lat=29.8):
        return {"id": name, "property_id": 1, "lat": lat, "lon": -95.4, "name": name,
                "industries": ind.industries_for_tenant(name), "arrival": arrival, "departure": departure,
                "sqft": 2000}

    def kit(self, rows):
        return lambda kit=None: (rows, n.GridIndex(rows))

    def test_momentum_counts_recent_moves_per_industry(self):
        rows = (self.tenancy("Club Pilates", "2025-02-01"), self.tenancy("Yoga One", "2026-04-01"),
                self.tenancy("Hot Yoga Lab", None, "2024-05-01"), self.tenancy("Ancient Yoga", "2015-01-01"),
                self.tenancy("Far Yoga", "2025-01-01", lat=31.0), self.tenancy("Law Office", "2025-03-01"))
        with mock.patch.object(n, "kit_tenancies", self.kit(rows)):
            out = n.momentum_agent(29.8, -95.4, ["yoga_pilates", "childcare"], today="2026-11-14")
        yoga = out["per_industry"]["yoga_pilates"]
        self.assertEqual(yoga["signal"]["value"], 1)  # 2 in, 1 out
        self.assertEqual(yoga["signal"]["stance"], 1)
        self.assertEqual([e["name"] for e in yoga["examples"]], ["Yoga One", "Club Pilates"])
        self.assertIsNone(out["per_industry"]["childcare"]["signal"]["stance"])  # no moves: unknown
        by_year = {r["fact"]: r for r in out["findings"]}["yoga_pilates.kit_arrivals_by_year"]["value"]
        self.assertNotIn(2015, by_year)


    def test_momentum_falls_back_to_the_group_and_says_so(self):
        rows = (self.tenancy("Club Pilates", "2025-02-01"), self.tenancy("Iron Gym", "2026-01-10"))
        with mock.patch.object(n, "kit_tenancies", self.kit(rows)):
            out = n.momentum_agent(29.8, -95.4, ["indoor_pickleball"], today="2026-11-14")
        signal = out["per_industry"]["indoor_pickleball"]["signal"]
        self.assertEqual(signal["value"], 2)
        self.assertIn("sports & fitness businesses (too few indoor pickleball moves alone)", signal["reason"])


class Lookalike(unittest.TestCase):
    def test_auc(self):
        self.assertEqual(n.auc([3, 4], [1, 2]), 1.0)
        self.assertEqual(n.auc([1], [1]), 0.5)
        self.assertAlmostEqual(n.auc([2, 0], [1]), 0.5)
        self.assertIsNone(n.auc([], [1]))

    def test_solve(self):
        self.assertEqual([round(v, 6) for v in n.solve([[2, 0], [0, 4]], [2, 8])], [1, 2])

    def test_fit_logistic_learns_direction(self):
        x = [[i / 10] for i in range(100)]
        y = [1 if i > 60 or i % 7 == 0 else 0 for i in range(100)]
        model = n.fit_logistic(x, y, l2=0.1)
        self.assertGreater(model["weights"][1], 0)
        self.assertGreater(n.model_logit(model, [9.0]), n.model_logit(model, [1.0]))

    def test_spatial_fold_is_stable_per_cell(self):
        self.assertEqual(n.spatial_fold(29.81, -95.41, 5), n.spatial_fold(29.82, -95.42, 5))

    def places(self, separable):
        rng = random.Random(1)
        pos = [{"lat": 29 + rng.random(), "lon": -95 - rng.random(),
                "x": [(5 if separable else 0) + rng.random(), 0.0], "positive": True} for _ in range(40)]
        bg = [{"lat": 29 + rng.random(), "lon": -95 - rng.random(), "x": [rng.random(), 0.0], "positive": False}
              for _ in range(200)]
        return pos, bg

    def test_cross_validation_separable_and_noise(self):
        fold = lambda r: n.spatial_fold(r["lat"], r["lon"], 5)  # noqa: E731
        pos, bg = self.places(True)
        held_pos, held_neg = n.cross_validate(pos, bg, [0], 5, fold)
        self.assertEqual(n.auc([s for s, _, _ in held_pos], held_neg), 1.0)
        pos, bg = self.places(False)
        held_pos, held_neg = n.cross_validate(pos, bg, [0], 5, fold)
        self.assertLess(abs(n.auc([s for s, _, _ in held_pos], held_neg) - 0.5), 0.15)

    def test_evaluate_refuses_too_few_facilities(self):
        with mock.patch.object(n, "training_data", lambda *a, **k: ([], [], 12)):
            out = n.evaluate("climbing_gym")
        self.assertEqual(out["status"], "too_few")
        self.assertFalse(out["validated"])

    def fake_eval(self, auc_value):
        model = {"mean": [0.0] * 8, "sd": [1.0] * 8, "weights": [0.0, 1.0] + [0.0] * 7, "features": list(n.FEATURES)}
        split = {"auc": auc_value, "auc_90ci": [auc_value - 0.04, auc_value + 0.04], "hit_rate_top30": 0.44,
                 "baseline_auc": {"income_only": 0.66, "density_only": 0.45, "shuffled_labels": 0.5}}
        return {"status": "ok", "model": model, "background_logits": [float(v) for v in range(11)],
                "facilities_used": 100, "facilities_mapped": 100, "background_places": 11,
                "evaluated_at": "2026-11-14T00:00:00+00:00", "validated": auc_value >= n.VALIDATED_AUC,
                "splits": {"spatial": split, "random": split}}

    def test_lookalike_agent_percentile_and_validation_gate(self):
        profile = {"density_per_sqmi": math.e ** 9 - 1, "median_income_approx": 1, "population": 1,
                   "share_renters": 0, "share_age_25_34": 0, "share_age_35_54": 0, "share_age_55_64": 0,
                   "share_age_65_plus": 0, "share_under_5": 0, "share_age_5_17": 0, "growth": 0}
        with mock.patch.object(n, "area_profile", lambda *a, **k: profile):
            with mock.patch.object(n, "lookalike_model", lambda key: self.fake_eval(0.64)):
                out = n.lookalike_agent(29.8, -95.4, ["indoor_pickleball"])
            signal = out["per_industry"]["indoor_pickleball"]["signal"]
            self.assertEqual(signal["value"], 86)  # logit 9 vs background 0..10 -> (9 + 0.5) / 11
            self.assertEqual(signal["stance"], 1)
            with mock.patch.object(n, "lookalike_model", lambda key: self.fake_eval(0.55)):
                out = n.lookalike_agent(29.8, -95.4, ["indoor_pickleball"])
            signal = out["per_industry"]["indoor_pickleball"]["signal"]
            self.assertIsNone(signal["stance"])
            self.assertIn("not used in the verdict", signal["reason"])


def sig(name, stance_value, value=None, validated=True):
    return {"name": name, "stance": stance_value, "value": value, "reason": name, "validated": validated}


class Coordinator(unittest.TestCase):
    def test_supported_needs_lookalike_and_total(self):
        d = n.coordinate("indoor_pickleball", [sig("lookalike", 1, 80), sig("population trend", 1),
                                               sig("local supply", 0)])
        self.assertEqual(d["verdict"], "supported")
        self.assertEqual(d["reasons"][0]["signal"], "lookalike")

    def test_weak_when_lookalike_is_low(self):
        d = n.coordinate("cafe", [sig("lookalike", -1, 20), sig("local supply", 1)])
        self.assertEqual(d["verdict"], "weak")
        self.assertIn("Few competitors", d["insight"])

    def test_unknown_without_validated_lookalike_or_enough_signals(self):
        d = n.coordinate("cafe", [sig("lookalike", None, 80), sig("population trend", 1), sig("local supply", 1)])
        self.assertEqual(d["verdict"], "unknown")
        self.assertEqual(n.coordinate("cafe", [sig("lookalike", 1, 80)])["verdict"], "unknown")

    def test_mixed_and_gap_insight(self):
        d = n.coordinate("fitness_gym", [sig("lookalike", 1, 75), sig("local supply", 1),
                                         sig("population trend", -1), sig("business arrivals", -1)])
        self.assertEqual(d["verdict"], "mixed")
        self.assertTrue(d["insight"].startswith("Gap"))


class Planner(unittest.TestCase):
    def test_plans(self):
        self.assertEqual(len(n.plan("suggest")["industries"]), len(ind.INDUSTRIES))
        self.assertEqual(n.plan("indoor pickleball")["industries"], ["indoor_pickleball"])
        self.assertEqual(n.plan("bouldering gym")["industries"], ["climbing_gym"])
        p = n.plan("warehouse / storage")
        self.assertEqual(p["industries"], [])
        self.assertIn("Business-to-business", p["not_modelled"]["warehouse / storage"])
        self.assertEqual(n.plan("spaceship factory")["unmatched"], "spaceship factory")


class Site(unittest.TestCase):
    def geocode(self, matches):
        payload = {"result": {"addressMatches": matches}}
        return lambda url, params=None, **k: (payload, {"url": "https://geocoding.test", "retrieved_at":
                                                         "2026-11-14T00:00:00+00:00", "cached": True})

    def test_address_geocodes_to_point(self):
        match = {"matchedAddress": "1 MAIN ST, HOUSTON, TX", "coordinates": {"x": -95.40, "y": 29.80},
                 "geographies": {"Census Tracts": [{"GEOID": "48201000100"}]}}
        with FakeTables(), mock.patch.object(n, "fetch", self.geocode([match])):
            out = n.site_agent(address="1 Main St, Houston, TX")
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["point"]["tract"], "48201000100")

    def test_ambiguous_or_outside_is_unknown(self):
        with FakeTables(), mock.patch.object(n, "fetch", self.geocode([])):
            self.assertEqual(n.site_agent(address="nowhere")["status"], "unknown")
        far = {"matchedAddress": "X", "coordinates": {"x": -80.0, "y": 25.0}, "geographies": {}}
        with FakeTables(), mock.patch.object(n, "fetch", self.geocode([far])):
            self.assertEqual(n.site_agent(address="Miami")["status"], "unknown")


class Narrator(unittest.TestCase):
    decision = {"use": "Indoor pickleball", "verdict": "weak", "insight": None,
                "reasons": [{"signal": "lookalike", "stance": -1, "reason": "22% of neighborhoods"}], "unknown": []}

    def run_with_reply(self, text):
        reply = mock.MagicMock()
        reply.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": text}}]}).encode()
        env = {"UPSTAGE_API_KEY": "test", "LLM_API_KEY": "", "NEIGHBORHOOD_OFFLINE": ""}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(n, "CACHE", Path(tmp)), \
                mock.patch.dict(os.environ, env), mock.patch.object(n, "urlopen", return_value=reply):
            return n.narrate([self.decision], "1 Main St")

    def test_accepts_text_with_only_known_numbers(self):
        text, step = self.run_with_reply("Weak: it resembles only 22% of neighborhoods with courts.")
        self.assertIsNotNone(text)
        self.assertTrue(step["computed_by"].startswith("llm"))

    def test_rejects_invented_numbers(self):
        text, step = self.run_with_reply("Weak, and about 5,000 players live nearby.")
        self.assertIsNone(text)
        self.assertEqual(step["status"], "rejected")

    def test_llm_config_prefers_team_contract(self):
        with mock.patch.dict(os.environ, {"LLM_API_KEY": "k", "LLM_BASE_URL": "https://openrouter.ai/api/v1/",
                                          "LLM_MODEL": "some/model"}):
            cfg = n.llm_config()
        self.assertEqual(cfg["base_url"], "https://openrouter.ai/api/v1")
        self.assertEqual(cfg["model"], "some/model")
        with mock.patch.dict(os.environ, {"LLM_API_KEY": "", "UPSTAGE_API_KEY": "u"}):
            self.assertIn("upstage", n.llm_config()["base_url"])


def fake_agent(name, stance_by_key, value_by_key=None):
    def agent(lat, lon, industries, **kw):
        per = {k: {"findings": [n.record(f"{k}.{name}", 1, "computed", status="agrees")],
                   "signal": {"name": name, "stance": stance_by_key(k), "validated": True,
                              "value": (value_by_key or (lambda k: None))(k), "reason": name},
                   "summary": name} for k in industries}
        return {"summary": name, "findings": n.flatten(per), "per_industry": per}
    return agent


class Pipeline(unittest.TestCase):
    def run_patched(self, request):
        site = lambda **kw: {"point": {"lat": 29.8, "lon": -95.4, "label": "X"}, "findings": [], "summary": "X"}  # noqa: E731
        specialists = [("residents", "r", fake_agent("population trend", lambda k: 1)),
                       ("competitors", "c", fake_agent("local supply", lambda k: 0)),
                       ("momentum", "m", fake_agent("business arrivals", lambda k: None)),
                       ("lookalike", "l", fake_agent("lookalike", lambda k: 1 if k == "cafe" else -1,
                                                     lambda k: 80 if k == "cafe" else 10))]
        with mock.patch.object(n, "site_agent", site), mock.patch.object(n, "SPECIALISTS", specialists):
            return n.investigate(request, address="X")

    def test_suggest_runs_each_specialist_once_and_ranks(self):
        report = self.run_patched("suggest")
        self.assertEqual(report["decisions"][0]["industry"], "cafe")
        self.assertEqual(report["decisions"][0]["verdict"], "supported")
        self.assertEqual(len(report["decisions"]), len(ind.INDUSTRIES))
        agents = [s["agent"] for s in report["trace"]]
        self.assertEqual(agents, ["planner", "site", "residents", "competitors", "momentum", "lookalike",
                                  "coordinator"])
        self.assertTrue(report["evidence"])
        self.assertEqual(report["trace"][2]["inputs"]["industries"], f"{len(ind.INDUSTRIES)} industries")

    def test_unmatched_request_runs_no_specialists(self):
        report = self.run_patched("spaceship factory")
        self.assertEqual(report["decisions"], [])
        self.assertEqual(report["unmatched"], "spaceship factory")
        self.assertEqual([s["agent"] for s in report["trace"]], ["planner", "site"])


class Tools(unittest.TestCase):
    def test_specs_and_dispatch(self):
        specs = tools.openai_tool_specs()
        self.assertEqual({s["function"]["name"] for s in specs}, set(tools.TOOLS))
        for s in specs:
            self.assertEqual(s["function"]["parameters"]["type"], "object")
            self.assertTrue(s["function"]["description"])
        out = tools.call("resolve_industry", {"description": "bouldering gym", "ignored": 1})
        self.assertEqual(out["industry"], "climbing_gym")

    def test_check_and_suggest_trim_the_report(self):
        decision = {"industry": "cafe", "use": "Coffee shop / cafe", "verdict": "mixed", "headline": "h",
                    "insight": None, "reasons": [{"signal": "lookalike", "stance": 0, "reason": "r"}], "unknown": [],
                    "lookalike_percentile": 50, "lookalike_validated": True}
        report = {"site": {"label": "X"}, "unmatched": None, "candidates": [], "not_modelled": {},
                  "decisions": [decision], "evidence": [n.record("cafe.x", 1, "computed", status="agrees")],
                  "trace": [{"agent": "site", "status": "ok", "ms": 1, "summary": "X"}], "elapsed_ms": 3}
        tools._run.cache_clear()
        with mock.patch.object(n, "investigate", lambda *a, **k: report):
            out = tools.check_neighborhood("cafe", property_id=1)
            self.assertEqual(out["decisions"][0]["evidence_records"], 1)
            self.assertEqual(tools.suggest_industries(property_id=1)["ranked"][0]["top_reason"], "r")
            self.assertEqual(tools.get_evidence("cafe", fact="cafe.", property_id=1)["total"], 1)
            with self.assertRaises(ValueError):
                tools.check_neighborhood("cafe")
        tools._run.cache_clear()


if __name__ == "__main__":
    unittest.main()

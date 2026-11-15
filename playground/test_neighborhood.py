"""Tests for the neighborhood demand pipeline. No network: tables are synthetic or cached."""
import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import neighborhood as n


def tract(geoid, lat, lon, pop, income=60000, households=None, land=1.0, **bands):
    row = {"geoid": geoid, "lat": lat, "lon": lon, "land_sqmi": land, "pop": pop, "pop_moe": 100,
           "households": households if households is not None else pop / 3, "income": income}
    for band in n.AGE_BANDS:
        row[band] = bands.get(band, pop / len(n.AGE_BANDS))
    return row


NEW = (tract("1", 29.80, -95.40, 4000, 100000), tract("2", 29.81, -95.40, 6000, 50000),
       tract("3", 30.30, -95.40, 5000, 40000))
OLD = (tract("a", 29.80, -95.40, 9000), tract("b", 30.30, -95.40, 4000))


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
        n.area_totals.cache_clear()
        n.reference_profiles.cache_clear()
        return self

    def __exit__(self, *exc):
        for p in self.patches:
            p.stop()
        n.area_totals.cache_clear()
        n.reference_profiles.cache_clear()
        self.tmp.cleanup()


class Basics(unittest.TestCase):
    def test_miles(self):
        # One degree of latitude is about 69 miles.
        self.assertAlmostEqual(n.miles(29.0, -95.0, 30.0, -95.0), 69.1, delta=0.2)

    def test_near_filters_by_radius(self):
        rows = [{"lat": 29.80, "lon": -95.40}, {"lat": 29.90, "lon": -95.40}]
        hits = n.near(rows, 29.80, -95.40, 3)
        self.assertEqual(len(hits), 1)

    def test_percentile_counts_half_ties_and_ignores_unknown(self):
        self.assertEqual(n.percentile(5, [1, 5, 9, None]), 50)
        self.assertIsNone(n.percentile(None, [1, 2]))
        self.assertIsNone(n.percentile(1, [None]))

    def test_stance(self):
        self.assertEqual(n.stance(0.05, plus=0.02, minus=-0.02), 1)
        self.assertEqual(n.stance(0.0, plus=0.02, minus=-0.02), 0)
        self.assertEqual(n.stance(-0.05, plus=0.02, minus=-0.02), -1)
        self.assertIsNone(n.stance(None, plus=1, minus=0))
        self.assertEqual(n.stance(3.0, plus=0.5, minus=2.0, higher_is_better=False), -1)

    def test_public_url_never_contains_key(self):
        url = n.public_url("https://api.census.gov/x", {"get": "A", "key": "SECRET"})
        self.assertNotIn("SECRET", url)
        self.assertIn("get=A", url)

    def test_offline_without_cache_raises_and_cache_is_read(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(n, "CACHE", Path(tmp)), \
                mock.patch.dict(os.environ, {"NEIGHBORHOOD_OFFLINE": "1"}):
            with self.assertRaises(n.Offline):
                n.fetch("https://example.test/a", {"q": 1})
            # Seed the cache the way fetch() writes it, then read it back offline.
            import hashlib
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
        self.assertEqual(len(trace), 1)


class Residents(unittest.TestCase):
    def test_area_profile_sums_tracts_in_radius(self):
        with FakeTables():
            p = n.area_profile(29.80, -95.40, 3)
        self.assertEqual(p["tracts"], 2)
        self.assertEqual(p["population"], 10000)
        # Household-weighted mean of tract medians: (100k*4000/3 + 50k*6000/3) / (10000/3)
        self.assertEqual(p["median_income_approx"], 70000)
        self.assertEqual(p["population_2019"], 9000)
        self.assertAlmostEqual(p["growth"], 10000 / 9000 - 1, places=3)

    def test_area_profile_none_when_no_tracts(self):
        with FakeTables():
            self.assertIsNone(n.area_profile(25.0, -80.0, 3))

    def test_residents_agent_records_and_signal(self):
        with FakeTables():
            out = n.residents_agent(29.80, -95.40, "indoor pickleball")
        facts = {r["fact"]: r for r in out["findings"]}
        self.assertEqual(facts["residents_population"]["value"], 10000)
        self.assertEqual(facts["residents_population"]["source"], "public:acs")
        # Area growth 10000/9000 = +11.1% vs Houston-area (15000/13000 = +15.4%) -> below area
        self.assertEqual(out["signal"]["stance"], -1)
        expected = facts["expected_players_at_national_rate"]
        self.assertEqual(expected["value"], round(10000 * 24_300_000 / 300_000_000))
        self.assertIn("national average", expected["note"])
        for r in out["findings"]:
            self.assertEqual(set(r), {"fact", "value", "source", "source_id", "captured_at", "confidence",
                                      "evidence_url", "status", "needs_human", "note"})

    def test_childcare_uses_under_5_trend(self):
        with FakeTables():
            out = n.residents_agent(29.80, -95.40, "childcare")
        self.assertIn("residents_under_5", {r["fact"] for r in out["findings"]})
        self.assertTrue(out["signal"]["reason"].startswith("Under-5"))


def facility(lat, lon, name=None, indoor=False, commercial=False, osm="node/1"):
    return {"lat": lat, "lon": lon, "name": name, "indoor": indoor, "commercial": commercial,
            "osm_ids": [osm], "features": 1, "osm_id": osm}


class Competitors(unittest.TestCase):
    def test_cluster_merges_courts_but_keeps_named_neighbours_apart(self):
        points = [facility(29.8, -95.4, None, osm="way/1"), facility(29.8005, -95.4, None, osm="way/2"),
                  facility(29.8, -95.4005, "Club A", True, True, "way/3"), facility(29.8, -95.401, "Club B", osm="n/4")]
        out = n.cluster(points, 0.15)
        names = sorted(f["name"] for f in out)
        self.assertEqual(names, ["Club A", "Club B"])
        club_a = next(f for f in out if f["name"] == "Club A")
        self.assertEqual(club_a["features"], 3)  # the two unnamed courts joined Club A
        self.assertTrue(club_a["indoor"])

    def test_competitors_agent_counts_ratio_and_stance(self):
        local = [facility(29.80, -95.40, "A", osm="n/1"), facility(29.805, -95.40, "B", osm="n/2")]
        far = [facility(30.30, -95.40, "C", osm="n/3")]
        with FakeTables(), mock.patch.object(n, "osm_facilities", lambda use: (
                local + far, (("url", "https://overpass.test"), ("retrieved_at", "2026-11-14T00:00:00"),
                              ("cached", True)))):
            out = n.competitors_agent(29.80, -95.40, "indoor pickleball")
        facts = {r["fact"]: r for r in out["findings"]}
        self.assertEqual(facts["competitors_within_radius"]["value"], 2)
        # Local: 2 per 10,000 residents = 2.0; area: 3 per 15,000 = 2.0 per 10k -> ratio 1.0, neutral
        self.assertEqual(facts["supply_per_10k_residents"]["value"], 2.0)
        self.assertEqual(out["signal"]["stance"], 0)
        self.assertEqual(facts["nearest_competitor"]["value"]["name"], "A")
        self.assertTrue(facts["nearest_competitor"]["evidence_url"].startswith("https://www.openstreetmap.org/"))

    def test_no_local_facilities_reads_underserved(self):
        with FakeTables(), mock.patch.object(n, "osm_facilities", lambda use: (
                [facility(30.30, -95.40, "C")], (("url", "u"), ("retrieved_at", "2026-11-14"), ("cached", True)))):
            out = n.competitors_agent(29.80, -95.40, "indoor pickleball")
        self.assertEqual(out["signal"]["stance"], 1)
        self.assertIn("underserved", out["signal"]["reason"])


class Momentum(unittest.TestCase):
    def test_categorize(self):
        self.assertEqual(n.categorize("JETSET Modern Pilates"), "fitness_recreation")
        self.assertEqual(n.categorize("Happy Kids Preschool"), "childcare")
        self.assertEqual(n.categorize("Golf Services Group"), "other")       # services firm, not a venue
        self.assertEqual(n.categorize("Pinnacle - Primrose at Heritage Park Apartments"), "other")
        self.assertEqual(n.categorize("The Lincoln Law Firm"), "other")
        self.assertEqual(n.categorize("Taqueria Arandas"), "food")

    def test_kit_tenancies_arrival_and_departure_rules(self):
        with tempfile.TemporaryDirectory() as kit, tempfile.TemporaryDirectory() as cache, \
                mock.patch.object(n, "CACHE", Path(cache)):
            data = Path(kit) / "data"
            data.mkdir()
            (data / "commercial-property.jsonl").write_text(json.dumps(
                {"id": 1, "primaryAddress": {"state": "TX", "latitude": 29.8, "longitude": -95.4}}) + "\n")
            (data / "company-detail.jsonl").write_text(
                json.dumps({"id": 10, "name": "True North Yoga", "profile": {"industryType": 21}}) + "\n")
            rows = [  # first lease, then a renewal: one arrival, and the renewal is not a departure
                {"id": 100, "propertyId": 1, "tenantLocationId": 10, "moveInDate": "2020-01-01",
                 "toDate": "2024-12-31", "expirationReason": 7},
                {"id": 101, "propertyId": 1, "tenantLocationId": 10, "fromDate": "2025-01-01",
                 "toDate": "2026-03-01", "expirationReason": 4},
            ]
            (data / "location-occupancy.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            n.kit_tenancies.cache_clear()
            out = {r["id"]: r for r in n.kit_tenancies(kit)}
            n.kit_tenancies.cache_clear()
        self.assertEqual(out[100]["arrival"], "2020-01-01")
        self.assertIsNone(out[100]["departure"])        # renewal
        self.assertIsNone(out[101]["arrival"])          # same tenant, same building
        self.assertEqual(out[101]["departure"], "2026-03-01")
        self.assertEqual(out[100]["category"], "fitness_recreation")

    def tenancy(self, name, arrival=None, departure=None, lat=29.8, category=None):
        return {"id": name, "property_id": 1, "lat": lat, "lon": -95.4, "name": name,
                "costar_industry": None, "category": category or n.categorize(name),
                "arrival": arrival, "departure": departure, "sqft": 2000}

    def test_momentum_counts_recent_moves_and_names_arrivals(self):
        rows = (self.tenancy("Club Pilates", "2025-02-01"), self.tenancy("Yoga One", "2026-04-01"),
                self.tenancy("Old Gym", None, "2024-05-01"), self.tenancy("Ancient Gym", "2015-01-01"),
                self.tenancy("Far Gym", "2025-01-01", lat=31.0), self.tenancy("Law Office", "2025-03-01"))
        with mock.patch.object(n, "kit_tenancies", lambda kit=None: rows):
            out = n.momentum_agent(29.8, -95.4, "fitness studio", today="2026-11-14")
        facts = {r["fact"]: r for r in out["findings"]}
        self.assertEqual(facts["kit_fitness_recreation_net_last_3_years"]["value"], 1)  # 2 in, 1 out
        self.assertEqual(out["signal"]["stance"], 1)
        self.assertEqual([e["name"] for e in out["examples"]], ["Yoga One", "Club Pilates"])
        by_year = facts["kit_fitness_recreation_arrivals_by_year"]["value"]
        self.assertNotIn(2015, by_year)                 # the table covers the last 8 years
        self.assertEqual(by_year[2025] + by_year[2026], 2)

    def test_momentum_too_few_moves_is_unknown(self):
        rows = (self.tenancy("Club Pilates", "2025-02-01"),)
        with mock.patch.object(n, "kit_tenancies", lambda kit=None: rows):
            out = n.momentum_agent(29.8, -95.4, "indoor pickleball", today="2026-11-14")
        self.assertIsNone(out["signal"]["stance"])
        facts = {r["fact"]: r for r in out["findings"]}
        self.assertEqual(facts["kit_fitness_recreation_net_last_3_years"]["status"], "unknown")


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

    def test_cross_validation_on_separable_places(self):
        rng = n.random.Random(1)
        pos = [{"lat": 29 + rng.random(), "lon": -95 - rng.random(), "x": [5 + rng.random(), 0.0],
                "indoor": False, "commercial": False, "name": "p"} for _ in range(40)]
        bg = [{"lat": 29 + rng.random(), "lon": -95 - rng.random(), "x": [rng.random(), 0.0]} for _ in range(200)]
        held_pos, held_neg = n.cross_validate(pos, bg, [0], 5, lambda r: n.spatial_fold(r["lat"], r["lon"], 5))
        self.assertEqual(n.auc([s for s, _, _ in held_pos], held_neg), 1.0)

    def fake_eval(self, auc_value):
        model = {"mean": [0.0] * 7, "sd": [1.0] * 7, "weights": [0.0, 1.0] + [0.0] * 6, "features": list(n.FEATURES)}
        split = {"auc": auc_value, "auc_90ci": [auc_value - 0.04, auc_value + 0.04], "hit_rate_top30": 0.44,
                 "baseline_auc": {"income_only": 0.66, "density_only": 0.45}}
        return {"model": model, "background_logits": [float(v) for v in range(11)], "facilities": 100,
                "background_places": 11, "evaluated_at": "2026-11-14T00:00:00+00:00",
                "splits": {"spatial": split, "random": split}}

    def test_lookalike_agent_percentile_and_validation_gate(self):
        profile = {"density_per_sqmi": math.e ** 9 - 1, "median_income_approx": 1, "population": 1,
                   "share_age_25_34": 0, "share_age_35_54": 0, "share_age_55_64": 0, "share_age_65_plus": 0,
                   "share_under_5": 0, "share_age_5_17": 0, "growth": 0}
        with mock.patch.object(n, "area_profile", lambda *a, **k: profile):
            with mock.patch.object(n, "lookalike_model", lambda use: self.fake_eval(0.64)):
                out = n.lookalike_agent(29.8, -95.4, "indoor pickleball")
            self.assertEqual(out["signal"]["value"], 86)   # logit 9 vs background 0..10 -> (9 + 0.5) / 11
            self.assertEqual(out["signal"]["stance"], 1)
            with mock.patch.object(n, "lookalike_model", lambda use: self.fake_eval(0.55)):
                out = n.lookalike_agent(29.8, -95.4, "indoor pickleball")
            self.assertIsNone(out["signal"]["stance"])     # not validated -> does not vote
            self.assertIn("not validated", out["signal"]["reason"])


def step(agent, name, stance_value, value=None):
    return {"agent": agent, "signal": {"name": name, "stance": stance_value, "value": value, "reason": name}}


class Coordinator(unittest.TestCase):
    def test_supported_needs_lookalike_and_total(self):
        d = n.coordinate("indoor pickleball", [step("lookalike", "lookalike", 1, 80), step("residents", "population trend", 1),
                                               step("competitors", "local supply", 0)])
        self.assertEqual(d["verdict"], "supported")
        self.assertEqual(d["reasons"][0]["signal"], "lookalike")

    def test_weak_when_lookalike_is_low(self):
        d = n.coordinate("indoor pickleball", [step("lookalike", "lookalike", -1, 20),
                                               step("competitors", "local supply", 1)])
        self.assertEqual(d["verdict"], "weak")
        self.assertIn("Few competitors", d["insight"])

    def test_unknown_without_validated_lookalike_or_enough_signals(self):
        d = n.coordinate("indoor pickleball", [step("lookalike", "lookalike", None, 80),
                                               step("residents", "population trend", 1),
                                               step("competitors", "local supply", 1)])
        self.assertEqual(d["verdict"], "unknown")
        d = n.coordinate("indoor pickleball", [step("lookalike", "lookalike", 1, 80)])
        self.assertEqual(d["verdict"], "unknown")

    def test_mixed_and_gap_insight(self):
        d = n.coordinate("fitness studio", [step("lookalike", "lookalike", 1, 75), step("competitors", "local supply", 1),
                                            step("residents", "population trend", -1),
                                            step("momentum", "business arrivals", -1)])
        self.assertEqual(d["verdict"], "mixed")
        self.assertTrue(d["insight"].startswith("Gap"))

    def test_unmodelled_use_is_unknown_with_reason(self):
        d = n.coordinate("warehouse / storage", [])
        self.assertEqual(d["verdict"], "unknown")
        self.assertIn("Business-to-business", d["headline"])


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
    decision = {"use": "indoor pickleball", "verdict": "weak", "insight": None,
                "reasons": [{"signal": "lookalike", "stance": -1, "reason": "22% of neighborhoods"}], "unknown": []}

    def run_with_reply(self, text):
        reply = mock.MagicMock()
        reply.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": text}}]}).encode()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(n, "CACHE", Path(tmp)), \
                mock.patch.dict(os.environ, {"UPSTAGE_API_KEY": "test", "NEIGHBORHOOD_OFFLINE": ""}), \
                mock.patch.object(n, "urlopen", return_value=reply):
            return n.narrate([self.decision], "1 Main St")

    def test_accepts_text_with_only_known_numbers(self):
        text, step = self.run_with_reply("Weak: it resembles only 22% of neighborhoods with courts.")
        self.assertIsNotNone(text)
        self.assertTrue(step["computed_by"].startswith("llm"))

    def test_rejects_invented_numbers(self):
        text, step = self.run_with_reply("Weak, and about 5,000 players live nearby.")
        self.assertIsNone(text)
        self.assertEqual(step["status"], "rejected")

    def test_no_key_means_no_summary(self):
        with mock.patch.dict(os.environ, {"UPSTAGE_API_KEY": ""}), tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(n, "CACHE", Path(tmp)):
            text, step = n.narrate([self.decision], "1 Main St")
        self.assertIsNone(text)
        self.assertEqual(step["status"], "unknown")


class Pipeline(unittest.TestCase):
    def test_investigate_suggest_ranks_and_traces(self):
        def fake(name, stance_value, value=None):
            return lambda **kw: {"summary": name, "findings": [n.record(name, 1, "computed", status="agrees")],
                                 "signal": {"name": name, "stance": stance_value, "value": value, "reason": name}}
        site = lambda **kw: {"point": {"lat": 29.8, "lon": -95.4, "label": "X"}, "findings": [], "summary": "X"}
        with mock.patch.object(n, "site_agent", site), \
                mock.patch.object(n, "residents_agent", fake("population trend", 1)), \
                mock.patch.object(n, "competitors_agent", fake("local supply", 0)), \
                mock.patch.object(n, "momentum_agent", fake("business arrivals", None)), \
                mock.patch.object(n, "lookalike_agent", lambda lat, lon, use: fake(
                    "lookalike", 1 if use == "fitness studio" else -1, 80 if use == "fitness studio" else 10)()):
            report = n.investigate("suggest", address="X")
        self.assertEqual(report["mode"], "suggest")
        self.assertEqual(report["decisions"][0]["use"], "fitness studio")
        self.assertEqual(report["decisions"][0]["verdict"], "supported")
        self.assertEqual(report["decisions"][-1]["verdict"], "unknown")
        agents = [s["agent"] for s in report["trace"]]
        self.assertEqual(agents[:2], ["planner", "site"])
        self.assertIn("coordinator", agents)
        self.assertTrue(all("computed_by" in s and "handoff" in s for s in report["trace"]))
        self.assertTrue(report["evidence"])


class Planner(unittest.TestCase):
    def test_plan_for_modeled_and_unmodeled_uses(self):
        steps, _ = n.plan("indoor pickleball")
        self.assertIn("lookalike", steps)
        steps, why = n.plan("warehouse / storage")
        self.assertNotIn("lookalike", steps)
        self.assertIn("Business-to-business", why)


if __name__ == "__main__":
    unittest.main()

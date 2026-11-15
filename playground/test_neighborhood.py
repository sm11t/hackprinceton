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


class Planner(unittest.TestCase):
    def test_plan_for_modeled_and_unmodeled_uses(self):
        steps, _ = n.plan("indoor pickleball")
        self.assertIn("lookalike", steps)
        steps, why = n.plan("warehouse / storage")
        self.assertNotIn("lookalike", steps)
        self.assertIn("Business-to-business", why)


if __name__ == "__main__":
    unittest.main()

"""Run with python3 -m unittest discover -s playground -p 'test_*.py'. The training test needs scikit-learn."""
import importlib.util
import math
import random
import unittest

from rent_model import (baseline, building_features, calibrate, choose_methods, conformity, peer_ranges, per_sf_year,
                        widen, year_of)

HAS_SKLEARN = importlib.util.find_spec("sklearn") is not None


def row(rent, city="houston", use=7, service=13, year=2024.0, group=1, **extra):
    return {"rent": rent, "city": city, "space_use": use, "service_type": service, "year": year, "group": group,
            "space_type": 1, "property_type": 2, "building_class": 2, "submarket": 10, "log_sf": math.log(10000),
            "year_built": 1980, "log_gba": math.log(50000), "stories": 1, "lat": 29.8, "lon": -95.5, **extra}


class Rows(unittest.TestCase):
    def test_rent_normalized_to_sf_per_year(self):
        self.assertEqual(per_sf_year(0.85, 0.85, 1), 10.2)
        self.assertEqual(per_sf_year(20, 24, 2), 22)
        self.assertIsNone(per_sf_year(0, 0, 2))      # 0 means no rate given
        self.assertIsNone(per_sf_year(20, 20, 0))    # unknown basis is not guessed
        self.assertIsNone(per_sf_year(900, 900, 2))  # implausible

    def test_year_is_fractional_and_falls_back(self):
        self.assertAlmostEqual(year_of(None, "2024-07-01T00:00:00"), 2024.5)
        self.assertIsNone(year_of(None, ""))

    def test_building_features_use_construction_complete_year(self):
        f = building_features({"constructionEvents": [{"eventType": 4, "year": 2010}, {"eventType": 2, "year": 1979}],
                               "primaryAddress": {"city": " Houston ", "latitude": 29.8, "longitude": -95.5}})
        self.assertEqual((f["year_built"], f["city"]), (1979, "houston"))


class Ranges(unittest.TestCase):
    def test_baseline_is_the_peer_median(self):
        predict = baseline([row(8), row(10), row(12), row(30, use=1, service=7)])
        self.assertEqual(predict(row(None)), 10)

    def test_recent_baseline_ignores_old_rents_when_recent_ones_exist(self):
        rows = [row(5, year=2005.0)] * 9 + [row(20, year=2024.0), row(22, year=2024.0)]
        self.assertEqual(baseline(rows)(row(None)), 5)  # all-years median, dragged down by old deals
        self.assertEqual(baseline(rows, since=2019)(row(None)), 21)
        self.assertEqual(baseline(rows, since=2030)(row(None)), 5)  # no recent pool: falls back to all years

    def test_conformal_width_reaches_the_target_coverage(self):
        rows = [row(10 * (1 + i / 100)) for i in range(100)]
        preds = [[9.5, 10, 10.5]] * 100
        width = calibrate(rows, preds, target=0.8)
        covered = sum(widen(p, width)[0] <= r["rent"] <= widen(p, width)[2] for r, p in zip(rows, preds))
        self.assertGreaterEqual(covered, 80)
        self.assertLess(conformity(row(10), [9, 10, 11]), 0)  # inside the range is negative

    def test_model_served_only_where_it_won_every_held_out_test(self):
        report = {"deals": {"by_space_use": {"flex": {"model_median_error_pct": 18, "baseline_median_error_pct": 19},
                                              "office": {"model_median_error_pct": 15, "baseline_median_error_pct": 21}}},
                  "listings": {"by_space_use": {"flex": {"model_median_error_pct": 28, "baseline_median_error_pct": 15}}}}
        methods = choose_methods(report)
        self.assertEqual((methods["flex"], methods["office"], methods["retail"]), ("similar_deals", "model", "similar_deals"))

    def test_peer_ranges_need_enough_recent_deals(self):
        deals = [row(5 + i % 10) for i in range(40)] + [row(20, use=6, year=2010.0)] * 40
        ranges = peer_ranges(deals, 2026)
        self.assertIn(("houston", 7, 13), ranges)
        self.assertNotIn(("houston", 6, 13), ranges)  # all too old


@unittest.skipUnless(HAS_SKLEARN, "scikit-learn not installed")
class Training(unittest.TestCase):
    def test_learns_size_and_city_and_keeps_ranges_ordered(self):
        from rent_model import fit, predict
        rng = random.Random(0)
        rows = []
        for i in range(600):
            city = "houston" if i % 2 else "los angeles"
            sf = rng.choice([2000, 10000, 50000])
            rent = (10 if city == "houston" else 20) * (1.3 if sf == 2000 else 1) * rng.uniform(0.9, 1.1)
            rows.append(row(rent, city=city, group=i, lon=-95.5 if city == "houston" else -118.3,
                            lat=29.8 if city == "houston" else 34.0, log_sf=math.log(sf)))
        preds = predict(fit(rows), rows[:50])
        self.assertTrue(all(p[0] <= p[1] <= p[2] for p in preds))
        hou = [p[1] for r, p in zip(rows[:50], preds) if r["city"] == "houston"]
        la = [p[1] for r, p in zip(rows[:50], preds) if r["city"] == "los angeles"]
        self.assertLess(max(hou), min(la))


if __name__ == "__main__":
    unittest.main()

"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import unittest

from jurisdiction import query_url, resolve_jurisdiction


def census(place=None, county=None):
    """A canned Census geocoder response: place=(NAME, GEOID), county=(NAME, GEOID)."""
    geographies = {}
    if place:
        geographies["Incorporated Places"] = [{"NAME": place[0], "GEOID": place[1]}]
    if county:
        geographies["Counties"] = [{"NAME": county[0], "GEOID": county[1]}]
    return lambda lat, lon: {"url": query_url(lat, lon), "retrieved_at": "2026-11-14T00:00:00+00:00",
                             "geographies": geographies}


HARRIS = ("Harris County", "48201")
LA_COUNTY = ("Los Angeles County", "06037")


class Jurisdiction(unittest.TestCase):
    def test_inside_houston_city(self):
        r = resolve_jurisdiction(29.854, -95.5317, fetch=census(("Houston city", "4835000"), HARRIS))
        self.assertEqual((r["code"], r["verified"], r["place"]), ("houston", True, "Houston city"))
        self.assertTrue(r["evidence_url"].startswith("https://geocoding.geo.census.gov/"))
        self.assertIn("annexation", r["note"])

    def test_unincorporated_harris(self):
        r = resolve_jurisdiction(30.02, -95.62, fetch=census(None, HARRIS))
        self.assertEqual((r["code"], r["verified"], r["place"]), ("harris_unincorporated", True, None))

    def test_city_and_county_of_los_angeles(self):
        self.assertEqual(resolve_jurisdiction(34.05, -118.24, fetch=census(("Los Angeles city", "0644000"),
                                                                           LA_COUNTY))["code"], "los_angeles")
        self.assertEqual(resolve_jurisdiction(34.0, -118.1, fetch=census(None, LA_COUNTY))["code"],
                         "la_unincorporated")

    def test_other_city_in_a_modeled_county_is_not_the_county(self):
        # Bellaire is inside Harris County but is its own city: never fall back to the county authority.
        r = resolve_jurisdiction(29.70, -95.46, fetch=census(("Bellaire city", "4807300"), HARRIS))
        self.assertEqual((r["code"], r["verified"], r["place"]), (None, False, "Bellaire city"))
        self.assertIn("own permitting authority", r["note"])
        r = resolve_jurisdiction(34.0, -118.08, fetch=census(("Pico Rivera city", "0656924"), LA_COUNTY))
        self.assertIsNone(r["code"])

    def test_other_county(self):
        r = resolve_jurisdiction(29.6, -95.7, fetch=census(None, ("Fort Bend County", "48157")))
        self.assertEqual((r["code"], r["verified"]), (None, False))

    def test_failures_never_raise_or_guess(self):
        def boom(lat, lon):
            raise RuntimeError("offline and no cached jurisdiction lookup for this point")
        r = resolve_jurisdiction(29.85, -95.53, fetch=boom)
        self.assertEqual((r["code"], r["verified"], r["evidence_url"]), (None, False, None))
        self.assertIn("unavailable", r["note"])
        for lat, lon in ((None, None), ("x", 1), (float("nan"), 0), (91, 0), (0, 181)):
            self.assertEqual(resolve_jurisdiction(lat, lon, fetch=boom)["code"], None)

    def test_query_has_no_key_and_rounds_the_point(self):
        url = query_url(29.8540012345, -95.5317098765)
        self.assertIn("y=29.85400", url)
        self.assertIn("x=-95.53171", url)
        self.assertNotIn("key", url)


if __name__ == "__main__":
    unittest.main()

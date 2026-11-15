"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import json
import tempfile
import unittest
from pathlib import Path

from deal import deal_facts, load_deal_data, load_rent_estimates, monthly_rent, rent_for_simulation

CONTRACT_KEYS = {"fact", "value", "source", "source_id", "captured_at", "confidence",
                 "evidence_url", "status", "needs_human", "note"}


def space(suite="A", sf=10000.0, rate=0.85, basis=1, service=13, available="2030-01-01T12:00:00-05:00", **extra):
    return {"listing_id": 7, "propertyId": 23296, "suite": suite, "squareFeetMax": sf, "rateLow": rate, "rateHigh": rate,
            "rateBasis": basis, "serviceType": service, "availableOnDate": available,
            "dateOnMarket": "2026-09-11T12:00:00-04:00", **extra}


def offer(price=7930000, assets=1, status=1, sale_type=2):
    return {"listing_id": 9, "askingPriceLow": price, "askingPriceHigh": price, "assetCount": assets,
            "saleStatus": status, "saleType": sale_type, "totalAvailableSquareFeet": 59025.0,
            "minDateOnMarket": "2026-09-11T12:00:00-04:00"}


def comp(price=2250000, when="2004-03-23T00:00:00", status=3, conditions=None, entities=1):
    return {"id": 1, "soldDate": when, "soldForPrice": price, "salePriceStatus": status, "saleType": 1,
            "saleConditions": conditions, "numberOfEntities": entities, "entities": [{"propertyId": 23296}]}


def fact(result, name, n=0):
    return [r for r in result["records"] if r["fact"] == name][n]


class Rent(unittest.TestCase):
    def test_monthly_rate_normalizes_to_month_and_year(self):
        self.assertEqual(monthly_rent(space()), (8500, 10.2))  # $0.85/sf/month on 10,000 sf

    def test_yearly_rate_normalizes(self):
        self.assertEqual(monthly_rent(space(sf=1334.0, rate=17, basis=2)), (1890, 17))

    def test_no_rate_is_unknown(self):
        self.assertEqual(monthly_rent(space(rate=0)), (None, None))
        result = deal_facts(23296, [space(rate=0)], [], [])
        self.assertEqual(fact(result, "lease_asking_rent")["status"], "unknown")

    def test_lease_basis_is_explained(self):
        note = fact(deal_facts(23296, [space()], [], []), "lease_asking_rent")["note"]
        self.assertIn("Suite A", note)
        self.assertIn("triple net", note)
        self.assertIn("plus taxes, insurance", note)


class Sale(unittest.TestCase):
    def test_asking_price_and_paths(self):
        result = deal_facts(23296, [space()], [offer()], [])
        self.assertEqual(result["paths"], ["lease", "buy"])
        self.assertEqual(fact(result, "sale_asking_price")["value"], 7930000)
        self.assertIn("owner/user", fact(result, "sale_asking_price")["note"])

    def test_undisclosed_texas_sale_is_unknown(self):
        result = deal_facts(23296, [], [], [comp(price=None)])
        self.assertEqual(fact(result, "last_sale_price")["status"], "unknown")
        self.assertIn("not disclosed", fact(result, "last_sale_price")["note"])

    def test_portfolio_price_is_not_the_building_price(self):
        result = deal_facts(23296, [], [], [comp(price=513808000, conditions=[12, 43])])
        rec = fact(result, "last_sale_price")
        self.assertIsNone(rec["value"])
        self.assertIn("not this building's value", rec["note"])

    def test_disclosed_sale_reports_its_basis(self):
        rec = fact(deal_facts(23296, [], [], [comp()]), "last_sale_price")
        self.assertEqual(rec["value"], 2250000)
        self.assertIn("confirmed", rec["note"])


class Capital(unittest.TestCase):
    def test_states_gaps_without_recommending(self):
        result = deal_facts(23296, [space()], [offer()], [], capital=320000)
        lease = fact(result, "capital_vs_lease")
        buy = fact(result, "capital_vs_purchase")
        self.assertEqual((lease["value"], lease["status"]), (102000, "agrees"))
        self.assertEqual(buy["status"], "conflict")
        self.assertIn("lender", buy["note"])
        self.assertNotIn("recommend", (lease["note"] + buy["note"]).lower())

    def test_bundled_sale_has_no_single_building_price(self):
        buy = fact(deal_facts(23296, [], [offer(assets=2)], [], capital=320000), "capital_vs_purchase")
        self.assertEqual(buy["status"], "unknown")
        self.assertIn("2 properties", buy["note"])

    def test_lease_check_uses_the_chosen_space(self):
        spaces = [space(suite="A", sf=10000.0), space(suite="B", sf=2000.0)]
        lease = fact(deal_facts(23296, spaces, [], [], capital=320000, suite="A"), "capital_vs_lease")
        self.assertEqual(lease["value"], 102000)

    def test_no_capital_no_check(self):
        result = deal_facts(23296, [space()], [offer()], [])
        self.assertFalse([r for r in result["records"] if r["fact"].startswith("capital_")])

    def test_records_keep_the_contract(self):
        result = deal_facts(23296, [space(), space(rate=0)], [offer(), offer(price=None)], [comp(), comp(price=None)],
                            capital=1)
        for r in result["records"]:
            self.assertEqual(set(r), CONTRACT_KEYS)


class SimulatorRent(unittest.TestCase):
    def test_rent_of_the_scenario_space_with_its_basis(self):
        spaces = [space(suite="B", sf=2000.0), space(suite="A", sf=10000.0)]
        self.assertEqual(rent_for_simulation(spaces, square_feet=10000.0),
                         {"monthly": 8500, "source": "CoStar asking rent, suite A, triple net (NNN)"})

    def test_no_priced_space_means_no_sourced_rent(self):
        self.assertIsNone(rent_for_simulation([space(rate=0)]))


def estimates(**overrides):
    e = {"property_id": 23296, "suite": "A", "space_use": "flex", "service_type": 13, "low": 8.0, "typical": 10.0,
         "high": 13.0, "asking": 10.2, "method": "model", "similar_recent_deals": 79, "low_confidence": False}
    e.update(overrides)
    return {"generated": "2026-11-14", "trained_on_deals": 8314, "train_since": 2012, "recent_years": 7,
            "evaluation": {"listings": {"model_median_error_pct": 15.4, "range_coverage_pct": 84, "by_space_use": {}}},
            "spaces": {"21863700": e}}


class MarketRent(unittest.TestCase):
    def market(self, rate=0.85, **overrides):
        result = deal_facts(23296, [space(rate=rate, id=21863700)], [], [], rent_estimates=estimates(**overrides))
        return fact(result, "market_rent_range")

    def test_asking_within_range_agrees(self):
        rec = self.market()  # $0.85/sf/month = $10.20/sf/year
        self.assertEqual((rec["status"], rec["value"]), ("agrees", 10.0))
        self.assertIn("$8.00–$13.00", rec["note"])
        self.assertIn("off by a median 15.4%", rec["note"])
        self.assertIn("not an appraisal", rec["note"])

    def test_asking_above_range_is_flagged_for_a_person(self):
        rec = self.market(rate=1.5)  # $18/sf/year
        self.assertEqual(rec["status"], "conflict")
        self.assertTrue(rec["needs_human"])
        self.assertIn("above the range", rec["note"])

    def test_call_for_rate_space_gets_an_estimate_marked_unknown(self):
        rec = self.market(rate=0)
        self.assertEqual(rec["status"], "unknown")
        self.assertIn("No asking rent is posted", rec["note"])

    def test_thin_evidence_is_rough_not_a_verdict(self):
        rec = self.market(rate=1.5, low_confidence=True, similar_recent_deals=0)
        self.assertEqual(rec["status"], "unknown")
        self.assertIn("No recent deals share", rec["note"])

    def test_says_when_the_range_comes_from_similar_deals(self):
        self.assertIn("79 similar flex deals", self.market(method="similar_deals")["note"])

    def test_no_estimates_file_means_no_records(self):
        self.assertIsNone(load_rent_estimates("/nonexistent/rent-estimates.json"))
        result = deal_facts(23296, [space(id=21863700)], [], [], rent_estimates=None)
        self.assertFalse([r for r in result["records"] if r["fact"] == "market_rent_range"])

    def test_keeps_the_contract(self):
        self.assertEqual(set(self.market()), CONTRACT_KEYS)


class KitLoading(unittest.TestCase):
    def test_only_this_buildings_active_listings_and_comps(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp, "data")
            data.mkdir()
            listings = [
                {"id": 1, "listingStatus": 1, "propertyId": 23296,
                 "forLeaseSummary": {"spaces": [space(), {**space(suite="Z"), "propertyId": 99999}]},
                 "forSaleSummary": offer()},
                {"id": 2, "listingStatus": 3, "propertyId": 23296, "forSaleSummary": offer(price=1)},  # off market
            ]
            (data / "commercial-listing-summary.jsonl").write_text("".join(json.dumps(x) + "\n" for x in listings))
            comps = [comp(), {**comp(), "id": 2, "entities": [{"propertyId": 12329600}]}]
            (data / "commercial-sale-comp.jsonl").write_text("".join(json.dumps(x) + "\n" for x in comps))
            spaces, offers, found = load_deal_data(tmp, 23296)
            self.assertEqual([s["suite"] for s in spaces], ["A"])
            self.assertEqual([o["askingPriceHigh"] for o in offers], [7930000])
            self.assertEqual([c["id"] for c in found], [1])


if __name__ == "__main__":
    unittest.main()

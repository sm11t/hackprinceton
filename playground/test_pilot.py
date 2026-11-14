"""Run with python3 -m unittest discover -s playground -p 'test_*.py'."""
import unittest
from pilot import comparison, evidence


class PilotTests(unittest.TestCase):
    def test_tenant_base_case(self):
        data = comparison({})
        sports = data['results'][1]
        self.assertEqual(sports['opening_month'], 4)
        self.assertEqual(sports['lowest_cash'], 82500)
        self.assertEqual(sports['extra_funding_needed'], 0)
        self.assertEqual(sports['rows'][3]['inflow'], 20790)

    def test_delay_crosses_reserve_without_changing_warehouse(self):
        base, delayed = comparison({}), comparison({'delay': 3})
        self.assertEqual(base['results'][0], delayed['results'][0])
        sports = delayed['results'][1]
        self.assertEqual(sports['opening_month'], 7)
        self.assertEqual(sports['lowest_cash'], 45000)
        self.assertEqual(sports['first_month_below_reserve'], 6)
        self.assertEqual(sports['extra_funding_needed'], 5000)

    def test_zero_bookings_and_larger_build_reduce_cash(self):
        base = comparison({})['results'][1]
        for inputs in ({'bookings': 0}, {'build_cost': 300000}):
            self.assertLess(comparison(inputs)['results'][1]['lowest_cash'], base['lowest_cash'])

    def test_reserve_changes_gap_not_curve(self):
        base, high = comparison({}), comparison({'reserve': 100000})
        self.assertEqual(base['results'][1]['rows'], high['results'][1]['rows'])
        self.assertEqual(high['results'][1]['extra_funding_needed'], 17500)

    def test_nessie_buyer_is_used(self):
        result = comparison({}, {'starting_cash': 400000, 'source': 'test sandbox',
                                 'recurring_bills': [{'monthly': 12000}]})
        self.assertEqual(result['buyer_source'], 'test sandbox')
        self.assertEqual(result['results'][1]['lowest_cash'], 158000)

    def test_invalid_inputs(self):
        for inputs in ({'bookings': 101}, {'delay': 1.5}, {'reserve': -1},
                       {'build_cost': float('nan')}, {'bookings': True}, {'unknown': 0}):
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                comparison(inputs)

    def test_zero_height_is_unknown_and_room_area_not_suite_area(self):
        model = {'floors': [{'rooms': [{'label': 'Warehouse', 'dimensionEstimates':
                                        {'height': 0, 'area': 593}}]}]}
        data = evidence({'grossBuildingAreaSquareFeet': 69500}, ['scan'], model)
        self.assertIsNone(data['warehouse_height_m'])
        self.assertEqual(data['warehouse_area_m2'], 593)
        self.assertEqual(data['building_area'], 69500)


if __name__ == '__main__':
    unittest.main()

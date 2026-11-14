"""Tanner tenant workspace adapter; projections stay in Jayant's simulator."""
import json
import math
from pathlib import Path

from nessie_pilot import simulate

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / 'scenarios/tanner_pickleball_tenant.json').read_text())
DEFAULTS = {'build_cost': 200000, 'bookings': 55, 'delay': 0, 'reserve': 50000,
            'warehouse_income': 18000}
LIMITS = {'build_cost': (0, 2000000), 'bookings': (0, 100), 'delay': (0, 24),
          'reserve': (0, 2000000), 'warehouse_income': (0, 200000)}


def comparison(inputs, buyer=None):
    values = dict(DEFAULTS)
    for key, raw in inputs.items():
        if key not in LIMITS:
            raise ValueError(f'Unknown assumption: {key}')
        if isinstance(raw, bool):
            raise ValueError(f'Invalid {key}')
        number = float(raw)
        low, high = LIMITS[key]
        if not math.isfinite(number) or not low <= number <= high:
            raise ValueError(f'{key} must be between {low} and {high}')
        if key == 'delay' and not number.is_integer():
            raise ValueError('Opening delay must be a whole number of months')
        values[key] = number
    buyer = buyer or {**CONFIG['buyer'], 'source': 'Demo scenario • simulated cash and bills'}
    sports = {**CONFIG['scenarios'][0], 'name': 'Indoor pickleball',
              'build_cost': values['build_cost'],
              'monthly_income': 3 * 12 * 30 * values['bookings'] / 100 * 35}
    warehouse = {'name': 'Warehouse use', 'build_months': 1, 'build_cost': 25000,
                 'monthly_income': values['warehouse_income'], 'monthly_operating_cost': 5000,
                 'monthly_carry': 2000}
    results = [simulate(warehouse, buyer, 24, values['reserve']),
               simulate(sports, buyer, 24, values['reserve'], int(values['delay']))]
    return {'inputs': values, 'starting_cash': buyer['starting_cash'],
            'monthly_bills': sum(b['monthly'] for b in buyer['recurring_bills']),
            'buyer_source': buyer['source'], 'results': results}


def evidence(prop, models, model=None, error=None, source='Live provider data'):
    rooms = [r for f in (model or {}).get('floors') or [] for r in f.get('rooms') or []]
    warehouse = next((r for r in rooms if (r.get('label') or '').lower() == 'warehouse'), {})
    dimensions = warehouse.get('dimensionEstimates') or {}
    return {'building_area': prop.get('grossBuildingAreaSquareFeet'),
            'model_ids': models, 'scan_name': (model or {}).get('name'),
            'warehouse_area_m2': dimensions.get('area'),
            'warehouse_height_m': dimensions.get('height') or None,
            'source': source, 'error': error}

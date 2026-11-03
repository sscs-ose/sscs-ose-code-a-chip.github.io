"""Fourteen physical inputs for partial-ring and direct-exit transformers.

Model topology codes are distinct from historical generator topology codes.
Source parameters remain unchanged. The network uses fourteen scalar
features and canonical four-port responses.
"""
import copy
import math
from numbers import Real

import numpy as np

SCHEMA = 'xfmr-physical14-two-topologies-v3'
INPUT_KEYS = ('topology', 'sb', 'pb', 'ps', 'm', 'u', 'us', 'w', 'wp', 's', 'ns', 'np', 'D', 'gap')
PHYSICAL_KEYS = tuple(key for key in INPUT_KEYS if key != 'topology')
SOURCE_KEYS = {key: key for key in PHYSICAL_KEYS}
SOURCE_KEYS.update(ps='secondary_return_edge', us='secondary_return_position_pct')
TOPOLOGY_CODES = {'legacy-partial-ring-v2': 0,
                  'series-direct-v2': 1}
TOPOLOGY_NAMES = ('parallel partial-ring primary',
                  'series primary, direct exit')
ENCODED_KEYS = INPUT_KEYS
EDGE_NAMES = ('right', 'bottom', 'left', 'top')


def normalize(parameters, *, integer_positions=False):
    """Validate model descriptors without interpreting an old generator vector."""
    if set(parameters) != set(INPUT_KEYS):
        raise ValueError('Expected exactly the fourteen physical input keys')
    values = dict(parameters)
    for key, value in values.items():
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not math.isfinite(float(value)):
            raise ValueError(f'{key} must be a finite number')
        values[key] = float(value)
    for key in ('sb', 'pb', 'ps', 'm', 'ns', 'np', 'topology'):
        if values[key] != int(values[key]):
            raise ValueError(f'{key} must be an integer')
        values[key] = int(values[key])
    if integer_positions:
        for key in ('u', 'us'):
            if values[key] != int(values[key]):
                raise ValueError(f'{key} must be an integer percentage for new layouts')
            values[key] = int(values[key])
    if values['topology'] not in (0, 1):
        raise ValueError('Model topology must be 0=partial ring or 1=direct')
    if values['sb'] not in (0, 1):
        raise ValueError('Coupling must be edge (0) or broadside (1)')
    if any(values[key] not in range(4) for key in ('pb', 'ps')):
        raise ValueError('Return edges use right=0, bottom=1, left=2, top=3')
    if values['m'] not in (1, 2) or any(not 1 <= values[key] <= 4 for key in ('ns', 'np')):
        raise ValueError('Require m in {1,2} and nominal winding counts in 1..4')
    if any(values[key] <= 0 for key in ('w', 'wp', 's', 'D', 'gap')):
        raise ValueError('Dimensions must be positive')
    # np counts nominal passes in each branch; m counts electrically parallel
    # branches. The supported parallel-primary design uses one pass per branch.
    if (values['m'] > 1 or values['topology'] == 0) and values['np'] != 1:
        raise ValueError('Partial-ring and parallel-primary layouts require nominal np=1')
    if values['topology'] == 1 and values['m'] != 1:
        raise ValueError('The supported direct-series class has one primary branch')
    if values['topology'] == 1 and (values['np'] < 2 or values['wp'] < 5):
        raise ValueError('Direct-series via landings require np >= 2 and wp >= 5 um')
    return {key: values[key] for key in INPUT_KEYS}


def from_source_row(row):
    """Translate one validated GDS/S4P catalog row; retain its source interface."""
    if row.get('kind') != 'xfmr' or row.get('geometry_layout_type') not in TOPOLOGY_CODES:
        raise ValueError('Record is outside the two approved transformer classes')
    if not all(row.get(key) is True for key in
               ('geometry_mask', 'gds_available', 'response_available', 'dataset_active')):
        raise ValueError('Expected validated physical inputs with an active GDS/S4P pair')
    parameters = {key: row['geometry_features'][source_key] for key, source_key in SOURCE_KEYS.items()}
    parameters['topology'] = TOPOLOGY_CODES[row['geometry_layout_type']]
    parameters = normalize(parameters)
    return dict(schema=SCHEMA, sample_id=row['sample_id'], parameters=parameters,
                source_layout_type=row['geometry_layout_type'],
                source_parameters=copy.deepcopy(row['parameters']),
                source_topology=row['parameters'].get('topology'),
                source_paths=copy.deepcopy(row['paths']),
                source_metadata_sha256=copy.deepcopy(row['source_sha256']),
                source_gds_sha256=row.get('source_gds_sha256'),
                roles=list(row.get('roles', [])),
                geometry_roles=list(row.get('geometry_roles', [])),
                training_candidate=bool(row.get('geometry_training_candidate', row.get('training_candidate', False))))


def encode(parameter_records, *, integer_positions=False):
    """Return exactly fourteen scalar physical features, including binary topology."""
    records = [normalize(record, integer_positions=integer_positions) for record in parameter_records]
    return np.asarray([[record[key] for key in INPUT_KEYS] for record in records], dtype=float).reshape(-1, len(INPUT_KEYS))

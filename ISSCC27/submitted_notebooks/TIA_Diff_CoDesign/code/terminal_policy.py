"""Integer terminal contract for generated optimization proposals."""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from environment import ROOT
from features14 import FEATURE_KEYS,physical14_features

SCHEMA='physical14-integer-terminal-proposal-v1'
PERCENT_TOLERANCE=1e-7
POLICY=dict(name='integer-terminal-percent-v1',mathematical_tolerance_pct=PERCENT_TOLERANCE)
MARKER_KEYS=('proposal_schema','terminal_position_policy')


def markers():
    return dict(proposal_schema=SCHEMA,terminal_position_policy=copy.deepcopy(POLICY))


def has_marker(proposal):
    return any(key in proposal for key in MARKER_KEYS)


def require_markers(proposal):
    if any(proposal.get(key)!=value for key,value in markers().items()):
        raise ValueError('Fresh proposals require the complete, unchanged integer-terminal schema')
    if 'stage_contract' in proposal:
        contract=proposal['stage_contract']
        if not isinstance(contract,dict) or any(contract.get(key)!=value for key,value in markers().items()):
            raise ValueError('Proposal and stage terminal-position policies disagree')


def physical(geometry):
    return dict(zip(FEATURE_KEYS,physical14_features(geometry)[0]))


def require_integer_geometry(geometry):
    from joint_passives import GeometryRejected
    values=physical(geometry)
    for key in ('u','us'):
        value=float(values[key])
        if not np.isfinite(value) or abs(value-round(value))>PERCENT_TOLERANCE:
            raise GeometryRejected(f'New proposal {key}={value:.12g}% is not an integer percentage')
    return values


def validate_entry(proposal,path,raw):
    require_markers(proposal)
    require_integer_geometry(proposal['geometry'])


def _measure_layout(geometry,path):
    """Compare physical marker coordinates at the actual GDS grid precision."""
    import gdstk
    lib=gdstk.read_gds(str(path))
    cells=lib.top_level()
    if len(cells)!=1:raise ValueError('Expected one generated transformer cell')
    grid_um=lib.precision/1e-6
    if not 0<grid_um<=.005+1e-12:raise ValueError('Unexpected or excessively coarse GDS grid')
    grid_tolerance_um=grid_um/2+1e-9
    values=physical(geometry);side=float(values['D']);measurements={}
    for layer,edge_key,key in ((202,'pb','u'),(204,'ps','us')):
        polygons=[p for p in cells[0].get_polygons() if p.layer==layer and p.datatype==0]
        if len(polygons)!=1:raise ValueError('Expected one generated return-terminal marker')
        point=np.mean(polygons[0].points,axis=0)*lib.unit/1e-6
        x,y=map(float,point);edge=int(values[edge_key])
        outside={0:x>side,1:y<0,2:x<0,3:y>side}
        if edge not in outside or not outside[edge]:raise ValueError('Generated return-terminal edge differs')
        coordinate=y if edge in (0,2) else x
        target=float(values[key])*side/100
        if abs(coordinate-target)>grid_tolerance_um:
            raise ValueError('Generated terminal position differs from its physical input: '+key)
        measurements[key]=dict(requested_pct=float(values[key]),measured_pct=100*coordinate/side,
                               coordinate_error_um=coordinate-target,gds_grid_um=grid_um,
                               gds_coordinate_tolerance_um=grid_tolerance_um)
    return measurements


def verify_new_layout(geometry,path):
    require_integer_geometry(geometry)
    return _measure_layout(geometry,path)


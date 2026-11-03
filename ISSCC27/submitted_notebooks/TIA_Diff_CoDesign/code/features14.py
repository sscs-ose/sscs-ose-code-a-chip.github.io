"""Convert source-generator geometries to fourteen physical ANN inputs.

Inputs use ``xfmr_schema`` dictionaries or its source vector order. Output
columns use ``section21_parameters.INPUT_KEYS``; topology is one scalar.
The terminal positions follow the stored generators' frame equations.
"""
import numpy as np

from section21_parameters import INPUT_KEYS, normalize
import xfmr_schema as XG


FEATURE_KEYS = INPUT_KEYS
FEATURE_SCHEMA = 'transformer-physical14-v1'


def _source_parameters(row):
    payload = row
    while isinstance(payload, dict) and 'parameters' in payload:
        payload = payload['parameters']
    if isinstance(payload, dict):
        if {'ps', 'us'} & payload.keys():
            raise ValueError('Expected source generator geometry, received physical ANN descriptors')
        values = [payload[key] for key in (*XG.KEYS, *XG.ALIASES) if key in payload]
    else:
        try:
            values = list(payload)
        except TypeError as exc:
            raise ValueError('Expected a source geometry dictionary or vector') from exc
    if any(isinstance(value, (bool, np.bool_)) for value in values):
        raise ValueError('Source geometry parameters cannot be booleans')
    parameters = XG.normalize(row)
    if parameters['topology'] not in (0, 3):
        raise ValueError('Physical14 supports source partial-ring (0) and direct-exit (3) layouts only')
    if parameters['sb'] not in (0, 1):
        raise ValueError('Physical14 supports edge or broadside coupling only')
    if parameters['ring_w'] != 30 or parameters['port_backing'] != 1:
        raise ValueError('Physical14 requires the measured source domain: ring_w=30 and port_backing=1')
    return parameters


def physical14_features(rawgeo):
    """Return an ``(N, 14)`` array from one source geometry or a batch.

    Source vectors retain their original 8/9/13/14-column interpretation;
    direct layouts require an explicit backed-port source record.
    Physical descriptor dictionaries are validated separately by
    ``section21_parameters.normalize`` and are not source geometries.
    """
    if isinstance(rawgeo, dict):
        rows = [rawgeo]
    else:
        try:
            rows = list(rawgeo)
        except TypeError as exc:
            raise ValueError('Expected a source geometry dictionary, vector or batch') from exc
        if rows and np.isscalar(rows[0]):
            rows = [rows]
    features = []
    for row in rows:
        source = _source_parameters(row)
        w, wp, s, ns, m, side = (source[key] for key in ('w', 'wp', 's', 'ns', 'm', 'D'))
        pitch = max(w, wp) + s
        if source['topology'] == 0:
            sb, pb, u = (source[key] for key in ('sb', 'pb', 'u'))
            if sb:
                secondary_position = 100 * (u * side / 100 - 2 * pitch * (m - 1) - 3 * pitch) / side
            else:
                # S0, P0, S1, P1, then the remaining secondary tracks.
                inner_offset = (ns + min(ns - 1, m)) * pitch
                secondary_position = 100 * (inner_offset + 2 * pitch) / side
            topology, ps, np_ = 0, sb, 1
        else:
            topology, sb, pb, ps, m, u, np_ = 1, 1, 3, 0, 1, 0, source['np']
            secondary_position = 50 - 50 * pitch / side
        physical = normalize(dict(topology=topology, sb=sb, pb=pb, ps=ps, m=m,
                                  u=u, us=secondary_position, w=w, wp=wp, s=s,
                                  ns=ns, np=np_, D=side, gap=source['gap']))
        features.append([physical[key] for key in FEATURE_KEYS])
    return np.asarray(features, dtype=float).reshape(-1, len(FEATURE_KEYS))

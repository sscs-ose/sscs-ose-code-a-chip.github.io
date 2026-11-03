"""Versioned transformer geometry shared by generators, EM jobs, and training.

The first nine fields retain the historical xfmr_gen meaning. In particular,
m counts parallel primary branches; np counts series primary turns. A topology
identifier is mandatory when identical dimensions describe different routing.
All lengths are micrometres. Port order is always P, Pbar, S, Sbar.
"""
import ast
import json
import math
from numbers import Real
from pathlib import Path

SCHEMA_VERSION = 2
KEYS = ('w', 's', 'ns', 'm', 'D', 'pb', 'sb', 'u', 'wp',
        'np', 'gap', 'ring_w', 'topology', 'port_backing')
LEGACY_KEYS = KEYS[:9]
TOPOLOGIES = {'legacy': 0, 'series_primary': 1, 'series_v3': 2, 'series_direct': 3}
PORT_ORDER = ('P', 'Pbar', 'S', 'Sbar')
ALIASES = {'turns_p': 'np', 'turns_s': 'ns', 'ring_width': 'ring_w'}


def normalize(geo, family=None):
    """Return the canonical dict; never guess what an untagged five-tuple means."""
    if isinstance(geo, dict):
        if 'layout_variant' in geo or 'terminal_positions' in geo:
            raise ValueError('Illustrative terminal extensions require example_layouts.py; they are outside the frozen model source schema')
        if geo.get('schema_version', SCHEMA_VERSION) not in (1, SCHEMA_VERSION):
            raise ValueError('Unsupported transformer geometry schema version')
        if geo.get('kind', 'xfmr') != 'xfmr':
            raise ValueError('Expected transformer metadata')
        if 'parameters' in geo:
            return normalize(geo['parameters'], family=family or geo.get('family'))
        g = {ALIASES.get(k, k): v for k, v in geo.items()}
        selected = g.get('topology', family or g.get('family', 'legacy'))
        if isinstance(selected, str):
            try:
                selected = TOPOLOGIES[selected]
            except KeyError as exc:
                raise ValueError(f'Unknown transformer topology {selected!r}') from exc
        if selected not in TOPOLOGIES.values():
            raise ValueError(f'Unknown transformer topology {selected!r}')
        if not all(k in g for k in ('w', 's', 'ns', 'D')):
            raise ValueError('Geometry requires w, s, ns, and D')
        defaults = dict(m=1, pb=0, sb=0 if selected == 0 else 1,
                        u=50 if selected == 0 else 0, wp=g['w'], np=0,
                        gap=20, ring_w=30, topology=selected,
                        port_backing=0 if selected in (2, 3) else 1)
        if selected and 'np' not in g:
            raise ValueError('Series transformers require explicit np (primary turns)')
        result = {k: g.get(k, defaults.get(k)) for k in KEYS}
        result['topology'] = selected
    else:
        values = list(geo)
        if len(values) in (8, 9):
            if family not in (None, 'legacy', 0):
                raise ValueError('Eight/nine values describe the legacy topology only')
            values = values + [values[0]] if len(values) == 8 else values
            return normalize(dict(zip(LEGACY_KEYS, values)))
        if len(values) == 5:
            if family not in ('series_primary', 1):
                raise ValueError('Five-value geometry requires the series_primary tag')
            w, s, np_, ns, D = values
            return normalize(dict(w=w, s=s, np=np_, ns=ns, D=D, topology=1))
        if len(values) in (13, len(KEYS)):
            return normalize(dict(zip(KEYS, values)))
        raise ValueError(f'Expected 8/9 legacy or {len(KEYS)} unified geometry values, got {len(values)}')
    for key, value in result.items():
        if not isinstance(value, Real) or not math.isfinite(float(value)):
            raise ValueError(f'{key} must be a finite number')
        result[key] = float(value)
    for key in ('ns', 'm', 'pb', 'sb', 'np', 'topology', 'port_backing'):
        if result[key] != int(result[key]):
            raise ValueError(f'{key} must be an integer')
        result[key] = int(result[key])
    if any(result[k] <= 0 for k in ('w', 'wp', 's', 'D', 'gap', 'ring_w')):
        raise ValueError('Widths, spacing, size, and ground dimensions must be positive')
    if result['ns'] < 1 or result['m'] < 1:
        raise ValueError('ns and m must be positive integers')
    if result['port_backing'] not in (0, 1):
        raise ValueError('port_backing must be 0 or 1')
    if result['topology'] == 0:
        if result['np'] != 0:
            raise ValueError('Legacy primary rings use m, not series-turn parameter np')
        if result['pb'] not in (0, 1) or result['sb'] not in (0, 1, 2):
            raise ValueError('Unsupported legacy pb/sb value')
        if result['gap'] != 20 or result['ring_w'] != 30 or result['port_backing'] != 1:
            raise ValueError('Legacy ground geometry is fixed at gap=20, ring_w=30, port_backing=1')
    else:
        if result['np'] < 1 or result['m'] != 1:
            raise ValueError('Series topology requires np >= 1 and m=1 (one series branch)')
        if result['pb'] != 0 or result['sb'] != 1 or result['u'] != 0:
            raise ValueError('Series topology uses fixed pb=0, sb=1, u=0; routing is identified by topology')
        if result['topology'] == 3 and (result['np'] < 2 or result['wp'] < 5):
            raise ValueError('Direct primary exit requires np >= 2 and wp >= 5 um')
        if result['topology'] == 1 and (result['wp'] != result['w'] or result['gap'] != 20
                                       or result['ring_w'] != 30 or result['port_backing'] != 1):
            raise ValueError('Historical series_primary geometry uses equal widths and fixed ground dimensions')
    return result


def vector(geo, family=None):
    g = normalize(geo, family)
    return [g[k] for k in KEYS]


def legacy_vector(geo):
    g = normalize(geo)
    if g['topology'] != 0:
        raise ValueError('This checkpoint supports legacy transformers only; train a unified model for series layouts')
    return [g[k] for k in LEGACY_KEYS]


def port_layers(geo):
    return ['TopMetal1' if normalize(geo)['topology'] in (2, 3) else 'TopMetal2'] * 4


def record(geo, **extra):
    g = normalize(geo)
    full_overlap = g['topology'] == 0 and g['sb'] == 2
    # Store actual directions rather than silently reversing a simulated port.
    return dict(schema_version=SCHEMA_VERSION, kind='xfmr',
                family=next(k for k, v in TOPOLOGIES.items() if v == g['topology']),
                parameter_keys=list(KEYS), parameters=g, port_order=list(PORT_ORDER),
                port_layers=port_layers(g), reference_layer='Metal4',
                primary_current_direction='ccw' if g['topology'] in (2, 3) or full_overlap else 'cw',
                secondary_current_direction='cw' if full_overlap else 'ccw', **extra)


def read_info(path):
    """Read legacy INFO logs or versioned JSON sidecars without rewriting sources."""
    path = Path(path)
    sidecar = path.with_suffix('.json')
    if sidecar.exists():
        return normalize(json.loads(sidecar.read_text(encoding='utf-8-sig')))
    text = path.read_text(encoding='utf-8-sig')
    if path.suffix.lower() == '.json':
        return normalize(json.loads(text))
    lines = text.splitlines()
    if len(lines) < 2 or lines[1].strip() != 'xfmr':
        raise ValueError('INFO record is not a transformer')
    tag = lines[2].strip() if len(lines) > 2 else ''
    if tag not in ('', 'series_primary', 'unified_v1', 'unified_v2'):
        raise ValueError(f'Unknown transformer INFO tag {tag!r}')
    return normalize(ast.literal_eval(lines[0]), family='series_primary' if tag == 'series_primary' else None)


def write_info(path, geo, **extra):
    """Write an INFO log plus authoritative JSON, preserving old eight/nine logs."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(repr(vector(geo)) + '\nxfmr\nunified_v2\n', encoding='utf-8')
    path.with_suffix('.json').write_text(json.dumps(record(geo, **extra), indent=2) + '\n', encoding='utf-8')

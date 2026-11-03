"""Parametric stacked rectangular transformers for SG13G2.

Primary A: TopMetal1, clockwise, outer end P- leaves at the top, inner end jumps on Metal5 to P (left).
Secondary B: TopMetal2, counter-clockwise, outer end S at the left (below P), inner end jumps on Metal5 to S- (right).
All corners are 90 degrees. Coil centre-line square is [0, D]^2, track pitch p = w + s.
The Metal4 ground window is the coil bounding box + gap on every side; all four port pads touch its edge.

Units: um. Layers: Metal4=50, Metal5=67, TopMetal1=126, TopMetal2=134, TopVia1=125, TopVia2=133,
port markers P=201, P-=202, S=203, S-=204 (EM flow convention: port n -> layer 200+n).

Usage: python generate_gds.py [--w 5 --s 3 --turns-p 3 --turns-s 3 --D 72 --gap 20 --ring-w 30 --out xfmr.gds]
The CLI defaults to series_direct: P leaves the final bottom edge horizontally
and traces cover the full via landings. Select --topology series_v3 to reproduce
the historical upward/dogleg escape. Ground clearance defaults to 20 um.
"""
import argparse
import json
from collections import defaultdict
from math import hypot
from pathlib import Path

import gdstk
import matplotlib
import numpy as np
import xfmr_schema as XG

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

M4, M5, TM1, TM2, TV1, TV2 = 50, 67, 126, 134, 125, 133
PORT_LAYERS = {'P': 201, 'P-': 202, 'S': 203, 'S-': 204}
LINKS = [{M5, TV1}, {TV1, TM1}, {TM1, TV2}, {TV2, TM2}]
V1 = dict(lower=M5, upper=TM1, cut=TV1, size=.42, pitch=.84, n=4)
V2 = dict(lower=TM1, upper=TM2, cut=TV2, size=.9, pitch=1.96, n=2)
VIA_PAD = 5.  # square landing pad of every via, independent of the line width


def build(w=5., s=3., turns_p=3, turns_s=3, D=72., gap=20., ring_w=30.,
          name='COUPLED_RECT', wp=None, port_backing=False, primary_exit='dogleg'):
    """Build v3; w is secondary width and wp is primary width (defaults to w).

    The historical keyword interface is preserved. Ground backing is optional
    for old visual examples; dataset generation enables it for vertical EM ports.
    """
    if turns_p != int(turns_p) or turns_s != int(turns_s):
        raise ValueError('turn counts must be integers')
    turns_p, turns_s = int(turns_p), int(turns_s)
    wp = w if wp is None else wp
    if primary_exit not in ('dogleg', 'direct'):
        raise ValueError('primary_exit must be dogleg or direct')
    if primary_exit == 'direct' and (turns_p < 2 or wp < VIA_PAD):
        raise ValueError('Direct primary exit requires np >= 2 and wp >= 5 um for the via landing')
    wm = max(w, wp)
    p, L, c0 = wm + s, VIA_PAD, D / 2
    if min(w, wp, s, D, gap, ring_w) <= 0 or min(turns_p, turns_s) < 1:
        raise ValueError('w, s, D, gap, ring_w must be > 0 and turns >= 1')
    if c0 - p - max(L, wm) / 2 - (max(turns_p, turns_s) - 1) * p - wm / 2 < s:
        raise ValueError('D too small for this many turns / this pitch')
    if gap < wm + 2 * s + L:
        raise ValueError('gap too small for the Metal5 jumper vias')

    xa, ya = c0 - p, c0 + p / 2          # historical primary inner end
    xb, yb = c0 + p, c0 - p / 2          # secondary inner end (via stack to Metal5)
    yp = 1.5 * p                         # P pad / Metal5 return row
    if primary_exit == 'direct':
        xa = ya = yp = (turns_p - 1) * p
    lo, hi = -gap - wm / 2, D + gap + wm / 2
    xpl, xsl, ypt, xsr = lo + wp / 2, lo + w / 2, hi - wp / 2, hi - w / 2
    xvl = -(wp / 2 + s + L / 2)
    xvr = xsr - (w / 2 + s + L / 2)
    ports = {'P': (xpl, yp, 'A'), 'P-': (0, ypt, 'A'), 'S': (xsl, 0, 'B'), 'S-': (xsr, yb, 'B')}

    A = [(0, ypt), (0, D)]
    for k in range(turns_p):
        A += [(D - k * p, D - k * p), (D - k * p, k * p), (k * p, k * p)]
        if primary_exit != 'direct' or k != turns_p - 1:
            A.append((k * p, D - (k + 1) * p))
    if primary_exit == 'dogleg':
        A += [(xa, D - turns_p * p), (xa, ya)]
    B = [(xsl, 0)]
    for k in range(turns_s):
        B += [(D - k * p, k * p), (D - k * p, D - k * p), (k * p, D - k * p), (k * p, (k + 1) * p)]
    B += [(xb, turns_s * p), (xb, yb)]

    lib = gdstk.Library(unit=1e-6, precision=5e-9)
    cell = lib.new_cell(name)
    nets = defaultdict(list)

    def add(poly, net):
        cell.add(poly)
        if net:
            nets[net].append(poly)

    def rect(a, b, layer, net=None, dt=0):
        add(gdstk.rectangle(a, b, layer=layer, datatype=dt), net)

    def route(pts, layer, net):
        width = wp if net == 'A' else w
        # Continue beyond each via centre to cover its complete landing.
        ends = (max(width, L) / 2, max(width, L) / 2) if primary_exit == 'direct' else 'flush'
        for q in gdstk.FlexPath(pts, width, joins='miter', ends=ends, layer=layer).to_polygons():
            add(q, net)

    def via(x, y, v, net):
        width = wp if net == 'A' else w
        pad = max(L, width) if primary_exit == 'direct' else L
        for layer in (v['lower'], v['upper']):
            rect((x - pad / 2, y - pad / 2), (x + pad / 2, y + pad / 2), layer, net)
        n = v['n']
        for i in range(n):
            for j in range(n):
                xx, yy = x + (i - (n - 1) / 2) * v['pitch'], y + (j - (n - 1) / 2) * v['pitch']
                rect((xx - v['size'] / 2, yy - v['size'] / 2), (xx + v['size'] / 2, yy + v['size'] / 2), v['cut'], net)

    route(A, TM1, 'A')
    route(B, TM2, 'B')
    # Only the part that crosses the windings runs on Metal5.
    via(xa, ya, V1, 'A')
    primary_return = [(xa, ya), (xvl, yp)] if primary_exit == 'direct' else [(xa, ya), (xa, yp), (xvl, yp)]
    route(primary_return, M5, 'A')
    via(xvl, yp, V1, 'A')
    route([(xvl, yp), (xpl, yp)], TM1, 'A')
    via(xb, yb, V2, 'B')
    via(xb, yb, V1, 'B')
    route([(xb, yb), (xvr, yb)], M5, 'B')
    via(xvr, yb, V1, 'B')
    route([(xvr, yb), (xsr, yb)], TM1, 'B')
    via(xsl, 0, V2, 'B')
    for pn, (x, y, net) in ports.items():
        width = wp if net == 'A' else w
        a, b = (x - width / 2, y - width / 2), (x + width / 2, y + width / 2)
        rect(a, b, TM1, net)
        rect(a, b, TM1, dt=2)
        rect(a, b, PORT_LAYERS[pn])
        if port_backing:
            # A ground landing under the complete vertical-port footprint. It
            # joins the M4 ring at the pad's outer edge, without a signal via.
            rect(a, b, M4)
        cell.add(gdstk.Label(pn, (x, y), layer=TM1, texttype=25), gdstk.Label(pn, (x, y), layer=PORT_LAYERS[pn], texttype=0))
    for q in gdstk.boolean(gdstk.rectangle((lo - ring_w, lo - ring_w), (hi + ring_w, hi + ring_w)),
                           gdstk.rectangle((lo, lo), (hi, hi)), 'not', layer=M4, precision=.005):
        cell.add(q)
    return lib, cell, nets, ports, dict(w=w, wp=wp, s=s, p=p, L=L, D=D, gap=gap,
                                      port_backing=bool(port_backing), primary_exit=primary_exit,
                                      lo=lo, hi=hi, paths={'A': A, 'B': B})


def _seg_dist(a, b):
    (ax0, ax1), (ay0, ay1) = sorted((a[0][0], a[1][0])), sorted((a[0][1], a[1][1]))
    (bx0, bx1), (by0, by1) = sorted((b[0][0], b[1][0])), sorted((b[0][1], b[1][1]))
    return hypot(max(bx0 - ax1, ax0 - bx1, 0), max(by0 - ay1, ay0 - by1, 0))


def _components(polys):
    box = [q.bounding_box() for q in polys]
    parent = list(range(len(polys)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, a in enumerate(polys):
        for j in range(i):
            b = polys[j]
            if not (a.layer == b.layer or {a.layer, b.layer} in LINKS):
                continue
            (ax0, ay0), (ax1, ay1) = box[i]
            (bx0, by0), (bx1, by1) = box[j]
            if ax0 > bx1 or bx0 > ax1 or ay0 > by1 or by0 > ay1:
                continue
            if gdstk.boolean([a], [b], 'and', precision=.005):
                parent[root(i)] = root(j)
    return [root(i) for i in range(len(polys))]


def check(gds_path, nets, ports, g):
    w, s, p, L = g['w'], g['s'], g['p'], g['L']
    # Own-winding spacing: non-adjacent centre-line segments >= pitch, end landing clear of the other segments.
    for net, pts in g['paths'].items():
        width = g.get('wp', w) if net == 'A' else w
        seg = list(zip(pts[:-1], pts[1:]))
        for i, a in enumerate(seg):
            for j in range(i + 2, len(seg)):
                assert _seg_dist(a, seg[j]) >= width + s - 1e-6, f'{net}: segments {i},{j} closer than the pitch'
        for a in seg[:-2]:
            assert _seg_dist(a, (pts[-1], pts[-1])) >= width / 2 + s + L / 2 - 1e-6, f'{net}: end landing too close to its winding'
    # Manhattan, checked on the stored polygons.
    cell = gdstk.read_gds(str(gds_path)).top_level()[0]
    bad = []
    for q in cell.polygons:
        d = np.roll(q.points, -1, axis=0) - q.points
        if np.any((abs(d[:, 0]) > 1e-8) & (abs(d[:, 1]) > 1e-8)):
            bad.append(q.layer)
    assert not bad, f'non-Manhattan polygons on layers {sorted(set(bad))}'
    # Check every cut's complete 0.5 um enclosure on both connected metals.
    for via_type in (V1, V2):
        cuts = [q for q in cell.polygons if q.layer == via_type['cut'] and q.datatype == 0]
        for metal in (via_type['lower'], via_type['upper']):
            conductor = [q for q in cell.polygons if q.layer == metal and q.datatype == 0]
            for cut in cuts:
                enclosure = gdstk.offset([cut], .5, join='miter', precision=.005)
                assert not gdstk.boolean(enclosure, conductor, 'not', precision=.005), f'via {via_type["cut"]} lacks full enclosure on metal {metal}'
    # A and B: two separate connected nets (vias included), >= s apart on every shared layer.
    polys = nets['A'] + nets['B']
    labels = ['A'] * len(nets['A']) + ['B'] * len(nets['B'])
    groups = defaultdict(set)
    for r, n in zip(_components(polys), labels):
        groups[r].add(n)
    assert len(groups) == 2 and all(len(v) == 1 for v in groups.values()), 'windings shorted or broken'
    for lay in (M5, TM1, TM2):
        a = [q for q in nets['A'] if q.layer == lay]
        b = [q for q in nets['B'] if q.layer == lay]
        if a and b:
            near = gdstk.offset(a, s - .01, join='round', use_union=True)
            assert not gdstk.boolean(near, b, 'and', precision=.005), f'layer {lay}: A/B closer than s'
    # Visual examples touch the ring; EM-ready examples have an M4 landing.
    ring = [q for q in cell.polygons if q.layer == M4]
    for pn, (x, y, net) in ports.items():
        width = g.get('wp', w) if net == 'A' else w
        pad = gdstk.rectangle((x - width / 2, y - width / 2), (x + width / 2, y + width / 2))
        if g.get('port_backing'):
            assert not gdstk.boolean([pad], ring, 'not', precision=.005), f'{pn} lacks Metal4 ground backing'
        else:
            assert not gdstk.boolean([pad], ring, 'and', precision=.005), f'{pn} overlaps the ring'
            assert gdstk.boolean(gdstk.offset([pad], .01, join='miter'), ring, 'and', precision=.001), f'{pn} does not touch the ring'
    if g.get('port_backing'):
        assert len(gdstk.boolean(ring, [], 'or', precision=.005)) == 1, 'M4 ground landings are disconnected'
    return cell


def preview(cell, ports, g, path):
    colors = {M4: '#b7bac2', M5: '#28a745', TM1: '#287bc1', TM2: '#d34343', TV1: '#111111', TV2: '#111111', 204: '#aa32bb'}
    sets = [{M5, TM1, TM2, TV1, TV2}, {M5, TM1, TV1}, {M5, TM2, TV2}]
    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    for ax, layers, title in zip(axes, sets, ['Overlay (Metal4 ring hidden)', 'Winding A: TopMetal1 + Metal5', 'Winding B: TopMetal2 + Metal5']):
        for q in cell.polygons:
            if q.layer in layers and q.datatype == 0:
                ax.add_patch(Polygon(q.points, facecolor=colors[q.layer], alpha=.6 if q.layer in (TM1, TM2) else .9,
                                     linewidth=.3, edgecolor=colors[q.layer]))
        for pn, (x, y, _) in ports.items():
            ax.text(x, y + g['w'], pn, ha='center', fontsize=9)
        ax.add_patch(Rectangle((g['lo'], g['lo']), g['hi'] - g['lo'], g['hi'] - g['lo'], fill=False, ls='--', lw=.8, ec='gray'))
        m = 8
        ax.set(xlim=(g['lo'] - m, g['hi'] + m), ylim=(g['lo'] - m, g['hi'] + m), aspect='equal', title=title, xlabel='x (um)', ylabel='y (um)')
        ax.grid(alpha=.15)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def build_from_geometry(geo, name='COUPLED_RECT'):
    """Use the shared schema; legacy shapes are delegated to their original code."""
    params = XG.normalize(geo)
    if params['topology'] in (2, 3):
        return build(w=params['w'], wp=params['wp'], s=params['s'],
                     turns_p=params['np'], turns_s=params['ns'], D=params['D'],
                     gap=params['gap'], ring_w=params['ring_w'],
                     port_backing=params['port_backing'], name=name,
                     primary_exit='direct' if params['topology'] == 3 else 'dogleg')
    if params['topology'] == 0:
        import xfmr_gen as old
        values = XG.legacy_vector(params)
        if params['sb'] == 2:
            raise ValueError('Historical sb=2 data can be trained, but its generator is not available here')
        if not old.is_valid(*values):
            raise ValueError('Invalid legacy transformer geometry')
        shapes = old.create_xfmr(*values)
    else:
        import xfmr_series_gen as old
        values = [params[k] for k in ('w', 's', 'np', 'ns', 'D')]
        if not old.valid(*values):
            raise ValueError('Invalid historical series_primary geometry')
        shapes = old.create_xfmr(*values)
    lib = gdstk.Library(unit=1e-6, precision=5e-9)
    cell = lib.new_cell(name)
    for shape in shapes:
        if shape is not None:
            cell.add(*(gdstk.Polygon(points, layer=layer, datatype=datatype)
                       for points, layer, datatype in zip(shape.polygons, shape.layers, shape.datatypes)))
    return lib, cell, None, None, None


def save_geometry(geo, out, info=None):
    """Write one GDS, authoritative parameter sidecar, and optional INFO record."""
    out = Path(out)
    params = XG.normalize(geo)
    targets = [out, out.with_suffix('.json')]
    if info is not None:
        targets.extend([Path(info), Path(info).with_suffix('.json')])
    if any(path.exists() for path in targets):
        raise FileExistsError('Output already exists; choose another path/index to preserve existing geometry and EM data')
    lib, cell, nets, ports, geometry = build_from_geometry(params, name=out.stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    lib.write_gds(str(out))
    if geometry is not None:
        cell = check(out, nets, ports, geometry)
        preview(cell, ports, geometry, out.with_name(out.stem + '_preview.png'))
    metadata = XG.record(params, generator='generate_gds.py', gds_file=out.name)
    out.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    if info is not None:
        XG.write_info(info, params, generator='generate_gds.py', gds_file=out.name)
    return metadata


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--w', type=float, default=5, help='line width (um)')
    ap.add_argument('--wp', type=float, help='primary width (um); defaults to secondary width --w')
    ap.add_argument('--s', type=float, default=3, help='line spacing between turns (um)')
    ap.add_argument('--np', '--turns-p', dest='np', type=int, default=3, help='series primary turns; never the legacy parallel count m')
    ap.add_argument('--ns', '--turns-s', dest='ns', type=int, default=3, help='secondary turns (legacy ns retains its original full-plus-partial convention)')
    ap.add_argument('--D', type=float, default=72, help='outer side of the centre-line square (um)')
    ap.add_argument('--gap', type=float, default=20, help='coil bbox to Metal4 ground window (um)')
    ap.add_argument('--ring-w', type=float, default=30, help='Metal4 ground ring width (um)')
    ap.add_argument('--topology', choices=list(XG.TOPOLOGIES), default='series_direct')
    ap.add_argument('--m', type=int, default=1, help='legacy parallel primary rings')
    ap.add_argument('--pb', type=int, default=0, help='legacy primary exit mode')
    ap.add_argument('--sb', type=int, default=0, help='legacy stacking mode')
    ap.add_argument('--u', type=float, default=50, help='legacy primary endpoint position (percent)')
    ap.add_argument('--port-backing', action='store_true', help='add Metal4 ground landings under v3 ports for EM simulation')
    ap.add_argument('--params', help='JSON geometry/sidecar or historical INFO log; preserves exact family semantics')
    ap.add_argument('--index', type=int, help='dataset index: write GDS/index.gds and INFO/index.log/.json; v3 ports are EM-backed')
    ap.add_argument('--root', default=str(Path(__file__).parent), help='dataset root (GDS, INFO, SPData)')
    ap.add_argument('--out', help='standalone GDS path; paired with a JSON sidecar')
    a = ap.parse_args()
    if a.index is not None and (a.index < 0 or a.out):
        ap.error('--index must be non-negative and cannot be combined with --out')
    if a.params:
        params = XG.read_info(a.params)
    else:
        params = dict(w=a.w, wp=a.wp if a.wp is not None else a.w, s=a.s,
                      ns=a.ns, D=a.D, gap=a.gap, ring_w=a.ring_w, topology=a.topology)
        if a.topology == 'legacy':
            params.update(m=a.m, pb=a.pb, sb=a.sb, u=a.u)
        else:
            params['np'] = a.np
        params = XG.normalize(params)
    if params['topology'] in (2, 3) and (a.port_backing or a.index is not None):
        params['port_backing'] = 1
    root = Path(a.root)
    if a.index is not None:
        if (root / 'SPData' / f'{a.index}.s4p').exists():
            raise FileExistsError('An EM result already uses this index; choose a new index')
        out, info = root / 'GDS' / f'{a.index}.gds', root / 'INFO' / f'{a.index}.log'
    else:
        out, info = Path(a.out or root / 'xfmr_series.gds'), None
    metadata = save_geometry(params, out, info)
    print('Generated:', out)
    print('Unified parameters:', metadata['parameters'])
    print('Port order:', metadata['port_order'], 'signal layers:', metadata['port_layers'])


if __name__ == '__main__':
    main()

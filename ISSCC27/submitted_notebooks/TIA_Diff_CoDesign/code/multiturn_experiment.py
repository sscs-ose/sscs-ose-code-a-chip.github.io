"""Passive layout generation, raw-network checks and circuit adapters."""
import hashlib
from pathlib import Path
import numpy as np


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def geometry_digest(path):
    """Compare stored polygons, independent of GDS timestamps and cell names."""
    import gdstk
    records = []
    for cell in gdstk.read_gds(str(path)).top_level():
        for poly in cell.get_polygons():
            points = [tuple(map(int, p)) for p in np.rint(poly.points / .005)]
            if points and points[0] == points[-1]:
                points.pop()
            def canonical(sequence):
                return min(tuple(sequence[i:] + sequence[:i]) for i, p in enumerate(sequence) if p == min(sequence))
            ring = min(canonical(points), canonical(points[::-1]))
            records.append((int(poly.layer), int(poly.datatype), ring))
    return hashlib.sha256(repr(sorted(records)).encode()).hexdigest()

def make_spiral(path, index, geometry):
    import gdspy
    import spiral_gen as SG
    if not SG.is_valid(*geometry):
        raise ValueError(f'Invalid spiral geometry {geometry}')
    lib = gdspy.GdsLibrary(name=f'Multiturn_{index}', precision=5e-9)
    cell = lib.new_cell(str(index))
    cell.add(SG.create_spiral(*geometry))
    for layer in (SG.TM1, SG.TM2):
        SG.merge_layer(cell, layer)
    lib.write_gds(str(path), [cell])
    path.with_suffix('.log').write_text(repr(geometry) + '\nspiral\n', encoding='utf-8')

def validate_network(path, nports):
    import skrf as rf
    net = rf.Network(str(path))
    if net.nports != nports or len(net.f) != 1001:
        raise ValueError(f'{path}: expected {nports} ports and 1001 frequency points')
    if not np.allclose(net.f, np.arange(1001) * 1e8, rtol=1e-9, atol=1):
        raise ValueError(f'{path}: expected the full 0..100 GHz frequency grid')
    if not np.isfinite(net.s).all() or not np.allclose(net.z0, 50, rtol=0, atol=1e-6):
        raise ValueError(f'{path}: non-finite S or reference impedance is not 50 ohm')
    for a in range(0, nports, 2):
        if abs(net.s[10, a + 1, a]) < .5:
            raise ValueError(f'{path}: winding {a//2 + 1} appears open at 1 GHz')
    return net

def permuted(s, permutation):
    return s[:, permutation, :][:, :, permutation]

def passive_figures(net, s):
    import surrogate as SU
    positive = net.f > 0
    f = net.f[positive]
    lp, ls, k, qp, qs = SU.xfmr_curves(f, s[positive])
    figures = {}
    for ghz in (1, 10, 20, 26):
        i = int(np.argmin(abs(f - ghz * 1e9)))
        figures[f'{ghz}GHz'] = dict(Lp_nH=float(lp[i] * 1e9), Ls_nH=float(ls[i] * 1e9),
                                   k=float(k[i]), Qp=float(qp[i]), Qs=float(qs[i]),
                                   n=float(np.sqrt(ls[i] / lp[i])) if lp[i] > 0 and ls[i] > 0 else None)
    for label, L in (('primary', lp), ('secondary', ls)):
        crossing = np.flatnonzero((L[:-1] > 0) & (L[1:] <= 0))
        figures[f'{label}_reactance_zero_ghz'] = float(f[crossing[0]] / 1e9) if len(crossing) else None
    return figures

def network_quality(net):
    ds = abs(net.s - np.swapaxes(net.s, -1, -2))
    maximum = float(np.linalg.svd(net.s[1:], compute_uv=False).max())
    return dict(reciprocity_mean=float(ds.mean()), reciprocity_max=float(ds.max()),
                max_singular_value=maximum, passivity_flag=maximum > 1.02,
                eligible_for_optimization=maximum <= 1.02 and float(ds.max()) <= .05,
                note='Raw EM is retained; no absolute coupling, reciprocity averaging or passivity projection applied')

def circuit_model(net, permutation=None, step_ghz=None):
    indices = np.flatnonzero(net.f > 0)
    if step_ghz:
        target = np.arange(step_ghz, 100 + step_ghz / 2, step_ghz) * 1e9
        indices = np.array([np.argmin(abs(net.f - f)) for f in target])
    s = net.s if permutation is None else permuted(net.s, permutation)
    return ('sp', net.f[indices], s[indices])

def measured_metrics(T, p, m):
    if m is None:
        return None
    values = {key: float(m[key]) for key in T.SPEC}
    gd = -np.gradient(np.unwrap(np.angle(m['zt'])), 2 * np.pi * m['f']) * 1e12
    for low in (1, 5):
        band = (m['f'] >= low * 1e9) & (m['f'] <= 26e9)
        values[f'gd_{low}_to_26_ps'] = float(np.ptp(gd[band])) if band.sum() > 1 else None
    values.update(headroom_v=float(T.headroom(m['op'])), jc=T.jc_of(p, m['op']), op=m['op'])
    return values

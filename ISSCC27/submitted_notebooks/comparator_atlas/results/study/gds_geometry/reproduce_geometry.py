"""Pinned MAG electrical-net selection to GDS conductor masks; geometry only, no RC model."""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import shutil
import struct
import subprocess

parser = argparse.ArgumentParser(
    description="Rebuild Comparator Atlas conductor-to-net geometry from published MAG/GDS")
parser.add_argument('--mag', required=True, type=Path, help='published atlas.mag')
parser.add_argument('--gds', required=True, type=Path, help='published atlas.gds')
parser.add_argument('--magic', required=True, type=Path, help='pinned Magic 8.3.684 executable')
parser.add_argument('--rcfile', required=True, type=Path, help='pinned sky130A.magicrc')
parser.add_argument('--pdk-root', required=True, type=Path, help='pinned open_pdks sky130 root')
parser.add_argument('--workdir', required=True, type=Path, help='new, absent local staging directory')
parser.add_argument('--output', required=True, type=Path, help='new, absent output JSON path')
args = parser.parse_args()
MAG = args.mag.resolve(strict=True)
GDS = args.gds.resolve(strict=True)
HERE = args.workdir.resolve()
OUTPUT = args.output.resolve()
if HERE.exists() or OUTPUT.exists():
    parser.error('workdir and output must not exist (never overwrite evidence)')
assert MAG.is_file() and GDS.is_file()
assert args.magic.is_file() and args.rcfile.is_file() and args.pdk_root.is_dir()
assert sha256(MAG.read_bytes()).hexdigest(
) == 'b2442585e4f9fec2be04b7dd48de4e5e1b87b8fcc375780df11a845be9a2c342'
assert sha256(GDS.read_bytes()).hexdigest(
) == 'a7d778406f5766b443eb954bfda33e56158a7604caf3ccd02d5b634d4b57d910'
HERE.mkdir(parents=False)
shutil.copyfile(MAG, HERE / 'atlas.mag')
PREVIOUS = HERE

NAMES = ['clk', 'tail', 'xp', 'xn', 'qp', 'qn', 'vinp', 'vinn', 'vdd', 'vss'] + \
    [p + str(i) for p in ('tp', 'tn', 'sp', 'sn') for i in range(4)]
STRICT = {'clk', 'tail', 'qp', 'vdd', 'vss'}
LAYERS = {(67, 20): 'locali', (68, 20): 'metal1', (69, 20): 'metal2', (70, 20): 'metal3', (71, 20): 'metal4',
          (66, 44): 'licon', (67, 44): 'mcon', (68, 44): 'via1', (69, 44): 'via2', (70, 44): 'via3'}
CONDUCTOR = [(x, 20) for x in (67, 68, 69, 70, 71)]
CONTACT = [(x, 44) for x in (66, 67, 68, 69, 70)]

MAGIC_SCRIPT = r"""
proc run {} {
    if {[tech name] ne "sky130A"} {error "wrong technology"}
    units internal
    snap internal
    random seed 1
    load atlas -silent
    box values 0 0 0 0
    gds write recreated-from-mag.gds
    extract style ngspice()
    extract no resistance
    extract do capacitance
    extract do coupling
    extract all
    ext2spice lvs
    ext2spice blackbox off
    ext2spice hierarchy off
    ext2spice subcircuit on
    ext2spice subcircuit top on
    ext2spice merge none
    ext2spice scale off
    ext2spice extresist off
    ext2spice cthresh 0
    ext2spice -o fresh.c.spice
    select do labels
    foreach name {clk tail xp xn qp qn vinp vinn vdd vss tp0 tp1 tp2 tp3 tn0 tn1 tn2 tn3
                  sp0 sp1 sp2 sp3 sn0 sn1 sn2 sn3} {
        load atlas -silent
        box values 0 0 0 0
        select clear
        findlabel $name
        switch -- $name {
            clk {select net via2}
            tail - qp - qn - vdd - vss {select net metal3}
            default {select net}
        }
        select save net_$name
        if {![file exists net_${name}.mag]} {error "missing net cell $name"}
        load net_$name -silent
        gds write mask_$name.gds
        if {![file exists mask_${name}.gds]} {error "missing net mask $name"}
        puts "PUBLIC_GEOMETRY_NET $name"
    }
    puts "PUBLIC_GEOMETRY_COMPLETE 26"
}
if {[catch {run} message options]} {
    puts stderr "PUBLIC_GEOMETRY_ERROR: $message"
    puts stderr [dict get $options -errorinfo]
    exit 1
}
exit 0
"""
env = os.environ.copy()
env['PDK_ROOT'] = str(args.pdk_root.resolve())
process = subprocess.run(
    [str(args.magic.resolve()), '-dnull', '-noconsole', '-rcfile', str(args.rcfile.resolve())],
    input=MAGIC_SCRIPT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    cwd=HERE, env=env, check=False)
(HERE / 'magic-console.log').write_text(process.stdout, encoding='utf-8')
assert process.returncode == 0 and 'PUBLIC_GEOMETRY_COMPLETE 26' in process.stdout


def gds(path):
    data = path.read_bytes()
    p = 0
    polys = defaultdict(list)
    labels = []
    cell = None
    while p < len(data):
        size, typ, _ = struct.unpack_from('>HBB', data, p)
        assert size >= 4 and p + size <= len(data)
        val = data[p + 4:p + size]
        p += size
        if typ in (8, 12):
            cell = {'kind': typ}
        elif typ in (13, 14, 22):
            cell[{13: 'layer', 14: 'datatype', 22: 'texttype'}[typ]] = int.from_bytes(val, 'big', signed=True)
        elif typ == 16:
            coords = struct.unpack('>' + 'i' * (len(val) // 4), val)
            cell['xy'] = tuple(zip(*[iter(coords)] * 2))
        elif typ == 25:
            cell['text'] = val.rstrip(b'\0').decode('ascii')
        elif typ == 17:
            if cell['kind'] == 8:
                poly = cell['xy']
                assert poly[0] == poly[-1]
                polys[(cell['layer'], cell['datatype'])].append(poly[:-1])
            else:
                labels.append(cell)
            cell = None
    assert p == len(data)
    return polys, labels


def canonical(poly):
    rev = poly[::-1]
    return min(tuple(x[i:] + x[:i]) for x in (poly, rev) for i in range(len(x)))


def read_mag(path):
    shapes = defaultdict(Counter)
    labels = []
    layer = None
    for line in path.read_text(encoding='ascii').splitlines():
        if line.startswith('<< '):
            layer = line[3:-3].strip()
        elif line.startswith('rect '):
            shapes[layer][tuple(map(int, line.split()[1:]))] += 1
        elif layer == 'labels' and line.startswith('rlabel '):
            labels.append(line.split()[-1])
    return shapes, labels


def merged(intervals):
    result = []
    for lo, hi in sorted(intervals):
        assert lo < hi
        if result and lo <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], hi))
        else:
            result.append((lo, hi))
    return result


def bands(polys):
    ys = sorted({y for poly in polys for _, y in poly})
    rows = []
    for lo, hi in zip(ys, ys[1:]):
        ints = []
        for poly in polys:
            crossings = []
            for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
                assert x1 == x2 or y1 == y2, 'non-Manhattan polygon'
                if x1 == x2 and 2 * min(y1, y2) < lo + hi < 2 * max(y1, y2):
                    crossings.append(x1)
            crossings.sort()
            assert len(crossings) % 2 == 0
            ints += list(zip(crossings[::2], crossings[1::2]))
        uni = merged(ints)
        if uni:
            rows.append((lo, hi, uni))
    return rows


def subtract(left, right):
    out = []
    for lo, hi in left:
        segments = [(lo, hi)]
        for a, b in right:
            segments = [piece for x, y in segments for piece in (
                (x, min(y, a)), (max(x, b), y)) if piece[0] < piece[1]]
        out += segments
    return out


def edges(rows):
    result = {'left': [], 'right': [], 'top': [], 'bottom': []}
    prev = []
    previous_y = None
    for y0, y1, intervals in rows:
        if previous_y is not None and previous_y != y0:
            result['top'] += [(previous_y, a, b) for a, b in prev]
            prev = []
        result['bottom'] += [(y0, a, b) for a, b in subtract(intervals, prev)]
        result['top'] += [(y0, a, b) for a, b in subtract(prev, intervals)]
        for x0, x1 in intervals:
            result['left'].append((x0, y0, y1))
            result['right'].append((x1, y0, y1))
        prev = intervals
        previous_y = y1
    if previous_y is not None:
        result['top'] += [(previous_y, a, b) for a, b in prev]
    return result


def metrics(polys):
    rows = bands(polys)
    area = sum((hi - lo) * sum(b - a for a, b in ints) for lo, hi, ints in rows)
    border = edges(rows)
    perim = sum(b - a for sections in border.values() for _, a, b in sections)
    rectangles = Counter()
    for poly in polys:
        xx = {x for x, _ in poly}
        yy = {y for _, y in poly}
        if len(poly) == 4 and len(xx) == len(yy) == 2:
            rectangles[(max(xx) - min(xx), max(yy) - min(yy))] += 1
    return {'polygon_count': len(polys), 'rectangle_count': sum(rectangles.values()),
            'nonrectangular_count': len(polys) - sum(rectangles.values()),
            'area_um2': area / 1000000, 'perimeter_um': perim / 1000,
            'rect_dims_um': [[x / 1000, y / 1000, n]
                             for (x, y), n in sorted(rectangles.items())]}, rows, border


def overlap(a, b):
    total = 0
    for lo, hi, ints in a:
        for bottom, top, others in b:
            height = min(hi, top) - max(lo, bottom)
            if height <= 0:
                continue
            for x, y in ints:
                for u, v in others:
                    total += height * max(0, min(y, v) - max(x, u))
    return total


def facing(a, b):
    lengths = Counter()
    for right, left in ((a['right'], b['left']), (b['right'], a['left']),
                        (a['top'], b['bottom']), (b['top'], a['bottom'])):
        for x0, a0, a1 in right:
            for x1, b0, b1 in left:
                gap = x1 - x0
                projection = min(a1, b1) - max(a0, b0)
                if gap > 0 and projection > 0:
                    lengths[gap] += projection
    return lengths


source, source_text = gds(GDS)
reference, ref_text = gds(HERE / 'recreated-from-mag.gds')
assert {k: Counter(map(canonical, v)) for k, v in source.items()} == {
    k: Counter(map(canonical, v)) for k, v in reference.items()}
assert len(source_text) == len(ref_text) == 26
assert Counter((e['layer'], e['texttype'], e['xy'], e['text']) for e in source_text) == Counter(
    (e['layer'], e['texttype'], e['xy'], e['text']) for e in ref_text)
assert sha256(GDS.read_bytes()).hexdigest(
) == 'a7d778406f5766b443eb954bfda33e56158a7604caf3ccd02d5b634d4b57d910'
assert sha256((HERE / 'atlas.mag').read_bytes()
              ).hexdigest() == 'b2442585e4f9fec2be04b7dd48de4e5e1b87b8fcc375780df11a845be9a2c342'
mag_shapes, mag_labels = read_mag(HERE / 'atlas.mag')
netmags = {}
netgds = {}
pernet = {}
perbands = {}
peredges = {}
for name in NAMES:
    path = HERE / ('net_' + name + '.mag')
    shapes, labels = read_mag(path)
    assert labels == [name], (name, labels)
    netmags[name] = shapes
    poly, text = gds(HERE / f'mask_{name}.gds')
    assert [e['text'] for e in text] == [name], (name, text)
    netgds[name] = poly
    pernet[name] = {}
    for k in CONDUCTOR + CONTACT:
        m, rows, border = metrics(poly.get(k, []))
        pernet[name][LAYERS[k]] = m
        perbands[(name, k)] = rows
        peredges[(name, k)] = border

mag_partition = {}
for layer in ('locali', 'metal1', 'metal2', 'metal3', 'metal4', 'viali', 'via1', 'via2', 'via3',
              'ndiffc', 'pdiffc', 'polycont', 'psubdiffcont', 'nsubdiffcont'):
    parts = sum((netmags[n][layer] for n in NAMES), Counter())
    assert parts == mag_shapes[layer], (layer, 'missing or duplicate Magic tile')
    mag_partition[layer] = {
        'source_tiles': sum(mag_shapes[layer].values()),
        'assigned_once': sum(parts.values()),
    }
mask_partition = {}
for k in CONDUCTOR + CONTACT:
    parts = sum((Counter(map(canonical, netgds[n].get(k, []))) for n in NAMES), Counter())
    original = Counter(map(canonical, source.get(k, [])))
    assert parts == original, (k, 'missing, extra or multiply assigned GDS polygon')
    mask_partition[LAYERS[k]] = {
        'gds_layer_datatype': list(k),
        'source_polygons': sum(original.values()),
        'assigned_once': sum(parts.values()),
    }
# Verify published logical interface and transistor inventory; selected label identity is
# validated above against original MAG rather than inferred from GDS-only text.
netlist = (PREVIOUS / 'fresh.c.spice').read_text()
ports = [line.split()[2:] for line in netlist.splitlines() if line.startswith('.subckt atlas ')]
mos = [line for line in netlist.splitlines() if line.startswith('X')]
assert len(ports) == 1 and len(ports[0]) == 15 and len(mos) == 27
assert set(NAMES) == set(mag_labels) and set(ports[0]).issubset(set(NAMES))
logical_extraction = (PREVIOUS / 'atlas.ext').read_text()
assert {line.split('\"')[1] for line in logical_extraction.splitlines()
        if line.startswith(('node ', 'substrate '))} == set(NAMES)
report = {'scope': 'Geometry/net mapping only, NOT a public-coefficient R/C estimate',
          'source_gds_sha256': sha256(GDS.read_bytes()).hexdigest(),
          'source_mag_sha256': sha256((HERE / 'atlas.mag').read_bytes()).hexdigest(),
          'mag_gds_export_polygons_and_text_match_archived_gds': True,
          'logical_check': {'ports': ports[0], 'net_names': NAMES, 'net_count': 26, 'mos_count': len(mos)},
          'mask_partition': mask_partition, 'magic_tile_partition': mag_partition,
          'units': ('GDS coordinates are 1 nm; dimensions in micrometers; '
                    'polygon area/perimeter are union geometry'),
          'per_net': pernet, 'opposing_pairs': {},
          'opposing_pair_method': ('raw facing parallel boundary projections at positive gaps; '
                                   'may be occluded by third nets'),
          'model_status': ('No sheet-R, contact-R, dielectric or fringe coefficient applied; '
                           'no solved network R/C')}
for a, b in [('clk', 'tail'), ('xp', 'xn'), ('qp', 'qn')]:
    pair = {}
    for k in CONDUCTOR:
        ga = peredges[(a, k)]
        gb = peredges[(b, k)]
        distances = facing(ga, gb)
        assert overlap(perbands[(a, k)], perbands[(b, k)]) == 0, (a, b, k, 'same layer short')
        pair[LAYERS[k]] = {'same_layer_min_positive_gap_um': min(distances) / 1000 if distances else None,
                           'facing_parallel_edge_um_at_gap_le_1um':
                               sum(v for g, v in distances.items() if g <= 1000) / 1000,
                           'gap_length_um': [[g / 1000, v / 1000]
                                             for g, v in sorted(distances.items()) if g <= 1000]}
    for lo, hi in zip(CONDUCTOR, CONDUCTOR[1:]):
        for x, y in ((a, b), (b, a)):
            pair[f'{x}_{LAYERS[lo]}_vs_{y}_{LAYERS[hi]}_overlap_um2'] = overlap(
                perbands[(x, lo)], perbands[(y, hi)]) / 1000000
    report['opposing_pairs'][f'{a}-{b}'] = pair
assert all(report['per_net'][n]['metal3']['rect_dims_um'] == [dims] for n, dims in {
    'clk': [48.8, 0.34, 1], 'tail': [123.6, 0.34, 1],
    'xp': [53.6, 0.34, 1], 'xn': [53.6, 0.34, 1],
    'qp': [50.8, 0.34, 1], 'qn': [50.8, 0.34, 1]}.items())
positive = {(pair, key) for pair, fields in report['opposing_pairs'].items()
            for key, value in fields.items() if key.endswith('_overlap_um2') and value > 0}
assert positive == {
    ('clk-tail', 'clk_metal2_vs_tail_metal3_overlap_um2'),
    ('clk-tail', 'tail_metal1_vs_clk_metal2_overlap_um2'),
    ('qp-qn', 'qn_metal2_vs_qp_metal3_overlap_um2'),
    ('qp-qn', 'qp_metal2_vs_qn_metal3_overlap_um2')}
OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print('PUBLIC_GEOMETRY_AUDIT_COMPLETE')

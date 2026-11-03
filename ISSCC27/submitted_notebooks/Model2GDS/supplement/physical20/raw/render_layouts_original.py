#!/usr/bin/env python3
"""Render preserved qualified 2x2/4x4 final GDS; never run an EDA flow."""
import argparse
from collections import Counter, defaultdict
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_dac27_round4_exploratory import qualified_subset
from scripts.phase1_common import canonical_bytes
from scripts.reproduce_figures import _gds_geometry

OUTPUT = 'results/figures/dac27_round5_layouts'
PHYSICAL = 'results/processed/dac27_round4_physical_recheck.json'
HISTORICAL = 'results/processed/dac27_round2_physical.json'
PDK_LAYERS = 'results/raw/phase2/dac27/round5/LAYOUT_001/sky130A.lyp'
DETAIL_WIDTH_UM = 80.0
LAYERS = {
    67: ('li1', '#74859b'), 68: ('met1', '#4b8bd6'),
    69: ('met2', '#55d5df'), 70: ('met3', '#69d99c'),
    71: ('met4', '#e9bd5b'), 72: ('met5', '#e88689'),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source(path, root=ROOT):
    p = root / path
    blob = p.read_bytes()
    return {'path': path, 'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def inputs(root=ROOT):
    physical_bytes = (root / PHYSICAL).read_bytes()
    require(physical_bytes == (root / HISTORICAL).read_bytes(),
            'Round-4 recheck differs from preserved original physical qualification')
    physical = json.loads(physical_bytes)
    admitted = qualified_subset(physical)
    records = []
    for item in admitted:
        row = next(r for r in physical['configurations'] if r['array_size'] == item['array_size'])
        require(row['gds'] == row['artifacts']['gds'], 'Final GDS artifact identity differs')
        record = {**row['gds'], 'top_cell': row['design_name'],
                  'array_size': row['array_size'], 'run_path': row['run_path'],
                  'qualification': row['qualification']}
        require(record['top_cell'] == f'phase2_core_{row["array_size"]}',
                'Unexpected accelerator top cell')
        require(source(record['path'], root) == row['gds'], 'Final GDS bytes changed')
        records.append(record)
    import xml.etree.ElementTree as ET
    lyp = ET.fromstring((root / PDK_LAYERS).read_bytes())
    observed = {p.findtext('source'): p.findtext('name') for p in lyp.iter()
                if p.findtext('source')}
    for number, (label, _) in LAYERS.items():
        require(observed.get(f'{number}/20@1') == f'{label}.drawing - {number}/20',
                'Layer label differs from pinned SKY130A display map')
    return records


def scale_length(width):
    target = width * .22
    order = 10 ** math.floor(math.log10(target))
    return max(x * order for x in (0.1, 0.2, 0.5, 1, 2, 5) if x * order <= target)


def draw(root, record):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Patch, Rectangle
    import numpy as np

    polygons, bounds = _gds_geometry(root, record)
    x0, y0 = (float(v) for v in bounds[0])
    x1, y1 = (float(v) for v in bounds[1])
    require(x1 - x0 > DETAIL_WIDTH_UM and y1 - y0 > DETAIL_WIDTH_UM,
            'Layout too small for fixed physical detail window')
    cx, cy, half = (x0 + x1) / 2, (y0 + y1) / 2, DETAIL_WIDTH_UM / 2
    crop = (cx - half, cy - half, cx + half, cy + half)
    groups, detail, outlines, counts = defaultdict(list), defaultdict(list), [], Counter()
    large_area = .8 * (x1 - x0) * (y1 - y0)
    for polygon in polygons:
        key = (polygon.layer, polygon.datatype)
        require(key[0] in LAYERS and key[1] == 20, 'Unexpected rendered layer')
        points = polygon.points
        counts[f'{key[0]}/{key[1]}'] += 1
        if polygon.area() >= large_area:
            outlines.append(points)
            continue
        groups[key].append(points)
        lo, hi = np.min(points, axis=0), np.max(points, axis=0)
        if hi[0] >= crop[0] and lo[0] <= crop[2] and hi[1] >= crop[1] and lo[1] <= crop[3]:
            detail[key].append(points)
    require(sum(map(len, detail.values())) > 0, 'Central detail has no selected geometry')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
        'figure.facecolor': '#0b1422', 'axes.facecolor': '#111d2d',
        'text.color': '#edf3fa', 'axes.labelcolor': '#b9c9db',
        'xtick.color': '#9cafc3', 'ytick.color': '#9cafc3',
        'axes.edgecolor': '#3a4c63', 'savefig.facecolor': '#0b1422'})
    fig, axes = plt.subplots(1, 2, figsize=(15, 8.5))
    fig.subplots_adjust(left=.065, right=.98, top=.82, bottom=.235, wspace=.20)
    windows = ((x0, y0, x1, y1), crop)
    scale_bars = []
    for ax, geometry, window in zip(axes, (groups, detail), windows):
        for key in sorted(geometry):
            ax.add_collection(PolyCollection(geometry[key], facecolors=LAYERS[key[0]][1],
                edgecolors='none', alpha=.86, rasterized=True))
        if outlines:
            ax.add_collection(PolyCollection(outlines, facecolors='none', edgecolors='#91a2b7',
                                             linewidths=.5))
        a, b, c, d = window
        ax.set(xlim=(a, c), ylim=(b, d), aspect='equal', xlabel='x (µm)', ylabel='y (µm)')
        ax.tick_params(labelsize=9)
        ax.ticklabel_format(axis='both', style='plain', useOffset=False)
        length = scale_length(c - a)
        sx, sy = a + .06 * (c - a), b + .075 * (d - b)
        ax.plot([sx, sx + length], [sy, sy], color='white', linewidth=3, solid_capstyle='butt', zorder=10)
        ax.text(sx + length / 2, sy + .025 * (d - b), f'{length:g} µm', ha='center',
                va='bottom', fontsize=10, color='white', zorder=10,
                bbox={'facecolor': '#0b1422', 'edgecolor': 'none', 'alpha': .9, 'pad': 3})
        scale_bars.append(length)
    axes[0].add_patch(Rectangle((crop[0], crop[1]), DETAIL_WIDTH_UM, DETAIL_WIDTH_UM,
        fill=False, edgecolor='white', linewidth=1.3, linestyle='--'))
    axes[0].set_title(f'Routing overview  ·  {x1-x0:.2f} × {y1-y0:.2f} µm extent',
                      loc='left', fontsize=12, pad=12)
    axes[1].set_title('Central detail  ·  80 × 80 µm', loc='left', fontsize=12, pad=12)
    size = record['array_size']
    fig.text(.065, .944, f'{size} × {size}  |  Actual final GDS', fontsize=24, fontweight='bold')
    fig.text(.065, .902, 'Independently qualified implementation  ·  SKY130A / sky130_fd_sc_hd',
             fontsize=12, color='#a9d6c2')
    fig.text(.065, .869, 'Selected top-cell metal geometry; the dashed square marks the detail window.',
             fontsize=10.5, color='#b9c9db')
    handles = [Patch(facecolor=color, label=f'{name}  {number}/20')
               for number, (name, color) in LAYERS.items()]
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(.06, .158),
               ncol=6, frameon=False, fontsize=10, labelcolor='#c6d4e5')
    fig.text(.065, .126, 'Visible: drawing polygons/paths only. Library-cell interiors, labels, cuts and other layers omitted.',
             fontsize=9.5, color='#a6b8ce')
    fig.text(.065, .096, f'Source: round2 / cfg_{size}x{size} / FINAL_002 / 58-magic-streamout / {record["top_cell"]}.gds',
             fontsize=9, color='#a6b8ce')
    fig.text(.065, .067, 'GDS SHA-256: ' + record['sha256'], fontsize=8.8,
             color='#8ea3bc', fontfamily='DejaVu Sans Mono')
    fig.text(.065, .030, 'Historical evidence visualization  ·  Original 2/4/8 family remains incomplete  ·  No new physical signoff',
             fontsize=9, color='#9dafc4')
    stream = BytesIO()
    fig.savefig(stream, format='png', dpi=180, metadata={'Software': 'Model2GDS qualified GDS visualization'})
    plt.close(fig)
    return stream.getvalue(), {'selected_polygon_counts': dict(sorted(counts.items())),
        'selected_polygon_total': len(polygons), 'large_polygons_outlined': len(outlines),
        'detail_intersecting_polygon_total': sum(map(len, detail.values())),
        'bounds_um': [[x0, y0], [x1, y1]], 'detail_bounds_um': [[crop[0], crop[1]], [crop[2], crop[3]]],
        'overview_scale_bar_um': scale_bars[0], 'detail_scale_bar_um': scale_bars[1]}


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--check', action='store_true', help='Re-render and require byte-identical artifacts')
    args = cli.parse_args(argv)
    import gdstk
    import matplotlib
    import numpy
    from PIL import Image
    payloads, images = {}, []
    for record in inputs():
        blob, statistics = draw(ROOT, record)
        path = f'{OUTPUT}/cfg_{record["array_size"]}x{record["array_size"]}_layout.png'
        image = Image.open(BytesIO(blob))
        payloads[path] = blob
        images.append({'array_size': record['array_size'], 'path': path, 'bytes': len(blob),
            'sha256': hashlib.sha256(blob).hexdigest(), 'pixels': list(image.size),
            'source_gds': record, 'geometry_statistics': statistics})
    manifest = {'schema_version': 1, 'record_type': 'QUALIFIED_FINAL_GDS_VISUALIZATION',
        'status': 'PASS', 'original_three_configuration_family_status': 'FAIL',
        'new_physical_signoff': False, 'eda_run': False,
        'qualification_scope': 'Independently qualified round2 FINAL_002 sizes 2 and 4 only.',
        'render_policy': {'unit': 'um', 'hierarchy_depth': 0, 'paths_included': True,
            'references_expanded': False, 'labels_included': False,
            'selected_layers': [{'name': name, 'layer': number, 'datatype': 20, 'color': color}
                               for number, (name, color) in LAYERS.items()],
            'detail_rule': 'Central 80 um square in selected-geometry bounds for both arrays.',
            'large_polygon_rule': 'Polygon area >= 80 percent of overview bounding area is outlined.',
            'omitted': 'Referenced cell internals, labels, cuts and all unselected layers.',
            'not_a_signoff_check': True},
        'versions': {'python': platform.python_version(), 'gdstk': gdstk.__version__,
                     'matplotlib': matplotlib.__version__, 'numpy': numpy.__version__,
                     'pillow': Image.__version__},
        'sources': [source(p) for p in (PHYSICAL, HISTORICAL, PDK_LAYERS,
            'scripts/render_dac27_round5_layouts.py', 'scripts/reproduce_figures.py',
            'scripts/analyze_dac27_round4_exploratory.py')], 'images': images}
    payloads[f'{OUTPUT}/layout_manifest.json'] = canonical_bytes(manifest)
    for relative, blob in payloads.items():
        path = ROOT / relative
        if args.check or path.exists():
            require(path.is_file() and path.read_bytes() == blob, 'Rendered bytes do not reproduce: ' + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(blob)
    print(json.dumps({'status': 'PASS', 'images': images, 'manifest': source(f'{OUTPUT}/layout_manifest.json')},
                     indent=2, sort_keys=True))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Regenerate publication figures from machine-derived, qualified final analysis.

The pure render_figures(data) API performs no Git, simulator or physical-tool
operation and is suitable for a separately verified portable submission package.
"""
import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.phase1_common import canonical_bytes, sha256

FIGURE_DIR = 'figures/final'
ANALYSIS_PATH = 'results/processed/final_analysis.json'
COLORS = {2: '#2166AC', 4: '#008577', 8: '#D27624'}
LABELS = {size: f'{size}×{size}' for size in (2, 4, 8)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
        'axes.titlesize': 12, 'axes.titleweight': 'bold', 'axes.labelsize': 10,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': '#707982', 'axes.labelcolor': '#28313A',
        'text.color': '#28313A', 'xtick.color': '#4D5965', 'ytick.color': '#4D5965',
        'grid.color': '#DCE2E7', 'grid.linewidth': .6,
        'legend.frameon': False, 'legend.fontsize': 9,
        'svg.fonttype': 'none', 'svg.hashsalt': 'model2gds-final-figures-v1',
        'figure.facecolor': 'white', 'savefig.facecolor': 'white'})
    return plt


def _coverage(plt, data):
    rows = data['functional']['coverage']
    fig, ax = plt.subplots(figsize=(8.0, 3.5), layout='constrained')
    categories = [('directed', 'Directed', '#2166AC'), ('randomized', 'Deterministic random', '#008577'),
                  ('frozen_workload_sanity', 'Frozen workload sanity', '#D27624')]
    left = [0] * len(rows)
    for key, label, color in categories:
        values = [row['category_counts'][key] for row in rows]
        ax.barh(range(len(rows)), values, left=left, height=.55, color=color, label=label,
                edgecolor='white', linewidth=.7)
        for index, value in enumerate(values):
            if value >= 5:
                ax.text(left[index] + value / 2, index, str(value), va='center', ha='center',
                        color='white', fontsize=10, fontweight='bold')
        left = [start + value for start, value in zip(left, values)]
    maximum = max(row['case_count'] for row in rows)
    for index, row in enumerate(rows):
        ax.text(maximum + 3, index,
                f"{row['numerical_passed']}/{row['case_count']} numerical\n{row['cycle_passed']}/{row['case_count']} cycles",
                va='center', fontsize=9, color='#354C57')
    ax.set(yticks=range(len(rows)), yticklabels=[LABELS[row['array_size']] for row in rows],
           xlim=(0, maximum * 1.34), xlabel='Verified case executions',
           title='One deterministic case plan, three verified array sizes')
    ax.set_xticks([0, maximum // 3, 2 * maximum // 3, maximum])
    ax.invert_yaxis()
    fig.legend(*ax.get_legend_handles_labels(), loc='outside lower center', ncol=3)
    ax.grid(axis='x', alpha=.45)
    ax.set_axisbelow(True)
    return fig


def _cycles(plt, data):
    points = data['functional']['cycle_points']
    fig, ax = plt.subplots(figsize=(6.4, 5.1), layout='constrained')
    low = min(min(row['model_cycles'], row['rtl_cycles']) for row in points)
    high = max(max(row['model_cycles'], row['rtl_cycles']) for row in points)
    ax.plot([low, high], [low, high], color='#9BA6AE', linestyle='--', linewidth=1,
            label='Exact agreement', zorder=1)
    for size, marker in zip((2, 4, 8), ('o', 's', '^')):
        subset = [row for row in points if row['array_size'] == size]
        ax.scatter([row['model_cycles'] for row in subset], [row['rtl_cycles'] for row in subset],
                   s=32, marker=marker, color=COLORS[size], alpha=.67,
                   edgecolors='white', linewidths=.35, label=f'{LABELS[size]} · {len(subset)} cases', zorder=2)
    ax.set(xscale='log', yscale='log', xlabel='Token-model counted rising edges',
           ylabel='RTL-observed counted rising edges', title='Matched model and RTL cycle semantics')
    ax.set_xlim(low / 1.6, high * 1.6)
    ax.set_ylim(low / 1.6, high * 1.6)
    ax.set_aspect('equal', adjustable='box')
    ax.grid(alpha=.6)
    differences = [abs(row['model_cycles'] - row['rtl_cycles']) for row in points]
    ax.text(.04, .95, f"{len(points)} executions\nMaximum absolute difference: {max(differences)} edges",
            transform=ax.transAxes, va='top', fontsize=10)
    ax.legend(loc='lower right')
    return fig


def _wavefront(plt, data):
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Rectangle
    trace = data['wavefront_example']
    frames = trace['trace']
    size = trace['array_size']
    require(size == 2 and trace['case_id'] == 'D_POSITIVE', 'Unexpected explanatory trace case')
    fig, (fabric, schedule) = plt.subplots(1, 2, figsize=(10.0, 4.0),
        gridspec_kw={'width_ratios': [1, 1.7]}, layout='constrained')
    for row in range(size):
        for col in range(size):
            x, y = col, size - 1 - row
            fabric.add_patch(Rectangle((x - .28, y - .25), .56, .50,
                facecolor='#E9F0F6', edgecolor=COLORS[2], linewidth=1.3))
            fabric.text(x, y, f'PE {row},{col}\nINT32 C', ha='center', va='center', fontsize=9)
            if col < size - 1:
                fabric.annotate('', (x + .7, y), (x + .30, y),
                    arrowprops={'arrowstyle': '->', 'color': COLORS[2], 'lw': 1.4})
            if row < size - 1:
                fabric.annotate('', (x, y - .73), (x, y - .28),
                    arrowprops={'arrowstyle': '->', 'color': COLORS[4], 'lw': 1.4})
        y = size - 1 - row
        fabric.annotate('', (-.3, y), (-.78, y),
            arrowprops={'arrowstyle': '->', 'color': COLORS[2], 'lw': 1.4})
        fabric.text(-.80, y + .14, f'A{row}[k]', ha='left', color=COLORS[2], fontsize=9)
    for col in range(size):
        fabric.annotate('', (col, 1.29), (col, 1.78),
            arrowprops={'arrowstyle': '->', 'color': COLORS[4], 'lw': 1.4})
        fabric.text(col, 1.82, f'B{col}[k]', ha='center', color=COLORS[4], fontsize=9)
    fabric.set(xlim=(-.95, 1.65), ylim=(-.50, 2.2), aspect='equal', title='Registered neighbor links')
    fabric.axis('off')
    activity = []
    for index in range(size * size):
        activity.append([frame['pe'][index]['a']['k'] + 1
                         if frame['pe'][index]['a']['valid'] and frame['pe'][index]['b']['valid'] else 0
                         for frame in frames])
    schedule.imshow(activity, cmap=ListedColormap(['#F0F3F5', '#8AC9C4', '#2166AC']),
                    aspect='auto', vmin=0, vmax=trace['K'], interpolation='nearest')
    for row in range(size * size):
        for col, frame in enumerate(frames):
            value = activity[row][col]
            label = f'k={value - 1}' if value else 'clear' if frame['phase'] == 'clear' else '—'
            if value and frame['pe'][row]['a']['last'] and frame['pe'][row]['b']['last']:
                label += '\nlast'
            schedule.text(col, row, label, ha='center', va='center', fontsize=9,
                          color='white' if value == trace['K'] else '#28313A')
    schedule.set(xticks=range(len(frames)), xticklabels=[frame['cycle'] for frame in frames],
        yticks=range(size * size), yticklabels=[f'PE {i // size},{i % size}' for i in range(size * size)],
        xlabel='Counted rising edge (clear included)', title=f"Aligned tokens, K={trace['K']}")
    schedule.set_xticks([i - .5 for i in range(len(frames) + 1)], minor=True)
    schedule.set_yticks([i - .5 for i in range(size * size + 1)], minor=True)
    schedule.grid(which='minor', color='white', linewidth=2)
    schedule.tick_params(which='minor', bottom=False, left=False)
    fig.suptitle(f"Output-stationary wavefront · accepted {trace['case_id']} input, explanatory model trace", fontsize=12)
    return fig


def _physical(plt, data):
    rows = data['scientific_analysis']['configurations']
    fig, (area, timing) = plt.subplots(1, 2, figsize=(9, 3.8), layout='constrained')
    xs = list(range(len(rows)))
    area.bar([x - .17 for x in xs], [row['cell_area_um2'] for row in rows], width=.32,
             color='#2166AC', label='Standard cells')
    area.bar([x + .17 for x in xs], [row['core_area_um2'] for row in rows], width=.32,
             color='#88B7D8', label='Core')
    area.set(ylabel='Area (µm²)', title='Post-route physical footprint')
    area.legend()
    timing.plot(xs, [row['sta_frequency_MHz'] for row in rows], marker='o', color=COLORS[4], linewidth=1.8)
    timing.set(ylabel='STA-derived frequency estimate (MHz)', title='Fixed-layout internal timing')
    for ax in (area, timing):
        ax.set(xticks=xs, xticklabels=[LABELS[row['array_size']] for row in rows], xlabel='Array configuration')
        ax.grid(axis='y', alpha=.5)
        ax.set_axisbelow(True)
    fig.suptitle('Accepted final family · one recipe and timing method', fontsize=12)
    return fig


def _latencies(plt, data):
    workloads = data['scientific_analysis']['workloads']
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.1), layout='constrained')
    for ax, field, label, title in zip(axes, ('model_cycles', 'implementation_latency_ns'),
            ('Counted rising edges', 'Implementation-aware latency (ns)'),
            ('Architecture abstraction', 'Cycles with accepted post-route timing')):
        for index, size in enumerate((2, 4, 8)):
            values = [next(row[field] for row in workload['configurations'] if row['array_size'] == size) for workload in workloads]
            ax.bar([position + (index - 1) * .24 for position in range(len(workloads))], values,
                   width=.23, color=COLORS[size], label=LABELS[size])
        ax.set(xticks=range(len(workloads)), xticklabels=[row['workload_id'] for row in workloads],
               yscale='log', ylabel=label, title=title)
        ax.grid(axis='y', alpha=.45)
        ax.set_axisbelow(True)
        ax.legend(ncol=3, loc='upper left')
    return fig


def _pairwise(plt, data):
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    decisions = data['scientific_analysis']['pairwise']['decisions']
    classes = {'preserved': 0, 'tied_or_indeterminate': 1, 'reversed': 2}
    colors = ['#D9E9F4', '#EEEEEE', '#F2C99F']
    pairs = [(2, 4), (2, 8), (4, 8)]
    ordered = [[next(row for row in decisions if row['workload_id'] == f'W{w}'
                        and (row['array_i'], row['array_j']) == pair) for pair in pairs] for w in range(1, 7)]
    fig, ax = plt.subplots(figsize=(7.1, 5.0), layout='constrained')
    ax.imshow([[classes[row['decision']] for row in line] for line in ordered],
              cmap=ListedColormap(colors), vmin=0, vmax=2, aspect='auto', interpolation='nearest')
    for i, line in enumerate(ordered):
        for j, row in enumerate(line):
            label = 'tied / indet.' if row['decision'] == 'tied_or_indeterminate' else row['decision']
            ax.text(j, i, f"{label}\nΔ log margin {row['margin_delta']:+.3f}", ha='center', va='center', fontsize=9)
    ax.set(xticks=range(3), xticklabels=[f'{LABELS[a]} : {LABELS[b]}' for a, b in pairs],
           yticks=range(6), yticklabels=[f'W{i}' for i in range(1, 7)],
           title=f'{len(decisions)} pairwise architecture-to-implementation decisions')
    ax.set_xticks([i - .5 for i in range(4)], minor=True)
    ax.set_yticks([i - .5 for i in range(7)], minor=True)
    ax.grid(which='minor', color='white', linewidth=2)
    ax.tick_params(which='minor', bottom=False, left=False)
    ax.legend(handles=[Patch(facecolor=colors[index], label=label) for index, label in
                       enumerate(('Preserved', 'Tied / indeterminate', 'Reversed'))],
              loc='lower center', bbox_to_anchor=(.5, -.17), ncol=3)
    return fig


def _margins(plt, data):
    decisions = data['scientific_analysis']['pairwise']['decisions']
    fig, ax = plt.subplots(figsize=(6.8, 5.0), layout='constrained')
    all_values = [row[key] for row in decisions for key in ('M_arch', 'M_impl')]
    low, high = min(all_values + [0.0]), max(all_values + [0.0])
    span = max(high - low, .5)
    lower, upper = low - span * .12, high + span * .12
    ax.plot([lower, upper], [lower, upper], color='#9BA6AE', linestyle='--', linewidth=1,
            label='Unchanged log margin')
    ax.axhline(0, color='#CDD4DA', linewidth=.7)
    ax.axvline(0, color='#CDD4DA', linewidth=.7)
    for pair, color, marker in zip(((2, 4), (2, 8), (4, 8)), COLORS.values(), ('o', 's', '^')):
        rows = [row for row in decisions if (row['array_i'], row['array_j']) == pair]
        ax.scatter([row['M_arch'] for row in rows], [row['M_impl'] for row in rows], s=46,
                   color=color, marker=marker, edgecolors='white', linewidths=.5,
                   label=f'{LABELS[pair[0]]} : {LABELS[pair[1]]} · {len(rows)} workloads')
    ax.set(xlim=(lower, upper), ylim=(lower, upper), xlabel='Architecture margin: ln(Cᵢ / Cⱼ)',
           ylabel='Implementation margin: ln(Tᵢ / Tⱼ)', title='Decision-margin transformation')
    ax.grid(alpha=.4)
    ax.legend(loc='best')
    ax.text(.02, .97, 'All observations retained; coincident points are not displaced.',
            transform=ax.transAxes, fontsize=8, va='top', color='#667481')
    return fig


def _gds_geometry(root, record):
    """Read bounded top-cell interconnect geometry; never synthesize routing.

    Numeric GDS layers 67--72, datatype 20 are selected consistently. Reference
    geometry is not expanded, so large arrays do not create millions of shapes.
    """
    import gdstk
    root = Path(root).resolve()
    relative = record['path']
    require(isinstance(relative, str) and not Path(relative).is_absolute()
            and '..' not in Path(relative).parts and '\\' not in relative,
            'Layout source must be repository-relative')
    path = root / relative
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root),
            'Missing/nonordinary layout GDS')
    blob = path.read_bytes()
    require(len(blob) == record['bytes'] and hashlib.sha256(blob).hexdigest() == record['sha256'],
            'Layout GDS identity differs from accepted source')
    library = gdstk.read_gds(path, unit=1e-6, filter={(layer, 20) for layer in range(67, 73)})
    selected = [cell for cell in library.top_level() if cell.name == record['top_cell']]
    require(len(selected) == 1, 'Accepted GDS top cell is missing or ambiguous')
    cell = selected[0]
    polygons = cell.get_polygons(apply_repetitions=True, include_paths=True, depth=0)
    bounds = cell.bounding_box()
    require(polygons and bounds is not None, 'Layout contains no polygon geometry')
    return polygons, bounds


def _layouts(plt, data, root):
    from collections import defaultdict
    from matplotlib.collections import PolyCollection
    records = data['layout_sources']
    primary = data['analysis_mode'] == 'PRIMARY_RESEARCH'
    require([record['array_size'] for record in records] == ([2, 4, 8] if primary else [None]),
            'Layout array family differs from analysis mode')
    require(all(record['kind'] == ('QUALIFIED_FINAL_ARRAY' if primary else 'TINY_COUNTER_TOOLCHAIN_PROOF')
                for record in records), 'Layout qualification differs from analysis mode')
    fig, axes = plt.subplots(1, len(records), figsize=(11.2, 4.6) if primary else (6.4, 5.4),
                             squeeze=False, layout='constrained')
    for ax, record in zip(axes[0], records):
        polygons, bounds = _gds_geometry(root, record)
        (x0, y0), (x1, y1) = bounds
        require(x1 > x0 and y1 > y0, 'Layout bounds must have positive extent')
        groups = defaultdict(list)
        outlines = []
        for polygon in polygons:
            if polygon.area() >= .8 * (x1 - x0) * (y1 - y0):
                outlines.append(polygon.points)
            else:
                groups[(polygon.layer, polygon.datatype)].append(polygon.points)
        for index, key in enumerate(sorted(groups)):
            color = plt.get_cmap('tab20')(index % 20)
            ax.add_collection(PolyCollection(groups[key], facecolors=[color], edgecolors='none',
                                             alpha=.68, rasterized=True))
        if outlines:
            ax.add_collection(PolyCollection(outlines, facecolors='none', edgecolors='#637180',
                                             linewidths=.45, rasterized=True))
        ax.set(xlim=(x0, x1), ylim=(y0, y1), aspect='equal', xlabel='x (µm)', ylabel='y (µm)',
               title=f"{record['array_size']}×{record['array_size']} accepted final" if primary else 'Tiny counter · accepted toolchain proof')
        ax.tick_params(labelsize=8)
        ax.text(.0, -.22, 'GDS SHA256: ' + record['sha256'][:16] + '…', transform=ax.transAxes,
                fontsize=8, color='#667481')
    fig.suptitle('Actual GDS layout geometry', fontsize=13, fontweight='bold')
    fig.supxlabel('Top-cell polygons/paths: GDS layers 67–72, datatype 20.\n'
                  'Reference-cell geometry and labels omitted; large boundary polygons shown as outlines.', fontsize=9)
    return fig


def render_figures(analysis, *, root=None):
    require(analysis.get('status') == 'PASS', 'Figure input analysis did not pass')
    mode = analysis.get('analysis_mode')
    require(mode in ('PRIMARY_RESEARCH', 'EDUCATIONAL_FALLBACK'), 'Unknown analysis mode')
    require((analysis.get('scientific_analysis') is not None) == (mode == 'PRIMARY_RESEARCH'),
            'Scientific quantities must be absent from fallback figures')
    require(analysis.get('rejected_physical_performance_used') is False, 'Rejected performance must not enter figures')
    plt = _style()
    makers = [('functional_coverage', _coverage), ('cycle_agreement', _cycles), ('token_wavefront', _wavefront)]
    if mode == 'PRIMARY_RESEARCH':
        makers += [('physical_scaling', _physical), ('cycles_and_latency', _latencies),
                   ('pairwise_decisions', _pairwise), ('margin_transformation', _margins)]
    if 'layout_sources' in analysis:
        require(root is not None, 'Actual GDS rendering requires the evidence root')
        makers.append(('layout_overview', lambda plt, data: _layouts(plt, data, root)))
    result = {}
    for name, maker in makers:
        figure = maker(plt, analysis)
        try:
            for extension in ('svg', 'png'):
                stream = BytesIO()
                metadata = ({'Date': None, 'Creator': 'Model2GDS reproducible figures'} if extension == 'svg'
                            else {'Software': 'Model2GDS reproducible figures'})
                figure.savefig(stream, format=extension, dpi=220, bbox_inches='tight', metadata=metadata)
                result[name + '.' + extension] = stream.getvalue()
        finally:
            plt.close(figure)
    return result


def write_or_check_figures(root, analysis, check=False):
    import matplotlib
    root = Path(root)
    require(analysis.get('layout_sources'), 'Final figures require accepted actual-GDS layout sources')
    payload = render_figures(analysis, root=root)
    records = []
    for name, data in sorted(payload.items()):
        relative = FIGURE_DIR + '/' + name
        records.append({'path': relative, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    manifest = {'schema_version': 1, 'status': 'PASS', 'analysis_mode': analysis['analysis_mode'],
        'analysis': {'path': ANALYSIS_PATH, 'sha256': sha256(root / ANALYSIS_PATH), 'bytes': (root / ANALYSIS_PATH).stat().st_size},
        'renderer': {'path': 'scripts/reproduce_figures.py', 'sha256': sha256(root / 'scripts/reproduce_figures.py'),
                     'bytes': (root / 'scripts/reproduce_figures.py').stat().st_size},
        'matplotlib_version': matplotlib.__version__, 'files': records,
        'layout_sources': analysis['layout_sources'],
        'gdstk_version': __import__('gdstk').__version__,
        'meaning': 'Figures contain parser/model-derived data. Fallback figures contain no physical-performance comparison.'}
    payload['figure_manifest.json'] = canonical_bytes(manifest)
    folder = root / FIGURE_DIR
    # Validate the whole existing set before writing anything new.
    expected_names = set(payload)
    if folder.exists():
        unexpected = {path.name for path in folder.iterdir() if path.is_file()} - expected_names
        require(not unexpected, 'Unexpected/stale figure files must be reviewed: ' + ','.join(sorted(unexpected)))
    for name, data in payload.items():
        path = folder / name
        if check or path.exists():
            require(path.is_file() and path.read_bytes() == data, 'Figure bytes do not reproduce: ' + name)
    if not check:
        folder.mkdir(parents=True, exist_ok=True)
        for name, data in payload.items():
            path = folder / name
            if not path.exists():
                with path.open('xb') as stream:
                    stream.write(data)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--portable', action='store_true', help='Require the package verifier before rendering its processed analysis')
    parser.add_argument('--selection', help='Explicit final-family selection; omitted preserves the historical default')
    parser.add_argument('--physical-output', help='Explicit processed physical record; omitted preserves the historical default')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.portable:
        require(args.selection is None and args.physical_output is None,
                'Portable rendering uses its verified package binding, not selection overrides')
        from scripts.build_submission import verify_package
        verification = verify_package(root)
        require(verification.get('status') == 'PASS', 'Portable package verification did not pass')
        analysis = json.loads((root / ANALYSIS_PATH).read_text(encoding='utf-8'))
    else:
        from scripts.analyze_final_results import analyze
        binding = {}
        if args.selection is not None:
            binding['selection_path'] = args.selection
        if args.physical_output is not None:
            binding['physical_output'] = args.physical_output
        analysis = analyze(root, **binding)
        require(canonical_bytes(analysis) == (root / ANALYSIS_PATH).read_bytes(), 'Analysis bytes do not reproduce')
    manifest = write_or_check_figures(root, analysis, args.check)
    print(canonical_bytes({'status': 'PASS', 'analysis_mode': manifest['analysis_mode'],
        'figure_files': len(manifest['files']), 'manifest': FIGURE_DIR + '/figure_manifest.json'}).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

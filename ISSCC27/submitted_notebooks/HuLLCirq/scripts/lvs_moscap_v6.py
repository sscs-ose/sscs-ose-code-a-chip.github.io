"""Qualified MOSCAP extraction inputs and pure retained-model proof.

Importing this module does nothing. CLI preparation/finalization is called only
by the explicitly started, fixed S13 launcher. No model, shell or EDA process is
started here. The source GDS, installed PDK and original reference SPICE are
never changed. Only separate run-local derived inputs/records are created.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

SCHEMA = 'hullcirq-qualified-moscap-recognition-v4'
CELL = 'sky130_fd_sc_hd__decap_3'
STYLE = 'hullcirq_moscap_v6'
BASE_STYLE = 'ngspice()'
BASE_TECH_SHA = 'd9ef56e3ab01b8fb605edf964fcfa01a0bf14ca8503f6ccecdecfd71f0907519'
LIBRARY_GDS = 'libs.ref/sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds'
LIBRARY_GDS_SHA = 'c0cce10fedffd4f5b3eb4c95bbefd2b035c33bfb9264d35c8495743b3b852911'
LIBRARY_SPICE = 'libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice'
LIBRARY_SPICE_SHA = '304da9725492089107bb20840a4020558b028487d300f8df79bbbad5332aaa99'
MODELS = {'hullcirq_moscap_nfet_v6': 'sky130_fd_pr__nfet_01v8',
          'hullcirq_moscap_pfet_v6': 'sky130_fd_pr__pfet_01v8_hvt'}
SAFE_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_$]*\Z')
FILES = {'base_tech': 'source-sky130A.tech', 'derived_tech': 'derived-sky130A-moscap-v6.tech',
         'reference_gds': 'source-sky130_fd_sc_hd.gds', 'reference_spice': 'source-sky130_fd_sc_hd.spice',
         'wrappers': 'lvs_moscap_models_v6.spice', 'plan': 'extraction-cell-plan.json',
         'plan_tcl': 'extraction-cell-plan.tcl', 'execution_log': 'extraction-cell-log.json',
         'raw_spice': 'extraction-raw.spice', 'comparison_spice': 'extraction-comparison.spice',
         'proof': 'extraction-model-proof.json'}
INVENTORY_SCHEMA = 'hullcirq-magic-source-inventory-v1'
INVENTORY_PHASES = ('pre_gds', 'post_gds', 'post_annotation')
NATIVE_ERROR_PATTERN = re.compile(r'freeMagic called with NULL argument\.?|'
    r'Device parameters do not match any extraction model\.?|No cell selected', re.I)


def require(condition, message):
    if not condition:
        raise ValueError('MOSCAP recognition: ' + message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def object_hash(value):
    def exact(item):
        if isinstance(item, Fraction):
            return {'gds_exact_fraction': [item.numerator, item.denominator]}
        raise TypeError('Unsupported canonical object type')
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                             allow_nan=False, default=exact).encode('utf-8'))


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda text: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


def native_path(value):
    require(type(value) is str, 'missing fixed input path')
    if sys.platform != 'win32' and re.match(r'^[A-Za-z]:[\\/]', value):
        return Path('/mnt/' + value[0].lower() + '/' + value[3:].replace('\\', '/'))
    return Path(value)


def linux_path(path):
    value = str(path.resolve()).replace('\\', '/')
    return '/mnt/' + value[0].lower() + '/' + value[3:] if re.match(r'^[A-Za-z]:/', value) else value


def _real(raw):
    word = int.from_bytes(raw, 'big')
    return Decimal(-1 if word >> 63 else 1) * Decimal(word & ((1 << 56) - 1)) / Decimal(1 << 56) * Decimal(16) ** (((word >> 56) & 127) - 64)


def _unit_picometres(raw):
    """Decode the exact REAL8 rational; never round geometric coordinates."""
    require(len(raw) == 8, 'invalid GDS unit')
    word = int.from_bytes(raw, 'big')
    exponent = ((word >> 56) & 127) - 64
    unit = Fraction(word & ((1 << 56) - 1), 1 << 56) * Fraction(16) ** exponent * 1_000_000_000_000
    require(not word >> 63 and unit > 0, 'GDS grid is not positive')
    return unit


def _ring(points):
    points = list(points)
    if points and points[0] == points[-1]:
        points.pop()
    require(len(points) >= 3, 'invalid polygon')
    while len(points) > 3:
        reduced = [p for i, p in enumerate(points) if
                   (p[0] - points[i-1][0]) * (points[(i+1) % len(points)][1] - p[1]) !=
                   (p[1] - points[i-1][1]) * (points[(i+1) % len(points)][0] - p[0])]
        if len(reduced) == len(points):
            break
        require(len(reduced) >= 3, 'degenerate polygon')
        points = reduced
    variants = []
    for ordered in (points, list(reversed(points))):
        variants += [tuple(ordered[i:] + ordered[:i]) for i in range(len(ordered))]
    return min(variants)


def gds_cells(raw):
    """Canonical full leaf geometry/labels; no extraction or layout changes."""
    offset, unit, cell, element = 0, None, None, None
    cells = {}
    while offset < len(raw):
        require(offset + 4 <= len(raw), 'truncated GDS header')
        length, kind, datatype = struct.unpack('>HBB', raw[offset:offset+4])
        require(length >= 4 and length % 2 == 0 and offset + length <= len(raw), 'invalid GDS record')
        value = raw[offset+4:offset+length]
        offset += length
        if kind == 3:
            require(len(value) == 16, 'invalid GDS units record')
            unit = _unit_picometres(value[8:])
        elif kind == 6:
            cell = value.rstrip(b'\0').decode('ascii')
            require(SAFE_NAME.fullmatch(cell) and cell not in cells, 'unsafe or duplicate GDS definition')
            cells[cell] = {'elements': [], 'children': []}
        elif kind in (8, 9, 10, 11, 12, 45):
            require(element is None and cell is not None, 'nested or unscoped GDS element')
            element = {'kind': kind, 'records': []}
        elif element is not None:
            if kind == 16:
                require(unit is not None and len(value) % 8 == 0, 'invalid GDS coordinates')
                values = struct.unpack('>' + 'i' * (len(value) // 4), value)
                coordinates = [v * unit for v in values]
                element['xy'] = list(zip(coordinates[::2], coordinates[1::2]))
            elif kind in (13, 14, 22):
                element[{13: 'layer', 14: 'datatype', 22: 'texttype'}[kind]] = struct.unpack('>h', value)[0]
            elif kind in (18, 25):
                element['master' if kind == 18 else 'text'] = value.rstrip(b'\0').decode('ascii')
            elif kind == 17:
                require('xy' in element, 'GDS element has no coordinates')
                if element['kind'] == 8:
                    canonical = [8, element.get('layer'), element.get('datatype'), _ring(element['xy'])]
                elif element['kind'] == 12:
                    # Font/presentation does not alter label attachment geometry.
                    canonical = [12, element.get('layer'), element.get('texttype'), element['xy'], element.get('text')]
                else:
                    canonical = element
                cells[cell]['elements'].append(canonical)
                if element['kind'] in (10, 11):
                    require(element.get('master') is not None, 'GDS reference has no master')
                    cells[cell]['children'].append(element['master'])
                element = None
            elif kind not in (23,):
                element['records'].append([kind, datatype, value.hex()])
    require(offset == len(raw) and element is None and unit is not None, 'incomplete GDS')
    for value in cells.values():
        value['geometry_sha256'] = object_hash(sorted(value['elements'], key=object_hash))
    return cells


def spice_number(text):
    match = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(meg|[tgkmunpf])?', text, re.I)
    require(match is not None, 'nonexact numeric device parameter')
    factors = {'t': 12, 'g': 9, 'meg': 6, 'k': 3, 'm': -3, 'u': -6, 'n': -9, 'p': -12, 'f': -15, None: 0}
    value = Decimal(match[1]) * Decimal(10) ** factors[match[2].lower() if match[2] else None]
    require(value.is_finite() and value >= 0, 'invalid device parameter')
    return format(value.normalize(), 'f')


def cell_spice(text, name):
    lines, selected, inside = [], [], False
    for line in text.splitlines():
        if line.lstrip().startswith('+'):
            require(bool(lines), 'orphan SPICE continuation')
            lines[-1] += ' ' + line.lstrip()[1:]
        else:
            lines.append(line.strip())
    for line in lines:
        if re.match(r'\.subckt\s+' + re.escape(name) + r'(?:\s|$)', line, re.I):
            require(not selected, 'duplicate qualified SPICE cell')
            inside = True
        if inside:
            selected.append(line)
            if re.match(r'\.ends(?:\s|$)', line, re.I):
                inside = False
    require(selected and not inside, 'qualified SPICE cell missing or incomplete')
    return selected


def cap_devices(text, aliases=False):
    lines = cell_spice(text, CELL)
    require(lines[0].split()[2:] == ['VGND', 'VNB', 'VPB', 'VPWR'], 'qualified cell port order changed')
    result = []
    for line in lines[1:-1]:
        if not line or line.startswith('*'):
            continue
        tokens = line.split()
        require(tokens[0][0].lower() == 'x', 'qualified cell contains unexpected device')
        count = 3 if aliases else 4
        require(len(tokens) > count + 2, 'incomplete qualified device')
        pins, model = tokens[1:count+1], tokens[count+1]
        parameters = {}
        for token in tokens[count+2:]:
            match = re.fullmatch(r'(w|l|as|ps|ad|pd)=(.+)', token, re.I)
            require(match and match[1].lower() not in parameters, 'unexpected or duplicate qualified parameter')
            parameters[match[1].lower()] = spice_number(match[2])
        require(set(parameters) >= {'w', 'l'} and Decimal(parameters['w']) > 0 and Decimal(parameters['l']) > 0, 'missing actual positive W/L')
        if aliases:
            require(model in MODELS, 'unexpected MOSCAP wrapper model')
            pins = [pins[0], pins[1], pins[0], pins[2]]
            model = MODELS[model]
        require(model in MODELS.values() and pins[0] == pins[2] and pins[0] != pins[1], 'not a tied-S/D MOSCAP')
        result.append({'model': model, 'pins': pins, 'w': parameters['w'], 'l': parameters['l']})
    require(len(result) == 2 and Counter(d['model'] for d in result) == Counter(MODELS.values()), 'require exactly both original MOSCAP devices')
    return sorted(result, key=object_hash)


def derived_tech(base):
    require(digest(base) == BASE_TECH_SHA, 'base PDK technology hash changed')
    text = base.decode('utf-8')
    match = re.search(r'^extract\s*\n(.*?)^end\s*$', text, re.M | re.S)
    require(match is not None, 'base extraction section missing')
    body = match[1]
    header = ' style ngspice variants (),(orig),(si),(hrhc),(lrhc),(hrlc),(lrlc)'
    require(body.count(header) == 1, 'base style declaration changed')
    alternate = body.replace(header, ' style ' + STYLE + ' variants ()', 1)
    for model, alias, gate, diffusion in (
            ('sky130_fd_pr__nfet_01v8', 'hullcirq_moscap_nfet_v6', 'nfet,scnfet', 'ndiff,ndiffres'),
            ('sky130_fd_pr__pfet_01v8_hvt', 'hullcirq_moscap_pfet_v6', 'pfethvt,scpfethvt', 'pdiff,pdiffres'),
            # Later width variants are searched first by Magic. They must have
            # the same SD signature for width-based model selection to reach
            # the main alias. Preserve both special names and all width limits.
            ('sky130_fd_pr__special_nfet_01v8', 'sky130_fd_pr__special_nfet_01v8', 'scnfet', 'ndiff,ndiffres'),
            ('sky130_fd_pr__special_pfet_01v8_hvt', 'sky130_fd_pr__special_pfet_01v8_hvt', 'scpfethvt', 'pdiff,pdiffres')):
        old = 'device msubcircuit ' + model + ' ' + gate + ' \\\n\t*' + diffusion + ' *' + diffusion
        new = 'device msubcircuit ' + alias + ' ' + gate + ' 1 \\\n\t*' + diffusion
        require(alternate.count(old) == 1, 'base MOS rule declaration changed')
        alternate = alternate.replace(old, new, 1)
    insertion = '\n# HuLLCirq v6: only the qualified leaf is extracted under this separate style.\n' + alternate
    return (text[:match.end(1)] + insertion + text[match.end(1):]).encode('utf-8')


def make_plan(gds_raw, reference_gds, reference_spice, top):
    cells, vendor = gds_cells(gds_raw), gds_cells(reference_gds)
    require(top in cells and CELL in cells and CELL in vendor, 'top or qualified MOSCAP definition missing')
    require(not cells[CELL]['children'] and not vendor[CELL]['children']
            and cells[CELL]['geometry_sha256'] == vendor[CELL]['geometry_sha256'], 'qualified MOSCAP full geometry/labels differ from pinned vendor master')
    expected_devices = cap_devices(reference_spice.decode('utf-8'))
    order, active, seen = [], set(), set()
    def visit(name):
        require(name in cells and name not in active, 'missing/cyclic GDS hierarchy')
        if name in seen:
            return
        active.add(name)
        for child in sorted(set(cells[name]['children'])):
            visit(child)
        active.remove(name)
        seen.add(name)
        order.append(name)
    visit(top)
    require(seen == set(cells), 'unreachable GDS definitions require separate qualification')
    return {'schema': SCHEMA, 'top': top, 'qualified_cell': CELL,
            'qualified_geometry_sha256': cells[CELL]['geometry_sha256'],
            'qualified_devices': expected_devices, 'definition_count': len(cells),
            'qualified_instance_uses': sum(v['children'].count(CELL) for v in cells.values()),
            'source_children': {name: sorted(set(value['children'])) for name, value in cells.items()},
            'cells': [{'name': name, 'style': STYLE + '()' if name == CELL else BASE_STYLE} for name in order]}


def _plan_tcl(plan):
    names = ' '.join('{' + row['name'] + '}' for row in plan['cells'])
    rows = ' '.join('{{' + row['name'] + '} {' + row['style'] + '}}' for row in plan['cells'])
    return ('set hullcirq_expected_cells {' + names + '}\nset hullcirq_cell_plan {' + rows + '}\n').encode('ascii')


def prepare(root):
    root = Path(root).resolve()
    manifest = load(root / 'input-manifest.json')
    profile = manifest['configuration']['profile']
    require(profile.get('profile_version') == 'hullcirq-sky130-lvs-v6', 'wrong extraction profile')
    pdk = load(root / 'pdk-input-manifest.json')
    pdk_root = native_path(pdk['root'])
    for relative, target, expected in (
            ('libs.tech/magic/sky130A.tech', FILES['base_tech'], BASE_TECH_SHA),
            (LIBRARY_GDS, FILES['reference_gds'], LIBRARY_GDS_SHA),
            (LIBRARY_SPICE, FILES['reference_spice'], LIBRARY_SPICE_SHA)):
        raw = (pdk_root / relative).read_bytes()
        require(digest(raw) == expected and pdk['files'][relative]['sha256'] == expected, 'pinned vendor source changed')
        write_new(root / target, raw)
    top = load(root / 'config.json')['DESIGN_NAME']
    plan = make_plan((root / 'input.gds').read_bytes(), (root / FILES['reference_gds']).read_bytes(),
                     (root / FILES['reference_spice']).read_bytes(), top)
    write_new(root / FILES['derived_tech'], derived_tech((root / FILES['base_tech']).read_bytes()))
    write_new(root / FILES['plan'], json_bytes(plan))
    write_new(root / FILES['plan_tcl'], _plan_tcl(plan))
    return plan


def record_execution(root, args):
    root = Path(root).resolve()
    plan = load(root / FILES['plan'])
    require(len(args) == len(plan['cells']) * 5, 'incomplete extraction execution record')
    records, previous = [], 0
    for index, row in enumerate(plan['cells']):
        name, style, selected, before, after = args[index*5:index*5+5]
        require({'name': name, 'style': style} == row and selected == name
                and re.fullmatch(r'\d+', before) and re.fullmatch(r'\d+', after), 'extraction selection/execution differs from exact plan')
        before, after = int(before), int(after)
        require(before == previous and after >= before, 'feedback disappeared during extraction/style change')
        records.append({**row, 'selected_cell': selected, 'feedback_before': before, 'feedback_after': after})
        previous = after
    value = {'schema': SCHEMA, 'cells': records, 'definition_count': len(records), 'feedback_count': previous}
    write_new(root / FILES['execution_log'], json_bytes(value))


def _inventory_path(root, phase):
    require(phase in INVENTORY_PHASES, 'unknown inventory phase')
    return Path(root) / ('source-inventory-' + phase + '.json')


def validate_inventory(value, plan, baseline=None, previous=None):
    require(type(value) is dict and value.get('schema') == INVENTORY_SCHEMA
            and value.get('phase') in INVENTORY_PHASES and type(value.get('cells')) is list,
            'invalid native definition inventory')
    rows = value['cells']
    require(all(type(row) is dict and set(row) == {'name', 'flags', 'children', 'paint_type_count',
                'label_count', 'selected_instance_count'} for row in rows), 'incomplete native definition inventory row')
    names = [row['name'] for row in rows]
    require(all(type(name) is str and name and '\n' not in name for name in names)
            and names == sorted(set(names)), 'duplicate or unsorted native definitions')
    source = set(plan['source_children'])
    for row in rows:
        require(all(type(row[key]) is list and all(type(v) is str for v in row[key])
                    and row[key] == sorted(set(row[key])) for key in ('flags', 'children')),
                'invalid native definition flags or child graph')
        require(all(type(row[key]) is int for key in ('paint_type_count', 'label_count', 'selected_instance_count')),
                'missing exact native geometry inventory counts')
    if value['phase'] == 'pre_gds':
        require(not source.intersection(names), 'source definition already existed before GDS load')
    else:
        require(baseline is not None and source <= set(names), 'source GDS definition was not loaded')
        require(set(names) - source <= {row['name'] for row in baseline['cells']},
                'unexpected native definition was introduced after source GDS load')
        for row in rows:
            if row['name'] in source:
                require(row['children'] == plan['source_children'][row['name']]
                        and all(row[key] == -1 for key in ('paint_type_count', 'label_count', 'selected_instance_count')),
                        'native source hierarchy differs from complete GDS discovery')
        if previous is not None:
            require(names == [row['name'] for row in previous['cells']],
                    'port annotation changed the native definition set')
    for row in rows:
        if row['name'] not in source:
            # This is not a name-based waiver. Only a definition observed before
            # GDS, with no paint types, labels, children or selected instances,
            # can be outside the complete source-GDS set at every phase.
            require(not row['children'] and all(row[key] == 0 for key in
                    ('paint_type_count', 'label_count', 'selected_instance_count')),
                    'non-source native definition contains actual geometry, labels or children')
    return {'phase': value['phase'], 'definition_count': len(rows),
            'source_definition_count': 0 if value['phase'] == 'pre_gds' else len(source),
            'preexisting_empty_definition_count': len(set(names) - source)}


def record_inventory(root, phase, args):
    """Retain raw observations before rejecting any unexpected native input."""
    root = Path(root).resolve()
    require(phase in INVENTORY_PHASES, 'unknown inventory phase')
    remaining, rows = list(args), []
    while remaining:
        require(len(remaining) >= 6, 'truncated native inventory arguments')
        name = remaining.pop(0)
        fields = {}
        for key in ('flags', 'children'):
            require(remaining and re.fullmatch(r'\d+', remaining[0]), 'invalid native inventory field size')
            count = int(remaining.pop(0))
            require(count <= len(remaining), 'truncated native inventory field')
            fields[key], remaining = remaining[:count], remaining[count:]
        require(len(remaining) >= 3 and all(re.fullmatch(r'-?\d+', v) for v in remaining[:3]),
                'invalid native geometry inventory counts')
        counts, remaining = [int(v) for v in remaining[:3]], remaining[3:]
        rows.append({'name': name, **fields, **dict(zip(
            ('paint_type_count', 'label_count', 'selected_instance_count'), counts))})
    value = {'schema': INVENTORY_SCHEMA, 'phase': phase, 'cells': rows}
    write_new(_inventory_path(root, phase), json_bytes(value))
    plan = load(root / FILES['plan'])
    baseline = load(_inventory_path(root, 'pre_gds')) if phase != 'pre_gds' else None
    previous = load(_inventory_path(root, 'post_gds')) if phase == 'post_annotation' else None
    require(baseline is None or (type(baseline) is dict and baseline.get('phase') == 'pre_gds'), 'baseline inventory filename/phase differs')
    require(previous is None or (type(previous) is dict and previous.get('phase') == 'post_gds'), 'previous inventory filename/phase differs')
    validate_inventory(value, plan, baseline, previous)


def comparison_bytes(root, raw, logical_root=None):
    logical = Path(root if logical_root is None else logical_root)
    include = '.include "' + linux_path(logical / FILES['wrappers']) + '"\n'
    return include.encode('utf-8') + raw


def _proof(root, layout=None, profile=None, logical_root=None):
    root = Path(root).resolve()
    # Finalize runs inside Magic, so this log may grow. Recheck its complete
    # retained bytes on every later validation; do not pin an inflight hash.
    # The adapter's retained-file manifest seals the final complete log bytes.
    native_log = root / 'runs/lvs/1-magic-spiceextraction/magic-spiceextraction.log'
    require(NATIVE_ERROR_PATTERN.search(native_log.read_text(encoding='utf-8')) is None,
            'retained native extraction log contains a known unresolved error diagnostic')
    gds = (root / 'input.gds').read_bytes()
    if layout is not None:
        original = next(a for a in layout['checks']['artifacts'] if a['id'] == 'gds')
        require(digest(gds) == original['sha256'] and len(gds) == original['bytes'], 'original GDS source binding changed')
    base = (root / FILES['base_tech']).read_bytes()
    reference_gds, reference_spice = ((root / FILES[key]).read_bytes() for key in ('reference_gds', 'reference_spice'))
    require(digest(base) == BASE_TECH_SHA and digest(reference_gds) == LIBRARY_GDS_SHA and digest(reference_spice) == LIBRARY_SPICE_SHA, 'retained vendor inputs changed')
    require((root / FILES['derived_tech']).read_bytes() == derived_tech(base), 'derived extraction deck changed beyond fixed separate-style insertion')
    top = load(root / 'config.json')['DESIGN_NAME']
    plan = make_plan(gds, reference_gds, reference_spice, top)
    require(load(root / FILES['plan']) == plan and (root / FILES['plan_tcl']).read_bytes() == _plan_tcl(plan), 'extraction discovery/plan changed')
    inventories = {phase: load(_inventory_path(root, phase)) for phase in INVENTORY_PHASES}
    inventory_proof = []
    for phase in INVENTORY_PHASES:
        require(type(inventories[phase]) is dict and inventories[phase].get('phase') == phase, 'native inventory filename/phase differs')
        summary = validate_inventory(inventories[phase], plan,
            inventories['pre_gds'] if phase != 'pre_gds' else None,
            inventories['post_gds'] if phase == 'post_annotation' else None)
        inventory_proof.append({**summary, 'sha256': digest(_inventory_path(root, phase).read_bytes())})
    execution = load(root / FILES['execution_log'])
    require(execution.get('schema') == SCHEMA and execution.get('definition_count') == len(plan['cells'])
            and len(execution.get('cells', [])) == len(plan['cells']), 'incomplete cell-by-cell extraction proof')
    previous, ext_records = 0, []
    directory = root / 'runs/lvs/1-magic-spiceextraction/extraction'
    require({p.stem for p in directory.glob('*.ext')} == {row['name'] for row in plan['cells']}, 'all-and-only discovered cell definitions must be extracted')
    for row, actual in zip(plan['cells'], execution['cells']):
        require({key: actual.get(key) for key in ('name', 'style')} == row
                and actual.get('selected_cell') == row['name']
                and type(actual.get('feedback_before')) is int and actual['feedback_before'] == previous
                and type(actual.get('feedback_after')) is int and actual['feedback_after'] >= previous, 'cell execution/style/feedback record changed')
        previous = actual['feedback_after']
        raw = (directory / (row['name'] + '.ext')).read_bytes()
        text = raw.decode('utf-8')
        require('\nstyle ' + row['style'] + '\n' in text, 'cell extracted under wrong style')
        if row['name'] != CELL:
            require(not any(alias in text for alias in MODELS), 'MOSCAP model leaked into ordinary cell')
        ext_records.append({'cell': row['name'], 'sha256': digest(raw), 'bytes': len(raw), 'style': row['style']})
    require(execution.get('feedback_count') == previous, 'final feedback count changed')
    raw = (root / FILES['raw_spice']).read_bytes()
    require(cap_devices(raw.decode('utf-8'), aliases=True) == plan['qualified_devices'], 'MOSCAP model/pins/exact W/L differ from original vendor devices')
    comparison = (root / FILES['comparison_spice']).read_bytes()
    require(comparison == comparison_bytes(root, raw, logical_root), 'comparison input is not exact include-plus-raw-SPICE transform')
    step_copy = root / 'runs/lvs/1-magic-spiceextraction' / (top + '.spice')
    require(step_copy.read_bytes() == comparison, 'Magic step output and comparison input disagree')
    wrapper = (root / FILES['wrappers']).read_bytes()
    if profile is not None:
        require(digest(wrapper) == profile['terminal_recognition_variant']['wrapper_sha256'], 'MOSCAP wrapper changed')
    return {'schema': SCHEMA, 'status': 'Passed', 'input_gds_sha256': digest(gds),
            'base_tech_sha256': digest(base), 'derived_tech_sha256': digest((root / FILES['derived_tech']).read_bytes()),
            'reference_gds_sha256': digest(reference_gds), 'reference_spice_sha256': digest(reference_spice),
            'wrapper_sha256': digest(wrapper), 'raw_spice_sha256': digest(raw), 'comparison_spice_sha256': digest(comparison),
            'comparison_transform': 'one_explicit_model_include_followed_by_unchanged_raw_ext2spice_bytes',
            'discovery': plan, 'all_definitions_extracted_exactly_once': True,
            'native_source_inventory': inventory_proof,
            'normal_cells_use_original_ngspice_rules': True, 'ordinary_ext_inventory': ext_records,
            'feedback_count_recorded': previous, 'model_device_count': 2,
            'qualified_width_variant_sd_rule_count': 4, 'original_width_bounds_preserved': True,
            'native_known_error_diagnostics_absent': True,
            'source_geometry_unchanged': True, 'original_reference_spice_unchanged': True}


def finalize(root):
    root = Path(root).resolve()
    profile = load(root / 'input-manifest.json')['configuration']['profile']
    raw = (root / FILES['raw_spice']).read_bytes()
    comparison = comparison_bytes(root, raw)
    write_new(root / FILES['comparison_spice'], comparison)
    top = load(root / 'config.json')['DESIGN_NAME']
    write_new(root / 'runs/lvs/1-magic-spiceextraction' / (top + '.spice'), comparison)
    proof = _proof(root, profile=profile)
    write_new(root / FILES['proof'], json_bytes(proof))


def validate_retained_model_proof(root, layout, profile, logical_root=None):
    expected = _proof(root, layout, profile, logical_root)
    require(load(Path(root) / FILES['proof']) == expected, 'saved recognition proof differs from complete pure reconstruction')
    return {'schema': SCHEMA, 'validation_status': 'Passed', 'model_device_count': 2,
            'qualified_width_variant_sd_rule_count': 4, 'original_width_bounds_preserved': True,
            'native_known_error_diagnostics_absent': True,
            'definition_count': expected['discovery']['definition_count'],
            'qualified_instance_uses': expected['discovery']['qualified_instance_uses'],
            'input_gds_sha256': expected['input_gds_sha256'], 'derived_tech_sha256': expected['derived_tech_sha256'],
            'wrapper_sha256': expected['wrapper_sha256'], 'raw_spice_sha256': expected['raw_spice_sha256'],
            'comparison_spice_sha256': expected['comparison_spice_sha256'],
            'proof_sha256': digest((Path(root) / FILES['proof']).read_bytes()),
            'native_source_inventory': expected['native_source_inventory'],
            'all_definitions_extracted_exactly_once': True, 'normal_cells_use_original_ngspice_rules': True}


def main():
    require(len(sys.argv) >= 3 and sys.argv[1] in ('prepare', 'inventory', 'record', 'finalize'), 'use fixed recipe operation and run directory')
    operation, root = sys.argv[1], Path(sys.argv[2])
    if operation == 'prepare':
        prepare(root)
    elif operation == 'inventory':
        require(len(sys.argv) >= 4, 'inventory phase is required')
        record_inventory(root, sys.argv[3], sys.argv[4:])
    elif operation == 'record':
        record_execution(root, sys.argv[3:])
    else:
        finalize(root)


if __name__ == '__main__':
    main()

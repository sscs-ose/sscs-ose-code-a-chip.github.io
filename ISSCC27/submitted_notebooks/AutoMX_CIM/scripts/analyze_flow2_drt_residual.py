#!/usr/bin/env python3
"""Classify detailed-routing residual violations of one native wrapper child.

Reads only native outputs (drt.drc, detailed log, routed DEF, macro LEFs) and
writes a JSON analysis; it never edits the run, summary or hashes.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re

MACROS = ('core_i', 'condition_i', 'adc_i')
ANALOG = re.compile(r'net:(AIN[PN]|H[PN][0-3]|BIAS_MON)$')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def macro_boxes(def_path, lefs):
    sizes = {}
    for lef in lefs:
        for m in re.finditer(r'MACRO (\S+).*?SIZE ([0-9.]+) BY ([0-9.]+)', Path(lef).read_text(), re.S):
            sizes[m[1]] = (float(m[2]), float(m[3]))
    pattern = re.compile(r'^\s*-\s+(' + '|'.join(MACROS) + r')\s+(\S+)\s+\+\s+FIXED\s+\(\s*(\d+)\s+(\d+)\s*\)\s+N\b')
    boxes, dbu = {}, 1000
    with Path(def_path).open(errors='replace') as handle:
        for line in handle:
            if line.startswith('UNITS DISTANCE MICRONS'):
                dbu = int(line.split()[3])
            m = pattern.match(line)
            if m:
                x, y = int(m[3]) / dbu, int(m[4]) / dbu
                w, h = sizes[m[2]]
                boxes[m[1]] = (x, y, x + w, y + h)
                if len(boxes) == len(MACROS):
                    break
    return boxes


def parse_drc(text, boxes):
    items = []
    for m in re.finditer(r'violation type: (.+?)\n\s+srcs: (.*?)\n\s+bbox = \( ([-0-9.]+), ([-0-9.]+) \) - '
                         r'\( ([-0-9.]+), ([-0-9.]+) \) on Layer (\S+)', text):
        x, y = (float(m[3]) + float(m[5])) / 2, (float(m[4]) + float(m[6])) / 2
        near, dist = None, None
        for name, (a, b, c, e) in boxes.items():
            dd = (max(a - x, 0, x - c) ** 2 + max(b - y, 0, y - e) ** 2) ** .5
            if dist is None or dd < dist:
                near, dist = name, dd
        items.append({'type': m[1].strip(), 'srcs': m[2].split(), 'x': x, 'y': y, 'layer': m[7],
                      'nearest_macro': near, 'distance_um': None if dist is None else round(dist, 2)})
    return items


def analyze(run_dir, config):
    run_dir = Path(run_dir)
    drc = run_dir / 'reports/routing/drt.drc'
    log = next(iter(sorted((run_dir / 'logs/routing').glob('*-detailed.log'))))
    boxes = macro_boxes(run_dir / 'results/routing/automx_cim_mixed_signal_proto.def', config['EXTRA_LEFS'])
    items = parse_drc(drc.read_text(), boxes)
    counts = [int(x) for x in re.findall(r'DRT-0199\]\s+Number of violations = (\d+)', log.read_text())]
    return {
        'format': 'automx-drt-residual-analysis-v1',
        'measured': {
            'violations_per_iteration': counts, 'DRT_OPT_ITERS': config.get('DRT_OPT_ITERS'),
            'final_violations': len(items),
            'by_type': dict(collections.Counter(i['type'] for i in items)),
            'by_layer': dict(collections.Counter(i['layer'] for i in items)),
            'involving_power_or_fake_pg': sum(any(s.startswith(('net:frFake', 'net:VPWR', 'net:VGND'))
                                                  for s in i['srcs']) for i in items),
            'involving_analog_nets': sum(any(ANALOG.match(s) for s in i['srcs']) for i in items),
            'within_5um_of_macro': dict(collections.Counter(i['nearest_macro'] for i in items
                                                            if i['distance_um'] is not None and i['distance_um'] <= 5)),
            'top_50um_clusters': [{'x0': k[0], 'y0': k[1], 'count': v} for k, v in collections.Counter(
                (int(i['x'] // 50) * 50, int(i['y'] // 50) * 50) for i in items).most_common(8)]},
        'macro_boxes_um': boxes, 'violations': items,
        'evidence': [{'path': str(p), 'sha256': sha(p)} for p in (drc, log)]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--gds-tag', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--classification', default='UNCLASSIFIED')
    p.add_argument('--reasoning', default='')
    a = p.parse_args()
    design = a.root / 'build/flow2_wrapper_integration' / a.gds_tag / 'design'
    report = analyze(design / 'runs' / a.gds_tag, json.loads((design / 'config.json').read_text()))
    report.update(tag=a.gds_tag, classification=a.classification, reasoning=a.reasoning)
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report['measured'].items() if k != 'violations_per_iteration'}, indent=1))
    print(report['measured']['violations_per_iteration'])


if __name__ == '__main__':
    main()

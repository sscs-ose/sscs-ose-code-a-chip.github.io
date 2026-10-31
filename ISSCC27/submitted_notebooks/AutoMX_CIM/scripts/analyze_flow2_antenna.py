#!/usr/bin/env python3
"""Summarize actual post-route antenna violations and isolated ECO targets."""
from collections import Counter
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common


def analyze(text):
    net = pin = master = layer = ratio = None
    pin_record = -1
    violations = []
    for line in text.splitlines():
        value = line.strip()
        if value.startswith('Net: '):
            net = value[5:]; pin = master = layer = ratio = None
        elif value.startswith('Pin: '):
            pin_record += 1
            match = re.fullmatch(r'Pin: (\S+) \(([^()]+)\)', value)
            if not match:
                raise ValueError('invalid antenna pin')
            pin, master = match.groups(); layer = ratio = None
        elif value.startswith(('Layer: ', 'Via: ')):
            layer = value.split(': ', 1)[1]; ratio = None
        elif 'area ratio:' in value and not value.startswith('Required'):
            ratio = float(value.rsplit(':', 1)[1])
        elif '(VIOLATED)' in value:
            match = re.fullmatch(r'Required ratio:\s*([0-9.eE+-]+) \(([^()]+)\) \(VIOLATED\)', value)
            if not match or None in (net, pin, master, layer, ratio):
                raise ValueError('antenna violation lacks its net/pin/layer/ratio')
            required = float(match[1])
            if required <= 0 or ratio <= required:
                raise ValueError('inconsistent antenna violation ratio')
            violations.append({'net': net, 'pin': pin, 'master': master, 'layer': layer,
                               'rule': match[2], 'actual': ratio, 'required': required,
                               'excess_factor': ratio/required, 'pin_report_record': pin_record})
    nets = re.findall(r'\[INFO ANT-0002\] Found (\d+) net violations\.', text)
    pins = re.findall(r'\[INFO ANT-0001\] Found (\d+) pin violations\.', text)
    completed = any(marker in text for marker in ('AUTOMX_ANTENNA_DONE', 'AUTOMX_PG_ANTENNA_DONE'))
    if not nets or not pins or not completed:
        raise ValueError('completed native antenna report required')
    targets = {(v['net'], v['pin']): {key: v[key] for key in ('net', 'pin', 'master')}
               for v in violations}
    # Native ARC may report the same net/pin in more than one Pin block.
    # Reconcile native pin totals against violating report records; keep the
    # unique physical ECO endpoint inventory separately, without dropping raw.
    records = {v['pin_report_record'] for v in violations}
    if len({v['net'] for v in violations}) != int(nets[-1]) or len(records) != int(pins[-1]):
        raise ValueError('parsed net/pin report records differ from native totals')
    targets = [targets[key] for key in sorted(targets)]
    return {'status': 'ANTENNA_RESIDUALS_CLASSIFIED', 'net_violations': int(nets[-1]),
            'pin_violations': int(pins[-1]), 'violated_rule_instances': len(violations),
            'unique_pin_targets': len(targets), 'violating_pin_report_records': len(records),
            'by_layer': dict(Counter(v['layer'] for v in violations)),
            'by_master_unique_pins': dict(Counter(v['master'] for v in targets)),
            'macro_pin_targets': [v for v in targets if v['pin'].startswith(('core_i/', 'condition_i/', 'adc_i/'))],
            'eco_targets': targets,
            'worst_rules': sorted(violations, key=lambda v: -v['excess_factor'])[:20],
            'action': 'Insert/size antenna protection at actual affected gates in a fresh derived '
                      'ODB, legalize and route incrementally, then remeasure DRC/antenna/timing. '
                      'This target list does not modify geometry or waive checks.'}


def run(root, *, source_tag, output):
    root = Path(root).resolve(); common.tag_ok(source_tag)
    receipt = root/common.BASE/source_tag/'summary.json'
    source = json.loads(receipt.read_text())
    check = source['checks']['antenna']
    log = common._verified(root, check['log'])
    gds = common._verified(root, source['views']['gds'])
    data = analyze(log.read_text())
    data.update(qualification='NOT_QUALIFIED', gds_tag=source['gds_tag'],
                sources=[common._item(root, p) for p in (receipt, log, gds, Path(__file__))])
    common.save_summary(output, data)
    return data


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--source-tag', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    data = run(a.root, source_tag=a.source_tag, output=a.output)
    print(json.dumps({key: data[key] for key in
        ('status', 'net_violations', 'pin_violations', 'by_layer', 'by_master_unique_pins')}, indent=2))

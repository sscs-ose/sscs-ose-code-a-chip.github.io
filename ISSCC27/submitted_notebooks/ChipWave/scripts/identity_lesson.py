"""Exercise the real measurement identity gate on copies of two saved deliveries."""
import argparse
import gzip
import json
import re
import shutil
from pathlib import Path

from run_postroute_workloads import ROOT, digest, source_views


def payload(path):
    if path.is_file():
        return path.read_bytes()
    return gzip.decompress(path.with_name(path.name + '.gz').read_bytes())


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    baseline = ROOT / 'results/benchmark-study/baseline/common/evidence'
    other = ROOT / 'results/benchmark-study/ppa/F2-1/candidates/03/physical/evidence'
    snapshot = json.loads((baseline / 'measurement-source.json').read_text())
    other_snapshot = json.loads((other / 'measurement-source.json').read_text())
    copied = output / 'views'
    copied.mkdir()
    for name in ('selected-delivery.json', 'measurement-source.json'):
        shutil.copy2(baseline / name, copied / name)
    for view in snapshot['views'].values():
        target = copied / view['path']
        if not target.resolve().is_relative_to(copied):
            raise ValueError('Unsafe measurement path')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload(baseline / view['path']))
        assert digest(target) == view['sha256']
    original = source_views(copied)
    outcomes = [dict(case='Original matched delivery', accepted=True)]

    def reject(name, expected):
        try:
            source_views(copied)
        except ValueError as error:
            assert expected in str(error), str(error)
            outcomes.append(dict(case=name, accepted=False, reason=str(error)))
        else:
            raise AssertionError('Mismatched measurement was accepted: ' + name)

    netlist = copied / snapshot['views']['netlist']['path']
    correct = netlist.read_bytes()
    replacement = payload(other / other_snapshot['views']['netlist']['path'])
    assert replacement != correct
    netlist.write_bytes(replacement)
    reject('Netlist from a different physical candidate', 'identity mismatch: netlist')
    netlist.write_bytes(correct)

    sdc = copied / snapshot['views']['sdc']['path']
    correct_sdc = sdc.read_bytes()
    changed, count = re.subn(rb'(-period\s+)[\d.]+', rb'\g<1>20.000', correct_sdc, count=1)
    assert count == 1 and changed != correct_sdc
    sdc.write_bytes(changed)
    reject('Clock changed without a new delivery', 'identity mismatch: sdc')
    sdc.write_bytes(correct_sdc)

    manifest = copied / 'measurement-source.json'
    correct_manifest = manifest.read_bytes()
    changed_manifest = dict(snapshot, source_delivery=other_snapshot['source_delivery'])
    assert changed_manifest['source_delivery'] != snapshot['source_delivery']
    manifest.write_text(json.dumps(changed_manifest))
    reject('Measurement manifest names another delivery', 'belong to another delivery')
    manifest.write_bytes(correct_manifest)
    assert source_views(copied)['hashes'] == original['hashes']
    outcomes.append(dict(case='Original delivery restored', accepted=True))
    result = dict(passed=True, cases=outcomes, period_ps=original['period_ps'],
                  source=str(baseline.relative_to(ROOT)),
                  alternate_source=str(other.relative_to(ROOT)),
                  source_hashes=original['hashes'],
                  guard_sha256=digest(ROOT / 'scripts/run_postroute_workloads.py'),
                  lesson_sha256=digest(Path(__file__)), model_calls=0, physical_calls=0,
                  scope='Real source_views gate on copied saved measurements. '
                        'Deliberate mismatches are teaching interventions, not new designs, '
                        'physical verification or proof against hostile manifest forgery.')
    (output / 'lesson.json').write_text(json.dumps(result, indent=2) + '\n')
    shutil.rmtree(copied)
    print('IDENTITY_LESSON_PASS: matched delivery accepted; three mismatches rejected; restored delivery accepted')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)

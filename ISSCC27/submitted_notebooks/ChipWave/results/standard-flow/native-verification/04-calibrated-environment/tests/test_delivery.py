"""Replay delivery validation with mutations confined to temporary fixtures."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'verification'))
from check_delivery import check_delivery

RESOURCE = Path('.nebula_inputs/authorized-root-project-delivery')
PROJECT = RESOURCE/'delivery/standard-project'
LOCAL_FILES = [
    'spec/source-contract.md', 'spec/acceptance.md', 'spec/draft.specir',
    'spec/contracts.json', 'spec/provenance.json', 'spec/questions.json',
    'integration/design.f', 'integration/dependencies.lock.json',
    'rtl/nebula_npu_dot4.sv', 'rtl/rv32i_five_stage_cpu.sv',
    'rtl/integration/nebula_cpu_npu_top.sv',
    'reports/verification/candidate-view.json', 'reports/verification/fixed-final.json',
]
CASES = [
    ('valid-publication', None, None),
    ('missing-contract', PROJECT/'t09-base-contract.md', 'missing'),
    ('directory-contract', PROJECT/'t09-base-contract.md', 'directory'),
    ('symlink-contract', PROJECT/'t09-base-contract.md', 'symlink'),
    ('truncated-contract', PROJECT/'t09-base-contract.md', 'truncate'),
    ('same-length-tampering', PROJECT/'t09-base-contract.md', 'tamper'),
    ('source-binding-mismatch', Path('spec/source-contract.md'), 'tamper'),
    ('companion-binding-mismatch', Path('spec/acceptance.md'), 'tamper'),
    ('frozen-manifest-binding-mismatch', RESOURCE/'project-delivery.manifest.json', 'tamper'),
    ('manifest-copy-mismatch', PROJECT/'project-delivery.manifest.json', 'tamper'),
    ('prior-dut-binding-mismatch', Path('reports/verification/candidate-view.json'), 'prior-dut'),
    ('published-dut-tampering', PROJECT/'rtl/rv32i_five_stage_cpu.sv', 'tamper'),
]

def run():
    started = time.monotonic()
    records = sorted(ROOT.glob('.nebula_inputs/*/artifact.json'))
    for path in records:
        json.loads(path.read_text())
    protected = records + [ROOT/p for p in LOCAL_FILES]
    protected += [p for p in (ROOT/RESOURCE).rglob('*') if p.is_file()]
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    (ROOT/'build/verify').mkdir(parents=True, exist_ok=True)
    results = []
    for name, relative, mutation in CASES:
        with tempfile.TemporaryDirectory(prefix='delivery-checker-', dir=ROOT/'build/verify') as temporary:
            fixture = Path(temporary)
            for source in records + [ROOT/p for p in LOCAL_FILES] + [ROOT/RESOURCE/'project-delivery.manifest.json', ROOT/RESOURCE/'t09-base-contract.md']:
                target = fixture/source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            shutil.copytree(ROOT/PROJECT, fixture/PROJECT)
            fixed = fixture/RESOURCE/'verification/fixed_common'
            fixed.parent.mkdir(parents=True)
            fixed.symlink_to(ROOT/RESOURCE/'verification/fixed_common', target_is_directory=True)
            if mutation:
                target = fixture/relative
                data = target.read_bytes()
                if mutation in ['missing', 'directory', 'symlink']:
                    target.unlink()
                    if mutation == 'directory': target.mkdir()
                    if mutation == 'symlink': target.symlink_to(fixture/RESOURCE/'t09-base-contract.md')
                elif mutation == 'truncate': target.write_bytes(data[:-1])
                elif mutation == 'tamper': target.write_bytes(bytes([data[0] ^ 1]) + data[1:])
                elif mutation == 'prior-dut':
                    prior = json.loads(data)
                    prior['sources'][0]['sha256'] = '0' * 64
                    target.write_text(json.dumps(prior))
            error = None
            try:
                receipt = check_delivery(fixture)
                assert receipt['verdict'] == 'passed'
            except (AssertionError, FileNotFoundError, IsADirectoryError, ValueError) as exc:
                error = type(exc).__name__
            passed = (error is None) if mutation is None else (error is not None)
            results.append({'id': name, 'verdict': 'passed' if passed else 'failed',
                'expected': 'accepted' if mutation is None else 'rejected',
                'observed': 'accepted' if error is None else 'rejected',
                'exception': error, 'mutated_fixture_path': str(relative) if relative else None})
            print(name + ': ' + results[-1]['verdict'] + ' (' + results[-1]['observed'] + ')')
    after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    assert before == after, 'Read-only input changed during checker regression'
    failed = sum(r['verdict'] == 'failed' for r in results)
    output = {'schema_version': 1, 'verdict': 'failed' if failed else 'passed',
        'scope': 'AC-DELIVERY checker validation only; temporary publication fixtures, no DUT simulation or functional-coverage contribution',
        'total': len(results), 'passed': len(results)-failed, 'failed': failed,
        'cases': results, 'immutable_inputs_unchanged': before == after,
        'protected_file_count': len(before), 'artifact_records_read': len(records),
        'commands': ['python3 -B tests/test_delivery.py'], 'python_version': sys.version,
        'elapsed_seconds': time.monotonic()-started}
    output_path = ROOT/'reports/verification/delivery-checker-tests.json'
    output_path.write_text(json.dumps(output, indent=2)+'\n')
    assert failed == 0, output

if __name__ == '__main__':
    run()

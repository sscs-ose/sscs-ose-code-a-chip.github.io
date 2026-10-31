#!/usr/bin/env python3
"""Package only the used case material; verify every archived file hash."""
import argparse
import gzip
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path
from study_protocol import preregistration

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'ISSCC27/submitted_notebooks/ChipWave/'
TOP = ('README.md','LICENSE','THIRD_PARTY_NOTICES.md','ChipWave.ipynb',
       'ChipWave.html','requirements-notebook.lock.txt','submission-studies.json','QUICKSTART.md')
FOLDERS = ('released_design','generation_seed','scripts','workflows','verification',
           'runtime','toolchain','ip','figures','results','diagnostics','evidence')
SECRET = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|'
                    rb'sk-[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def gzip_info(path):
    h = hashlib.sha256()
    size = 0
    with gzip.open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            size += len(block)
            h.update(block)
    return size, h.hexdigest()


def files():
    chosen = [ROOT/name for name in TOP]
    assert all(p.is_file() for p in chosen)
    for folder in FOLDERS:
        for p in sorted((ROOT/folder).rglob('*')):
            relative = p.relative_to(ROOT)
            if p.is_symlink():
                raise ValueError('Unexpected symlink: '+str(relative))
            if not p.is_file():
                continue
            if any(part in ('.git','__pycache__','obj_dir','obj') or
                   part.startswith('obj-') or part.endswith('.egg-info') for part in relative.parts):
                continue
            if 'build' in relative.parts and folder != 'results':
                continue
            if p.suffix in ('.pyc','.o','.a','.so') or relative == Path('scripts/local_env.sh'):
                continue
            if folder == 'results' and p.name in ('acceptance','sim','npu_compile'):
                continue
            chosen.append(p)
    assert len(chosen) == len(set(chosen))
    assert not any('.codex' in p.parts or p.name in ('auth.json','.env') for p in chosen)
    return chosen


def validate_deliveries(candidates):
    chosen = set(candidates)
    for delivery in (ROOT/'results').rglob('selected-delivery.json'):
        metadata=json.loads(delivery.read_text())
        for item in metadata.get('collected_files',[]):
            path=delivery.parent/item['path']
            if not path.resolve().is_relative_to(delivery.parent.resolve()):
                raise ValueError('Unsafe collected-file path: '+item['path'])
            stored = path if path in chosen else path.with_name(path.name+'.gz')
            assert stored in chosen, 'Selected delivery file would be omitted: '+str(path.relative_to(ROOT))
            actual = (path.stat().st_size, digest(path)) if stored == path else gzip_info(stored)
            assert actual == (item['bytes'], item['sha256']), path


def validate_study():
    extension = ROOT/'results/benchmark-study'
    if extension.exists():
        report = json.loads((extension/'analysis.json').read_text())
        protocol = json.loads((extension/'protocol.json').read_text())
        from replay_benchmark_study import audit_accounting
        audit_accounting(extension,report)
        if not report['ppa_complete'] or not report.get('benchmark', {}).get('qualified'):
            raise ValueError('Benchmark/workflow extension is incomplete; a working draft cannot be packaged as final')
        expected = {job['id'] for job in protocol['ppa_jobs']}
        if {row['job']['id'] for row in report['rows']} != expected or not all(row['terminal'] for row in report['rows']):
            raise ValueError('New workflow schedule is incomplete')
        if not all(row['terminal'] for row in report['demonstrations']):
            raise ValueError('New task demonstrations lack terminal records')
        high = json.loads((extension/'high-frequency/summary.json').read_text())
        if not high['finished']:
            raise ValueError('New high-frequency challenges are incomplete')
        accounting=report['physical_accounting']
        if accounting['allocated']>accounting['limits']['absolute_total']:
            raise ValueError('New physical campaign exceeded its authorized cap')
        if accounting['terminal']!=accounting['allocated']:
            raise ValueError('New physical campaign still has an unterminated accepted attempt')
        exported=json.loads((extension/'export-manifest.json').read_text())
        if not exported['complete']:
            raise ValueError('A development export cannot be packaged as a final submission')
        seen=set()
        for item in exported['files']:
            path=extension/item['path']
            if item['path'] in seen or path.is_symlink() or not path.resolve().is_relative_to(extension):
                raise ValueError('Unsafe or duplicate benchmark evidence path')
            seen.add(item['path'])
            if path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:
                raise ValueError('Benchmark evidence differs from its export: '+item['path'])
    study = ROOT/'results/configurable-study'
    load = lambda name: json.loads((study/name).read_text())
    protocol = load('protocol.json')
    if protocol != json.loads(json.dumps(preregistration())):
        raise ValueError('The candidate does not match the frozen study protocol')
    generation = load('generation/analysis.json')
    ppa = load('ppa/analysis.json')
    if not generation['complete'] or len(generation['rows']) != 12 or {row['job']['id'] for row in generation['rows']} != {
            job['id'] for job in protocol['generation']['jobs']}:
        raise ValueError('The twelve scheduled generation experiments are incomplete')
    if not load('baseline/mhz95-run03/evaluation-v4.json')['rank_eligible']:
        raise ValueError('The normalization baseline is unqualified')
    if not load('tutorial/summary.json')['passed'] or not load('transfer/counter/results/result.json')['passed']:
        raise ValueError('The configuration tutorial or counter transfer is incomplete')
    scheduled = {job['id'] for job in protocol['ppa']['sessions']}
    if not ppa['complete'] or len(ppa['rows']) != 7 or {row['id'] for row in ppa['rows']} != scheduled:
        raise ValueError('The seven scheduled PPA searches are incomplete')
    for row in ppa['rows']:
        if not row['finished'] or row['physical_launches'] > 3 or row['physical_launches']+row['unused_slots'] != 3:
            raise ValueError('Incomplete PPA candidate accounting: '+row['id'])
    for name in ('representatives','high-frequency'):
        report = load(name+'/summary.json')
        selection_key = 'integrations' if name == 'representatives' else 'choices'
        expected = report['selection'][selection_key]
        if not report['finished'] or len(report['rows']) != len(expected):
            raise ValueError('Physical extension incomplete: '+name)
    if not load('export-manifest.json')['complete']:
        raise ValueError('A foundation-only evidence export is not a final candidate')
    notebook = json.loads((ROOT/'ChipWave.ipynb').read_text())
    if notebook['metadata']['chipwave_submission']['stage'] != 'experiments_complete':
        raise ValueError('The notebook is still a working draft')
    code = [cell for cell in notebook['cells'] if cell['cell_type']=='code']
    if not code or any(cell.get('execution_count') is None or any(
            output.get('output_type')=='error' for output in cell.get('outputs',[])) for cell in code):
        raise ValueError('Execute the final notebook successfully before packaging')


def package(output):
    if output.exists():
        raise ValueError('Existing archive preserved; choose a new archive name.')
    from evidence_store import restore, verify
    evidence = verify(ROOT)
    restore(ROOT)
    validate_study()
    from submission_studies import validate
    validate(ROOT)
    for name in ('functional','physical','reproduction'):
        assert json.loads((ROOT/'results'/f'{name}.json').read_text())['passed']
    candidates = files()
    validate_deliveries(candidates)
    # All original deliveries are validated before storing their lossless compact form.
    compacted = {item['path'] for item in evidence['files']}
    candidates = [p for p in candidates if str(p.relative_to(ROOT)) not in compacted]
    records = []
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='chipwave-package-') as temp:
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for original in candidates:
                relative = str(original.relative_to(ROOT))
                size = original.stat().st_size
                if size < 10_000_000:
                    assert not SECRET.search(original.read_bytes()), 'Potential secret in '+relative
                source = original
                entry = dict(path=relative,bytes=size,sha256=digest(original))
                if size > 90_000_000:
                    assert original.suffix == '.lvsdb', 'Review oversized submission file: '+relative
                    source = Path(temp)/'physical-database.gz'
                    with original.open('rb') as src, gzip.open(source,'wb',compresslevel=6) as dest:
                        for block in iter(lambda:src.read(1024*1024),b''):
                            dest.write(block)
                    entry.update(encoding='gzip',decoded_path=relative,decoded_bytes=size,
                                 decoded_sha256=entry['sha256'])
                    entry.update(path=relative+'.gz',bytes=source.stat().st_size,sha256=digest(source))
                elif original.name.endswith('.lvsdb.gz'):
                    decoded_size, decoded_hash = gzip_info(original)
                    entry.update(encoding='gzip', decoded_path=relative[:-3],
                                 decoded_bytes=decoded_size, decoded_sha256=decoded_hash)
                assert entry['bytes'] < 100_000_000
                archive.write(source,PREFIX+entry['path'])
                records.append(entry)
            manifest = dict(format_version=1,scope='case files and complete evidence; large originals restored from evidence/index.json',
                            archive_prefix=PREFIX,files=records,
                            oversized_physical_databases='gzip-compressed; decode to verify the original selected-delivery hashes',
                            evidence_index='evidence/index.json',
                            restore_command='python scripts/evidence_store.py restore')
            data = (json.dumps(manifest,indent=2)+'\n').encode()
            archive.writestr(PREFIX+'release-manifest.json',data)
            (ROOT/'release-manifest.json').write_bytes(data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(records)+1
        for entry in records:
            h = hashlib.sha256()
            with archive.open(PREFIX+entry['path']) as handle:
                for block in iter(lambda:handle.read(1024*1024),b''):
                    h.update(block)
            assert h.hexdigest() == entry['sha256'],entry['path']
    checksum = digest(output)
    output.with_suffix(output.suffix+'.sha256').write_text(checksum+'  '+output.name+'\n')
    print(json.dumps(dict(archive=str(output),files=len(records),bytes=output.stat().st_size,
                         sha256=checksum,archive_crc_and_hashes_verified=True),indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    package(parser.parse_args().output.resolve())

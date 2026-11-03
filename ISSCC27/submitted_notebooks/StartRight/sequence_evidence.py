"""Audit saved reset-sequence data without running SPICE.
SPDX-License-Identifier: Apache-2.0
"""
import hashlib, io, json, re, zipfile
import numpy as np
from reset_sequence import HERE, measure, save
from sequence_circuits import generate_sequence


def normalize_deck(text):
    # Only the environment-dependent absolute model root is normalized.
    return re.sub(r'(?m)^(\.include ")[^"\n]*?(/(?:cells|models)/[^"\n]+")$', r'\1<PDK>\2', text.replace('\r\n', '\n'))


def audit():
    root = HERE/'results/sequence'; spec = json.loads((root/'evidence_manifest.json').read_text()); archive = root/'raw_evidence.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != spec['archive_sha256']:
        raise ValueError('Saved evidence archive hash mismatch')
    rows = []
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in spec['cases']:
            prefix = item['id']+'/'; data = z.read(prefix+'vectors.npz')
            assert hashlib.sha256(data).hexdigest() == item['vector_sha256']
            for name, digest in item['raw_hashes'].items():
                assert hashlib.sha256(z.read(prefix+name)).hexdigest() == digest
            config, scenario = item['configuration'], item['scenario']
            text, points, windows = generate_sequence(config, scenario, item['contract'], item['settings'])
            actual = text.replace('.control\n', '.control\nset numdgt=17\n')
            assert normalize_deck(actual) == normalize_deck(z.read(prefix+'input.cir').decode())
            init = z.read(prefix+'.spiceinit').decode()
            assert 'option '+config.get('solver', 'klu') in init and 'set ngbehavior=hsa' in init
            with np.load(io.BytesIO(data), allow_pickle=False) as vectors:
                result = measure(vectors['cold'], vectors['interface'], config, scenario, item['contract'], points, windows)
            assert result['observed_pass'] == item['reference_observed_pass']
            for field in ['declared_precondition_verified', 'alternate_state_exercised', 'sampled_restoration_observed']:
                assert result[field] == item['measured'][field]
            for field in ['delivered_J', 'returned_J', 'net_J']:
                assert abs(result['source_work'][field]-item['measured']['source_work'][field]) < 1e-18
            rows.append(dict(id=item['id'], group=item['group'], corner=scenario['corner'], configuration=config['id'], result=result))
    unresolved = json.loads((root/'unresolved_manifest.json').read_text())
    limits_archive = root/'unresolved_logs.zip'
    assert hashlib.sha256(limits_archive.read_bytes()).hexdigest() == unresolved['archive_sha256']
    with zipfile.ZipFile(limits_archive) as z:
        assert z.testzip() is None
        for item in unresolved['cases']:
            assert item['status'] == 'unresolved' and item['reason']
            for name, digest in item['files'].items():
                assert hashlib.sha256(z.read(item['case']+'/'+name)).hexdigest() == digest
    record = dict(status='passed', evidence_kind='saved-data audit, no fresh SPICE', cases=rows,
                  unresolved_log_count=len(unresolved['cases']),
                  scope=spec['scope'], encoding=spec['encoding'], raw_archive_sha256=spec['archive_sha256'])
    save(root/'evidence_audit.json', record)
    print('PASS:', len(rows), 'saved complete waveform pairs remeasured; decks and source work checked.', flush=True)
    return record


if __name__ == '__main__': audit()

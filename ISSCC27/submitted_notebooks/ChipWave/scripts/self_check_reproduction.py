"""Reject invalid selected-source replay inputs before creating output."""
import hashlib
import json
import tempfile
from pathlib import Path
from reproduce import reproduce

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    source, output = root / 'source', root / 'output'
    source.mkdir()
    for value in (None, True, -1, float('inf'), float('nan')):
        try:
            reproduce(output, False, source, value)
        except ValueError:
            pass
        else:
            raise AssertionError('Missing or invalid engineering time accepted')
    (source / 'rtl').mkdir()
    (source / 'rtl/dut.sv').write_text('modified source')
    record = source / 'selected-delivery.json'
    record.write_text(json.dumps({'exported_source_sha256': {
        'rtl/dut.sv': hashlib.sha256(b'original source').hexdigest()}}))
    try:
        reproduce(output, False, source, 10)
    except AssertionError:
        pass
    else:
        raise AssertionError('Modified selected RTL accepted')
    record.write_text(json.dumps({'exported_source_sha256': {'../outside.sv': '0' * 64}}))
    try:
        reproduce(output, False, source, 10)
    except ValueError:
        pass
    else:
        raise AssertionError('Escaping source path accepted')
    assert not output.exists(), 'Rejected replay must not create output'
print('SELECTED_SOURCE_SELF_CHECK_PASS: time, integrity, path confinement and no output mutation')

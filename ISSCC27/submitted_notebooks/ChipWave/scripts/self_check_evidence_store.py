"""Roundtrip, deduplication, corruption and unsafe-path checks on local fixtures."""
import json
from pathlib import Path
import tempfile
import evidence_store as store


def rejected(call):
    try:
        call()
    except (ValueError, OSError, EOFError):
        return
    raise AssertionError('Invalid evidence accepted')


with tempfile.TemporaryDirectory() as temp:
    root=Path(temp); (root/'results').mkdir()
    data=(bytes(range(256))*8192)
    for name in ('a.bin','b.bin'):(root/'results'/name).write_bytes(data)
    (root/'results/summary.json').write_text('{}')
    index=store.compact(root)
    assert len(index['files'])==2 and index['unique_chunks']==1
    assert not (root/'results/a.bin').exists()
    store.restore(root)
    assert (root/'results/a.bin').read_bytes()==data
    assert (root/'results/a.bin').stat().st_ino != (root/'results/b.bin').stat().st_ino
    store.restore(root)
    (root/'results/a.bin').write_bytes(b'edited')
    rejected(lambda:store.restore(root)); rejected(lambda:store.compact(root))
    assert (root/'results/a.bin').read_bytes()==b'edited'
    (root/'results/a.bin').write_bytes(data)
    store.compact(root)
    key=index['files'][0]['chunks'][0]; path=root/'evidence/objects'/f'{key}.gz'; saved=path.read_bytes()
    path.write_bytes(b'broken');rejected(lambda:store.verify(root));rejected(lambda:store.restore(root))
    assert not (root/'results/a.bin').exists()
    path.write_bytes(saved)
    manifest=root/'evidence/index.json'; original=manifest.read_text()
    index['files'][0]['path']='results/../../escape'
    manifest.write_text(json.dumps(index));rejected(lambda:store.restore(root));manifest.write_text(original)
    outside=root/'outside';outside.mkdir();(root/'results/link').symlink_to(outside,target_is_directory=True)
    rejected(lambda:store.safe(root,'results/link/data'))
    store.restore(root)
    assert (root/'results/b.bin').read_bytes()==data
print('PASS: independent roundtrip, dedup, idempotence, no overwrite, corrupt archive, traversal and symlink rejection')

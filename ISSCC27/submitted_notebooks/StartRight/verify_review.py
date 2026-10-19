"""Verify an extracted review with Python's standard library only.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import hashlib,json

def verify(root):
    root=Path(root).resolve()
    manifest=json.loads((root/'review_manifest.json').read_text(encoding='utf8'))
    if manifest.get('project')!='StartRight' or not isinstance(manifest.get('files'),dict):
        raise ValueError('Not a StartRight review manifest')
    for name,expected in manifest['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root):raise ValueError('Manifest path leaves the project: '+name)
        data=path.read_bytes()
        if len(data)!=expected['bytes'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:
            raise ValueError('File differs from the packaged review: '+name)
    return dict(status='passed',version=manifest['version'],verified_files=len(manifest['files']),scope='Included-manifest integrity only, not an external signature or circuit validation.')

if __name__=='__main__':
    print(json.dumps(verify(Path(__file__).resolve().parent),indent=2))

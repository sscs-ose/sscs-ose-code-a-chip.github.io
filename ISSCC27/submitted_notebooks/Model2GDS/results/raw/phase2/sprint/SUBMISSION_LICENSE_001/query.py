"""Read pinned PDK licensing and preserve exact attribution sources; no EDA."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

OUT = Path(__file__).resolve().parent
REV = '0fe599b2afb6708d281543108caf8310912f54af'
PDK = Path('/home/huawei/.local/share/model2gds-codex/pdks/volare/sky130/versions') / REV / 'sky130A'


def save(name, content, origin):
    with (OUT / name).open('xb') as stream:
        stream.write(content)
    return {'path': name, 'source': origin, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Model2GDS-license-provenance'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read(), response.status, response.geturl()


node = (PDK / '.config/nodeinfo.json').read_bytes()
metadata = json.loads(node)
assert metadata['commit']['open_pdks'] == REV
scl_revision = metadata['stdcells']['sky130_fd_sc_hd']
sources = [save('installed_nodeinfo.json', node, str(PDK / '.config/nodeinfo.json')),
           save('installed_SOURCES.txt', (PDK / 'SOURCES').read_bytes(), str(PDK / 'SOURCES'))]
projects = [
    ('sky130_fd_sc_hd', 'efabless/skywater-pdk-libs-sky130_fd_sc_hd', scl_revision,
     'cells/and2/sky130_fd_sc_hd__and2_1.v'),
    ('open_pdks', 'RTimothyEdwards/open_pdks', REV, 'sky130/Makefile.in'),
]
observations = []
for label, repository, revision, supporting_path in projects:
    api = f'https://api.github.com/repos/{repository}/contents?ref={revision}'
    raw, status, actual_url = get(api)
    sources.append(save(label + '_root_listing.json', raw, api))
    listing = json.loads(raw)
    legal_names = [item['name'] for item in listing
                   if item['type'] == 'file' and item['name'].upper() in ('LICENSE', 'NOTICE', 'COPYRIGHT', 'AUTHORS')]
    assert 'LICENSE' in legal_names
    observations.append({'project': label, 'repository': repository, 'revision': revision,
                         'root_legal_files': sorted(legal_names), 'root_listing_http_status': status,
                         'root_listing_resolved_url': actual_url})
    for name in legal_names + [supporting_path]:
        url = f'https://raw.githubusercontent.com/{repository}/{revision}/{name}'
        content, status, actual_url = get(url)
        record = save(label + '_' + name.replace('/', '__'), content, url)
        record.update(http_status=status, resolved_url=actual_url)
        sources.append(record)
        if name == 'LICENSE':
            assert b'Apache License' in content and b'Version 2.0, January 2004' in content
result = {'schema_version': 1, 'status': 'PASS', 'queried_at': datetime.now(timezone.utc).isoformat(),
          'pdk': 'sky130A', 'open_pdks_revision': REV, 'scl': 'sky130_fd_sc_hd',
          'scl_revision_from_installed_nodeinfo': scl_revision, 'projects': observations, 'sources': sources,
          'scope': 'Read-only installed PDK metadata and pinned upstream license sources; no EDA or PDK modification.'}
print(json.dumps(result, indent=2, sort_keys=True))

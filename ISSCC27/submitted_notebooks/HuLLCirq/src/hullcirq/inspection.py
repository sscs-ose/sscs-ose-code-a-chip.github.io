"""Read-only views of saved waveforms, managed files and recorded activity.

No filesystem path, tool command, save, review or mutation is accepted here.
"""
import base64
import codecs
import copy
from datetime import datetime, timezone
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat

from .domain import DomainError
from .physical_tools import io_path, read_bytes
from .verification import object_hash

ROOT = Path(__file__).resolve().parents[2]
GROUPS = {'workflow': 'workflow', 'global-workflow': 'global_workflow',
          'physical-workflow': 'physical_workflow', 'drc-workflow': 'drc_workflow',
          'lvs-workflow': 'lvs_workflow', 'postlayout-workflow': 'postlayout_workflow'}
WAVE_STAGES = {'workflow': 'local_netlist_simulation', 'global-workflow': 'global_netlist_simulation',
               'postlayout-workflow': 'post_layout_verification'}
CHANGE_FILE = 'docs/implementation_activity.json'
MAX_TEXT = 2 * 1024 * 1024
MAX_PAGED_TEXT = 64 * 1024 * 1024
TEXT_PAGE_BYTES = 64 * 1024
PREPARED_PROFILE_FILES = {
    'postlayout_runtime.json': 'post_layout_verification',
    'lvs_repair_direct_runtime_v7.json': 'lvs',
    **{f'lvs_repair_runtime_v{version}.json': 'lvs' for version in range(3, 8)},
    'physical_repair_runtime.json': 'layout',
    'physical_repair_runtime_v2.json': 'layout',
    'physical_repair_runtime_v3.json': 'layout',
}


def require(condition, message):
    if not condition: raise DomainError('inspection_unavailable', message, 409)


def scope(server):
    workspace = getattr(server, 'workspace', None)
    require(workspace is not None and workspace.context is not None, 'Open a project and system first.')
    return {k: workspace.identity[k] for k in ('project_id', 'system_id', 'session_id')}


def state(manager):
    with manager.lock: return copy.deepcopy(manager._state)


def selected(server, group, identifier):
    require(group in GROUPS, 'Choose a managed execution group.')
    saved = state(getattr(server, GROUPS[group]))
    matches = [r for r in saved['runs'] if r['id'] == identifier]
    require(len(matches) == 1, 'The selected saved execution does not exist.')
    run = matches[0]
    require(run.get('record_hash') == object_hash({k: v for k, v in run.items() if k != 'record_hash'}),
            'The saved execution checksum changed.')
    return run


def safe_file(value):
    # Validate lexical ancestry before resolving; links must not hide an escape.
    path = Path(os.path.abspath(value)); root = ROOT.resolve()
    require(path.is_relative_to(root) and path != root, 'The file is outside this HuLLCirq checkout.')
    cursor = root
    for part in path.relative_to(root).parts:
        cursor /= part
        info = io_path(cursor).lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                'Linked or redirected files are not inspected.')
    require(stat.S_ISREG(info.st_mode), 'Choose a regular managed file.')
    return path


def verified_artifact(run, item):
    relative = Path(item['relative_path'])
    require(not relative.is_absolute() and '..' not in relative.parts, 'Invalid retained artifact path.')
    path = safe_file(Path(run['checks']['artifacts_directory']) / relative)
    require(item['bytes'] <= 32 * 1024 * 1024, 'The saved waveform exceeds the 32 MiB viewer limit.')
    raw = read_bytes(path)
    require(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'],
            'The saved artifact hash or size changed; it was not displayed.')
    return raw


def waveform(server, group, identifier):
    identity = scope(server); run = selected(server, group, identifier)
    require(group in WAVE_STAGES and run['stage_id'] == WAVE_STAGES[group], 'Choose S06, S10 or S14 simulation evidence.')
    require(run.get('execution_status') not in ('Queued', 'Running'), 'Wait for a terminal saved result.')
    plan = run.get('verification_plan') or {}
    generic = plan.get('kind') == 'generic_cycle_vectors'
    checks = run.get('checks') or {}
    if group == 'workflow': records = (checks.get('cycle_runtime') or {}).get('records', [])
    elif group == 'global-workflow': records = checks.get('actual_output_transfers', []) if generic else []
    else:
        report = next((a for a in checks.get('artifacts', []) if a['id'] == 'functional-report'), None)
        records = json.loads(verified_artifact(run, report)).get('records', []) if report and generic else []
    # Convert values before JSON leaves Python: wide integers must never pass
    # through JavaScript Number and become a different expected/observed value.
    samples = [{'cycle': r['cycle'], 'signal': r['signal'], 'value': str(r['value'])} for r in records]
    vectors = [{**row, 'drive': {k: str(v) for k, v in row['drive'].items()},
                'expect': {k: str(v) for k, v in row['expect'].items()}} for row in plan.get('public_boundary_vectors', [])] if generic else []
    vcd = next((a for a in checks.get('artifacts', []) if a['id'] == 'simulation-waveform'), None)
    require(generic or vcd is not None, 'This historical result retained no supported waveform or per-cycle samples. No execution was started.')
    return {'schema': 'hullcirq-saved-waveform-v1', 'identity': identity, 'run_id': identifier,
            'stage': run['stage_id'], 'source_sha256': object_hash(run), 'record_hash': run['record_hash'],
            'execution_status': run['execution_status'], 'validation_status': run['validation_status'],
            'interface': plan.get('interface') if generic else None,
            'timing': plan.get('stimulus_timing') if generic else None,
            'vectors': vectors, 'samples': samples,
            'vcd': verified_artifact(run, vcd).decode('utf-8', errors='strict') if vcd else None,
            'vcd_sha256': vcd['sha256'] if vcd else None,
            'limits': 'Observed samples establish values only at recorded check times. Stimulus and expected values come from the saved testbench contract. No intermediate output transitions are inferred. S14 VCD is functional, not dynamic SDF timing.'}


def catalog(server):
    identity = scope(server); store = state(server.store)
    entries, events, payloads = [], [], {}
    def add(label, category, location, *, raw=None, physical=None, expected=None, at=None, action=None,
            run_id=None, stage_id=None, node_id=None, source_revision=None, download_url=None):
        identifier = hashlib.sha256((category + '\0' + location + '\0' + str(run_id)).encode()).hexdigest()
        item = {'id': identifier, 'name': label, 'category': category, 'location': location, 'run_id': run_id,
                'stage_id': stage_id, 'node_id': node_id, 'source_revision': source_revision,
                'download_url': download_url,
                'time': at, 'action': action, 'storage': 'Retained file' if physical else 'Stored JSON record',
                'sha256': hashlib.sha256(raw).hexdigest() if raw is not None else expected.get('sha256') if expected else None,
                'bytes': len(raw) if raw is not None else expected.get('bytes') if expected else None}
        entries.append(item); payloads[identifier] = (raw, physical, expected)
        return item
    def rel(path):
        path = Path(os.path.abspath(path))
        return path.relative_to(ROOT.resolve()).as_posix() if path.is_relative_to(ROOT.resolve()) else None
    def encoded(value): return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    project_folder = server.store.state_path.parent
    require(rel(server.store.state_path) is not None, 'This managed-file viewer supports projects stored inside this HuLLCirq checkout.')
    # Only this system's declared stores and source-bound artifacts, not an
    # arbitrary recursive OS explorer or any sibling project's data.
    names = ['state.json', 'generation.json', 'generation_batches.json', 'repair_analysis.json', 'workflow.json', 'global_generation.json', 'global_workflow.json',
             'implementation_specs.json', 'physical_workflow.json', 'drc_workflow.json', 'lvs_workflow.json', 'postlayout_workflow.json']
    paths = [project_folder/name for name in names]
    if project_folder.parent.name == 'systems':
        paths.append(project_folder.parent.parent/'hullcirq.project.json')
    recovery = project_folder/'physical_recovery'
    # Validate the directory before enumerating its immediate declared records.
    if io_path(recovery).is_dir():
        require(rel(recovery) is not None, 'Recovery records must be inside this checkout.')
        safe_file(server.store.state_path)  # Validate all parent directories first.
        require(not io_path(recovery).is_symlink() and not (getattr(io_path(recovery).lstat(), 'st_file_attributes', 0) & 0x400), 'Linked recovery folders are unsupported.')
        paths.extend(recovery/p.name for p in io_path(recovery).glob('*.json'))
    for path in paths:
        if io_path(path).is_file():
            path = safe_file(path); info = io_path(path).stat()
            add(path.name, 'Project stores', rel(path), physical=str(path),
                at=datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat(), action='Observed file modification time; actor is not inferred')
    registry = getattr(server.workspace, 'registry', None)
    if registry is not None:
        from .workspace_server import _postlayout_profile_directory
        directory = _postlayout_profile_directory(registry.root, identity['project_id'], identity['system_id'])
        # Keep the lexical ancestry for safe_file(), even though the shared
        # scope builder resolves paths. A link must not alias another system.
        lexical = Path(os.path.abspath(Path(registry.root)/'runtime_profiles'/directory.name))
        require(lexical == directory, 'The active prepared-profile directory is redirected.')
        for filename, stage_id in PREPARED_PROFILE_FILES.items():
            path = lexical/filename
            if io_path(path).is_file():
                path = safe_file(path); info = io_path(path).stat()
                add(filename, 'Prepared runtime profiles', rel(path), physical=str(path), stage_id=stage_id,
                    at=datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat(),
                    action='Observed prepared-profile file modification time; actor is not inferred')
    snapshots = store.get('snapshots', {})
    previous = None
    for index, (revision, design) in enumerate(snapshots.items()):
        changes = []
        if previous is not None:
            changes = [k for k in sorted(set(previous)|set(design)) if previous.get(k) != design.get(k)]
        add('Saved design '+revision, 'Specifications and expectations', rel(server.store.state_path)+'#snapshots/'+revision,
            raw=encoded(design), action='Initial saved snapshot' if previous is None else 'Changed top-level fields: '+(', '.join(changes) or 'none'))
        if previous is not None:
            diff = ''.join(difflib.unified_diff(encoded(previous).decode().splitlines(True), encoded(design).decode().splitlines(True),
                                                fromfile='Previous saved snapshot', tofile=revision))
            add('Design diff '+revision, 'Design changes', rel(server.store.state_path)+'#diff/'+revision,
                raw=diff.encode(), action='Difference between retained adjacent snapshots; edit actor/time not inferred')
        events.append({'time': store['revision'].get('created_at') if revision == store['revision']['id'] else None,
                       'action': 'Saved design snapshot', 'record_id': revision, 'detail': 'Retained order '+str(index+1)+'; '+(', '.join(changes) or 'initial snapshot'),
                       'location': rel(server.store.state_path)+'#snapshots/'+revision, 'actor': 'Not recorded'})
        previous = design
    manager_stages = {'generation': 'local_rtl_generation', 'global_generation': 'global_rtl_generation',
                      'physical_workflow': 'layout', 'drc_workflow': 'drc', 'lvs_workflow': 'lvs',
                      'postlayout_workflow': 'post_layout_verification', 'implementation_specs': 'node_implementation_specs'}
    managers = [('state', server.store)] + [(name, getattr(server, name)) for name in (*manager_stages, 'workflow', 'global_workflow',
                'generation_batches', 'repair_analysis') if getattr(server, name, None) is not None]
    for name, manager in managers:
        saved = state(manager); filename = name+'.json'; location = rel(project_folder/filename)
        rows = saved.get('jobs', saved.get('runs', saved.get('specs', saved.get('batches', []))))
        if not isinstance(rows, list): rows = []
        for run in rows:
            identifier = run['id']; created = run.get('finished_at') or run.get('created_at')
            stage_id = run.get('stage_id') or run.get('stage') or manager_stages.get(name)
            source = {'at': created, 'run_id': identifier, 'stage_id': stage_id,
                      'node_id': run.get('node_id'), 'source_revision': run.get('revision_id') or run.get('requested_revision_id')}
            if name == 'state':
                add('Input validation · '+identifier, 'Verification records', location+'#'+identifier,
                    raw=encoded(run), action='Saved input validation record', **source)
            events.append({'time': created, 'action': run.get('stage_id', name)+' · '+run.get('execution_status', 'Saved'),
                'record_id': identifier, 'detail': run.get('validation_status', '')+' / '+run.get('review_status', ''),
                'location': location+'#'+identifier, 'actor': 'Recorded application execution'})
            for key in ('rtl', 'global_rtl', 'netlist'):
                if isinstance(run.get(key), str): add(key+' · '+identifier, 'RTL and netlists', location+'#'+identifier+'/'+key,
                    raw=run[key].encode(), action='Saved '+key, **source)
            # These are generated sources stored inside the owning JSON file,
            # not invented physical files. Include jobs before/without checks.
            for key, category in (('raw_content', 'Model responses'), ('raw_reasoning', 'Model responses'),
                                  ('diff', 'Generated changes'), ('instruction', 'Generation inputs')):
                if isinstance(run.get(key), str) and run[key]:
                    add(key+' · '+identifier, category, location+'#'+identifier+'/'+key,
                        raw=run[key].encode(), action='Retained '+key, **source)
            for key, category in (('specification', 'Specifications and expectations'),
                                  ('verification_plan', 'Specifications and expectations'),
                                  ('context', 'Generation inputs'), ('report', 'Verification records'), ('diagnostics', 'Verification records'),
                                  ('events', 'Verification records')):
                if run.get(key):
                    add(key+' · '+identifier, category, location+'#'+identifier+'/'+key,
                        raw=encoded(run[key]), action='Retained '+key, **source)
            if run.get('checks'):
                add('Checks and logs · '+identifier, 'Verification records', location+'#'+identifier+'/checks',
                    raw=encoded(run['checks']), action='Recorded checks, raw logs and commands', **source)
            checks = run.get('checks') or {}; folder = checks.get('artifacts_directory')
            for artifact in checks.get('artifacts', []):
                if folder and isinstance(artifact.get('relative_path'), str):
                    path = Path(folder)/artifact['relative_path']; relative = rel(path)
                    if relative:
                        download = ('/api/artifacts/'+name.replace('_', '-')+'/'+identifier+'/'+artifact['id']
                                    if name in ('physical_workflow', 'drc_workflow', 'lvs_workflow', 'postlayout_workflow') else None)
                        add(artifact['id'], 'EDA files', relative, physical=str(path), expected=artifact,
                            action='Retained output/input artifact', download_url=download, **source)
        for review in saved.get('reviews', []):
            events.append({'time': review.get('created_at'), 'action': 'Review · '+str(review.get('decision')),
                'record_id': review.get('run_id', review.get('job_id')), 'detail': review.get('note', ''),
                'location': location+'#reviews/'+str(review.get('id', '')), 'actor': review.get('provenance') or review.get('actor', 'Not recorded')})
    changes = ROOT/CHANGE_FILE
    if io_path(changes).is_file():
        declared = json.loads(read_bytes(safe_file(changes)))
        for record in declared.get('interventions', []):
            events.append({'time': record['finished_at'], 'action': 'Application implementation · '+record['id'],
                'record_id': record['id'], 'detail': record['description'], 'location': CHANGE_FILE, 'actor': record['actor']})
        for record in declared.get('files', []):
            require(record['path'].startswith(('src/', 'tests/', 'docs/', 'results/')), 'Invalid implementation manifest path.')
            path = safe_file(ROOT/record['path'])
            add(record['path'], 'Application implementation', record['path'], physical=str(path),
                expected={'sha256': record['after_sha256'], 'bytes': record['bytes']}, action='Declared implementation change; inspect diff')
            add('Diff · '+record['path'], 'Application changes', CHANGE_FILE+'#'+record['path'], raw=record['diff'].encode(),
                action='Before/after this implementation task, not an inferred external-editor history')
    events.sort(key=lambda e: e.get('time') or '', reverse=True)
    return {'schema': 'hullcirq-managed-file-catalog-v1', 'identity': identity, 'revision_id': store['revision']['id'],
            'entries': entries, 'events': events,
            'limits': 'Read-only managed project files and recorded actions. A # location is a JSON record, not a separate file. Unknown historical edit times/actors remain unknown. External OS edits are not automatically attributed.'}, payloads


def _utf8_boundary(stream, position, size):
    """Align nominal page boundaries backward to the same UTF-8 code point."""
    if position <= 0 or position >= size:
        return min(max(position, 0), size)
    start = max(0, position-3)
    stream.seek(start); window = stream.read(position-start+1); offset = position-start
    while offset and window[offset] & 0xC0 == 0x80:
        offset -= 1
    return start+offset


def _stream_content(stream, size, result, expected, page, sha256):
    if size > MAX_PAGED_TEXT:
        require(page == 0, 'This file exceeds the 64 MiB paged-preview limit.')
        return {**result, 'kind': 'binary', 'sha256': None, 'verified': False,
                'message': 'This file exceeds the 64 MiB preview limit. Its content and checksum were not read; use its stage download.'}
    count = (size+TEXT_PAGE_BYTES-1)//TEXT_PAGE_BYTES if size > MAX_TEXT else 1
    require(0 <= page < count, 'Choose a page within this saved file.')
    digest = hashlib.sha256(); decoder = codecs.getincrementaldecoder('utf-8')('strict')
    valid_text = True; has_nul = False; read_size = 0
    while chunk := stream.read(1024*1024):
        digest.update(chunk); read_size += len(chunk); has_nul |= b'\x00' in chunk
        require(read_size <= MAX_PAGED_TEXT, 'The file grew beyond the 64 MiB preview limit while being read.')
        if valid_text:
            try: decoder.decode(chunk, final=False)
            except UnicodeError: valid_text = False
    if valid_text:
        try: decoder.decode(b'', final=True)
        except UnicodeError: valid_text = False
    require(read_size == size, 'The file changed while it was being read; select it again.')
    checksum = digest.hexdigest()
    if expected:
        require(size == expected['bytes'] and checksum == expected['sha256'], 'The retained file no longer matches its saved hash/size.')
    require(sha256 is None or sha256 == checksum, 'The file changed between pages. Select it again to open the new saved version.')
    result = {**result, 'sha256': checksum, 'verified': True}
    if size <= MAX_TEXT:
        stream.seek(0); raw = stream.read()
        if raw.startswith(b'\x89PNG\r\n\x1a\n'):
            return {**result, 'kind': 'image', 'mime_type': 'image/png', 'data_base64': base64.b64encode(raw).decode('ascii')}
    if not valid_text or has_nul:
        return {**result, 'kind': 'binary', 'message': 'This binary format has no inline preview. Its saved bytes and checksum were verified; use Download saved file or its stage download.'}
    if size <= MAX_TEXT:
        return {**result, 'kind': 'text', 'text': raw.decode('utf-8')}
    start = _utf8_boundary(stream, page*TEXT_PAGE_BYTES, size)
    end = _utf8_boundary(stream, (page+1)*TEXT_PAGE_BYTES, size)
    stream.seek(start); text = stream.read(end-start).decode('utf-8', errors='strict')
    return {**result, 'kind': 'text', 'text': text,
            'pagination': {'page': page, 'page_count': count, 'start_byte': start, 'end_byte': end,
                           'total_bytes': size, 'nominal_page_bytes': TEXT_PAGE_BYTES}}


def file_content(server, identifier, *, page=0, sha256=None):
    require(type(page) is int and page >= 0, 'Page must be a non-negative integer.')
    require(sha256 is None or type(sha256) is str and re.fullmatch(r'[0-9a-f]{64}', sha256), 'Retain the whole-file SHA-256 when changing pages.')
    require(page == 0 or sha256 is not None, 'Open the first page before requesting a later page.')
    index, payloads = catalog(server)
    require(identifier in payloads, 'Choose a file from the active system catalog.')
    entry = next(e for e in index['entries'] if e['id'] == identifier)
    raw, physical, expected = payloads[identifier]
    result = {'identity': index['identity'], 'revision_id': index['revision_id'], 'entry': entry}
    if physical:
        path = safe_file(physical)
        signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        with io_path(path).open('rb') as stream:
            before = os.fstat(stream.fileno())
            preview = _stream_content(stream, before.st_size, {**result, 'bytes': before.st_size}, expected, page, sha256)
            safe_file(path)
            require(signature(os.fstat(stream.fileno())) == signature(before) == signature(io_path(path).stat()),
                    'The file changed while it was being read; select it again.')
            return preview
    require(raw is not None, 'This saved record has no retained content.')
    return _stream_content(io.BytesIO(raw), len(raw), {**result, 'bytes': len(raw)}, None, page, sha256)

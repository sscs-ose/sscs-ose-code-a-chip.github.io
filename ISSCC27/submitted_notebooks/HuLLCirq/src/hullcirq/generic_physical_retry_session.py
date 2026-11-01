"""Append-only GUI preparation for repeated generic electrical correction.

Every preparation validates the previous immutable bundle and complete native
failure. Preparation launches nothing. Actual S11 and downstream checks remain
separate user actions. Historical v1/NPU sessions retain their original meaning.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

from . import physical_repair_generic as generic
from . import physical_repair_generic_v2 as recipe
from .domain import DomainError
from .store import strict_loads, utc_now
from .verification import object_hash

SCHEMA = 'hullcirq-gui-generic-physical-retry-session-v2'
PREFIX = 'generic_physical_retry_'
MAX_ATTEMPTS = 256


def require(condition, message):
    if not condition:
        raise DomainError('generic_physical_retry_ineligible', message, 409)


def _paths(directory):
    paths = sorted(Path(directory).glob(PREFIX + '*'))
    require(len(paths) <= MAX_ATTEMPTS, 'Inspect the bounded correction history before further attempts.')
    require(all(path.name == f'{PREFIX}{index:06d}.json' and path.is_file()
                and not path.is_symlink() and not path.is_junction()
                for index, path in enumerate(paths, 1)),
            'Keep the complete contiguous immutable generic correction history; no linked or unknown bundle names.')
    return paths


def _publish(path, bundle):
    """Publish complete bytes exclusively; never replace an existing attempt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.generic-retry-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(bundle, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
            handle.flush(); os.fsync(handle.fileno())
        try:
            if os.name == 'nt':
                # Windows rename is atomic and refuses an existing destination.
                # It does not need hard-link permission in restricted accounts.
                os.rename(temporary, path)
            else:
                os.link(temporary, path)
        except FileExistsError:
            raise DomainError('generic_physical_retry_exists',
                'Another correction bundle already occupies this attempt. Its bytes were preserved; refresh saved status.', 409) from None
    finally:
        Path(temporary).unlink(missing_ok=True)


def _record(store, stage, identifier, revision_id, previous, cache):
    from . import physical_repair_session as legacy
    from .physical_workflow import validate_failed_physical_proof
    from .physical_tools import validate_failed_layout_result
    from .presentation_revision import same_source_design
    same_source_design(store, revision_id)
    if stage == 'post_layout_verification':
        failed, records = legacy._failure(store, identifier, revision_id, cache)
        layout = records['layout']
    else:
        require(stage == 'layout', 'Select a complete failed S11 or S14 execution.')
        state = legacy._saved(store, 'physical_workflow', cache)
        rows = [run for run in state['runs'] if run.get('id') == identifier]
        require(len(rows) == 1, 'The complete failed layout must remain saved.')
        failed = layout = rows[0]
        legacy._checksum(failed)
        result = failed.get('checks', {})
        required = ('source_identity', 'configuration', 'routing', 'timing', 'electrical')
        require(failed.get('revision_id') == revision_id and failed.get('stage_id') == 'layout'
                and failed.get('execution_status') == 'Completed' and failed.get('validation_status') == 'Failed'
                and failed.get('review_status') != 'Accepted' and failed.get('error') is None
                and failed.get('evidence_kind') == 'trusted_fixed_tool_execution'
                and failed.get('software_qa_fixture') is not True
                and result.get('origin') == 'trusted_fixed_tool_adapter'
                and result.get('status') == 'Completed' and result.get('validation_status') == 'Failed'
                and result.get('software_qa_fixture') is not True
                and result.get('technology_mapping_executed') is True
                and result.get('upstream_technology_mapping_reused') is False
                and type(result.get('checks')) is dict and set(result['checks']) == set(required)
                and all(type(result['checks'][name]) is dict
                        and result['checks'][name].get('validation_status') == ('Failed' if name == 'electrical' else 'Passed')
                        for name in required)
                and type(result.get('commands')) is list and len(result['commands']) == 2
                and object_hash(failed.get('diagnostics')) == object_hash(result.get('diagnostics')),
                'Only a complete actual fresh-mapping S11 electrical-only failure is eligible; no failed launch or waived check.')
        validate_failed_physical_proof(failed, validate_failed_layout_result)
    require(generic.is_generic(layout.get('runtime_configuration'))
            and object_hash(layout['runtime_configuration']) == object_hash(previous[2]),
            'The failed execution must use the exact previously prepared generic runtime.')
    return failed, layout


def _derive(layout, failed, previous, base, raw_sha, attempt, directory):
    from .physical_tools import ROOT
    from .drc_tools import configuration_projection as drc_projection
    from .lvs_tools import configuration_projection as lvs_projection
    previous_runtime = previous[2]
    last_density = previous_runtime.get('generic_retry_source_binding', {}).get('core_utilization',
                    previous_runtime['profile']['config']['FP_CORE_UTIL'])
    density = max(10, last_density - 5)
    scope = hashlib.sha256(str(Path(directory).resolve()).encode('utf-8')).hexdigest()[:16]
    root = ROOT / '.work' / 'generic_retry_v2' / scope / f'{attempt:06d}'
    # Every ancestor is checked before any future mkdir/execution can traverse it.
    for path in (root, *root.parents):
        require(not path.is_symlink() and not path.is_junction(), 'Managed correction roots cannot traverse links.')
        if path == ROOT:
            break
    physical = recipe.prepare_configuration(layout, failed, root / 'p', attempt=attempt,
        previous_bundle_sha256=raw_sha, core_utilization=density)
    derived = {'physical': physical}
    for name, index in (('drc', 3), ('lvs', 4)):
        value = copy.deepcopy(base[index])
        require(type(value) is dict, 'Retain the original server DRC/LVS configuration.')
        value.update(physical_runtime=copy.deepcopy(physical), working_directory=str(root / name[0]))
        derived[name] = value
    preview = copy.deepcopy(layout)
    preview['runtime_configuration'] = physical
    drc_projection(preview, derived['drc'])
    lvs_projection({'layout_snapshot': preview, 'layout_record_sha256': object_hash(preview)}, preview, derived['lvs'])
    return derived


def _status(bundle):
    binding = bundle['configurations']['physical']['generic_retry_source_binding']
    return {'configured': True, 'bundle_present': True, 'error': None, 'session_schema': SCHEMA,
        'profile_version': recipe.PROFILE, 'repair_generation': binding['attempt'] + 1,
        'retry_attempt': binding['attempt'], 'core_utilization': binding['core_utilization'],
        'implementation_kind': recipe.IMPLEMENTATION_KIND, 'technology_mapping_reused': False,
        'source_identity': copy.deepcopy(binding)}


def _read_chain(store, base, directory, project_id, system_id, prior, legacy_status):
    from . import physical_repair_session as legacy
    paths = _paths(directory)
    if not paths:
        return prior, legacy_status, None
    require(legacy_status.get('configured') and legacy_status.get('session_schema') == legacy.GENERIC_SCHEMA,
            'Repeated generic correction requires its intact original generic preparation, not an NPU retry.')
    cache = legacy._RestorationReads()
    previous_raw = cache.bytes(legacy._bundle_path(directory))
    first = legacy._validate_bundle(strict_loads(previous_raw.decode('utf-8')), store, base,
                                    project_id, system_id, cache)
    require(all(object_hash(first[name]) == object_hash(prior[index])
                for name, index in (('physical', 2), ('drc', 3), ('lvs', 4))),
            'The original generic bundle changed between restoration phases.')
    result = tuple(copy.deepcopy(prior))
    last = None
    for index, path in enumerate(paths, 1):
        raw = cache.bytes(path)
        bundle = strict_loads(raw.decode('utf-8'))
        legacy._checksum(bundle)
        require(set(bundle) == {'schema', 'project_id', 'system_id', 'revision_id', 'base_configuration_sha256',
                'previous_bundle_sha256', 'source_identity', 'configurations', 'actor', 'created_at', 'record_hash'}
                and bundle.get('schema') == SCHEMA and bundle.get('project_id') == project_id
                and bundle.get('system_id') == system_id and bundle.get('actor') == 'explicit_GUI_action'
                and type(bundle.get('created_at')) is str
                and bundle.get('base_configuration_sha256') == legacy._base_hashes(base)
                and bundle.get('previous_bundle_sha256') == hashlib.sha256(previous_raw).hexdigest(),
                'The repeated correction bundle must retain its exact immutable predecessor, host and project.')
        binding = bundle.get('source_identity', {})
        require(type(binding) is dict and binding.get('attempt') == index,
                'Do not skip or renumber correction attempts.')
        failed, layout = _record(store, binding.get('failed_stage'), binding.get('failed_run_id'),
                                 bundle['revision_id'], result, cache)
        derived = _derive(layout, failed, result, base, bundle['previous_bundle_sha256'], index, directory)
        require(object_hash(bundle.get('configurations')) == object_hash(derived)
                and binding == derived['physical']['generic_retry_source_binding'],
                'Reconstruct the exact failed-source runtime; rehashed edits cannot replace its recipe or density.')
        result = list(result)
        for name, slot in (('physical', 2), ('drc', 3), ('lvs', 4)):
            result[slot] = copy.deepcopy(derived[name])
        result = tuple(result)
        previous_raw, last = raw, bundle
    require(_paths(directory) == paths, 'Correction history changed during restoration.')
    cache.verify()
    return result, _status(last), previous_raw


def restore(store, base, directory, project_id, system_id, prior, status):
    try:
        restored, new_status, _ = _read_chain(store, base, directory, project_id, system_id, prior, status)
        return restored, new_status
    except (DomainError, OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
        return tuple(copy.deepcopy(base)), {'configured': False, 'bundle_present': True,
            'error': {'code': getattr(error, 'code', 'generic_physical_retry_unavailable'),
                      'message': getattr(error, 'message', 'The repeated correction history is invalid; all bytes were preserved.')}}


def prepare(server, identifier, revision_id, stage):
    from . import physical_repair_session as legacy
    from .workspace_server import _postlayout_profile_directory
    require(type(identifier) is str and type(revision_id) is str, 'Provide the exact failed-run and current revision IDs.')
    with server.execution_lock:
        workspace = getattr(server, 'workspace', None)
        require(workspace is not None and workspace.context is not None and not workspace.identity['read_only'],
                'Open the editable original system before preparing another correction.')
        for name in legacy.MANAGERS:
            manager = getattr(server, name, None)
            require(manager is not None and not getattr(manager, '_storage_error', None)
                    and not (getattr(manager, '_worker', None) and manager._worker.is_alive())
                    and not (hasattr(manager, 'is_active') and manager.is_active()),
                    'Finish all active work and resolve process cleanup before correction preparation.')
        manager = server.physical_workflow if stage == 'layout' else server.postlayout_workflow
        with manager._source_locks(), manager.lock:
            manager.observe_design()
            runs = manager._state['runs']
            require(runs and runs[-1]['id'] == identifier and manager._decorate(runs[-1])['freshness'] == 'Current'
                    and server.store.envelope()['revision']['id'] == revision_id,
                    'Select the latest current complete failure and saved design, not historical evidence.')
            identity = workspace.identity
            base = workspace.configurations
            directory = _postlayout_profile_directory(workspace.registry.root, identity['project_id'], identity['system_id'])
            initial, status = legacy._load_legacy_repair_configurations(server.store, base, directory,
                                                       identity['project_id'], identity['system_id'])
            previous, restored_status, last_raw = _read_chain(server.store, base, directory,
                                                       identity['project_id'], identity['system_id'], initial, status)
            require(restored_status.get('configured') and generic.is_generic(previous[2])
                    and object_hash(server.physical_workflow.tool_configuration) == object_hash(previous[2]),
                    'Restore the exact previous prepared generic profile before correction.')
            attempt = restored_status.get('retry_attempt', 0) + 1
            require(attempt <= MAX_ATTEMPTS, 'The bounded correction history is full; inspect results before more attempts.')
            cache = legacy._RestorationReads()
            if last_raw is None:
                last_raw = cache.bytes(legacy._bundle_path(directory))
            failed, layout = _record(server.store, stage, identifier, runs[-1]['revision_id'], previous, cache)
            require(object_hash(runs[-1]) == object_hash(failed), 'Refresh the unchanged complete durable failed execution.')
            if stage == 'post_layout_verification':
                _, _, adopted, _ = manager._adopted_sources_locked()
                require(all(object_hash(adopted[name]) == object_hash(failed[name + '_snapshot'])
                            for name in ('layout', 'drc', 'lvs')), 'Keep the exact current adopted physical source chain.')
                manager._validate_sources(adopted['lvs'], adopted['drc'], adopted['layout'])
            derived = _derive(layout, failed, previous, base, hashlib.sha256(last_raw).hexdigest(), attempt, directory)
            path = Path(directory) / f'{PREFIX}{attempt:06d}.json'
            require(not path.exists() and not path.is_symlink() and not path.is_junction(),
                    'Never overwrite an existing correction bundle; refresh the saved outcome.')
            bundle = {'schema': SCHEMA, 'project_id': identity['project_id'], 'system_id': identity['system_id'],
                'revision_id': failed['revision_id'], 'base_configuration_sha256': legacy._base_hashes(base),
                'previous_bundle_sha256': hashlib.sha256(last_raw).hexdigest(),
                'source_identity': copy.deepcopy(derived['physical']['generic_retry_source_binding']),
                'configurations': derived, 'actor': 'explicit_GUI_action', 'created_at': utc_now()}
            bundle['record_hash'] = object_hash(bundle)
            cache.verify()
            _publish(path, bundle)
            new_status = _status(bundle)
            workspace.context.physical_repair_session = copy.deepcopy(new_status)
            server.physical_repair_session = copy.deepcopy(new_status)
            for name in ('physical', 'drc', 'lvs'):
                getattr(server, name + '_workflow').tool_configuration = copy.deepcopy(derived[name])
        for name in ('physical_workflow', 'drc_workflow', 'lvs_workflow', 'postlayout_workflow'):
            getattr(server, name).observe_design()
        return copy.deepcopy(new_status)

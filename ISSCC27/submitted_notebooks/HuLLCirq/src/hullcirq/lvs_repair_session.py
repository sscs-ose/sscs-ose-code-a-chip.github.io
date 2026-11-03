"""Explicit host-local preparation of a versioned terminal-safe S13 recipe.

Preparation and restoration inspect saved actual proof; neither starts EDA nor
changes an existing run, physical design, expectation, or adoption policy.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re

from .domain import DomainError
from .physical_repair_session import _RestorationReads, _write, MANAGERS
from .presentation_revision import same_source_design
from .store import strict_loads, utc_now
from .verification import object_hash

SCHEMA = 'hullcirq-gui-lvs-terminal-repair-session-v1'
BUNDLE_NAME = 'lvs_repair_runtime_v3.json'
PROFILE = 'hullcirq-sky130-lvs-v3'
ROOT = Path(__file__).resolve().parents[2]
BINDING_SCHEMA = 'hullcirq-lvs-terminal-repair-source-v1'
UPGRADE_SCHEMA = 'hullcirq-gui-lvs-terminal-repair-session-v2'
UPGRADE_BINDING_SCHEMA = 'hullcirq-lvs-terminal-repair-upgrade-v1'
UPGRADE_PROFILE = 'hullcirq-sky130-lvs-v4'
UPGRADE_BUNDLE_NAME = 'lvs_repair_runtime_v4.json'
V5_PROFILE = 'hullcirq-sky130-lvs-v5'
V6_PROFILE = 'hullcirq-sky130-lvs-v6'
V7_PROFILE = 'hullcirq-sky130-lvs-v7'
DIRECT_SCHEMA = 'hullcirq-gui-lvs-terminal-repair-direct-v7'
DIRECT_PENDING_SCHEMA = 'hullcirq-gui-lvs-terminal-repair-direct-v7-unreviewed-v1'
DIRECT_BUNDLE_NAME = 'lvs_repair_direct_runtime_v7.json'
# Fixed known recipes only. Descriptors preserve every saved v4 field/value;
# adding a later recipe does not reinterpret its immutable ancestors.
UPGRADES = {
    UPGRADE_PROFILE: {'previous': PROFILE, 'schema': UPGRADE_SCHEMA, 'bundle': UPGRADE_BUNDLE_NAME,
                      'profile_file': 'lvs_profile_sky130_v4.json', 'work': 'lv4', 'mode': 'upgrade_v4'},
    V5_PROFILE: {'previous': UPGRADE_PROFILE, 'schema': 'hullcirq-gui-lvs-terminal-repair-session-v3',
                 'bundle': 'lvs_repair_runtime_v5.json', 'profile_file': 'lvs_profile_sky130_v5.json',
                 'work': 'lv5', 'mode': 'upgrade_v5'},
    V6_PROFILE: {'previous': V5_PROFILE, 'schema': 'hullcirq-gui-lvs-terminal-repair-session-v4',
                 'bundle': 'lvs_repair_runtime_v6.json', 'profile_file': 'lvs_profile_sky130_v6.json',
                 'work': 'lv6', 'mode': 'upgrade_v6'},
    V7_PROFILE: {'previous': V6_PROFILE, 'schema': 'hullcirq-gui-lvs-terminal-repair-session-v5',
                 'bundle': 'lvs_repair_runtime_v7.json', 'profile_file': 'lvs_profile_sky130_v7.json',
                 'work': 'lv7', 'mode': 'upgrade_v7'},
}


def require(condition, code, message):
    if not condition:
        raise DomainError(code, message, 409)


def _checksum(record):
    require(type(record) is dict and record.get('record_hash') == object_hash(
        {key: value for key, value in record.items() if key != 'record_hash'}),
        'lvs_repair_record_changed', 'The original durable source checksums changed; saved bytes were preserved.')


def _execution_hash(record):
    return object_hash({key: value for key, value in record.items()
                        if key not in ('record_hash', 'review_status', 'acceptance_epoch')})


def _warnings(lvs):
    feedback = lvs['checks'].get('summary', {}).get('extraction', {}).get('feedback')
    require(type(feedback) is list and len(feedback) == 2, 'lvs_repair_warning_scope',
            'Select the complete original two missing-device-terminal supply warnings.')
    supplies = []
    for item in feedback:
        match = re.fullmatch(r'device missing 1 terminal;\s*connecting remainder to node (VGND|VPWR)',
                            item.get('description', '').strip()) if type(item) is dict else None
        require(match is not None, 'lvs_repair_warning_scope',
                'This version corrects only the retained missing-device-terminal supply feedback, not arbitrary extraction errors.')
        supplies.append(match[1])
    require(sorted(supplies) == ['VGND', 'VPWR'], 'lvs_repair_warning_scope', 'Retain both original supply-terminal warning records.')


def _path(directory):
    directory = Path(directory).absolute()
    require(not directory.is_symlink() and not directory.is_junction()
            and directory.resolve().parent.name == 'runtime_profiles',
            'lvs_repair_path', 'Use the compact host-managed system profile directory.')
    path = directory / BUNDLE_NAME
    require(not path.is_symlink() and not path.is_junction(), 'lvs_repair_path', 'The saved LVS profile cannot be a link.')
    return path


def _saved(store, name, cache):
    state = cache.saved(store.state_path.parent / (name+'.json'))
    require(type(state) is dict and type(state.get('runs')) is list and type(state.get('reviews')) is list,
            'lvs_repair_history', 'Retain the complete original physical verification histories.')
    return state


def _source(store, layout_id, drc_id, source_lvs_id, source_revision_id, cache, *, allow_pending_lvs=False):
    from .physical_workflow import validate_physical_proof
    from .physical_tools import validate_layout_result
    from .drc_workflow import validate_drc_proof
    from .drc_tools import validate_drc_result
    from .lvs_workflow import validate_lvs_proof, validate_source_snapshot
    from .lvs_tools import validate_lvs_result
    states = {name: _saved(store, name+'_workflow', cache) for name in ('physical', 'drc', 'lvs')}
    records = {}
    for name, identifier in (('physical', layout_id), ('drc', drc_id), ('lvs', source_lvs_id)):
        matches = [record for record in states[name]['runs'] if record.get('id') == identifier]
        require(len(matches) == 1, 'lvs_repair_source_missing', 'Retain the exact original S11/S12/S13 source records.')
        record = matches[0]; _checksum(record)
        pending = allow_pending_lvs and name == 'lvs' and record.get('review_status') == 'Awaiting Review'
        require(record.get('execution_status') == 'Completed' and record.get('validation_status') == 'Passed'
                and (record.get('review_status') == 'Accepted' or pending) and not record.get('error')
                and record.get('checks', {}).get('cleanup_unresolved') is not True
                and record.get('checks', {}).get('software_qa_fixture') is not True,
                'lvs_repair_ineligible', 'Prepare only from complete actual adopted evidence with resolved cleanup.')
        reviews = [review for review in states[name]['reviews'] if review.get('run_id') == identifier]
        require((pending and not reviews) or (not pending and reviews and reviews[-1].get('decision') == 'accepted'
                and reviews[-1].get('source_key') == record.get('source_key')
                and reviews[-1].get('acceptance_epoch') == record.get('acceptance_epoch')), 'lvs_repair_adoption',
                'The original authoritative source adoptions must remain accepted.')
        records[name] = record
    layout, drc, lvs = (records[name] for name in ('physical', 'drc', 'lvs'))
    require(lvs.get('evidence_kind') == 'trusted_fixed_lvs_execution'
            and drc.get('evidence_kind') == 'trusted_fixed_drc_execution'
            and layout.get('evidence_kind') in ('trusted_fixed_tool_execution', 'trusted_saved_tool_revalidation')
            and all(record['revision_id'] == source_revision_id for record in records.values())
            and object_hash(lvs.get('layout_snapshot')) == object_hash(drc.get('layout_snapshot')) == object_hash(layout)
            and object_hash(lvs.get('drc_snapshot')) == object_hash(drc),
            'lvs_repair_source_changed', 'The exact actual adopted S11/S12/S13 chain must remain saved.')
    same_source_design(store, source_revision_id)
    validate_physical_proof(layout, validate_layout_result)
    validate_drc_proof(drc, validate_drc_result)
    validate_source_snapshot(lvs); validate_lvs_proof(lvs, validate_lvs_result)
    _warnings(lvs)
    return records


def _identity(records):
    layout, drc, lvs = (records[name] for name in ('physical', 'drc', 'lvs'))
    return {'schema': BINDING_SCHEMA, 'historical_lvs_run_id': lvs['id'],
            'historical_lvs_record_sha256': object_hash(lvs), 'historical_lvs_execution_sha256': _execution_hash(lvs),
            'layout_run_id': layout['id'], 'layout_record_sha256': object_hash(layout),
            'drc_run_id': drc['id'], 'drc_record_sha256': object_hash(drc),
            'source_inputs_sha256': object_hash(lvs['source_inputs'])}


def _build(records, base_configuration, directory):
    from .lvs_tools import configuration_projection
    layout, drc, lvs = (records[name] for name in ('physical', 'drc', 'lvs'))
    require(type(base_configuration) is dict
            and object_hash(base_configuration) == object_hash(lvs['runtime_configuration'])
            and object_hash(base_configuration.get('physical_runtime')) == object_hash(layout['runtime_configuration']),
            'lvs_repair_base_changed', 'Keep the exact source LVS runtime after restoration of physical correction profiles.')
    profile_path = ROOT / 'configs/lvs_profile_sky130_v3.json'
    require(profile_path.is_file(), 'lvs_repair_recipe_unavailable', 'The fixed terminal-safe LVS recipe has not been prepared on this host.')
    profile = strict_loads(profile_path.read_text(encoding='utf-8'))
    require(profile.get('profile_version') == PROFILE, 'lvs_repair_recipe_unavailable', 'Use the separate versioned terminal-safe extraction profile.')
    work = Path(directory) / 'lv3'
    require(not work.is_symlink() and not work.is_junction() and work.resolve().parent == Path(directory).resolve(),
            'lvs_repair_path', 'Keep new LVS outputs within the host-managed system scope.')
    result = copy.deepcopy(base_configuration)
    result.update(profile=profile, working_directory=str(work), repair_source_binding=_identity(records))
    configuration_projection(drc, layout, result)
    return result


def _validate(bundle, store, base_configuration, directory, project_id, system_id, cache):
    _checksum(bundle)
    require(set(bundle) == {'schema', 'project_id', 'system_id', 'source_revision_id', 'base_configuration_sha256',
                            'source_identity', 'configuration', 'actor', 'created_at', 'record_hash'}
            and bundle.get('schema') == SCHEMA and bundle.get('project_id') == project_id
            and bundle.get('system_id') == system_id and bundle.get('actor') == 'explicit_GUI_action'
            and type(bundle.get('created_at')) is str
            and bundle.get('base_configuration_sha256') == object_hash(base_configuration),
            'lvs_repair_profile_incompatible', 'The saved LVS correction differs from this exact host runtime or system; its bytes were preserved.')
    identity = bundle['source_identity']
    records = _source(store, identity['layout_run_id'], identity['drc_run_id'], identity['historical_lvs_run_id'],
                      bundle['source_revision_id'], cache)
    require(identity == _identity(records), 'lvs_repair_profile_incompatible', 'The original extraction source changed after preparation.')
    derived = _build(records, base_configuration, directory)
    require(object_hash(bundle['configuration']) == object_hash(derived), 'lvs_repair_profile_incompatible',
            'A recomputed checksum cannot authorize a changed extraction recipe or output directory.')
    return derived


def _load_v3_configuration(store, configurations, directory, project_id, system_id):
    """Read-only restoration after physical repair, before manager construction."""
    original = tuple(copy.deepcopy(configurations))
    status = {'configured': False, 'bundle_present': False, 'error': None}
    try:
        path = _path(directory)
        if not path.exists():
            return original, status
        status['bundle_present'] = True
        cache = _RestorationReads(); raw = cache.bytes(path)
        bundle = strict_loads(raw.decode('utf-8'))
        derived = _validate(bundle, store, original[4], directory, project_id, system_id, cache)
        cache.verify()
        require(path.read_bytes() == raw, 'lvs_repair_profile_changed', 'The saved correction changed while reopening; refresh the saved system.')
        result = list(original); result[4] = derived
        status.update(configured=True, profile_version=PROFILE, source_identity=copy.deepcopy(bundle['source_identity']),
                      bundle_sha256=hashlib.sha256(raw).hexdigest())
        return tuple(result), status
    except (DomainError, OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
        status['error'] = {'code': getattr(error, 'code', 'lvs_repair_profile_unavailable'),
                           'message': getattr(error, 'message', 'The saved LVS correction could not be restored; its bytes were preserved.')}
        return original, status


def _prepare_v3(server, layout_run_id, drc_run_id, source_lvs_run_id, revision_id):
    from .workspace_server import _postlayout_profile_directory
    require(all(type(value) is str for value in (layout_run_id, drc_run_id, source_lvs_run_id, revision_id)),
            'lvs_repair_request_invalid', 'Provide only the exact saved source IDs and current saved revision.')
    with server.execution_lock:
        workspace = getattr(server, 'workspace', None)
        require(workspace is not None and workspace.context is not None and not workspace.identity['read_only'],
                'lvs_repair_readonly', 'Open the editable original system before preparing corrected extraction.')
        for name in MANAGERS:
            manager = getattr(server, name, None)
            require(manager is not None and not getattr(manager, '_storage_error', None)
                    and not (getattr(manager, '_worker', None) and manager._worker.is_alive())
                    and not (hasattr(manager, 'is_active') and manager.is_active()),
                    'lvs_repair_busy', 'Finish active work and resolve process cleanup or history errors before preparing extraction.')
        identity = workspace.identity
        directory = _postlayout_profile_directory(workspace.registry.root, identity['project_id'], identity['system_id'])
        path = _path(directory)
        # Reconstruct the runtime that existed before this independent S13
        # correction, including any earlier generic physical-closure bundle.
        from .physical_repair_session import load_repair_configurations
        bases, physical_status = load_repair_configurations(server.store, workspace.configurations, directory,
                                                          identity['project_id'], identity['system_id'])
        require(not physical_status.get('error'), 'lvs_repair_base_changed', 'Restore the original physical correction profile first.')
        lvs = server.lvs_workflow
        with lvs._source_locks():
            current = server.store.envelope()
            require(current['revision']['id'] == revision_id, 'lvs_repair_source_not_current', 'Open the latest saved revision before preparing extraction.')
            _, active_source, error = lvs._source_state()
            require(active_source is not None and error is None
                    and active_source['layout']['id'] == layout_run_id and active_source['drc']['id'] == drc_run_id,
                    'lvs_repair_source_not_current', 'The latest current adopted S11/S12 must still match this correction request.')
            with lvs.lock:
                cache = _RestorationReads()
                if path.exists():
                    raw = cache.bytes(path); bundle = strict_loads(raw.decode('utf-8'))
                    derived = _validate(bundle, server.store, bases[4], directory, identity['project_id'], identity['system_id'], cache)
                    wanted = bundle['source_identity']
                    require((layout_run_id, drc_run_id, source_lvs_run_id) == (wanted['layout_run_id'], wanted['drc_run_id'], wanted['historical_lvs_run_id'])
                            and object_hash(lvs.tool_configuration) == object_hash(derived),
                            'lvs_repair_profile_exists', 'A different immutable extraction correction already exists; saved bytes were preserved.')
                else:
                    lvs.observe_design(); runs = lvs._state['runs']
                    require(runs and runs[-1]['id'] == source_lvs_run_id and lvs._decorate(runs[-1])['freshness'] == 'Current',
                            'lvs_repair_source_not_current', 'Select the latest current actual adopted S13 with the original terminal warnings.')
                    source_revision = runs[-1]['revision_id']
                    records = _source(server.store, layout_run_id, drc_run_id, source_lvs_run_id, source_revision, cache)
                    require(object_hash(runs[-1]) == object_hash(records['lvs']) and object_hash(lvs.tool_configuration) == object_hash(bases[4]),
                            'lvs_repair_base_changed', 'Retain the exact durable S13 and its original active extraction profile.')
                    derived = _build(records, bases[4], directory)
                    bundle = {'schema': SCHEMA, 'project_id': identity['project_id'], 'system_id': identity['system_id'],
                              'source_revision_id': source_revision, 'base_configuration_sha256': object_hash(bases[4]),
                              'source_identity': _identity(records), 'configuration': derived,
                              'actor': 'explicit_GUI_action', 'created_at': utc_now()}
                    bundle['record_hash'] = object_hash(bundle)
                    cache.verify()
                    require(not path.exists(), 'lvs_repair_profile_exists', 'An existing immutable correction bundle cannot be overwritten.')
                    _write(path, bundle)
                cache.verify()
                status = {'configured': True, 'bundle_present': True, 'error': None, 'profile_version': PROFILE,
                          'source_identity': copy.deepcopy(bundle['source_identity']),
                          'bundle_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                lvs.tool_configuration = copy.deepcopy(derived)
                workspace.context.lvs_repair_session = copy.deepcopy(status)
                server.lvs_repair_session = copy.deepcopy(status)
        lvs.observe_design(); server.postlayout_workflow.observe_design()
        return copy.deepcopy(status)


def _initial_eligibility(server, profile_version=PROFILE):
    """Read-only preparation candidate metadata, never proof or execution."""
    result = {'available': False, 'eligible': False, 'blocked_reason': None, 'profile_version': profile_version, 'source': None}
    workspace = getattr(server, 'workspace', None)
    if workspace is None or workspace.context is None or workspace.identity['read_only']:
        result['blocked_reason'] = 'Open the editable original system to prepare corrected extraction.'
        return result
    result['available'] = True
    try:
        status = getattr(server, 'lvs_repair_session', {})
        require(not status.get('configured') and not status.get('bundle_present'), 'lvs_repair_profile_exists',
                status.get('error', {}).get('message') if type(status.get('error')) is dict else 'The immutable corrected extraction profile is already saved.')
        for name in MANAGERS:
            manager = getattr(server, name, None)
            require(manager is not None and not getattr(manager, '_storage_error', None)
                    and not (getattr(manager, '_worker', None) and manager._worker.is_alive())
                    and not (hasattr(manager, 'is_active') and manager.is_active()),
                    'lvs_repair_busy', 'Finish active work and resolve process cleanup or history errors before preparing extraction.')
        manager = server.lvs_workflow
        with manager._source_locks():
            key, source, error = manager._source_state()
            require(source is not None and error is None, 'lvs_repair_source_not_current', 'Current adopted S11 and S12 are required.')
            with manager.lock:
                runs = manager._state['runs']
                require(runs, 'lvs_repair_source_missing',
                        'Run the original LVS check and inspect its extraction feedback before preparing correction. Adoption is not required for direct v7 correction.')
                record = runs[-1]; view = manager._decorate(record)
                require(all(view.get(k) == v for k, v in (('execution_status', 'Completed'), ('validation_status', 'Passed'),
                        ('freshness', 'Current')))
                        and (view.get('review_status') == 'Accepted' or
                             (profile_version == V7_PROFILE and view.get('review_status') == 'Awaiting Review'))
                        and record.get('evidence_kind') == 'trusted_fixed_lvs_execution'
                        and record['source_key'] == key and not record.get('error')
                        and record.get('checks', {}).get('software_qa_fixture') is not True,
                        'lvs_repair_ineligible', 'Select the latest current completed LVS result with its original terminal warnings; adoption is not required for correction.')
                _checksum(record); _warnings(record)
                if profile_version == V7_PROFILE:
                    require(record.get('runtime_configuration', {}).get('profile', {}).get('profile_version') == 'hullcirq-sky130-lvs-v2',
                            'lvs_repair_base_changed', 'Direct v7 preparation requires the original completed v2 warning record; its adoption is not required.')
                layout, drc = source['layout'], source['drc']
                result['source'] = {'layout_run_id': layout['id'], 'drc_run_id': drc['id'], 'source_lvs_run_id': record['id'],
                    'revision_id': server.store.envelope()['revision']['id'], 'source_revision_id': record['revision_id'],
                    'layout_record_hash': layout['record_hash'], 'drc_record_hash': drc['record_hash'],
                    'source_lvs_record_hash': record['record_hash'], 'source_lvs_record_sha256': object_hash(record),
                    'input_gds_sha256': record['input_gds_sha256'], 'input_netlist_sha256': record['input_netlist_sha256']}
        from .lvs_tools import _fixed_profile, lvs_capability
        if profile_version == V7_PROFILE:
            from .workspace_server import _postlayout_profile_directory
            directory = _postlayout_profile_directory(workspace.registry.root, workspace.identity['project_id'], workspace.identity['system_id'])
            _no_legacy_bundles(directory)
            require(not _direct_path(directory).exists(), 'lvs_repair_profile_exists', 'Restore the existing immutable direct preparation before another action.')
        path = ROOT / 'configs' / ('lvs_profile_sky130_v7.json' if profile_version == V7_PROFILE else 'lvs_profile_sky130_v3.json')
        require(path.is_file(), 'lvs_repair_recipe_unavailable', 'The fixed terminal-safe extraction recipe is not installed.')
        profile = _fixed_profile(strict_loads(path.read_text(encoding='utf-8')))
        capability = lvs_capability({**copy.deepcopy(manager.tool_configuration), 'profile': profile})
        require(capability.get('available') is True, 'lvs_repair_recipe_unavailable', capability.get('reason') or 'The fixed extraction recipe is unavailable.')
        result['eligible'] = True
    except (DomainError, OSError, ValueError, KeyError, TypeError) as error:
        result['blocked_reason'] = getattr(error, 'message', 'The current source or fixed extraction recipe is unavailable.')
    return result


def _upgrade_path(directory, profile_version=UPGRADE_PROFILE):
    require(profile_version in UPGRADES, 'lvs_repair_upgrade_incompatible', 'Use only a fixed versioned extraction upgrade.')
    path = _path(directory).with_name(UPGRADES[profile_version]['bundle'])
    require(not path.is_symlink() and not path.is_junction(), 'lvs_repair_path', 'An immutable extraction bundle cannot be a link.')
    return path


def _upgrade_failure_status(record, previous_profile):
    # v7 fixes only a completed v6 circuit-comparison failure. An incomplete
    # v6 launch cannot use that route. Older actual launch failures keep their
    # original admission meaning.
    expected_execution = 'Completed' if previous_profile == V6_PROFILE else 'Failed'
    result = record.get('execution_status') == expected_execution and record.get('validation_status') == 'Failed'
    if previous_profile == V6_PROFILE:
        checks = record.get('checks', {})
        result = result and checks.get('status') == 'Completed' and checks.get('executed') is True \
            and type(checks.get('exit_code')) is int and checks['exit_code'] == 0 \
            and checks.get('checks', {}).get('extraction', {}).get('validation_status') == 'Passed' \
            and checks.get('checks', {}).get('lvs', {}).get('validation_status') == 'Failed'
    return result


def _failed_v3(store, identifier, previous, cache, previous_profile=PROFILE):
    """Reconstruct an exact known failed recipe, never certify LVS success."""
    from .lvs_workflow import validate_source_snapshot
    from .lvs_tools import validate_failed_lvs_result
    state = _saved(store, 'lvs_workflow', cache)
    matches = [record for record in state['runs'] if record.get('id') == identifier]
    require(len(matches) == 1, 'lvs_repair_upgrade_source', 'Retain the exact terminal failed extraction record.')
    failed = matches[0]; _checksum(failed)
    require(_upgrade_failure_status(failed, previous_profile)
            and failed.get('review_status') == 'Awaiting Review' and failed.get('error') is None
            and failed.get('evidence_kind') == 'trusted_fixed_lvs_execution'
            and failed.get('checks', {}).get('cleanup_unresolved') is False
            and failed.get('checks', {}).get('software_qa_fixture') is not True
            and not any(review.get('run_id') == identifier for review in state['reviews'])
            and object_hash(failed.get('runtime_configuration')) == object_hash(previous['configuration'])
            and failed.get('runtime_configuration', {}).get('profile', {}).get('profile_version') == previous_profile
            and failed.get('revision_id') == previous['source_revision_id']
            and failed.get('layout_run_id') == previous['source_identity']['layout_run_id']
            and failed.get('drc_run_id') == previous['source_identity']['drc_run_id']
            and object_hash(failed.get('source_inputs')) == previous['source_identity']['source_inputs_sha256'],
            'lvs_repair_upgrade_source', 'Use only the unmodified actual failed execution of the immediately preceding recipe.')
    validate_source_snapshot(failed)
    proof = validate_failed_lvs_result(failed['checks'], failed['drc_snapshot'], failed['layout_snapshot'], failed['runtime_configuration'])
    require(type(proof) is dict and proof.get('validation_status') == 'Passed'
            and proof.get('scope') == 'actual_failed_'+previous_profile.rsplit('-', 1)[-1]+'_execution_proof_only_not_LVS_success',
            'lvs_repair_upgrade_source', 'The exact failed execution proof must be reconstructed; failure is not LVS success.')
    return failed


def _upgrade_identity(previous_raw, failed, previous_profile=PROFILE):
    return {'schema': UPGRADE_BINDING_SCHEMA, 'previous_profile_version': previous_profile,
            'previous_bundle_sha256': hashlib.sha256(previous_raw).hexdigest(),
            'failed_lvs_run_id': failed['id'], 'failed_lvs_record_sha256': object_hash(failed),
            'failed_lvs_execution_sha256': _execution_hash(failed)}


def _build_upgrade(previous, previous_raw, failed, directory, profile_version=UPGRADE_PROFILE):
    from .lvs_tools import configuration_projection
    require(profile_version in UPGRADES, 'lvs_repair_upgrade_incompatible', 'Use only a fixed versioned extraction upgrade.')
    step = UPGRADES[profile_version]
    path = ROOT / 'configs' / step['profile_file']
    require(path.is_file(), 'lvs_repair_recipe_unavailable', 'The separate fixed extraction recipe is not installed.')
    profile = strict_loads(path.read_text(encoding='utf-8'))
    require(profile.get('profile_version') == profile_version, 'lvs_repair_recipe_unavailable', 'Use the exact versioned extraction recipe.')
    work = Path(directory) / step['work']
    require(not work.is_symlink() and not work.is_junction() and work.resolve().parent == Path(directory).resolve(),
            'lvs_repair_path', 'Keep corrected extraction outputs in a separate host-managed directory.')
    result = copy.deepcopy(previous['configuration'])
    result.update(profile=profile, working_directory=str(work), repair_upgrade_binding=_upgrade_identity(previous_raw, failed, step['previous']))
    configuration_projection(failed['drc_snapshot'], failed['layout_snapshot'], result)
    return result


def _validate_upgrade(bundle, previous, previous_raw, store, directory, project_id, system_id, cache, profile_version=UPGRADE_PROFILE):
    require(profile_version in UPGRADES, 'lvs_repair_upgrade_incompatible', 'Use only a fixed versioned extraction upgrade.')
    step = UPGRADES[profile_version]
    _checksum(bundle)
    require(set(bundle) == {'schema', 'project_id', 'system_id', 'source_revision_id', 'source_identity',
                            'previous_bundle_sha256', 'upgrade_identity', 'configuration', 'actor', 'created_at', 'record_hash'}
            and bundle.get('schema') == step['schema'] and bundle.get('project_id') == project_id
            and bundle.get('system_id') == system_id and bundle.get('actor') == 'explicit_GUI_action'
            and type(bundle.get('created_at')) is str
            and bundle.get('source_revision_id') == previous['source_revision_id']
            and bundle.get('source_identity') == previous['source_identity']
            and bundle.get('previous_bundle_sha256') == hashlib.sha256(previous_raw).hexdigest()
            and type(bundle.get('upgrade_identity')) is dict,
            'lvs_repair_upgrade_incompatible', 'Preserve the original v3 bundle, original adopted source and exact system identity.')
    failed = _failed_v3(store, bundle['upgrade_identity'].get('failed_lvs_run_id'), previous, cache, step['previous'])
    require(bundle['upgrade_identity'] == _upgrade_identity(previous_raw, failed, step['previous']), 'lvs_repair_upgrade_incompatible',
            'The failed v3 source or original immutable bundle changed.')
    result = _build_upgrade(previous, previous_raw, failed, directory, profile_version)
    require(object_hash(result) == object_hash(bundle['configuration']), 'lvs_repair_upgrade_incompatible',
            'A new checksum cannot authorize altered versioned configuration or source bindings.')
    return result


def load_repair_configuration(store, configurations, directory, project_id, system_id):
    original = tuple(copy.deepcopy(configurations))
    if _direct_path(directory).exists():
        return _load_direct(store, original, directory, project_id, system_id)
    restored, status = _load_v3_configuration(store, original, directory, project_id, system_id)
    try:
        if not any(_upgrade_path(directory, version).exists() for version in UPGRADES):
            return restored, status
        require(status.get('configured') and status.get('profile_version') == PROFILE and not status.get('error'),
                'lvs_repair_upgrade_incompatible', 'Restore the original immutable v3 correction before v4.')
        cache = _RestorationReads(); previous_raw = cache.bytes(_path(directory)); previous = strict_loads(previous_raw.decode('utf-8'))
        _validate(previous, store, original[4], directory, project_id, system_id, cache)
        result = list(restored)
        for version, step in UPGRADES.items():
            path = _upgrade_path(directory, version)
            if not path.exists():
                require(not any(_upgrade_path(directory, later).exists() for later in list(UPGRADES)[list(UPGRADES).index(version)+1:]),
                        'lvs_repair_upgrade_incompatible', 'Retain every immutable ancestor before restoring a later extraction recipe.')
                break
            raw = cache.bytes(path); bundle = strict_loads(raw.decode('utf-8'))
            result[4] = _validate_upgrade(bundle, previous, previous_raw, store, directory, project_id, system_id, cache, version)
            status = {'configured': True, 'bundle_present': True, 'error': None, 'profile_version': version,
                'source_identity': copy.deepcopy(bundle['source_identity']), 'upgrade_identity': copy.deepcopy(bundle['upgrade_identity']),
                'bundle_sha256': hashlib.sha256(raw).hexdigest(), 'previous_bundle_sha256': hashlib.sha256(previous_raw).hexdigest()}
            previous, previous_raw = bundle, raw
        cache.verify()
        return tuple(result), status
    except (DomainError, OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
        return original, {'configured': False, 'bundle_present': True, 'error': {
            'code': getattr(error, 'code', 'lvs_repair_upgrade_unavailable'),
            'message': getattr(error, 'message', 'The immutable correction chain could not be restored; saved bundles were preserved.')}}


def _prepare_upgrade(server, layout_run_id, drc_run_id, failed_lvs_run_id, revision_id, profile_version=UPGRADE_PROFILE):
    from .workspace_server import _postlayout_profile_directory
    from .physical_repair_session import load_repair_configurations
    require(profile_version in UPGRADES, 'lvs_repair_upgrade_incompatible', 'Use a fixed extraction upgrade.')
    step = UPGRADES[profile_version]
    require(all(type(value) is str for value in (layout_run_id, drc_run_id, failed_lvs_run_id, revision_id)),
            'lvs_repair_request_invalid', 'Provide only exact saved source IDs and the current revision.')
    with server.execution_lock:
        workspace = getattr(server, 'workspace', None)
        require(workspace is not None and workspace.context is not None and not workspace.identity['read_only'],
                'lvs_repair_readonly', 'Open the editable original system before preparing corrected extraction.')
        for name in MANAGERS:
            manager = getattr(server, name, None)
            require(manager is not None and not getattr(manager, '_storage_error', None)
                    and not (getattr(manager, '_worker', None) and manager._worker.is_alive())
                    and not (hasattr(manager, 'is_active') and manager.is_active()),
                    'lvs_repair_busy', 'Finish active work and resolve cleanup before preparing corrected extraction.')
        scope = workspace.identity
        directory = _postlayout_profile_directory(workspace.registry.root, scope['project_id'], scope['system_id'])
        path = _upgrade_path(directory, profile_version); previous_path = _path(directory)
        bases, physical_status = load_repair_configurations(server.store, workspace.configurations, directory, scope['project_id'], scope['system_id'])
        require(not physical_status.get('error'), 'lvs_repair_base_changed', 'Restore the original physical correction first.')
        lvs = server.lvs_workflow
        with lvs._source_locks():
            require(server.store.envelope()['revision']['id'] == revision_id, 'lvs_repair_source_not_current', 'Open the latest saved revision.')
            _, source, error = lvs._source_state()
            require(source is not None and error is None and source['layout']['id'] == layout_run_id and source['drc']['id'] == drc_run_id,
                    'lvs_repair_source_not_current', 'Retain the current adopted original S11/S12 source chain.')
            with lvs.lock:
                cache = _RestorationReads(); previous_raw = cache.bytes(previous_path); previous = strict_loads(previous_raw.decode('utf-8'))
                old_configuration = _validate(previous, server.store, bases[4], directory, scope['project_id'], scope['system_id'], cache)
                for ancestor in UPGRADES:
                    if ancestor == profile_version:
                        break
                    ancestor_raw = cache.bytes(_upgrade_path(directory, ancestor)); ancestor_bundle = strict_loads(ancestor_raw.decode('utf-8'))
                    old_configuration = _validate_upgrade(ancestor_bundle, previous, previous_raw, server.store, directory,
                                                          scope['project_id'], scope['system_id'], cache, ancestor)
                    previous, previous_raw = ancestor_bundle, ancestor_raw
                require((layout_run_id, drc_run_id) == (previous['source_identity']['layout_run_id'], previous['source_identity']['drc_run_id']),
                        'lvs_repair_upgrade_source', 'Retain both original adopted source IDs.')
                if path.exists():
                    raw = cache.bytes(path); bundle = strict_loads(raw.decode('utf-8'))
                    derived = _validate_upgrade(bundle, previous, previous_raw, server.store, directory, scope['project_id'], scope['system_id'], cache, profile_version)
                    require(bundle['upgrade_identity']['failed_lvs_run_id'] == failed_lvs_run_id
                            and object_hash(lvs.tool_configuration) == object_hash(derived),
                            'lvs_repair_profile_exists', 'A different immutable correction already exists; saved bytes were preserved.')
                else:
                    require(object_hash(lvs.tool_configuration) == object_hash(old_configuration), 'lvs_repair_upgrade_source', 'Keep the exact immediately preceding configured runtime.')
                    lvs.observe_design(); runs = lvs._state['runs']
                    require(runs and runs[-1]['id'] == failed_lvs_run_id and lvs._decorate(runs[-1])['freshness'] == 'Current',
                            'lvs_repair_source_not_current', 'Select the latest current terminal failed extraction of the preceding recipe.')
                    failed = _failed_v3(server.store, failed_lvs_run_id, previous, cache, step['previous'])
                    require(object_hash(runs[-1]) == object_hash(failed), 'lvs_repair_upgrade_source', 'Retain the exact durable failed record.')
                    derived = _build_upgrade(previous, previous_raw, failed, directory, profile_version)
                    bundle = {'schema': step['schema'], 'project_id': scope['project_id'], 'system_id': scope['system_id'],
                        'source_revision_id': previous['source_revision_id'], 'source_identity': copy.deepcopy(previous['source_identity']),
                        'previous_bundle_sha256': hashlib.sha256(previous_raw).hexdigest(), 'upgrade_identity': _upgrade_identity(previous_raw, failed, step['previous']),
                        'configuration': derived, 'actor': 'explicit_GUI_action', 'created_at': utc_now()}
                    bundle['record_hash'] = object_hash(bundle)
                    cache.verify(); require(not path.exists(), 'lvs_repair_profile_exists', 'Never overwrite an immutable extraction bundle.')
                    _write(path, bundle)
                cache.verify()
                status = {'configured': True, 'bundle_present': True, 'error': None, 'profile_version': profile_version,
                    'source_identity': copy.deepcopy(bundle['source_identity']), 'upgrade_identity': copy.deepcopy(bundle['upgrade_identity']),
                    'bundle_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'previous_bundle_sha256': hashlib.sha256(previous_raw).hexdigest()}
                lvs.tool_configuration = copy.deepcopy(derived)
                workspace.context.lvs_repair_session = copy.deepcopy(status); server.lvs_repair_session = copy.deepcopy(status)
        lvs.observe_design(); server.postlayout_workflow.observe_design()
        return copy.deepcopy(status)


def prepare_repair(server, layout_run_id, drc_run_id, source_lvs_run_id, revision_id):
    status = getattr(server, 'lvs_repair_session', {})
    if status.get('preparation_kind') == 'direct_v7':
        return _prepare_direct(server, layout_run_id, drc_run_id, source_lvs_run_id, revision_id)
    runs = getattr(getattr(server, 'lvs_workflow', None), '_state', {}).get('runs', [])
    active_profile = status.get('profile_version')
    if runs and _upgrade_failure_status(runs[-1], active_profile) and runs[-1].get('id') == source_lvs_run_id:
        next_profile = next((version for version, step in UPGRADES.items() if step['previous'] == active_profile
                             and runs[-1].get('runtime_configuration', {}).get('profile', {}).get('profile_version') == active_profile), None)
        if next_profile:
            return _prepare_upgrade(server, layout_run_id, drc_run_id, source_lvs_run_id, revision_id, next_profile)
    if active_profile in UPGRADES:
        return _prepare_upgrade(server, layout_run_id, drc_run_id, source_lvs_run_id, revision_id, active_profile)
    if active_profile == PROFILE:
        return _prepare_v3(server, layout_run_id, drc_run_id, source_lvs_run_id, revision_id)
    return _prepare_direct(server, layout_run_id, drc_run_id, source_lvs_run_id, revision_id)


def eligibility(server):
    status = getattr(server, 'lvs_repair_session', {})
    if status.get('preparation_kind') == 'direct_v7' and status.get('configured'):
        return {'available': False, 'eligible': False, 'blocked_reason': 'Direct v7 is already prepared; Run remains separate.',
                'profile_version': V7_PROFILE, 'mode': 'initial_v7', 'source': None}
    active_profile = status.get('profile_version')
    target_profile = next((version for version, step in UPGRADES.items() if step['previous'] == active_profile), None)
    if target_profile is None and active_profile in UPGRADES and status.get('configured'):
        return {'available': False, 'eligible': False, 'blocked_reason': 'The immutable correction is already prepared; execution remains a separate action.',
                'profile_version': active_profile, 'mode': UPGRADES[active_profile]['mode'], 'source': None}
    if target_profile is None or not status.get('configured'):
        result = _initial_eligibility(server, V7_PROFILE); result['mode'] = 'initial_v7'
        return result
    step = UPGRADES[target_profile]
    result = {'available': False, 'eligible': False, 'blocked_reason': None, 'profile_version': target_profile,
              'mode': step['mode'], 'source': None}
    workspace = getattr(server, 'workspace', None)
    if workspace is None or workspace.context is None or workspace.identity['read_only']:
        result['blocked_reason'] = 'Open the editable original system to prepare corrected extraction.'
        return result
    result['available'] = True
    try:
        require(not status.get('error'), 'lvs_repair_upgrade_incompatible', 'Restore the original correction session first.')
        for name in MANAGERS:
            manager = getattr(server, name, None)
            require(manager is not None and not getattr(manager, '_storage_error', None)
                    and not (getattr(manager, '_worker', None) and manager._worker.is_alive())
                    and not (hasattr(manager, 'is_active') and manager.is_active()), 'lvs_repair_busy', 'Finish active work and resolve cleanup first.')
        manager = server.lvs_workflow
        with manager._source_locks():
            key, source, error = manager._source_state()
            require(source is not None and error is None, 'lvs_repair_source_not_current', 'Current adopted S11/S12 are required.')
            with manager.lock:
                require(manager._state['runs'], 'lvs_repair_upgrade_source', 'Select the complete failed record of the preceding recipe.')
                record = manager._state['runs'][-1]; view = manager._decorate(record)
                require(_upgrade_failure_status(record, active_profile)
                        and record.get('review_status') == 'Awaiting Review' and view.get('freshness') == 'Current'
                        and record.get('source_key') == key and record.get('evidence_kind') == 'trusted_fixed_lvs_execution'
                        and record.get('error') is None and record.get('checks', {}).get('cleanup_unresolved') is False
                        and record.get('checks', {}).get('software_qa_fixture') is not True
                        and record.get('runtime_configuration', {}).get('profile', {}).get('profile_version') == active_profile,
                        'lvs_repair_upgrade_source', 'Select the latest current actual terminal failed extraction of the preceding recipe.')
                _checksum(record)
                from .workspace_server import _postlayout_profile_directory
                directory = _postlayout_profile_directory(workspace.registry.root, workspace.identity['project_id'], workspace.identity['system_id'])
                previous_path = _path(directory) if active_profile == PROFILE else _upgrade_path(directory, active_profile)
                previous_raw = previous_path.read_bytes(); previous = strict_loads(previous_raw.decode('utf-8')); _checksum(previous)
                require(previous['source_identity'] == status['source_identity']
                        and object_hash(record['runtime_configuration']) == object_hash(previous['configuration']),
                        'lvs_repair_upgrade_source', 'Retain the exact preceding configured session and original source binding.')
                layout, drc = source['layout'], source['drc']
                result['source'] = {'layout_run_id': layout['id'], 'drc_run_id': drc['id'], 'source_lvs_run_id': record['id'],
                    'revision_id': server.store.envelope()['revision']['id'], 'source_revision_id': record['revision_id'],
                    'layout_record_hash': layout['record_hash'], 'drc_record_hash': drc['record_hash'],
                    'source_lvs_record_hash': record['record_hash'], 'source_lvs_record_sha256': object_hash(record),
                    'input_gds_sha256': record['input_gds_sha256'], 'input_netlist_sha256': record['input_netlist_sha256'],
                    'historical_lvs_run_id': previous['source_identity']['historical_lvs_run_id'],
                    'historical_lvs_record_sha256': previous['source_identity']['historical_lvs_record_sha256'],
                    'previous_profile_version': active_profile, 'previous_bundle_sha256': hashlib.sha256(previous_raw).hexdigest()}
        from .lvs_tools import _fixed_profile, lvs_capability
        profile = _fixed_profile(strict_loads((ROOT/'configs'/step['profile_file']).read_text(encoding='utf-8')))
        capability = lvs_capability({**copy.deepcopy(manager.tool_configuration), 'profile': profile})
        require(capability.get('available') is True, 'lvs_repair_recipe_unavailable', capability.get('reason') or 'The fixed versioned recipe is unavailable.')
        result['eligible'] = True
    except (DomainError, OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
        result['blocked_reason'] = getattr(error, 'message', 'The preceding failed source or separate fixed recipe is unavailable.')
    return result


def _direct_path(directory):
    path = _path(directory).with_name(DIRECT_BUNDLE_NAME)
    require(not path.is_symlink() and not path.is_junction(), 'lvs_repair_path', 'The immutable direct extraction bundle cannot be a link.')
    return path


def _no_legacy_bundles(directory):
    require(not _path(directory).exists() and not any(_upgrade_path(directory, version).exists() for version in UPGRADES),
            'lvs_repair_profile_exists', 'Direct preparation cannot bypass or overwrite an existing immutable correction chain.')


def _build_direct(records, base_configuration, directory):
    from .lvs_tools import configuration_projection
    layout, drc, lvs = (records[name] for name in ('physical', 'drc', 'lvs'))
    require(object_hash(base_configuration) == object_hash(lvs['runtime_configuration'])
            and lvs['runtime_configuration'].get('profile', {}).get('profile_version') == 'hullcirq-sky130-lvs-v2'
            and object_hash(base_configuration.get('physical_runtime')) == object_hash(layout['runtime_configuration']),
            'lvs_repair_base_changed', 'Direct v7 preparation requires the exact adopted original v2 runtime and source.')
    path = ROOT/'configs/lvs_profile_sky130_v7.json'
    require(path.is_file(), 'lvs_repair_recipe_unavailable', 'The fixed direct v7 extraction recipe is not installed.')
    profile = strict_loads(path.read_text(encoding='utf-8'))
    require(profile.get('profile_version') == V7_PROFILE, 'lvs_repair_recipe_unavailable', 'Use the fixed v7 extraction recipe.')
    work = Path(directory)/'lv7-direct'
    require(not work.is_symlink() and not work.is_junction() and work.resolve().parent == Path(directory).resolve(),
            'lvs_repair_path', 'Use the separate host-managed direct v7 output scope.')
    result = copy.deepcopy(base_configuration)
    require('repair_upgrade_binding' not in result, 'lvs_repair_base_changed', 'A direct preparation cannot inherit an upgrade binding.')
    result.update(profile=profile, working_directory=str(work), repair_preparation_kind='direct_v7', repair_source_binding=_identity(records))
    configuration_projection(drc, layout, result)
    return result


def _validate_direct(bundle, store, base_configuration, directory, project_id, system_id, cache):
    _checksum(bundle)
    require(set(bundle) == {'schema', 'project_id', 'system_id', 'source_revision_id', 'base_configuration_sha256',
                           'source_identity', 'configuration', 'actor', 'created_at', 'record_hash'}
            and bundle.get('schema') in (DIRECT_SCHEMA, DIRECT_PENDING_SCHEMA) and bundle.get('project_id') == project_id
            and bundle.get('system_id') == system_id and bundle.get('actor') == 'explicit_GUI_action'
            and type(bundle.get('created_at')) is str and bundle.get('base_configuration_sha256') == object_hash(base_configuration),
            'lvs_repair_profile_incompatible', 'Retain the exact original direct-preparation system and base runtime.')
    source = bundle['source_identity']
    records = _source(store, source['layout_run_id'], source['drc_run_id'], source['historical_lvs_run_id'], bundle['source_revision_id'], cache,
                      allow_pending_lvs=bundle['schema'] == DIRECT_PENDING_SCHEMA)
    require(source == _identity(records), 'lvs_repair_source_changed', 'The original direct-preparation source changed.')
    derived = _build_direct(records, base_configuration, directory)
    require(derived == bundle['configuration'], 'lvs_repair_profile_incompatible', 'A new checksum cannot authorize changed direct v7 configuration.')
    return derived


def _direct_status(bundle, raw):
    return {'configured': True, 'bundle_present': True, 'error': None, 'profile_version': V7_PROFILE,
            'preparation_kind': 'direct_v7', 'source_identity': copy.deepcopy(bundle['source_identity']),
            'bundle_sha256': hashlib.sha256(raw).hexdigest()}


def _load_direct(store, configurations, directory, project_id, system_id):
    original = tuple(copy.deepcopy(configurations))
    try:
        _no_legacy_bundles(directory)
        cache = _RestorationReads(); raw = cache.bytes(_direct_path(directory)); bundle = strict_loads(raw.decode('utf-8'))
        result = list(original); result[4] = _validate_direct(bundle, store, original[4], directory, project_id, system_id, cache)
        cache.verify()
        return tuple(result), _direct_status(bundle, raw)
    except (DomainError, OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
        return original, {'configured': False, 'bundle_present': True, 'error': {
            'code': getattr(error, 'code', 'lvs_repair_profile_unavailable'),
            'message': getattr(error, 'message', 'The direct v7 correction is incompatible; saved bytes were preserved.')}}


def _prepare_direct(server, layout_run_id, drc_run_id, source_lvs_run_id, revision_id):
    from .workspace_server import _postlayout_profile_directory
    from .physical_repair_session import load_repair_configurations
    require(all(type(value) is str for value in (layout_run_id, drc_run_id, source_lvs_run_id, revision_id)),
            'lvs_repair_request_invalid', 'Provide the exact saved source IDs and current revision.')
    with server.execution_lock:
        workspace = getattr(server, 'workspace', None)
        require(workspace is not None and workspace.context is not None and not workspace.identity['read_only'],
                'lvs_repair_readonly', 'Open the editable original system to prepare direct v7 extraction.')
        for name in MANAGERS:
            manager = getattr(server, name, None)
            require(manager is not None and not getattr(manager, '_storage_error', None)
                    and not (getattr(manager, '_worker', None) and manager._worker.is_alive())
                    and not (hasattr(manager, 'is_active') and manager.is_active()),
                    'lvs_repair_busy', 'Finish active work and resolve cleanup before preparation.')
        scope = workspace.identity
        directory = _postlayout_profile_directory(workspace.registry.root, scope['project_id'], scope['system_id'])
        _no_legacy_bundles(directory); path = _direct_path(directory)
        bases, physical_status = load_repair_configurations(server.store, workspace.configurations, directory, scope['project_id'], scope['system_id'])
        require(not physical_status.get('error'), 'lvs_repair_base_changed', 'Restore the original physical correction first.')
        lvs = server.lvs_workflow
        with lvs._source_locks():
            require(server.store.envelope()['revision']['id'] == revision_id, 'lvs_repair_source_not_current', 'Open the latest saved revision.')
            _, source, error = lvs._source_state()
            require(source is not None and error is None and source['layout']['id'] == layout_run_id and source['drc']['id'] == drc_run_id,
                    'lvs_repair_source_not_current', 'Retain the current adopted original S11/S12 chain.')
            with lvs.lock:
                cache = _RestorationReads()
                if path.exists():
                    raw = cache.bytes(path); bundle = strict_loads(raw.decode('utf-8'))
                    derived = _validate_direct(bundle, server.store, bases[4], directory, scope['project_id'], scope['system_id'], cache)
                    require(bundle['source_identity']['historical_lvs_run_id'] == source_lvs_run_id
                            and object_hash(lvs.tool_configuration) == object_hash(derived),
                            'lvs_repair_profile_exists', 'A different immutable direct preparation already exists.')
                else:
                    lvs.observe_design(); runs = lvs._state['runs']
                    require(runs and runs[-1]['id'] == source_lvs_run_id and lvs._decorate(runs[-1])['freshness'] == 'Current',
                            'lvs_repair_source_not_current', 'Select the latest current adopted original v2 terminal warnings.')
                    records = _source(server.store, layout_run_id, drc_run_id, source_lvs_run_id, runs[-1]['revision_id'], cache, allow_pending_lvs=True)
                    require(object_hash(runs[-1]) == object_hash(records['lvs']) and object_hash(lvs.tool_configuration) == object_hash(bases[4]),
                            'lvs_repair_base_changed', 'Keep the original durable accepted source and active v2 runtime.')
                    derived = _build_direct(records, bases[4], directory)
                    schema = DIRECT_PENDING_SCHEMA if records['lvs']['review_status'] == 'Awaiting Review' else DIRECT_SCHEMA
                    bundle = {'schema': schema, 'project_id': scope['project_id'], 'system_id': scope['system_id'],
                        'source_revision_id': runs[-1]['revision_id'], 'base_configuration_sha256': object_hash(bases[4]),
                        'source_identity': _identity(records), 'configuration': derived, 'actor': 'explicit_GUI_action', 'created_at': utc_now()}
                    bundle['record_hash'] = object_hash(bundle)
                    cache.verify(); require(not path.exists(), 'lvs_repair_profile_exists', 'Never overwrite an immutable direct preparation.')
                    _write(path, bundle)
                cache.verify(); status = _direct_status(bundle, path.read_bytes())
                lvs.tool_configuration = copy.deepcopy(derived)
                workspace.context.lvs_repair_session = copy.deepcopy(status); server.lvs_repair_session = copy.deepcopy(status)
        lvs.observe_design(); server.postlayout_workflow.observe_design()
        return copy.deepcopy(status)

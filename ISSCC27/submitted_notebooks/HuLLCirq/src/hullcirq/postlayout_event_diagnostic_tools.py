"""Recheck the fixed event-recorded timed diagnostic without launching any tool.

The development assistant implemented this review adapter. The original NPU
job, PDK models, signed timing limits and simulator outputs remain separate
evidence. Successful integrity checks never qualify the unsupported S14 flow.
"""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path

from .domain import DomainError
from .physical_tools import require, load, sha
from .postlayout_execution_audit import validate_completed_execution
from .verification import object_hash

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / 'configs/postlayout_saved_event_diagnostic_sky130_v1.json'
# Frozen after original-job completion and separate functional/event audits.
PROFILE_SHA256 = '80c17bebbc8c00b794a28c4353b7e2a7303d1e59a6b7d7c3593f9be89ee2af70'
SCOPE = 'saved_event_diagnostic_review'
ARCHIVE_RELATIVE_PATH = 'results/npu_postlayout_event_diagnostic_v1/evidence.json'
ORIGINAL_JOB_RELATIVE_PATH = '.work/m2l/dynamic/original-job-xbd2e32a'
SCHEMA = 'hullcirq-postlayout-saved-event-diagnostic-evidence-v1'
PHYSICAL_INPUTS = ('gds', 'def', 'netlist', 'powered_netlist')
EVENT_ARTIFACTS = frozenset({'event-transcript', 'event-manifest', 'event-summary',
    'event-audit-report', 'conditional-path-report', 'native-delay-readback',
    'native-delay-manifest', 'functional-provenance'})


def handles(configuration):
    """An unsupported diagnostic profile must never fall back to preflight."""
    return type(configuration) is dict and (
        configuration.get('execution_scope') == SCOPE
        or type(configuration.get('profile')) is dict
        and configuration['profile'].get('execution_scope') == SCOPE)


def _configuration(configuration):
    require(type(configuration) is dict and set(configuration) == {
        'profile', 'original_preflight_configuration', 'execution_scope', 'verification_supported'},
        'postlayout_diagnostic_configuration', 'Use the exact saved diagnostic review configuration.')
    require(configuration['execution_scope'] == SCOPE and configuration['verification_supported'] is False,
        'postlayout_diagnostic_configuration', 'Saved diagnostic review cannot enable S14 adoption.')
    require(len(PROFILE_SHA256) == 64 and PROFILE.is_file() and sha(PROFILE) == PROFILE_SHA256,
        'postlayout_diagnostic_profile', 'The frozen diagnostic profile is missing or changed.')
    profile = load(PROFILE)
    require(type(configuration['profile']) is dict and object_hash(configuration['profile']) == object_hash(profile)
        and profile.get('version') == 'hullcirq-sky130-saved-event-diagnostic-review-v1'
        and profile.get('execution_scope') == SCOPE and profile.get('verification_supported') is False
        and profile.get('archive_relative_path') == ARCHIVE_RELATIVE_PATH,
        'postlayout_diagnostic_profile', 'Only the pinned original-job diagnostic archive is supported.')
    original = configuration['original_preflight_configuration']
    require(type(original) is dict and object_hash(original) == profile.get('original_preflight_configuration_sha256'),
        'postlayout_diagnostic_configuration', 'Retain the unchanged original S14 readiness configuration.')
    # This validates the original PDK/model/profile bytes. It executes no tool.
    from .postlayout_tools import _configuration as preflight_configuration
    preflight_configuration(original)
    path = ROOT / ARCHIVE_RELATIVE_PATH
    require(path.is_file() and sha(path) == profile.get('evidence_sha256'),
        'postlayout_diagnostic_evidence', 'The frozen diagnostic evidence is missing or changed.')
    evidence = load(path)
    require(type(evidence) is dict and evidence.get('schema_version') == SCHEMA
        and type(evidence.get('original_source_binding')) is dict
        and type(evidence.get('original_source_inputs')) is dict
        and type(evidence.get('review_source_inputs')) is dict
        and type(evidence.get('frozen_result')) is dict
        and type(evidence.get('execution_audits')) is dict,
        'postlayout_diagnostic_evidence', 'Require the complete original source and retained execution bindings.')
    result = evidence['frozen_result']
    folder = (ROOT / ORIGINAL_JOB_RELATIVE_PATH).resolve()
    require(result.get('validation_status') == 'Unsupported' and result.get('executed') is True
        and result.get('verification_supported') is False and result.get('cleanup_unresolved') is False
        and result.get('status') == 'Completed' and type(result.get('diagnostics')) is list
        and type(result.get('commands')) is list and len(result['commands']) == 2
        and type(result.get('artifacts_directory')) is str
        and Path(result['artifacts_directory']).resolve() == folder
        and object_hash(evidence.get('artifact_manifest')) == object_hash(result.get('artifacts')),
        'postlayout_diagnostic_result', 'A retained unsupported diagnostic cannot be promoted or redirected.')
    from .postlayout_workflow import validate_artifact_manifest
    validate_artifact_manifest(result)
    require(EVENT_ARTIFACTS <= {entry['id'] for entry in result['artifacts']}
        and type(result.get('summary')) is dict,
        'postlayout_event_diagnostic_artifacts',
        'Retain all event, conditional-path, native-delay and functional reports with their exact summary.')
    require(set(evidence['execution_audits']) == {'compile', 'simulate'},
        'postlayout_diagnostic_execution', 'Both original tool operations need frozen birth and completion proofs.')
    for index, operation in enumerate(('compile', 'simulate')):
        audit = validate_completed_execution(folder, operation, worker_version='v3')
        require(object_hash(audit) == object_hash(evidence['execution_audits'][operation]),
            'postlayout_diagnostic_execution', 'An original tool request, input or process proof changed.')
        original_command = load(folder / ('compile-execution.json' if operation == 'compile' else 'simulate-execution.json'))
        require(object_hash(original_command) == object_hash(result['commands'][index])
            and original_command.get('executed') is True and original_command.get('status') == 'Completed'
            and type(original_command.get('exit_code')) is int and original_command['exit_code'] == 0,
            'postlayout_diagnostic_execution', 'Retain the exact original tool invocation and output record.')
    inputs = evidence['review_source_inputs']; old = evidence['original_source_inputs']
    require(set(inputs) == set(old) and 'timed_adapter' in inputs
        and all(object_hash(inputs[key]) == object_hash(value) for key, value in old.items() if key != 'timed_adapter'),
        'postlayout_diagnostic_source', 'Only the explicitly recorded executed timed adapter may differ from readiness.')
    adapter = inputs['timed_adapter']; payload = (folder / 'timed-testbench.v').read_bytes()
    require(type(adapter) is dict and adapter.get('origin') == 'executed_original_job_timed_v2_full_hierarchy_dump'
        and adapter.get('sha256') == hashlib.sha256(payload).hexdigest() and adapter.get('bytes') == len(payload),
        'postlayout_diagnostic_source', 'The executed timed adapter bytes must retain their distinct provenance.')
    return profile, evidence


def runtime_descriptor(configuration):
    try:
        profile, _ = _configuration(configuration)
        return {'available': True, 'verification_supported': False, 'execution_scope': SCOPE,
            'reason': profile['reason'], 'execution_started_by_this_review': False}
    except (DomainError, OSError, ValueError, KeyError, TypeError) as error:
        return {'available': False, 'verification_supported': False, 'execution_scope': SCOPE,
            'reason': getattr(error, 'message', 'The pinned retained diagnostic is unavailable or inconsistent.'),
            'execution_started_by_this_review': False}


def source_inputs(layout, configuration):
    _, evidence = _configuration(configuration)
    binding = evidence['original_source_binding']
    require(layout.get('id') == binding.get('layout_run_id')
        and layout.get('revision_id') == binding.get('revision_id')
        and object_hash(layout) == binding.get('layout_record_sha256')
        and object_hash(layout.get('verification_plan')) == binding.get('verification_plan_sha256')
        == layout.get('verification_plan_sha256'),
        'postlayout_diagnostic_source', 'This diagnostic applies only to its exact original adopted S11 record and GUI job.')
    from .postlayout_tools import source_inputs as preflight_source_inputs
    current = preflight_source_inputs(layout, configuration['original_preflight_configuration'])
    require(object_hash(current) == object_hash(evidence['original_source_inputs']),
        'postlayout_diagnostic_source', 'Current physical, model, SDF, plan or original readiness inputs changed.')
    return copy.deepcopy(evidence['review_source_inputs'])


def run_postlayout(lvs, drc, layout, configuration, cancel_event=None):
    """Return a verified saved result; there is deliberately no process API here."""
    _, evidence = _configuration(configuration)
    inputs = source_inputs(layout, configuration)
    binding = evidence['original_source_binding']
    for name, record in (('layout', layout), ('drc', drc), ('lvs', lvs)):
        require(record.get('id') == binding.get(name + '_run_id')
            and object_hash(record) == binding.get(name + '_record_sha256')
            and record.get('revision_id') == binding.get('revision_id'),
            'postlayout_diagnostic_source', 'The saved diagnostic requires the exact original adopted S11/S12/S13 triple.')
    require(all(object_hash(inputs[key]) == object_hash(lvs['source_inputs'][key]) for key in PHYSICAL_INPUTS)
        and lvs['layout_record_sha256'] == drc['layout_record_sha256'] == object_hash(layout)
        and lvs['drc_record_sha256'] == object_hash(drc),
        'postlayout_diagnostic_source', 'Retain the complete physical source chain for saved diagnostic review.')
    result = copy.deepcopy(evidence['frozen_result'])
    original_configuration_sha = result.get('configuration_sha256')
    result.update(execution_scope=SCOPE, review_mode=SCOPE,
        execution_started_by_this_review=False, retained_execution=True,
        verification_supported=False, validation_status='Unsupported',
        origin='trusted_saved_postlayout_event_diagnostic_review',
        configuration_sha256=object_hash(configuration),
        retained_execution_configuration_sha256=original_configuration_sha,
        diagnostic_evidence_sha256=configuration['profile']['evidence_sha256'])
    if cancel_event is not None and cancel_event.is_set():
        result.update(status='Cancelled', validation_status='Not Checked')
        result['diagnostics'].append({'code': 'postlayout_event_review_cancelled', 'severity': 'info',
            'message': 'S14 saved event-diagnostic review was cancelled. This review started no tool process; original retained execution and diagnostics remain unchanged.'})
    return result


def validate_postlayout_result(result, lvs, drc, layout, configuration):
    raise DomainError('postlayout_unsupported',
        'Saved timed diagnostics remain Unsupported; integrity review cannot qualify or adopt S14.', 422)

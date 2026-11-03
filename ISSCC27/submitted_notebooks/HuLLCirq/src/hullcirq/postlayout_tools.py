"""Dispatch source-bound S14 methods without relabeling historical evidence.

The compatibility branch performs no execution. Saved diagnostic branches keep
their Unsupported status; functional simulation plus extracted STA uses its own
fixed adapter, artifacts and validation contract.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from .domain import DomainError
from .verification import object_hash
from . import physical_tools as physical
from . import lvs_tools
from .drc_tools import _safe
from .postlayout_testbench import timed_testbench

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / 'configs/postlayout_preflight_sky130_v1.json'
TEXT = 'text/plain; charset=utf-8'
require, sha, load = physical.require, physical.sha, physical.load
MODEL_FILES = {'cell_models': 'libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v',
               'primitives': 'libs.ref/sky130_fd_sc_hd/verilog/primitives.v'}


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def _descriptor(path, relative, origin, **extra):
    return {'relative_path': relative, 'sha256': sha(path), 'bytes': path.stat().st_size,
            'origin': origin, **extra}


def _configuration(configuration):
    require(type(configuration) is dict and type(configuration.get('profile')) is dict,
            'postlayout_configuration_invalid', 'Configure the explicit fixed readiness profile.')
    profile = configuration['profile']
    require(object_hash(profile) == object_hash(load(PROFILE))
            and profile.get('verification_supported') is False
            and profile.get('execution_scope') == 'compatibility_preflight_only',
            'postlayout_profile_invalid', 'Only the versioned compatibility-only profile is implemented.')
    require(configuration.get('verification_supported') is False
            and configuration.get('execution_scope') == 'compatibility_preflight_only',
            'postlayout_profile_invalid', 'Readiness configuration cannot enable dynamic verification.')
    report_path = ROOT / profile['readiness_report']
    require(report_path.is_file() and sha(report_path) == profile['readiness_report_sha256'],
            'postlayout_readiness_conflict', 'The fixed simulator investigation changed or is missing.')
    report = load(report_path)
    require(report.get('status') == 'Unsupported' and report.get('can_run_full_S14') is False
            and report.get('S14_accepted') is False and report.get('corner') == profile['corner'],
            'postlayout_readiness_conflict', 'Readiness is not a qualified original-job simulation.')
    manifest_path = Path(configuration.get('pdk_manifest', ''))
    pdk_root = Path(configuration.get('pdk_root', ''))
    require(manifest_path.is_absolute() and manifest_path.is_file() and pdk_root.is_absolute()
            and sha(manifest_path) == profile['pdk_manifest_sha256'],
            'postlayout_pdk_conflict', 'Use the original pinned PDK input manifest.')
    manifest = load(manifest_path)
    require(manifest.get('ciel_revision') == profile['pdk_revision']
            and Path(manifest.get('root', '')).resolve() == pdk_root.resolve(),
            'postlayout_pdk_conflict', 'PDK root and revision must match the frozen manifest.')
    for name, relative in MODEL_FILES.items():
        p = _safe(pdk_root, relative); original = manifest['files'][relative]
        observed = report['input_lineage'][Path(relative).name]
        require(p.stat().st_size == original['bytes'] == observed['bytes']
                and sha(p) == original['sha256'] == observed['sha256'],
                'postlayout_pdk_conflict', 'Original PDK timing model bytes changed: ' + name)
    working = Path(configuration.get('working_directory', ''))
    require(working.is_absolute() and working.resolve().is_relative_to((ROOT / '.work').resolve()),
            'postlayout_path_invalid', 'Readiness work must use a separate directory below HuLLCirq/.work.')
    return profile, report, manifest, pdk_root, working


def runtime_descriptor(configuration):
    if type(configuration) is dict and configuration.get('execution_scope') == 'post_route_functional_plus_sta':
        from . import postroute_tools
        return postroute_tools.runtime_descriptor(configuration)
    from . import postlayout_event_diagnostic_tools as event_diagnostic
    if event_diagnostic.handles(configuration):
        return event_diagnostic.runtime_descriptor(configuration)
    from . import postlayout_diagnostic_tools as diagnostic
    if diagnostic.handles(configuration):
        return diagnostic.runtime_descriptor(configuration)
    if configuration is None:
        return {'available': False, 'verification_supported': False,
                'execution_scope': 'compatibility_preflight_only',
                'reason': 'No S14 readiness configuration is set. Dynamic verification is unsupported.'}
    try:
        profile, _, _, _, _ = _configuration(configuration)
        return {'available': True, 'verification_supported': False,
                'execution_scope': 'compatibility_preflight_only', 'reason': profile['reason']}
    except (DomainError, OSError, ValueError, KeyError, TypeError) as error:
        return {'available': False, 'verification_supported': False,
                'execution_scope': 'compatibility_preflight_only',
                'reason': getattr(error, 'message', 'The fixed S14 readiness inputs are unavailable or inconsistent.')}


def source_inputs(layout, configuration):
    if type(configuration) is dict and configuration.get('execution_scope') == 'post_route_functional_plus_sta':
        from . import postroute_tools
        return postroute_tools.source_inputs(layout, configuration)
    from . import postlayout_event_diagnostic_tools as event_diagnostic
    if event_diagnostic.handles(configuration):
        return event_diagnostic.source_inputs(layout, configuration)
    from . import postlayout_diagnostic_tools as diagnostic
    if diagnostic.handles(configuration):
        return diagnostic.source_inputs(layout, configuration)
    profile, report, manifest, pdk_root, _ = _configuration(configuration)
    require(type(configuration.get('physical_runtime')) is dict
            and object_hash(configuration['physical_runtime']) == object_hash(layout['runtime_configuration']),
            'postlayout_source_conflict', 'S14 must inherit the exact S11 runtime and physical circuit.')
    inputs = lvs_tools.source_inputs(layout)
    folder = Path(layout['checks']['artifacts_directory']).resolve()
    final = next(e for e in layout['checks']['artifacts'] if e['id'] == 'final-state')
    state = physical.load_tool_json(_safe(folder, final['relative_path']))
    corner = profile['corner']
    require(type(state.get('sdf')) is dict and corner in state['sdf'],
            'postlayout_sdf_missing', 'The adopted S11 final-state must point to the selected SDF corner.')
    relative = lvs_tools._pointer_relative(state['sdf'][corner], folder)
    path = _safe(folder, relative)
    inputs['sdf'] = _descriptor(path, relative, 'original_S11_pointer_newly_observed_at_S14_not_retained_S11_hash', corner=corner)
    require(layout['id'] == report['source_layout_id'] and layout['revision_id'] == report['source_revision_id']
            and all(inputs[key]['sha256'] == report['input_lineage'][name]['sha256']
                    and inputs[key]['bytes'] == report['input_lineage'][name]['bytes']
                    for key, name in (('netlist', 'mapped_netlist.v'), ('sdf', 'layout.sdf'))),
            'postlayout_source_conflict', 'Readiness probes apply only to this exact saved physical source.')
    for name, relative in MODEL_FILES.items():
        inputs[name] = _descriptor(_safe(pdk_root, relative), relative,
            'original_pinned_PDK_bytes_newly_frozen_at_S14', pdk_revision=profile['pdk_revision'])
    plan = layout['verification_plan']
    require(object_hash(plan) == layout['verification_plan_sha256'],
            'postlayout_plan_conflict', 'Preserve the complete original GUI verification plan.')
    candidate, metadata = timed_testbench(plan, layout['settings'])
    for name, payload, origin in (
        ('timed_adapter', candidate.encode('utf-8'), 'unexecuted_development_assistant_timing_adapter'),
        ('verification_plan', _json_bytes(plan), 'unchanged_original_GUI_job_plan'),
        ('public_vectors', _json_bytes(plan['public_boundary_vectors']), 'inherited_vectors_not_all_monitored_after_flattening')):
        inputs[name] = {'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload), 'origin': origin}
    inputs['timed_adapter']['metadata'] = metadata
    return inputs


def run_postlayout(lvs, drc, layout, configuration, cancel_event=None):
    if type(configuration) is dict and configuration.get('execution_scope') == 'post_route_functional_plus_sta':
        from . import postroute_tools
        return postroute_tools.run_postlayout(lvs, drc, layout, configuration, cancel_event=cancel_event)
    from . import postlayout_event_diagnostic_tools as event_diagnostic
    if event_diagnostic.handles(configuration):
        return event_diagnostic.run_postlayout(lvs, drc, layout, configuration, cancel_event=cancel_event)
    from . import postlayout_diagnostic_tools as diagnostic
    if diagnostic.handles(configuration):
        return diagnostic.run_postlayout(lvs, drc, layout, configuration, cancel_event=cancel_event)
    profile, report, _, pdk_root, working = _configuration(configuration)
    inputs = source_inputs(layout, configuration)
    require(all(object_hash(inputs[k]) == object_hash(lvs['source_inputs'][k])
                for k in ('gds', 'def', 'netlist', 'powered_netlist'))
            and lvs['layout_record_sha256'] == drc['layout_record_sha256'] == object_hash(layout)
            and lvs['drc_record_sha256'] == object_hash(drc),
            'postlayout_source_conflict', 'Freeze one exact adopted S11/S12/S13 chain.')
    working.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='hullcirq-s14-preflight-', dir=working))
    plan = layout['verification_plan']; candidate, adapter = timed_testbench(plan, layout['settings'])
    artifacts = []
    def save(identifier, name, data=None, source=None, media='application/json'):
        dest = folder / name
        if source is not None:
            shutil.copyfile(source, dest)
        else:
            dest.write_bytes(data if isinstance(data, bytes) else _json_bytes(data))
        artifacts.append({'id': identifier, 'relative_path': name, 'sha256': sha(dest),
                          'bytes': dest.stat().st_size, 'content_type': media})
    base = Path(layout['checks']['artifacts_directory'])
    for key, identifier, name, media in (
        ('gds', 'input-gds', 'input.gds', 'application/octet-stream'),
        ('def', 'input-def', 'input.def', TEXT), ('netlist', 'input-netlist', 'input.nl.v', TEXT),
        ('powered_netlist', 'input-powered-netlist', 'input.pnl.v', TEXT), ('sdf', 'input-sdf', 'input.sdf', TEXT)):
        save(identifier, name, source=_safe(base, inputs[key]['relative_path']), media=media)
        require(artifacts[-1]['sha256'] == inputs[key]['sha256'] and artifacts[-1]['bytes'] == inputs[key]['bytes'],
                'postlayout_source_conflict', 'A physical input changed while freezing readiness files.')
    # The two original files remain separate within one retained, explicit bundle.
    models = {}
    for key, relative in MODEL_FILES.items():
        payload = _safe(pdk_root, relative).read_bytes()
        require(len(payload) == inputs[key]['bytes'] and hashlib.sha256(payload).hexdigest() == inputs[key]['sha256'],
                'postlayout_source_conflict', 'A PDK model changed while freezing readiness files.')
        # Decode without universal-newline conversion; re-encoding retains raw bytes.
        models[Path(relative).name] = {'sha256': inputs[key]['sha256'], 'bytes': inputs[key]['bytes'],
                                      'original_text': payload.decode('utf-8')}
    save('cell-models', 'cell-models.json', models)
    save('timed-testbench', 'candidate-timed-testbench.v', candidate.encode('utf-8'), media=TEXT)
    save('public-vectors', 'public-vectors.json', plan['public_boundary_vectors'])
    save('frozen-verification-plan', 'verification-plan.json', plan)
    save('configuration', 'configuration.json', configuration)
    binding = {'source_inputs': inputs, 'candidate_adapter': {**adapter, 'executed': False},
               'verification_plan_sha256': object_hash(plan),
               **{name + '_run_id': record['id'] for name, record in (('layout', layout), ('drc', drc), ('lvs', lvs))}}
    save('source-binding', 'source-binding.json', binding)
    save('tool-versions', 'tool-versions.json', {'investigated_simulator': report['simulator'],
         'simulator_started_by_this_check': False, 'readiness_report_sha256': profile['readiness_report_sha256']})
    unavailable = {'validation_status': 'Unsupported', 'executed': False, 'reason': profile['reason']}
    save('annotation-report', 'annotation-report.json', {**unavailable, 'coverage': report['annotation_coverage'],
         'syntactic_SDF_counts_not_annotation_success': report['SDF_syntactic_construct_counts']})
    save('timing-check-report', 'timing-check-report.json', {**unavailable, 'observed_HOLD_values_ns': report['HOLD_values_ns']})
    save('simulation-report', 'simulation-report.json', {**unavailable, 'original_job_run': False,
         'expected_outputs': plan['output_count'], 'observed_outputs': None, 'waveform': None,
         'candidate_timed_adapter_executed': False, 'simulator_readiness': report})
    cancelled = cancel_event is not None and cancel_event.is_set()
    result = {'status': 'Cancelled' if cancelled else 'Completed',
        'validation_status': 'Not Checked' if cancelled else 'Unsupported', 'executed': False,
        'execution_scope': 'compatibility_preflight_only', 'verification_supported': False,
        'origin': 'trusted_fixed_postlayout_preflight', 'commands': [], 'exit_code': None,
        'cleanup_unresolved': False, 'artifacts_directory': str(folder), 'artifacts': artifacts,
        **{name + '_run_id': record['id'] for name, record in (('layout', layout), ('drc', drc), ('lvs', lvs))},
        **{name + '_record_sha256': object_hash(record) for name, record in (('layout', layout), ('drc', drc), ('lvs', lvs))},
        'input_gds_sha256': inputs['gds']['sha256'], 'input_netlist_sha256': inputs['netlist']['sha256'],
        'input_sdf_sha256': inputs['sdf']['sha256'], 'configuration_sha256': object_hash(configuration),
        'verification_plan_sha256': object_hash(plan), **{k: plan[k] for k in ('vector_hash', 'testbench_sha256', 'public_boundary_vector_hash')},
        'checks': {'source_identity': {'validation_status': 'Passed', 'scope': 'raw source bytes and original plan only'},
                   'configuration': {'validation_status': 'Passed', 'scope': 'fixed compatibility-only profile'},
                   **{k: copy.deepcopy(unavailable) for k in ('annotation', 'functional', 'timing_checks')}},
        'metrics': {'original_expected_outputs': plan['output_count'], 'dynamic_observed_outputs': None,
                    'SDF_syntactic_counts_not_successful_annotation': report['SDF_syntactic_construct_counts']},
        'summary': {'scope': 'readiness only; no simulator process or original-job dynamic execution',
                    'reason': profile['reason'], 'candidate_timed_testbench': 'retained but unexecuted'},
        'diagnostics': [{'code': 'postlayout_dynamic_unsupported', 'severity': 'warning', 'message': profile['reason']}]}
    if cancelled:
        result['diagnostics'].append({'code': 'postlayout_preflight_cancelled', 'severity': 'info',
            'message': 'S14 readiness check was cancelled. No simulator process was started; unsupported capability reports remain retained.'})
    return result


def validate_postlayout_result(result, lvs, drc, layout, configuration):
    if type(configuration) is dict and configuration.get('execution_scope') == 'post_route_functional_plus_sta':
        from . import postroute_tools
        return postroute_tools.validate_postlayout_result(result, lvs, drc, layout, configuration)
    from . import postlayout_event_diagnostic_tools as event_diagnostic
    if event_diagnostic.handles(configuration):
        return event_diagnostic.validate_postlayout_result(result, lvs, drc, layout, configuration)
    from . import postlayout_diagnostic_tools as diagnostic
    if diagnostic.handles(configuration):
        return diagnostic.validate_postlayout_result(result, lvs, drc, layout, configuration)
    # Deliberately no actual-Passed implementation. Neither forged reports nor
    # changing configuration flags can promote these probes into S14 evidence.
    raise DomainError('postlayout_unsupported',
        'No qualified dynamic post-layout adapter is implemented. Readiness cannot be adopted as Passed.', 422)

"""Repeated fresh generic correction; legacy executed v1 remains immutable."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re

from .domain import DomainError
from .verification import content_hash, object_hash

ROOT = Path(__file__).resolve().parents[2]
PROFILE = 'hullcirq-sky130-generic-closure-v2'
PROFILE_FILE = 'physical_profile_sky130_generic_closure_v2.json'
LAUNCHER = 'route_closure_generic_v2.py'
FLOW = 'HuLLCirqGenericRouteClosureV2'
PROFILE_SHA = '4ad64ddddb393fa7d9f4a4ae0ec8e6e9816bd0231ab9d82040f2faa8e3afb75a'
LAUNCHER_SHA = '3f0bf202c97f091a006f28b973c4d44020c3d9548bb92ec0a4dfda6f70035607'
ORIGIN = 'explicit_GUI_repeated_generic_correction_unchanged_sources_and_signoff'
VERSION = 'hullcirq-generic-physical-correction-source-v2'
IMPLEMENTATION_KIND = 'fresh_generic_standard_electrical_closure'
UTILIZATIONS = (10, 15, 20, 25, 30, 35, 40, 45, 50)
SOURCE_FIELDS = ('revision_id', 'global_job_id', 'synthesis_run_id', 'netlist_run_id',
                 'global_rtl_sha256', 'source_manifest_sha256', 'settings_sha256', 'verification_plan_sha256')
BINDING_FIELDS = {'version', 'failed_stage', 'failed_run_id', 'failed_execution_sha256',
                  'layout_run_id', 'layout_record_sha256', 'previous_runtime_sha256',
                  'previous_bundle_sha256', 'attempt', 'core_utilization', *SOURCE_FIELDS}


def require(condition, message):
    if not condition:
        raise DomainError('generic_physical_retry_source', message, 409)


def is_generic(configuration):
    return (type(configuration) is dict and type(configuration.get('profile')) is dict
            and configuration['profile'].get('profile_version') == PROFILE)


def validate_configuration(configuration, settings, manifest):
    from .generic_global_verification import build_plan, handles
    from .store import strict_loads
    require(is_generic(configuration) and configuration.get('origin') == ORIGIN,
            'Use the separately versioned repeated generic correction profile.')
    require(not any(key in configuration for key in ('resume', 'block_plan', 'block_plan_sha256',
                'repair_source_binding', 'repair_checkpoint_inventory', 'generic_repair_source_binding')),
            'Repeated generic correction cannot reuse checkpoints or discard block fences.')
    require(type(manifest) is dict and handles(manifest.get('design'))
            and object_hash(manifest['design'].get('settings')) == object_hash(settings),
            'Retain the original generic cycle contract and complete settings.')
    binding = configuration.get('generic_retry_source_binding')
    require(type(binding) is dict and set(binding) == BINDING_FIELDS
            and binding.get('version') == VERSION and binding.get('failed_stage') in ('layout', 'post_layout_verification')
            and type(binding.get('attempt')) is int and 1 <= binding['attempt'] <= 256
            and type(binding.get('core_utilization')) is int and binding['core_utilization'] in UTILIZATIONS,
            'Retain the complete failed-execution binding and bounded explicit density.')
    require(all(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value)
                for key, value in binding.items() if key.endswith('_sha256'))
            and all(type(binding[key]) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,191}', binding[key])
                    for key in ('failed_run_id', 'layout_run_id', 'revision_id', 'global_job_id', 'synthesis_run_id', 'netlist_run_id')),
            'Saved source IDs and hashes must be exact, not paths or inferred names.')
    require(binding['source_manifest_sha256'] == object_hash(manifest)
            and binding['settings_sha256'] == object_hash(settings)
            and binding['verification_plan_sha256'] == object_hash(build_plan(manifest['design'])),
            'Independent expectations, original clock and complete source manifest cannot change during correction.')
    profile_path = ROOT / 'configs' / PROFILE_FILE
    launcher_path = ROOT / 'scripts' / LAUNCHER
    require(hashlib.sha256(profile_path.read_bytes()).hexdigest() == PROFILE_SHA
            and hashlib.sha256(launcher_path.read_bytes()).hexdigest() == LAUNCHER_SHA
            and object_hash(configuration['profile']) == object_hash(strict_loads(profile_path.read_text(encoding='utf-8'))),
            'The fixed repeated-correction recipe changed.')


def validate_source(configuration, rtl, manifest, settings):
    validate_configuration(configuration, settings, manifest)
    require(configuration['generic_retry_source_binding']['global_rtl_sha256'] == content_hash(rtl),
            'Map the exact adopted RTL, never a replacement or precomputed output.')


def prepare_configuration(layout, failed, working_directory, *, attempt, previous_bundle_sha256, core_utilization):
    from .physical_tools import configuration_projection
    from .postlayout_cleanup import execution_hash
    from .store import strict_loads
    runtime = copy.deepcopy(layout['runtime_configuration'])
    require(layout.get('record_hash') == object_hash({key: value for key, value in layout.items() if key != 'record_hash'})
            and layout.get('evidence_kind') == 'trusted_fixed_tool_execution'
            and layout.get('execution_status') == 'Completed'
            and layout.get('runtime_configuration_sha256') == object_hash(runtime),
            'Keep the exact complete source layout and its physical runtime.')
    require(runtime.get('profile', {}).get('profile_version') in ('hullcirq-sky130-generic-closure-v1', PROFILE)
            and not any(key in runtime for key in ('resume', 'block_plan', 'block_plan_sha256')),
            'Repeated correction starts from a generic mixed-placement correction, not an NPU or block checkpoint.')
    require(type(failed) is dict and failed.get('stage_id') in ('layout', 'post_layout_verification'),
            'Retain the exact source-bound complete failed S11 or S14 execution.')
    destination = Path(working_directory)
    require(destination.is_absolute(), 'Use a host-managed absolute correction directory.')
    destination = destination.resolve()
    original = Path(layout['checks']['artifacts_directory']).resolve()
    require(destination != ROOT / '.work' and destination.is_relative_to((ROOT / '.work').resolve())
            and not destination.is_relative_to(original) and not original.is_relative_to(destination),
            'New outputs must remain isolated from previous evidence and inside the managed workspace.')
    binding = {'version': VERSION, 'failed_stage': failed['stage_id'], 'failed_run_id': failed['id'],
        'failed_execution_sha256': execution_hash(failed), 'layout_run_id': layout['id'],
        'layout_record_sha256': layout['record_hash'], 'previous_runtime_sha256': object_hash(runtime),
        'previous_bundle_sha256': previous_bundle_sha256, 'attempt': attempt,
        'core_utilization': core_utilization, **{key: layout[key] for key in SOURCE_FIELDS}}
    runtime.pop('generic_repair_source_binding', None)
    runtime.pop('generic_retry_source_binding', None)
    runtime.update(origin=ORIGIN, working_directory=str(destination), generic_retry_source_binding=binding,
                   profile=strict_loads((ROOT / 'configs' / PROFILE_FILE).read_text(encoding='utf-8')))
    validate_source(runtime, layout['global_rtl'], layout['source_manifest'], layout['settings'])
    configuration_projection(layout['settings'], runtime, layout['source_manifest'])
    return runtime

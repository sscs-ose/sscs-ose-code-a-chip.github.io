"""Source-bound fresh physical correction for explicit generic cycle plans.

This recipe does not resume or rename an older NPU checkpoint. Preparation is
read-only; an explicit later S11 action performs fresh mapping and routing.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re

from .domain import DomainError
from .verification import content_hash, object_hash

ROOT = Path(__file__).resolve().parents[2]
PROFILE = 'hullcirq-sky130-generic-closure-v1'
PROFILE_FILE = 'physical_profile_sky130_generic_closure_v1.json'
LAUNCHER = 'route_closure_generic_v1.py'
FLOW = 'HuLLCirqGenericRouteClosureV1'
PROFILE_SHA = 'aaa3a6fd30afc052ace7e9e4d6953d4c6f48300e51f3e05ed4972bdc2c2792c3'
LAUNCHER_SHA = 'cbc39ce8333f864f510ed811509f66c29732d3790aab07ebd936a1bdb4bc66f5'
BINDING_VERSION = 'hullcirq-generic-physical-correction-source-v1'
IMPLEMENTATION_KIND = 'fresh_generic_standard_electrical_closure'
ORIGIN = 'explicit_GUI_generic_electrical_correction_original_sources_and_signoff_constraints_unchanged'
BINDING_FIELDS = {'version', 'failed_s14_id', 'failed_s14_execution_sha256',
    'layout_run_id', 'layout_record_sha256', 'revision_id', 'global_job_id',
    'synthesis_run_id', 'netlist_run_id', 'global_rtl_sha256',
    'source_manifest_sha256', 'settings_sha256', 'verification_plan_sha256',
    'original_runtime_configuration_sha256'}


def require(condition, message):
    if not condition:
        raise DomainError('generic_physical_repair_source', message, 409)


def is_generic(configuration):
    return (type(configuration) is dict and type(configuration.get('profile')) is dict
            and configuration['profile'].get('profile_version') in (PROFILE, 'hullcirq-sky130-generic-closure-v2'))


def recipe_for(configuration):
    if configuration.get('profile', {}).get('profile_version') == 'hullcirq-sky130-generic-closure-v2':
        from . import physical_repair_generic_v2
        return physical_repair_generic_v2
    import sys
    return sys.modules[__name__]


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_configuration(configuration, settings, manifest):
    """Validate only this new recipe; legacy physical recipes are independent."""
    if recipe_for(configuration).__name__ != __name__:
        return recipe_for(configuration).validate_configuration(configuration, settings, manifest)
    from .generic_global_verification import build_plan, handles
    from .store import strict_loads
    require(is_generic(configuration) and configuration.get('origin') == ORIGIN,
            'Use the explicit versioned generic physical correction profile.')
    require(not any(key in configuration for key in ('resume', 'block_plan', 'block_plan_sha256',
                'repair_source_binding', 'repair_checkpoint_inventory')),
            'Fresh generic correction cannot reuse checkpoints or silently discard block fences.')
    require(type(manifest) is dict and handles(manifest.get('design')),
            'Generic physical correction requires its original saved generic cycle-vector design.')
    require(object_hash(manifest['design'].get('settings')) == object_hash(settings),
            'Keep the original complete saved settings, including clock/reset names and polarity.')
    binding = configuration.get('generic_repair_source_binding')
    require(type(binding) is dict and set(binding) == BINDING_FIELDS
            and binding.get('version') == BINDING_VERSION,
            'Retain the exact failed S14 and adopted physical source binding.')
    require(all(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value)
                for key, value in binding.items() if key.endswith('_sha256'))
            and all(type(binding[key]) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,191}', binding[key])
                    for key in ('failed_s14_id', 'layout_run_id', 'revision_id', 'global_job_id',
                                'synthesis_run_id', 'netlist_run_id')),
            'Source IDs and original hashes must be complete, not paths or inferred names.')
    require(binding['source_manifest_sha256'] == object_hash(manifest)
            and binding['settings_sha256'] == object_hash(settings)
            and binding['verification_plan_sha256'] == object_hash(build_plan(manifest['design'])),
            'The correction must retain the exact original source, independent vectors and clock.')
    profile_path = ROOT / 'configs' / PROFILE_FILE
    launcher_path = ROOT / 'scripts' / LAUNCHER
    require(profile_path.is_file() and launcher_path.is_file()
            and _sha(profile_path) == PROFILE_SHA and _sha(launcher_path) == LAUNCHER_SHA
            and object_hash(configuration['profile']) == object_hash(strict_loads(profile_path.read_text(encoding='utf-8'))),
            'The fixed generic correction profile or launcher bytes changed.')


def validate_source(configuration, rtl, manifest, settings):
    if recipe_for(configuration).__name__ != __name__:
        return recipe_for(configuration).validate_source(configuration, rtl, manifest, settings)
    validate_configuration(configuration, settings, manifest)
    require(configuration['generic_repair_source_binding']['global_rtl_sha256'] == content_hash(rtl),
            'Fresh correction must map the exact adopted integration RTL, not a replacement.')


def prepare_configuration(layout, working_directory, failed_s14):
    """Pure builder after strict actual-failure/current-adoption validation."""
    from .generic_global_verification import build_plan
    from .physical_tools import configuration_projection
    from .postlayout_cleanup import execution_hash
    from .store import strict_loads
    original = {key: value for key, value in layout.items() if key not in ('freshness', 'artifacts')}
    require(original.get('record_hash') == object_hash({key: value for key, value in original.items() if key != 'record_hash'})
            and original.get('execution_status') == 'Completed' and original.get('validation_status') == 'Passed'
            and original.get('review_status') == 'Accepted' and original.get('evidence_kind') == 'trusted_fixed_tool_execution',
            'Prepare fresh correction only from the unchanged actual adopted S11 record.')
    require(type(failed_s14) is dict and failed_s14.get('runtime_configuration', {}).get('profile_version')
            == 'hullcirq-postroute-functional-sta-v4'
            and failed_s14.get('layout_run_id') == original.get('id')
            and object_hash(failed_s14.get('layout_snapshot')) == object_hash(original),
            'Generic correction requires the source-bound actual generic v4 S14 failure.')
    runtime = copy.deepcopy(original['runtime_configuration'])
    require(not is_generic(runtime) and not any(key in runtime for key in ('resume', 'block_plan', 'block_plan_sha256')),
            'This first generic correction requires a fresh mixed layout; block fences and previous corrections cannot be discarded.')
    require(original.get('runtime_configuration_sha256') == object_hash(runtime),
            'Keep the original physical runtime identity.')
    configuration_projection(original['settings'], runtime, original['source_manifest'])
    require(object_hash(original['verification_plan']) == object_hash(build_plan(original['source_manifest']['design']))
            == original['verification_plan_sha256'], 'The original independent generic verification plan changed.')
    require(isinstance(working_directory, (str, Path)) and Path(working_directory).is_absolute(),
            'Use a host-managed absolute fresh correction directory.')
    destination = Path(working_directory).resolve()
    work = (ROOT / '.work').resolve()
    old = Path(original['checks']['artifacts_directory']).resolve()
    require(destination != work and destination.is_relative_to(work)
            and not destination.is_relative_to(old) and not old.is_relative_to(destination),
            'Keep fresh correction outputs isolated from the original saved physical result.')
    binding = {'version': BINDING_VERSION, 'failed_s14_id': failed_s14['id'],
        'failed_s14_execution_sha256': execution_hash(failed_s14),
        'layout_run_id': original['id'], 'layout_record_sha256': original['record_hash'],
        **{key: original[key] for key in ('revision_id', 'global_job_id', 'synthesis_run_id', 'netlist_run_id',
            'global_rtl_sha256', 'source_manifest_sha256', 'settings_sha256', 'verification_plan_sha256')},
        'original_runtime_configuration_sha256': object_hash(runtime)}
    runtime.update(origin=ORIGIN, working_directory=str(destination),
        profile=strict_loads((ROOT / 'configs' / PROFILE_FILE).read_text(encoding='utf-8')),
        generic_repair_source_binding=binding)
    validate_source(runtime, original['global_rtl'], original['source_manifest'], original['settings'])
    configuration_projection(original['settings'], runtime, original['source_manifest'])
    return runtime

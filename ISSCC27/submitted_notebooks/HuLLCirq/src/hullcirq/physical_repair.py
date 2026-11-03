"""Bounded reuse of fixed original-job checkpoints for standard route repair.

The fixed checkpoint is copied, never edited. The new run still executes actual
global routing, repair, detailed routing, extraction and stream-out. This is not
fresh synthesis and is not saved-output revalidation.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path, PurePosixPath
import re

from .verification import object_hash, _wsl_path

PROFILE_VERSION = 'hullcirq-sky130-route-repair-v2'
PROFILE_NPU2 = 'hullcirq-sky130-route-repair-npu2v1'
PROFILE_NPU2_RETRY = 'hullcirq-sky130-route-repair-npu2v2'
PROFILE_NPU2_FINAL = 'hullcirq-sky130-route-repair-npu2v3'
PROFILE_VERSIONS = (PROFILE_VERSION, 'hullcirq-sky130-route-repair-v3', 'hullcirq-sky130-route-repair-v4', 'hullcirq-sky130-route-repair-v5', 'hullcirq-sky130-route-repair-v6', PROFILE_NPU2, PROFILE_NPU2_RETRY, PROFILE_NPU2_FINAL)
STATE_SHA = '5d32d1eff9edb0d87e56e996e50c52e463610b0979230812ef076939eeb42255'
INPUT_SHA = '58561947a9cb4146de098dcf012c06f866cd21ced00c33ef3b08edebaab95d22'
START_STEP = 'OpenROAD.CTS'
V5_STATE_SHA = '2320f4c3c747e650bb72bf0290b538bf854c51837214e14716f6ea36b959c0e0'
V5_INPUT_SHA = 'edf7f5455e022bd95b4a6f19547f497330c0e8050c841fe2984dc4001ddb92e9'
V6_STATE_SHA = 'c10e8e244916f24538c08e85091f8cafd9d1b8c0712ab7250061f078f3a3909a'
V6_INPUT_SHA = '53a45406df085ef5ce07f7e79bec33175da227fbb749f6937fd9b266560aa787'
V5_LAUNCHER_SHA = '4b863a00b212d4cabe94e268fae3857ac345f0a92df705152bb2c121eaca84cc'
NPU2_STATE_SHA = '43a86aab6073e22c325e167fab44e7a7cf114a7cf2ee76f44d8c589ab5b1efe8'
NPU2_INPUT_SHA = 'c058e9ef5ce214a4814975f96b5c72cf88a6b7b64151620f7d9a5c58c7e428cc'
NPU2_CHECKPOINT = 'runs/physical/34-openroad-detailedplacement/state_out.json'
NPU2_SOURCE_BINDING = {
    'layout_run_id': 'physical-workflow-7490fdd470a941c9b097033613816d72',
    'layout_record_sha256': 'cb67921cea5616107a93c9a20d05c8fd25b624d5e98adfd9069961de8b40c88f',
    'revision_id': 'revision-d5698859b71f4e6ebe8f4d396e14c03c',
    'global_job_id': 'global-generation-a8cda8d2a55e4c1baac70c6c110e3c56',
    'global_rtl_sha256': '3059922dbaca9f784b7769692d6657102ebcc2dd35b090f1d7f2c7c9ff0d4006',
    'source_manifest_sha256': 'c18591e13c41d2a637dd44ee88f13cce1867de515a79f272d205d1088211b145',
    'settings_sha256': '5067d8e4f26b3cf07ba6593a10a796b77bb79b93c0a8fb9dde4a5baf5bcd2a16',
    'verification_plan_sha256': '5ccc97bfa95e84307362a892ac541b443f4af99f98e2316496235c91a7e498a1',
    'original_runtime_configuration_sha256': '841073cef717f777a5d129b67e1aca41194ac8d973d71b6ceb0d67177c1c5103',
    'checkpoint_view_hash_origin': 'observed_at_repair_snapshot_not_original_S11_retained_hash',
}
NPU2_RETRY_STATE_SHA = '07ed6c04f5d5b08cabd0313815cde9eebc0710e79820e83db693a76b5ebf8fe8'
NPU2_RETRY_INPUT_SHA = 'da946574bb920aafee4b022fc1894f1d7590a294b3020d9b0113e44f1e9eb538'
NPU2_RETRY_CHECKPOINT = 'runs/physical/05-openroad-globalrouting/state_out.json'
NPU2_RETRY_LAUNCHER_SHA = 'd9c6a709eea2360afa8386fecc6f4ae5ca98d434fb6eca9471f69ccd27baf24f'
NPU2_RETRY_INVENTORY_SHA = '6b89729901418cf385925ca47bcc1b6c2968127e2324559c1ce366a4af226e7e'
NPU2_RETRY_INVENTORY_ORIGIN = 'observed_after_first_repair_failure_before_retry_not_original_retained_hash'
NPU2_RETRY_SOURCE_BINDING = {
    **{key: value for key, value in NPU2_SOURCE_BINDING.items()
       if key not in ('layout_run_id', 'layout_record_sha256', 'original_runtime_configuration_sha256')},
    'layout_run_id': 'physical-workflow-124ca1012520439c97ca35b56518824d',
    'layout_record_sha256': '68f07fd76cc1443175ab9d496ef588886732f822429685c1491c04ac0e68bca8',
    'layout_record_hash_origin': 'original_failed_terminal_record_before_review_metadata_updates',
    'layout_execution_sha256': '319be892ec86a37d70c10e89fa3d90bf561e38be7c63692351dda49e4e68ac72',
    'original_runtime_configuration_sha256': '7986f55ca0dd75f9f15e6f77c5092e53c1e63ede6b13e5178876dce86c19350c',
    'checkpoint_view_hash_origin': NPU2_RETRY_INVENTORY_ORIGIN,
}
NPU2_FINAL_STATE_SHA = '685fdf31a1ceb18f928f5ca18769b0c9badb2a01d90e2d5302d7923e348b2f54'
NPU2_FINAL_INPUT_SHA = 'c74d6ce016d2558ff43ed075df3b289b53fb1a19c2f1d14e3eea380f077e4829'
NPU2_FINAL_CHECKPOINT = 'runs/physical/05-openroad-stamidpnr-3/state_out.json'
NPU2_FINAL_STEP = 'HuLLCirq.RepairDesignAfterTimingV3'
NPU2_FINAL_LAUNCHER_SHA = '492a28fcf8b5d6f8f016e4d61e502ced358c1b66c1535ac6ced57a5ffb6b45f4'
NPU2_FINAL_INVENTORY_SHA = '2bbaa7a5cd7910623f362310a8d71ce31aaa07dca533f2a69e7f2dd31f4af5c8'
NPU2_FINAL_INVENTORY_ORIGIN = 'observed_after_second_repair_failure_before_final_not_original_retained_hash'
NPU2_FINAL_SOURCE_BINDING = {
    **{key: value for key, value in NPU2_SOURCE_BINDING.items()
       if key not in ('layout_run_id', 'layout_record_sha256', 'original_runtime_configuration_sha256')},
    'layout_run_id': 'physical-workflow-8c0636d426f3410ba947195343216b3f',
    'layout_record_sha256': '93126a0955c88a4681b208fa77ce89669ef017ce1fde2e672d63acfdcf312840',
    'layout_record_hash_origin': 'observed_after_GUI_request_changes_not_original_terminal_record_hash',
    'layout_execution_sha256': '164901b4702ab9048c3204cb04b74d31499495d28d0c1ab9009b7a2ec9214b2b',
    'original_runtime_configuration_sha256': '343fec48e5be83cefe3b329f7b927880b4be10cf5beb464dec74010e58fbd695',
    'checkpoint_view_hash_origin': NPU2_FINAL_INVENTORY_ORIGIN,
}


def uses_closure_flow(configuration):
    return configuration.get('profile', {}).get('profile_version') in ('hullcirq-sky130-route-repair-v5', 'hullcirq-sky130-route-repair-v6', PROFILE_NPU2, PROFILE_NPU2_RETRY, PROFILE_NPU2_FINAL)


def closure_launcher(configuration):
    """Keep historical launchers immutable when a new repair flow is selected."""
    if configuration.get('profile', {}).get('profile_version') == PROFILE_NPU2_FINAL:
        return 'route_closure_npu2_v3.py', 'HuLLCirqNpu2RouteClosureV3', NPU2_FINAL_LAUNCHER_SHA
    if configuration.get('profile', {}).get('profile_version') == PROFILE_NPU2_RETRY:
        return 'route_closure_npu2_v2.py', 'HuLLCirqNpu2RouteClosureV2', NPU2_RETRY_LAUNCHER_SHA
    return 'route_closure_v5.py', 'HuLLCirqRouteClosureV5', V5_LAUNCHER_SHA


def _retry_inventory_descriptor(configuration=None):
    if (configuration or {}).get('profile', {}).get('profile_version') == PROFILE_NPU2_FINAL:
        return {'relative_path': 'configs/npu2_final_checkpoint_inventory.json',
                'sha256': NPU2_FINAL_INVENTORY_SHA, 'origin': NPU2_FINAL_INVENTORY_ORIGIN}
    return {'relative_path': 'configs/npu2_retry_checkpoint_inventory.json',
            'sha256': NPU2_RETRY_INVENTORY_SHA, 'origin': NPU2_RETRY_INVENTORY_ORIGIN}


def _retry_checkpoint_inventory(configuration=None):
    """Load fixed pre-retry observations, never re-pin current changed bytes."""
    from .physical_tools import ROOT, load, require, sha
    final = (configuration or {}).get('profile', {}).get('profile_version') == PROFILE_NPU2_FINAL
    descriptor = _retry_inventory_descriptor(configuration)
    binding = NPU2_FINAL_SOURCE_BINDING if final else NPU2_RETRY_SOURCE_BINDING
    state_sha, input_sha = (NPU2_FINAL_STATE_SHA, NPU2_FINAL_INPUT_SHA) if final else (NPU2_RETRY_STATE_SHA, NPU2_RETRY_INPUT_SHA)
    checkpoint = NPU2_FINAL_CHECKPOINT if final else NPU2_RETRY_CHECKPOINT
    path = ROOT / descriptor['relative_path']
    require(path.is_file() and sha(path) == descriptor['sha256'],
            'physical_resume_inventory', 'The fixed pre-retry checkpoint inventory changed.')
    inventory = load(path)
    require(inventory.get('schema') == ('hullcirq-npu2-final-checkpoint-inventory-v1' if final else 'hullcirq-npu2-retry-checkpoint-inventory-v1')
            and inventory.get('origin') == descriptor['origin']
            and inventory.get('source_run_id') == binding['layout_run_id']
            and inventory.get('source_execution_sha256') == binding['layout_execution_sha256']
            and inventory.get('checkpoint_relative_path') == checkpoint
            and inventory.get('checkpoint_sha256') == state_sha
            and inventory.get('input_manifest_sha256') == input_sha
            and type(inventory.get('files')) is list and bool(inventory['files']),
            'physical_resume_inventory', 'Retain the exact source and observation origin of the retry checkpoint inventory.')
    names = set()
    for item in inventory['files']:
        require(type(item) is dict and set(item) == {'relative_path', 'sha256', 'bytes'}
                and type(item['relative_path']) is str and bool(item['relative_path'])
                and not PurePosixPath(item['relative_path']).is_absolute()
                and not any(part in ('.', '..') for part in PurePosixPath(item['relative_path']).parts)
                and not any(char in item['relative_path'] for char in ('\\', ':'))
                and item['relative_path'] not in names
                and type(item['bytes']) is int and item['bytes'] > 0
                and type(item['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', item['sha256']),
                'physical_resume_inventory', 'Retry view pins require unique contained relative paths and exact raw hashes.')
        names.add(item['relative_path'])
    return inventory


def _validate_retry_views(state, root, configuration=None):
    from .physical_tools import require, sha
    expected = {item['relative_path']: item for item in _retry_checkpoint_inventory(configuration)['files']}
    observed = set()
    root = Path(root).resolve()

    def visit(value):
        if value is None:
            return
        if type(value) is dict:
            for item in value.values():
                visit(item)
            return
        require(type(value) is str, 'physical_resume_state', 'A retry checkpoint view must be a path or corner map.')
        path = _native(value).resolve()
        require(path.is_relative_to(root) and path.is_file(),
                'physical_resume_path', 'Every retry view must remain within its observed first-repair run.')
        relative = path.relative_to(root).as_posix()
        item = expected.get(relative)
        require(item is not None and path.stat().st_size == item['bytes'] and sha(path) == item['sha256'],
                'physical_resume_inventory', 'A retry checkpoint view changed after its fixed pre-retry observation: ' + relative)
        observed.add(relative)

    for key, value in state.items():
        if key != 'metrics':
            visit(value)
    require(observed == set(expected), 'physical_resume_inventory', 'The retry inventory must cover every checkpoint view exactly.')


def _validate_retry_copy_pins(configuration, manifest):
    from .physical_tools import require
    descriptor = _retry_inventory_descriptor(configuration)
    expected = {'resume-files/' + item['relative_path']: item for item in _retry_checkpoint_inventory(configuration)['files']}
    require(manifest.get('checkpoint_inventory_sha256') == descriptor['sha256']
            and manifest.get('checkpoint_view_hash_origin') == descriptor['origin']
            and set(manifest['files']) == set(expected),
            'physical_resume_inventory', 'Retain the fixed pre-retry inventory binding and complete copied view set.')
    root = Path(configuration['resume']['source_input_manifest_path']).resolve().parent
    for relative, item in expected.items():
        copied = manifest['files'][relative]
        require(copied.get('bytes') == item['bytes'] and copied.get('sha256') == item['sha256']
                and type(copied.get('original_path')) is str
                and _native(copied['original_path']).resolve() == (root / item['relative_path']).resolve(),
                'physical_resume_inventory', 'A copied retry view differs from its fixed pre-retry pin: ' + relative)


def checkpoint_identity(configuration):
    version = configuration.get('profile', {}).get('profile_version')
    if version == PROFILE_NPU2_FINAL:
        return NPU2_FINAL_STATE_SHA, NPU2_FINAL_INPUT_SHA, NPU2_FINAL_STEP
    if version == PROFILE_NPU2_RETRY:
        return NPU2_RETRY_STATE_SHA, NPU2_RETRY_INPUT_SHA, 'OpenROAD.RepairDesignPostGRT'
    if version == PROFILE_NPU2:
        return NPU2_STATE_SHA, NPU2_INPUT_SHA, START_STEP
    if version == 'hullcirq-sky130-route-repair-v6':
        return V6_STATE_SHA, V6_INPUT_SHA, 'OpenROAD.RepairDesignPostGRT'
    if version == 'hullcirq-sky130-route-repair-v5':
        return V5_STATE_SHA, V5_INPUT_SHA, 'OpenROAD.RepairDesignPostGRT'
    return STATE_SHA, INPUT_SHA, START_STEP


def implementation_kind(configuration):
    return 'resumed_post_GRT_route_repair' if checkpoint_identity(configuration)[2] != START_STEP else 'resumed_pre_CTS_route_repair'


def is_repair(configuration):
    profile = configuration.get('profile')
    return type(profile) is dict and profile.get('profile_version') in PROFILE_VERSIONS


def has_pnr_headroom(configuration):
    return configuration.get('profile', {}).get('profile_version') in ('hullcirq-sky130-route-repair-v4', 'hullcirq-sky130-route-repair-v5', 'hullcirq-sky130-route-repair-v6', PROFILE_NPU2, PROFILE_NPU2_RETRY, PROFILE_NPU2_FINAL)


def pnr_sdc(original):
    """Stricter optimization target; original signoff SDC remains unchanged."""
    return original + b'\n# HuLLCirq v4: reserve fanout headroom for antenna diodes during PnR only.\nset_max_fanout 8 [current_design]\n'


def validate_configuration(configuration):
    from .physical_tools import require
    value = configuration.get('resume')
    state_sha, input_sha, start_step = checkpoint_identity(configuration)
    require(type(value) is dict and set(value) == {'initial_state_path', 'initial_state_sha256',
            'source_input_manifest_path', 'source_input_manifest_sha256', 'from_step'}
            and value['initial_state_sha256'] == state_sha
            and value['source_input_manifest_sha256'] == input_sha
            and value['from_step'] == start_step
            and all(type(value[k]) is str and Path(value[k]).is_absolute()
                    for k in ('initial_state_path', 'source_input_manifest_path')),
            'physical_resume_configuration', 'Resume only the versioned fixed original-job checkpoint and its exact source manifest.')
    if configuration.get('profile', {}).get('profile_version') == PROFILE_NPU2:
        require(object_hash(configuration.get('repair_source_binding')) == object_hash(NPU2_SOURCE_BINDING),
                'physical_resume_source', 'The NPU2 repair profile must retain its exact adopted original layout and source identity.')
    if configuration.get('profile', {}).get('profile_version') == PROFILE_NPU2_RETRY:
        require(object_hash(configuration.get('repair_source_binding')) == object_hash(NPU2_RETRY_SOURCE_BINDING),
                'physical_resume_source', 'The NPU2 retry must retain the exact executed first-repair source independently of later review metadata.')
        require(object_hash(configuration.get('repair_checkpoint_inventory')) == object_hash(_retry_inventory_descriptor()),
                'physical_resume_inventory', 'The NPU2 retry runtime must bind the fixed pre-retry view inventory.')
    if configuration.get('profile', {}).get('profile_version') == PROFILE_NPU2_FINAL:
        require(object_hash(configuration.get('repair_source_binding')) == object_hash(NPU2_FINAL_SOURCE_BINDING),
                'physical_resume_source', 'Retain the exact executed second-repair source independently of review metadata.')
        require(object_hash(configuration.get('repair_checkpoint_inventory')) == object_hash(_retry_inventory_descriptor(configuration)),
                'physical_resume_inventory', 'Bind the fixed observed post-timing view inventory.')


def prepare_npu2_configuration(layout, working_directory):
    """Prepare only the fixed adopted NPU2 checkpoint; execute and write nothing.

    The caller must additionally check that this original layout is current in
    its active project and that the selected S14 failure refers to it. Runtime
    paths come from the adopted record, never from browser-provided paths.
    """
    from .physical_tools import ROOT, configuration_projection, load, load_tool_json, require, sha
    require(type(layout) is dict and layout.get('freshness', 'Current') == 'Current',
            'physical_resume_source', 'Prepare repair only from the current adopted original NPU2 layout.')
    # Public read views add these two presentation fields to the raw record.
    original = {key: value for key, value in layout.items() if key not in ('freshness', 'artifacts')}
    binding = NPU2_SOURCE_BINDING
    require(original.get('id') == binding['layout_run_id']
            and original.get('record_hash') == binding['layout_record_sha256']
            and object_hash({key: value for key, value in original.items() if key != 'record_hash'}) == binding['layout_record_sha256']
            and original.get('stage_id') == 'layout' and original.get('execution_status') == 'Completed'
            and original.get('validation_status') == 'Passed' and original.get('review_status') == 'Accepted'
            and original.get('evidence_kind') == 'trusted_fixed_tool_execution'
            and all(original.get(key) == binding[key] for key in ('revision_id', 'global_job_id', 'global_rtl_sha256',
                    'source_manifest_sha256', 'settings_sha256', 'verification_plan_sha256')),
            'physical_resume_source', 'This repair version accepts only the unchanged adopted original NPU2 record.')
    runtime = copy.deepcopy(original['runtime_configuration'])
    require(original.get('runtime_configuration_sha256') == object_hash(runtime) == binding['original_runtime_configuration_sha256'],
            'physical_resume_source', 'Retain the original adopted physical runtime identity.')
    configuration_projection(original['settings'], runtime, original['source_manifest'])
    result = original['checks']
    require(type(result) is dict and type(result.get('artifacts_directory')) is str
            and Path(result['artifacts_directory']).is_absolute(),
            'physical_resume_path', 'The adopted layout must retain its absolute physical run directory.')
    root = Path(result['artifacts_directory']).resolve()
    require(root.is_relative_to((ROOT / '.work').resolve()) and root.name.startswith('hullcirq-layout-')
            and root.parent == Path(runtime['working_directory']).resolve(),
            'physical_resume_path', 'The original checkpoint must remain in its recorded isolated physical run.')
    state = (root / NPU2_CHECKPOINT).resolve()
    inputs = (root / 'input-manifest.json').resolve()
    require(state.is_relative_to(root) and inputs.is_relative_to(root),
            'physical_resume_path', 'The original checkpoint and input manifest must stay within the adopted run.')
    for relative, expected, entries, field in (
            (NPU2_CHECKPOINT, NPU2_STATE_SHA, result.get('retained_files'), 'relative_path'),
            ('input-manifest.json', NPU2_INPUT_SHA, result.get('artifacts'), 'relative_path')):
        require(type(entries) is list, 'physical_resume_source', 'Retain the original checkpoint/input file descriptors.')
        matches = [entry for entry in entries if type(entry) is dict and entry.get(field) == relative]
        path = (root / relative).resolve()
        require(len(matches) == 1 and matches[0].get('sha256') == expected
                and path.is_file() and type(matches[0].get('bytes')) is int
                and matches[0]['bytes'] == path.stat().st_size and sha(path) == expected,
                'physical_resume_source', 'The adopted checkpoint or source-input bytes changed.')
    frozen_inputs = load(inputs)
    _source_identity(frozen_inputs, original['global_rtl'], original['source_manifest'], original['settings'])
    require(object_hash(frozen_inputs.get('runtime_configuration')) == binding['original_runtime_configuration_sha256'],
            'physical_resume_source', 'The checkpoint input manifest must retain the original runtime.')

    def preflight_view(value):
        if value is None:
            return
        if type(value) is dict:
            for item in value.values():
                preflight_view(item)
            return
        require(type(value) is str, 'physical_resume_state', 'A checkpoint view must be a file path or corner map.')
        path = _native(value).resolve()
        require(path.is_relative_to(root) and path.is_file(),
                'physical_resume_path', 'Every checkpoint view must remain available within its original adopted run.')

    for key, value in load_tool_json(state).items():
        if key != 'metrics':
            preflight_view(value)
    require(isinstance(working_directory, (str, Path)) and Path(working_directory).is_absolute(),
            'physical_repair_destination', 'Use a host-managed absolute repair working directory.')
    destination = Path(working_directory).resolve()
    require(destination.is_relative_to((ROOT / '.work').resolve()) and not destination.is_relative_to(root),
            'physical_repair_destination', 'Keep new repair runs below the host workspace and outside the original adopted run.')
    runtime.update(origin='gui_fixed_current_NPU2_physical_repair_original_GUI_job_and_signoff_constraints_unchanged',
                   working_directory=str(destination),
                   profile=load(ROOT / 'configs/physical_profile_sky130_repair_npu2v1.json'),
                   repair_source_binding=copy.deepcopy(binding),
                   resume={'initial_state_path': str(state), 'initial_state_sha256': NPU2_STATE_SHA,
                           'source_input_manifest_path': str(inputs), 'source_input_manifest_sha256': NPU2_INPUT_SHA,
                           'from_step': START_STEP})
    configuration_projection(original['settings'], runtime, original['source_manifest'])
    return runtime


def prepare_npu2_retry_configuration(failed_layout, working_directory):
    """Prepare the fixed failed first-repair checkpoint without writes or EDA.

    The caller additionally validates the full actual failed-tool proof and
    current active-project source. Review-only updates may change the raw
    record hash, so authority is the fixed execution hash plus self-checksum.
    """
    return _prepare_failed_npu2_configuration(failed_layout, working_directory, final=False)


def prepare_npu2_final_configuration(failed_layout, working_directory):
    """Read-only preparation of one extra standard electrical-repair pass.

    This is not a completed correction. The caller must validate the complete
    actual failed-tool proof and unchanged active source before GUI preparation.
    """
    return _prepare_failed_npu2_configuration(failed_layout, working_directory, final=True)


def _prepare_failed_npu2_configuration(failed_layout, working_directory, *, final):
    from .physical_tools import ROOT, configuration_projection, load, load_tool_json, require, sha
    from .postlayout_cleanup import execution_hash
    require(type(failed_layout) is dict and failed_layout.get('freshness', 'Current') == 'Current',
            'physical_resume_source', 'Prepare retry only from the current failed first NPU2 repair.')
    original = {key: value for key, value in failed_layout.items() if key not in ('freshness', 'artifacts')}
    binding = NPU2_FINAL_SOURCE_BINDING if final else NPU2_RETRY_SOURCE_BINDING
    state_sha = NPU2_FINAL_STATE_SHA if final else NPU2_RETRY_STATE_SHA
    input_sha = NPU2_FINAL_INPUT_SHA if final else NPU2_RETRY_INPUT_SHA
    checkpoint = NPU2_FINAL_CHECKPOINT if final else NPU2_RETRY_CHECKPOINT
    target_version = PROFILE_NPU2_FINAL if final else PROFILE_NPU2_RETRY
    target = {'profile': {'profile_version': target_version}}
    require(original.get('id') == binding['layout_run_id']
            and original.get('record_hash') == object_hash({key: value for key, value in original.items() if key != 'record_hash'})
            and execution_hash(original) == binding['layout_execution_sha256']
            and original.get('stage_id') == 'layout' and original.get('execution_status') == 'Completed'
            and original.get('validation_status') == 'Failed'
            and original.get('review_status') in ('Awaiting Review', 'Changes Requested')
            and original.get('evidence_kind') == 'trusted_fixed_tool_execution'
            and all(original.get(key) == binding[key] for key in ('revision_id', 'global_job_id', 'global_rtl_sha256',
                    'source_manifest_sha256', 'settings_sha256', 'verification_plan_sha256')),
            'physical_resume_source', 'Retry only the exact executed first-repair failure; review metadata cannot substitute another source.')
    runtime = copy.deepcopy(original['runtime_configuration'])
    require(original.get('runtime_configuration_sha256') == object_hash(runtime) == binding['original_runtime_configuration_sha256']
            and runtime.get('profile', {}).get('profile_version') == (PROFILE_NPU2_RETRY if final else PROFILE_NPU2),
            'physical_resume_source', 'Retain the exact first-repair runtime identity.')
    configuration_projection(original['settings'], runtime, original['source_manifest'])
    result = original['checks']
    expected_checks = {'configuration': 'Passed', 'source_identity': 'Passed', 'routing': 'Passed',
                       'timing': 'Passed', 'electrical': 'Failed'}
    require(type(result) is dict and result.get('validation_status') == 'Failed' and result.get('executed') is True
            and type(result.get('exit_code')) is int and result['exit_code'] == 0
            and result.get('cleanup_unresolved') is False and type(result.get('checks')) is dict
            and set(result['checks']) == set(expected_checks)
            and all(result['checks'][key].get('validation_status') == status for key, status in expected_checks.items())
            and type(result.get('commands')) is list and len(result['commands']) == 2
            and all(command.get('executed') is True and command.get('status') == 'Completed'
                    and type(command.get('exit_code')) is int and command['exit_code'] == 0 for command in result['commands'])
            and any(item.get('code') == 'physical_checks_failed' for item in result.get('diagnostics', [])),
            'physical_resume_source', 'Only a complete actual electrical-only failure with verified cleanup can prepare retry.')
    require(type(result.get('artifacts_directory')) is str and Path(result['artifacts_directory']).is_absolute(),
            'physical_resume_path', 'The failed first repair must retain its absolute physical run directory.')
    root = Path(result['artifacts_directory']).resolve()
    require(root.is_relative_to((ROOT / '.work').resolve()) and root.name.startswith('hullcirq-layout-')
            and root.parent == Path(runtime['working_directory']).resolve(),
            'physical_resume_path', 'The retry checkpoint must remain in the recorded first-repair run.')
    state = (root / checkpoint).resolve()
    inputs = (root / 'input-manifest.json').resolve()
    require(state.is_relative_to(root) and inputs.is_relative_to(root),
            'physical_resume_path', 'Keep the retry checkpoint and input manifest within their original run.')
    for relative, expected, entries in (
            (checkpoint, state_sha, result.get('retained_files')),
            ('input-manifest.json', input_sha, result.get('artifacts'))):
        require(type(entries) is list, 'physical_resume_source', 'Retain the exact failed-run checkpoint/input descriptors.')
        matches = [entry for entry in entries if type(entry) is dict and entry.get('relative_path') == relative]
        path = (root / relative).resolve()
        require(len(matches) == 1 and matches[0].get('sha256') == expected and path.is_file()
                and type(matches[0].get('bytes')) is int and matches[0]['bytes'] == path.stat().st_size and sha(path) == expected,
                'physical_resume_source', 'The first-repair checkpoint or input bytes changed.')
    frozen_inputs = load(inputs)
    _source_identity(frozen_inputs, original['global_rtl'], original['source_manifest'], original['settings'])
    require(object_hash(frozen_inputs.get('runtime_configuration')) == binding['original_runtime_configuration_sha256'],
            'physical_resume_source', 'The retry checkpoint must belong to the exact first-repair runtime.')

    _validate_retry_views(load_tool_json(state), root, target)
    require(isinstance(working_directory, (str, Path)) and Path(working_directory).is_absolute(),
            'physical_repair_destination', 'Use a host-managed absolute retry working directory.')
    destination = Path(working_directory).resolve()
    require(destination.is_relative_to((ROOT / '.work').resolve()) and not destination.is_relative_to(root),
            'physical_repair_destination', 'Keep retry output below the host workspace and outside the failed source run.')
    runtime.update(origin=('gui_fixed_NPU2_extra_standard_electrical_repair_after_timing_original_GUI_job_and_signoff_constraints_unchanged' if final else 'gui_fixed_NPU2_retry_standard_non_delay_buffer_repair_original_GUI_job_and_signoff_constraints_unchanged'),
                   working_directory=str(destination),
                   profile=load(ROOT / ('configs/physical_profile_sky130_repair_npu2v3.json' if final else 'configs/physical_profile_sky130_repair_npu2v2.json')),
                   repair_source_binding=copy.deepcopy(binding),
                   repair_checkpoint_inventory=_retry_inventory_descriptor(target),
                   resume={'initial_state_path': str(state), 'initial_state_sha256': state_sha,
                           'source_input_manifest_path': str(inputs), 'source_input_manifest_sha256': input_sha,
                           'from_step': NPU2_FINAL_STEP if final else 'OpenROAD.RepairDesignPostGRT'})
    configuration_projection(original['settings'], runtime, original['source_manifest'])
    return runtime


def _native(path):
    match = re.fullmatch(r'/mnt/([a-zA-Z])/(.+)', path)
    return Path(match[1].upper() + ':/' + match[2]) if match else Path(path)


def _source_identity(inputs, rtl, source_manifest, settings):
    from .physical_tools import require
    from .global_workflow import source_bundle
    from .verification import content_hash
    require(object_hash(inputs.get('settings')) == object_hash(settings)
            and inputs.get('global_rtl_sha256') == content_hash(rtl)
            and inputs.get('source_manifest_sha256') == object_hash(source_manifest)
            and object_hash(inputs.get('source_bundle')) == object_hash(source_bundle(rtl, source_manifest)),
            'physical_resume_source', 'The checkpoint must belong to the unchanged original GUI settings and adopted RTL.')


def snapshot_resume(configuration, folder, rtl, source_manifest, settings):
    from .physical_tools import load, load_tool_json, require, sha
    validate_configuration(configuration)
    state_sha, input_sha, start_step = checkpoint_identity(configuration)
    value = configuration['resume']
    source_state = Path(value['initial_state_path']).resolve()
    source_inputs = Path(value['source_input_manifest_path']).resolve()
    require(sha(source_state) == state_sha and sha(source_inputs) == input_sha,
            'physical_resume_source', 'The original checkpoint or input manifest changed.')
    _source_identity(load(source_inputs), rtl, source_manifest, settings)
    root = source_inputs.parent
    require(source_state.is_relative_to(root), 'physical_resume_path', 'Keep the checkpoint within its original physical run.')
    retry = configuration.get('profile', {}).get('profile_version') in (PROFILE_NPU2_RETRY, PROFILE_NPU2_FINAL)
    if retry:
        _validate_retry_views(load_tool_json(source_state), root, configuration)
    folder = Path(folder).resolve()
    (folder / 'resume-original-state.json').write_bytes(source_state.read_bytes())
    (folder / 'resume-original-input-manifest.json').write_bytes(source_inputs.read_bytes())
    # LibreLane tool state may contain Infinity metrics. Preserve its JSON meaning
    # for LibreLane; all acceptance metrics are checked separately as finite.
    state = json.loads(source_state.read_text(encoding='utf-8'))
    files = {}

    def project(value):
        if value is None:
            return None
        if type(value) is dict:
            return {key: project(item) for key, item in value.items()}
        require(type(value) is str, 'physical_resume_state', 'A checkpoint view must be a file path or corner map.')
        source = _native(value).resolve()
        require(source.is_relative_to(root) and source.is_file(), 'physical_resume_path', 'Keep every checkpoint view in the original run.')
        relative = 'resume-files/' + source.relative_to(root).as_posix()
        destination = folder / relative
        if relative not in files:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as handle:
                handle.write(source.read_bytes())
            files[relative] = {'original_path': value, 'sha256': sha(destination), 'bytes': destination.stat().st_size}
        return _wsl_path(destination)

    derived = {key: copy.deepcopy(value) if key == 'metrics' else project(value) for key, value in state.items()}
    with (folder / 'resume-state.json').open('x', encoding='utf-8') as handle:
        json.dump(derived, handle, indent=2); handle.write('\n')
    manifest = {'schema': 'hullcirq-original-checkpoint-copy-v1', 'from_step': start_step,
                'original_state_sha256': state_sha, 'original_input_manifest_sha256': input_sha,
                'derived_state_sha256': sha(folder / 'resume-state.json'), 'files': files,
                'technology_mapping_executed': False, 'upstream_technology_mapping_reused': True}
    if retry:
        descriptor = _retry_inventory_descriptor(configuration)
        manifest.update(checkpoint_inventory_sha256=descriptor['sha256'],
                        checkpoint_view_hash_origin=descriptor['origin'])
        _validate_retry_copy_pins(configuration, manifest)
    with (folder / 'resume-manifest.json').open('x', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=2); handle.write('\n')
    validate_resume(configuration, folder, rtl, source_manifest, settings)


def validate_resume(configuration, folder, rtl, source_manifest, settings):
    from .physical_tools import load, load_tool_json, require, sha
    validate_configuration(configuration)
    state_sha, input_sha, start_step = checkpoint_identity(configuration)
    folder = Path(folder).resolve()
    require(sha(folder / 'resume-original-state.json') == state_sha
            and sha(folder / 'resume-original-input-manifest.json') == input_sha,
            'physical_resume_source', 'Retain the original raw checkpoint and its source identity.')
    _source_identity(load(folder / 'resume-original-input-manifest.json'), rtl, source_manifest, settings)
    manifest = load(folder / 'resume-manifest.json')
    require(manifest.get('schema') == 'hullcirq-original-checkpoint-copy-v1'
            and manifest.get('from_step') == start_step
            and manifest.get('original_state_sha256') == state_sha
            and manifest.get('original_input_manifest_sha256') == input_sha
            and manifest.get('technology_mapping_executed') is False
            and manifest.get('upstream_technology_mapping_reused') is True
            and manifest.get('derived_state_sha256') == sha(folder / 'resume-state.json')
            and type(manifest.get('files')) is dict and bool(manifest['files']),
            'physical_resume_manifest', 'Retain the exact checkpoint copy manifest and explicit reuse scope.')
    if configuration.get('profile', {}).get('profile_version') in (PROFILE_NPU2_RETRY, PROFILE_NPU2_FINAL):
        _validate_retry_copy_pins(configuration, manifest)
    originals = {}
    for relative, metadata in manifest['files'].items():
        path = (folder / relative).resolve()
        require(relative.startswith('resume-files/') and path.is_relative_to(folder / 'resume-files')
                and path.is_file() and metadata.get('bytes') == path.stat().st_size
                and metadata.get('sha256') == sha(path) and type(metadata.get('original_path')) is str
                and metadata['original_path'] not in originals,
                'physical_resume_copy', 'Every copied checkpoint view must retain its original bytes.')
        originals[metadata['original_path']] = _wsl_path(path)
    used = set()

    def project(value):
        if value is None:
            return None
        if type(value) is dict:
            return {key: project(item) for key, item in value.items()}
        require(type(value) is str and value in originals, 'physical_resume_copy', 'No checkpoint view may be omitted or substituted.')
        used.add(value)
        return originals[value]

    state = load_tool_json(folder / 'resume-original-state.json')
    expected = {key: value if key == 'metrics' else project(value) for key, value in state.items()}
    require(used == set(originals) and object_hash(expected) == object_hash(load_tool_json(folder / 'resume-state.json')),
            'physical_resume_state', 'Only file relocation may change the copied checkpoint state.')

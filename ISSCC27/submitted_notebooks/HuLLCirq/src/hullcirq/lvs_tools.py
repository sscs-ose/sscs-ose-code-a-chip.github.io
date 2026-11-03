"""Fixed S13 extraction/comparison of unchanged S11 outputs after adopted DRC."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile

from .domain import DomainError
from .verification import object_hash, trusted_command, _wsl_path
from . import physical_tools as physical
from .drc_tools import _safe
from .drc_tools import read_markers
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TAG = 'lvs'
SCOPE = 'exact_adopted_GDS_transistor_extraction_vs_corresponding_S11_powered_netlist'
require, sha, load = physical.require, physical.sha, physical.load
file_stat, file_exists = physical.file_stat, physical.file_exists
read_bytes, read_text, artifact_files = physical.read_bytes, physical.read_text, physical.artifact_files
TEXT = 'text/plain; charset=utf-8'
FILE_TYPES = {key: 'application/json' for key in ('config','initial-state','final-state','metrics','tool-versions','lvs-summary','lvs-json')}
FILE_TYPES.update({key: TEXT for key in ('input-def','input-netlist','input-powered-netlist','extracted-spice','lvs-report','extraction-feedback','lvs-script')})
FILE_TYPES.update({'input-gds':'application/octet-stream','extraction-markers':'application/xml'})
FIXED_FILES = {'input-gds':'input.gds','input-def':'input.def','input-netlist':'input.nl.v','input-powered-netlist':'input.pnl.v',
    'config':'config.json','initial-state':'initial-state.json','tool-versions':'tool-versions.json','lvs-summary':'lvs-summary.json',
    'extracted-spice':'runs/lvs/1-magic-spiceextraction/hullcirq_npu.spice',
    'extraction-feedback':'runs/lvs/1-magic-spiceextraction/feedback.txt',
    'extraction-markers':'runs/lvs/1-magic-spiceextraction/feedback.xml',
    'lvs-report':'runs/lvs/2-netgen-lvs/reports/lvs.netgen.rpt','lvs-json':'runs/lvs/2-netgen-lvs/reports/lvs.netgen.json',
    'lvs-script':'runs/lvs/2-netgen-lvs/lvs_script.lvs','final-state':'runs/lvs/2-netgen-lvs/state_out.json','metrics':'runs/lvs/final/metrics.json'}
POWER_PINS = {'VPWR':'VPWR','VPB':'VPWR','VGND':'VGND','VNB':'VGND'}
RECOGNITION_PROFILE = 'hullcirq-sky130-lvs-v3'
RECOGNITION_PROFILES = (RECOGNITION_PROFILE, 'hullcirq-sky130-lvs-v4', 'hullcirq-sky130-lvs-v5', 'hullcirq-sky130-lvs-v6', 'hullcirq-sky130-lvs-v7')
INVENTORY_PROFILES = ('hullcirq-sky130-lvs-v4', 'hullcirq-sky130-lvs-v5', 'hullcirq-sky130-lvs-v6', 'hullcirq-sky130-lvs-v7')
UPGRADE_PREVIOUS = {'hullcirq-sky130-lvs-v4':RECOGNITION_PROFILE,
    'hullcirq-sky130-lvs-v5':'hullcirq-sky130-lvs-v4', 'hullcirq-sky130-lvs-v6':'hullcirq-sky130-lvs-v5',
    'hullcirq-sky130-lvs-v7':'hullcirq-sky130-lvs-v6'}
REPAIR_BINDING_KEYS = {'schema', 'historical_lvs_run_id', 'historical_lvs_record_sha256',
    'historical_lvs_execution_sha256', 'layout_run_id', 'layout_record_sha256',
    'drc_run_id', 'drc_record_sha256', 'source_inputs_sha256'}
UPGRADE_BINDING_KEYS = {'schema', 'previous_profile_version', 'previous_bundle_sha256',
    'failed_lvs_run_id', 'failed_lvs_record_sha256', 'failed_lvs_execution_sha256'}
METRIC_NAMES = {'error_count':'design__lvs_error__count','device_difference_count':'design__lvs_device_difference__count',
    'net_difference_count':'design__lvs_net_difference__count','property_fail_count':'design__lvs_property_fail__count',
    'unmatched_device_count':'design__lvs_unmatched_device__count','unmatched_net_count':'design__lvs_unmatched_net__count',
    'unmatched_pin_count':'design__lvs_unmatched_pin__count'}

def _recognition_profile(profile):
    return type(profile) is dict and profile.get('profile_version') in RECOGNITION_PROFILES


def _file_types(profile=None):
    # New evidence is mandatory only for the new recipe. Historical v1/v2
    # artifact sets and their exact saved interpretation remain unchanged.
    result={**FILE_TYPES, **({'extraction-model-proof':'application/json',
        'extraction-raw-spice':TEXT,'extraction-models':TEXT,'extraction-deck':TEXT}
        if _recognition_profile(profile) else {})}
    if type(profile) is dict and profile.get('profile_version') in INVENTORY_PROFILES:
        result.update({key:'application/json' for key in ('extraction-inventory-pre-gds',
            'extraction-inventory-post-gds','extraction-inventory-post-annotation')})
    return result


def _fixed_files(layout,profile=None):
    """Derive the one top-named Magic output while preserving old records.

    ``FIXED_FILES`` remains the exact historical ``hullcirq_npu`` table.  The
    saved layout top selects the derived path for a new run, so the old top
    produces byte-for-byte identical artifact metadata.
    """
    require(type(layout) is dict and type(layout.get('settings')) is dict,
            'lvs_source_conflict','Require saved S11 settings for LVS artifact binding.')
    top=physical._top_identifier(layout['settings'].get('top_module'))
    files=dict(FIXED_FILES)
    files['extracted-spice']='runs/lvs/1-magic-spiceextraction/'+top+'.spice'
    if _recognition_profile(profile):
        variant=profile['terminal_recognition_variant']
        files.update({'extracted-spice':variant['comparison_spice'],
            'extraction-model-proof':variant['proof'],
            'extraction-raw-spice':variant['raw_spice'],
            'extraction-models':Path(variant['wrapper_path']).name,
            'extraction-deck':variant['derived_tech']})
    if type(profile) is dict and profile.get('profile_version') in INVENTORY_PROFILES:
        files.update({'extraction-inventory-pre-gds':'source-inventory-pre_gds.json',
            'extraction-inventory-post-gds':'source-inventory-post_gds.json',
            'extraction-inventory-post-annotation':'source-inventory-post_annotation.json'})
    return files

def _flat_netlist(text):
    """Recognize only the saved flat OpenROAD named-port Verilog subset."""
    require('/*' not in text and '//' not in text and text.count('endmodule')==1,
            'lvs_netlist_unsupported','Require the complete flat OpenROAD output; unsupported syntax is not silently skipped.')
    statements=text.replace('endmodule','').strip().split(';')
    require(not statements[-1].strip(),'lvs_netlist_unsupported','Require complete terminated statements.')
    header=re.fullmatch(r'\s*module\s+(\w+)\s*\((.*?)\)\s*',statements[0],re.S)
    require(header is not None,'lvs_netlist_unsupported','Require one flat named top module.')
    ports=[v.strip() for v in header[2].split(',')]
    require(len(set(ports))==len(ports),'lvs_netlist_unsupported','Duplicate top ports are unsupported.')
    declarations=[];assignments=[];instances={}
    identifier=r'(?:\\[^\s]+|[A-Za-z_$][\w$]*)'
    for statement in statements[1:-1]:
        statement=statement.strip()
        if re.match(r'^(input|output|inout|wire)\b',statement):
            if statement in ('inout VPWR','inout VGND','wire VPWR','wire VGND'):continue
            declarations.append(re.sub(r'\s+','',statement));continue
        if statement.startswith('assign '):
            assignments.append(re.sub(r'\s+','',statement));continue
        match=re.fullmatch(r'('+identifier+r')\s+('+identifier+r')\s*\((.*)\)',statement,re.S)
        require(match is not None,'lvs_netlist_unsupported','Unsupported non-declaration in saved flat netlist.')
        cell,name,body=match.groups();name=name.lstrip('\\');bindings={}
        for part in body.split(',') if body.strip() else []:
            pin=re.fullmatch(r'\s*\.([A-Za-z_$][\w$]*)\s*\(([^()]*)\)\s*',part,re.S)
            require(pin is not None and pin[1] not in bindings,'lvs_netlist_unsupported','Require unique complete named cell pins.')
            bindings[pin[1]]=re.sub(r'\s+','',pin[2])
        require(name not in instances,'lvs_netlist_unsupported','Duplicate instances are unsupported.')
        instances[name]={'cell':cell,'pins':bindings}
    require(instances,'lvs_netlist_unsupported','An empty comparison circuit cannot pass.')
    return {'top':header[1],'ports':ports,'declarations':sorted(declarations),'assignments':sorted(assignments),'instances':instances}

def bind_powered_netlist(netlist_text,powered_text,def_text,top):
    """Check the actual saved companion; never edit or generate a netlist."""
    logical=_flat_netlist(netlist_text);powered=_flat_netlist(powered_text)
    require(logical['top']==powered['top']==top and 'VPWR' not in logical['ports'] and 'VGND' not in logical['ports']
            and set(powered['ports'])==set(logical['ports'])|{'VPWR','VGND'}
            and [p for p in powered['ports'] if p not in ('VPWR','VGND')]==logical['ports']
            and logical['declarations']==powered['declarations'] and logical['assignments']==powered['assignments'],
            'lvs_powered_netlist_conflict','The saved powered companion must preserve every original signal port, declaration and assignment.')
    component_block=re.search(r'\bCOMPONENTS\s+([0-9]+)\s*;(.*?)\bEND COMPONENTS\b',def_text,re.S)
    require(component_block is not None and 'DESIGN '+top+' ;' in def_text,'lvs_def_conflict','Require the adopted complete DEF component table.')
    components={}
    for name,cell in re.findall(r'^\s*-\s+(\S+)\s+(\S+)',component_block[2],re.M):
        require(name not in components,'lvs_def_conflict','Duplicate DEF components.')
        components[name.lstrip('\\')]=cell
    require(len(components)==int(component_block[1]) and set(components)==set(powered['instances']),
            'lvs_powered_netlist_conflict','Every powered instance must correspond to exactly one adopted DEF component.')
    projected={};extras=[];pins_checked=0
    for name,instance in powered['instances'].items():
        require(instance['cell']==components[name],'lvs_powered_netlist_conflict','Powered cell type differs from adopted DEF.')
        pins=instance['pins'];power={k:v for k,v in pins.items() if k in POWER_PINS}
        expected_power={'VPWR':'VPWR','VGND':'VGND'} if instance['cell']=='sky130_fd_sc_hd__tapvpwrvgnd_1' else POWER_PINS
        require(power==expected_power,'lvs_powered_netlist_conflict','Every cell must retain its explicit correct supply and available well connections.')
        signals={k:v for k,v in pins.items() if k not in POWER_PINS}
        if name in logical['instances']:
            projected[name]={'cell':instance['cell'],'pins':signals};pins_checked+=len(signals)
        else:
            require(not signals and re.fullmatch(r'sky130_fd_sc_hd__(?:fill|decap|tapvpwrvgnd)_\d+',instance['cell']),
                    'lvs_powered_netlist_conflict','Only DEF-backed power-only physical cells may be absent from the signal netlist.')
            extras.append(name)
    require(object_hash(projected)==object_hash(logical['instances']),'lvs_powered_netlist_conflict','Every adopted logical instance and signal pin must match the original powered companion.')
    return {'validation_status':'Passed','scope':'complete_flat_signal_graph_and_DEF_component_identity_with_explicit_supply_pins',
        'logical_instances':len(projected),'signal_pin_connections':pins_checked,'powered_instances':len(powered['instances']),
        'power_only_physical_instances':sum(not v['pins'] for v in projected.values())+len(extras),'signal_graph_sha256':object_hash(projected),
        'supply_pin_bindings':POWER_PINS,'tap_cell_supply_pins':{'VPWR':'VPWR','VGND':'VGND'}}

def _pointer_relative(pointer,folder):
    require(type(pointer) is str,'lvs_source_conflict','Require a concrete original S11 output pointer.')
    match=re.fullmatch(r'/mnt/([a-zA-Z])/(.+)',pointer)
    path=Path(match[1].upper()+':/'+match[2]) if match else Path(pointer)
    path=path.resolve();folder=Path(folder).resolve()
    require(path.is_relative_to(folder),'lvs_source_conflict','The powered companion must remain in the original S11 output directory.')
    return path.relative_to(folder).as_posix()

def source_inputs(layout):
    folder=Path(layout['checks']['artifacts_directory']).resolve()
    entries={e['id']:e for e in layout['checks']['artifacts']}
    result={}
    for identifier in ('gds','def','netlist','final-state'):
        e=entries[identifier];p=_safe(folder,e['relative_path'])
        require(type(e['bytes']) is int and file_stat(p).st_size==e['bytes'] and sha(p)==e['sha256'],'lvs_source_conflict','An adopted S11 input changed: '+identifier)
        if identifier!='final-state':result[identifier]=copy.deepcopy(e)
    state=physical.load_tool_json(folder/entries['final-state']['relative_path'])
    for identifier,key in (('gds','gds'),('def','def'),('netlist','nl')):
        require(_pointer_relative(state[key],folder)==result[identifier]['relative_path'],'lvs_source_conflict','S11 final state and fixed artifacts disagree.')
    relative=_pointer_relative(state['pnl'],folder);p=_safe(folder,relative)
    binding=bind_powered_netlist(read_text((folder/result['netlist']['relative_path']),encoding='utf-8'),read_text(p,encoding='utf-8'),
        read_text((folder/result['def']['relative_path']),encoding='utf-8'),layout['settings']['top_module'])
    result['powered_netlist']={'id':'powered-netlist','relative_path':relative,'sha256':sha(p),'bytes':file_stat(p).st_size,'content_type':TEXT,
        'origin':'original_S11_state_pointer_observed_at_S13_start','binding':binding}
    return result

def configuration_projection(drc,layout,configuration):
    require(type(configuration) is dict and type(configuration.get('physical_runtime')) is dict,'lvs_configuration_invalid','Configure the explicit fixed S13 runtime.')
    runtime=configuration['physical_runtime']
    require(object_hash(runtime)==object_hash(layout['runtime_configuration']) and object_hash(drc['layout_snapshot'])==object_hash(layout)
            and drc['layout_record_sha256']==object_hash(layout),'lvs_source_conflict','LVS must retain the exact S11 input adopted by S12.')
    physical.configuration_projection(layout['settings'],runtime,layout.get('source_manifest'))
    profile=configuration.get('profile')
    _fixed_profile(profile)
    if _recognition_profile(profile):
        binding=configuration.get('repair_source_binding')
        require(type(binding) is dict and set(binding)==REPAIR_BINDING_KEYS
            and binding.get('schema')=='hullcirq-lvs-terminal-repair-source-v1'
            and all(type(binding.get(k)) is str and re.fullmatch(r'[0-9a-f]{64}',binding[k])
                    for k in REPAIR_BINDING_KEYS if k.endswith('_sha256'))
            and type(binding.get('historical_lvs_run_id')) is str and binding['historical_lvs_run_id']
            and binding.get('layout_run_id')==layout['id'] and binding.get('layout_record_sha256')==object_hash(layout)
            and binding.get('drc_run_id')==drc['id'] and binding.get('drc_record_sha256')==object_hash(drc),
            'lvs_repair_source_conflict','Prepare the new extraction profile from the exact retained original LVS and adopted S11/S12 chain.')
    direct=(profile.get('profile_version')=='hullcirq-sky130-lvs-v7'
        and configuration.get('repair_preparation_kind')=='direct_v7')
    if direct:
        require('repair_upgrade_binding' not in configuration, 'lvs_repair_upgrade_conflict',
            'Direct v7 preparation must bind the original accepted warning source, not fabricate a failed ancestor.')
    elif profile.get('profile_version') in INVENTORY_PROFILES:
        if profile.get('profile_version')=='hullcirq-sky130-lvs-v7':
            require('repair_preparation_kind' not in configuration, 'lvs_repair_upgrade_conflict',
                'Use only the exact fixed direct-v7 preparation or the proven v6 upgrade.')
        upgrade=configuration.get('repair_upgrade_binding')
        previous=UPGRADE_PREVIOUS[profile['profile_version']]
        require(type(upgrade) is dict and set(upgrade)==UPGRADE_BINDING_KEYS
            and upgrade.get('schema')=='hullcirq-lvs-terminal-repair-upgrade-v1'
            and upgrade.get('previous_profile_version')==previous
            and type(upgrade.get('failed_lvs_run_id')) is str and bool(upgrade['failed_lvs_run_id'])
            and all(type(upgrade.get(k)) is str and re.fullmatch(r'[0-9a-f]{64}',upgrade[k])
                    for k in UPGRADE_BINDING_KEYS if k.endswith('_sha256')),
            'lvs_repair_upgrade_conflict','Prepare the fixed next version explicitly from its retained failed execution and immutable prior bundle.')
    require(type(configuration.get('working_directory')) is str and Path(configuration['working_directory']).is_absolute(),
            'lvs_path_invalid','Use a separate absolute S13 work directory.')
    return {'meta':{'version':2,'flow':profile['flow']},'DESIGN_NAME':layout['settings']['top_module'],**copy.deepcopy(profile['config'])}

def _fixed_profile(profile):
    require(any(object_hash(profile)==object_hash(load(ROOT/'configs'/name)) for name in
                ('lvs_profile_sky130.json','lvs_profile_sky130_v2.json','lvs_profile_sky130_v3.json','lvs_profile_sky130_v4.json','lvs_profile_sky130_v5.json','lvs_profile_sky130_v6.json','lvs_profile_sky130_v7.json')),
            'lvs_profile_invalid','Use an exact versioned fixed extraction/LVS profile.')
    return profile

def _variant_files(profile):
    if not profile.get('force_full_extraction'):return {}
    variant=profile['extraction_variant']
    sources={Path(variant[k+'_path']).name:(ROOT/variant[k+'_path'],variant[k+'_sha256']) for k in ('script','launcher')}
    if _recognition_profile(profile):
        recognition=profile['terminal_recognition_variant']
        sources.update({Path(recognition[k+'_path']).name:(ROOT/recognition[k+'_path'],recognition[k+'_sha256'])
            for k in ('helper','wrapper')})
    return sources


def _recognition_helper(root,profile):
    """Load only hash-pinned application code, without writing import caches.

    No arbitrary artifact or supplied path becomes executable. The exact fixed
    profile pins this trusted recipe, copied unchanged into the retained run.
    Its module has no execution side effects and is never loaded as __main__.
    """
    recognition=profile['terminal_recognition_variant']
    path=_safe(root,Path(recognition['helper_path']).name)
    raw=read_bytes(path)
    require(hashlib.sha256(raw).hexdigest()==recognition['helper_sha256'],'lvs_recognition_source_changed',
            'Retain the exact versioned MOSCAP recognition helper.')
    namespace={'__file__':str(path),'__name__':'_hullcirq_lvs_moscap_v3_retained'}
    exec(compile(raw,str(path),'exec'),namespace)
    return namespace


def _validate_recognition_model_proof(root,layout,profile,logical_root=None):
    try:
        # Keep the frozen helper and logical/native recipe paths unchanged.
        # Its Path-based retained-file reads need the Windows extended-path
        # spelling, including the deeper cell-by-cell extraction inventory.
        proof=_recognition_helper(root,profile)['validate_retained_model_proof'](physical.io_path(root),layout,profile,
            logical_root=root if logical_root is None else logical_root)
        require(type(proof) is dict and proof.get('validation_status')=='Passed',
                'lvs_recognition_unproven','The exact retained MOSCAP recognition and model proof must pass.')
        return proof
    except (ValueError,KeyError,TypeError,OSError) as error:
        raise DomainError('lvs_recognition_unproven',
            'Retained MOSCAP extraction/model proof is invalid: '+str(error),409) from error


def _validate_native_recognition_diagnostics(profile,stdout,stderr):
    # V6 additionally rejects native errors actually observed during v5. An
    # empty feedback XML cannot waive allocator/model/selection diagnostics.
    # Historical profiles keep their original interpretation unchanged.
    if profile.get('profile_version') not in ('hullcirq-sky130-lvs-v6','hullcirq-sky130-lvs-v7'):return
    require(not re.search(r'freeMagic called with NULL argument|Device parameters do not match any extraction model|No cell selected',
            stdout+'\n'+stderr,re.I), 'lvs_native_recognition_error',
            'Retained native extraction contains allocator, model-matching or selection errors; zero feedback cannot authorize adoption.')

def _validate_variant(profile,root,logical,stdout):
    for name,(_,digest) in _variant_files(profile).items():
        require(sha(root/name)==digest,'lvs_runtime_conflict','Retain the exact fixed full-extraction launcher and Tcl.')
    if not profile.get('force_full_extraction'):return
    if _recognition_profile(profile):
        variant=profile['extraction_variant'];recognition=profile['terminal_recognition_variant']
        prefix='HuLLCirq MOSCAP extraction launcher: '
        banners=[json.loads(line[len(prefix):]) for line in stdout.splitlines() if line.startswith(prefix)]
        expected={'librelane':physical.RELEASE,'entrypoint':'librelane.__main__.cli',
            'step':'Magic.SpiceExtraction','profile_version':profile['profile_version'],
            'upstream_script_sha256':variant['upstream_sha256'],
            'script':_wsl_path(logical/Path(variant['script_path']).name),
            'script_sha256':variant['script_sha256'],'helper_sha256':recognition['helper_sha256'],
            'wrapper_sha256':recognition['wrapper_sha256'],'qualified_cell':recognition['qualified_cell'],
            'added_abstract_cells':0,'added_ignore_rules':0}
        require(len(banners)==1 and object_hash(banners[0])==object_hash(expected),
                'lvs_configuration_conflict','Require the exact recorded MOSCAP extraction dispatch; no ignore or abstraction additions.')
        return
    script=read_bytes((root/'extract_spice_full.tcl'));variant=profile['extraction_variant']
    require(script.count(b'\nextract all\n')==1 and hashlib.sha256(
        script.replace(b'\nextract all\n',b'\nextract\n',1)).hexdigest()==variant['upstream_sha256'],
        'lvs_runtime_conflict','The retained Tcl must differ from the pinned upstream by exactly the declared single line.')
    prefix='HuLLCirq full extraction launcher: '
    banners=[json.loads(line[len(prefix):]) for line in stdout.splitlines() if line.startswith(prefix)]
    require(len(banners)==1 and object_hash(banners[0])==object_hash({'librelane':physical.RELEASE,'entrypoint':'librelane.__main__.cli',
        'step':'Magic.SpiceExtraction','upstream_script_sha256':variant['upstream_sha256'],
        'script':_wsl_path(logical/'extract_spice_full.tcl'),'script_sha256':variant['script_sha256'],
        'change':'extract -> extract all','added_abstract_cells':0,'added_ignore_rules':0}),
        'lvs_configuration_conflict','The frozen launcher must record its exact full-extraction dispatch.')

def lvs_capability(configuration):
    if configuration is None:return {'available':False,'reason':'No trusted S13 LVS runtime is configured.'}
    try:
        runtime=configuration['physical_runtime']
        require(runtime.get('appimage_sha256')==physical.IMAGE_SHA and runtime.get('pdk_revision')==physical.PDK_REVISION
            and file_exists(Path(runtime['appimage_path'])) and file_exists(Path(runtime['pdk_manifest_path'])),
            'lvs_runtime_missing','Prepare the supported pinned physical runtime and S13 profile.')
        _fixed_profile(configuration['profile'])
        require(all(sha(path)==digest for path,digest in _variant_files(configuration['profile']).values()),
                'lvs_runtime_missing','The fixed full-extraction sources changed.')
        return {'available':True,'reason':None}
    except (DomainError,KeyError,TypeError,OSError,ValueError) as error:return {'available':False,'reason':str(error)}

def fixed_commands(configuration,folder):
    folder=Path(folder).resolve();runtime=configuration['physical_runtime']
    require(folder.parent==Path(configuration['working_directory']).resolve() and folder.name.startswith('hullcirq-lvs-'),
            'lvs_path_invalid','Use a new configured isolated S13 directory.')
    _fixed_profile(configuration['profile'])
    launcher=['python3',_wsl_path(folder/Path(configuration['profile']['extraction_variant']['launcher_path']).name)] if configuration['profile'].get('force_full_extraction') else ['librelane']
    arguments=[['python3',_wsl_path(folder/'capture_lvs_versions.py'),_wsl_path(folder/'tool-versions.json')],
        [*launcher,'--pdk','sky130A','--scl','sky130_fd_sc_hd','--pdk-root',_wsl_path(Path(runtime['pdk_root'])),
         '--jobs','2','--run-tag',TAG,'--with-initial-state',_wsl_path(folder/'initial-state.json'),'--hide-progress-bar',_wsl_path(folder/'config.json')]]
    return [trusted_command(runtime,runtime['executable'],args,folder) for args in arguments]

def _count(value):
    require(type(value) is int and value>=0,'lvs_metric_invalid','Require explicit nonnegative integer counts, never missing, boolean or nonfinite values.')
    return value

def summarize(root,layout,profile=None,logical_root=None):
    files=_fixed_files(layout,profile);root=Path(root).resolve();metrics=load(_safe(root,files['metrics']))
    counts={k:_count(metrics.get(v)) for k,v in METRIC_NAMES.items()}
    overlap=_count(metrics.get('magic__illegal_overlap__count'))
    markers,feedback=read_markers(_safe(root,files['extraction-markers']),'Magic extraction')
    # LibreLane 3.0.16 counts only descriptions containing this exact phrase.
    # Other feedback is preserved and disclosed, never mislabeled as resolved.
    illegal=[item for item in feedback if 'Illegal overlap' in item['description']]
    require(len(illegal)==overlap,'lvs_overlap_conflict','Extracted illegal overlap metrics and corresponding complete marker items must agree.')
    stats=load(_safe(root,files['lvs-json']))
    require(type(stats) is list and bool(stats) and all(type(c) is dict for c in stats),'lvs_report_invalid','Require a nonempty complete Netgen comparison list.')
    top=stats[-1];name=top.get('name')
    require(type(name) is list and name==[layout['settings']['top_module']]*2,'lvs_top_conflict','Both final Netgen circuits must be the expected top cell.')
    nets=top.get('nets');devices=top.get('devices');pins=top.get('pins')
    require(type(nets) is list and len(nets)==2 and all(_count(v)>0 for v in nets)
        and type(devices) is list and len(devices)==2 and all(type(v) is list and v for v in devices)
        and len(devices[0])==len(devices[1]) and type(pins) is list and len(pins)==2
        and all(type(v) is list and v for v in pins) and len(pins[0])==len(pins[1]),
        'lvs_report_invalid','Require explicit nonempty top nets/devices/pins and complete pairs; truncated pairs cannot pass.')
    for side in devices:
        for pair in side:
            require(type(pair) is list and len(pair)==2 and type(pair[0]) is str and pair[0] and _count(pair[1])>0,
                    'lvs_report_invalid','Require complete named nonempty device counts.')
    derived={'net_difference_count':abs(nets[0]-nets[1]),'device_difference_count':sum(abs(a[1]-b[1]) for a,b in zip(*devices)),
        'unmatched_pin_count':0,'property_fail_count':0}
    mismatches=[]
    for cell in stats:
        for key in ('badnets','badelements','properties'):
            if key in cell:require(type(cell[key]) is list,'lvs_report_invalid','Mismatch details must be complete lists.')
        derived['property_fail_count']+=len(cell.get('properties',[]))
        if any(cell.get(k) for k in ('badnets','badelements','properties')):mismatches.append(copy.deepcopy(cell))
    derived['unmatched_device_count']=len(top.get('badelements',[]));derived['unmatched_net_count']=len(top.get('badnets',[]))
    for first,second in zip(*pins):
        require(type(first) is str and type(second) is str and first and second,'lvs_report_invalid','Require complete pin names.')
        a=first.lower().removesuffix('!');b=second.lower().removesuffix('!')
        if a!=b and '(no pin)' not in (a,b):derived['unmatched_pin_count']+=1
    derived['error_count']=sum(derived.values())
    require(counts==derived,'lvs_count_conflict','Final metrics must equal counts reconstructed from the complete actual Netgen JSON.')
    report=read_text(_safe(root,files['lvs-report']),encoding='utf-8')
    # Netgen 1.5.316 can print a unique match followed by property errors while
    # omitting corresponding JSON details (upstream issue 104). Never adopt that
    # contradictory zero-count report; preserve the raw attempt as Failed.
    require(counts['error_count']!=0 or (not mismatches and not re.search(
        r'Property errors were found|following cells had property errors',report,re.I)),
        'lvs_unreported_mismatch','Raw property/mismatch evidence contradicts zero error counts; unique match alone cannot override it.')
    final=report.rsplit('Final result:',1)
    unique=len(final)==2 and bool(re.match(r'\s*Circuits match uniquely\.',final[-1]))
    require(counts['error_count']!=0 or unique,'lvs_match_unproven','Zero counts require an explicit final unique match, not only exit zero.')
    summary={'design':layout['settings']['top_module'],'extraction':{'illegal_overlap_count':overlap,
        'feedback_item_count':markers['error_count'],'feedback_categories':markers['categories'],'feedback':feedback,
        'non_overlap_feedback_count':len(feedback)-len(illegal),
        'feedback_scope':'All feedback is retained. Zero illegal overlaps does not assert that other extraction warnings are harmless or resolved.'},
        'lvs':{**counts,'match_status':'Unique match' if unique else 'Mismatch','comparison_count':len(stats),
               'top_net_counts':nets,'top_device_counts':devices,'top_pin_counts':[len(v) for v in pins]},
        'mismatches':mismatches,'limits':(profile or load(ROOT/'configs/lvs_profile_sky130.json'))['limits']}
    if profile and profile.get('force_full_extraction'):
        summary['extraction']['variant']=copy.deepcopy(profile['extraction_variant'])
    ext_status='Passed' if overlap==0 else 'Failed';lvs_status='Passed' if counts['error_count']==0 and unique else 'Failed'
    if _recognition_profile(profile):
        # The new correction must remove the cause, not merely relabel an
        # existing feedback item. Both independent retained feedback formats
        # must be empty for its extraction check to pass. Older recipes keep
        # their original gate and preserve their original warnings.
        raw_feedback=read_text(_safe(root,files['extraction-feedback']),encoding='utf-8')
        feedback_clean=not raw_feedback.strip() and markers['error_count']==0 and not feedback
        proof=_validate_recognition_model_proof(root,layout,profile,logical_root)
        summary['extraction']['recognition_proof']=proof
        summary['extraction']['zero_feedback_required']=True
        summary['extraction']['raw_feedback_empty']=not raw_feedback.strip()
        summary['extraction']['missing_device_terminal_count']=sum(
            bool(re.search(r'device missing \d+ terminals?',item['description'])) for item in feedback)
        ext_status='Passed' if overlap==0 and feedback_clean else 'Failed'
    checks={'source_identity':{'validation_status':'Passed'},'configuration':{'validation_status':'Passed'},
        'extraction':{'validation_status':ext_status,'executed':True,'completed':True,'illegal_overlap_count':overlap},
        'lvs':{'validation_status':lvs_status,'executed':True,'completed':True,**counts}}
    if _recognition_profile(profile):
        checks['extraction'].update(feedback_item_count=markers['error_count'],
            raw_feedback_empty=not raw_feedback.strip(),recognition_proof_status='Passed')
    return summary,metrics,checks

def _input_manifest(result,drc,layout,configuration):
    return {'drc_run_id':drc['id'],'drc_record_sha256':object_hash(drc),'layout_run_id':layout['id'],
        'layout_record_sha256':object_hash(layout),'source_inputs':result['source_inputs'],'configuration':configuration,
        'adapter_source_sha256':result['adapter_source_sha256'],'version_capture_sha256':result['version_capture_sha256']}

def validate_failed_lvs_result(result,drc,layout,configuration):
    """Reconstruct a resolved failed launch/check, never certify success.

    This admission proof exists only to prepare a new immutable recipe. It
    cannot be substituted for complete extraction/comparison validation.
    """
    version=configuration.get('profile',{}).get('profile_version')
    if version=='hullcirq-sky130-lvs-v6':
        require(result.get('status')=='Completed' and result.get('validation_status')=='Failed',
            'lvs_failed_execution_conflict','Require the complete retained failed v6 comparison, not an incomplete launch or success.')
        # This version reached full extraction and Netgen. Reconstruct its
        # entire native proof and failed mandatory checks, not just an exit.
        validate_lvs_result(result,drc,layout,configuration)
        require(result.get('checks',{}).get('extraction',{}).get('validation_status')=='Passed'
            and result.get('checks',{}).get('lvs',{}).get('validation_status')=='Failed',
            'lvs_failed_execution_conflict','Retain v6 extraction success and its actual failed comparison separately.')
        return {'validation_status':'Passed','scope':'actual_failed_v6_execution_proof_only_not_LVS_success'}
    require(version in (RECOGNITION_PROFILE,'hullcirq-sky130-lvs-v4','hullcirq-sky130-lvs-v5'),
            'lvs_failed_profile_invalid','Only a retained failed v3/v4/v5 recipe can authorize its fixed next version.')
    config=configuration_projection(drc,layout,configuration)
    root=Path(result['artifacts_directory']).resolve();runtime=configuration['physical_runtime']
    inputs=source_inputs(layout)
    require(object_hash(result.get('source_inputs'))==object_hash(inputs)
        and configuration['repair_source_binding']['source_inputs_sha256']==object_hash(inputs)
        and result.get('origin')=='trusted_fixed_lvs_adapter' and result.get('scope')==SCOPE
        and result.get('drc_run_id')==drc['id'] and result.get('drc_record_sha256')==object_hash(drc)
        and result.get('layout_run_id')==layout['id'] and result.get('layout_record_sha256')==object_hash(layout)
        and result.get('configuration_sha256')==object_hash(configuration)
        and result.get('input_gds_sha256')==inputs['gds']['sha256']
        and result.get('input_netlist_sha256')==inputs['netlist']['sha256']
        and result.get('input_powered_netlist_sha256')==inputs['powered_netlist']['sha256'],
        'lvs_source_conflict','Retain the exact original source chain for the failed execution.')
    commands=result.get('commands')
    require(result.get('status')=='Failed' and result.get('validation_status')=='Failed'
        and result.get('executed') is True and result.get('cleanup_unresolved') is False
        and type(result.get('exit_code')) is int and result['exit_code']!=0
        and type(commands) is list and len(commands)==2,
        'lvs_failed_execution_conflict','Require an actual terminal failed launch with resolved cleanup.')
    for operation,record,command,timeout in zip(('version','lvs'),commands,fixed_commands(configuration,root),(120,7200)):
        logs=root/operation
        request=load(logs/'request.json');terminal=load(logs/'process-result.json');start=load(logs/'process-start.json')
        worker_sha=sha(logs/'worker.py')
        expected={'version':'hullcirq-physical-worker-v2','argv':command[command.index('--exec')+1:],
            'cwd':_wsl_path(root),'timeout_seconds':timeout,'worker_sha256':physical.WORKER_V2_SHA}
        supervisor=trusted_command(runtime,'/usr/bin/python3',[_wsl_path(logs/'worker.py'),_wsl_path(logs/'request.json'),
            '--request-sha256',sha(logs/'request.json'),'--worker-sha256',worker_sha],root)
        require(worker_sha==physical.WORKER_V2_SHA and record.get('worker_sha256')==worker_sha
            and record.get('command')==command and record.get('supervisor_command')==supervisor
            and object_hash(request)==object_hash(expected) and record.get('request_sha256')==sha(logs/'request.json')
            and record.get('process_start_sha256')==sha(logs/'process-start.json')
            and record.get('status')=='Completed' and record.get('executed') is True
            and type(record.get('exit_code')) is int
            and (record['exit_code']==0 if operation=='version' else record['exit_code']==result['exit_code'])
            and all(object_hash(record.get(k))==object_hash(v) for k,v in terminal.items())
            and record.get('request_unchanged_at_completion') is True
            and record.get('worker_unchanged_at_completion') is True
            and record.get('observed_child_cwd') in (None,_wsl_path(root)),
            'lvs_worker_conflict','Reconstruct both actual fixed requests, worker births and terminal exits.')
        physical.validate_worker_binding(request,record,start,root,worker_sha)
        require(record.get('stdout')==read_text((logs/'stdout.log'),encoding='utf-8',errors='replace')
            and record.get('stderr')==read_text((logs/'stderr.log'),encoding='utf-8',errors='replace'),
            'lvs_log_conflict','Retain complete failed-launch raw logs.')
    require(result.get('stdout')==''.join(r['stdout'] for r in commands)
        and result.get('stderr')==''.join(r['stderr'] for r in commands),
        'lvs_log_conflict','Retain the exact combined failed-launch logs.')
    for identifier,filename in (('gds','input.gds'),('def','input.def'),('netlist','input.nl.v'),('powered_netlist','input.pnl.v')):
        path=root/filename;entry=inputs[identifier]
        require(file_stat(path).st_size==entry['bytes'] and sha(path)==entry['sha256'],
            'lvs_input_conflict','Failed execution must retain unchanged staged sources.')
    initial={'gds':_wsl_path(root/'input.gds'),'def':_wsl_path(root/'input.def'),
        'nl':_wsl_path(root/'input.nl.v'),'pnl':_wsl_path(root/'input.pnl.v'),'metrics':{}}
    state=next(e for e in layout['checks']['artifacts'] if e['id']=='final-state')
    require(sha(root/'source-layout-state.json')==state['sha256']
        and object_hash(load(root/'config.json'))==object_hash(config)
        and object_hash(load(root/'initial-state.json'))==object_hash(initial)
        and object_hash(load(root/'input-manifest.json'))==object_hash(_input_manifest(result,drc,layout,configuration))
        and sha(root/'pdk-input-manifest.json')==runtime['pdk_manifest_sha256']
        and sha(root/'lvs_tools.py')==result.get('adapter_source_sha256')
        and sha(root/'capture_lvs_versions.py')==result.get('version_capture_sha256'),
        'lvs_input_conflict','Retain the failed execution source/configuration/provenance bytes.')
    _validate_variant(configuration['profile'],root,root,commands[1]['stdout'])
    versions=load(root/'tool-versions.json')
    require(versions.get('librelane')==physical.RELEASE and set(versions.get('tools',{}))=={'magic','netgen'}
        and all(type(v.get('exit_code')) is int and v['exit_code']==0
            and (v.get('stdout','')+v.get('stderr','')).strip() for v in versions['tools'].values()),
        'lvs_version_conflict','Retain successful actual tool-version queries before the failed extraction.')
    retained=result.get('retained_files')
    require(type(retained) is list and len({e['relative_path'] for e in retained})==len(retained),
        'lvs_retained_invalid','Retain unique complete failed-execution records.')
    required={'config.json','initial-state.json','input-manifest.json','source-layout-state.json',
        'input.gds','input.def','input.nl.v','input.pnl.v','pdk-input-manifest.json',
        'lvs_tools.py','capture_lvs_versions.py','tool-versions.json'}|set(_variant_files(configuration['profile']))
    required|={op+'/'+name for op in ('version','lvs') for name in
        ('request.json','process-result.json','process-start.json','worker.py','stdout.log','stderr.log')}
    require(required<={e['relative_path'] for e in retained},'lvs_retained_invalid','Missing failed-execution proof.')
    for entry in retained:
        path=_safe(root,entry['relative_path'])
        require(type(entry['bytes']) is int and file_stat(path).st_size==entry['bytes'] and sha(path)==entry['sha256'],
            'lvs_retained_changed','A retained failed-execution artifact changed.')
    return {'validation_status':'Passed','scope':'actual_failed_'+version.rsplit('-',1)[-1]+'_execution_proof_only_not_LVS_success'}


def validate_lvs_result(result,drc,layout,configuration,artifact_root=None):
    """Pure retained-evidence validation; alternate root never reads live inputs."""
    profile=configuration.get('profile');files=_fixed_files(layout,profile);types=_file_types(profile)
    config=configuration_projection(drc,layout,configuration)
    logical=Path(result['artifacts_directory']).resolve();root=Path(artifact_root).resolve() if artifact_root else logical
    inputs=result.get('source_inputs',{})
    require(type(inputs) is dict and set(inputs)=={'gds','def','netlist','powered_netlist'},'lvs_source_conflict','Require all four frozen source descriptors.')
    if _recognition_profile(profile):
        require(configuration['repair_source_binding']['source_inputs_sha256']==object_hash(inputs),
                'lvs_repair_source_conflict','The correction must retain all four exact original source descriptors.')
    for identifier in ('gds','def','netlist'):
        expected=next(e for e in layout['checks']['artifacts'] if e['id']==identifier)
        require(object_hash(inputs[identifier])==object_hash(expected),'lvs_source_conflict','Preserve adopted S11 source descriptors.')
    powered=inputs['powered_netlist']
    require(powered.get('origin')=='original_S11_state_pointer_observed_at_S13_start','lvs_source_conflict','Do not claim a new powered-netlist hash was retained in S11.')
    original_state=next(e for e in layout['checks']['artifacts'] if e['id']=='final-state')
    state_path=_safe(root,'source-layout-state.json')
    require(sha(state_path)==original_state['sha256'] and file_stat(state_path).st_size==original_state['bytes'],
            'lvs_source_conflict','Retain the original adopted S11 state bytes containing the powered companion pointer.')
    original_folder=Path(layout['checks']['artifacts_directory']).resolve();source_state=physical.load_tool_json(state_path)
    for identifier,key in (('gds','gds'),('def','def'),('netlist','nl'),('powered_netlist','pnl')):
        require(_pointer_relative(source_state[key],original_folder)==inputs[identifier]['relative_path'],
                'lvs_source_conflict','Frozen input descriptors must follow the unchanged adopted S11 state pointers.')
    require(result.get('origin')=='trusted_fixed_lvs_adapter' and result.get('scope')==SCOPE
        and result.get('drc_run_id')==drc['id'] and result.get('drc_record_sha256')==object_hash(drc)
        and result.get('layout_run_id')==layout['id'] and result.get('layout_record_sha256')==object_hash(layout)
        and result.get('configuration_sha256')==object_hash(configuration)
        and result.get('input_gds_sha256')==inputs['gds']['sha256'] and result.get('input_netlist_sha256')==inputs['netlist']['sha256']
        and result.get('input_powered_netlist_sha256')==powered['sha256'],'lvs_source_conflict','Preserve exact full S12/S11 records, inputs and runtime.')
    require(result.get('status')=='Completed' and result.get('executed') is True and type(result.get('exit_code')) is int
        and result['exit_code']==0 and result.get('cleanup_unresolved') is False and len(result.get('commands',[]))==2,
        'lvs_execution_conflict','Both actual fixed commands must complete with verified cleanup.')
    runtime=configuration['physical_runtime']
    for operation,record,command,timeout in zip(('version','lvs'),result['commands'],fixed_commands(configuration,logical),(120,7200)):
        logs=root/operation;logical_logs=logical/operation
        request=load(logs/'request.json');terminal=load(logs/'process-result.json');start=load(logs/'process-start.json');worker_sha=sha(logs/'worker.py')
        expected={'version':'hullcirq-physical-worker-v2','argv':command[command.index('--exec')+1:],'cwd':_wsl_path(logical),
                  'timeout_seconds':timeout,'worker_sha256':physical.WORKER_V2_SHA}
        supervisor=trusted_command(runtime,'/usr/bin/python3',[_wsl_path(logical_logs/'worker.py'),_wsl_path(logical_logs/'request.json'),
            '--request-sha256',sha(logs/'request.json'),'--worker-sha256',worker_sha],logical)
        require(worker_sha==physical.WORKER_V2_SHA and record.get('worker_sha256')==worker_sha and record.get('command')==command
            and record.get('supervisor_command')==supervisor and object_hash(request)==object_hash(expected)
            and record.get('request_sha256')==sha(logs/'request.json') and record.get('process_start_sha256')==sha(logs/'process-start.json')
            and record.get('status')=='Completed' and record.get('executed') is True and type(record.get('exit_code')) is int and record['exit_code']==0
            and all(object_hash(record.get(k))==object_hash(v) for k,v in terminal.items())
            and record.get('request_unchanged_at_completion') is True and record.get('worker_unchanged_at_completion') is True
            and record.get('observed_child_cwd') in (None,_wsl_path(logical)),
            'lvs_worker_conflict','The actual frozen worker/request/birth/exit must match the fixed LVS recipe.')
        physical.validate_worker_binding(request,record,start,logical,worker_sha)
        require(record.get('stdout')==read_text((logs/'stdout.log'),encoding='utf-8',errors='replace')
            and record.get('stderr')==read_text((logs/'stderr.log'),encoding='utf-8',errors='replace'),'lvs_log_conflict','Preserve complete actual raw logs.')
    require(result['stdout']==''.join(r['stdout'] for r in result['commands']) and result['stderr']==''.join(r['stderr'] for r in result['commands']),
            'lvs_log_conflict','Preserve both command logs.')
    require(not re.search(r'(?im)^\s*(?:fatal(?: error)?|error)(?:\s|:)',result['stdout']+'\n'+result['stderr']),
            'lvs_tool_fatal','A zero exit cannot override a raw fatal/error message.')
    _validate_native_recognition_diagnostics(profile,result['stdout'],result['stderr'])
    entries=result.get('artifacts',[])
    require(type(entries) is list and len(entries)==len(types) and {e['id'] for e in entries}==set(types),
            'lvs_artifact_missing','Require complete fixed extraction and comparison artifacts.')
    for entry in entries:
        require(entry['relative_path']==files[entry['id']] and entry['content_type']==types[entry['id']],
                'lvs_artifact_conflict','Require exact fixed raw artifact names and types.')
        p=_safe(root,entry['relative_path'])
        require(type(entry['bytes']) is int and entry['bytes']>=(0 if entry['id']=='extraction-feedback' else 1)
            and file_stat(p).st_size==entry['bytes'] and sha(p)==entry['sha256'],'lvs_artifact_changed','A retained artifact changed.')
    for identifier,filename in (('gds','input.gds'),('def','input.def'),('netlist','input.nl.v'),('powered_netlist','input.pnl.v')):
        p=root/filename;e=inputs[identifier]
        require(file_stat(p).st_size==e['bytes'] and sha(p)==e['sha256'],'lvs_input_conflict','Staged input bytes differ from frozen sources.')
    binding=bind_powered_netlist(read_text((root/'input.nl.v'),encoding='utf-8'),read_text((root/'input.pnl.v'),encoding='utf-8'),
        read_text((root/'input.def'),encoding='utf-8'),layout['settings']['top_module'])
    require(object_hash(binding)==object_hash(powered['binding']),'lvs_input_conflict','Reconstruct the powered signal graph/DEF/supply binding.')
    initial={'gds':_wsl_path(logical/'input.gds'),'def':_wsl_path(logical/'input.def'),'nl':_wsl_path(logical/'input.nl.v'),
             'pnl':_wsl_path(logical/'input.pnl.v'),'metrics':{}}
    require(object_hash(load(root/'config.json'))==object_hash(config) and object_hash(load(root/'initial-state.json'))==object_hash(initial)
        and object_hash(load(root/'input-manifest.json'))==object_hash(_input_manifest(result,drc,layout,configuration)),
        'lvs_input_conflict','Freeze exact configuration, empty initial metrics and input provenance.')
    require(sha(root/'pdk-input-manifest.json')==runtime['pdk_manifest_sha256']
        and load(root/'pdk-input-manifest.json')['ciel_revision']==physical.PDK_REVISION
        and sha(root/'lvs_tools.py')==result.get('adapter_source_sha256')
        and sha(root/'capture_lvs_versions.py')==result.get('version_capture_sha256'),
        'lvs_runtime_conflict','Retain the pinned PDK manifest and both frozen adapter sources.')
    _validate_variant(configuration['profile'],root,logical,result['commands'][1]['stdout'])
    versions=load(root/'tool-versions.json')
    require(versions.get('librelane')==physical.RELEASE and set(versions.get('tools',{}))=={'magic','netgen'}
        and all(type(v.get('exit_code')) is int and v['exit_code']==0 and (v.get('stdout','')+v.get('stderr','')).strip()
                for v in versions['tools'].values()),'lvs_version_conflict','Require successful actual Magic/Netgen version queries.')
    for step in ('1-magic-spiceextraction','2-netgen-lvs'):
        resolved=load(root/'runs/lvs'/step/'config.json')
        require(resolved.get('DESIGN_NAME')==layout['settings']['top_module'] and resolved.get('MAGIC_EXT_USE_GDS') is True,
                'lvs_configuration_conflict','Use the original top and direct full GDS extraction.')
        if step.startswith('1'):
            require(resolved.get('MAGIC_EXT_ABSTRACT') is False and resolved.get('MAGIC_EXT_ABSTRACT_CELLS') in (None,[])
                and resolved.get('MAGIC_EXT_UNIQUE')=='all' and resolved.get('MAGIC_EXT_SHORT_RESISTOR') is False
                and str(resolved.get('MAGICRC','')).endswith('/libs.tech/magic/sky130A.magicrc'),
                'lvs_configuration_conflict','Do not replace full geometry with abstract extraction.')
            require(resolved['MAGICRC']==_wsl_path(Path(load(root/'pdk-input-manifest.json')['root'])/'libs.tech/magic/sky130A.magicrc'),
                    'lvs_configuration_conflict','Use the exact pinned Magic startup file.')
        else:
            require(resolved.get('LVS_FLATTEN_CELLS') in (None,[]) and resolved.get('LVS_IGNORE_CELLS') in (None,[])
                and resolved.get('LVS_INCLUDE_MARCO_NETLISTS') is False and resolved.get('CELL_SPICE_MODELS')
                and not resolved.get('SPICE_MODELS') and not resolved.get('EXTRA_SPICE_MODELS') and not resolved.get('PAD_SPICE_MODELS')
                and str(resolved.get('NETGEN_SETUP','')).endswith('/libs.tech/netgen/sky130A_setup.tcl'),
                'lvs_configuration_conflict','Require pinned cell SPICE and no added ignore/flatten or model substitutions.')
            pdk=Path(load(root/'pdk-input-manifest.json')['root'])
            model_paths=[_wsl_path(pdk/relative) for relative in load(root/'pdk-input-manifest.json')['files']
                         if relative.startswith('libs.ref/sky130_fd_sc_hd/spice/') and relative.endswith('.spice')]
            require(resolved['NETGEN_SETUP']==_wsl_path(pdk/'libs.tech/netgen/sky130A_setup.tcl')
                and type(resolved['CELL_SPICE_MODELS']) is list and len(resolved['CELL_SPICE_MODELS'])==len(model_paths)
                and set(resolved['CELL_SPICE_MODELS'])==set(model_paths),
                'lvs_configuration_conflict','Use the exact pinned Netgen setup and complete HD cell SPICE input.')
    state=load(root/files['final-state']);summary,metrics,checks=summarize(root,layout,configuration['profile'],logical)
    require(all(state.get(k)==v for k,v in initial.items() if k!='metrics') and object_hash(state.get('metrics'))==object_hash(metrics)
        and object_hash(result.get('metrics'))==object_hash(metrics) and object_hash(result.get('checks'))==object_hash(checks)
        and object_hash(load(root/'lvs-summary.json'))==object_hash(summary) and object_hash(result.get('summary'))==object_hash(summary)
        and result.get('validation_status')==('Passed' if all(c['validation_status']=='Passed' for c in checks.values()) else 'Failed'),
        'lvs_result_conflict','Reconstruct extraction and LVS checks from complete raw outputs.')
    retained=result.get('retained_files',[])
    require(type(retained) is list and len({e['relative_path'] for e in retained})==len(retained),'lvs_retained_invalid','Require unique complete raw records.')
    mandatory=set(files.values())|{'input-manifest.json','pdk-input-manifest.json','lvs_tools.py','capture_lvs_versions.py','source-layout-state.json'}
    mandatory|={op+'/'+name for op in ('version','lvs') for name in ('request.json','process-result.json','process-start.json','worker.py','stdout.log','stderr.log')}
    mandatory|={'runs/lvs/'+step+'/config.json' for step in ('1-magic-spiceextraction','2-netgen-lvs')}
    mandatory|=set(_variant_files(configuration['profile']))
    if configuration['profile'].get('force_full_extraction'):mandatory.add('runs/lvs/1-magic-spiceextraction/COMMANDS')
    require(mandatory<={e['relative_path'] for e in retained},'lvs_retained_invalid','The retained manifest must include every fixed artifact, input and execution proof.')
    for e in retained:
        p=_safe(root,e['relative_path'])
        require(file_stat(p).st_size==e['bytes'] and sha(p)==e['sha256'],'lvs_retained_changed','A retained raw record changed.')

def _retain(result,layout,profile=None):
    files=_fixed_files(layout,profile);types=_file_types(profile)
    root=Path(result['artifacts_directory'])
    result['artifacts']=[{'id':k,'kind':'lvs','relative_path':v,'sha256':sha(root/v),'bytes':file_stat((root/v)).st_size,'content_type':types[k]}
        for k,v in files.items() if file_exists((root/v))]
    result['retained_files']=[{'relative_path':p.relative_to(root).as_posix(),'sha256':sha(p),'bytes':file_stat(p).st_size}
        for p in sorted(artifact_files(root)) if file_exists(p) and p.name!='adapter-report.json']

def run_lvs(drc,layout,configuration,cancel_event=None):
    config=configuration_projection(drc,layout,configuration);runtime=configuration['physical_runtime'];inputs=source_inputs(layout)
    if _recognition_profile(configuration['profile']):
        require(configuration['repair_source_binding']['source_inputs_sha256']==object_hash(inputs),
                'lvs_repair_source_conflict','Use the unchanged original four source inputs for the corrected extraction.')
    parent=Path(configuration['working_directory']).resolve();parent.mkdir(parents=True,exist_ok=True)
    root=Path(tempfile.mkdtemp(prefix='hullcirq-lvs-',dir=parent))
    result={'origin':'trusted_fixed_lvs_adapter','scope':SCOPE,'status':'Failed','validation_status':'Failed','executed':False,'exit_code':None,
        'drc_run_id':drc['id'],'drc_record_sha256':object_hash(drc),'layout_run_id':layout['id'],'layout_record_sha256':object_hash(layout),
        'source_inputs':inputs,'input_gds_sha256':inputs['gds']['sha256'],'input_netlist_sha256':inputs['netlist']['sha256'],
        'input_powered_netlist_sha256':inputs['powered_netlist']['sha256'],'configuration_sha256':object_hash(configuration),
        'artifacts_directory':str(root),'commands':[],'checks':{},'metrics':{},'artifacts':[],'retained_files':[],'diagnostics':[],
        'stdout':'','stderr':'','cleanup_unresolved':False,'adapter_source_sha256':sha(Path(__file__)),
        'version_capture_sha256':sha(ROOT/'scripts/capture_lvs_versions.py')}
    try:
        require(sha(runtime['appimage_path'])==physical.IMAGE_SHA and sha(runtime['pdk_manifest_path'])==runtime['pdk_manifest_sha256'],
                'lvs_runtime_changed','Pinned AppImage or PDK manifest bytes changed.')
        manifest=load(runtime['pdk_manifest_path']);pdk=Path(manifest['root']).absolute()
        require(manifest['ciel_revision']==physical.PDK_REVISION and pdk.is_relative_to(Path(runtime['pdk_root']).resolve()),
                'lvs_pdk_changed','Require the same pinned PDK directory.')
        for relative,e in manifest['files'].items():
            physical.verify_pdk_file(pdk,relative,e,'lvs_pdk_changed')
        for relative,digest in configuration['profile']['deck_files'].items():
            require(sha(_safe(pdk,relative))==digest,'lvs_deck_changed','A pinned extraction/LVS deck changed.')
        for identifier,filename in (('gds','input.gds'),('def','input.def'),('netlist','input.nl.v'),('powered_netlist','input.pnl.v')):
            p=_safe(Path(layout['checks']['artifacts_directory']).resolve(),inputs[identifier]['relative_path'])
            (root/filename).write_bytes(read_bytes(p))
            require(sha(root/filename)==inputs[identifier]['sha256'],'lvs_input_changed','Source changed during staging.')
        for source,destination in ((Path(__file__),'lvs_tools.py'),(ROOT/'scripts/capture_lvs_versions.py','capture_lvs_versions.py'),
                (Path(runtime['pdk_manifest_path']),'pdk-input-manifest.json')):(root/destination).write_bytes(read_bytes(source))
        for name,(source,digest) in _variant_files(configuration['profile']).items():
            (root/name).write_bytes(read_bytes(source))
            require(sha(root/name)==digest,'lvs_adapter_source_conflict','Full-extraction sources changed during freeze.')
        original_state=next(e for e in layout['checks']['artifacts'] if e['id']=='final-state')
        (root/'source-layout-state.json').write_bytes(read_bytes(_safe(Path(layout['checks']['artifacts_directory']).resolve(),original_state['relative_path'])))
        require(sha(root/'lvs_tools.py')==result['adapter_source_sha256'] and sha(root/'capture_lvs_versions.py')==result['version_capture_sha256'],
                'lvs_adapter_source_conflict','Adapter source changed during freeze.')
        initial={'gds':_wsl_path(root/'input.gds'),'def':_wsl_path(root/'input.def'),'nl':_wsl_path(root/'input.nl.v'),
                 'pnl':_wsl_path(root/'input.pnl.v'),'metrics':{}}
        for name,value in (('config.json',config),('initial-state.json',initial),('input-manifest.json',_input_manifest(result,drc,layout,configuration))):
            (root/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for operation,command,timeout in zip(('version','lvs'),fixed_commands(configuration,root),(120,7200)):
            execution=physical._execute(command,runtime,root,operation,cancel_event,timeout)
            result['commands'].append(execution);result['stdout']+=execution['stdout'];result['stderr']+=execution['stderr']
            result['executed']=any(c['executed'] for c in result['commands']);result['exit_code']=execution['exit_code']
            result['cleanup_unresolved']=execution.get('cleanup_unresolved') is True
            if execution['status']!='Completed' or execution['exit_code']!=0:
                result['status']='Cancelled' if execution['status']=='Cancelled' else 'Failed'
                if not physical._record_cancelled_command(result, execution, 'lvs'):
                    result['diagnostics'].append({'code':'lvs_tool_failed','severity':'error','message':'Inspect retained '+operation+' output: '+execution['status']})
                return result
        result['status']='Completed';summary,metrics,checks=summarize(root,layout,configuration['profile'])
        (root/'lvs-summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        result.update(metrics=metrics,checks=checks,summary=summary,validation_status='Passed' if all(c['validation_status']=='Passed' for c in checks.values()) else 'Failed')
        if summary['extraction']['non_overlap_feedback_count']:
            result['diagnostics'].append({'code':'lvs_extraction_feedback','severity':'warning',
                'message':str(summary['extraction']['non_overlap_feedback_count'])+' non-overlap extraction feedback items remain recorded; inspect every description and geometry. The connectivity match does not establish that these warnings are harmless or resolved.'})
        if result['validation_status']=='Failed':result['diagnostics'].append({'code':'lvs_mismatch','severity':'error','message':'Actual extraction or circuit mismatch remains; inspect full raw reports.'})
        _retain(result,layout,configuration['profile']);validate_lvs_result(result,drc,layout,configuration)
    except (DomainError,OSError,ValueError,KeyError,TypeError,StopIteration,ET.ParseError) as error:
        result['validation_status']='Failed';result['diagnostics'].append({'code':getattr(error,'code','lvs_tool_error'),'severity':'error','message':str(error)})
    finally:_retain(result,layout,configuration['profile'])
    return result

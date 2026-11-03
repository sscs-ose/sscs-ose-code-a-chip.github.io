"""Verify a post-diode checkpoint; import it only AFTER fresh native prep.

Never clone a run directory, source its config.tcl, overwrite evidence, or
borrow old metrics. Only routing resource knobs may differ from source config.
"""
from pathlib import Path
import json,re
from scripts import flow2_integration_common as common

TUNABLE={'GRT_ADJUSTMENT','GRT_OVERFLOW_ITERS','DRT_OPT_ITERS','ROUTING_CORES','RT_MIN_LAYER','DRT_MIN_LAYER','GRT_ALLOW_CONGESTION'}
FILE_KEYS={'VERILOG_FILES','VERILOG_FILES_BLACKBOX','EXTRA_LEFS','EXTRA_GDS_FILES',
           'MACRO_PLACEMENT_CFG','FP_PDN_CFG'}


def compare_configs(source,target):
    if (set(source)^set(target))-TUNABLE:raise ValueError('checkpoint config keys differ')
    for key in source:
        if key in TUNABLE:continue
        if key in FILE_KEYS:
            a=source[key] if isinstance(source[key],list) else [source[key]]
            b=target[key] if isinstance(target[key],list) else [target[key]]
            if len(a)!=len(b) or [common._sha(Path(x)) for x in a]!=[common._sha(Path(x)) for x in b]:
                raise ValueError('checkpoint circuit/view changed: '+key)
        elif source[key]!=target[key]:raise ValueError('checkpoint config changed: '+key)


def prepare(root,source_tag,target_config,build,openlane_pdk,openlane_source,stage='post_diode'):
    root,build=Path(root).resolve(),Path(build);common.tag_ok(source_tag)
    source=root/common.BUILD/source_tag/'design/runs'/source_tag
    summary=json.loads((root/common.BASE/source_tag/'summary.json').read_text())
    failure=summary.get('primary_failure') or {}
    if stage not in ('post_diode','post_cts'):raise ValueError('unsupported checkpoint stage')
    if stage=='post_diode' and not any('GRT-0119' in x for x in failure.get('errors',[])):
        raise ValueError('source must have an actual routing-congestion failure')
    if stage=='post_cts':
        expected="TypeError: '<' not supported between instances of 'tuple' and 'list'"
        if failure.get('phase')!='POST_CTS_FANOUT' or expected not in failure.get('errors',[]):
            raise ValueError('post-CTS recovery requires the measured location-sort failure')
        if (source/'tmp/wrapper_fanout/split.odb').exists():
            raise ValueError('failed splitter unexpectedly wrote output; inspect before recovery')
    inputs=json.loads((root/common.BASE/source_tag/'inputs.json').read_text())
    repairs=[]
    for item in inputs['sources']:
        if stage=='post_cts' and item['path']=='scripts/flow2_split_fanout_odb.py':
            saved=source.parent.parent.parent/'executed_host_sources/flow2_split_fanout_odb.py'
            current=root/item['path']
            if not saved.is_file() or common._sha(saved)!=item['sha256']:
                raise ValueError('original failed splitter source snapshot required')
            before=saved.read_text();after=current.read_text()
            old='return pin.getInst().getLocation()';new='return tuple(pin.getInst().getLocation())'
            if before.count(old)!=1 or before.replace(old,new)!=after:
                raise ValueError('only the exact location normalization repair is allowed')
            repairs.append({'before':common._item(root,saved),'after':common._item(root,current),
                            'reason':'post-CTS fanout stage failed before output; normalize OpenDB coordinates'})
        else:common._verified(root,item)
    if summary.get('pdn',{}).get('status')!='PASS_WRAPPER_PDN_CONNECTIVITY':
        raise ValueError('source PDN evidence required')
    old=json.loads((source.parent.parent/'config.json').read_text());compare_configs(old,target_config)
    config=source/'config.tcl';text=config.read_text()
    paths={}
    for key in ['CURRENT_ODB','CURRENT_DEF','CURRENT_NETLIST','CURRENT_POWERED_NETLIST','CURRENT_SDC']:
        match=re.search(r'^set ::env\('+key+r'\) "([^"\n]+)"$',text,re.M)
        if not match:
            if key=='CURRENT_POWERED_NETLIST':continue
            raise ValueError('missing checkpoint '+key)
        p=Path(match[1]).resolve()
        if not p.is_relative_to(source) or not p.is_file():raise ValueError('unsafe/missing checkpoint '+key)
        paths[key]=p
    if stage=='post_diode' and 'diodes_legalized' not in paths['CURRENT_ODB'].name:
        raise ValueError('only post-diode legalized source is supported')
    if stage=='post_cts' and (paths['CURRENT_ODB'].parent!=source/'results/cts' or
                             paths['CURRENT_SDC'].parent!=source/'results/cts'):
        raise ValueError('measured CTS ODB and matching CTS SDC required')
    match=re.search(r'^set ::env\(PDKPATH\) "([^"\n]+)"$',text,re.M)
    if not match or Path(match[1]).resolve()!=(Path(openlane_pdk)/'sky130A').resolve():
        raise ValueError('native PDK differs from checkpoint')
    if (source/'OPENLANE_VERSION').read_text().strip()!='OpenLane 30ee1388932eb55a89ad84ee43997bfe3a386421':
        raise ValueError('OpenLane revision differs')
    if (source/'PDK_SOURCES').read_text().strip()!=(Path(openlane_pdk)/'sky130A/SOURCES').read_text().strip():
        raise ValueError('native PDK sources differ')
    proof={'source_tag':source_tag,'mode':'FRESH_PREP_THEN_VERIFIED_'+stage.upper()+'_IMPORT',
        'checkpoint_stage':stage,'stage_source_repairs':repairs,
        'inputs':[common._item(root,p) for p in [config,source/'OPENLANE_VERSION',source/'PDK_SOURCES',*paths.values()]],
        'routing_changes':{k:{'old':old.get(k),'new':target_config.get(k)} for k in TUNABLE},
        'source_native_status':summary['status'],'source_synthesis_placement_CTS':'REUSED_NOT_REMEASURED'}
    pdn_script=build/'import_pdn.tcl'
    pdn_script.write_text('''source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read
check_power_grid -net VPWR
check_power_grid -net VGND
write
''')
    lines=['proc automx_import_verified_route_checkpoint {} {',
        '    set dest [file join $::env(RUN_DIR) tmp imported_checkpoint]',
        '    file mkdir $dest']
    for key,path in paths.items():
        lines+=['    file copy {'+str(path)+'} [file join $dest {'+path.name+'}]',
                '    set ::env('+key+') [file join $dest {'+path.name+'}]']
    lines+=['    set ::env(IO_READ_DEF) 0','    set ::env(CURRENT_INDEX) 0',
        '    increment_index',
        '    run_openroad_script {'+str(pdn_script)+'} -indexed_log [index_file $::env(floorplan_logs)/pdn.log] -save "to=$::env(floorplan_results),name=$::env(DESIGN_NAME),noindex,def,odb"']
    if stage=='post_cts':lines+=['    automx_wrapper_finish_cts_fanout']
    else:lines+=['    set ::env(RUN_HEURISTIC_DIODE_INSERTION) 0','    set ::env(DIODE_ON_PORTS) none']
    lines+=['    puts AUTOMX_VERIFIED_POST_PREP_CHECKPOINT_IMPORTED','}', '']
    common._save(build/'route_checkpoint.json',proof)
    return '\n'.join(lines),proof


def patch_driver(text):
    marker='    prep {*}$args\n    # signal trap'
    start='    set ::env(CURRENT_STEP) "verilator_lint_check"'
    if text.count(marker)!=1 or text.count(start)!=1:
        raise ValueError('unknown pinned native prep/step contract')
    return text.replace(marker,'    prep {*}$args\n    automx_import_verified_route_checkpoint\n    # signal trap',1).replace(start,'    set ::env(CURRENT_STEP) "routing"',1)

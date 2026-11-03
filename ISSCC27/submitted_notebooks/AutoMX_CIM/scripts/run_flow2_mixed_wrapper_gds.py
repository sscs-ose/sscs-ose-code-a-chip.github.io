#!/usr/bin/env python3
"""Harden the actual core/front + conditioner + ADC + sequencer prototype.

This is an integration experiment. Strict Stage-8 preflight is unchanged:
analog timing/accuracy need characterization beyond the digital boundary LIB.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_integration_common as common
from scripts import flow2_wrapper_design as d
from scripts import flow2_wrapper_physical as physical
from scripts import flow2_adc_c_only as reduction
from scripts import prepare_flow2_mixed_wrapper as prepare
from scripts import run_flow2_acquisition_layout as acq
from scripts import run_flow2_adc_finish as finish
from scripts import run_notebook_core_bound as notebook
from scripts import run_flow2_core_bound_fanout as fanout
from scripts import audit_core_bound_clean as timing
from scripts import flow2_wrapper_pdn as pdn
from scripts import flow2_wrapper_container_runtime as container_runtime

PDK_GATE_SETTINGS={"RUN_LINTER":1,"QUIT_ON_LINTER_ERRORS":1,
    "LINTER_INCLUDE_PDK_MODELS":1,"SYNTH_READ_BLACKBOX_LIB":1,
    "QUIT_ON_SYNTH_CHECKS":1,"QUIT_ON_UNMAPPED_CELLS":1}
PROTOTYPE_DIE=(3600,1400)
ANALOG_RESIZER_PROTECTION=r'^(BIAS_MON|AIN[PN]|H[PN][0-3])$'


def routing_settings(options=None):
    values={"GRT_OVERFLOW_ITERS":30,"DRT_OPT_ITERS":16,"GRT_ADJUSTMENT":.15,"ROUTING_CORES":8,
            "RT_MIN_LAYER":"met1","DRT_MIN_LAYER":"met1"}
    if options:
        if set(options)-set(values)-{'GRT_ALLOW_CONGESTION'}:raise ValueError('unsupported routing option')
        values.update(options)
    if 'GRT_ALLOW_CONGESTION' in values and (type(values['GRT_ALLOW_CONGESTION']) is not int or values['GRT_ALLOW_CONGESTION'] not in (0,1)):
        raise ValueError('GRT_ALLOW_CONGESTION must be 0 or 1; detailed-route and signoff gates remain required')
    if any(values[k] not in ('met1','met2') for k in ('RT_MIN_LAYER','DRT_MIN_LAYER')):
        raise ValueError('prototype routing minimum layer must be met1 or met2')
    if any(type(values[k]) is not int for k in ('ROUTING_CORES','GRT_OVERFLOW_ITERS','DRT_OPT_ITERS')) or \
            not 1<=values['ROUTING_CORES']<=16 or not 1<=values['GRT_OVERFLOW_ITERS']<=100 or \
            not 1<=values['DRT_OPT_ITERS']<=64:
        raise ValueError('invalid routing threads/iterations')
    if not 0<=values['GRT_ADJUSTMENT']<1:raise ValueError('invalid routing reserve')
    return values


def inherit_checkpoint_analog_policy(configuration,source_configuration):
    result=dict(configuration)
    if 'RSZ_DONT_TOUCH_RX' in source_configuration:
        result['RSZ_DONT_TOUCH_RX']=source_configuration['RSZ_DONT_TOUCH_RX']
    else:result.pop('RSZ_DONT_TOUCH_RX',None)
    return result


def config(root, design_dir, core_views, cond_views, adc_gds, routing_options=None):
    absfile=lambda name:str((design_dir/name).resolve())
    return {"DESIGN_NAME":d.TOP,"VERILOG_FILES":[str(root/"rtl/automx_cim_readout_seq.sv"),absfile(d.TOP+".sv")],
        "VERILOG_FILES_BLACKBOX":absfile("wrapper_blackboxes.sv"),
        # The PWM chain directly instantiates real SKY130 buffers. Both
        # Verilator and Yosys must load their PDK definitions. The standalone
        # transaction TB has its own fixture and cannot validate this binding.
        **PDK_GATE_SETTINGS,
        "EXTRA_LEFS":[str(core_views["lef"]),str(cond_views["lef"]),absfile("adc_top.power_access.lef")],
        "EXTRA_GDS_FILES":[str(core_views["gds"]),str(cond_views["gds"]),str(adc_gds)],
        "MACRO_PLACEMENT_CFG":absfile("macro_placement.cfg"),
        "CLOCK_PORT":"clk_i","CLOCK_PERIOD":20,"DESIGN_IS_CORE":1,
        "FP_SIZING":"absolute","DIE_AREA":"0 0 %s %s"%PROTOTYPE_DIE,"FP_CORE_UTIL":15,"PL_TARGET_DENSITY":.20,
        "VDD_NETS":"VPWR","GND_NETS":"VGND",
        "FP_PDN_MACRO_HOOKS":"core_i VPWR VGND VPWR VGND, condition_i VPWR VGND VPWR VGND, adc_i VPWR VGND VDD VSS",
        "FP_PDN_CFG":str(root/pdn.PDN_TCL),"FP_PDN_CHECK_NODES":1,
        "RUN_LVS":1,"LVS_INSERT_POWER_PINS":1,"QUIT_ON_LVS_ERROR":1,
        "RUN_MAGIC_DRC":1,"MAGIC_DRC_USE_GDS":1,"QUIT_ON_MAGIC_DRC":1,
        "RUN_KLAYOUT_DRC":1,"QUIT_ON_TR_DRC":1,"RUN_CVC":0,
        "RUN_SPEF_EXTRACTION":1,"STA_WRITE_LIB":1,
        # Measure timing, but allow a slower prototype to publish its layout.
        "QUIT_ON_TIMING_VIOLATIONS":0,"QUIT_ON_SETUP_VIOLATIONS":0,"QUIT_ON_HOLD_VIOLATIONS":0,
        # Avoid two expensive preliminary global routes before the final one.
        "GLB_RESIZER_DESIGN_OPTIMIZATIONS":0,"GLB_RESIZER_TIMING_OPTIMIZATIONS":0,
        **routing_settings(routing_options),
        "RUN_HEURISTIC_DIODE_INSERTION":1,"HEURISTIC_ANTENNA_THRESHOLD":20,
        "CTS_SINK_CLUSTERING_SIZE":4,"MAX_FANOUT_CONSTRAINT":10,
        # These are transistor voltages, including the external bias monitor.
        # Port buffering/resizing must not replace them with logic levels.
        "RSZ_DONT_TOUCH_RX":ANALOG_RESIZER_PROTECTION,
        # Pinned OpenLane's set_routing_layers.tcl consumes RT_MIN_LAYER;
        # GRT_MIN_LAYER is ignored there. DRT_MIN_LAYER retains met1 access.
        "GPL_CELL_PADDING":2,"DPL_CELL_PADDING":2,"GRT_MIN_LAYER":"met2"}


PLACEMENTS={'core_i':(50.,50.),'condition_i':(1100.,50.),'adc_i':(3100.,50.)}


def floorplan_geometry(lefs):
    boxes={}
    for inst,path in lefs.items():
        text=Path(path).read_text(encoding='utf-8')
        m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;',text)
        if not m:raise ValueError('LEF size missing: '+inst)
        w,h=map(float,m.groups());x,y=PLACEMENTS[inst]
        if min(w,h)<=0 or x-20<0 or y-20<0 or x+w+20>PROTOTYPE_DIE[0] or y+h+20>PROTOTYPE_DIE[1]:
            raise ValueError('macro/PG margin does not fit wrapper die: '+inst)
        boxes[inst]=[x,y,x+w,y+h]
    names=list(boxes)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            aa,bb=boxes[a],boxes[b]
            if not (aa[2]+20<=bb[0] or bb[2]+20<=aa[0] or aa[3]+20<=bb[1] or bb[3]+20<=aa[1]):
                raise ValueError('macro halos overlap: '+a+'/'+b)
    return boxes


def core_views(root, previous):
    tag=previous["child_tags"]["core"]
    frozen=root/common.BASE/tag/"layout.step.json"
    receipt=json.loads(frozen.read_text(encoding="utf-8"))
    if receipt.get("returncode")!=0:raise ValueError("source composite layout is not complete")
    out={}
    for key,suffix in (("gds",".gds"),("lef",".lef")):
        matches=[v for v in receipt["artifacts"] if v["path"].endswith('/'+d.core.CELL+suffix)]
        if len(matches)!=1:raise ValueError("ambiguous source composite view")
        source=common._verified(root,matches[0])
        published=root/common.PHYSICAL/tag/(d.core.CELL+suffix)
        if not published.is_file() or common._sha(source)!=common._sha(published):
            raise ValueError("published core/front view differs from passed layout")
        out[key]=published
    out["schematic"]=root/common.PHYSICAL/tag/(d.core.CELL+".reference.spice")
    if not out["schematic"].is_file():raise FileNotFoundError(out["schematic"])
    return out


def fanout_hook(root):
    return f'''if {{[llength [info procs run_cts]] != 1}} {{error "run_cts missing"}}
rename run_cts automx_wrapper_original_cts
proc run_cts {{args}} {{
    automx_wrapper_original_cts {{*}}$args
    automx_wrapper_finish_cts_fanout
}}
proc automx_wrapper_finish_cts_fanout {{}} {{
    set dest [file join $::env(RUN_DIR) tmp wrapper_fanout]
    file mkdir $dest
    set output [file join $dest split.odb]
    set split_log [file join $dest split.log]
    if {{[catch {{exec $::env(OPENROAD_BIN) -exit -no_init -python {{{(root/fanout.SPLITTER).as_posix()}}} --input-odb $::env(CURRENT_ODB) --output-odb $output --report [file join $dest topology.json] --limit 4 >$split_log 2>@1}} detail options]}} {{
        set stream [open $split_log r]
        puts stderr [read $stream]
        close $stream
        return -options $options $detail
    }}
    set ::env(CURRENT_ODB) $output
    set ::env(IO_READ_DEF) 0
    increment_index
    run_openroad_script {{{(root/fanout.LEGALIZE).as_posix()}}} -indexed_log [index_file $::env(cts_logs)/wrapper_fanout.log] -save "to=$::env(cts_results),name=$::env(DESIGN_NAME).fanout,noindex,def,sdc,odb,netlist,powered_netlist"
}}
'''


def audit(run_dir):
    reasons=[];metrics={};not_measured=[];path=run_dir/"reports/metrics.csv"
    if path.is_file():
        rows=list(csv.DictReader(path.open(encoding="utf-8")))
        if len(rows)==1:metrics=rows[0]
    if metrics.get('config') not in (None,run_dir.name):
        reasons.append('metrics belong to another run: '+str(metrics['config']))
    completed=metrics.get("flow_status")=="flow completed"
    if not completed:reasons.append("OpenLane did not complete")
    for name in ("tritonRoute_violations","Magic_violations","klayout_violations","lvs_total_errors",
                 "pin_antenna_violations","net_antenna_violations"):
        value=metrics.get(name)
        if value is None or value=='-1':not_measured.append(name)
        elif value!="0":reasons.append(name+" = "+str(value))
    signoff=run_dir/'reports/signoff'
    sta_reasons=[]
    if list(signoff.glob('*-rcx_sta.*.rpt')):
        sta,sta_reasons=timing._sta_reasons(run_dir)
    else:sta={};not_measured.append('post_route_STA')
    power=pdn.audit_pdn(run_dir)
    if power['status']!='PASS_WRAPPER_PDN_CONNECTIVITY':
        not_measured.append('wrapper_VPWR_VGND_connectivity')
    gds=run_dir/f"results/final/gds/{d.TOP}.gds"
    reach={}
    if gds.is_file():
        graph=fanout.core._gds_hierarchy(gds)
        reach={cell:fanout.core._gds_reaches(graph,d.TOP,cell) for cell in (d.core.CELL,d.COND,"adc_top")}
        if not all(reach.values()):reasons.append("one real hard macro is missing from GDS hierarchy")
    else:not_measured.append('final_mixed_signal_GDS')
    lef=run_dir/f'results/final/lef/{d.TOP}.lef'
    if not lef.is_file():not_measured.append('final_wrapper_LEF')
    elif not re.search(r'(?m)^\s*MACRO\s+'+re.escape(d.TOP)+r'\s*$',lef.read_text(encoding='utf-8')):
        reasons.append('native final LEF does not define the wrapper top')
    lib=run_dir/f'results/final/lib/{d.TOP}.lib'
    if not lib.is_file() or not valid_timing_model(lib.read_text(encoding='utf-8')):
        if lib.is_file():reasons.append('native OpenSTA boundary LIB invalid')
        else:not_measured.append('native_OpenSTA_boundary_LIB')
    spef_root=run_dir/'results/final/spef'
    if not any(p.is_file() and p.stat().st_size for p in spef_root.rglob('*.spef*')):
        not_measured.append('final_extracted_SPEF')
    if completed and not_measured:reasons.append('required outputs/checks not measured: '+', '.join(not_measured))
    primary=None
    launch_log=run_dir.parent.parent.parent/'openlane.log'
    if launch_log.is_file():
        launch_text=launch_log.read_text(encoding='utf-8',errors='replace')
        errors=[s for s in launch_text.splitlines()
                if '[ERROR]' in s and 'A run for ' in s and 'already exists' in s]
        if errors:
            primary={'phase':'OPENLANE_PREP_EXISTING_RUN','errors':errors,'log':str(launch_log)}
            reasons.append('native prep refused an existing run directory')
        elif 'flow2_wrapper_pdn.py' in launch_text and 'SyntaxError: future feature annotations is not defined' in launch_text:
            primary={'phase':'WRAPPER_DEF_CHECKER_RUNTIME',
                'errors':['container Python rejected the DEF checker future annotations import'],'log':str(launch_log)}
            reasons.append('DEF guard failed in the container Python runtime after native PDN')
    lint=run_dir/'logs/synthesis/linter.log'
    if primary is None and lint.is_file():
        errors=[line for line in lint.read_text(encoding='utf-8',errors='replace').splitlines()
                if line.startswith('%Error') and not re.match(r'%Error:\s*Exiting\b',line)]
        if errors:primary={'phase':'VERILATOR_LINT','errors':errors,'log':str(lint)}
    if primary and primary['phase']=='VERILATOR_LINT':reasons.append('Verilator rejected the full wrapper top; see primary_failure')
    if primary is None:
        for log in sorted((run_dir/'logs/synthesis').glob('*-synthesis.log')):
            errors=[line for line in log.read_text(encoding='utf-8',errors='replace').splitlines()
                    if re.search(r'\bERROR:',line)]
            if errors:
                primary={'phase':'YOSYS_SYNTHESIS','errors':errors,'log':str(log)}
                reasons.append('Yosys rejected the wrapper RTL; see primary_failure')
                break
    if primary is None and power['errors']:
        primary={'phase':'PDN_CONNECTIVITY','errors':power['errors'],
                 'logs':power['logs'],'unconnected_nodes':power['unconnected_nodes']}
        reasons.append('wrapper VPWR/VGND PDN failed; see primary_failure')
    if primary is None:
        split_log=run_dir/'tmp/wrapper_fanout/split.log'
        if split_log.is_file():
            lines=split_log.read_text(encoding='utf-8',errors='replace').splitlines()
            errors=[line for line in lines if re.search(r'(?:Error|Exception):',line)]
            if errors:
                primary={'phase':'POST_CTS_FANOUT','errors':errors,'log':str(split_log)}
                reasons.append('post-CTS fanout failed; see primary_failure')
    if primary is None and not completed:
        for log in sorted((run_dir/'logs/routing').glob('*.log')):
            errors=[line for line in log.read_text(encoding='utf-8',errors='replace').splitlines()
                    if re.search(r'\[(?:ERROR|FATAL)\b',line)]
            if errors:
                primary={'phase':'NATIVE_ROUTING','errors':errors,'log':str(log)}
                break
    if primary is None and not completed:
        for log in (run_dir/'openlane.log',launch_log,run_dir/'errors.log'):
            if not log.is_file():continue
            lines=log.read_text(encoding='utf-8',errors='replace').splitlines()
            errors=[line for line in lines if '[ERROR]' in line or re.search(r'(?:Error|Exception):',line)]
            if errors:
                primary={'phase':'NATIVE_OPENLANE','errors':errors[-12:],'log':str(log)}
                break
        if primary is None:
            primary={'phase':'NATIVE_INCOMPLETE' if any(run_dir.rglob('*.log')) else 'NATIVE_NOT_EXECUTED',
                     'errors':['No completed native run; retain evidence and execute with a fresh tag'],
                     'log':str(run_dir)}
    # Prototype physical work continues when only the digital STA target fails.
    # Keep actual timing failures visible; do not relabel them as signoff PASS.
    # Missing timing-only views must not prevent transistor extraction/render
    # of a physically verified prototype. Preserve those gates separately.
    timing_outputs={'post_route_STA','native_OpenSTA_boundary_LIB'}
    physical_missing=[name for name in not_measured if name not in timing_outputs]
    layout_reasons=[reason for reason in reasons if not reason.startswith('required outputs/checks not measured:')
                    and reason!='native OpenSTA boundary LIB invalid']
    layout_ready=not layout_reasons and not physical_missing
    if 'native OpenSTA boundary LIB invalid' in reasons:
        sta_reasons.append('native OpenSTA boundary LIB invalid')
    if any(name in timing_outputs for name in not_measured):
        sta_reasons.append('timing evidence not measured: '+', '.join(name for name in not_measured if name in timing_outputs))
    status=('MIXED_WRAPPER_LAYOUT_AND_DIGITAL_STA_PASS' if layout_ready and not sta_reasons else
            'MIXED_WRAPPER_LAYOUT_PASS_TIMING_PENDING' if layout_ready else 'BLOCKED_WRAPPER_IMPLEMENTATION')
    return {"status":status,"layout_checks_pass":layout_ready,
        "reasons":reasons+sta_reasons,"metrics":metrics,"digital_sta":sta,
        "digital_sta_status":"NOT_MEASURED" if 'post_route_STA' in not_measured else
                             "FAIL" if sta_reasons else "PASS" if layout_ready else "NOT_MEASURED",
        "digital_sta_reasons":sta_reasons,"pdn":power,"physical_macro_reachability":reach,
        "primary_failure":primary,"not_measured_checks":not_measured,
        "scope":"GDS DRC, LEF macro-connectivity LVS and digital STA; transistor LVS/analog timing checked separately"}


def valid_timing_model(text):
    return bool(re.search(r'\bcell\s*\(\s*'+re.escape(d.TOP)+r'\s*\)',text) and
                re.search(r'\bclock\s*:\s*true\s*;',text) and
                re.search(r'\btiming\s*\(',text) and not re.search(r'(?i)\b(?:nan|infinity)\b',text))


def native_command(root,tag,design_dir,build,openlane_source,openlane_pdk,route_checkpoint_from=None,
                   route_checkpoint_stage='post_diode'):
    """Let native prep create the run. Never pass -overwrite on saved evidence.

    OpenLane 30ee138 rejects a preseeded run before reaching CURRENT_STEP.
    Reuse the checked hard macros, then execute the complete native flow.
    """
    if (design_dir/'runs'/tag).exists():
        raise FileExistsError('native prep requires an absent target run; retain it and use a fresh tag')
    notebook._requirements(root,Path(openlane_source),Path(openlane_pdk),notebook.DEFAULT_IMAGE)
    hook=build/'wrapper_fanout.tcl'
    native_flow=fanout.patched_flow((Path(openlane_source)/'flow.tcl').read_text(),Path(openlane_source),hook)
    if route_checkpoint_from:
        from scripts import flow2_wrapper_route_checkpoint as checkpoint
        extra,proof=checkpoint.prepare(root,route_checkpoint_from,
            json.loads((design_dir/'config.json').read_text()),build,openlane_pdk,openlane_source,stage=route_checkpoint_stage)
        with hook.open('a') as stream:stream.write(extra)
        native_flow=checkpoint.patch_driver(native_flow)
    driver=build/'flow_wrapper.tcl';driver.write_text(native_flow,encoding='utf-8')
    cmd=notebook.docker_command(root,tag,Path(openlane_source),Path(openlane_pdk),notebook.DEFAULT_IMAGE)
    cmd[cmd.index('--entrypoint')+1]='tclsh';cmd.insert(cmd.index(notebook.DEFAULT_IMAGE)+1,str(driver))
    cmd[cmd.index('-design')+1]=str(design_dir);cmd[cmd.index('-config_file')+1]=str(design_dir/'config.json')
    cmd[2:2]=['--name','automx-wrap-'+tag.lower()]
    return cmd


def _run(root, *, pdk_root, source_tag="readout_progress_20261018_04", condition_tag,
        rtl_tag, tag="mixed_wrapper_20261020_01", execute=False, timeout_s=10800,
        openlane_source=notebook.DEFAULT_SOURCE, openlane_pdk=notebook.DEFAULT_PDK,
        resume_from=None, audit_only=False,route_checkpoint_from=None,routing_options=None,
        route_checkpoint_stage='post_diode', core_repair_tag=None):
    root,pdk=Path(root).resolve(),Path(pdk_root).resolve();common.tag_ok(tag)
    report={"status":"PREPARED","top":d.TOP,"tag":tag,
        "native_mode":"FRESH_NATIVE_FLOW_REUSING_VERIFIED_HARD_MACROS",
        "routing_settings":routing_settings(routing_options),
        "not_signoff":"prototype full connected GDS; ADC loaded transfer, reference startup, calibrated PWM, final LIB/noise/PVT remain"}
    if route_checkpoint_from:
        common.tag_ok(route_checkpoint_from)
        report.update(native_mode='FRESH_PREP_THEN_VERIFIED_'+route_checkpoint_stage.upper()+'_IMPORT',
                      route_checkpoint_from=route_checkpoint_from,route_checkpoint_stage=route_checkpoint_stage)
    if resume_from:
        common.tag_ok(resume_from)
        if resume_from==tag:raise ValueError('PDN continuation requires a fresh GDS tag')
        report['requested_resume_from']=resume_from
        report['resume_status']='NOT_SUPPORTED_BY_PINNED_PREP; full native flow used'
    run_dir=root/common.BUILD/tag/'design/runs'/tag
    if audit_only:
        result=audit(run_dir)
        result.update(tag=tag,run_dir=run_dir.relative_to(root).as_posix(),execution_mode='AUDIT_ONLY',
                      native_executed=False)
        return result
    if not execute:return report
    if run_dir.exists():
        existing=audit(run_dir)
        if not existing['layout_checks_pass']:
            raise RuntimeError('existing native run is incomplete; no EDA executed. Retain '+str(run_dir)+
                               ' and use a fresh --tag (or --audit-only for read-only inspection)')
    previous,_,_,_,_,_=finish.verify_source(root,source_tag,check_fanout=False)
    cond=json.loads((root/common.BASE/condition_tag/"summary.json").read_text())
    rtl=json.loads((root/common.BASE/rtl_tag/"summary.json").read_text())
    if cond.get("status")!="BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS" or cond.get("electrical",{}).get("status")!="MEASURED_CONDITIONER_TT_PILOT":
        raise ValueError("conditioner physical/loaded block pilot gate required")
    if rtl.get("status")!="PASS_WRAPPER_RTL_TRANSACTIONS":raise ValueError("native RTL regression required")
    for item in rtl["inputs"]["sources"]:common._verified(root,item)
    cv=core_views(root,previous)
    nv={k:common._verified(root,v) for k,v in cond["views"].items()}
    if core_repair_tag:
        common.tag_ok(core_repair_tag)
        receipt=root/common.BASE/core_repair_tag/'summary.json'
        repair=json.loads(receipt.read_text())
        if repair.get('status')!='CORE_FULL_DRC_LVS_ACCESS_READY':
            raise ValueError('full-DRC core repair receipt required')
        for item in repair['sources']:common._verified(root,item)
        if not any(item['path']==cv['gds'].relative_to(root).as_posix() for item in repair['sources']):
            raise ValueError('core repair derives from a different source macro')
        cv.update({k:common._verified(root,repair['views'][k]) for k in ('gds','lef','schematic')})
        nv['lef']=common._verified(root,repair['views']['conditioner_lef'])
        report['core_full_drc_repair']=common._item(root,receipt)
        report['core_analog_characterization']='PENDING_NEW_RC_PEX_FOR_TAP_GEOMETRY'
    adc_src=root/d.ip.FILES["gds_gz"]
    if common._sha(adc_src)!=d.ip.EXPECTED_SHA256["gds_gz"]:raise ValueError("pinned ADC GDS changed")
    sources=[acq._item(root,p) for p in [*cv.values(),*nv.values(),adc_src,root/fanout.SPLITTER,root/fanout.LEGALIZE,
        root/"rtl/automx_cim_readout_seq.sv",root/pdn.RECIPE,root/pdn.PDN_TCL,root/pdn.GROUND_REPAIR_TCL,Path(container_runtime.__file__),
        root/d.ip.FILES['lef'],root/common.BASE/condition_tag/"summary.json",root/common.BASE/rtl_tag/"summary.json"]]
    if core_repair_tag:sources.append(common._item(root,receipt))
    store=common.Store(root,tag,{"sources":sources,"runner":common._sha(Path(__file__)),
        "topology":common._sha(Path(d.__file__)),"generator":common._sha(Path(prepare.__file__)),"pdk":str(pdk),"openlane_pdk":str(openlane_pdk),
        "requested_resume_from":resume_from,"native_mode":report['native_mode'],
        "route_checkpoint_from":route_checkpoint_from,"routing_settings":routing_settings(routing_options),
        "route_checkpoint_stage":route_checkpoint_stage})
    report['sources']=sources
    snapshot=store.build/'executed_host_sources'
    snapshot.mkdir(parents=True,exist_ok=True)
    report['host_source_snapshot']=[]
    host_sources=[Path(__file__)]
    if route_checkpoint_from:
        host_sources.extend(root/'scripts'/name for name in
                            ('flow2_wrapper_route_checkpoint.py','run_flow2_wrapper_route_recovery.py'))
    for path in host_sources:
        dest=snapshot/path.name
        if dest.exists() and common._sha(dest)!=common._sha(path):
            raise FileExistsError('different saved host source: '+str(dest))
        if not dest.exists():shutil.copy2(path,dest)
        report['host_source_snapshot'].append(acq._item(root,dest))
    process=None;timer=None;container="automx-wrap-"+tag.lower()
    def stop():
        try:subprocess.run(["docker","stop","--time","10",container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
        except (OSError,subprocess.TimeoutExpired):pass
        if process and process.poll() is None:process.terminate()
    try:
        design_dir=store.build/"design"
        prepare.generate(root,design_dir)
        adc_gds=design_dir/"adc_top.gds"
        data=gzip.decompress(adc_src.read_bytes())
        if adc_gds.exists() and adc_gds.read_bytes()!=data:raise FileExistsError("expanded ADC changed")
        if not adc_gds.exists():adc_gds.write_bytes(data)
        report['ADC_PG_access_abstraction']=pdn.prepare(root,design_dir/'adc_top.power_access.lef',gds_data=data)
        report['floorplan_geometry']=floorplan_geometry({'core_i':cv['lef'],'condition_i':nv['lef'],'adc_i':root/d.ip.FILES['lef']})
        placement=''.join(f'{inst} {x:g} {y:g} N\n' for inst,(x,y) in PLACEMENTS.items())
        (design_dir/"macro_placement.cfg").write_text(placement,encoding="utf-8")
        conf=config(root,design_dir,cv,nv,adc_gds,routing_options)
        if route_checkpoint_from:
            # A checkpoint already contains any prior port buffers. A new
            # guard cannot retroactively repair it; preserve its exact recipe.
            source_config=root/common.BUILD/route_checkpoint_from/'design/config.json'
            source_conf=json.loads(source_config.read_text())
            conf=inherit_checkpoint_analog_policy(conf,source_conf)
            report['analog_resizer_protection']='SOURCE_CHECKPOINT_POLICY_REUSED_NOT_RETROACTIVE'
        else:report['analog_resizer_protection']=ANALOG_RESIZER_PROTECTION
        common._save(design_dir/"config.json",conf)
        hook=store.build/"wrapper_fanout.tcl";hook.write_text(pdn.floorplan_hook()+fanout_hook(root),encoding="utf-8")
        run_dir=design_dir/"runs"/tag
        if not run_dir.exists():
            cmd=native_command(root,tag,design_dir,store.build,openlane_source,openlane_pdk,route_checkpoint_from,
                               route_checkpoint_stage)
            if route_checkpoint_from:report['route_checkpoint']=json.loads((store.build/'route_checkpoint.json').read_text())
            report.update(execution_mode='EXECUTE_NATIVE',native_executed=True,native_command=cmd,
                          native_image=notebook.DEFAULT_IMAGE)
            store.note('PREFLIGHT pinned container DEF checker and OpenROAD Python before native execution')
            report['container_runtime']=container_runtime.run(root,cmd,notebook.DEFAULT_IMAGE,store.folder)
            if report['container_runtime']['status']!='PASS':
                raise RuntimeError('native container runtime preflight failed; inspect container_runtime.json before EDA')
            if resume_from:store.note('Pinned prep rejects preseeded runs; requested checkpoint resume replaced by full native flow')
            store.note('START OpenLane '+('fresh prep and verified routing checkpoint' if route_checkpoint_from else
                       'full wrapper from lint/synthesis')+'; stage logs stream below')
            with (store.build/"openlane.log").open("w",encoding="utf-8") as log:
                process=subprocess.Popen(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
                timer=threading.Timer(timeout_s,stop);timer.start()
                for line in process.stdout:print(line,end="",flush=True);log.write(line);log.flush()
                report["openlane_returncode"]=process.wait()
        else:
            report.update(execution_mode='AUDIT_COMPLETED_NATIVE',native_executed=False)
            runtime_path=store.folder/'container_runtime.json'
            if runtime_path.is_file():
                report['container_runtime']=json.loads(runtime_path.read_text(encoding='utf-8'))
            store.note("AUDIT existing wrapper run; routed files are not overwritten")
        report.update(audit(run_dir))
        report["run_dir"]=run_dir.relative_to(root).as_posix()
        report["views"]={}
        for key,pattern in (("gds",f"results/final/gds/{d.TOP}.gds"),("lef",f"results/final/lef/{d.TOP}.lef"),
                            ("lib",f"results/final/lib/{d.TOP}.lib")):
            path=run_dir/pattern
            if path.is_file():report["views"][key]=acq._item(root,path)
        spef_root=run_dir/'results/final/spef'
        spefs=sorted(set(spef_root.rglob('*.spef'))|set(spef_root.rglob('*.spef.gz')))
        report["spef_files"]=[acq._item(root,p) for p in spefs]
        lib=run_dir/f'results/final/lib/{d.TOP}.lib'
        report["final_wrapper_LIB"]=("OPENSTA_EXTRACTED_DIGITAL_BOUNDARY_ETM" if lib.is_file() and
            valid_timing_model(lib.read_text(encoding='utf-8')) else "INVALID_OPENSTA_TIMING_MODEL" if lib.is_file()
            else "MISSING_OPENSTA_TIMING_MODEL")
        report["lib_scope"]="native post-route digital clock/setup/hold model; ADC analog timing/startup/load are not characterized by this ETM"
        report["strict_stage8_gate"]="PENDING_COMPLETE_WRAPPER_CHARACTERIZATION"
        if not report.get('layout_checks_pass') and report['views'].get('gds'):
            # Collect independent prototype evidence even if native signoff
            # stopped at Magic DRC. Original metrics/status remain failures.
            from scripts.run_flow2_wrapper_postroute import run as postroute_run
            report['prototype_postroute']=postroute_run(root,gds_tag=tag,tag=tag+'_postroute',
                timeout_s=180,execute=True)
        if report.get('layout_checks_pass'):
            # Full GDS is ready for the independent transistor extraction;
            # no LEF blackbox result is relabelled as transistor LVS.
            from scripts.run_flow2_wrapper_transistor_lvs import run as transistor_run
            report["composite_transistor_checks"]=transistor_run(root,pdk_root=pdk,tag=tag+"_dev",
                source_run=run_dir,core_reference=cv["schematic"],condition_reference=nv["schematic"],timeout_s=3600)
            store.physical.mkdir(parents=True,exist_ok=True)
            for key,item in list(report['views'].items()):
                path=common._verified(root,item);dest=store.physical/path.name
                shutil.copy2(path,dest);report['views'][key]=acq._item(root,dest)
            report['published_spef_files']=[]
            for item in report['spef_files']:
                path=common._verified(root,item);dest=store.physical/'spef'/path.relative_to(spef_root)
                dest.parent.mkdir(parents=True,exist_ok=True)
                if dest.exists() and common._sha(dest)!=common._sha(path):
                    raise ValueError('different SPEF views have colliding filenames')
                shutil.copy2(path,dest);report['published_spef_files'].append(acq._item(root,dest))
            try:
                png=store.folder/'top.png';tool=shutil.which('klayout')
                if not tool:raise FileNotFoundError('native KLayout missing for render')
                import os
                env=os.environ.copy();env.update(QT_QPA_PLATFORM='offscreen',AUTOMX_GDS=str(root/report['views']['gds']['path']),
                                                AUTOMX_PNG=str(png),AUTOMX_TOP=d.TOP)
                rr=subprocess.run([tool,'-z','-x','-r',str(root/'scripts/render_flow2_wrapper_gds.py')],
                                  cwd=root,env=env,text=True,capture_output=True,timeout=180)
                (store.folder/'render.log').write_text(rr.stdout+rr.stderr,encoding='utf-8')
                if rr.returncode or not png.is_file() or png.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':
                    raise RuntimeError('GDS retained; inspect render.log for image export failure')
                report['png']=acq._item(root,png)
            except Exception as error:report['render_status']=str(error)
        report["timestamp_utc"]=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
    except FileExistsError:raise
    except KeyboardInterrupt:
        stop();report["status"]="INTERRUPTED_WRAPPER_IMPLEMENTATION";raise
    except Exception as error:
        report.update(status="BLOCKED_MIXED_WRAPPER",error=f"{type(error).__name__}: {error}")
    finally:
        if timer:timer.cancel()
        if sys.exc_info()[0] is not FileExistsError:
            common.save_summary(store.folder/"summary.json",report)
            store.note("END "+report["status"])
            common.bundle(root,tag,sources)
    return report


def run(root, **kwargs):
    if not kwargs.get('execute',False) or kwargs.get('audit_only',False):
        return _run(root,**kwargs)
    import fcntl
    tag=kwargs.get('tag','mixed_wrapper_20261020_01');common.tag_ok(tag)
    folder=Path(root).resolve()/common.BASE/tag
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/'runner.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('native wrapper is already running; follow '+str(folder/'history.log')) from error
        return _run(root,**kwargs)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--pdk-root",type=Path,required=True);p.add_argument("--condition-tag",required=True)
    p.add_argument("--rtl-tag",required=True);p.add_argument("--tag",default="mixed_wrapper_20261020_01")
    mode=p.add_mutually_exclusive_group();mode.add_argument("--run",action="store_true")
    mode.add_argument("--audit-only",action="store_true");a=p.parse_args()
    print(json.dumps(run(a.root,pdk_root=a.pdk_root,condition_tag=a.condition_tag,rtl_tag=a.rtl_tag,tag=a.tag,
                         execute=a.run,audit_only=a.audit_only),indent=2))

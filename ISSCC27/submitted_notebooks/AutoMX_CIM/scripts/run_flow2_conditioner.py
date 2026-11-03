#!/usr/bin/env python3
"""Build the real source-follower/mux/reference block using verified leaves."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_wrapper_design as design
from scripts import flow2_wrapper_physical as physical
from scripts import run_flow2_acquisition_layout as acq
from scripts import flow2_integration_common as common
from scripts.run_flow2_acquisition_transient_recovery import DEFAULT_PDK
from scripts import flow2_waveforms as waves
from scripts import flow2_live_spice as live

ANALYSIS = 'CONDITIONER_RAW_V2_CURRENT_ALIASES'


def supply_current_key(vectors):
    """ngspice 31 writes i(i(vvdd)); 44 writes i(vvdd). Keep raw unchanged."""
    keys=[k for k in ('i(vvdd)','i(i(vvdd))','vvdd#branch') if k in vectors]
    if not keys:raise ValueError('missing measured VVDD branch current')
    for key in keys[1:]:
        if not np.allclose(vectors[keys[0]],vectors[key],rtol=1e-10,atol=1e-15):
            raise ValueError('ambiguous VVDD branch-current aliases')
    return keys[0]


def analyze_point(path):
    v=waves.read_raw(path)
    if abs(float(v['time'][0]))>1e-18 or float(v['time'][-1])<500e-9*(1-1e-10):
        raise ValueError('conditioner raw does not cover the complete 0..500 ns bench')
    vp=waves.sample(v,'v(AINP)',450e-9);vn=waves.sample(v,'v(AINN)',450e-9)
    current=supply_current_key(v)
    return dict(status='MEASURED_CONDITIONER_POINT',analysis_version=ANALYSIS,
        output_diff_v=vp-vn,output_cm_v=(vp+vn)/2,
        bias_v=waves.sample(v,'v(BIAS_MON)',450e-9),current_vector=current,
        supply_current_a=-waves.sample(v,current,450e-9),
        within_supply_rails=0.05<min(vp,vn) and max(vp,vn)<1.75,
        within_prototype_cm_window=.7<(vp+vn)/2<1.1)


def legacy_completed(root, tag, work, text, *, index=None):
    """Reanalyze an exported, completed legacy case before rerunning SPICE.

    The old runner failed between raw parsing and receipt writing. Its export
    preserves hashes of the deck/raw/log, but did not capture the executable
    fingerprint for this case; retain that limitation in the new receipt.
    """
    index=Path(index) if index else root/'server_results/flow2_wrapper_integration'/tag/'export.json'
    if not index.is_file():return None
    frozen={v['path']:v for v in json.loads(index.read_text(encoding='utf-8'))['files']}
    for attempt in sorted(work.glob('attempt_*'),reverse=True):
        paths=[attempt/'bench.spice',attempt/'conditioner.raw',attempt/'ngspice.live.log']
        if not all(p.is_file() and p.relative_to(root).as_posix() in frozen for p in paths):continue
        for p in paths:common._verified(root,frozen[p.relative_to(root).as_posix()])
        if paths[0].read_text(encoding='utf-8')!=text:continue
        log=paths[2].read_text(encoding='utf-8',errors='replace')
        if not re.search(r'(?im)^ngspice-\d+(?:\.\d+)? done\s*$',log):continue
        result=analyze_point(paths[1])
        result.update(raw=acq._item(root,paths[1]),native_log=acq._item(root,paths[2]),
            provenance='REANALYZED_EXPORTED_LEGACY_RAW',
            original_runtime_identity='NOT_CAPTURED_BY_V1; no legacy executable fingerprint inferred',
            legacy_export_sha256=common._sha(index))
        return result
    return None


def layout(root, views):
    source = (root/acq.RECIPE).read_text(encoding="utf-8")
    # Reuse the actual passing via/contact and FET escape geometry.
    source = source.replace("foreach kind {nfet pfet pre cap}", "foreach kind {nfet pfet cap}")
    source = source.replace("foreach net $PINS {", "foreach net $BUS_NETS {", 2)
    source = source.replace('30.0+2.0*$index','30.0+4.0*$index')
    source = source.replace('foreach net $BUS_NETS {hwire metal4 1.0 $total_width $bus_y($net) 0.60}',
        'foreach net $BUS_NETS {\n    set width [expr {$net in {VPWR VGND} ? 3.0 : 0.60}]\n'
        '    hwire metal4 1.0 $total_width $bus_y($net) $width\n}')
    source = source.replace("85um", "${bus_top}um")
    source = source.replace("AUTOMX_ACQUISITION_DRC=", "AUTOMX_WRAPPER_DRC=")
    source = source.replace("AUTOMX_ACQUISITION_DONE", "AUTOMX_WRAPPER_LAYOUT_DONE")
    devices = design.conditioner()
    buses = list(dict.fromkeys([*design.COND_PINS, *(n for d in devices for n in d["nets"])]))
    lines = [f"set CELL {design.COND}", f"set PINS {{{' '.join(design.COND_PINS)}}}",
        f"set BUS_NETS {{{' '.join(buses)}}}", f"set bus_top {40+4*len(buses)}"]
    for kind in ("nfet", "pfet", "cap"):
        v=views[kind]
        lines += [f"set source_cell({kind}) {v['cell']}",f"set source_gds({kind}) {{{v['gds'].as_posix()}}}"]
    lines += ["set components {", *[f"  {{{d['name']} {d['kind']} {{{' '.join(d['nets'])}}}}}" for d in devices], "}", source]
    return "\n".join(lines)


def bench(model, net, variant, selected, diff):
    pins=design.COND_PINS;name=design.COND+ ("_pex" if variant=="pex" else "")
    lines=[".title conditioner physical prototype load stress",f'.lib "{model.as_posix()}" tt',
        f'.include "{net.as_posix()}"',".temp 25", ".option method=gear reltol=1e-4",
        "VVDD VPWR 0 PWL(0 0 1n 1.8)", "VGND VGND 0 0"]
    for c in range(4):
        for pol,sign in (("P",1),("N",-1)):
            lines.append(f"VH{pol}{c} H{pol}{c} 0 PWL(0 0 1n {1.7+sign*diff/2:.12g})")
        lines.append(f"VSEL{c} SEL{c} 0 {1.8 if c==selected else 0}")
    lines += [f"XCOND {' '.join(pins)} {name}",
        "* 2-pF per-input test load: stress model, not an ADC transfer proof.",
        "CLOADP AINP 0 2p", "CLOADN AINN 0 2p", ".tran 1n 500n 0 1n",
        ".control", "set filetype=ascii", "set numdgt=17", "run",
        "write conditioner.raw v(AINP) v(AINN) v(BIAS_MON) i(VVDD)", "quit", ".endc", ".end", ""]
    return "\n".join(lines)


def electrical(root, pdk, tag, block, timeout_s, *, legacy_index=None):
    store_folder=root/common.BASE/tag
    if block["status"]!="BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS":
        return {"status":"SKIPPED_PHYSICAL_GATE", "jobs":[]}
    # These small native block benches use the server's original SKY130 model.
    model=pdk/"libs.tech/ngspice/sky130.lib.spice"
    tool=acq.stage5._find_tool("ngspice")
    if not tool or not model.is_file():raise ValueError("native block ngspice/model missing")
    report={"status":"STARTED", "jobs":[], "planned_sims":8,"completed_sims":0,"reused_points":0,
        "scope":"all four mux selections at TT with 2-pF driven load",
        "prototype_cm_window_v":[.7,1.1],"cm_window_scope":"design target, not an ADC vendor signoff specification"}
    for variant in ("schematic","pex"):
        net=common._verified(root,block["views"][variant])
        for selected,diff in ((0,-.1),(1,0.),(2,.05),(3,.1)):
            work=root/common.BUILD/tag/f"tt_{variant}_{selected}"
            work.mkdir(parents=True,exist_ok=True)
            text=bench(model,net,variant,selected,diff); deck=work/"bench.spice"
            if deck.exists() and deck.read_text(encoding="utf-8")!=text:raise FileExistsError("block bench changed")
            if not deck.exists():deck.write_text(text,encoding="utf-8")
            saved=work/"receipt.json"
            spec={"deck":common._sha(deck),"model":common._sha(model),"network":common._sha(net),
                  "tool_binary":common._sha(Path(tool))}
            reuse=json.loads(saved.read_text()) if saved.is_file() else None
            if reuse and reuse.get("inputs")!=spec:raise FileExistsError("block electrical inputs changed")
            if reuse and reuse.get("status")=="MEASURED_CONDITIONER_POINT":
                raw=common._verified(root,reuse['raw']);item={**reuse,**analyze_point(raw)}
                report['reused_points']+=1
            elif (legacy:=legacy_completed(root,tag,work,text,index=legacy_index)) is not None:
                item={"variant":variant,"selected_column":selected,"input_diff_v":diff,
                      "inputs":spec,**legacy}
                print(f'REANALYZE completed conditioner raw: {variant} column {selected}',flush=True)
                report['reused_points']+=1
                common._save(saved,item)
            else:
                # Preserve failed runs before a retry; do not overwrite their logs.
                numbers=[int(p.name.split('_')[1]) for p in work.glob('attempt_*') if re.fullmatch(r'attempt_\d+',p.name)]
                attempt=work/f"attempt_{max(numbers,default=-1)+1:03d}"
                attempt.mkdir()
                (attempt/"bench.spice").write_text(text,encoding="utf-8")
                r=live.run([tool,"-b","bench.spice"],attempt,timeout_s)
                # Retain execution identity even if a later parser raises.
                native={'inputs':spec,'returncode':r.returncode,
                        'log':acq._item(root,attempt/'ngspice.live.log')}
                if (attempt/'conditioner.raw').is_file():native['raw']=acq._item(root,attempt/'conditioner.raw')
                common._save(attempt/'native.receipt.json',native)
                item={"variant":variant,"selected_column":selected,"input_diff_v":diff,"inputs":spec,
                    "returncode":r.returncode,"status":"BLOCKED_CONDITIONER_POINT"}
                raw=attempt/"conditioner.raw"
                if r.returncode==0 and raw.is_file():
                    item.update(raw=acq._item(root,raw),native_receipt=acq._item(root,attempt/'native.receipt.json'),
                                **analyze_point(raw))
                common._save(saved,item)
            report["jobs"].append(item)
            report['completed_sims']=sum(j['status']=='MEASURED_CONDITIONER_POINT' for j in report['jobs'])
            print(f"Conditioner TT {report['completed_sims']}/8: {variant} column {selected} {item['status']}",flush=True)
            common.save_summary(store_folder/"conditioner_electrical.json",report)
    pex=[j for j in report["jobs"] if j["variant"]=="pex"]
    measured=all(j["status"]=="MEASURED_CONDITIONER_POINT" for j in report["jobs"])
    ordered=measured and all(j.get("within_supply_rails",False) and j.get("within_prototype_cm_window",False) for j in report["jobs"])
    ordered=ordered and all(a['output_diff_v']<b['output_diff_v'] for a,b in zip(pex,pex[1:]))
    report["status"]="MEASURED_CONDITIONER_TT_PILOT" if ordered else "BLOCKED_CONDITIONER_OPERATING_POINT"
    report["not_signoff"]="driven held pins and ideal 2-pF stress capacitors; connected core droop, ADC kickback, full transfer/PVT remain"
    common.save_summary(store_folder/"conditioner_electrical.json",report)
    return report


def run(root, *, pdk_root=DEFAULT_PDK, tag="wrapper_condition_20261020_01", execute=False, timeout_s=1800):
    root,pdk=Path(root).resolve(),Path(pdk_root).resolve();common.tag_ok(tag)
    if not execute:
        return {"status":"PREPARED", "cell":design.COND, "devices":design.expected_conditioner(), "new_spice_jobs":8}
    # Snapshot the prior export BEFORE physical() refreshes its export index.
    legacy_index=None
    old_index=root/'server_results/flow2_wrapper_integration'/tag/'export.json'
    if old_index.is_file():
        legacy_index=root/common.BASE/tag/('electrical_source_export_'+common._sha(old_index)[:16]+'.json')
        legacy_index.parent.mkdir(parents=True,exist_ok=True)
        if not legacy_index.exists():legacy_index.write_bytes(old_index.read_bytes())
    views,source=acq._sources(root,"sample_fet_20261017_03","precharge_leaf_guarded_20261017_03","hold_cap_mim3_20261017_02")
    if common._sha(pdk/"libs.tech/magic/sky130A.tech")!=source["magic_technology_sha256"]:
        raise ValueError("integration technology differs from verified leaves")
    inputs=[acq._item(root,views[k]["gds"]) for k in ("nfet","pfet","cap")]
    inputs += [v for v in source.values() if isinstance(v,dict) and 'path' in v and 'sha256' in v]
    r=physical.physical(root,pdk=pdk,tag=tag,cell=design.COND,pins=design.COND_PINS,
        layout_tcl=layout(root,views),reference=design.schematic(),sources=inputs,timeout_s=timeout_s)
    if r['status']=='BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS':
        r['substrate_rc_audit']=acq._rc_audit(common._verified(root,r['views']['pex']))
        if r['substrate_rc_audit']['unreferenced_capacitive_nodes']:
            r.update(status='BLOCKED_CONDITIONER_SUBSTRATE_RC',error='unreferenced PEX capacitor/substrate nodes; no artificial substrate shunt added')
    try:r["electrical"]=electrical(root,pdk,tag,r,timeout_s,legacy_index=legacy_index)
    except FileExistsError:raise
    except KeyboardInterrupt:
        r['electrical']={'status':'INTERRUPTED'}
        common.save_summary(root/common.BASE/tag/'summary.json',r)
        common.bundle(root,tag,inputs)
        raise
    except Exception as error:r['electrical']={'status':'BLOCKED_CONDITIONER_ELECTRICAL','error':f'{type(error).__name__}: {error}'}
    common.save_summary(root/common.BASE/tag/"summary.json",r)
    common.bundle(root,tag,inputs)
    return r


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=ROOT);p.add_argument("--pdk-root",type=Path,default=DEFAULT_PDK)
    p.add_argument("--tag",default="wrapper_condition_20261020_01");p.add_argument("--run",action="store_true")
    p.add_argument("--timeout-s",type=int,default=1800);a=p.parse_args()
    r=run(a.root,pdk_root=a.pdk_root,tag=a.tag,execute=a.run,timeout_s=a.timeout_s)
    print(json.dumps(r,indent=2))
    if a.run and r.get("electrical",{}).get("status")!="MEASURED_CONDITIONER_TT_PILOT":raise SystemExit(1)

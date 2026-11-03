from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
from collections import defaultdict

from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator, TransportTemporalOrderError
from glitchscope.inertial import InertialSimulator
from glitchscope.analysis import stable_epoch_maps
from glitchscope.classify import extract_pulses
from glitchscope.lineage import classify_glitch_lineages

from validate_real_sky130_b6 import (
    EXPECTED_SHA, sha256_file, find_cell, sole_output, build_net, pulse_lineage
)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--lib",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)

    if sha256_file(a.lib)!=EXPECTED_SHA:
        raise AssertionError("Real Liberty authority SHA mismatch")

    lib=parse_liberty_file(a.lib)
    p=LibertyDelayProvider(lib)
    buf=find_cell(lib,"sky130_fd_sc_hd__buf_1","__buf_")
    xor=find_cell(lib,"sky130_fd_sc_hd__xor2_1","__xor2_")
    buf_out=sole_output(lib.cells[buf]); xor_out=sole_output(lib.cells[xor])

    ax=[x for x in lib.cells[xor].timing_arcs
        if x.related_pin=="A" and x.timing_sense=="positive_unate"]
    bx=[x for x in lib.cells[xor].timing_arcs
        if x.related_pin=="B" and x.timing_sense=="negative_unate"]
    if len(ax)!=1 or len(bx)!=1:
        raise AssertionError("B7 requires closed B5 XOR arc authority")
    rise_arc=ax[0]; fall_arc=bx[0]

    rise_loads=set(float(v) for v in rise_arc.cell_rise.index_2)
    fall_loads=set(float(v) for v in fall_arc.cell_fall.index_2)
    common=sorted(rise_loads & fall_loads)
    if not common:
        lo=max(min(rise_loads),min(fall_loads))
        hi=min(max(rise_loads),max(fall_loads))
        if hi<lo: raise AssertionError("No common XOR load interval")
        common=[lo,(lo+hi)/2.0,hi]
    loads=[]
    for raw in common:
        ff=raw*lib.capacitance_unit_ff
        if ff not in loads: loads.append(ff)
    if len(loads)>5:
        idx=sorted(set([0,1,len(loads)//2,len(loads)-2,len(loads)-1]))
        loads=[loads[i] for i in idx]

    input_slew_fs=ps_to_fs(10)
    t0=ps_to_fs(100)
    epoch=StimulusEpoch(t0,{"S":1},1)

    rows=[]
    supported=[]
    rejected=[]
    final_mismatch_count=0

    for load in loads:
        for nchain in range(1,7):
            net,bnet=build_net(buf,buf_out,xor,xor_out,nchain)
            row={
                "nchain":nchain,"output_load_ff":load,"status":"",
                "reason":"","input_skew_fs":"","m0_pulse_width_fs":"",
                "m1_outcome":"","m1_pulse_width_fs":"",
                "overtake_instance":"","pending_time_fs":"","new_time_fs":"",
            }
            try:
                m0=TransportSimulator(
                    net,p,input_slew_fs_by_net={"S":input_slew_fs},
                    auto_load_from_liberty=True,
                    primary_output_load_ff_by_net={"Y":load},
                )
                t_m0,state=m0.run([epoch])
                if state["Y"]!=0:
                    raise AssertionError("Supported M0 final Y not stable-low")
                bp=[e for e in t_m0 if e.net==bnet]
                if len(bp)!=1:
                    raise AssertionError("Expected exactly one slow-path event")
                skew=bp[0].time_fs-t0
                p0,l0,_=pulse_lineage(net,t_m0,epoch)
                yp=[x for x in p0 if x.net=="Y"]
                yl=[x for x in l0 if x.net=="Y"]
                if len(yp)!=1 or len(yl)!=1:
                    raise AssertionError("Expected one supported M0 Y pulse")
                if yl[0].classification!="GENERATED" or yl[0].root_ids!=("GROOT0001",):
                    raise AssertionError("Supported M0 lineage mismatch")

                m1=InertialSimulator(
                    net,p,input_slew_fs_by_net={"S":input_slew_fs},
                    auto_load_from_liberty=True,
                    primary_output_load_ff_by_net={"Y":load},
                )
                t_m1,state1=m1.run([epoch])
                if state1["Y"]!=0:
                    raise AssertionError("M1 final Y not stable-low")
                p1,l1,_=pulse_lineage(net,t_m1,epoch)
                y1=[x for x in p1 if x.net=="Y"]
                sy=[x for x in m1.last_suppressed_transitions if x.instance=="U_X"]
                if len(y1)==0:
                    if len(sy)!=1: raise AssertionError("Suppressed case ledger mismatch")
                    outcome="SUPPRESSED"; m1width=""
                elif len(y1)==1:
                    if sy: raise AssertionError("Survived case unexpectedly suppressed")
                    if y1[0].width_fs!=yp[0].width_fs:
                        raise AssertionError("M1 survived width differs from M0")
                    outcome="SURVIVED"; m1width=y1[0].width_fs
                else:
                    raise AssertionError("Unexpected M1 Y pulse count")

                row.update({
                    "status":"SUPPORTED","input_skew_fs":skew,
                    "m0_pulse_width_fs":yp[0].width_fs,
                    "m1_outcome":outcome,"m1_pulse_width_fs":m1width,
                })
                supported.append(dict(row))
            except TransportTemporalOrderError as e:
                row.update({
                    "status":"M0_OVERTAKE_REJECTED",
                    "reason":str(e),"overtake_instance":e.instance,
                    "pending_time_fs":e.previous_time_fs,
                    "new_time_fs":e.new_time_fs,
                })
                if not e.new_time_fs <= e.previous_time_fs:
                    raise AssertionError("B7 rejection does not actually overtake")
                rejected.append(dict(row))
            except AssertionError as e:
                if "Timed/final mismatch" in str(e):
                    final_mismatch_count += 1
                raise
            rows.append(row)

    if len(rows)!=30:
        raise AssertionError("Expected 30 B7 real sweep cases")
    if len(supported)!=19:
        raise AssertionError("Expected 19 M0-supported real cases, got %d"%len(supported))
    if len(rejected)!=11:
        raise AssertionError("Expected 11 explicit M0-overtake rejections, got %d"%len(rejected))
    if final_mismatch_count!=0:
        raise AssertionError("Generic final-state mismatch remains after B7 guard")
    if any(r["overtake_instance"]!="U_X" for r in rejected):
        raise AssertionError("Expected all real overtakes at reconvergent XOR")
    if any(not int(r["new_time_fs"])<=int(r["pending_time_fs"]) for r in rejected):
        raise AssertionError("Invalid overtake timing relation")

    # Strong matched-load control: same XOR output load, only chain/skew changes.
    byload=defaultdict(list)
    for r in supported:
        byload[float(r["output_load_ff"])].append(r)

    brackets=[]
    for load,rs in byload.items():
        supp=[r for r in rs if r["m1_outcome"]=="SUPPRESSED"]
        surv=[r for r in rs if r["m1_outcome"]=="SURVIVED"]
        for s in supp:
            longer=[r for r in surv if int(r["nchain"])>int(s["nchain"])]
            if longer:
                l=min(longer,key=lambda r:(int(r["nchain"]),int(r["input_skew_fs"])))
                brackets.append((int(s["nchain"]),load,int(l["nchain"]),s,l))

    if not brackets:
        raise AssertionError("No matched-load M1 suppression/survival bracket")
    brackets.sort(key=lambda x:(x[0],x[1],x[2]))
    _,matched_load,_,short,long=brackets[0]
    if float(short["output_load_ff"])!=float(long["output_load_ff"]):
        raise AssertionError("Matched bracket load mismatch")
    if not int(long["nchain"])>int(short["nchain"]):
        raise AssertionError("Matched bracket does not increase chain length")
    if not int(long["input_skew_fs"])>int(short["input_skew_fs"]):
        raise AssertionError("Matched bracket does not increase skew")
    if short["m1_outcome"]!="SUPPRESSED" or long["m1_outcome"]!="SURVIVED":
        raise AssertionError("Matched bracket M1 outcomes wrong")

    fields=[
        "nchain","output_load_ff","status","reason","input_skew_fs",
        "m0_pulse_width_fs","m1_outcome","m1_pulse_width_fs",
        "overtake_instance","pending_time_fs","new_time_fs",
    ]
    with (out/"real_sky130_b7_domain_sweep.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows:w.writerow(r)

    selected=[
        dict(short,case="MATCHED_LOAD_SHORT_SUPPRESSED"),
        dict(long,case="MATCHED_LOAD_LONG_SURVIVED"),
    ]
    sf=sorted({k for r in selected for k in r})
    with (out/"real_sky130_b7_matched_bracket.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=sf); w.writeheader()
        for r in selected:w.writerow(r)

    summary={
        "status":"PASS",
        "source_sha256":sha256_file(a.lib),
        "model":"B7_M0_TEMPORAL_ORDER_DOMAIN_CLOSURE",
        "sweep_case_count":len(rows),
        "m0_supported_case_count":len(supported),
        "m0_overtake_rejected_count":len(rejected),
        "generic_final_mismatch_count":final_mismatch_count,
        "overtake_policy":"FAIL_CLOSED_ON_NEW_EVENT_TIME_LE_PENDING_EVENT_TIME",
        "matched_load_ff":matched_load,
        "matched_short":short,
        "matched_long":long,
        "matched_control":"same_output_load_only_buffer_chain_and_skew_change",
        "m2_spice_calibrated":False,
    }
    (out/"real_sky130_b7_summary.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)
    )

    print("B7_REAL_SWEEP_CASE_COUNT=%d"%len(rows))
    print("B7_REAL_M0_SUPPORTED_CASE_COUNT=%d"%len(supported))
    print("B7_REAL_M0_OVERTAKE_REJECTED_COUNT=%d"%len(rejected))
    print("B7_REAL_GENERIC_FINAL_MISMATCH_COUNT=%d"%final_mismatch_count)
    print("B7_REAL_MATCHED_LOAD_FF=%s"%matched_load)
    print("B7_REAL_MATCHED_SHORT_CHAIN_LENGTH=%s"%short["nchain"])
    print("B7_REAL_MATCHED_SHORT_M0_WIDTH_FS=%s"%short["m0_pulse_width_fs"])
    print("B7_REAL_MATCHED_LONG_CHAIN_LENGTH=%s"%long["nchain"])
    print("B7_REAL_MATCHED_LONG_M0_M1_WIDTH_FS=%s"%long["m0_pulse_width_fs"])
    print("B7_REAL_TEMPORAL_OVERTAKE_FAIL_CLOSED_PASS")
    print("B7_REAL_NO_GENERIC_FINAL_MISMATCH_PASS")
    print("B7_REAL_MATCHED_LOAD_M1_BRACKET_PASS")
    print("B7_REAL_SUPPORTED_DOMAIN_EXACTNESS_PASS")

if __name__=="__main__":
    main()

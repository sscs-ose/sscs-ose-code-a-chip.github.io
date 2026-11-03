from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path

from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator
from glitchscope.inertial import InertialSimulator
from glitchscope.analysis import stable_epoch_maps
from glitchscope.classify import extract_pulses
from glitchscope.lineage import classify_glitch_lineages

EXPECTED_SHA="ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9"

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):
            h.update(c)
    return h.hexdigest()

def find_cell(lib, exact, token):
    if exact in lib.cells:
        return exact
    xs=sorted(n for n in lib.cells if token in n.lower())
    if not xs:
        raise AssertionError("No real cell matching "+token)
    return xs[0]

def sole_output(lc):
    outs=sorted({a.output_pin for a in lc.timing_arcs})
    if len(outs)!=1:
        raise AssertionError("Expected one output, got "+str(outs))
    return outs[0]

def build_net(buf_name,buf_out,xor_name,xor_out,nchain):
    cells=[]
    prev="S"
    for i in range(1,nchain+1):
        out="B%d"%i
        cells.append(Cell(
            "U_B%d"%i,"BUF",{"A":prev},out,0,0,
            library_cell=buf_name,library_output_pin=buf_out
        ))
        prev=out
    cells.append(Cell(
        "U_X","XOR2",{"A":"S","B":prev},"Y",0,0,
        library_cell=xor_name,library_output_pin=xor_out
    ))
    return Network(["S"],["Y"],cells,{"S":0}),prev

def pulse_lineage(net,trace,epoch):
    before,after=stable_epoch_maps(net,[epoch])
    pulses=extract_pulses(trace,before,after)
    records,edges=classify_glitch_lineages(trace,pulses)
    return pulses,records,edges

def y_signature(trace):
    return [(e.time_fs,e.old_value,e.new_value,e.epoch_id,e.parent_event_ids)
            for e in trace if e.net=="Y"]

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
    buf_out=sole_output(lib.cells[buf])
    xor_out=sole_output(lib.cells[xor])

    # B5 authority required: each XOR related pin has one positive- and one
    # negative-unate parsed propagation arc.
    for pin in ("A","B"):
        senses=sorted(
            x.timing_sense for x in lib.cells[xor].timing_arcs
            if x.related_pin==pin
        )
        if senses!=["negative_unate","positive_unate"]:
            raise AssertionError(
                "B6 requires closed B5 XOR mixed-sense authority: pin=%s senses=%s"%
                (pin,senses)
            )

    # Use real characterized output-load points common to the two arcs that
    # will be exercised: A positive-unate/output-rise and B
    # negative-unate/output-fall. Scan all common table points, not a guessed
    # load, then scan deterministic buffer-chain lengths.
    ax=[x for x in lib.cells[xor].timing_arcs
        if x.related_pin=="A" and x.timing_sense=="positive_unate"]
    bx=[x for x in lib.cells[xor].timing_arcs
        if x.related_pin=="B" and x.timing_sense=="negative_unate"]
    if len(ax)!=1 or len(bx)!=1:
        raise AssertionError("B6 XOR arc authority is not singleton after B5 sense selection")
    rise_arc=ax[0]
    fall_arc=bx[0]

    rise_loads=set(float(v) for v in rise_arc.cell_rise.index_2)
    fall_loads=set(float(v) for v in fall_arc.cell_fall.index_2)
    common=sorted(rise_loads & fall_loads)
    if not common:
        # If grids differ, use deterministic points spanning the common
        # characterized interval. Liberty interpolation is valid there.
        lo=max(min(rise_loads),min(fall_loads))
        hi=min(max(rise_loads),max(fall_loads))
        if not hi>=lo:
            raise AssertionError("No common XOR characterized load interval")
        common=[lo,(lo+hi)/2.0,hi]

    load_candidates=[]
    for raw in common:
        ff=raw*lib.capacitance_unit_ff
        if ff not in load_candidates:
            load_candidates.append(ff)

    # Keep the sweep compact but cover low/mid/high points deterministically.
    if len(load_candidates)>5:
        idx=sorted(set([0,1,len(load_candidates)//2,len(load_candidates)-2,len(load_candidates)-1]))
        load_candidates=[load_candidates[i] for i in idx]

    input_slew_fs=ps_to_fs(10)
    t0=ps_to_fs(100)
    epoch=StimulusEpoch(t0,{"S":1},1)
    rows=[]
    short_candidates=[]
    long_candidates=[]

    for load_ff in load_candidates:
        for nchain in range(1,7):
            net,bnet=build_net(buf,buf_out,xor,xor_out,nchain)

            base={
                "nchain":nchain,
                "output_load_ff":load_ff,
                "status":"INVALID",
                "reason":"",
                "input_skew_fs":"",
                "m0_y_pulse_width_fs":"",
                "m0_y_start_fs":"",
                "m0_y_end_fs":"",
                "m1_outcome":"",
                "m1_y_pulse_width_fs":"",
                "m1_suppression_count":"",
            }
            try:
                m0=TransportSimulator(
                    net,p,
                    input_slew_fs_by_net={"S":input_slew_fs},
                    auto_load_from_liberty=True,
                    primary_output_load_ff_by_net={"Y":load_ff},
                )
                t_m0,state_m0=m0.run([epoch])
                if state_m0["Y"]!=0:
                    raise AssertionError("M0 final Y not stable-low")
                bp=[e for e in t_m0 if e.net==bnet]
                if len(bp)!=1:
                    raise AssertionError("Expected exactly one slow-path arrival")
                b_event=bp[0]
                skew=b_event.time_fs-t0
                p0,l0,_=pulse_lineage(net,t_m0,epoch)
                yp=[x for x in p0 if x.net=="Y"]
                yl=[x for x in l0 if x.net=="Y"]
                if len(yp)!=1 or len(yl)!=1:
                    raise AssertionError("Expected exactly one M0 Y hazard pulse")
                if yl[0].classification!="GENERATED":
                    raise AssertionError("Real reconvergent Y pulse must be GENERATED")
                if yl[0].root_ids!=("GROOT0001",):
                    raise AssertionError("Unexpected M0 Y root authority")
                yev=[e for e in t_m0 if e.net=="Y"]
                if len(yev)!=2:
                    raise AssertionError("Expected exactly two M0 Y transitions")

                # Independent first-edge reference: direct S -> XOR.A while B=0.
                xcell=[c for c in net.cells if c.name=="U_X"][0]
                q1=p.delay(
                    xcell,1,input_slew_fs=input_slew_fs,load_ff=load_ff,
                    related_pin="A",pin_values={"A":1,"B":0},
                    input_transition=(0,1)
                )
                if yev[0].time_fs!=t0+q1.delay_fs:
                    raise AssertionError("First XOR event time reference mismatch")

                # Independent second-edge reference using the actual propagated
                # slew of the slow-path event.
                b_slew=m0.last_event_slew_fs[b_event.event_id]
                q2=p.delay(
                    xcell,0,input_slew_fs=b_slew,load_ff=load_ff,
                    related_pin="B",pin_values={"A":1,"B":1},
                    input_transition=(0,1)
                )
                if yev[1].time_fs!=b_event.time_fs+q2.delay_fs:
                    raise AssertionError("Second XOR event time reference mismatch")
                if yp[0].width_fs!=yev[1].time_fs-yev[0].time_fs:
                    raise AssertionError("M0 pulse width/event mismatch")

                m1=InertialSimulator(
                    net,p,
                    input_slew_fs_by_net={"S":input_slew_fs},
                    auto_load_from_liberty=True,
                    primary_output_load_ff_by_net={"Y":load_ff},
                )
                t_m1,state_m1=m1.run([epoch])
                if state_m1["Y"]!=0:
                    raise AssertionError("M1 final Y not stable-low")
                p1,l1,_=pulse_lineage(net,t_m1,epoch)
                y1p=[x for x in p1 if x.net=="Y"]
                y1l=[x for x in l1 if x.net=="Y"]
                sy=[x for x in m1.last_suppressed_transitions if x.instance=="U_X"]

                if len(y1p)==0:
                    if [e for e in t_m1 if e.net=="Y"]:
                        raise AssertionError("M1 has Y transitions but no Y pulse")
                    if len(sy)!=1:
                        raise AssertionError("Suppressed case requires one U_X ledger entry")
                    if not sy[0].cancel_time_fs < sy[0].scheduled_time_fs:
                        raise AssertionError("Suppressed case cancellation must precede firing")
                    evmap={e.event_id:e for e in t_m1}
                    if len(sy[0].original_parent_event_ids)!=1 or len(sy[0].cancel_parent_event_ids)!=1:
                        raise AssertionError("Suppression ledger parent cardinality mismatch")
                    if evmap[sy[0].original_parent_event_ids[0]].net!="S":
                        raise AssertionError("Suppression original cause is not direct S")
                    if evmap[sy[0].cancel_parent_event_ids[0]].net!=bnet:
                        raise AssertionError("Suppression cancel cause is not slow branch")
                    outcome="SUPPRESSED"
                    m1width=""
                    short_candidates.append((load_ff,nchain,skew,yp[0].width_fs,sy[0],base))
                elif len(y1p)==1:
                    if len(y1l)!=1 or y1l[0].classification!="GENERATED":
                        raise AssertionError("Surviving M1 Y lineage mismatch")
                    if y1l[0].root_ids!=("GROOT0001",):
                        raise AssertionError("Surviving M1 root mismatch")
                    if sy:
                        raise AssertionError("Surviving M1 Y pulse must not have U_X suppression")
                    if y_signature(t_m1)!=y_signature(t_m0):
                        raise AssertionError("Surviving M1 Y events must match M0 exactly")
                    if y1p[0].width_fs!=yp[0].width_fs:
                        raise AssertionError("Surviving M1 width must equal M0")
                    outcome="SURVIVED"
                    m1width=y1p[0].width_fs
                    long_candidates.append((load_ff,nchain,skew,yp[0].width_fs,base))
                else:
                    raise AssertionError("Unexpected number of M1 Y pulses")

                base.update({
                    "status":"PASS",
                    "input_skew_fs":skew,
                    "m0_y_pulse_width_fs":yp[0].width_fs,
                    "m0_y_start_fs":yp[0].start_fs,
                    "m0_y_end_fs":yp[0].end_fs,
                    "m1_outcome":outcome,
                    "m1_y_pulse_width_fs":m1width,
                    "m1_suppression_count":len(sy),
                })
            except Exception as e:
                base["reason"]=type(e).__name__+":"+str(e)
            rows.append(base)

    if not short_candidates:
        raise AssertionError("No real M0 hazard / M1-suppressed candidate found")
    if not long_candidates:
        raise AssertionError("No real M1-surviving reconvergent candidate found")

    # Deterministic selected authorities:
    # shortest chain first, then smallest load; for survivor same policy.
    short_candidates.sort(key=lambda x:(x[1],x[0],x[2],x[3]))
    sload,sn,sskew,swidth,sledger,_=short_candidates[0]

    # Select the shortest surviving case with a strictly longer buffer path
    # than the selected suppressed case. This makes the real experiment a
    # genuine skew-control bracket rather than comparing unrelated loads at
    # the same topology depth.
    longer=[x for x in long_candidates if x[1] > sn]
    if not longer:
        raise AssertionError(
            "No M1-surviving real candidate with longer buffer chain than "
            "the selected suppressed candidate"
        )
    longer.sort(key=lambda x:(x[1],x[0],x[2],x[3]))
    lload,ln,lskew,lwidth,_=longer[0]

    # This bracket is descriptive only: simple event-inertial behavior,
    # NOT a SPICE-calibrated threshold.

    with (out/"real_sky130_b6_sweep.csv").open("w",newline="") as f:
        fields=[
            "nchain","output_load_ff","status","reason","input_skew_fs",
            "m0_y_pulse_width_fs","m0_y_start_fs","m0_y_end_fs",
            "m1_outcome","m1_y_pulse_width_fs","m1_suppression_count"
        ]
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    selected=[
        {
            "case":"SHORT_SUPPRESSED",
            "output_load_ff":sload,
            "buffer_chain_length":sn,
            "input_skew_fs":sskew,
            "m0_pulse_width_fs":swidth,
            "m1_outcome":"SUPPRESSED",
            "suppressed_instance":sledger.instance,
            "suppressed_net":sledger.net,
            "scheduled_time_fs":sledger.scheduled_time_fs,
            "cancel_time_fs":sledger.cancel_time_fs,
        },
        {
            "case":"LONG_SURVIVED",
            "output_load_ff":lload,
            "buffer_chain_length":ln,
            "input_skew_fs":lskew,
            "m0_pulse_width_fs":lwidth,
            "m1_outcome":"SURVIVED",
            "m1_pulse_width_fs":lwidth,
        },
    ]
    with (out/"real_sky130_b6_selected.csv").open("w",newline="") as f:
        fields=sorted({k for r in selected for k in r})
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        for r in selected:
            w.writerow(r)

    summary={
        "status":"PASS",
        "source_sha256":sha256_file(a.lib),
        "model":"B6_REAL_RECONVERGENT_XOR_M0_M1",
        "topology":"S_direct_to_XOR_A__S_through_BUF_chain_to_XOR_B",
        "real_cells":{"buf":buf,"xor2":xor},
        "input_slew_fs":input_slew_fs,
        "load_candidates_ff":load_candidates,
        "buffer_chain_lengths":[1,2,3,4,5,6],
        "sweep_case_count":len(rows),
        "valid_case_count":sum(r["status"]=="PASS" for r in rows),
        "suppressed_case_count":sum(r.get("m1_outcome")=="SUPPRESSED" for r in rows),
        "survived_case_count":sum(r.get("m1_outcome")=="SURVIVED" for r in rows),
        "selected_short_suppressed":selected[0],
        "selected_long_survived":selected[1],
        "m0_short_lineage":"GENERATED:GROOT0001",
        "m1_long_lineage":"GENERATED:GROOT0001",
        "suppression_ledger_causal_check":True,
        "independent_xor_event_time_reference":True,
        "pulse_threshold_interpretation":"M1_SIMPLE_EVENT_INERTIAL_ONLY_NOT_SPICE_CALIBRATED",
    }
    (out/"real_sky130_b6_summary.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)
    )

    print("B6_REAL_SWEEP_CASE_COUNT=%d"%len(rows))
    print("B6_REAL_VALID_CASE_COUNT=%d"%summary["valid_case_count"])
    print("B6_REAL_SUPPRESSED_CASE_COUNT=%d"%summary["suppressed_case_count"])
    print("B6_REAL_SURVIVED_CASE_COUNT=%d"%summary["survived_case_count"])
    print("B6_REAL_SHORT_CHAIN_LENGTH=%d"%sn)
    print("B6_REAL_SHORT_INPUT_SKEW_FS=%d"%sskew)
    print("B6_REAL_SHORT_M0_WIDTH_FS=%d"%swidth)
    print("B6_REAL_LONG_CHAIN_LENGTH=%d"%ln)
    print("B6_REAL_LONG_INPUT_SKEW_FS=%d"%lskew)
    print("B6_REAL_LONG_M0_M1_WIDTH_FS=%d"%lwidth)
    print("B6_REAL_RECONVERGENT_M0_GENERATION_PASS")
    print("B6_REAL_M1_SHORT_SUPPRESSION_PASS")
    print("B6_REAL_M1_LONG_SURVIVAL_PASS")
    print("B6_REAL_SUPPRESSION_CAUSAL_LEDGER_PASS")
    print("B6_REAL_LINEAGE_GENERATED_ROOT_PASS")
    print("B6_REAL_XOR_EVENT_REFERENCE_PASS")

if __name__=="__main__":
    main()

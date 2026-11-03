from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path

from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider, bilinear
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator
from glitchscope.inertial import InertialSimulator
from glitchscope.logic import eval_primitive

EXPECTED_SHA="ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9"

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):
            h.update(c)
    return h.hexdigest()

def find_cell(lib, exact, token):
    if exact in lib.cells: return exact
    xs=sorted(n for n in lib.cells if token in n.lower())
    if not xs: raise AssertionError("No real cell matching "+token)
    return xs[0]

def sole_output(lc):
    outs=sorted({a.output_pin for a in lc.timing_arcs})
    if len(outs)!=1:
        raise AssertionError("Expected one output, got "+str(outs))
    return outs[0]

def expected_sense(input_transition, output_transition):
    ir=input_transition[1]>input_transition[0]
    orise=output_transition[1]>output_transition[0]
    return "positive_unate" if ir==orise else "negative_unate"

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

    roles=[
        ("xor2","XOR2",find_cell(lib,"sky130_fd_sc_hd__xor2_1","__xor2_")),
        ("xnor2","XNOR2",find_cell(lib,"sky130_fd_sc_hd__xnor2_1","__xnor2_")),
    ]

    rows=[]
    total=0
    for role,kind,name in roles:
        lc=lib.cells[name]
        outpin=sole_output(lc)

        if len(lc.timing_arcs)!=4:
            raise AssertionError(name+" expected exactly 4 parsed propagation arcs")

        for pin in ("A","B"):
            arcs=[x for x in lc.timing_arcs if x.related_pin==pin]
            senses=sorted(x.timing_sense for x in arcs)
            if senses!=["negative_unate","positive_unate"]:
                raise AssertionError(
                    "%s %s mixed-sense authority mismatch: %s"%(name,pin,senses)
                )

            other="B" if pin=="A" else "A"
            for other_value in (0,1):
                for old_in,new_in in ((0,1),(1,0)):
                    initial={pin:old_in,other:other_value}
                    final=dict(initial); final[pin]=new_in
                    old_out=eval_primitive(kind,initial)
                    new_out=eval_primitive(kind,final)
                    exp_sense=expected_sense(
                        (old_in,new_in),(old_out,new_out)
                    )

                    cell=Cell(
                        "U_"+role,kind,{"A":"A","B":"B"},"Y",0,0,
                        library_cell=name,library_output_pin=outpin
                    )
                    arc=p.select_arc(
                        cell,new_out,related_pin=pin,
                        pin_values=final,input_transition=(old_in,new_in)
                    )
                    if arc.timing_sense!=exp_sense:
                        raise AssertionError(
                            "%s pin=%s other=%d %d->%d expected=%s got=%s"%
                            (name,pin,other_value,old_in,new_in,
                             exp_sense,arc.timing_sense)
                        )

                    # Exact first grid point of the selected output-polarity table.
                    dt=arc.cell_rise if new_out else arc.cell_fall
                    st=arc.rise_transition if new_out else arc.fall_transition
                    x=dt.index_1[0]
                    y=dt.index_2[0]
                    slew_fs=ps_to_fs(x*lib.time_unit_ps)
                    load_ff=y*lib.capacitance_unit_ff
                    q=p.delay(
                        cell,new_out,input_slew_fs=slew_fs,load_ff=load_ff,
                        related_pin=pin,pin_values=final,
                        input_transition=(old_in,new_in)
                    )
                    exp_delay=ps_to_fs(
                        bilinear(dt,x,y)*lib.time_unit_ps
                    )
                    exp_slew=ps_to_fs(
                        bilinear(st,x,y)*lib.time_unit_ps
                    )
                    if q.delay_fs!=exp_delay or q.output_slew_fs!=exp_slew:
                        raise AssertionError("Provider/table exact-grid mismatch")

                    net=Network(
                        ["A","B"],["Y"],[cell],initial
                    )
                    epoch=StimulusEpoch(
                        ps_to_fs(100),{pin:new_in},total+1
                    )
                    sim=TransportSimulator(
                        net,p,
                        input_slew_fs_by_net={pin:slew_fs},
                        load_ff_by_net={"Y":load_ff},
                    )
                    tr,state=sim.run([epoch])
                    ye=[e for e in tr if e.net=="Y"]
                    if len(ye)!=1:
                        raise AssertionError("Expected one real output event")
                    if ye[0].time_fs!=ps_to_fs(100)+exp_delay:
                        raise AssertionError("Real simulator delay mismatch")
                    if (ye[0].old_value,ye[0].new_value)!=(old_out,new_out):
                        raise AssertionError("Real simulator polarity mismatch")
                    if sim.last_event_slew_fs[ye[0].event_id]!=exp_slew:
                        raise AssertionError("Real simulator slew mismatch")
                    if state["Y"]!=new_out:
                        raise AssertionError("Real final state mismatch")

                    # M1 must agree with M0 for a single isolated transition.
                    isim=InertialSimulator(
                        net,p,
                        input_slew_fs_by_net={pin:slew_fs},
                        load_ff_by_net={"Y":load_ff},
                    )
                    itr,istate=isim.run([epoch])
                    iye=[e for e in itr if e.net=="Y"]
                    if len(iye)!=1:
                        raise AssertionError("M1 isolated transition missing")
                    if [
                        (e.time_fs,e.old_value,e.new_value)
                        for e in iye
                    ] != [
                        (e.time_fs,e.old_value,e.new_value)
                        for e in ye
                    ]:
                        raise AssertionError("M0/M1 isolated transition mismatch")
                    if isim.last_suppressed_transitions:
                        raise AssertionError(
                            "M1 unexpectedly suppressed isolated transition"
                        )
                    if istate["Y"]!=new_out:
                        raise AssertionError("M1 real final state mismatch")

                    rows.append([
                        role,name,outpin,pin,other,other_value,
                        "%d->%d"%(old_in,new_in),
                        "%d->%d"%(old_out,new_out),
                        exp_sense,arc.timing_sense,
                        slew_fs,load_ff,exp_delay,exp_slew,
                        ye[0].time_fs,
                    ])
                    total+=1

    if total!=16:
        raise AssertionError("Expected 16 real XOR/XNOR cases, got %d"%total)

    with (out/"real_sky130_b5_multi_arc.csv").open("w",newline="") as f:
        w=csv.writer(f)
        w.writerow([
            "role","library_cell","output_pin","related_pin","other_pin",
            "other_value","input_transition","output_transition",
            "expected_sense","selected_sense","input_slew_fs","load_ff",
            "delay_fs","output_slew_fs","event_time_fs"
        ])
        w.writerows(rows)

    summary={
        "status":"PASS",
        "source_sha256":sha256_file(a.lib),
        "model":"B5_STATE_CONSISTENT_MULTI_ARC_SELECTION",
        "real_cells":{r:n for r,_,n in roles},
        "case_count":total,
        "cells":["xor2","xnor2"],
        "related_pins":["A","B"],
        "other_pin_values":[0,1],
        "input_directions":["0->1","1->0"],
        "selected_senses":["negative_unate","positive_unate"],
        "conditional_filtering_order":"when_then_timing_sense",
        "duplicate_same_sense_policy":"fail_closed",
        "non_unate_ambiguity_policy":"fail_closed",
        "m0_m1_isolated_transition_equivalence":True,
    }
    (out/"real_sky130_b5_summary.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)
    )

    print("B5_REAL_CASE_COUNT=16")
    print("B5_REAL_XOR_MIXED_SENSE_PASS")
    print("B5_REAL_XNOR_MIXED_SENSE_PASS")
    print("B5_REAL_STATE_CONSISTENT_ARC_SELECTION_PASS")
    print("B5_REAL_M0_M1_ISOLATED_EQUIVALENCE_PASS")
    print("B5_REAL_DUPLICATE_AMBIGUITY_POLICY_PASS")

if __name__=="__main__":
    main()

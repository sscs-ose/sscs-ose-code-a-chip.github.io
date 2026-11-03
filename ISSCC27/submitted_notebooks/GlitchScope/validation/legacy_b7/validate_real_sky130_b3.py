from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path

from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):
            h.update(c)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--lib",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=True)

    lib=parse_liberty_file(a.lib)
    p=LibertyDelayProvider(lib)
    inv="sky130_fd_sc_hd__inv_1"
    if inv not in lib.cells:
        xs=sorted(n for n in lib.cells if "__inv_" in n.lower())
        if not xs:
            raise AssertionError("No real SKY130 inverter")
        inv=xs[0]

    arcs=[x for x in lib.cells[inv].timing_arcs
          if x.related_pin=="A" and not x.when]
    if len(arcs)!=1:
        raise AssertionError("Expected one unconditional INV A arc")
    arc=arcs[0]

    # Common interior load characterized for both output polarities.
    lo=max(min(arc.cell_rise.index_2),min(arc.cell_fall.index_2))
    hi=min(max(arc.cell_rise.index_2),max(arc.cell_fall.index_2))
    if not hi>lo:
        raise AssertionError("No common INV characterized load interval")
    load=((lo+hi)/2.0)*lib.capacitance_unit_ff

    s0=ps_to_fs(20)
    n=Network(
        ["A"],["Y"],
        [Cell("U_INV","INV",{"A":"A"},"Y",0,0,
              library_cell=inv,library_output_pin="Y")],
        {"A":0},
    )
    c=n.cells[0]

    qfall=p.delay(
        c,0,input_slew_fs=s0,load_ff=load,
        related_pin="A",pin_values={"A":1},input_transition=(0,1)
    )
    qrise=p.delay(
        c,1,input_slew_fs=s0,load_ff=load,
        related_pin="A",pin_values={"A":0},input_transition=(1,0)
    )

    # Choose a PI pulse interval that is strictly shorter than the first
    # output delay, so epoch 2 arrives while epoch-1 work is pending, while
    # preserving chronological output edge order.
    lower=max(1,qfall.delay_fs-qrise.delay_fs+1)
    upper=qfall.delay_fs-1
    if lower>upper:
        raise AssertionError(
            "Unable to construct ordered real overlapping pulse from INV delays"
        )
    sep=(lower+upper)//2

    t0=ps_to_fs(100)
    t1=t0+sep
    expected_fall=t0+qfall.delay_fs
    expected_rise=t1+qrise.delay_fs
    if not (t1<expected_fall<expected_rise):
        raise AssertionError("Constructed overlap inequalities failed")

    sim=TransportSimulator(
        n,p,default_input_slew_fs=s0,
        load_ff_by_net={"Y":load},
    )
    tr,state=sim.run([
        StimulusEpoch(t0,{"A":1},1),
        StimulusEpoch(t1,{"A":0},2),
    ])

    if [e.time_fs for e in tr] != sorted(e.time_fs for e in tr):
        raise AssertionError("Real B3 trace is not chronological")

    pi=[e for e in tr if e.net=="A"]
    y=[e for e in tr if e.net=="Y"]
    if len(pi)!=2 or len(y)!=2:
        raise AssertionError("Expected two PI and two output transitions")

    if [e.time_fs for e in pi] != [t0,t1]:
        raise AssertionError("PI chronology mismatch")
    if [e.time_fs for e in y] != [expected_fall,expected_rise]:
        raise AssertionError("Real transport output times mismatch")
    if [(e.old_value,e.new_value) for e in y] != [(1,0),(0,1)]:
        raise AssertionError("Real transport output polarity mismatch")
    if y[0].epoch_id!=1 or y[1].epoch_id!=2:
        raise AssertionError("Output epoch provenance mismatch")
    if sim.last_event_slew_fs[y[0].event_id]!=qfall.output_slew_fs:
        raise AssertionError("Falling output slew mismatch")
    if sim.last_event_slew_fs[y[1].event_id]!=qrise.output_slew_fs:
        raise AssertionError("Rising output slew mismatch")
    if sim.last_overlap_epoch_ids!=(2,):
        raise AssertionError(
            "Expected epoch 2 to be reported as overlapping pending transport work"
        )
    if state["Y"]!=1:
        raise AssertionError("Unexpected final real INV state")

    width=expected_rise-expected_fall
    if width<=0:
        raise AssertionError("Expected positive transported pulse width")

    with (out/"real_sky130_b3_overlap.csv").open("w",newline="") as f:
        w=csv.writer(f)
        w.writerow([
            "pi_separation_fs","load_ff","input_slew_fs",
            "fall_delay_fs","rise_delay_fs","fall_output_slew_fs",
            "rise_output_slew_fs","output_fall_time_fs",
            "output_rise_time_fs","transported_pulse_width_fs"
        ])
        w.writerow([
            sep,load,s0,qfall.delay_fs,qrise.delay_fs,
            qfall.output_slew_fs,qrise.output_slew_fs,
            expected_fall,expected_rise,width
        ])

    summary={
        "status":"PASS",
        "source_sha256":sha256_file(a.lib),
        "library_cell":inv,
        "model":"M0_transport_global_chronological",
        "primary_input_slew_fs":s0,
        "load_ff":load,
        "pi_separation_fs":sep,
        "first_output_delay_fs":qfall.delay_fs,
        "second_output_delay_fs":qrise.delay_fs,
        "output_fall_time_fs":expected_fall,
        "output_rise_time_fs":expected_rise,
        "transported_pulse_width_fs":width,
        "output_fall_slew_fs":qfall.output_slew_fs,
        "output_rise_slew_fs":qrise.output_slew_fs,
        "overlap_epoch_ids":[2],
        "trace_time_monotonic":True,
        "same_time_epoch_policy":"fail_closed",
        "final_state_Y":state["Y"],
    }
    (out/"real_sky130_b3_summary.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)
    )

    print("B3_REAL_PI_SEPARATION_FS=%d"%sep)
    print("B3_REAL_FALL_DELAY_FS=%d"%qfall.delay_fs)
    print("B3_REAL_RISE_DELAY_FS=%d"%qrise.delay_fs)
    print("B3_REAL_TRANSPORTED_PULSE_WIDTH_FS=%d"%width)
    print("B3_REAL_GLOBAL_CHRONOLOGY_PASS")
    print("B3_REAL_OVERLAPPING_EPOCH_TRANSPORT_PASS")
    print("B3_REAL_EVENT_PROVENANCE_PASS")

if __name__=="__main__":
    main()

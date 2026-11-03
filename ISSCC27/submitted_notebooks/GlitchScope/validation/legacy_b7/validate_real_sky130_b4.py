from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path

from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator
from glitchscope.inertial import InertialSimulator

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):
            h.update(c)
    return h.hexdigest()

def output_events(trace):
    return [e for e in trace if e.net=="Y"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--lib",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=True)

    lib=parse_liberty_file(a.lib)
    provider=LibertyDelayProvider(lib)
    inv="sky130_fd_sc_hd__inv_1"
    if inv not in lib.cells:
        xs=sorted(n for n in lib.cells if "__inv_" in n.lower())
        if not xs:
            raise AssertionError("No real SKY130 inverter")
        inv=xs[0]

    arcs=[x for x in lib.cells[inv].timing_arcs
          if x.related_pin=="A" and not x.when]
    if len(arcs)!=1:
        raise AssertionError("Expected one unconditional INV A timing arc")
    arc=arcs[0]

    lo=max(min(arc.cell_rise.index_2),min(arc.cell_fall.index_2))
    hi=min(max(arc.cell_rise.index_2),max(arc.cell_fall.index_2))
    if not hi>lo:
        raise AssertionError("No common characterized INV load interval")
    load=((lo+hi)/2.0)*lib.capacitance_unit_ff
    slew=ps_to_fs(20)

    n=Network(
        ["A"],["Y"],
        [Cell("U_INV","INV",{"A":"A"},"Y",0,0,
              library_cell=inv,library_output_pin="Y")],
        {"A":0},
    )
    c=n.cells[0]
    qfall=provider.delay(
        c,0,input_slew_fs=slew,load_ff=load,
        related_pin="A",pin_values={"A":1},input_transition=(0,1)
    )
    qrise=provider.delay(
        c,1,input_slew_fs=slew,load_ff=load,
        related_pin="A",pin_values={"A":0},input_transition=(1,0)
    )
    if qfall.delay_fs<=1:
        raise AssertionError("Real falling delay too small for short-pulse test")

    t0=ps_to_fs(100)
    short_sep=max(1,qfall.delay_fs//2)
    boundary_sep=qfall.delay_fs
    margin=max(1,qfall.delay_fs//2)
    long_sep=max(qfall.delay_fs+margin,
                 qfall.delay_fs-qrise.delay_fs+1+margin)

    def run_case(sep):
        epochs=[
            StimulusEpoch(t0,{"A":1},1),
            StimulusEpoch(t0+sep,{"A":0},2),
        ]
        kwargs=dict(
            delay_provider=provider,
            default_input_slew_fs=slew,
            load_ff_by_net={"Y":load},
        )
        m0=TransportSimulator(n,**kwargs)
        tr0,st0=m0.run(epochs)
        m1=InertialSimulator(n,**kwargs)
        tr1,st1=m1.run(epochs)
        return tr0,st0,m1,tr1,st1

    short_m0,_,short_sim,short_m1,short_state=run_case(short_sep)
    if len(output_events(short_m0))!=2:
        raise AssertionError("M0 short pulse did not transport two output edges")
    if output_events(short_m1):
        raise AssertionError("M1 short pulse was not suppressed")
    if len(short_sim.last_suppressed_transitions)!=1:
        raise AssertionError("Expected one M1 short-pulse suppression")
    sq=short_sim.last_suppressed_transitions[0]
    if sq.scheduled_time_fs != t0+qfall.delay_fs:
        raise AssertionError("Short suppression scheduled time mismatch")
    if sq.cancel_time_fs != t0+short_sep:
        raise AssertionError("Short suppression cancel time mismatch")
    if short_state["Y"]!=1:
        raise AssertionError("Short M1 final state mismatch")

    boundary_m0,_,boundary_sim,boundary_m1,boundary_state=run_case(boundary_sep)
    if len(output_events(boundary_m0))!=2:
        raise AssertionError("M0 boundary pulse did not transport")
    if output_events(boundary_m1):
        raise AssertionError("M1 boundary pulse was not suppressed")
    if len(boundary_sim.last_suppressed_transitions)!=1:
        raise AssertionError("Expected one boundary suppression")
    bq=boundary_sim.last_suppressed_transitions[0]
    if bq.cancel_time_fs != bq.scheduled_time_fs:
        raise AssertionError("Boundary cancellation is not exactly at pending event")
    if boundary_state["Y"]!=1:
        raise AssertionError("Boundary M1 final state mismatch")

    long_m0,_,long_sim,long_m1,long_state=run_case(long_sep)
    y0=output_events(long_m0)
    y1=output_events(long_m1)
    if [(e.time_fs,e.old_value,e.new_value) for e in y0] != [
       (e.time_fs,e.old_value,e.new_value) for e in y1]:
        raise AssertionError("M1 long-pulse output does not match M0")
    if len(y1)!=2:
        raise AssertionError("Expected long M1 pulse to survive")
    if long_sim.last_suppressed_transitions:
        raise AssertionError("Long M1 pulse unexpectedly recorded suppression")
    if long_state["Y"]!=1:
        raise AssertionError("Long M1 final state mismatch")

    long_width=y1[1].time_fs-y1[0].time_fs
    short_m0_width=output_events(short_m0)[1].time_fs-output_events(short_m0)[0].time_fs
    boundary_m0_width=output_events(boundary_m0)[1].time_fs-output_events(boundary_m0)[0].time_fs

    rows=[
        ["short",short_sep,2,0,1,short_m0_width],
        ["boundary",boundary_sep,2,0,1,boundary_m0_width],
        ["long",long_sep,2,2,0,long_width],
    ]
    with (out/"real_sky130_b4_m1_cases.csv").open("w",newline="") as f:
        w=csv.writer(f)
        w.writerow([
            "case","pi_separation_fs","m0_output_edges","m1_output_edges",
            "m1_suppressed_events","output_pulse_width_fs"
        ])
        w.writerows(rows)

    summary={
        "status":"PASS",
        "source_sha256":sha256_file(a.lib),
        "library_cell":inv,
        "model":"M1_SIMPLE_EVENT_INERTIAL",
        "m0_reference_model":"M0_transport_global_chronological",
        "load_ff":load,
        "primary_input_slew_fs":slew,
        "fall_delay_fs":qfall.delay_fs,
        "rise_delay_fs":qrise.delay_fs,
        "short_pi_separation_fs":short_sep,
        "boundary_pi_separation_fs":boundary_sep,
        "long_pi_separation_fs":long_sep,
        "short_m0_output_pulse_width_fs":short_m0_width,
        "boundary_m0_output_pulse_width_fs":boundary_m0_width,
        "long_m1_output_pulse_width_fs":long_width,
        "short_m1_suppressed":True,
        "boundary_m1_suppressed":True,
        "long_m1_survived":True,
        "inertial_tie_policy":"external_epoch_first_cancel_if_equal_time",
        "suppression_reason":"logical_reversal_before_pending_output_fired",
        "cell_specific_calibration":False,
        "spice_calibrated":False,
    }
    (out/"real_sky130_b4_summary.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)
    )

    print("B4_REAL_FALL_DELAY_FS=%d"%qfall.delay_fs)
    print("B4_REAL_RISE_DELAY_FS=%d"%qrise.delay_fs)
    print("B4_REAL_SHORT_SEPARATION_FS=%d"%short_sep)
    print("B4_REAL_BOUNDARY_SEPARATION_FS=%d"%boundary_sep)
    print("B4_REAL_LONG_SEPARATION_FS=%d"%long_sep)
    print("B4_REAL_SHORT_M0_WIDTH_FS=%d"%short_m0_width)
    print("B4_REAL_LONG_M1_WIDTH_FS=%d"%long_width)
    print("B4_REAL_M0_SHORT_TRANSPORT_PASS")
    print("B4_REAL_M1_SHORT_REJECTION_PASS")
    print("B4_REAL_M1_BOUNDARY_REJECTION_PASS")
    print("B4_REAL_M1_LONG_SURVIVAL_PASS")
    print("B4_REAL_SUPPRESSION_LEDGER_PASS")

if __name__=="__main__":
    main()

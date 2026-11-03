from __future__ import annotations
import argparse
from .fixtures import *
from .timed import TransportSimulator
from .analysis import stable_epoch_maps
from .classify import extract_pulses
from .lineage import classify_glitch_lineages
from .report import write_results

FIXTURES={
"inverter":inverter_fixture,
"xor_atomic":xor_atomic_no_glitch_fixture,
"xor_reconvergent":xor_reconvergent_fixture,
"static1_hazard":static1_hazard_fixture,
"propagated_glitch":propagated_glitch_fixture,
"changed_final_state":changed_final_state_glitch_fixture,
"two_epoch":two_epoch_glitch_fixture,
"merged_roots":merged_roots_fixture,
}
def main():
    p=argparse.ArgumentParser(); p.add_argument("fixture",choices=sorted(FIXTURES)); p.add_argument("--out",default="results/run")
    a=p.parse_args()
    net,epochs=FIXTURES[a.fixture]()
    before,after=stable_epoch_maps(net,epochs)
    trace,state=TransportSimulator(net).run(epochs)
    pulses=extract_pulses(trace,before,after)
    lineages,edges=classify_glitch_lineages(trace,pulses)
    write_results(a.out,trace,pulses,state,lineages,edges)
    print(f"FIXTURE={a.fixture}")
    for g in lineages:
        print(f"{g.glitch_id} epoch={g.epoch_id} net={g.net} class={g.classification} roots={','.join(g.root_ids)} width_fs={g.width_fs} polarity={g.polarity}")
    print("GLITCHSCOPE_PHASE_A2_RUN_PASS")
if __name__=="__main__": main()

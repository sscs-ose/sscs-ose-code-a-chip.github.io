from pathlib import Path
from xschem_testbench import xschem_testbench

if __name__ == "__main__":
    tests_dir = Path("/workspaces/bandgapReferenceCircuit/tests/")
    sch_dir = Path("/workspaces/bandgapReferenceCircuit/bandgap_sky130_v1/")
    tests = [
        ["dc_op", "bandgap_1v_v01_dcop_testbench.sch"],
        ["tran",  "bandgap_1v_v01_transient_sim.sch"],
        ["tran_gauss", "bandgap_1v_v01_transient_gauss.sch"], # MonteCarlo
        ["tempsweep", "tsmc_bandgap_real_tempsweep.sch"],
    ]
    for test in tests:
        xschem_testbench.run(test[1], sch_dir / test[1], tests_dir / test[0])

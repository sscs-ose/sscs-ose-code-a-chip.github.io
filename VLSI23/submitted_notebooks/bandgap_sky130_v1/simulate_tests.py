from importlib.resources import path
import tests
import bandgap_sky130_v1
from xschem_testbench import xschem_testbench


if __name__ == "__main__":
    with (path(tests), path(bandgap_sky130_v1)) \
        as (tests_dir, sch_dir):
        tests = [
            ["dc_op", "bandgap_1v_v01_dcop_testbench.sch"],
            #["tran",  "tsmc_bandgap_real_tran.sch"],
            #["tran_gauss", "tsmc_bandgap_real_tran_gauss.sch"], # MonteCarlo
            #["tempsweep", "tsmc_bandgap_real_tempsweep.sch"],
        ]
        for test in tests:
            xschem_testbench.run(test[1], sch_dir / test[1], tests_dir / test[0])

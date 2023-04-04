from pathlib import path

import hdl21 as h
from hdl21.sim import Op, Include, Save, SaveMode
import sky130
from vlsir import spice

bandgap = h.SchematicModule(
    name="bandgap_01",
    desc="The bandgap top-level",
    domain="xschem schematic",
    port_list=[h.Inout(name="PLUS"), h.Inout(name="MINUS")],
    schematic_path=Path("/workspaces/prjs/bandgapReferenceCircuit/tests/dc_op/bandgap_1v_v01_dcop_testbench.sch"),
)


@hs.sim
class BandgapDcopSim:
    """# Bandgap DC Operating Point Simulation Input"""

    @h.module
    class Tb:
        """# Basic Mos Testbench"""

        VSS = h.Port()  # The testbench interface: sole port VSS
        vdc = h.Vdc(dc=1.8)(n=VSS)  # A DC voltage source
        dut = bandgap()()

    # Simulation Stimulus
    op = Op()
    mod = Include(sky130.install.models)
    save = Save(SaveMode.ALL)


def run():
    """# Run the simulation."""

    # Set a few runtime options.
    # If you'd like a different simulator, this and the check below are the place to specify it!
    opts = spice.SimOptions(
        simulator=spice.SupportedSimulators.NGSPICE,
        fmt=spice.ResultFormat.SIM_DATA,  # Get Python-native result types
        rundir="./scratch",  # Set the working directory for the simulation. Uses a temporary directory by default.
    )
    if not spice.ngspice.available():
        print("ngspice is not available. Skipping simulation.")
        return

    # Run the simulation!
    results = BandgapDcopSim.run(opts)

if __name__ == "__main__":
    run()

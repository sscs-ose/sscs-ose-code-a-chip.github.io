import numpy as np
import matplotlib.pyplot as plt
from pathsim.blocks.sources import Source
from pathsim.blocks.scope import Scope  
from pathsim.connection import Connection
from pathsim.simulation import Simulation
from pathsim.solvers import RKBS32
import argparse
from crsar import CRSARCtrlODC

parser = argparse.ArgumentParser(description="FIXME")

parser.add_argument("-a", type=float, required=True, help="Analog Offset")
parser.add_argument("-o", type=str, required=True, help="Output file path")

args = parser.parse_args()

analog_offset = args.a
output_path = args.o

f_clk = 20e6
T_clk = 1.0 / f_clk
OVERSAMPLING_RATIO = 100
num_cycles = 10
ctrl_tau_cycles = 1
sar_tau_cycles = 2

sar_const_dout = 27

src_sar_done = Source(lambda t: 1 if ((t % T_clk) < (T_clk / 2) and t > (sar_tau_cycles*T_clk)) else 0)
src_sar_dout = Source(lambda t: sar_const_dout)
crsar_ctrl_odc = CRSARCtrlODC(analog_offset=analog_offset, tau=ctrl_tau_cycles*T_clk)
scope = Scope(sampling_period=T_clk/OVERSAMPLING_RATIO, 
              labels=['Vinp offset', 'Vinn offset', 'Sample Enable', 'ODC State'])

connections = [
    Connection(src_sar_done, crsar_ctrl_odc[0]),
    Connection(src_sar_dout, crsar_ctrl_odc[1]),
    Connection(crsar_ctrl_odc[4], scope[0]),
    Connection(crsar_ctrl_odc[5], scope[1]),
    Connection(crsar_ctrl_odc[3], scope[2]),
    Connection(crsar_ctrl_odc[2], scope[3])
]

blocks = [src_sar_done, src_sar_dout, crsar_ctrl_odc, scope]

# Simulation with adaptive solver
Sim = Simulation(
    blocks,
    connections,
    Solver=RKBS32
)

Sim.run((num_cycles + sar_tau_cycles)*T_clk)

scope.save(output_path)
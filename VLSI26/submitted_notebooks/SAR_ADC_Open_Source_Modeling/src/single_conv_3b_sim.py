import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from pathsim.blocks.sources import Source
from pathsim.blocks.scope import Scope  
from pathsim.connection import Connection
from pathsim.simulation import Simulation
from pathsim.solvers import RKBS32
from crsar import CRSAR
import argparse

parser = argparse.ArgumentParser(description="Accept n and output file path")

parser.add_argument("-o", type=str, required=True, help="Output file path")
parser.add_argument("-se", type=float, required=False, default=0, help="CDAC Settling Error in %")
parser.add_argument("-wa", type=str, required=False, default=None, help="Path to actual conversion weights (assumed to be in npy file)")

args = parser.parse_args()

output_path = args.o
se = args.se
weights_actual = np.load(args.wa) if args.wa is not None else None

n_bits = 3
f_clk = 20e6
T_clk = 1.0 / f_clk
vd = -0.4
vref = 1
vcm = 0.5
OVERSAMPLING_RATIO = 100

# Blocks that define the system
srcp = Source(lambda t: vcm + vd/2)
srcn = Source(lambda t: vcm - vd/2)
src_null = Source(lambda t: 0)
src_samp_en = Source(lambda t: 1)
crsar = CRSAR(n_bits=n_bits, vref=1.0, T=T_clk, settling_error_pct=se, weights=weights_actual)
scope = Scope(sampling_period=T_clk/OVERSAMPLING_RATIO, 
              labels=['(+) Comp. In', '(-) Comp. In', 'Done', 'Dout'])

# Connections between the blocks
connections = [
    Connection(srcp, crsar[0]),
    Connection(srcn, crsar[1]),
    Connection(src_null, crsar[2]),
    Connection(src_null, crsar[3]),
    Connection(src_samp_en, crsar[4]),
    Connection(crsar[3], scope[0]),
    Connection(crsar[4], scope[1]),
    Connection(crsar[2], scope[2]),
    Connection(crsar[1], scope[3])
]

blocks = [srcp, srcn, crsar, scope, src_null, src_samp_en]

# Simulation with adaptive solver
Sim = Simulation(
    blocks,
    connections,
    Solver=RKBS32
)

Sim.run(2*n_bits*T_clk)

scope.save(output_path)
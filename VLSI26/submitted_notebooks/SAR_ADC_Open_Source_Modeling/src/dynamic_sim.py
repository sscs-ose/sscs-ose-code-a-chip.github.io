import numpy as np
from pathsim.blocks.sources import Source
from pathsim.blocks.scope import Scope  
from pathsim.blocks.adder import Adder
from pathsim.connection import Connection
from pathsim.simulation import Simulation
from pathsim.solvers import RKBS32
from crsar import CRSAR
import argparse

parser = argparse.ArgumentParser(description="Accept n and output file path")

parser.add_argument("-n", type=int, required=True, help="ADC resolution")
parser.add_argument("-N", type=int, required=True, help="FFT Size")
parser.add_argument("-M", type=int, required=True, help="Signal Frequency Bin")
parser.add_argument("-o", type=str, required=True, help="Output file path")
parser.add_argument("-wa", type=str, required=False, default=None, help="Path to actual conversion weights (assumed to be in npy file)")
parser.add_argument("-we", type=str, required=False, default=None, help="Path to estimated conversion weights (assumed to be in npy file)")
parser.add_argument("-se", type=float, required=False, default=0, help="CDAC Settling Error in %")
parser.add_argument("-cn", type=float, required=False, default=0, help="RMS Value of Input-Referred Comparator Noise")

args = parser.parse_args()

n = args.n
output_path = args.o
N = args.N
M = args.M
se = args.se
cn = args.cn
weights_actual = np.load(args.wa) if args.wa is not None else None
weights_estimated = np.load(args.we) if args.we is not None else None
ndecisions = len(weights_actual) if args.wa is not None else n

f_clk = 20e6
T_clk = 1.0 / f_clk
STARTUP_CYCLES = 10
OVERSAMPLING_RATIO = 2
vcm = 0.5
vref = 1.0
vlsb = vref / (2 ** n)
vd = vref-(vlsb/2) # SAR is mid-rise quantizer so SQNR maximized at Vref-delta/2

# Blocks that define the system
srcp = Source(lambda t: vcm+(vd/2)*np.cos(2*np.pi*(M/N)*f_clk*t))
srcn = Source(lambda t: vcm-(vd/2)*np.cos(2*np.pi*(M/N)*f_clk*t))
samp_enable = Source(lambda t: 1)
voff = Source(lambda t: 0)
crsar = CRSAR(n_bits=n, vref=1.0, T=T_clk, tau=0, 
              weights=weights_actual, estimated_weights=weights_estimated,
             settling_error_pct=se, comp_noise_rms=cn)
sub = Adder('+-')
scope = Scope(sampling_period=(T_clk)/(OVERSAMPLING_RATIO*ndecisions), labels=['vout', 'vindiff', 'done', 'dout'])

# Connections between the blocks
connections = [
    Connection(crsar[6], sub[0]),
    Connection(crsar[7], sub[1]),
    Connection(srcp, crsar[0]),
    Connection(srcn, crsar[1]),
    Connection(voff, crsar[2]),
    Connection(voff, crsar[3]),
    Connection(samp_enable, crsar[4]),
    Connection(crsar[0], scope[0]),
    Connection(sub, scope[1]),
    Connection(crsar[2], scope[2]),
    Connection(crsar[1], scope[3])
]

blocks = [srcp, srcn, crsar, sub, scope, voff, samp_enable]

# Simulation with adaptive solver
Sim = Simulation(
    blocks,
    connections,
    Solver=RKBS32
)

Sim.run((N+STARTUP_CYCLES)*T_clk)

scope.save(output_path)
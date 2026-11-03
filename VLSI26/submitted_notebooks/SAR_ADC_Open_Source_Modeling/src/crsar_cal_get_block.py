import numpy as np
from pathsim.blocks.sources import Source
from pathsim.blocks.scope import Scope  
from pathsim.blocks.adder import Adder
from pathsim.blocks.amplifier import Amplifier
from pathsim.connection import Connection
from pathsim.simulation import Simulation
from pathsim.solvers import RKBS32
from crsar import CRSAR, CRSARCtrlODC
import argparse

parser = argparse.ArgumentParser(description="FIXME")

parser.add_argument("-c", type=str, required=True, help="Config file path")

args = parser.parse_args()

path_to_config_file = args.c

try:
    import tomllib
except ImportError:
    import tomli as tomllib

with open(path_to_config_file, "rb") as _f:
    _cfg = tomllib.load(_f)

# SAR config
vref    = _cfg["sar"]["vref"]
n       = _cfg["sar"]["n"]
f_clk   = _cfg["sar"]["f_clk"]
T_clk   = 1.0 / f_clk
sar_tau = _cfg["sar"]["sar_tau"]

# comparator parameters
comp_noise_rms = _cfg["comparator"]["noise_rms"]
comp_offset    = _cfg["comparator"]["offset"]

# CDAC parameters — values may be inline arrays or paths to .npy binary files
def _load_array(val):
    if isinstance(val, str):
        return np.load(val)
    return np.array(val)

def _load_scalar(val):
    if isinstance(val, str):
        return float(np.load(val))
    return float(val)

estimated_weights = _load_array(_cfg["weights"]["estimated"])
actual_weights    = _load_array(_cfg["weights"]["actual"])

# Digital offset parameters — actual offset drives the ODC analog injection
actual_offset_lsb    = _load_scalar(_cfg["offset"]["actual"])
estimated_offset_lsb = _load_scalar(_cfg["offset"]["estimated"])
analog_offset_volts  = (2*vref / 2**n) * actual_offset_lsb

# simulation config
N                      = _cfg["simulation"]["n_fft"]
M                      = _cfg["simulation"]["m_freq"]
STARTUP_CYCLES         = _cfg["simulation"]["startup_cycles"]
SCOPE_OVERSAMPLING_RATIO = _cfg["simulation"]["scope_oversampling_ratio"]
OUTPUT_PATH = _cfg["simulation"]["output_path"]

# adc input source
vincm = _cfg["input"]["vincm"]
vid   = _cfg["input"]["vid"]

f_sample = f_clk / 2

srcp = Source(lambda t: vincm+(vid/2)*np.cos(2*np.pi*(M/N)*f_sample*t))
srcn = Source(lambda t: vincm-(vid/2)*np.cos(2*np.pi*(M/N)*f_sample*t))

crsar = CRSAR(n_bits=n, weights=actual_weights, vref=vref, T=T_clk, tau=sar_tau, 
              estimated_weights=estimated_weights, comp_noise_rms=comp_noise_rms, comp_offset=comp_offset, 
              total_sampling_cap=0, settling_error_pct=0)

crsar_odc_ctrl = CRSARCtrlODC(analog_offset=analog_offset_volts, tau=0)

# want SAR dout, ODC dout1,2
scope = Scope(sampling_period=T_clk/SCOPE_OVERSAMPLING_RATIO, labels=[])

# Connections between the blocks
# SAR input indicies
sar_vinp_idx = crsar.input_port_labels["vinp"]
sar_vinn_idx = crsar.input_port_labels["vinn"]
sar_voffp_idx = crsar.input_port_labels["voffp"]
sar_voffn_idx = crsar.input_port_labels["voffn"]
sar_samp_en_idx = crsar.input_port_labels["samp_en"]

# used SAR output indicies
sar_dout_idx = crsar.output_port_labels["dout"]
sar_done_idx = crsar.output_port_labels["done"]
sar_dout_raw_idx = crsar.output_port_labels["dout_raw"]

# ODC Controller input indicies
odc_sar_done_idx = crsar_odc_ctrl.input_port_labels["sar_done"]
odc_sar_dout_idx = crsar_odc_ctrl.input_port_labels["sar_dout"]
odc_sar_dout_raw_idx = crsar_odc_ctrl.input_port_labels["sar_dout_raw"]

# used ODC output indicies
odc_dout_offsetp_idx = crsar_odc_ctrl.output_port_labels["odc_dout_offsetp"]
odc_dout_offsetn_idx = crsar_odc_ctrl.output_port_labels["odc_dout_offsetn"]
odc_sar_samp_en_idx = crsar_odc_ctrl.output_port_labels["sar_samp_en"]
odc_sar_vinp_offset_idx = crsar_odc_ctrl.output_port_labels["sar_vinp_offset"]
odc_sar_vinn_offset_idx = crsar_odc_ctrl.output_port_labels["sar_vinn_offset"]
odc_sar_dout_raw_offsetp_idx = crsar_odc_ctrl.output_port_labels["odc_dout_raw_offsetp"]
odc_sar_dout_raw_offsetn_idx = crsar_odc_ctrl.output_port_labels["odc_dout_raw_offsetn"]

connections = [
    # connect SAR inputs
    Connection(srcp, crsar[sar_vinp_idx]),
    Connection(srcn, crsar[sar_vinn_idx]),
    Connection(crsar_odc_ctrl[odc_sar_vinp_offset_idx], crsar[sar_voffp_idx]),
    Connection(crsar_odc_ctrl[odc_sar_vinn_offset_idx], crsar[sar_voffn_idx]),
    Connection(crsar_odc_ctrl[odc_sar_samp_en_idx], crsar[sar_samp_en_idx]),

    # connect ODC controller inputs
    Connection(crsar[sar_done_idx], crsar_odc_ctrl[odc_sar_done_idx]),
    Connection(crsar[sar_dout_idx], crsar_odc_ctrl[odc_sar_dout_idx]),
    Connection(crsar[sar_dout_raw_idx], crsar_odc_ctrl[odc_sar_dout_raw_idx]),

    # connect scope inputs
    Connection(crsar_odc_ctrl[odc_dout_offsetp_idx], scope[0]),
    Connection(crsar_odc_ctrl[odc_dout_offsetn_idx], scope[1]),
    Connection(crsar_odc_ctrl[odc_sar_samp_en_idx], scope[2]),
    Connection(crsar_odc_ctrl[odc_sar_dout_raw_offsetp_idx], scope[3]),
    Connection(crsar_odc_ctrl[odc_sar_dout_raw_offsetn_idx], scope[4])
]

blocks = [
    srcp, srcn, crsar, crsar_odc_ctrl, scope
]

# Simulation with adaptive solver
Sim = Simulation(
    blocks,
    connections,
    Solver=RKBS32
)

# sample rate effectively halved
Sim.run(2*(STARTUP_CYCLES+N+1)*T_clk)

t, dataset = scope.read()
dout_offsetp = dataset[0]
dout_offsetn = dataset[1]
samp_en = dataset[2]
dout_raw_offsetp = dataset[3]
dout_raw_offsetn = dataset[4]

# quantize all data to done transistions
transitions = np.where(np.diff(samp_en) == 1)[0] + 1

sampled_dict = {}
sampled_dict["time"] = t[transitions][STARTUP_CYCLES:STARTUP_CYCLES+N]
sampled_dict["dout_offsetp"] = dout_offsetp[transitions][STARTUP_CYCLES:STARTUP_CYCLES+N]
sampled_dict["dout_offsetn"] = dout_offsetn[transitions][STARTUP_CYCLES:STARTUP_CYCLES+N]
sampled_dict["dout_raw_offsetp"] = dout_raw_offsetp[transitions][STARTUP_CYCLES:STARTUP_CYCLES+N]
sampled_dict["dout_raw_offsetn"] = dout_raw_offsetn[transitions][STARTUP_CYCLES:STARTUP_CYCLES+N]

np.savez(OUTPUT_PATH, **sampled_dict)
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import argparse

try:
    import tomllib
except ImportError:
    import tomli as tomllib

def ints_to_bits(arr: np.ndarray, width: int) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.uint64)
    
    # Create bit positions (MSB → LSB)
    shifts = np.arange(width - 1, -1, -1, dtype=np.uint64)
    
    # Broadcast and extract bits
    bits = ((arr[:, None] >> shifts) & 1).astype(np.uint8)
    return bits

def estimate_conv_result(weights, decisions, n_bits):
    result = np.zeros(decisions.shape[0])
    for i in range(0, len(weights)):
        result += weights[i] * (2 * decisions[:, i].astype('float') - 1)

    return np.floor(0.5*(result + 1) * (2 ** n_bits))

def _load_array(val):
    if isinstance(val, str):
        return np.load(val)
    return np.array(val)

def _load_scalar(val):
    if isinstance(val, str):
        return float(np.load(val))
    return float(val)

parser = argparse.ArgumentParser(description="Trains ADC Weights/ODC Offset Voltage from static data file using ODC LMS Update Equations")

parser.add_argument("-c", type=str, required=True, help="Config file path")
parser.add_argument("-d", type=str, required=True, help="Path to data file")
parser.add_argument("-o", type=str, required=True, help="Path to output NPZ file")
parser.add_argument("-mw", type=float, required=False, default=1e-4, help="Learning rate for weights")
parser.add_argument("-mo", type=float, required=False, default=1e-3, help="Learning rate for ODC offset")
parser.add_argument("-nb", type=int, required=False, default=int(1e4), help="Number of LMS Blocks")

args = parser.parse_args()

config_file_path = args.c
data_file_path = args.d
output_file_path = args.o
mu_w = args.mw
mu_offset = args.mo
NUM_ITERATIONS = args.nb

with open(config_file_path, "rb") as _f:
    _cfg = tomllib.load(_f)

estimated_offset_lsb = _load_scalar(_cfg["offset"]["estimated"])
estimated_weights = _load_array(_cfg["weights"]["estimated"])
actual_offset_lsb = _load_scalar(_cfg["offset"]["actual"])
actual_weights = _load_array(_cfg["weights"]["actual"])
signal_freq_m = _cfg["simulation"]["m_freq"]
npoints = _cfg["simulation"]["n_fft"]
n_bits = _cfg["sar"]["n"]
f_clk   = _cfg["sar"]["f_clk"]

data_dict = np.load(data_file_path)
ndecisions = len(estimated_weights)
current_digital_offset_lsb = estimated_offset_lsb
current_weights = estimated_weights

raw_p_bits = ints_to_bits(data_dict['dout_raw_offsetp'], width=ndecisions)
raw_n_bits = ints_to_bits(data_dict['dout_raw_offsetn'], width=ndecisions)

# exit if error already minimized
mse_min = 1e-15

# fft parameters
window = 'boxcar'
nfft = npoints
nperseg = npoints
scaling = 'spectrum'
fs = f_clk/2

sfdr_arr = []
for i in range(NUM_ITERATIONS):
    # compute doutp based on current weights
    dout_offsetp = estimate_conv_result(current_weights, raw_p_bits, n_bits)
    dout_offsetn = estimate_conv_result(current_weights, raw_n_bits, n_bits)

    conv_error = dout_offsetp - dout_offsetn - 2*current_digital_offset_lsb

    bit_error = raw_p_bits.astype('float') - raw_n_bits.astype('float')
    grad_w = np.mean(conv_error[:, None] * bit_error, axis=0)
    grad_offset = np.mean(conv_error)

    current_weights -= mu_w * grad_w
    current_digital_offset_lsb += mu_offset * grad_offset

    mse_weights = np.mean((current_weights-actual_weights)**2)
    mse_offset = (current_digital_offset_lsb - actual_offset_lsb)**2

    if (mse_weights < mse_min and mse_offset < mse_min):
        break

    # calculate SFDR and SNDR
    # estimate based on current weights
    dout_offsetp_cal = estimate_conv_result(current_weights, raw_p_bits, n_bits).astype('float')
    dout_offsetn_cal = estimate_conv_result(current_weights, raw_p_bits, n_bits).astype('float')
    conv_result_cal = dout_offsetp_cal*0.5 + dout_offsetn_cal*0.5

    f, csd_cal = signal.csd(conv_result_cal, conv_result_cal, fs=fs, 
                    window=window, nperseg=nperseg, nfft=nfft,
                    scaling=scaling)

    fft_freq = f[1:]
    fft_cal = np.sqrt(np.abs(csd_cal))[1:] + 1e-25
    fft_cal *= np.sqrt(2) / (2**(n_bits-1)) 

    fft_signal_bin = signal_freq_m - 1    

    sfdr_cal = fft_cal[fft_signal_bin] / np.max(np.delete(fft_cal, fft_signal_bin))

    sfdr_arr.append(sfdr_cal)

dout_offsetp = np.array(data_dict["dout_offsetp"]).astype('float')
dout_offsetn = np.array(data_dict["dout_offsetn"]).astype('float')
conv_result_original = dout_offsetp*0.5 + dout_offsetn*0.5

dout_offsetp_cal = estimate_conv_result(current_weights, raw_p_bits, n_bits).astype('float')
dout_offsetn_cal = estimate_conv_result(current_weights, raw_p_bits, n_bits).astype('float')
conv_result_cal = dout_offsetp_cal*0.5 + dout_offsetn_cal*0.5

f, csd_original = signal.csd(conv_result_original, conv_result_original, fs=fs, 
                    window=window, nperseg=nperseg, nfft=nfft,
                    scaling=scaling)

fft_original = np.sqrt(np.abs(csd_original))[1:] + 1e-25
fft_original *= np.sqrt(2) / (2**(n_bits-1)) 
sfdr_original = fft_original[fft_signal_bin] / np.max(np.delete(fft_original, fft_signal_bin))

f, csd_cal = signal.csd(conv_result_cal, conv_result_cal, fs=fs, 
                    window=window, nperseg=nperseg, nfft=nfft,
                    scaling=scaling)

fft_freq = f[1:]
fft_cal = np.sqrt(np.abs(csd_cal))[1:] + 1e-25
fft_cal *= np.sqrt(2) / (2**(n_bits-1)) 
sfdr_cal = fft_cal[fft_signal_bin] / np.max(np.delete(fft_cal, fft_signal_bin))

results_dict = {}

results_dict["sfdr_calibrated"] = sfdr_cal
results_dict["sfdr_original"] = sfdr_original
results_dict["sfdr_learning_curve"] = sfdr_arr
results_dict["fft_freq"] = fft_freq
results_dict["fft_original"] = fft_original
results_dict["fft_calibrated"] = fft_cal

np.savez(output_file_path, **results_dict)
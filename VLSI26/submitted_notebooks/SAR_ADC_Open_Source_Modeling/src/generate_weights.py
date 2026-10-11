import numpy as np
import argparse

parser = argparse.ArgumentParser(description="CDAC Weight Generation")

parser.add_argument("-n", type=int, required=True, help="ADC resolution")
parser.add_argument("-r", type=float, required=True, help="CDAC Radix")
parser.add_argument("-u", type=float, required=True, help="Unit Capacitor Value")
parser.add_argument("-s", type=float, required=True, help="Unit Capacitor Sigma")
parser.add_argument("-o", type=str, required=True, help="Output file path")
args = parser.parse_args()

rng = np.random.default_rng(seed=1)

seed = 1
N = args.n
base = args.r
c_unit = args.u
c_unit_sigma = args.s
exponents = np.arange(N - 1, -1, -1)
c_array = c_unit * (base ** exponents)
c_array_sigma = c_unit_sigma * np.sqrt((base ** exponents)) # assume pelgrom mismatch

# weights_estimated: based on ideal CDAC levels with no mismatch
# for radix 2, assume termination cap = unit cap, otherwise assume no termination
if base == 2:
    weights_estimated = c_array / (np.sum(c_array) + c_unit)
else:
    weights_estimated = c_array / (np.sum(c_array))

# weights_actual: same but each weight perturbed by Gaussian noise
noise = rng.normal(0, c_array_sigma)
termination_cap = c_unit + rng.normal(0, c_unit_sigma)
c_array_actual = c_array + noise

if base == 2:
    weights_actual = c_array_actual / (np.sum(c_array_actual) + termination_cap)
else:
    weights_actual = c_array_actual / (np.sum(c_array_actual))

base_str = f"{base:.2f}".replace('.', '_')

if c_unit_sigma > 0:
    np.save(f"{args.o}/weights_estimated_{N}b_radix{base_str}.npy", weights_estimated)
    np.save(f"{args.o}/weights_actual_{N}b_radix{base_str}.npy", weights_actual)

else:
    np.save(f"{args.o}/weights_actual_{N}b_radix{base_str}.npy", weights_estimated)
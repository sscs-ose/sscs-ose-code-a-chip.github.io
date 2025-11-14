from pygmid import Lookup as lk
import numpy as np
import scipy.constants as sc

# Load lookup tables from local folder (same directory)
n = lk('nfet_03v3.mat')
p = lk('pfet_03v3.mat')

# Print available VGS and L ranges
print("VGS range:", min(n['VGS']), "to", max(n['VGS']))
print("L range:", min(n['L']), "to", max(n['L']))
print("")
# ===== Mode 1: Simple lookup =====
gm_n = n.lookup('GM', L=0.28, VGS=1, VDS=1.65, VSB=0)
gm_p = p.lookup('GM', L=0.28, VGS=1, VDS=1.65, VSB=0)
print("GM (nmos):", gm_n/1e-3, "mS")
print("GM (pmos):", gm_p/1e-3, "mS")
print("")
# Default values
gm_n_def = n.lookup('GM', VGS=1)
gm_p_def = p.lookup('GM', VGS=1)
print("GM default (nmos):", gm_n_def/1e-3, "mS")
print("GM default (pmos):", gm_p_def/1e-3, "mS")
print("")
# Threshold voltage
vt_n = n.lookup('VT', VGS=1)
vt_p = p.lookup('VT', VGS=1)
print("VT (nmos):", vt_n)
print("VT (pmos):", vt_p)
print("")
# ===== Mode 2: gm/id and ID/W =====
gm_id_n = n.lookup('GM_ID', VGS=0.8)
gm_id_p = p.lookup('GM_ID', VGS=0.8)
print("GM/ID (nmos):", gm_id_n)
print("GM/ID (pmos):", gm_id_p)
print("")
jd_n = n.lookup('ID_W', VGS=0.8)
jd_p = p.lookup('ID_W', VGS=0.8)
print("ID/W (nmos):", jd_n, "A/um")
print("ID/W (pmos):", jd_p, "A/um")
print("")
# ===== Mode 3: gm/cgg vs gm/id =====
gm_cgg_n = n.lookup('GM_CGG', GM_ID=10)
gm_cgg_p = p.lookup('GM_CGG', GM_ID=10)
print("fT (nmos):", gm_cgg_n / (2 * np.pi * 1e9), "GHz")
print("fT (pmos):", gm_cgg_p / (2 * np.pi * 1e9), "GHz")
print("")
# ===== Noise =====
gamma_n = n.lookup('STH', VGS=1) / (4 * sc.Boltzmann * 300 * n.lookup('GM', VGS=1))
gamma_p = p.lookup('STH', VGS=1) / (4 * sc.Boltzmann * 300 * p.lookup('GM', VGS=1))
print("Gamma (nmos):", gamma_n)
print("Gamma (pmos):", gamma_p)
print("")
sfl_gate_n = n.lookup('SFL_GM', VGS=1)
sfl_gate_p = p.lookup('SFL_GM', VGS=1)
print("SFL (nmos):", sfl_gate_n)
print("SFL (pmos):", sfl_gate_p)

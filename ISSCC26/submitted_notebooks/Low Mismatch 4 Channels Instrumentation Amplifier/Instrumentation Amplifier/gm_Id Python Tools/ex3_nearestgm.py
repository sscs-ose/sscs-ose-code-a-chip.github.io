from pygmid import Lookup as lk
import numpy as np
import pandas as pd
from tabulate import tabulate

# Load lookup table
n = lk('pfet_03v3.mat')

# Spesifikasi
L = 3
ID_target = 151.5e-6  # Ampere

# Sweep ID manual
id_range = np.linspace(0.1e-6, 1e-3, 1000)

# Ambil GM dan VT
data = []
for id_val in id_range:
    try:
        gm_val = n.lookup('GM', ID=id_val, L=L)
        vt_val = n.lookup('VT', ID=id_val, L=L)
        if np.isnan(gm_val) or np.isnan(vt_val):
            continue
        selisih = abs(id_val - ID_target)
        # 👇 pastikan semua float!
        data.append((float(id_val), float(gm_val), float(vt_val), float(selisih)))
    except:
        continue

# Buat DataFrame dan cari nilai GM & VT terdekat
df = pd.DataFrame(data, columns=['ID', 'GM', 'VT', 'selisih'])
terdekat = df.nsmallest(10, 'selisih')

# Tampilkan
print(tabulate(terdekat, headers='keys', tablefmt='grid', floatfmt=".4e"))

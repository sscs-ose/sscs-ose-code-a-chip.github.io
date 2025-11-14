from scipy.io import loadmat
import numpy as np

# Load file
matfile = loadmat("pfet_03v3.mat")

# Pilih field yang ingin ditampilkan
fields_to_show = ['W', 'NFING']

for field in fields_to_show:
    # Cari field di dalam struktur .mat
    found = False
    for key in matfile:
        if not key.startswith("__"):
            data = matfile[key]
            if isinstance(data, np.ndarray):
                try:
                    if field in data.dtype.names:
                        value = data[field][0][0]
                        print(f"\nField: {field}")
                        print(f"Shape: {value.shape if hasattr(value, 'shape') else '(scalar)'}")
                        # Handle if scalar
                        if np.isscalar(value):
                            print(f"First 10 values: [{value}]")
                        else:
                            print(f"First 10 values: {value[:10]}")
                        found = True
                        break
                except Exception:
                    pass
    if not found:
        print(f"\nField '{field}' not found.")

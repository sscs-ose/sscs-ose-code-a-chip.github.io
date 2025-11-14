# Input target kapasitansi dan densitas
C_target_pF = 3.454       # Target kapasitansi dalam pF
density_fF_per_um2 = 2     # Densitas dalam fF/µm^2

# Konversi pF ke fF
C_target_fF = C_target_pF * 1e3

# Hitung luas area yang dibutuhkan
area_um2 = C_target_fF / density_fF_per_um2

# bentuk bujur sangkar (default)
side_um = area_um2 ** 0.5

print(f"Luas: {area_um2:.2f} µm²")
print(f"W or L: {side_um:.2f} µm")
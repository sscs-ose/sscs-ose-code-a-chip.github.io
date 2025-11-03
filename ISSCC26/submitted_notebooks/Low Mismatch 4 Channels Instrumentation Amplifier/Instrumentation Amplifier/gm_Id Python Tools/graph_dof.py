import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# === 1. Load data from CSV file ===
df = pd.read_csv('nfet_03v3_full_table.csv')  # Change to your filename

# === 2. Smart column identification ===
def find_col(df, patterns):
    for col in df.columns:
        for pattern in patterns:
            if pattern.lower() in col.lower():
                return col
    return None

vgs_col = find_col(df, ['vgs', 'gate-source', 'vg'])
vds_col = find_col(df, ['vds', 'drain-source', 'vd'])
l_col = find_col(df, ['l', 'length', 'channel length'])
id_col = find_col(df, ['id', 'drain current', 'current'])
gm_col = find_col(df, ['gm', 'transconductance'])

# Verify columns
if None in [vgs_col, vds_col, l_col, id_col, gm_col]:
    print("ERROR: Could not identify all required columns")
    print("Please manually specify column names")
    print("Available columns:", df.columns.tolist())
    exit()

# === 3. Filter data for L = 3 μm ===
target_L = 3.0  # μm
tolerance = 0.01  # Tolerance for floating point comparison

# Create mask for L ≈ 3μm
L_mask = np.abs(df[l_col] - target_L) < tolerance
filtered_df = df[L_mask]

if len(filtered_df) == 0:
    unique_L = df[l_col].unique()
    closest_L = unique_L[np.argmin(np.abs(unique_L - target_L))]
    print(f"No data for L=3μm, using closest: {closest_L}μm")
    L_mask = np.abs(df[l_col] - closest_L) < tolerance
    filtered_df = df[L_mask]
    target_L = closest_L  # Update target for plots

# Extract data
vgs = filtered_df[vgs_col].values
ids = filtered_df[id_col].values
gm = filtered_df[gm_col].values
gm_id = gm / ids

# === 4. Create separate figures for each plot ===
plt.rcParams.update({'font.size': 12, 'figure.figsize': (10, 7)})

# Figure 1: Id vs VGS
plt.figure(1)
plt.semilogy(vgs, np.abs(ids), 'b-', linewidth=2)
plt.xlabel('VGS (V)', fontsize=14)
plt.ylabel('Drain Current (A)', fontsize=14)
plt.title(f'Drain Current vs Gate-Source Voltage (L={target_L}μm)', fontsize=16)
plt.grid(True, which="both", ls="--", alpha=0.7)
plt.tight_layout()

# Figure 2: gm/Id vs VGS
plt.figure(2)
plt.plot(vgs, gm_id, 'r-', linewidth=2)
plt.xlabel('VGS (V)', fontsize=14)
plt.ylabel('gm/Id (S/A)', fontsize=14)
plt.title(f'Transconductance Efficiency vs Gate-Source Voltage (L={target_L}μm)', fontsize=16)
plt.grid(True, ls="--", alpha=0.7)
plt.tight_layout()

# Figure 3: Id vs gm/Id
plt.figure(3)
plt.semilogy(gm_id, np.abs(ids), 'g-', linewidth=2)
plt.xlabel('gm/Id (S/A)', fontsize=14)
plt.ylabel('Drain Current (A)', fontsize=14)
plt.title(f'Drain Current vs Transconductance Efficiency (L={target_L}μm)', fontsize=16)
plt.grid(True, which="both", ls="--", alpha=0.7)
plt.tight_layout()

# Figure 4: Combined plot (ID and gm/Id vs VGS)
plt.figure(4)
fig, ax1 = plt.subplots(figsize=(10, 7))
ax1.semilogy(vgs, np.abs(ids), 'b-', linewidth=2, label='ID')
ax1.set_xlabel('VGS (V)', fontsize=14)
ax1.set_ylabel('Drain Current (A)', color='b', fontsize=14)
ax1.tick_params(axis='y', labelcolor='b')
ax1.grid(True, which="both", ls="--", alpha=0.7)

ax2 = ax1.twinx()
ax2.plot(vgs, gm_id, 'r-', linewidth=2, label='gm/Id')
ax2.set_ylabel('gm/Id (S/A)', color='r', fontsize=14)
ax2.tick_params(axis='y', labelcolor='r')

plt.title(f'Current and Efficiency vs Gate Voltage (L={target_L}μm)', fontsize=16)
fig.tight_layout()

# === 5. Show all plots ===
plt.show()

# === 6. Summary statistics ===
print(f"\n{' Summary ':=^60}")
print(f"Device: PFET (L = {target_L}μm)")
print(f"Data points: {len(filtered_df)}")
print(f"VGS range: {np.min(vgs):.2f}V to {np.max(vgs):.2f}V")
print(f"ID range: {np.min(np.abs(ids)):.2e}A to {np.max(np.abs(ids)):.2e}A")
print(f"gm/Id range: {np.min(gm_id):.2f}S/A to {np.max(gm_id):.2f}S/A")
print(f"gm range: {np.min(gm):.2e}S to {np.max(gm):.2e}S")
print("="*60)
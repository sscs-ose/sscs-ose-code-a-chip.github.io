import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# File input dan output
input_csv = "nmos1_gm.csv"
output_csv = "nmos1_gm_id.csv"

try:
    # Baca file CSV yang sudah ada
    df = pd.read_csv(input_csv)
    
    # Hitung gm/Id (dalam satuan V⁻¹)
    # Gunakan nilai absolut untuk menghindari pembagian dengan nilai negatif mendekati nol
    df['gm/Id (V⁻¹)'] = np.abs(df['gm (A/V)']) / np.abs(df['Id (A)'])
    
    # Simpan ke file CSV baru
    df.to_csv(output_csv, index=False)
    
    print(f"File baru berhasil dibuat: {output_csv}")
    print("Kolom yang tersedia:", df.columns.tolist())
    #print("\n5 data pertama:")
    #print(df.head())
    
    # Analisis data
    max_gm_id = df['gm/Id (V⁻¹)'].max()
    min_gm_id = df['gm/Id (V⁻¹)'].min()
    vgs_max = df.loc[df['gm/Id (V⁻¹)'].idxmax(), 'Vgs (V)']
    vgs_min = df.loc[df['gm/Id (V⁻¹)'].idxmin(), 'Vgs (V)']
    
    print(f"\nEfisiensi maksimum (gm/Id): {max_gm_id:.2f} V⁻¹ pada Vgs = {vgs_max:.1f}V")
    print(f"Efisiensi minimum (gm/Id): {min_gm_id:.2f} V⁻¹ pada Vgs = {vgs_min:.1f}V")
    
    # Identifikasi region operasi
    print("\nRegion operasi berdasarkan gm/Id:")
    print(f"- Subthreshold (gm/Id > 20): Vgs < {df[df['gm/Id (V⁻¹)'] > 20]['Vgs (V)'].max():.1f}V")
    print(f"- Moderate inversion (10-20): Vgs = {df[(df['gm/Id (V⁻¹)'] >= 10) & (df['gm/Id (V⁻¹)'] <= 20)]['Vgs (V)'].min():.1f}-{df[(df['gm/Id (V⁻¹)'] >= 10) & (df['gm/Id (V⁻¹)'] <= 20)]['Vgs (V)'].max():.1f}V")
    print(f"- Strong inversion (gm/Id < 10): Vgs > {df[df['gm/Id (V⁻¹)'] < 10]['Vgs (V)'].min():.1f}V")
    
    # ======================================
    # Membuat plot karakteristik transistor
    # ======================================
    plt.figure(figsize=(15, 12))
    
    # Plot 1: Transfer characteristic (Id vs Vgs)
    plt.subplot(3, 2, 1)
    plt.semilogy(df['Vgs (V)'], np.abs(df['Id (A)']), 'bo-', linewidth=2)
    plt.xlabel('Vgs (V)')
    plt.ylabel('Id (A)')
    plt.title('Transfer Characteristic')
    plt.grid(True, which="both", ls="--")
    plt.axvline(x=vgs_max, color='r', linestyle='--', alpha=0.5, label='Max gm/Id')
    plt.axvline(x=vgs_min, color='g', linestyle='--', alpha=0.5, label='Min gm/Id')
    plt.legend()
    
    # Plot 2: gm vs Vgs
    plt.subplot(3, 2, 2)
    plt.plot(df['Vgs (V)'], df['gm (A/V)']*1e6, 'ro-', linewidth=2)
    plt.xlabel('Vgs (V)')
    plt.ylabel('gm (μS)')
    plt.title('Transconductance')
    plt.grid(True)
    plt.axvline(x=vgs_max, color='r', linestyle='--', alpha=0.5)
    plt.axvline(x=vgs_min, color='g', linestyle='--', alpha=0.5)
    
    # Plot 3: gm/Id vs Vgs
    plt.subplot(3, 2, 3)
    plt.plot(df['Vgs (V)'], df['gm/Id (V⁻¹)'], 'go-', linewidth=2)
    plt.xlabel('Vgs (V)')
    plt.ylabel('gm/Id (V⁻¹)')
    plt.title('Transconductance Efficiency')
    plt.grid(True)
    plt.axhline(y=20, color='b', linestyle='--', alpha=0.5, label='Subthreshold')
    plt.axhline(y=10, color='m', linestyle='--', alpha=0.5, label='Moderate Inversion')
    plt.legend()
    
    # Plot 4: gm/Id vs Id (log scale)
    plt.subplot(3, 2, 4)
    plt.semilogx(np.abs(df['Id (A)']), df['gm/Id (V⁻¹)'], 'mo-', linewidth=2)
    plt.xlabel('Drain Current (A) - Log Scale')
    plt.ylabel('gm/Id (V⁻¹)')
    plt.title('Efficiency vs Drain Current')
    plt.grid(True, which="both", ls="--", alpha=0.7)
    
    # Plot 5: gm vs Id (log scale)
    plt.subplot(3, 2, 5)
    plt.loglog(np.abs(df['Id (A)']), np.abs(df['gm (A/V)']), 'co-', linewidth=2)
    plt.xlabel('Drain Current (A)')
    plt.ylabel('gm (S)')
    plt.title('Transconductance vs Drain Current')
    plt.grid(True, which="both", ls="--")
    
    # Plot 6: Derivative of gm (d(gm)/dVgs)
    plt.subplot(3, 2, 6)
    dgm_dvgs = np.gradient(df['gm (A/V)'], df['Vgs (V)'])
    plt.plot(df['Vgs (V)'], dgm_dvgs*1e6, 'ko-', linewidth=2)
    plt.xlabel('Vgs (V)')
    plt.ylabel('d(gm)/dVgs (μS/V)')
    plt.title('Transconductance Derivative')
    plt.grid(True)
    
    # Atur layout dan simpan
    plt.tight_layout()
    plt.savefig('nmos_characteristics.png', dpi=300)
    print("\nPlot karakteristik disimpan sebagai 'nmos_characteristics.png'")
    
    # Tampilkan plot
    plt.show()
    
    # ======================================
    # Plot tambahan: Karakteristik di region penting
    # ======================================
    plt.figure(figsize=(12, 8))
    
    # Subthreshold region
    plt.subplot(2, 2, 1)
    sub_df = df[df['Vgs (V)'] < 0.9]
    plt.semilogy(sub_df['Vgs (V)'], np.abs(sub_df['Id (A)']), 'bo-', linewidth=2)
    plt.xlabel('Vgs (V)')
    plt.ylabel('Id (A)')
    plt.title('Subthreshold Region')
    plt.grid(True, which="both", ls="--")
    
    # Moderate inversion
    plt.subplot(2, 2, 2)
    mod_df = df[(df['Vgs (V)'] >= 0.6) & (df['Vgs (V)'] <= 1.2)]
    plt.plot(mod_df['Vgs (V)'], mod_df['gm/Id (V⁻¹)'], 'go-', linewidth=2)
    plt.xlabel('Vgs (V)')
    plt.ylabel('gm/Id (V⁻¹)')
    plt.title('Moderate Inversion Region')
    plt.grid(True)
    
    # Strong inversion - Id vs Vgs
    plt.subplot(2, 2, 3)
    strong_df = df[df['Vgs (V)'] > 0.9]
    plt.plot(strong_df['Vgs (V)'], np.abs(strong_df['Id (A)']), 'ro-', linewidth=2)
    plt.xlabel('Vgs (V)')
    plt.ylabel('Id (A)')
    plt.title('Strong Inversion Region (Linear Scale)')
    plt.grid(True)
    
    # Strong inversion - gm vs Vgs
    plt.subplot(2, 2, 4)
    plt.plot(strong_df['Vgs (V)'], strong_df['gm (A/V)']*1e6, 'mo-', linewidth=2)
    plt.xlabel('Vgs (V)')
    plt.ylabel('gm (μS)')
    plt.title('Strong Inversion Transconductance')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('nmos_regions.png', dpi=300)
    print("Plot region operasi disimpan sebagai 'nmos_regions.png'")
    plt.show()

except FileNotFoundError:
    print(f"Error: File '{input_csv}' tidak ditemukan")
except Exception as e:
    print(f"Terjadi kesalahan: {str(e)}")
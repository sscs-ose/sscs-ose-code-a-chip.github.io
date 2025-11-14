# CODE FOR MAKING/UPDATING .csv from .raw generated from Xschem
# Functionality : Read your .raw file containing simulation sampling points
# Note* belum include sama konsiderasi zise (W/L)
# .raw file harus Id vs Vgs

import numpy as np

# Fungsi parse file, determina mana value yang perlu dimasukkin ke .csv
def parse_ngspice_raw(raw_text):
    lines = raw_text.strip().split('\n')
    data = []
    in_values = False
    point_counter = 0
    current_vgs = 0
    read_lines = 0
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Start reading after "Values:" section
        # Skip the title, variable name, etc
        if line.startswith("Values:"):
            in_values = True
            continue
        if not in_values: # Bukan values
            continue
            
        # Point header line (e.g., "0 0.000000...")
        if line.split()[0].isdigit():
            parts = line.split()
            point_counter = int(parts[0])
            current_vgs = float(parts[1])
            read_lines = 0
            continue
            
        # Data lines (4 lines per point)
        read_lines += 1
        
        # Third line after header is i(v1) (drain current)
        if read_lines == 3:
            try:
                i_v1 = float(line.split()[0])
                id_current = -i_v1  # Drain current = -i(v1)
                data.append((current_vgs, id_current))
            except (ValueError, IndexError):
                continue
    
    return np.array(data)

# Rumus/Fungsi perhitungan parameter gm
# gm = dId/dVgs (gradien)
# data .raw berisi sampling point terhadap Id (y) vs Vgs (x)
def calculate_gm(vgs, id_current):
    if len(vgs) < 2:
        raise ValueError("Insufficient data points (less than 2)")
    gm = np.zeros_like(vgs)
    # Forward difference for first point
    gm[0] = (id_current[1] - id_current[0]) / (vgs[1] - vgs[0])
    # Central difference for middle points
    for i in range(1, len(vgs)-1):
        gm[i] = (id_current[i+1] - id_current[i-1]) / (vgs[i+1] - vgs[i-1])
    # Backward difference for last point
    gm[-1] = (id_current[-1] - id_current[-2]) / (vgs[-1] - vgs[-2])
    return gm 
    # gm akan bervariasi berdasarkan titik pemilihan 

# Main program
if __name__ == "__main__":
    # Read directly from .raw file
    input_filename = "nmos1.raw"
    output_filename = "nmos1_gm.csv"
    # Mechanisme of reading file (biasa)
    try:
        # Read raw file
        with open(input_filename, 'r') as f:
            raw_data = f.read()
        # Process data
        data = parse_ngspice_raw(raw_data)
        if len(data) == 0: # Data NULL
            print("Error: No data extracted from .raw file")
        else:
            vgs = data[:, 0]
            id_current = data[:, 1]
            
            # Calculate transconductance
            try:
                gm = calculate_gm(vgs, id_current)
                # Save to CSV file
                with open(output_filename, 'w') as f:
                    f.write("Vgs (V),Id (A),gm (A/V)\n")
                    for i in range(len(vgs)):
                        f.write(f"{vgs[i]:.1f},{id_current[i]:.6e},{abs(gm[i]):.6e}\n")
                print(f"CSV File baru (generated): {output_filename}")
                print(f"Jumlah data ref point: {len(vgs)}")
                # Print sample data (tulis datanya)
                print("\nSample data:")
                print(f"Vgs = {vgs[0]:.1f} V, Id = {id_current[0]:.2e} A, gm = {abs(gm[0]):.2e} S")
                print(f"Vgs = {vgs[-1]:.1f} V, Id = {id_current[-1]:.2e} A, gm = {abs(gm[-1]):.2e} S")
            # Pembatasan, perhitungan gm salah
            except ValueError as e:
                print(f"Error calculating gm: {e}")
    # Pembatasan input, file salah
    except FileNotFoundError:
        print(f"Error: File '{input_filename}' tidak ditemukan")
    except Exception as e:
        print(f"Terjadi kesalahan: {str(e)}")
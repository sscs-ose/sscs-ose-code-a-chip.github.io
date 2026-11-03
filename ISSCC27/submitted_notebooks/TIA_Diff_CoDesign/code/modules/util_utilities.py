# -*- coding: utf-8 -*-

import os, tempfile, platform, sys


# ============================== filename and path  =================================

def get_script_path(filename):
    # Define paths and directories
    script_path = os.path.normcase(os.path.dirname(filename))
    return script_path

def get_basename (filename):
    # get file basename without .gds or .py extension
    basename = os.path.basename(filename).replace('.gds', '')
    basename = basename.replace('.py','')
    return basename

def create_sim_path (script_path, model_basename):
    # set directory for simulation output, create path if it does not exist
    base_path = os.path.join(script_path, 'output')

    # check if we might run into path length issues, leave some margin for nested subdiretories and filenames
    if platform.system() == "Windows" and len(base_path) > 200:
        print('[WARNING] Path length limitation, using temp directory for simulation data')
        base_path =  os.path.join(tempfile.gettempdir(), 'openEMS')

    # try to create data directory
    try: 
        sim_path = os.path.join(base_path, model_basename + '_data')
        if not os.path.exists(sim_path):
            os.makedirs(sim_path, exist_ok=True)
    except:
        print('[WARNING] Could not create simulation data directory ', sim_path)
        print('Now trying to use temp directory for simulation data!\n')
        base_path =  os.path.join(tempfile.gettempdir(), 'openEMS')
        sim_path = os.path.join(base_path, model_basename + '_data')

    return sim_path


def get_excitation_path (sim_path, ports):
    # get path for one specific port excitation, input is list of excited ports, because sometimes multiple ports are excited together
    portnumber = ports[0]
    ex_path = os.path.join(sim_path, 'sub-' + str(portnumber))
    if not os.path.exists(ex_path):
        os.makedirs(ex_path)
    return ex_path    

# ========================= S-parameter calculations  =============================

def calculate_Sij (i, j, f, sim_path, simulation_ports):
    # S-parameter calculation for one element of the S matrix
    try:
        excitation_path = get_excitation_path (sim_path, [j])
        
        if not os.path.exists(excitation_path):
            print('\n\n ERROR ** Excitation path ', excitation_path, ' does not exist. ')
            exit(1)

        CSX_port_i = simulation_ports.get_port_by_number(i).CSXport
        CSX_port_i.CalcPort(excitation_path, f, simulation_ports.get_port_by_number(i).port_Z0)
        if i==j:
            Sij = CSX_port_i.uf_ref  / CSX_port_i.uf_inc
        else:    
            CSX_port_j = simulation_ports.get_port_by_number(j).CSXport
            CSX_port_j.CalcPort(excitation_path, f, simulation_ports.get_port_by_number(j).port_Z0)
            Sij = CSX_port_i.uf_ref  / CSX_port_j.uf_inc

        return Sij

    except FileNotFoundError as e:
        print('[ERROR] FileNotFoundError when evaluting S',i,j,'\n', e)
        sys.exit(1)


def calculate_Yij_2port (i, j, f, sim_path, simulation_ports, symmetry=False):
    # Y parameter calculation for 2-port data, returns  one element of the Y matrix, 
    # requires all ports excitations to be simulated because we need full S matrix
    try:
        Z0 = simulation_ports.get_port_by_number(1).port_Z0
        # check if we have the same impedance at both ports
        if Z0 != simulation_ports.get_port_by_number(2).port_Z0:
            print('[ERROR] Y-parameter calculation requires same port impedance on both ports')
            sys.exit(1)

        # get S matrix elements
        s11 = calculate_Sij (1, 1, f, sim_path, simulation_ports)
        s21 = calculate_Sij (2, 1, f, sim_path, simulation_ports)
        if symmetry:
            s22 = s11
            s12 = s21
        else:    
            s12 = calculate_Sij (1, 2, f, sim_path, simulation_ports)
            s22 = calculate_Sij (2, 2, f, sim_path, simulation_ports)        
    
        Y0 = 1/Z0

        if (i==1) and (j==1):
            # Y11
            return Y0*((1-s11)*(1+s22)+s12*s21)/((1+s11)*(1+s22)-s12*s21)
        elif (i==1) and (j==2):    
            # Y12
            return Y0*(-2*s12)/((1+s11)*(1+s22)-s12*s21)
        elif (i==2) and (j==1):    
            # Y21
            return Y0*(-2*s21)/((1+s11)*(1+s22)-s12*s21)
        elif (i==2) and (j==2):    
            # Y22
            return Y0*((1+s11)*(1-s22)+s12*s21)/((1+s11)*(1+s22)-s12*s21)
        else:
            print('[ERROR] Invalid parameter requested: Y',i,j)
            sys.exit(1)            


    except:
        print('[ERROR] Error in Y-parameter calculation')
        sys.exit(1)


        
def calculate_Zij_2port (i, j, f, sim_path, simulation_ports, symmetry=False):
    # Z parameter calculation for 2-port data, returns  one element of the Z matrix, 
    # requires all ports excitations to be simulated because we need full S matrix
    try:
        Z0 = simulation_ports.get_port_by_number(1).port_Z0

        # check if we have the same impedance at both ports
        if Z0 != simulation_ports.get_port_by_number(2).port_Z0:
            print('[ERROR] Z-parameter calculation requires same port impedance on both ports')
            sys.exit(1)

        # get S matrix elements
        s11 = calculate_Sij (1, 1, f, sim_path, simulation_ports)
        s21 = calculate_Sij (2, 1, f, sim_path, simulation_ports)
        if symmetry:
            s22 = s11
            s12 = s21
        else:    
            s12 = calculate_Sij (1, 2, f, sim_path, simulation_ports)
            s22 = calculate_Sij (2, 2, f, sim_path, simulation_ports)        
    
        
        if (i==1) and (j==1):
            # Z11
            return Z0*((1+s11)*(1-s22)+s12*s21)/((1-s11)*(1-s22)-s12*s21)
        elif (i==1) and (j==2):    
            # Z12
            return Z0*(2*s12)/((1-s11)*(1-s22)-s12*s21)
        elif (i==2) and (j==1):    
            # Z21
            return Z0*(2*s21)/((1-s11)*(1-s22)-s12*s21)
        elif (i==2) and (j==2):    
            # Z22
            return Z0*((1-s11)*(1+s22)+s12*s21)/((1-s11)*(1-s22)-s12*s21)
        else:
            print('[ERROR] Invalid parameter requested: Y',i,j)
            sys.exit(1)            


    except:
        print('[ERROR] Error in Y-parameter calculation')
        sys.exit(1)
        



# =========================== S-parameter output  =================================

def write_snp (Smatrix,f, filename):
    # Smatrix input must np.array[s11] or np.array[[s11,s21],[s12,s22]], more ports are also supported

    print('Creating  S-parameter file')
    matrixsize = len(Smatrix)
    numfreq = len(f)

    snp_file = open(filename, 'w')
    snp_file.write('#   Hz   S  RI   R   50\n')
    snp_file.write('!\n')

    # address elements as Sij
    for index in range(0, numfreq):
        freq = f[index]
        line = f"{freq:.6e}" 

        if matrixsize==1:
            #1-port data
            line = line + f" {Smatrix[0,index].real:.6e} {Smatrix[0,index].imag:.6e}"
        else:
            # multiport data
            for j in range(0,matrixsize):   
                for i in range(0,matrixsize):  
                    line = line + f" {Smatrix[i, j, index].real:.6e} {Smatrix[i, j, index].imag:.6e}"

        snp_file.write(line + '\n')
    snp_file.close()





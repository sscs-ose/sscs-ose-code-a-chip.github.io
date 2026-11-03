import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules')))

import modules.util_stackup_reader as stackup_reader
import modules.util_gds_reader as gds_reader
import modules.util_utilities as utilities
import modules.util_simulation_setup as simulation_setup
import modules.util_meshlines as util_meshlines

import os
import matplotlib.pyplot as plt  # pip install matplotlib
import numpy as np
from CSXCAD import ContinuousStructure
from CSXCAD import AppCSXCAD_BIN
from openEMS import openEMS
from openEMS.physical_constants import *


# Model comments
# Changes for IHP Analog Academy in 01/2026:
# Changed to MUR boundary at zmax so that radiation can be absorbed.
# From experience, using MUR can create numerical issue when it touches the lossy silicon, so it is ONLY used at zmax.
# All other boundaries use PEC, for best simulation speed.
# Distance to side walls reduced, we have not much field there because of the Metal1 ground layout.


# ======================== workflow settings ================================

# preview model/mesh only?
# postprocess existing data without re-running simulation?
preview_only = True
force_simulation=True
postprocess_only = False

# ===================== input files and path settings =======================

# GDS filename
gds_filename = "../klayout/Interconnect_base_v2.gds"
XML_filename = "SG13G2.xml"

# OBSOLETE! preprocess GDSII for safe handling of cutouts/holes?
# preprocess_gds = True

# merge polygons with distance less than xxx um, or set to 0 to disable via array merging
merge_polygon_size = 1 # Top2Via is 1.09 um apart, via2-4 0.42 um

# get path for this simulation file
script_path = utilities.get_script_path(__file__)

# use script filename as model basename
model_basename = utilities.get_basename(__file__)

# set and create directory for simulation output
sim_path = utilities.create_sim_path (script_path,model_basename)
print('Simulation data directory: ', sim_path)


# ======================== simulation settings ================================

# geometry is in microns
unit   = 1e-06   

# distance in microns from GDSII geometry boundary to simulation boundary 
margin = 20    

# Gauss impulse formation:
fstart = 0
fstop  = 350e9

# Fourier Transform - affects postprocessing only, not the FDTD itself!
numfreq = 401

# Meshing
cells_per_wavelength = 20   # how many mesh cells per wavelength, must be 10 or more
refined_cellsize = 0.5      # mesh cell size in conductor region in microns


# choices for boundary xmin,xmax,ymin,ymax,zmin,zmax: 
# 'PEC' : perfect electric conductor (default)
# 'PMC' : perfect magnetic conductor, useful for symmetries
# 'MUR' : simple MUR absorbing boundary conditions
# 'PML_8' : PML absorbing boundary conditions
Boundaries = ['PEC', 'PEC', 'PEC', 'PEC', 'PEC', 'PEC']


energy_limit = -50          # end criteria for residual energy (dB)

# ports from GDSII Data, polygon geometry from specified special layer
# note that for multiport simulation, excitations are switched on/off in simulation_setup.createSimulation below
simulation_ports = simulation_setup.all_simulation_ports()
simulation_ports.add_port(simulation_setup.simulation_port(portnumber=1, voltage=1, port_Z0=50, source_layernum=201, from_layername='Metal2', to_layername='Metal5', direction='z'))
simulation_ports.add_port(simulation_setup.simulation_port(portnumber=2, voltage=1, port_Z0=50, source_layernum=202, from_layername='Metal2', to_layername='TopMetal2', direction='z'))
simulation_ports.add_port(simulation_setup.simulation_port(portnumber=3, voltage=1, port_Z0=50, source_layernum=203, target_layername='Metal2', direction='-x'))


materials_list, dielectrics_list, metals_list = stackup_reader.read_substrate (XML_filename)
# get list of layers from technology
layernumbers = metals_list.getlayernumbers()
layernumbers.extend(simulation_ports.portlayers)

# read geometries from GDSII, only purpose 0
allpolygons = gds_reader.read_gds(gds_filename, layernumbers, purposelist=[0], metals_list=metals_list, merge_polygon_size=merge_polygon_size)


# calculate maximum cellsize from wavelength in dielectric
wavelength_air = 3e8/fstop
max_cellsize = (wavelength_air/unit)/(np.sqrt(materials_list.eps_max)*cells_per_wavelength) 


########### create model, run and post-process ###########


# Create simulation for port 1 .. 4 excitation, return value is data path for that excitation

FDTD = openEMS(EndCriteria=np.exp(energy_limit/10 * np.log(10)))
FDTD.SetGaussExcite( (fstart+fstop)/2, (fstop-fstart)/2 )
FDTD.SetBoundaryCond( Boundaries )

excite_ports_list = [[1],[2],[3]]  # list of ports that are excited in the different excitation runs
for excite_ports in excite_ports_list:
    # define excitation and stop criteria and boundaries
    FDTD = simulation_setup.setupSimulation (excite_ports, simulation_ports, FDTD, materials_list, dielectrics_list, metals_list, allpolygons, max_cellsize, refined_cellsize, margin, unit, xy_mesh_function=util_meshlines.create_xy_mesh_from_polygons)
    simulation_setup.runSimulation (excite_ports, FDTD, sim_path, model_basename, preview_only, postprocess_only, force_simulation)


if preview_only==False:

    print('Begin data evaluation')

    # Initialize an empty matrix for S-parameters
    num_ports = simulation_ports.portcount
    s_params = np.empty((num_ports, num_ports, numfreq), dtype=object)

    # Define frequency resolution (postprocessing)
    f = np.linspace(fstart, fstop, numfreq)

    # Populate the S-parameter matrix with simulation results
    for i in range(1, num_ports + 1):
        for j in range(1, num_ports + 1):
            s_params[i-1, j-1] = utilities.calculate_Sij(i, j, f, sim_path, simulation_ports)

    # Write to Touchstone *.snp file
    snp_name = os.path.join(sim_path, model_basename + '.s' + str(num_ports) + 'p')
    utilities.write_snp(s_params, f, snp_name, z0=simulation_ports.get_reference_impedance())

    print('Created S-parameter output file at ', snp_name)
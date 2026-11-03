########################################################################
#
# Copyright 2025 Volker Muehlhaus and IHP PDK Authors
#
# Licensed under the GNU General Public License, Version 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.gnu.org/licenses/gpl-3.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
########################################################################

import os

from gds2openEMS import *

from openEMS import openEMS
import numpy as np


# Model comments
#
# This is a generic model running port excitation for all ports defined below,
# to get full [S] matrix data.
# Output is stored to Touchstone S-parameter file.
# No data plots are created by this script.
#
# This model uses the settings{} dictionary syntax and the gds2openEMS PyPI package
# (pip install gds2openEMS) instead of a local copy of the modules folder - see the
# README for the loose-variable / local-modules-copy alternative, still fully supported.


# ======================== workflow settings ================================

settings = {}

settings['preview_only'] = True  # preview model/mesh only?
settings['no_gui'] = False # if set to True, there is no mesh/model preview in AppCSXCAD, and simulation starts immediately.

# ===================== input files and path settings =======================

gds_filename = "../klayout/Tline_coll_out.gds"   # geometries
XML_filename = "SG13G2.xml"          # stackup

# preprocess GDSII for safe handling of cutouts/holes?
settings['preprocess_gds'] = False

# merge via polygons with distance less than .. microns, set to 0 to disable via merging.
settings['merge_polygon_size'] = 1


# get path for this simulation file
script_path = utilities.get_script_path(__file__)
# use script filename as model basename
model_basename = utilities.get_basename(__file__)
# set and create directory for simulation output
sim_path = utilities.create_sim_path (script_path,model_basename)
print('Simulation data directory: ', sim_path)
# change current path to model script path
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ======================== simulation settings ================================

settings['unit']   = 1e-6  # geometry is in microns
settings['margin'] = 200    # distance in microns from GDSII geometry boundary to simulation boundary

settings['fstart']  = 0e9
settings['fstop']   = 350e9
settings['numfreq'] = 401

settings['refined_cellsize'] = 0.3  # mesh cell size in conductor region

# choices for boundary:
# 'PEC' : perfect electric conductor (default)
# 'PMC' : perfect magnetic conductor, useful for symmetries
# 'MUR' : simple MUR absorbing boundary conditions
# 'PML_8' : PML absorbing boundary conditions
settings['Boundaries'] = ['PEC', 'PEC', 'PEC', 'PEC', 'PEC', 'PEC']

settings['cells_per_wavelength'] = 20   # how many mesh cells per wavelength, must be 10 or more
settings['energy_limit'] = -50          # end criteria for residual energy (dB)

# port configuration, port geometry is read from GDSII file on the specified layer
simulation_ports = simulation_setup.all_simulation_ports()

# in-plane port is specified with target_layername= and direction x or y
# via port is specified with from_layername= and to_layername= and direction z
simulation_ports.add_port(simulation_setup.simulation_port(portnumber=1, 
                                                           voltage=1, 
                                                           port_Z0=50, 
                                                           source_layernum=201, 
                                                           from_layername='Metal2', 
                                                           to_layername='TopMetal2', 
                                                           direction='z'))

simulation_ports.add_port(simulation_setup.simulation_port(portnumber=2, 
                                                           voltage=1, 
                                                           port_Z0=50, 
                                                           source_layernum=202, 
                                                           from_layername='Metal2', 
                                                           to_layername='TopMetal1', 
                                                           direction='z'))

# optional field dump based on bounding box of GDSII layer data on special layers
# supported dump_type = 'E','H','J','rotH'
# supported file_type = 'vtk', 'hdf5'
# z-position is zmax of from_layername, zmin of to_layername
# if field_dumps == True:
#     field_dumps = simulation_setup.all_field_dumps()
#     field_dumps.add_frequency_dump(name='Jf', file_type='vtk', dump_type='J', frequency=60e9, source_layernum=301, from_layername='TopMetal2', to_layername='TopMetal2', offset_top=0, offset_bottom=0)
#     field_dumps.add_time_dump(name='Et', file_type='vtk', dump_type='E', source_layernum=302, from_layername='Metal2', to_layername='TopMetal2', offset_top=10, offset_bottom=0)
# settings['field_dumps'] = field_dumps

# ======================== simulation ================================

# get technology stackup data
materials_list, dielectrics_list, metals_list = stackup_reader.read_substrate (XML_filename)
# get list of layers from technology
layernumbers = metals_list.getlayernumbers()
# we must also read the layers where we added ports, these are not included in technology layers
layernumbers.extend(simulation_ports.portlayers)

# read geometries from GDSII, only purpose 0
allpolygons = gds_reader.read_gds(gds_filename,
                                  layernumbers,
                                  purposelist=[0],
                                  metals_list=metals_list,
                                  preprocess=settings['preprocess_gds'],
                                  merge_polygon_size=settings['merge_polygon_size'])

# maximum cellsize is calculated inside setupSimulation when using settings dictionary

# define excitation and stop criteria and boundaries
FDTD = openEMS(EndCriteria=np.exp(settings['energy_limit']/10 * np.log(10)))
FDTD.SetGaussExcite( (settings['fstart']+settings['fstop'])/2, (settings['fstop']-settings['fstart'])/2 )
FDTD.SetBoundaryCond( settings['Boundaries'] )

settings['simulation_ports'] = simulation_ports
settings['materials_list'] = materials_list
settings['dielectrics_list'] = dielectrics_list
settings['metals_list'] = metals_list
settings['layernumbers'] = layernumbers
settings['allpolygons'] = allpolygons
settings['sim_path'] = sim_path
settings['model_basename'] = model_basename


########### create model, run and post-process ###########

# run all active port excitations, one after another. Ports with voltage=0 are skipped here -
# their S-parameters are left out of the result, see the FAQ in the user's guide.

for excite_portnumbers in simulation_ports.all_active_excitations():
    settings['excite_portnumbers'] = excite_portnumbers

    simulation_setup.setupSimulation (FDTD=FDTD, settings=settings)  # must use named parameters when using settings dict!
    simulation_setup.runSimulation   (FDTD=FDTD, settings=settings)  # must use named parameters when using settings dict!


# Initialize an empty matrix for S-parameters
num_ports = simulation_ports.portcount
s_params = np.empty((num_ports, num_ports, settings['numfreq']), dtype=object)

# Define frequency resolution. Due to FFT from Empire time domain results,
# this is postprocessing and we can change it again at any time.
f = np.linspace(settings['fstart'],settings['fstop'],settings['numfreq'])

# Populate the S-parameter matrix with simulation results
for i in range(1, num_ports + 1):
    for j in range(1, num_ports + 1):
        s_params[i-1, j-1] = utilities.calculate_Sij(i, j, f, sim_path, simulation_ports)

# Write to Touchstone *.snp file
snp_name = os.path.join(sim_path, model_basename + '.s' + str(num_ports) + 'p')
utilities.write_snp(s_params, f, snp_name, z0=simulation_ports.get_reference_impedance())

print('Created S-parameter output file at ', snp_name)
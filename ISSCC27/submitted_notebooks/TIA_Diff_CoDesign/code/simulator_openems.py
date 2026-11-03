# N-port openEMS simulation of a transformer (4 ports) or spiral (2 ports).
# No symmetry is assumed: every port is excited once (N FDTD runs), the S-matrix is written as touchstone.
# Env: EM_MARGIN (um), EM_ENERGY (dB end criterion), EM_SKIP_PORT=k skips the excitation of port k (S column by reciprocity, S_kk by energy balance).
# Usage: python simulator_openems.py -g x.gds -s x.s4p -x SG13G2.xml -m name -r workdir [--nports 4] [--preview]
import os
import sys
import argparse

from em_port_metadata import resolve_port_metadata,resolve_port_metal,validate_port_coverage


parser = argparse.ArgumentParser("parser")
parser.add_argument('-g', '--gds')
parser.add_argument('-s', '--snp')
parser.add_argument('-x', '--xml')
parser.add_argument('-m', '--model')
parser.add_argument('-r', '--script')
parser.add_argument('--nports', type=int, default=4)
parser.add_argument('--port-metal', choices=('TopMetal1', 'TopMetal2'), help='port landing metal; inferred from INFO or the GDS JSON sidecar by default')
parser.add_argument('--preview', action='store_true')
args = parser.parse_args()
try:
	PORT_DEFINITION = resolve_port_metadata(args.gds,args.script,args.port_metal,args.nports)
	validate_port_coverage(args.gds,PORT_DEFINITION)
	PORT_METAL = PORT_DEFINITION['port_layers'][0]
except (ValueError, KeyError, TypeError, OSError) as e:
	parser.error(str(e))

sys.path.insert(0, os.path.abspath(os.path.join(args.script, 'modules')))

import modules.util_stackup_reader as stackup_reader
import modules.util_gds_reader as gds_reader
import modules.util_utilities as utilities
import modules.util_simulation_setup as simulation_setup
import modules.util_meshlines as util_meshlines

from openEMS import openEMS
import numpy as np
import skrf as rf

preview_only = args.preview
postprocess_only = False

gds_filename = args.gds
XML_filename = args.xml
preprocess_gds = True
merge_polygon_size = 1.5
script_path = args.script
model_basename = args.model

sim_path = os.path.join('/tmp/ray_cache', 'TIADN_' + model_basename + '_sim')
print('Simulation data directory: ', sim_path)
os.chdir(script_path)

unit = 1e-6
margin = float(os.environ.get('EM_MARGIN', 200))

fstart = 0
fstop = 100e9
numfreq = 1001

refined_cellsize = 1.0
Boundaries = ['PEC', 'PEC', 'PEC', 'PEC', 'PEC', 'PEC']
cells_per_wavelength = 20
energy_limit = float(os.environ.get('EM_ENERGY', -50))
SKIP = int(os.environ.get('EM_SKIP_PORT', 0))   # port whose excitation is skipped (4-port only); its column is estimated

NPORTS = args.nports
simulation_ports = simulation_setup.all_simulation_ports()
for pn in range(1, NPORTS + 1):
	simulation_ports.add_port(simulation_setup.simulation_port(portnumber=pn, voltage=1, port_Z0=50, source_layernum=200 + pn, from_layername='Metal4', to_layername=PORT_METAL, direction='z'))

materials_list, dielectrics_list, metals_list = stackup_reader.read_substrate(XML_filename)
layernumbers = metals_list.getlayernumbers()
layernumbers.extend(simulation_ports.portlayers)

allpolygons = gds_reader.read_gds(gds_filename, layernumbers, purposelist=[0], metals_list=metals_list, preprocess=preprocess_gds, merge_polygon_size=merge_polygon_size)

wavelength_air = 3e8 / fstop / unit
max_cellsize = (wavelength_air) / (np.sqrt(materials_list.eps_max) * cells_per_wavelength)

FDTD = openEMS(EndCriteria=np.exp(energy_limit / 10 * np.log(10)))
FDTD.SetGaussExcite((fstart + fstop) / 2, (fstop - fstart) / 2)
FDTD.SetBoundaryCond(Boundaries)

EXC = [pn for pn in range(1, NPORTS + 1) if pn != SKIP]
for pn in EXC:
	FDTD = simulation_setup.setupSimulation([pn],
											simulation_ports,
											FDTD,
											materials_list,
											dielectrics_list,
											metals_list,
											allpolygons,
											max_cellsize,
											refined_cellsize,
											margin,
											unit,
											xy_mesh_function=util_meshlines.create_xy_mesh_from_polygons)
	simulation_setup.runSimulation([pn], FDTD, sim_path, model_basename, preview_only, postprocess_only)

if not preview_only:
	print('Begin data evaluation')
	f = np.linspace(fstart, fstop, numfreq)
	s = np.zeros((numfreq, NPORTS, NPORTS), dtype=complex)
	for j in EXC:
		for i in range(1, NPORTS + 1):
			s[:, i - 1, j - 1] = utilities.calculate_Sij(i, j, f, sim_path, simulation_ports)
	if SKIP:
		k, p = SKIP - 1, {0: 1, 1: 0, 2: 3, 3: 2}[SKIP - 1]   # p = the other end of the same winding
		for i in range(NPORTS):
			if i != k:
				s[:, i, k] = s[:, k, i]   # reciprocity
		# |S_kk|^2 from energy balance with the partner's loss, phase of the partner's S_pp
		off = sum(np.abs(s[:, i, k]) ** 2 for i in range(NPORTS) if i != k)
		loss_p = 1 - (np.abs(s[:, :, p]) ** 2).sum(axis=1)
		s[:, k, k] = np.sqrt(np.clip(1 - off - loss_p, 0, 1)) * np.exp(1j * np.angle(s[:, p, p]))
	ext = f'.s{NPORTS}p'
	rf.Network(frequency=rf.Frequency.from_f(f, unit='hz'), s=s, z0=50).write_touchstone(
		args.snp[:-len(ext)] if args.snp.endswith(ext) else args.snp, form='ri')

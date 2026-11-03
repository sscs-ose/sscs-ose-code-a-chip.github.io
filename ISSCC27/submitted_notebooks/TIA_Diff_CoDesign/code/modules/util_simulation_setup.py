# -*- coding: utf-8 -*-

import os

import util_stackup_reader as stackup_reader
import util_gds_reader as gds_reader
import util_utilities as utilities
import util_meshlines

from pylab import *
from CSXCAD import ContinuousStructure
from CSXCAD import AppCSXCAD_BIN
from openEMS import openEMS
from openEMS.physical_constants import *


class simulation_port:
  """
    port object
    for in-plane port, parameter target_layername is specified
    for via port, parameters from_layername and to_layername are specified for the metals above and below   
  """
  
  def __init__ (self, portnumber, voltage, port_Z0, source_layernum, target_layername=None, from_layername=None, to_layername=None, direction='x'):
    self.portnumber = portnumber
    self.source_layernum = source_layernum        # source for port geometry is a GDSII layer, just one port per layer
    self.target_layername = target_layername      # target layer where we create the port, if specified we create in-plane port
    self.from_layername  = from_layername         # layer on one end of via port, used if target_layername is None
    self.to_layername    = to_layername           # layer on other  end of via port
    self.reversed_direction = ('-' in direction)  # detect reversed port direction
    self.direction  = direction.replace('-', '')  # remove sign that before sending to openEMS
    self.direction  = self.direction.replace('+', '')  # just in case users might specify positive sign in direction string
    
    self.port_Z0 = port_Z0
    self.voltage = voltage
    self.CSXport = None

  def set_CSXport (self, CSXport):
    self.CSXport = CSXport  

  def __str__ (self):
    # string representation 
    mystr = 'Port ' + str(self.portnumber) + ' voltage = ' + str(self.voltage) + ' GDS source layer = ' + str(self.source_layernum) + ' target layer = ' + str(self.target_layername) + ' direction = ' + str(self.direction)
    return mystr
  

class all_simulation_ports:
  """
  all simulation ports object
  """
  
  def __init__ (self):
      self.ports = []
      self.portcount = 0
      self.portlayers = []

  def add_port (self, port):
      self.ports.append(port)
      self.portcount = len(self.ports)
      self.portlayers.append(port.source_layernum)

  def get_port_by_layernumber (self, layernum):  # special GDSII layer for ports only, one port per layer, so we have 1:1 mapping
      found = None
      for port in self.ports:
          if port.source_layernum == layernum:
              found = port
              break
      return found       
  
  def get_port_by_number (self, portnum):
      return self.ports[portnum-1] 


def addGeometry_to_CSX (CSX, excite_portnumbers,simulation_ports,FDTD, materials_list, dielectrics_list, metals_list, allpolygons):
# Add polygons   

    # hold CSX material definitions, but only for stackup materials that are actually used
    CSX_materials_list = {}

    # add geometries on metal and via layers
    for poly in allpolygons.polygons:
        # each poly knows its layer number
        # get material name for poly, by using metal information from stackup
        # special case MIM: we can have two different materials (metal and dielectric) coming from same source layer

        all_assigned = metals_list.getallbylayernumber (poly.layernum)
        if all_assigned != None:
            for metal in all_assigned:
                materialname = metal.material
                # check for openEMS CSX material object that belongs to this material name
                if materialname in CSX_materials_list.keys():
                    # already in list, was used before
                    CSX_material = CSX_materials_list[materialname]
                else:
                    # create CSX material, was not used before
                    material = materials_list.get_by_name(materialname)
                    CSX_material = CSX.AddMaterial(material.name, kappa=material.sigma, epsilon=material.eps)
                    CSX_materials_list.update({material.name: CSX_material})
                    # set color for IHP layers, if available, so that we see that color in AppCSXCAD 3D view
                    if material.color != "":
                        CSX_material.SetColor('#' + material.color, 255)  # transparency value 255 = solid

                # add Polygon to CSX 
                # remember value for MA meshing algorithm, which works on CSX polygons rather than our GDS polygons
                p = CSX_material.AddLinPoly(priority=200, points=poly.pts, norm_dir ='z', elevation=metal.zmin, length=metal.thickness)
                poly.CSXpoly = p
                
    return CSX, CSX_materials_list                    


def addDielectrics_to_CSX (CSX, CSX_materials_list,  materials_list, dielectrics_list, allpolygons, margin, addPEC):
# Add dielectric layers (these extend through simulation area and have no polygons in GDSII)

    for dielectric in dielectrics_list.dielectrics:
        # get CSX material object for this dielectric layers material name
        materialname = dielectric.material
        material = materials_list.get_by_name(materialname)
        
        if materialname in CSX_materials_list.keys():
            # already defined in CSX materials, was used before
            CSX_material = CSX_materials_list[materialname]
        else:
            # create CSX material, was not used before
            CSX_material = CSX.AddMaterial(material.name, kappa=material.sigma, epsilon=material.eps)
            CSX_materials_list.update({material.name: CSX_material})
            # set color for IHP layers, if available
            if material.color != "":
                CSX_material.SetColor('#' + material.color, 20)  # transparency value 20, very transparent

        # now that we have a CSX material, add the dielectric body (substrate, oxide etc)
            CSX_material.AddBox(priority=10, start=[allpolygons.xmin - margin, allpolygons.ymin - margin, dielectric.zmin], stop=[allpolygons.xmax + margin, allpolygons.ymax + margin, dielectric.zmax])

    # Optional: add a layer of PEC with zero thickness below stackup
    # This is useful if we have air layer around for absorbing boundaries (antenna simulation)
    if addPEC:
        PEC = CSX.AddMetal( 'PEC_bottom' )
        PEC.SetColor('#ffffff', 50) 
        PEC.AddBox(priority=255, start=[allpolygons.xmin - margin, allpolygons.ymin - margin, 0], stop=[allpolygons.xmax + margin, allpolygons.ymax + margin, 0])

    return CSX, CSX_materials_list  


def addPorts_to_CSX (CSX, excite_portnumbers,simulation_ports,FDTD, materials_list, dielectrics_list, metals_list, allpolygons):
# Add polygons   

    # hold CSX material definitions, but only for stackup materials that are actually used
    CSX_materials_list = {}

    # add geometries on metal and via layers
    for poly in allpolygons.polygons:
        # each poly knows its layer number
        # get material name for poly, by using metal information from stackup
        metal = metals_list.getbylayernumber (poly.layernum)
        if metal == None: # this layer does not exist in XML stackup
            # found a layer that is not defined in stackup from XML, check if used for ports
            if poly.layernum in simulation_ports.portlayers:
                # mark polygon for special handling in meshing
                poly.is_port = True 

                # find port definition for this GDSII source layer number
                port = simulation_ports.get_port_by_layernumber(poly.layernum)
                if port != None:
                    portnum = port.portnumber
                    port_direction = port.direction
                    port_Z0 = port.port_Z0
                    if portnum in excite_portnumbers: # list of excited ports, this can be more than one port number for GSG with composite ports
                        voltage = port.voltage        # only apply source voltage to ports that are excited in this simulation run
                    else:
                        voltage = 0                   # passive port in this simulation run
                    if port.reversed_direction:       # port direction changes polarity
                        xmin = poly.xmax
                        xmax = poly.xmin
                        ymin = poly.ymax
                        ymax = poly.ymin
                    else:        
                        xmin = poly.xmin
                        xmax = poly.xmax
                        ymin = poly.ymin
                        ymax = poly.ymax
                    
                    # port z coordinates are different between in-plane ports and via ports
                    if port.target_layername != None:
                        # in-plane port   
                        port_metal = metals_list.getbylayername(port.target_layername)
                        zmin = port_metal.zmin
                        zmax = port_metal.zmax
                    else:
                       # via port 
                       if port.from_layername == 'GND': # special case bottom of simulation box
                         zmin_from = 0
                         zmax_from = 0
                       else:
                         from_metal = metals_list.getbylayername(port.from_layername)
                         if from_metal==None:
                            print('[ERROR] Invalid layer ' , port.from_layername, ' in port definition, not found in XML stackup file!')
                            sys.exit(1)                             
                         zmin_from  = from_metal.zmin
                         zmax_from  = from_metal.zmax
                       
                       if port.to_layername == 'GND': # special case bottom of simulation box
                         zmin_to = 0
                         zmax_to = 0
                       else:
                         to_metal   = metals_list.getbylayername(port.to_layername)
                         if to_metal==None:
                            print('[ERROR] Invalid layer ' , port.to_layername, ' in port definition, not found in XML stackup file!')
                            sys.exit(1)                             
                         zmin_to    = to_metal.zmin
                         zmax_to    = to_metal.zmax
                       
                       # if necessary, swap from and to position
                       if zmin_from < zmin_to:
                           # from layer is lower layer
                           zmin = zmax_from
                           zmax = zmin_to
                       else:    
                           # to layer is lower layer
                           zmin = zmax_to
                           zmax = zmin_from

                    CSX_port = FDTD.AddLumpedPort(portnum, port_Z0, [xmin, ymin, zmin], [xmax, ymax, zmax], port_direction, voltage, priority=150)
                    # store CSX_port in the port object, for evaluation later
                    port.set_CSXport(CSX_port)
                    


    return CSX





def addMesh_to_CSX (CSX, allpolygons, dielectrics_list, metals_list, refined_cellsize, max_cellsize, margin, air_around, unit, z_mesh_function, xy_mesh_function):
# Add mesh using default method
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(unit)

    # meshing of dielectrics and metals
    no_z_mesh_list = ['SiO2','LBE'] # exclude SiO2 from meshing because we only mesh metal layers in that region, exclude LBE because we mesh substrate
    mesh = z_mesh_function (mesh, dielectrics_list, metals_list, refined_cellsize, max_cellsize, air_around, no_z_mesh_list)
    mesh = xy_mesh_function (mesh, allpolygons, margin, air_around, refined_cellsize, max_cellsize)

    return mesh



def setupSimulation (excite_portnumbers,simulation_ports, FDTD, materials_list, dielectrics_list, metals_list, allpolygons, max_cellsize, refined_cellsize, margin, unit, z_mesh_function=util_meshlines.create_z_mesh, xy_mesh_function=util_meshlines.create_standard_xy_mesh, air_around=0):
# Define function for model creation because we need to create and run separate CSX
# for each excitation. For S11,S21 we only need to excite port 1, but for S22,S12
# we need to excite port 2. This requires separate CSX with different port settings.

    CSX = ContinuousStructure()
    FDTD.SetCSX(CSX)

    # add geometries and return list of used materials
    CSX, CSX_materials_list = addGeometry_to_CSX (CSX, excite_portnumbers,simulation_ports,FDTD, materials_list, dielectrics_list, metals_list, allpolygons)
    CSX, CSX_materials_list = addDielectrics_to_CSX (CSX, CSX_materials_list,  materials_list, dielectrics_list, allpolygons, margin, addPEC=(air_around>0))

    # add ports
    CSX  = addPorts_to_CSX (CSX, excite_portnumbers,simulation_ports,FDTD, materials_list, dielectrics_list, metals_list, allpolygons)

    # check which layers are actually used, this information is required for meshing in z direction
    # mark if polygon is a via
    if metals_list != None: 
      for poly in allpolygons.polygons:
        layernum = poly.layernum
        metal = metals_list.getbylayernumber(layernum)
        if metal != None:
            metal.is_used = True
            # set polygon via property, used later for meshing
            poly.is_via = metal.is_via

    # add mesh
    mesh = addMesh_to_CSX (CSX, allpolygons, dielectrics_list, metals_list, refined_cellsize, max_cellsize, margin, air_around, unit, z_mesh_function, xy_mesh_function )

    # display mesh information (line count and smallest mesh cells)
    meshinfo = util_meshlines.get_mesh_information(mesh)
    print(meshinfo)

    return FDTD


def runSimulation (excite_portnumbers, FDTD, sim_path, model_basename, preview_only, postprocess_only, force_simulation=False):
 
    excitation_path = utilities.get_excitation_path (sim_path, excite_portnumbers)
    
    if not postprocess_only:
        # write CSX file 
        CSX_file = os.path.join(excitation_path, model_basename + '.xml')
        CSX = FDTD.GetCSX()
        CSX.Write2XML(CSX_file)

        # preview model
        if False and 1 in excite_portnumbers:  # only for first port excitation
            print('Starting AppCSXCAD 3D viewer with file: \n', CSX_file)
            print('Close AppCSXCAD to continue or press <Ctrl>-C to abort')
            ret = os.system(AppCSXCAD_BIN + ' "{}"'.format(CSX_file))
            if ret != 0:
                print('[ERROR] AppCSXCAD failed to launch. Exit code: ', ret)
                sys.exit(1)

    if not (preview_only or postprocess_only):  # start simulation 
        # Check if we can read a hash file from the result folder
        existing_data_hash = get_hash_from_data_folder(excitation_path)

        # Create hash of newly created CSX file, we will store that to result folder when simulation is finished.
        # This will enable checking for pre-existing data of the exact same model.
        XML_hash = calculate_sha256_of_file(CSX_file)

        if (existing_data_hash != XML_hash) or force_simulation:
            # Hash is different or not found, or simulation is forced
            print('Starting FDTD simulation for excitation ', str(excite_portnumbers))
            try:

                n_threads = int(os.environ.get('OPENEMS_THREADS', 0))
                if n_threads > 0:
                    FDTD.Run(excitation_path, numThreads=n_threads)
                else:
                    FDTD.Run(excitation_path)  # DO NOT SPECIFY COMMAND LINE OPTIONS HERE! That will fail for repeated runs with multiple excitations.
                print('FDTD simulation completed successfully for excitation ', str(excite_portnumbers))
                # Now that simulation created output data, write the hash of the underlying XML model. This will help to identify existing data for this model.
                write_hash_to_data_folder(excitation_path, XML_hash)
            except AssertionError as e:
                print('[ERROR] AssertionError during FDTD simulation: ', e)
                sys.exit(1)
        else:
            print('Data for this model already exists, skipping simulation!')
            print('To force re-simulation, add parameter "force_simulation=True" to the runSimulation() call.')


    return excitation_path


######### end of function createSimulation ()  ##########

# Utility functions for hash file.
# By creating and storing a hash of CSX file to the result folder when simulation is finished,
# we can identify pre-existing data of the exact same model. In this case, we can skip simulation.

def calculate_sha256_of_file(filename):
    import hashlib
    sha256_hash = hashlib.sha256()
    with open(filename, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()

def write_hash_to_data_folder (excitation_path, hash_value):
    filename = os.path.join(excitation_path, 'simulation_model.hash')
    hashfile = open(filename, 'w')
    hashfile.write(str(hash_value))
    hashfile.close() 

def get_hash_from_data_folder (excitation_path):
    filename = os.path.join(excitation_path, 'simulation_model.hash')
    hashvalue = ''
    if os.path.isfile(filename):
        hashfile = open(filename, "r")
        hashvalue = hashfile.read()
        hashfile.close()
    return hashvalue


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

# Read ADS *.subst and materials.matdb, create XML for IHP OpenEMS workflow
# Required Python version: Python 3

# Version: 18 Dec 2024


import os, sys
import xml.etree.ElementTree 

# --------------------- file names --------------------------

ADS_materials_filename = "materials.matdb"

# ---------------------- special processing ---------------------------

# define list of dielectrics that we want to skip while building stackup
# exclude_dielectrics = ["Passive"]
exclude_dielectrics = []

# air layer thickness above substrate
air_above = 300

merge_dielectrics = True

# -------------------- IHP colors ---------------------------
# Materials not listed here get their color set to empty string

colormapping = {
"Activ" : "00ff00", 
"Metal1": "39bfff",
"Metal2": "ccccd9",
"Metal3": "d80000",
"Metal4": "93e837",
"Metal5": "dcd146",
"MIM":    "268c6b",
"TopMetal1": "ffe6bf",
"TopMetal2": "ff8000",
"ThickCu1": "bdb76b",
"ThickCu2": "ffebcd",
"ThickAl": "ff8c00",
"ThinAl": "deb887",

"TopVia2": "ff8000",
"TopVia1": "ffe6bf",
"Vmim": "c0c0c0",
"Via7": "ff7f50",
"Via6": "faebd7",
"Via5": "ff69b4",
"Via4": "deac5e",
"Via3": "9ba940",
"Via2": "ff3736",
"Via1": "ccccff",
"Cont": "00ffff",
"Passive": "a0a0f0",
"SiO2" : "fffcad",
"EPI"  : "294fff",
"Substrate" : "01e0ff",
"AIR" : "d0d0d0"
}


def color_from_layername (layername, defaultcolor):
  splitlist = layername.split("_", 1)
  basename = splitlist[0]
  color_from_dictionary = colormapping.get(basename, defaultcolor)
    
  # print ("Layer basename: ", basename , " color: ", color_from_dictionary)
  return color_from_dictionary


# -------------------- material types ---------------------------

class ADS_conductor_material:
    
  def __init__ (self, name, conductivity_string):
    self.name = name
    self.materialtype = "conductor"
    self.priority = 200
    self.thinsheet = 0
    self.ohmspersquare = 0
    self.display_color = ""
    self.used = False  # material used in metal layer?

    # split conductivity string, get pure conductivity/resistance value
    conductivity_value = float(conductivity_string.split()[0])
    
    # check if we have Ohm/Sq or Siemens/m
    if "Ohm/Sq" in conductivity_string:
      # not supported 
      print ("THIN SHEET: will be ignored, Ohm/square metal type is not supported")
      self.sigma = 0
      self.thinsheet = 1
      ohmspersquare = conductivity_value
      
    elif "Siemens/m" in conductivity_string:
      self.sigma = conductivity_value
    else:
      self.sigma = 1e10

  def __str__ (self):
    # string representation for XML output
    mystr = '      <Material Name="' + self.name + '" Type="Conductor" Permittivity="1" DielectricLossTangent="0" Conductivity="' +  str(self.sigma) + '" Color="' + self.display_color + '"/>\n'
    return mystr
    



class ADS_dielectric_material:
    
  def __init__ (self, name, eps_string, tand_string):
    self.name = name
    self.materialtype = "dielectric"
    self.priority = 100
    self.semiconductor = False
    self.display_color = ""
    self.used = False  # material used in dielectric layer?

    # get epsilon, default is air
    if eps_string != None:
      eps_value = float(eps_string)
    else:
      eps_value = 1
    self.epsilon = eps_value

    # get loss tangent, default is 0
    tand_value = 0
    if tand_string != None:
      if tand_string != "":
        tand_value = float(tand_string)
    self.tand = tand_value  

    # set conductivity to 0
    self.sigma = 0

  
  def __str__ (self):
    # string representation: return XML string
    mystr = '      <Material Name="' + self.name + '" Type="Dielectric" Permittivity="' + str(self.epsilon) + '" DielectricLossTangent="' + str(self.tand) + '" Conductivity="' +  str(self.sigma) + '" Color="' + self.display_color + '"/>\n'
    return mystr




class ADS_semiconductor_material:
    
  def __init__ (self, name, eps_string, resistivity_string):
    self.name = name
    self.materialtype = "semiconductor"
    self.priority = 100
    self.semiconductor = True
    self.display_color = ""
    self.used = False  # material used in semiconductor layer?

    # get epsilon, default is air
    if eps_string != None:
      eps_value = float(eps_string)
    else:
      eps_value = 1
    self.epsilon = eps_value


    # get conductivity
    
    resistivity_value = float(resistivity_string.split()[0]) # mOhm*cm
    self.sigma = 1 / (resistivity_value*0.01)

  
  def __str__ (self):
    # string representation: return XML string
    mystr = '      <Material Name="' + self.name + '" Type="Semiconductor" Permittivity="' + str(self.epsilon) + '" DielectricLossTangent="0" Conductivity="' +  str(self.sigma) + '" Color="' + self.display_color + '"/>\n'
    return mystr
    



# -------------------- utilities ---------------------------


def find_by_name (myList, name):
  for a in myList:
    if a.name == name:
      return a

def print_all (myList):
  for a in myList:
    print (a)


def testequal (a,b):
  abcompare = (abs(a-b)<0.0001)
  return abcompare

def value2string (value):
  # return string with 4 decimal digits
   return format(value,'.4f')
  

def get_thickness_micron (thickness_string, thickunit_string):
  
  # evaluate unit factor in substrate file, convert to micron
  if thickunit_string=="meter":
    thickfactor = 1e6
  elif thickunit_string=="millimeter":
    thickfactor = 1e3
  elif thickunit_string=="micron":
    thickfactor = 1.0
  elif thickunit_string=="nanometer":
    thickfactor = 1e-3
  elif thickunit_string=="mil":
    thickfactor = 25.4
  elif thickunit_string=="inch":
    thickfactor = 25.4e3
  else:
    thickfactor = 1.0   # default
    
  
  if thickness_string != None:
    thickness_um = float(thickness_string) * thickfactor
  else: 
    thickness_um = 0  # default
  
  return thickness_um


# -------------------- ADS dielectric stackup elements ---------------------------

class ADS_dielectric_layer:

  def __init__ (self, materialname, material, thickness_string, thickunit_string):
    self.layername = materialname

    self.thickness = get_thickness_micron (thickness_string, thickunit_string)
    self.material = material
   
    self.zmin = 0
    self.zmax = 0
    
  def __str__ (self): 
    if self.thickness > 0.0001:
      mystr = '        <Dielectric Name="' +  self.layername +  '" '
      mystr = mystr + 'Material="' + self.material.name +  '" '
      mystr = mystr + 'Thickness="' + value2string(self.thickness) +  '" '
      mystr = mystr + '/>\n'
    else:
      mystr = ''
    return mystr

  

class ADS_dielectric_layer_list (list):

  def __init__ (self):
    self.layers = []      # list with dielectric_layer objects
    self.interface_pos = []   # list with z position of ADS "interfaces" where metals go
    self.used_layer_name_list = []
    
  def append (self, what):
    self.layers.append (what)
    
  def getlayer_by_index (self, index):
    return self.layers[index]
  
  def get_zpos_by_index (self, index):
    return self.interface_pos[index]
  
  def count (self):
    return len(self.layers)
    
  def merge_if_same_material (self):
    # merge dielectrics if possible
    index = 1
    while index < (len(self.layers)):
      this_dielectric = self.layers[index]
      last_dielectric = self.layers[index-1]
      
      # get string representation
      this_material_property = str(this_dielectric.material)
      last_material_property = str(last_dielectric.material)

      # remove the name from the line, because for merging we don't care what the name is
      this_name = this_material_property.split()[1]
      this_material_property = this_material_property.replace(this_name, "")
      last_name = last_material_property.split()[1]
      last_material_property = last_material_property.replace(last_name, "")

      if this_material_property == last_material_property:
        # then we have the same material, so just update add thickness values 
      
        last_dielectric.thickness = last_dielectric.thickness + this_dielectric.thickness
        del self.layers[index]
        index = index-1
        print ("Merged dielectrics ", this_name, " and ", last_name)
      
      index = index + 1 


  def assign_z_positions (self):
    # store min and max z position of dielectric layer
    z = 0
    index = 0
    while index < (len(self.layers)):
      this_dielectric = self.layers[index]
      this_dielectric.zmin = z
      this_dielectric.zmax = this_dielectric.zmin  + this_dielectric.thickness
      z = this_dielectric.zmax
      index = index + 1

  
  def assign_unique_layername (self):
    index = 1
    while index < (len(self.layers)):
      dielectric = self.layers[index]
      layername = dielectric.layername
      # make sure we have a unique name
      if layername in self.used_layer_name_list:
        n = 1
        while (layername + "_" + str(n)) in self.used_layer_name_list:
          n = n+1
        layername = layername + "_" + str(n)
      self.used_layer_name_list.append(layername)   # store to list of used names
      dielectric.layername = layername  # back annotate name to dieelectric 
      
      index = index + 1 
  

  def assign_interface_positions (self):
    # stores possible positions of metal layers BEFORE merging dielectrics
    z = 0
    index = 0
    while index < (len(self.layers)):
      this_dielectric = self.layers[index]
      z = z + this_dielectric.thickness
      self.interface_pos.append(z)
      index = index + 1

  def tag_materials (self):
    # Tag materials as used
    for layer in self.layers:
      layer.material.used = True

    
  def process_dielectric_layers (self):
    # Run this AFTER reading metals, because some metals can expand the dielectric thickness

    # merge identical materials on adjacent layers
    if merge_dielectrics:
      self.merge_if_same_material()

    # add zmin and zmax to dielectric layersafter merging
    self.assign_z_positions()

    # Rename duplicate dielectric layer names, assure unique name
    self.assign_unique_layername()

    # Tag materials as used, so that they appear in final materials list output
    # This is done AFTER cleaning and merging list of dielectric layers
    self.tag_materials()
    

  def get_total_stackup_height (self):
    # Return the upper position of the topmost dielectric, 
    # used for calculating the total stackup height
    top_dielectric_index = len(self.layers)-1
    top_dielectric = self.layers[top_dielectric_index]
    height = top_dielectric.zmax
    return height
    
  def get_semiconductor_height (self):
    # Return the upper position of the topmost semiconductor, 
    # used for calculating the z-position of LBE layer for localized backside etching
    zmax = 0
    index = 0
    while index < (len(self.layers)):
      this_dielectric = self.layers[index]
      this_material = this_dielectric.material
      if this_material.semiconductor:
        zmax = this_dielectric.zmax
      index = index + 1
    return zmax 

  def get_semiconductor_zmin (self):
    # Return the lowest bottom position of semiconductors, 
    # used for calculating the z-position of LBE layer for localized backside etching
    zmin = 10000
    index = 0
    while index < (len(self.layers)):
      this_dielectric = self.layers[index]
      this_material = this_dielectric.material
      if this_material.semiconductor:
        zmin = min(zmin, this_dielectric.zmin)
      index = index + 1
    return zmin


  def __str__ (self): 
    composite = "Dielectrics\n"
    for l in self.layers:
      composite = composite + str(l) + "\n"
      
    composite = composite + "\nInterfaces\n"
    for i in self.interface_pos:
      composite = composite + str(i) + "\n"

    return composite
      

# -------------------- ADS metal layer stackup elements ---------------------------
  

class ADS_metal_layer:
  def __init__ (self, materialname, material, gdslayer, zpos, thickness_string, thickunit_string):
    self.layername = materialname + "_" + gdslayer  # add number to make it unique

    self.gdslayer = gdslayer    # ADS and GDSIII layer number
    self.material = material
    self.thickness = get_thickness_micron (thickness_string, thickunit_string)
    self.zpos1 = zpos
    self.zpos2 = zpos + self.thickness
    self.purpose = 0


  def __str__ (self): 
    mystr = '        <Layer Name="' +  str(self.material.name) +  '" '
    mystr = mystr + 'Type="conductor" '
    mystr = mystr + 'Zmin="' + value2string(self.zpos1) +  '" '
    mystr = mystr + 'Zmax="' + value2string(self.zpos2) +  '" '
    mystr = mystr + 'Material="' + self.material.name +  '" '
    mystr = mystr + 'Layer="' + str(self.gdslayer) + '" ' 
    mystr = mystr + '/>\n'
    return mystr


class ADS_metal_layers_list:
  def __init__ (self):
    self.layers = []
    
  def append (self, what):
    self.layers.append (what)
  
  def getlayer_by_index (self, index):
    return self.layers[index]
  
  def count (self):
    return len(self.layers)
    
  def find_from_zpos(self, zpos):
    found = None
    for l in self.layers:
      if testequal(l.zpos1, zpos):
        found=l
    return found  
    

  def __str__ (self): 
    composite = "Metal layers\n"
    for l in self.layers:
      composite = composite + str(l) + "\n"
    return composite


# -------------------- ADS via layer stackup elements ---------------------------

class ADS_via_layer:
  def __init__ (self, materialname, material, gdslayer, zpos1, zpos2):
    self.layername = materialname
    
    self.gdslayer = gdslayer    # ADS and GDSII layer number
    self.material = material
    self.zpos1 = zpos1
    self.zpos2 = zpos2
    self.purpose = 0
    
  def __str__ (self):

    mystr = '        <Layer Name="' +  str(self.layername) +  '" '
    mystr = mystr + 'Type="via" '
    mystr = mystr + 'Zmin="' + value2string(self.zpos1) +  '" '
    mystr = mystr + 'Zmax="' + value2string(self.zpos2) +  '" '
    mystr = mystr + 'Material="' + self.material.name +  '" '
    mystr = mystr + 'Layer="' + str(self.gdslayer) + '" ' 
    mystr = mystr + '/>\n'
    return mystr
  



class ADS_via_layers_list:
  def __init__ (self):
    self.layers = []
    
  def append (self, what):
    self.layers.append (what)
  
  def getlayer_by_index (self, index):
    return self.layers[index]
  
  def count (self):
    return len(self.layers)

   
  def find_from_zpos(self, zpos):
    found = None
    for l in self.layers:
      if testequal(l.zpos1, zpos):
        found=l
    return found  


  def __str__ (self): 
    composite = "Metal layers\n"
    for l in self.layers:
      composite = composite + str(l) + "\n"
    return composite




# ---------------- Get ADS substrate filename -----------------------------

mydir  = os.getcwd()             #    Base directory
print (mydir)

if len(sys.argv) < 2:
    print('Usage: momentum_to_xml <name.subst>')
else: 
  ADS_substrate_filename = sys.argv[1]
  print('Input filename: ', ADS_substrate_filename)
  if os.path.isfile(ADS_substrate_filename):

    # check if the name is IHP substrate name, for IHP special features 
    is_IHP_substrate = 'SG13' in ADS_substrate_filename.upper()

    # ----------- parse material file, store name and empire material string into lists -----------


    material_list = []      # holds instances of ADS_conductor, ADS_dielectric, ADS_semiconductor


    print ("Reading shared materials file ", ADS_materials_filename)
    materials_tree = xml.etree.ElementTree.parse(ADS_materials_filename)
    materials_root = materials_tree.getroot()


    for conductor in materials_root.iter("Conductor"):
      material_list.append (ADS_conductor_material(conductor.get("name"), conductor.get("real")))

    for dielectric in materials_root.iter("Dielectric"):
      material_list.append (ADS_dielectric_material(dielectric.get("name"), dielectric.get("er_real"), dielectric.get("er_loss")))

    for semiconductor in materials_root.iter("Semiconductor"):
      material_list.append (ADS_semiconductor_material(semiconductor.get("name"), semiconductor.get("er_real"), semiconductor.get("resistivity")))

    # Add ADS predefined materials
    material_list.append (ADS_dielectric_material("AIR", "1.0", "0.0"))

    
    # ----------- parse substrate file, get materials from list created before -----------


    print ("Reading substrate file ", ADS_substrate_filename, "\n")

    # data source is *.subst XML file
    substrate_tree = xml.etree.ElementTree.parse(ADS_substrate_filename)
    substrate_root = substrate_tree.getroot()


    # get dielectric layers from *.subst XML

    ADS_dielectric_layers = ADS_dielectric_layer_list () # initialize empty list
    for substrate in  substrate_root.iter("material"):

      thickness_string = substrate.get("thick")
      thickunit_string = substrate.get("thickunit")
      materialname = substrate.get("materialname")
      material = find_by_name (material_list, materialname)
      if material != None:
        if not materialname in exclude_dielectrics:
          dielectric_layer = ADS_dielectric_layer(materialname, material, thickness_string, thickunit_string)
          ADS_dielectric_layers.append (dielectric_layer)
        else:  
          print ("Skipped ", materialname, ", is listed in list of dielectrics to be excluded from model")
      else:
        print ("Material ", materialname, " not found in ", ADS_materials_filename)


    # add an air layer above
    material = find_by_name (material_list, "AIR")
    if material != None:
      ADS_dielectric_layers.append (ADS_dielectric_layer("AIR", material,str(air_above), "micron"))


    # check what metals expand dielectric layer thickness

    # process dielectric, set interface position where metal goes
    # do this before actually creating the metal list

    for layer in substrate_root.iter("layer"):
      metal_thickness = get_thickness_micron(layer.get("thick"), layer.get("thickunit"))
      layerindex = int(layer.get("index"))

      if metal_thickness > 0:
        # expand dielectric above
        dielectric = ADS_dielectric_layers.getlayer_by_index(layerindex+1)
      else:
        # expand dielectric below
        dielectric = ADS_dielectric_layers.getlayer_by_index(layerindex)
        
      expand = layer.get("expand")
      # special case expand where dielectric above or below must grow:
      if expand=="1":

        dielectric.thickness = dielectric.thickness + fabs(metal_thickness) # abs value because grow down comes as negative thickness
        print ("expand ", dielectric.layername, " t=", dielectric.thickness, " + " , metal_thickness )

    # now we have preliminary dielectric thickness and know metal layer positions
    ADS_dielectric_layers.assign_interface_positions() 
    

    # ---------------------------- prepare for substrate height parameter  ----------------------
    

    # get metal layers from *.subst XML

    ADS_metal_layers = ADS_metal_layers_list ()# initialize empty list
    for layer in substrate_root.iter("layer"):

      thickness_string = layer.get("thick")
      thickunit_string = layer.get("thickunit")

      # get z position from previously processed dielectrics
      layerindex = int(layer.get("index"))
      zpos = ADS_dielectric_layers.get_zpos_by_index(layerindex)

      gdslayer = layer.get ("layer")
      sheet = layer.get("sheet")

      materialname = layer.get("materialname")
      material = find_by_name (material_list, materialname)
      if material != None:
        name_upstr = materialname.upper()
        no_MIM = (name_upstr.find('MIM') <0)
        
        # skip layers with "MIM" in the layer name, e.g. VMIM or MIM
        if no_MIM:
          metal_layer = ADS_metal_layer(materialname, material, gdslayer, zpos, thickness_string, thickunit_string)
          material.used = True
        
          # special case thin metal simulation:
          if sheet=="1":
            print ("Layer " + materialname + " is flat metal model (SHEET), converted to thick metal model.")
            metal_layer.material.thinsheet=1
            metal_layer.material.ohmspersquare = 1 / (metal_layer.material.sigma*get_thickness_micron (thickness_string, thickunit_string)*1e-6)
        
          # append to list
          ADS_metal_layers.append (metal_layer) 
      else:
        print ("Could not find material definition for ", materialname)

        

    # get via layers from *.subst XML

    ADS_via_layers = ADS_via_layers_list ()# initialize empty list
    for via in substrate_root.iter("via"):

      thickness_string = layer.get("thick")
      thickunit_string = layer.get("thickunit")

      # get z position from previously processed dielectrics
      layerindex1 = int(via.get("index1"))
      layerindex2 = int(via.get("index2"))
      zpos1 = ADS_dielectric_layers.get_zpos_by_index(layerindex1)
      zpos2 = ADS_dielectric_layers.get_zpos_by_index(layerindex2)
      
      gdslayer = via.get ("layer")

      materialname = via.get("materialname")
      material = find_by_name (material_list, materialname)

      if material != None:
          
        if material.materialtype == "conductor":
          material.priority = 190 # priority smaller than metal layers
        else: 
          material.priority = 120 # priority higher than normal dieletric layers

        
        name_upstr = materialname.upper()
        no_MIM = (name_upstr.find('MIM') <0)
        
        # skip layers with "MIM" in the layer name, e.g. VMIM or MIM
        if no_MIM:
          via_layer = ADS_via_layer(materialname, material, gdslayer, zpos1, zpos2)
          material.used = True
          ADS_via_layers.append (via_layer) 
      else:
        print ("Could not find material definition for ", materialname)


    # process dielectric, set layer positions and names
    # We do this now, after metals, because some metals can expand the dielectric thickness
    ADS_dielectric_layers.process_dielectric_layers ()


    # get total stackup height 
    total_height_subst = ADS_dielectric_layers.get_total_stackup_height()
    print ("\ntotal_height_subst = ", str (total_height_subst-air_above), ' + ' , air_above, ' AIR ')
    
    # get height of semiconductors (for LBE)
    semi_height = ADS_dielectric_layers.get_semiconductor_height()
    print ("semiconductor height = " + str (semi_height))
    
    if is_IHP_substrate:
      if semi_height > 0:
        # add LBE on layer 157
        material = find_by_name (material_list, 'AIR')
        zpos1 = ADS_dielectric_layers.get_semiconductor_zmin()
        zpos2 = zpos1 + semi_height

        LBE_layer = ADS_via_layer('LBE', material, '157', zpos1, zpos2)
        ADS_via_layers.append (LBE_layer) 

    
    # ---------------------------- assign IHP colors if layer name matches list ----------------------
    
    if is_IHP_substrate:

      for metal in ADS_metal_layers.layers:
        IHP_color = color_from_layername(metal.layername, metal.material.display_color)
        if (IHP_color!=metal.material.display_color):
          metal.material.display_color=IHP_color
        
      for via in ADS_via_layers.layers:
        IHP_color = color_from_layername(via.layername, via.material.display_color)
        if (IHP_color!=via.material.display_color):
          via.material.display_color=IHP_color
      
      for dielectric in ADS_dielectric_layers.layers:
        IHP_color = color_from_layername(dielectric.layername, dielectric.material.display_color)
        if (IHP_color!=dielectric.material.display_color):
          dielectric.material.display_color=IHP_color

    
    # --------------- write out XML stackup file ---------------
    
    # This is created as strings, not using the XML writer, so that we can create the EXACT format
    XML_layer_file = ADS_substrate_filename.replace(".subst",".xml")
    print('\nWriting output file: ', XML_layer_file)
    
    file = open(XML_layer_file, "w")
    
    file.write ('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n')
    file.write ('  <Stackup schemaVersion="2.0">\n')

    # ---------- materials -----------

    file.write ('    <Materials>\n')
    
    # iterate over materials list
      
    for material in material_list:
      if material.used:  # only material definitions that are actually in use in final file
        file.write (str(material))
    
    file.write ('    </Materials>\n')
    file.write ('    <ELayers LengthUnit="um">\n')

    # ---------- Dielectrics -----------
    
    # We need a list of dielectric layers, from top to bottom. That is reverse order than *.subst, so reverse the lsit
    # But for internal processing, we need to go from bottom to top
    
      
    dielectrics_stringlist = []   # To revert the output order later, we have an intermediate list to hold the strings

    for dielectric in ADS_dielectric_layers.layers:
      dielectrics_stringlist.append (str(dielectric))
    

    file.write ('      <Dielectrics>\n')
    
    dielectrics_stringlist.reverse()
    for line in dielectrics_stringlist:
      file.write(line)

    file.write ('      </Dielectrics>\n')
    
    # ---------- Metals and Vias -----------
    
    
    for metal in ADS_metal_layers.layers:
      metal.zpos1 = metal.zpos1 - semi_height
      metal.zpos2 = metal.zpos2 - semi_height

    for via in ADS_via_layers.layers:
      via.zpos1 = via.zpos1 - semi_height
      via.zpos2 = via.zpos2 - semi_height
      
    
    # change via start position, so that it starts at top of metal and not at bottom
    for via in ADS_via_layers.layers:
      for metal in ADS_metal_layers.layers:
        if testequal(via.zpos1, metal.zpos1):
          via.zpos1 = via.zpos1 + metal.thickness
    
    
    file.write ('      <Layers>\n')
    file.write ('        <Substrate Offset="' + str(semi_height) + '"/>\n')
    
    for metal in ADS_metal_layers.layers:
      file.write(str(metal))

    for via in ADS_via_layers.layers:
      file.write(str(via))


    file.write ('      </Layers>\n')
    file.write ('    </ELayers>\n')
    file.write ('  </Stackup>\n\n')
    
    file.close()

  else:
    print('Input file ' + ADS_substrate_filename + ' not found')


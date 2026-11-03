# Read XML file with SG13G2 stackup

# File history: 
# Initial version 20 Nov 2024  Volker Muehlhaus 

import os
import xml.etree.ElementTree 


# -------------------- material types ---------------------------

class stackup_material:
  """
    stackup material object
  """
    
  def __init__ (self, data):
    self.name = data.get("Name")
    self.type = data.get("Type")
    self.eps  = float(data.get("Permittivity"))
    self.tand = float(data.get("DielectricLossTangent"))
    self.sigma = float(data.get("Conductivity"))
    self.color = data.get("Color")


  def __str__ (self):
    # string representation 
    mystr = '      Material Name=' + self.name + ' Type=' + self.type +' Permittivity=' + str(self.eps) + ' DielectricLossTangent=' +  str(self.tand) + ' Conductivity=' +  str(self.sigma)  + ' Color = ' + self.color
    return mystr



class stackup_materials_list:
  """
    list of stackup material objects
  """

  def __init__ (self):
    self.materials = []      # list with material objects
    self.eps_max   = 0
    
  def append (self, material):
    # append material
    self.materials.append (material)
    # set maximum permittivity in model
    self.eps_max = max(self.eps_max, material.eps)
  
  def get_by_name (self, materialname):  
    # find material object from materialname
    found = None
    for material in self.materials:
      if material.name == materialname:
        found = material
    return found    


# -------------------- dielectrics ---------------------------

class dielectric_layer:
  """
    dielectric layer object
  """
    
  def __init__ (self, data):
    self.name = data.get("Name")
    self.material = data.get("Material")
    self.thickness  = float(data.get("Thickness"))
    # z Position will be set later
    self.zmin = 0
    self.zmax = 0
    self.is_top = False
    self.is_bottom = False

  def __str__ (self):
    # string representation 
    mystr = '      Dielectric Name=' + self.name + ' Material=' + self.material +' Thickness=' + str(self.thickness) + ' Zmin=' +  str(self.zmin) + ' Zmax=' +  str(self.zmax)
    return mystr



class dielectric_layers_list:
  """
    list of dielectric layer objects
  """

  def __init__ (self):
    self.dielectrics = []      # list with dielectric objects
    
  def append (self, dielectric, materials_list ):
    self.dielectrics.append (dielectric)

  def calculate_zpositions (self):
    # dielectrics in XML are in reverse order, so we need to build position upside down
    z = 0
    for dielectric in reversed(self.dielectrics):
      t = float(dielectric.thickness)
      dielectric.zmin = z
      dielectric.zmax = z + t
      z = dielectric.zmax

  def get_by_name (self, name_to_find):  
    # find material object from materialname
    found = None
    for dielectric in self.dielectrics:
      if dielectric.name ==  name_to_find:
        found = dielectric
    return found    



# -------------------- conductor layers (metal and via) ---------------------------

class metal_layer:
  """
    metal layer object (metal or via)
  """
    
  def __init__ (self, data):
    self.name = data.get("Name")
    self.layernum = data.get("Layer")
    self.type = data.get("Type")
    self.material = data.get("Material")
    self.zmin = float(data.get("Zmin"))
    self.zmax = float(data.get("Zmax"))
    self.thickness = self.zmax-self.zmin
    self.is_via = (self.type=="via")
    self.is_metal = (self.type=="conductor")
    self.is_used = False

  def __str__ (self):
    # string representation 
    mystr = '      Metal Name=' + self.name + ' Layer=' + self.layernum + ' Type=' + self.type + ' Material=' + self.material + ' Zmin=' +  str(self.zmin) + ' Zmax=' +  str(self.zmax)
    return mystr
  



class metal_layers_list:
  """
    list of metal layer objects
  """


  def __init__ (self):
    self.metals = []      # list with conductor objects
    
  def append (self, metal):
    self.metals.append (metal)

  def getbylayernumber (self, number_to_find):
    # returns one metal by layer number, returns first match
    found = None
    for metal in self.metals:
      if metal.layernum == str(number_to_find):
        found = metal
        break 
    return found  

  def getallbylayernumber (self, number_to_find):
    # returns all metals by layer number as list, finds multiple metals mapped to same number
    found = []
    for metal in self.metals:
      if metal.layernum == str(number_to_find):
          found.append(metal)
    if found==[]:
      found = None
    return found  


  def getbylayername (self, name_to_find):
    found = None
    for metal in self.metals:
      if metal.name == str(name_to_find):
        found = metal
        break 
    return found  

  def getlayernumbers (self):  # list of all metal and via layer numbers in technology
    layernumbers = []
    for metal in self.metals:
      layernumbers.append(int(metal.layernum))
    return layernumbers 

  def add_offset (self, offset): # add offset in z position, used to add stackup height for final z position
    for metal in self.metals:
      metal.zmin = metal.zmin + offset
      metal.zmax = metal.zmax + offset



# ----------- parse substrate file, get materials from list created before -----------

def read_substrate (XML_filename):

  """
  Read XML substrate and return materials_list, dielectrics_list, metals_list.
  input value: filename
  """

  if os.path.isfile(XML_filename):  
    print('Reading XML stackup  file:', XML_filename)

    # data source is *.subst XML file
    substrate_tree = xml.etree.ElementTree.parse(XML_filename)
    substrate_root = substrate_tree.getroot()

    # get materials  from  XML
    materials_list = stackup_materials_list() # initialize empty list
    for data in  substrate_root.iter("Material"):
        materials_list.append (stackup_material(data))

    # get dielectric layers from  XML
    dielectrics_list = dielectric_layers_list() # initialize empty list
    for data in  substrate_root.iter("Dielectric"):
        dielectrics_list.append (dielectric_layer(data), materials_list)
    # mark top and bottom, order from XML is top material first
    dielectrics_list.dielectrics[0].is_top = True
    dielectrics_list.dielectrics[len(dielectrics_list.dielectrics)-1].is_bottom = True

    # calculate z positions in dielectric layers, after reading all of them
    dielectrics_list.calculate_zpositions()

    # get metal layers (metals + vias) from XML
    metals_list = metal_layers_list() # initialize empty list
    for data in  substrate_root.iter("Layer"):
        metals_list.append (metal_layer(data))

    # get substrate offset, required for v2 stackup file version
    offset = 0
    for data in substrate_root.iter("Substrate"):
        assert data!=None
        offset = float(data.get("Offset"))      
    if offset > 0:
      metals_list.add_offset(offset)

    return materials_list, dielectrics_list, metals_list
  
  else:
    print('XML stackup file not found: ', XML_filename)
    exit(1)
  # =========================== utilities ===========================



  # =======================================================================================
  # Test code when running as standalone script
  # =======================================================================================

if __name__ == "__main__":

  XML_filename = "SG13.xml"
  materials_list, dielectrics_list, metals_list = read_substrate (XML_filename)

  for material in materials_list.materials:
    print(material)

  for dielectric in dielectrics_list.dielectrics:
    print(dielectric)

  for metal in metals_list.metals:
    print(metal)

  print('__________________________________________')

  # test finding a layer by layer number
  metal = metals_list.getbylayernumber (134)
  print('Layer 134 name => ', metal.name)

  print('Layer 134 thickness => ', metals_list.getbylayernumber (134).thickness)
  print('Test if Layer 134 is a via layer => ', metals_list.getbylayernumber(134).is_via)

  # test finding a layer by name
  metal = metals_list.getbylayername ("TopMetal1")
  print('TopMetal1 layer number => ', metal.layernum)


 


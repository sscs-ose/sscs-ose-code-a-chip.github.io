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

# Extract objects from layers in GDSII file

__version__ = "1.1.0"

import gdspy
import numpy as np
import os

# check that we have gdspy version 1.6.x or later
# gdspy 1.4.2 is known for issues with our geometries

version_str = gdspy.__version__
major, minor, patch = version_str.split('.')
if int(major) == 1:
  if int(minor) < 6:
    print('\nERROR: Your gdspy module version ', version_str, ' is too old. Please update to 1.6.13 or later!')
    print('Consider using venv if you are not allowed to modify the global Python modules of your system.')
    print('https://docs.python.org/3/library/venv.html')
    exit(1)



# ============= technology specific stuff ===============


# ======================================

class layer_bounding_box:
  """
    bounding box class is used to store xmin, xmax, ymin, ymax for one layer.
    All instances of this are then managed by using all_bounding_box_list.
  """
  def __init__ (self, xmin, xmax, ymin, ymax):
    """Create layer_bounding_box instance for one layer from xmin, xmax, ymin, ymax
    Args:
        xmin (float): coordinate
        xmax (float): coordinate
        ymin (float): coordinate
        ymax (float): coordinate
    """
    self.xmin = xmin
    self.xmax = xmax
    self.ymin = ymin
    self.ymax = ymax

  def update (self, xmin, xmax, ymin, ymax):
    """Update layer_bounding_box instance for one layer from additional polygon data, store new total bounding box
    Args:
        xmin (float): coordinate
        xmax (float): coordinate
        ymin (float): coordinate
        ymax (float): coordinate
    """
    self.xmin = min(xmin, self.xmin)
    self.xmax = max(xmax, self.xmax)
    self.ymin = min(ymin, self.ymin)
    self.ymax = max(ymax, self.ymax)



class all_bounding_box_list:
  """
    stores bounding box instances for multiple layers
    and global bounding box across all layers
  """
  def __init__ (self):
    """_summary_
    """
    self.bounding_boxes = {}
    # initialize values for bounding box calculation
    self.xmin=float('inf')
    self.ymin=float('inf')
    self.xmax=float('-inf')
    self.ymax=float('-inf')

  def update (self, layer, xmin, xmax, ymin, ymax):
    """Update all_bounding_box_list instance with additional polygon data
    Args:
        layer(int): GDSII layer number
        xmin (float): coordinate
        xmax (float): coordinate
        ymin (float): coordinate
        ymax (float): coordinate
    """

    if self.bounding_boxes.get(layer) is not None:
      self.bounding_boxes[layer].update(xmin, xmax, ymin, ymax)
    else:
      self.bounding_boxes[layer] = layer_bounding_box(xmin, xmax, ymin, ymax)
    # also update global values
    self.xmin = min(self.xmin, xmin)   
    self.xmax = max(self.xmax, xmax)   
    self.ymin = min(self.ymin, ymin)   
    self.ymax = max(self.ymax, ymax)   

  def get_layer_bounding_box (self, layer):
    """Return bounding box of one specific layer.     If layer not found, return global bounding box.
    Args:
        layer (int): GDSII layer number
    Returns:
        xmin, xmax, ymin, ymax (float)
    """

    xmin = self.xmin 
    xmax = self.xmax
    ymin = self.ymin
    ymax = self.ymax
    if layer is not None:
      if self.bounding_boxes.get(layer) is not None:
        bbox = self.bounding_boxes[int(layer)]
        xmin = bbox.xmin 
        xmax = bbox.xmax
        ymin = bbox.ymin
        ymax = bbox.ymax
    return xmin, xmax, ymin, ymax  
  
  def merge (self, another_bounding_box_list):
    """Combine this bounding box with another bounding box from another GDSII import.
    Args:
        another_bounding_box_list (all_bounding_box_list): data from other import, can be discarded after merge 
    """

    # combine this bounding box with another bounding box from another GDSII import
    # combine the dictionaries with per-layer data
    self.bounding_boxes.update (another_bounding_box_list.bounding_boxes)
    # combine the overall total boundary
    self.xmin = min(self.xmin, another_bounding_box_list.xmin)
    self.xmax = max(self.xmax, another_bounding_box_list.xmax)
    self.ymin = min(self.ymin, another_bounding_box_list.ymin)
    self.ymax = max(self.ymax, another_bounding_box_list.ymax)


# ============= polygons ===============

class gds_polygon:
  """
    gds polygon object
  """
  
  def __init__ (self, layernum):
    """Initialize  polygon with empty vertex list, store layer number
    Args:
        layernum (int): GDSII layer number
    """
    self.pts_x = np.array([])
    self.pts_y = np.array([])
    self.pts   = np.array([])
    self.layernum = layernum
    self.is_port = False
    self.is_via = False
    self.CSXpoly = None
    
  def add_vertex (self, x,y):
    """Add one point (vertex) to the polygon
    Args:
        x (float): point x
        y (float): point y
    """
    self.pts_x = np.append(self.pts_x, x)
    self.pts_y = np.append(self.pts_y, y)

  def process_pts (self):
    """Process and update all points, update bounding box data fields
    """
    self.pts = [self.pts_x, self.pts_y]
    self.xmin = np.min(self.pts_x)
    self.xmax = np.max(self.pts_x)
    self.ymin = np.min(self.pts_y)
    self.ymax = np.max(self.pts_y)

  def __str__ (self):
    """Create string representation of polygon data, useful for debugging
    Returns:
        string: string representation of polygon data
    """
    # string representation 
    mystr = 'Layer = ' + str(self.layernum) + ', Polygon = ' + str(self.pts) + ', Via = ' + str(self.is_via)
    return mystr


class all_polygons_list:
  """
  Class instance holds all polygon data (all polygons with their layer data etc)
  """

  def __init__ (self):
    """Initialize empty list of polygons and empty bounding box dictionary
    """
    self.polygons = []
    self.bounding_box = all_bounding_box_list() # manages bounding box per layer and global

  def append (self, poly):
    """Append one instance of gds_polygon
    Args:
        poly (gds_polygon): Data for one single polygon
    """
    # before we append, combine points in polygon from pts_x and pts_y into pts
    poly.process_pts()
    # add polygon to list
    self.polygons.append (poly)

  def add_rectangle (self, x1,y1,x2,y2, layernum, is_port=False, is_via=False):
    """This function adds a rectangle, it can be called in code created manually. Not used in GDSII import.

    Args:
        x1 (float): point 1 x
        y1 (float): point 1 y
        x2 (float): point 2 x
        y2 (float): point 2 y
        layernum (int): layer number assigned to this rectangle
        is_port (bool, optional): Treat as port polygon. Defaults to False.
        is_via (bool, optional): Treat as via polygon. Defaults to False.
    """
    # append simple rectangle to list, this can also be done later, after reading GDSII file
    poly = gds_polygon(layernum)
    poly.add_vertex(x1,y1)
    poly.add_vertex(x1,y2)
    poly.add_vertex(x2,y2)
    poly.add_vertex(x2,y1)
    poly.is_port = is_port
    poly.is_via = is_via
    self.append(poly)

    # need to update min and max here, for gds data that is done after reading file
    self.bounding_box.update (layernum, min(x1,x2), max(x1,x2),min(y1,y2),max(y1,y2))


  def add_polygon (self, xy, layernum, is_port=False, is_via=False):
    """This function adds a polygon, it can be called in code created manually. Not used in GDSII import.
    Polygon data structure must be [[x1,y1],[x2,y2],...[xn,yn]]

    Args:
        xy (list of [x,y]): polygon points
        layernum (int): layer number assigned to this polygon
        is_port (bool, optional): Treat as port polygon. Defaults to False.
        is_via (bool, optional): Treat as via polygon. Defaults to False.
    """
    # append polygon array to list, this can also be done later, after reading GDSII file
    # polygon data structure must be [[x1,y1],[x2,y2],...[xn,yn]]
    xmin=float('inf')
    ymin=float('inf')
    xmax=float('-inf')
    ymax=float('-inf')

    poly = gds_polygon(layernum)
    numpts = len(xy)
    for pt in range(0, numpts):
      pt = xy[pt]
      x = pt[0]
      y = pt[1]
      poly.add_vertex(x,y)
      # need to update min and max here, for gds data that is done after reading file
      xmin = min(xmin, x)
      xmax = max(xmax, x)
      ymin = min(ymin, y)
      ymax = max(ymax, y)      
    # need to update min and max here, for gds data that is done after reading file
    self.bounding_box.update (layernum, xmin, xmax, ymin, ymax)
    self.append(poly)        


  def set_bounding_box (self, xmin,xmax,ymin,ymax):
    """Set the global bounding box, over all evaluated layers, to these values. No checks, force these values.

    Args:
        xmin (float): coordinate
        xmax (float): coordinate
        ymin (float): coordinate
        ymax (float): coordinate
    """
    # global bounding box, over all evaluated layers
    self.bounding_box.xmin = xmin
    self.bounding_box.xmax = xmax
    self.bounding_box.ymin = ymin
    self.bounding_box.ymax = ymax


  def get_layer_bounding_box (self, layer):
    """Return bounding box for specific layer, returns global if layer not found
    Args:
        layer (int): layer number assigned to this polygon
    Returns:
        xmin, xmax, ymin, ymax (float)
    """
    return self.bounding_box.get_layer_bounding_box (layer)


  def get_bounding_box (self):
    """return global bounding box
    Returns:
        xmin, xmax, ymin, ymax (float)
    """
    return self.bounding_box.xmin, self.bounding_box.xmax, self.bounding_box.ymin, self.bounding_box.ymax 
 

  def get_xmin (self):
    # return global bounding box
    return self.bounding_box.xmin

  def get_xmax (self):
    # return global bounding box
    return self.bounding_box.xmax

  def get_ymin (self):
    # return global bounding box
    return self.bounding_box.ymin

  def get_ymax (self):
    # return global bounding box
    return self.bounding_box.ymax
  

  def merge (self, another_polygons_list):
    """merge with another polygon list from another GDSII import
    Args:
        another_polygons_list (all_polygons_list): another polygon list, maybe from another GDSII import
    """
    
    for polygon in another_polygons_list.polygons:
      self.polygons.append(polygon)
    # also merge boundary information  
    self.bounding_box.merge(another_polygons_list.bounding_box)          


# ---------------------- via merging option --------------------



def _store_layer_polygons (all_polygons, layerpolygons, target_layer):
  """Convert raw gdspy polygon point arrays for one layer into gds_polygon objects,
  append them to all_polygons and update its per-layer bounding box.

  Args:
      all_polygons (all_polygons_list): running result, updated in place
      layerpolygons (list of ndarray): raw gdspy polygon point arrays for this layer
      target_layer (int): layer number (offset already applied) to tag these polygons with
  """

  xmin=float('inf')
  ymin=float('inf')
  xmax=float('-inf')
  ymax=float('-inf')

  # Issue warning when very many polygons on layer
  numpoly = len(layerpolygons)
  if numpoly > 200:
    print(f'Layer {target_layer} has {numpoly} polygons')
    print(' ==> Consider via array merging by setting merge_polygon_size > 0')

  # iterate over layer polygons
  for polypoints in layerpolygons:

    numvertices = int(polypoints.size/polypoints.ndim)

    # new polygon, store layer number information
    new_poly = gds_polygon(target_layer)

    # get vertices
    for vertex in range(numvertices):
      x = polypoints[vertex,0]
      y = polypoints[vertex,1]

      new_poly.add_vertex(x,y)

      # update bounding box information
      xmin = min(x,xmin)
      xmax = max(x,xmax)
      ymin = min(y,ymin)
      ymax = max(y,ymax)

    # polygon is complete, process and add to list
    all_polygons.append(new_poly)

  # done with this layer, store bounding box for this layer
  if numpoly > 0:
    all_polygons.bounding_box.update(target_layer, xmin, xmax, ymin, ymax)


def resolve_derived_layers (cell, derived_layers, layerlist, purposelist, layer_polygons_gds, layernumber_offset, all_polygons):
  """Compute derived layers (boolean operations on other layers) and add requested ones to all_polygons.

  Derived layers are processed in dependency order (a derived layer that uses another derived
  layer as operand is computed after that operand). Operand layers that were not already
  extracted as part of the requested layerlist are pulled from the GDSII cell on demand, so
  operands do not need to be requested individually. If a derived layer has a non-zero
  Oversize, the boolean result (or, with a single operand, that operand as-is) is grown
  (positive) or shrunk (negative) by that distance before being cached/stored.

  Args:
      cell (gdspy.Cell): flattened top level cell being processed
      derived_layers (derived_layers_list): derived layer definitions from util_stackup_reader
      layerlist (list of int): layer numbers explicitly requested for output
      purposelist (list of int): GDSII data types (purposes) to be processed
      layer_polygons_gds (dict): {layer_num: list of ndarray} cache of raw gdspy polygons per
          layer, already populated for natively-extracted layers, updated in place with results
      layernumber_offset (int): offset applied to GDSII layer numbers, same as in read_gds
      all_polygons (all_polygons_list): running result, updated in place for requested derived layers
  """

  # by_spec polygon lookup, used to pull operand layers that were not part of layerlist
  LPPpolylist = cell.get_polygons(by_spec=True, depth=0)

  def get_layer_polygons (layernum):
    # already extracted (native layer from main loop, or previously computed derived layer)
    if layernum in layer_polygons_gds:
      return layer_polygons_gds[layernum]

    # not yet extracted: treat as native GDSII layer and pull it on demand
    layer_gds = layernum - layernumber_offset
    found_polygons = []
    for LPP in LPPpolylist:
      layer = LPP[0]
      purpose = LPP[1]
      if (layer == layer_gds) and (purpose in purposelist):
        found_polygons.extend(LPPpolylist[(layer, purpose)])

    layer_polygons_gds[layernum] = found_polygons
    return found_polygons

  for derived in derived_layers.get_ordered():

    target_layer = int(derived.layernum)
    operation = 'not' if derived.operation == 'NOT' else derived.operation.lower()

    operand_polygons = [get_layer_polygons(int(op)) for op in derived.operands]

    # fold operands pairwise: (op1 <operation> op2) <operation> op3 ...
    result = operand_polygons[0]
    for next_operand in operand_polygons[1:]:
      boolean_result = gdspy.boolean(result, next_operand, operation, max_points=199)
      result = boolean_result.polygons if boolean_result is not None else []

    # optionally grow (positive) or shrink (negative) the outline of the result
    if derived.oversize != 0 and len(result) > 0:
      offset_result = gdspy.offset(result, derived.oversize, join='miter', tolerance=2, precision=0.001, join_first=False, max_points=199)
      result = offset_result.polygons

    # cache result so later derived layers can use this derived layer as an operand
    layer_polygons_gds[target_layer] = result

    # only add to output if this derived layer was actually requested
    if target_layer in layerlist:
      _store_layer_polygons(all_polygons, result, target_layer)


def merge_via_array (polygons, maxspacing):
  """Used internally in processing data from gdspy, does not work on our own all_polygons_list class!

  Args:
      polygons (_type_): LPPpolylist data
      maxspacing (float): offset for oversize/undersize of polygons during via array merge

  Returns:
      _type_: LPPpolylist data
  """

  # Via array merging consists of 3 steps: oversize, merge, undersize
  # Value for oversize depends on via layer
  # Oversized vias touch if each via is oversized by half spacing
  
  offset = maxspacing/2 + 0.01
  
  offsetpolygonset=gdspy.offset(polygons, offset, join='miter', tolerance=2, precision=0.001, join_first=False, max_points=199)
  mergedpolygonset=gdspy.boolean(offsetpolygonset, None,"or", max_points=199)
  mergedpolygonset=gdspy.offset(mergedpolygonset, -offset, join='miter', tolerance=2, precision=0.001, join_first=False, max_points=199)
  
  # offset and boolean return PolygonSet, we only need the list of polygons from that
  return mergedpolygonset.polygons 



# ----------- read GDSII file, return openEMS polygon list object -----------

def read_gds(filename, layerlist, purposelist, metals_list, preprocess=False, merge_polygon_size=0, mirror=False, offset_x=0, offset_y=0, gds_boundary_layers=[], layernumber_offset=0, cellname="", derived_layers=None):
  """
  Read GDSII file and return polygon list object.

  Args:
      filename (str): Input filename.
      layerlist (list of int): List of layer numbers to be processed.
      purposelist (list of int): List of GDSII data types to be processed.
      metals_list (metal_layers_list): Instance of class `metal_layers_list` defined in `util_stackup_reader`.
      preprocess (bool, optional): Enable GDSII geometry preprocessing. Defaults to False.
      merge_polygon_size (float, optional): Enable via array merging when value is > 0.
      mirror (bool, optional): Mirror the geometry about the y-axis. Defaults to False.
      offset_x (float, optional): Geometry offset in x direction. Defaults to 0.
      offset_y (float, optional): Geometry offset in y direction. Defaults to 0.
      gds_boundary_layers (list of int, optional): List of extra layers to evaluate for finite dielectric size. Defaults to [].
      layernumber_offset (int, optional): Optional offset applied to GDSII layer numbers to avoid duplicates when reading multiple files. Defaults to 0.
      derived_layers (derived_layers_list, optional): Derived layer definitions (boolean operations on
          other layers) from `util_stackup_reader`. Defaults to None, in which case metals_list.derived_layers
          is used if present (set automatically by read_substrate() when the XML has a DerivedLayers section).

  Returns:
      all_polygons_list: All polygon information data.
  """

  if derived_layers is None:
    derived_layers = getattr(metals_list, 'derived_layers', None)

  if os.path.isfile(filename):
    print('Reading GDSII input file:', filename)
  
    input_library = gdspy.GdsLibrary(infile=filename)

    if preprocess: 
      # obsolete, cutouts are handles safely downstream after flattening
      print('Ignoring obsolete pre-processing setting, no longer required')

    # evaluate only first top level cell
    toplevel_cell_list = input_library.top_level()
    
    # try to get cell named cellname, otherwise top level cell
    cell = input_library.cells.get(cellname, toplevel_cell_list[0])
    
    all_polygons = all_polygons_list()

    # cache of raw gdspy polygon arrays per layer number (offset applied), used to compute derived layers
    layer_polygons_gds = {}

    # flatten hierarchy below this cell
    cell.flatten(single_layer=None, single_datatype=None, single_texttype=None)

    # optional mirror and translation of entire cell
    for poly in cell.polygons:
      if mirror:
        # optional mirror
        poly = poly.mirror(p1=[0,0],p2=[0,1])
      if (offset_x != 0) or (offset_y != 0):
        # optional translation after mirror
        poly = poly.translate(offset_x, offset_y)


    # iterate over XML technology metal layers and (optional) dielectric layer boundary spec
    extended_layer_list = layerlist
    extended_layer_list.extend(gds_boundary_layers)

    for layer_to_extract in extended_layer_list:
      
      # print ("Evaluating layer ", str(layer_to_extract))

      # get layers used in cell
      used_layers = cell.get_layers()

      # Note on layer numbers:
      # Used layer is the layer base number, layer_to_extract has the layer number offset from XML
      # For this file, the layernumber_offset applies ALWAYS

      # check if layer-to-extract is used in cell 
      layer_to_extract_gds = layer_to_extract - layernumber_offset
      if (layer_to_extract_gds in used_layers):  # use base layer number here to match GDSII
              
        # iterate over layer-purpose pairs (by_spec=true)
        # do not descend into cell references (depth=0)
        LPPpolylist = cell.get_polygons(by_spec=True, depth=0)

        for LPP in LPPpolylist:
          layer = LPP[0]   
          purpose = LPP[1]
          
          # now get polygons for this one layer-purpose-pair
          if (layer==layer_to_extract_gds) and (purpose in purposelist):
            layerpolygons = LPPpolylist[(layer, purpose)]

            # optional via array merging, only for via layers
            metal = metals_list.getbylayernumber(layer_to_extract) # this is the layer number with offset, to match XML stackup
            if metal != None:
              if (merge_polygon_size>0) and metal.is_via:
                layerpolygons = merge_via_array (layerpolygons, merge_polygon_size)

            # cache raw polygons for this layer, so derived layers can use it as an operand
            layer_polygons_gds[layer + layernumber_offset] = layerpolygons

            _store_layer_polygons(all_polygons, layerpolygons, layer + layernumber_offset)

    # ----------- derived layers: boolean operations on other layers -----------
    if derived_layers is not None and len(derived_layers.derived_layers) > 0:
      resolve_derived_layers(cell, derived_layers, layerlist, purposelist, layer_polygons_gds, layernumber_offset, all_polygons)

    '''
    # Re-evaluate bounding box if we have a bounding box specified in GDS file and evaluation is requested
    if gds_boundary is not None:
      spec = gds_boundary.split(":")
      boundary_layer = int(spec[0])
      if len(spec)>1:
        # user has specified purpose explicitely
        boundary_purpose_list = [int(spec[1])]
      else:  
        # use global purpose list
        boundary_purpose_list = purposelist

      # get layers used in cell
      used_layers = cell.get_layers()

      # check if layer-to-extract is used in cell 
      if (boundary_layer in used_layers):
        # reset previous bounding box and start all over again
        xmin=float('inf')
        ymin=float('inf')
        xmax=float('-inf')
        ymax=float('-inf')
              
        # iterate over layer-purpose pairs (by_spec=true)
        # do not descend into cell references (depth=0)
        LPPpolylist = cell.get_polygons(by_spec=True, depth=0)
        for LPP in LPPpolylist:
          layer = LPP[0]
          purpose = LPP[1]
          
          # now get polygons for this one layer-purpose-pair
          if (layer==boundary_layer) and (purpose in boundary_purpose_list):
            layerpolygons = LPPpolylist[(layer, purpose)]
           
            # iterate over layer polygons
            for polypoints in layerpolygons:
              numvertices = int(polypoints.size/polypoints.ndim)

              # get vertices
              for vertex in range(numvertices):
                x = polypoints[vertex,0]
                y = polypoints[vertex,1]
                
                # update bounding box information
                if x<xmin: xmin=x
                if x>xmax: xmax=x
                if y<ymin: ymin=y
                if y>ymax: ymax=y
    '''


    # all_polygons.set_bounding_box (xmin,xmax,ymin,ymax)
    
    # done!
    return all_polygons
  
  else:
    print('GDSII input file not found: ', filename)
    exit()
 



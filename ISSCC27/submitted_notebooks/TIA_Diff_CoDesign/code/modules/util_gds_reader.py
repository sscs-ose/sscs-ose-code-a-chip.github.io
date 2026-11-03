# Extract objects on IHP layers in GDSII file

import gdspy
import numpy as np
import os
import util_stackup_reader as stackup_reader


# ============= technology specific stuff ===============


# ============= polygons ===============

class gds_polygon:
  """
    gds polygon object
  """
  
  def __init__ (self, layernum):
    self.pts_x = np.array([])
    self.pts_y = np.array([])
    self.pts   = np.array([])
    self.layernum = layernum
    self.is_port = False
    self.is_via = False
    self.CSXpoly = None
    
  def add_vertex (self, x,y):
    self.pts_x = np.append(self.pts_x, x)
    self.pts_y = np.append(self.pts_y, y)

  def process_pts (self):
    self.pts = [self.pts_x, self.pts_y]
    self.xmin = np.min(self.pts_x)
    self.xmax = np.max(self.pts_x)
    self.ymin = np.min(self.pts_y)
    self.ymax = np.max(self.pts_y)

  def __str__ (self):
    # string representation 
    mystr = 'Layer = ' + str(self.layernum) + ', Polygon = ' + str(self.pts) + ', Via = ' + str(self.is_via)
    return mystr


class all_polygons_list:
  """
    list of gds polygon objects
  """

  def __init__ (self):
    self.polygons = []
    self.xmin = 0
    self.xmax = 0
    self.ymin = 0
    self.ymax = 0

  def append (self, poly):
    # combine points in polygon from pts_x and pts_y into pts
    poly.process_pts()
    # add polygon to list
    self.polygons.append (poly)

  def add_rectangle (self, x1,y1,x2,y2, layernum, is_port=False, is_via=False):
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
    self.xmin = min(self.xmin, x1, x2)
    self.xmax = max(self.xmax, x1, x2)
    self.ymin = min(self.ymin, y1, y2)
    self.ymax = max(self.ymax, y1, y2)

  def add_polygon (self, xy, layernum, is_port=False, is_via=False):
    # append polygon array to list, this can also be done later, after reading GDSII file
    # polygon data structure must be [[x1,y1],[x2,y2],...[xn,yn]]
    poly = gds_polygon(layernum)
    numpts = len(xy)
    for pt in range(0, numpts):
      pt = xy[pt]
      x = pt[0]
      y = pt[1]
      poly.add_vertex(x,y)
      # need to update min and max here, for gds data that is done after reading file
      self.xmin = min(self.xmin, x)
      self.xmax = max(self.xmax, x)
      self.ymin = min(self.ymin, y)
      self.ymax = max(self.ymax, y)      
    self.append(poly)        

    


  def set_bounding_box (self, xmin,xmax,ymin,ymax):
    self.xmin = xmin
    self.xmax = xmax
    self.ymin = ymin
    self.ymax = ymax

  def get_bounding_box (self):
    return self.xmin, self.xmax, self.ymin, self.ymax 


# ---------------------- via merging option --------------------



def merge_via_array (polygons, maxspacing):
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

def read_gds(filename, layerlist, purposelist, metals_list, preprocess=False, merge_polygon_size=0 ):

  """
  Read GDSII file and return polygon list object
  input value: filename
  """
  if os.path.isfile(filename):
    print('Reading GDSII input file:', filename)
  
    input_library = gdspy.GdsLibrary(infile=filename)

    if preprocess: 
      print('Pre-processing GDSII to handle cutouts and self-intersecting polygons')
      # iterate over cells
      for cell in input_library:
        
        # iterate over polygons
        for poly in cell.polygons:
          
          # points of this polygon
          polypoints = poly.polygons[0]

          poly_layer = poly.layers[0]
          poly_purpose = poly.datatypes[0]

          if ((poly_layer in layerlist) and (poly_purpose in purposelist)):
          
            # get number of vertices
            numvertices = len(polypoints) 
            
            seen   = set()    # already seen vertex values
            dupefound = False

            # iterate over vertices to find duplicates
            for i_vertex in range(numvertices):
              
              # print('polypoints  = ' + str(polypoints))
              x = polypoints[i_vertex][0]
              y = polypoints[i_vertex][1]
              
              # create string representation so that we can check for duplicates
              vertex_string = str(x)+','+str(y)
              if vertex_string in seen:
                dupefound = True
                # print('      found duplicate at vertex ' + str(i_vertex) + ': ' + vertex_string)
              else:
                seen.add(vertex_string)  

            if dupefound:
                          
              # do the slicing
              
              # convert polygon to format required for slicing
              basepoly_points = []

              for i_vertex in range(numvertices):
                basepoly_points.append((polypoints[i_vertex,0], polypoints[i_vertex,1]))

              # create new polygon
              basepoly = gdspy.Polygon(basepoly_points, layer=poly_layer, datatype=poly_purpose)  
              fractured = basepoly.fracture(max_points=6)

              # add fractured polygon to cell
              cell.add(fractured)

              # invalidate original polygon
              poly.layers=[0]
              # remove original polygon
              cell.remove_polygons(lambda pts, layer, datatype:
                layer == 0)
    
    # end preprocessing


    # evaluate only first top level cell
    toplevel_cell_list = input_library.top_level()
    cell = toplevel_cell_list[0]

    all_polygons = all_polygons_list()

    # initialize values for bounding box calculation
    xmin=float('inf')
    ymin=float('inf')
    xmax=float('-inf')
    ymax=float('-inf')
      
    # iterate over IHP technology layers
    for layer_to_extract in layerlist:
      
      # print ("Evaluating layer ", str(layer_to_extract))
      # flatten hierarchy below this cell
      cell.flatten(single_layer=None, single_datatype=None, single_texttype=None)
      
      # get layers used in cell
      used_layers = cell.get_layers()
      
      # check if layer-to-extract is used in cell 
      if (layer_to_extract in used_layers):
              
        # iterate over layer-purpose pairs (by_spec=true)
        # do not descend into cell references (depth=0)
        LPPpolylist = cell.get_polygons(by_spec=True, depth=0)
        for LPP in LPPpolylist:
          layer = LPP[0]
          purpose = LPP[1]
          
          # now get polygons for this one layer-purpose-pair
          if (layer==layer_to_extract) and (purpose in purposelist):
            layerpolygons = LPPpolylist[(layer, purpose)]

            # optional via array merging, only for via layers
            metal = metals_list.getbylayernumber(layer_to_extract)
            if metal != None:
              if (merge_polygon_size>0) and metal.is_via:
                layerpolygons = merge_via_array (layerpolygons, merge_polygon_size)
            
            # iterate over layer polygons
            for polypoints in layerpolygons:

              numvertices = int(polypoints.size/polypoints.ndim)

              # new polygon, store layer number information
              new_poly = gds_polygon(layer)

              # get vertices
              for vertex in range(numvertices):
                x = polypoints[vertex,0]
                y = polypoints[vertex,1]

                new_poly.add_vertex(x,y)
                
                # update bounding box information
                if x<xmin: xmin=x
                if x>xmax: xmax=x
                if y<ymin: ymin=y
                if y>ymax: ymax=y
              
              # polygon is complete, process and add to list
              all_polygons.append(new_poly)

    all_polygons.set_bounding_box (xmin,xmax,ymin,ymax)
    
          
      
    # done!
    return all_polygons
  
  else:
    print('GDSII input file not found: ', filename)
    exit()
 


# =======================================================================================
# Test code when running as standalone script
# =======================================================================================

if __name__ == "__main__":

  filename = "L_2n0_simplified.gds"
  allpolygons = read_gds(filename,[134, 133, 126, 8],[0], None)  # read layers 134,133,126, 8 with purpose 0
  for poly in allpolygons.polygons:
    print(poly)

  print("Bounding box: " + str(allpolygons.xmin) + " " + str(allpolygons.xmax) + " " + str(allpolygons.ymin) + " " + str(allpolygons.ymax))
  

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

# create mesh lines for metals and dielectrics

import math
import numpy as np


def get_margins (margin):
    """get margins at xmin,xmax,ymin,ymax from user specified data (single value or list)

    Args:
        margin (float or list): single value for equal margings or list for xmin,xmax,ymin,ymax
        Return value: margin at xmin,xmax,ymin,ymax
    """
    # air_around can be specified as single value or array, check what we have here
    if isinstance(margin, list):
        if len(margin)==4:
            margin_xmin = margin[0]
            margin_xmax = margin[1]
            margin_ymin = margin[2]
            margin_ymax = margin[3]
        else:
            print('Error: expected margin to be a single value or a list of 4 values:')
            print('[margin_xmin, margin_xmax, margin_ymin, margin_ymax]')
            print('but instead we have this: ', str(margin))    
            exit(1)
    else:
        # all the same
        margin_xmin = margin_xmax = margin_ymin = margin_ymax = margin

    return margin_xmin, margin_xmax, margin_ymin, margin_ymax


def create_z_mesh(mesh, dielectrics_list, metals_list, target_cellsize, max_cellsize, antenna_margin, exclude_list):

    class mesh_stackup_layer:
        # dielectric layer for meshing control

        def __init__ (self, dielectric):
            self.dielectric = dielectric
            self.metal_inside = False
            self.meshsize_top = 0
            self.meshsize_bottom = 0
            self.mesh_done = False

    class mesh_stackup_layers:
        # all dielectric layer for meshing control

        def __init__ (self):
            self.stackup_layers = []
            # first, add all stackup, which also tags layers with metal mesh inside
            for dielectric in dielectrics_list.dielectrics:
                self.stackup_layers.append(mesh_stackup_layer(dielectric))
            # next, set the neighbours of metal layers to the target meshsize as starting value
            for i, stackup_layer in enumerate(self.stackup_layers):
                if stackup_layer.metal_inside:
                    if not stackup_layer.dielectric.is_top:
                        above = self.stackup_layers[i+1]
                        above.meshsize_bottom = target_cellsize
                    elif not stackup_layer.dielectric.is_bottom:
                        below = self.stackup_layers[i-1]
                        below.meshsize_bottom = target_cellsize
                

        def append (self, stackup_layer):
            self.stackup_layers.append (stackup_layer)

            # check for metal inside
            for metal in metals_list.metals:
                # metals from the exclude list are not meshed like other metals, so skip them here
                if metal.name not in exclude_list:
                    # only metal layers with polygons or vias are meshed
                    if metal.is_used or metal.is_via:
                        # if this is inside our dielectric, mark as metal_inside
                        # Note: this only detects metals fully encloded by the dielectric
                        if (metal.zmin > stackup_layer.dielectric.zmin) and (metal.zmax < stackup_layer.dielectric.zmax):
                            stackup_layer.metal_inside = True
                            stackup_layer.meshsize_top = target_cellsize
                            stackup_layer.meshsize_bottom = target_cellsize



    
    for metal in metals_list.metals:
        if metal.name not in exclude_list:
            # print('Checking metal layer ', metal.name, ' used:', str(metal.is_used), ' via:', str(metal.is_via))
            if metal.is_used:
                if not  metal.is_via:
                    metal_thickness = metal.zmax-metal.zmin
                    if metal_thickness > 3*target_cellsize:
                        # for thick metals, we just place mesh lines at top and bottom, and let smoothing do the filling
                        mesh.AddLine('z', metal.zmin)
                        mesh.AddLine('z', metal.zmin + target_cellsize)
                        mesh.AddLine('z', metal.zmax)
                        mesh.AddLine('z', metal.zmax - target_cellsize)
                    else:    
                        target_cellsize_z = min(target_cellsize, metal_thickness)
                        add_equal_meshlines(mesh, 'z', metal.zmin, metal.zmax, target_cellsize_z)
                else:
                    # via     
                    mesh.AddLine('z', metal.zmin)
                    mesh.AddLine('z', metal.zmax)

    
    # mesh dielectric layers

    stackup_layers = mesh_stackup_layers()
    # note: 
    # metal layers are already when creating mesh_stackup_layers()
    # and for adjacent dielectrics, mesh size is set boundary 
    
    for i, stackup_layer in enumerate(stackup_layers.stackup_layers):
        zmax = stackup_layer.dielectric.zmax
        zmin = stackup_layer.dielectric.zmin
        target_cellsize_z = min(target_cellsize, zmax-zmin)            

        if not stackup_layer.metal_inside:
            # check if we have extra margins for antenna simulation, then we push out the top and bottom boundary
            if stackup_layer.dielectric.is_top:
                # zmax = max(stackup_layer.dielectric.zmax, stackup_layer.dielectric.zmin + antenna_margin)
                zmax = zmax + antenna_margin
            elif stackup_layer.dielectric.is_bottom:
                zmin = zmin - antenna_margin

            # place mesh line at interface    
            mesh.AddLine('z', zmin)
            mesh.AddLine('z', zmax)
            if stackup_layer.meshsize_bottom > 0:
                mesh.AddLine('z', zmin+stackup_layer.meshsize_bottom)
            if stackup_layer.meshsize_top > 0:
                mesh.AddLine('z', zmin+stackup_layer.meshsize_top)



    # check for possible gaps
    def add_missing_lines (direction):
        lines = mesh.GetLines(direction, do_sort=True)
       
        added_something = False
        for index in range(1, len(lines)-1):
            previous_line = lines[index-1]
            this_line = lines[index]
            next_line = lines[index+1]
            previous_dist = this_line-previous_line
            this_dist = next_line-this_line

            ratio = this_dist/previous_dist
            if ratio > 3:
                point = (this_line + this_dist/2)
                mesh.AddLine(direction, point)
                added_something = True
            elif ratio < 1/3:
                point = (this_line - previous_dist/2)
                mesh.AddLine(direction, point)
                added_something = True

        return added_something


    check_z = True
    while check_z:
        check_z = add_missing_lines('z')
    
    # add mesh line at bottom of stackup at z=0
    mesh.AddLine('z', 0.0)

    mesh.SmoothMeshLines('z', max_cellsize, 1.3)
    
    return mesh


def create_standard_xy_mesh(mesh, allpolygons, margin, antenna_margin, target_cellsize, max_cellsize):

    margin_xmin, margin_xmax, margin_ymin, margin_ymax  = get_margins (margin)
    
   
    # geometry region
    add_equal_meshlines(mesh, 'x', allpolygons.get_xmin(), allpolygons.get_xmax(), target_cellsize)
    add_equal_meshlines(mesh, 'y', allpolygons.get_ymin(), allpolygons.get_ymax(), target_cellsize)

    # margins
    add_graded_meshlines (mesh, 'x', allpolygons.get_xmin(), allpolygons.get_xmin() - (margin_xmin+antenna_margin), -1.5*target_cellsize, 1.3, -max_cellsize)
    add_graded_meshlines (mesh, 'x', allpolygons.get_xmax(), allpolygons.get_xmax() + (margin_xmax+antenna_margin),  1.5*target_cellsize, 1.3,  max_cellsize)    
    
    add_graded_meshlines (mesh, 'y', allpolygons.get_ymin(), allpolygons.get_ymin() - (margin_ymin+antenna_margin), -1.5*target_cellsize, 1.3, -max_cellsize)
    add_graded_meshlines (mesh, 'y', allpolygons.get_ymax(), allpolygons.get_ymax() + (margin_ymax+antenna_margin),  1.5*target_cellsize, 1.3,  max_cellsize)    
    
    return mesh


def create_xy_mesh_from_polygons (mesh, allpolygons, margin, antenna_margin, target_cellsize, max_cellsize):
    
    class weighted_meshline:  
        def __init__ (self, value, weight):
            self.value = value
            self.weight = weight

    class all_weighted_meshlines: 
        # list of weighted meshlines
        def __init__ (self):
            self.meshlines = []

        def addPolyEdge (self, value):
            self.meshlines.append (weighted_meshline(value, 10))    

        def addViaEdge (self, value):
            self.meshlines.append (weighted_meshline(value, 5))    # lower priority in meshing, might move outline if necessary

        def addFill (self, value):
            self.meshlines.append (weighted_meshline(value, 1))    # lowest priority in meshing, might move outline if necessary

        def addPortEdge (self, value):
            self.meshlines.append (weighted_meshline(value, 20))   # higest priority

        def sort(self):
            # function to get value for sorting
            def getvalue(item):
                return (item.value)
            # sort by value, increasing order
            self.meshlines = sorted(self.meshlines, key=getvalue)

        def remove_duplicates(self):
            no_dupe_list = []
            values = []
            for line in self.meshlines:
                if line.value not in values:
                    no_dupe_list.append(line) 
                    values.append(line.value)
                else:
                    # we already have this value, but possibly with different weight
                    # keep the higher weight
                    i = values.index(line.value) 
                    existing = no_dupe_list[i]
                    existing.weight = max(line.weight,existing.weight)
            self.meshlines = no_dupe_list     

        def getLines(self):
            # remove duplicate entries
            self.remove_duplicates()
            # return lines in a format that we can use for openEMS mesh.addLine  
            values = []
            for line in self.meshlines:
                values.append(line.value)
            return np.array(values)    

        def addFillRange (self, start, stop, target_cellsize):
            n = int(abs((math.ceil((stop-start)/target_cellsize)+1)))
            points = np.linspace(start, stop, n)
            for value in points.tolist():
                self.addFill(value)    


    # initialize our own list of meshlines, do not yet store them to CSX
    weighted_meshlines_x = all_weighted_meshlines()
    weighted_meshlines_y = all_weighted_meshlines()

    # outer simulation boundary
    
    margin_xmin, margin_xmax, margin_ymin, margin_ymax  = get_margins (margin)

    weighted_meshlines_x.addPolyEdge(allpolygons.get_xmin() - margin_xmin)
    weighted_meshlines_x.addPolyEdge(allpolygons.get_xmax() + margin_xmax)
    weighted_meshlines_y.addPolyEdge(allpolygons.get_ymin() - margin_ymin)
    weighted_meshlines_y.addPolyEdge(allpolygons.get_ymax() + margin_ymax)

    if antenna_margin>0:
        weighted_meshlines_x.addPolyEdge(allpolygons.get_xmin() - margin_xmin - antenna_margin)
        weighted_meshlines_x.addPolyEdge(allpolygons.get_xmax() + margin_xmax + antenna_margin)
        weighted_meshlines_y.addPolyEdge(allpolygons.get_ymin() - margin_ymin - antenna_margin)
        weighted_meshlines_y.addPolyEdge(allpolygons.get_ymax() + margin_ymax + antenna_margin)
    

    # step 1: create lines at all polygon edges
    for poly in allpolygons.polygons:
        if poly.is_via:
            for point in poly.pts_x:
                weighted_meshlines_x.addViaEdge(point)
            for point in poly.pts_y:
                weighted_meshlines_y.addViaEdge(point)
        else:
            for point in poly.pts_x:
                if poly.is_port: # highest priority in meshing
                    weighted_meshlines_x.addPortEdge(point)
                else: # regular polygon   
                    weighted_meshlines_x.addPolyEdge(point)
                # add small cell left and right
                if point > allpolygons.get_xmin():  
                    weighted_meshlines_x.addFill(point-target_cellsize)
                if point < allpolygons.get_xmax():  
                    weighted_meshlines_x.addFill(point+target_cellsize)
            for point in poly.pts_y:
                if poly.is_port:  # highest priority in meshing
                    weighted_meshlines_y.addPortEdge(point)
                else:  # regular polygon     
                    weighted_meshlines_y.addPolyEdge(point)
                if point > allpolygons.get_ymin():  
                    weighted_meshlines_y.addFill(point-target_cellsize)
                if point < allpolygons.get_ymax():  
                    weighted_meshlines_y.addFill(point+target_cellsize)

        
        # special case port, the polygon is then a rectangle and we want to insert one extra mesh line in the middle
        if poly.is_port:
            # get orientation, place extra mesh line along the short axis
            size_x = poly.xmax - poly.xmin
            size_y = poly.ymax - poly.ymin
            if size_x > size_y:
                weighted_meshlines_y.addFill((min(poly.pts_y)+max(poly.pts_y))/2)
            else:
                weighted_meshlines_x.addFill((min(poly.pts_x)+max(poly.pts_x))/2)
        


    # step 2: place extra lines along diagonal lines
    weighted_meshlines_x.sort()
    weighted_meshlines_y.sort()

    # create list of diagonal segments
    diagonal_regions_x = []
    diagonal_regions_y = []
    for poly in allpolygons.polygons:
        for i in range(0, len(poly.pts_x)):
            last_x = poly.pts_x[i-1]
            last_y = poly.pts_y[i-1]
            point_x = poly.pts_x[i]
            point_y = poly.pts_y[i]

            # check if we have different x AND y, then we have a digonal segment
            if ((point_x!=last_x) and (point_y!=last_y)):
                diagonal_regions_x.append([last_x,point_x])
                diagonal_regions_y.append([last_y,point_y])

    # add extra points in diagonal regions
    for diagonal_region in diagonal_regions_x:       
        xmin = min(diagonal_region[0],diagonal_region[1])
        xmax = max(diagonal_region[0],diagonal_region[1])
        if (xmax-xmin) > 2*target_cellsize:
            weighted_meshlines_x.addFillRange(xmin, xmax, target_cellsize)

    for diagonal_region in diagonal_regions_y:       
        ymin = min(diagonal_region[0],diagonal_region[1])
        ymax = max(diagonal_region[0],diagonal_region[1])
        if (ymax-ymin) > 2*target_cellsize:
            weighted_meshlines_y.addFillRange(ymin, ymax, target_cellsize)

    weighted_meshlines_x.sort()
    weighted_meshlines_y.sort()

    weighted_meshlines_x.remove_duplicates()
    weighted_meshlines_y.remove_duplicates()
    
    # step 3: remove mesh lines that are too close, replace with one mesh line in the middle
    def remove_closely_spaced_lines (line_list):
        new_lines = []
        index = 0
        removed_something = False
        linecount = len(line_list)

        while index < linecount-1:
            this_line = line_list[index]
            next_line = line_list[index+1]
            this_dist = abs(next_line.value-this_line.value)

            if this_dist > target_cellsize*0.8: 
                # accept slightly smaller mesh cells than target size
                new_lines.append(line_list[index]) # append line with value and weight unchanged
            else:
                if index<linecount-2: 
                    if this_line.weight == next_line.weight:
                        # add with average value, unchanged weight 
                        new_lines.append(weighted_meshline((this_line.value + next_line.value)/2, this_line.weight))
                    elif this_line.weight > next_line.weight:
                        # this_line is a polygon edge, prioritize this_line
                        new_lines.append(this_line)
                    else:
                        # next_line is a polygon edge, prioritize next_line
                        new_lines.append(next_line)
                # skip next line, we already handled that
                index = index+1
                removed_something = True

            index = index+1

        # add very last line
        new_lines.append(line_list[-1])
        
        return new_lines, removed_something

    run_check = True
    while run_check:
        weighted_meshlines_x.meshlines, removed_x = remove_closely_spaced_lines(weighted_meshlines_x.meshlines)
        weighted_meshlines_y.meshlines, removed_y = remove_closely_spaced_lines(weighted_meshlines_y.meshlines)
        run_check = removed_x or removed_y

    # ----------- we have finished the pre-processing of WEIGHTED mesh lines, now switch to openEMS mesh typ --------------
    
    mesh.AddLine('x', weighted_meshlines_x.getLines())
    mesh.AddLine('y', weighted_meshlines_y.getLines())
    
    # step 4: add intermediate lines in large mesh cells
    def add_extra_lines (direction, minvalue, maxvalue):
        lines = mesh.GetLines(direction, do_sort=True)
       
        for index in range(0, len(lines)-1):
            this_line = lines[index]
            next_line = lines[index+1]
            dist = next_line-this_line

            # refine only in  drawn metal polygons region
            if (this_line > minvalue) and (this_line < maxvalue):
                if dist > 4*target_cellsize:
                    point = this_line+target_cellsize
                    mesh.AddLine(direction, point)
                    if next_line < maxvalue:
                        point = next_line-target_cellsize
                        mesh.AddLine(direction, point)
                elif dist > 3*target_cellsize:    
                    point = (this_line+next_line)/2
                    mesh.AddLine(direction, point)
    

    add_extra_lines('x', allpolygons.get_xmin(), allpolygons.get_xmax())
    add_extra_lines('y', allpolygons.get_ymin(), allpolygons.get_ymax())

    mesh.SmoothMeshLines('x', max_cellsize, 1.3)
    mesh.SmoothMeshLines('y', max_cellsize, 1.3)
    
    # step 5: check for possible gaps
    def add_missing_lines (direction):
        lines = mesh.GetLines(direction, do_sort=True)
       
        added_something = False
        for index in range(1, len(lines)-1):
            previous_line = lines[index-1]
            this_line = lines[index]
            next_line = lines[index+1]
            previous_dist = this_line-previous_line
            this_dist = next_line-this_line

            ratio = this_dist/previous_dist
            if ratio > 2.5:
                point = (this_line + this_dist/2)
                mesh.AddLine(direction, point)
                added_something = True
            elif ratio < 1/2.5:
                point = (this_line - previous_dist/2)
                mesh.AddLine(direction, point)
                added_something = True


        return added_something

    run_check = True
    while run_check:
        check_x = add_missing_lines('x')
        check_y = add_missing_lines('y')
        run_check = check_x or check_y
        mesh.SmoothMeshLines('x', max_cellsize, 1.3)
        mesh.SmoothMeshLines('y', max_cellsize, 1.3)
    
    # done
    return mesh


# ------------------- Mesh using autoMesh module -------------------------

def create_xy_using_easyMesh(CSX, allpolygons, simulation_ports, margin, antenna_margin, target_cellsize, max_cellsize, primitives_mesh_setup, properties_mesh_setup, settings):
    
    # load easyMesh module
    from easyMesh import GenerateMesh

    # configure easyMesh for xyz direction (no separate call for z direction!)
    global_mesh_setup = {
        'drawing_unit': settings['unit'],  # geometry is in microns
        'start_frequency': settings['fstart'],
        'stop_frequency': settings['fstop'],
        'mesh_resolution': settings.get('mesh_resolution','medium'), # 'low', 'medium', 'high', 'very_high'
        'use_circle_detection': settings.get('use_circle_detection', False), 
        'boundary_distance': settings.get('boundary_distance', [None, None, None, None, None, None]), # value, 'auto' or None
        'handle_closely_placed_edges': settings.get('handle_closely_placed_edges', True),  # if True, then mesher will try to handle close placed edges by merging them
        'min_cellsize': settings.get('refined_cellsize', 1),
        'dirs': 'xyz'
    }

    GenerateMesh(CSX, global_mesh_setup, primitives_mesh_setup, properties_mesh_setup)
    mesh = CSX.GetGrid()
    return mesh

# no need for separate z mesh function, that is all done in create_xyz_using_autoMesh

# ------------------- internal utilities -------------------------



def add_equal_meshlines(mesh, axis, start, stop, target_cellsize):
    """
    Adds a number of equally spaced meshlines 
    """
    if stop-start > 1.5 * target_cellsize: 
        # calculate required number of mesh cells
        n = int(abs((math.ceil((stop-start)/target_cellsize)+1)))
        points = np.linspace(start, stop, n)
        for point in points:
            mesh.AddLine(axis, point)
    else:
        mesh.AddLine(axis, start)
        mesh.AddLine(axis, stop)



def add_graded_meshlines(mesh, axis, start, stop, stepstart, factor, maxstep):
    """
    Adds graded mesh lines outward from the center.
    """
    mesh.AddLine(axis, start)
    value = start
    step = stepstart

    while (step > 0 and value < stop) or (step < 0 and value > stop):
        value = value + step

        # check how far we are away from stop, to avoid tiny step at the boundary
        if abs(stop - value) < abs (1.5*step) :
            mesh.AddLine(axis, (value-step+stop)/2)
            value = stop

        mesh.AddLine(axis, value)

        step = step * factor
        if (step/maxstep > 1):
            step = maxstep

    if (value!=stop):
       mesh.AddLine(axis, stop)
   
    return step    


def get_smallest_cell (mesh, direction):
    lines = mesh.GetLines(direction, do_sort=True)
    smallest = math.inf
    for n in range(0, len(lines)-1):
        delta = lines[n+1]-lines[n]
        smallest = min(delta, smallest)
    return smallest    
 

def get_mesh_information (mesh):
    meshinfo = ''
    x_count = mesh.GetQtyLines('x')
    y_count = mesh.GetQtyLines('y')
    z_count = mesh.GetQtyLines('z')
    numcells = x_count * y_count * z_count
    meshinfo = meshinfo + '\n________________________\nMesh cells by axis (total ' + format(numcells/1E3,'.0f') +' kcells):\n x = ' + str(x_count) + '\n y = ' + str(y_count) + '\n z = ' + str(z_count) + '\n'

    x_smallest = get_smallest_cell(mesh,'x')    
    y_smallest = get_smallest_cell(mesh,'y')    
    z_smallest = get_smallest_cell(mesh,'z')    
    meshinfo = meshinfo + 'Smallest cell size:\n dx = ' + format(x_smallest,'.4f') + '\n dy = ' + format(y_smallest,'.4f') + '\n dz = ' + format(z_smallest,'.4f') + '\n________________________\n'
    return meshinfo


import sys
import numpy as np
from pathlib import Path

XPOS = 0
YPOS = 1

# TODO this implementation has a flaw: non-horizontal parts do not have the same trace width as the horizontal ones due to a principle algorithm problem. We have to compute the corner points with another trigonometric approach!

class UI:
    def __init__(self):
        self.grid = 5e-9

        self.radius = 5e-6
        self.height_turn = 12e-6
        self.width = 150e-6
        self.trace_width = 3e-6

        self.num_turns = 10 # Has to be greater equal 1

        self.num_points_curve = 10 # Greater equal 2

        self.initial_height = 5e-6 # Has to be > 0
        self.final_hight = 5e-6 # Has to be > 0

        self.initial_width = self.width / 2
        self.final_width = self.width / 2

### Functions ### 
def print_to_console(arr: np.array):
    for row in arr:
        print(*row, sep='\t')

def is_greater(x, y, ui: UI):
    return x - y >= ui.grid


def is_lower(x, y, ui: UI):
    return y - x >= ui.grid


def is_equal(x, y, ui: UI):
    return np.abs(x - y) < ui.grid


def find_corner_points(ui: UI):
    '''
    Snakes left and right and find the points where the lines end.
    '''

    corner_points = np.zeros((4 * ui.num_turns + 6, 2))

    # First four points manually
    corner_points[0] = [ui.initial_width,0]
    corner_points[1] = [ui.initial_width, ui.initial_height]
    corner_points[2] = [ui.initial_width + ui.radius, ui.initial_height + ui.radius]
    corner_points[3] = [ui.width - ui.radius, ui.initial_height + ui.radius]

    prev = "upleft-up"
    for index in range(3, corner_points.shape[0] - 4):
        # Next: up right (left turn)
        if prev == "upleft-up":
            corner_points[index + 1] = [corner_points[index, XPOS] + ui.radius, corner_points[index, YPOS] + ui.radius]
            prev = "up-upright"

        # Next: up (from previous rightup)
        elif prev == "up-upright":
            corner_points[index + 1] = [corner_points[index, XPOS], corner_points[index, YPOS] + (ui.height_turn - 2*ui.radius)]
            prev = "upright-right"

        # Next: up left (left turn)
        elif prev == "upright-right":
            corner_points[index + 1] = [corner_points[index, XPOS] - ui.radius, corner_points[index, YPOS] + ui.radius]
            prev = "right-upright"

        # Next: left
        elif prev == "right-upright":
            corner_points[index + 1] = [corner_points[index, XPOS] - ui.width + 2*ui.radius, corner_points[index, YPOS]]
            prev = "upright-up"

        # Next: up left (right turn)
        elif prev == "upright-up":
            corner_points[index + 1] = [corner_points[index, XPOS] - ui.radius, corner_points[index, YPOS] + ui.radius]
            prev = "up-upleft"

        # Next: up (from previous leftup)
        elif prev == "up-upleft":
            corner_points[index + 1] = [corner_points[index, XPOS], corner_points[index, YPOS] + (ui.height_turn - 2*ui.radius)]
            prev = "upleft-left"

        # Next: up right (right turn)
        elif prev == "upleft-left":
            corner_points[index + 1] = [corner_points[index, XPOS] + ui.radius, corner_points[index, YPOS] + ui.radius]
            prev = "left-upleft"

        # Next: right
        elif prev == "left-upleft":
            corner_points[index + 1] = [corner_points[index, XPOS] + ui.width - 2*ui.radius, corner_points[index, YPOS]]
            prev = "upleft-up"

    # Last three points manually
    if ui.num_turns % 2 != 0:
        corner_points[-3] = [ui.width - ui.final_width + ui.radius, corner_points[-4, YPOS]]
    else:
        corner_points[-3] = [ui.final_width - ui.radius, corner_points[-4, YPOS]]
    corner_points[-2] = [ui.final_width, corner_points[-4, YPOS] + ui.radius]
    corner_points[-1] = [ui.final_width, corner_points[-4, YPOS] + ui.radius + ui.final_hight]

    return corner_points


def generate_polygon_points(corner_points: np.ndarray, ui: UI):
    ''''
    Fills the corners with points
    '''
    angles = np.linspace(0, 90, ui.num_points_curve)

    polygon_points_right = np.zeros((round((ui.num_points_curve * 2) * ui.num_turns + ui.num_points_curve * 2 + 2), 2))
    polygon_points_right[0] = [corner_points[0, XPOS] + ui.trace_width / 2, corner_points[0,YPOS]]
    polygon_points_right[-1] = [corner_points[-1, XPOS] + ui.trace_width / 2, corner_points[-1,YPOS]]

    polygon_points_left = np.zeros((round((ui.num_points_curve * 2) * ui.num_turns + ui.num_points_curve * 2 + 2), 2))
    polygon_points_left[0] = [corner_points[0, XPOS] - ui.trace_width / 2, corner_points[0,YPOS]]
    polygon_points_left[-1] = [corner_points[-1, XPOS] - ui.trace_width / 2, corner_points[-1,YPOS]]

    start_index_curve_points = 1
    for index in range(1, corner_points.shape[0] - 1):
        if (is_equal(corner_points[index-1, XPOS], corner_points[index, XPOS], ui) and 
            is_lower(corner_points[index-1, YPOS], corner_points[index, YPOS], ui) and
            is_greater(corner_points[index+1, XPOS], corner_points[index, XPOS], ui)):

            fill_curve(start_index_curve_points, index, corner_points, polygon_points_right, polygon_points_left, angles, "up-upright", ui)
            start_index_curve_points += ui.num_points_curve

        elif (is_equal(corner_points[index-1, YPOS], corner_points[index, YPOS], ui) and 
             is_lower(corner_points[index-1, XPOS], corner_points[index, XPOS], ui) and
             is_greater(corner_points[index+1, YPOS], corner_points[index, YPOS], ui)):
            
            fill_curve(start_index_curve_points, index, corner_points, polygon_points_right, polygon_points_left, angles, "right-upright", ui)
            start_index_curve_points += ui.num_points_curve

        elif (is_equal(corner_points[index-1, XPOS], corner_points[index, XPOS], ui) and 
            is_lower(corner_points[index-1, YPOS], corner_points[index, YPOS], ui) and
            is_lower(corner_points[index+1, XPOS], corner_points[index, XPOS], ui)):

            fill_curve(start_index_curve_points, index, corner_points, polygon_points_right, polygon_points_left, angles, "up-upleft", ui)
            start_index_curve_points += ui.num_points_curve

        elif (is_equal(corner_points[index-1, YPOS], corner_points[index, YPOS], ui) and 
            is_greater(corner_points[index-1, XPOS], corner_points[index, XPOS], ui) and
            is_greater(corner_points[index+1, YPOS], corner_points[index, YPOS], ui)):

            fill_curve(start_index_curve_points, index, corner_points, polygon_points_right, polygon_points_left, angles, "left-upleft", ui)
            start_index_curve_points += ui.num_points_curve

    polygon_points = np.concatenate((polygon_points_right, np.flip(polygon_points_left, axis=0)), axis=0)

    return polygon_points


def fill_curve(start, index_corner, corner_points, polygon_points_right, polygon_points_left, angles, typ, ui: UI):
    if typ == "up-upright":
        for i in range(0, ui.num_points_curve):
            polygon_points_right[start+i,XPOS] = corner_points[index_corner+1, XPOS] - np.cos(np.deg2rad(angles[i])) * (ui.radius - ui.trace_width / 2)
            polygon_points_right[start+i,YPOS] = corner_points[index_corner, YPOS] + np.sin(np.deg2rad(angles[i])) * (ui.radius - ui.trace_width / 2)

            polygon_points_left[start+i,XPOS] = corner_points[index_corner+1, XPOS] - np.cos(np.deg2rad(angles[i])) * (ui.radius + ui.trace_width / 2)
            polygon_points_left[start+i,YPOS] = corner_points[index_corner, YPOS] + np.sin(np.deg2rad(angles[i])) * (ui.radius + ui.trace_width / 2)

    elif typ == "right-upright":
        for i in range(0, ui.num_points_curve):
            polygon_points_right[start+i,XPOS] = corner_points[index_corner, XPOS] + np.sin(np.deg2rad(angles[i])) * (ui.radius + ui.trace_width / 2)
            polygon_points_right[start+i,YPOS] = corner_points[index_corner+1, YPOS] - np.cos(np.deg2rad(angles[i])) * (ui.radius + ui.trace_width / 2)

            polygon_points_left[start+i,XPOS] = corner_points[index_corner, XPOS] + np.sin(np.deg2rad(angles[i])) * (ui.radius - ui.trace_width / 2)
            polygon_points_left[start+i,YPOS] = corner_points[index_corner+1, YPOS] - np.cos(np.deg2rad(angles[i])) * (ui.radius - ui.trace_width / 2)

    elif typ == "up-upleft":
        for i in range(0, ui.num_points_curve):
            polygon_points_right[start+i,XPOS] = corner_points[index_corner+1, XPOS] + np.cos(np.deg2rad(angles[i])) * (ui.radius + ui.trace_width / 2)
            polygon_points_right[start+i,YPOS] = corner_points[index_corner, YPOS] + np.sin(np.deg2rad(angles[i])) * (ui.radius + ui.trace_width / 2)

            polygon_points_left[start+i,XPOS] = corner_points[index_corner+1, XPOS] + np.cos(np.deg2rad(angles[i])) * (ui.radius - ui.trace_width / 2)
            polygon_points_left[start+i,YPOS] = corner_points[index_corner, YPOS] + np.sin(np.deg2rad(angles[i])) * (ui.radius - ui.trace_width / 2)

    elif typ == "left-upleft":
        for i in range(0, ui.num_points_curve):
            polygon_points_right[start+i,XPOS] = corner_points[index_corner, XPOS] - np.sin(np.deg2rad(angles[i])) * (ui.radius - ui.trace_width / 2)
            polygon_points_right[start+i,YPOS] = corner_points[index_corner+1, YPOS] - np.cos(np.deg2rad(angles[i])) * (ui.radius - ui.trace_width / 2)

            polygon_points_left[start+i,XPOS] = corner_points[index_corner, XPOS] - np.sin(np.deg2rad(angles[i])) * (ui.radius + ui.trace_width / 2)
            polygon_points_left[start+i,YPOS] = corner_points[index_corner+1, YPOS] - np.cos(np.deg2rad(angles[i])) * (ui.radius + ui.trace_width / 2)


def save_to_txt(arr: np.ndarray):
    file_path = Path(__file__).resolve().parent / "snake_inductor_polygon.txt"

    with open(file_path, "w") as file:
        for row in arr:
            print(*row, sep="\t", file=file)


### Main ###
def main():

    ui = UI()

    # TODO check user input for implementability
    if ui.height_turn - ui.radius < ui.radius:
        print("Reduce radius or increase height_turn!")
        sys.exit()
    if ui.radius > ui.trace_width / 2:
        print("Reduce radius or decrease trace width!")

    # First find the corner points
    corner_points = find_corner_points(ui)

    # Finally, generate the outer points that define the polygon
    polygon_points = generate_polygon_points(corner_points, ui)

    # Set the entire points on the desired grid
    polygon_points = np.round(polygon_points / ui.grid) * ui.grid

    # Convert to um
    polygon_points = np.round(polygon_points * 1e6, 3)

    # Save to txt file
    save_to_txt(polygon_points)

if __name__ == "__main__":
    main()
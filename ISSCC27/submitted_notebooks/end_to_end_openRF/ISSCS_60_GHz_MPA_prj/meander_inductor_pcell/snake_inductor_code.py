__version__ = '$Revision: #1 $'

from cni.dlo import *
from .geometry import *
from .utility_functions import *

import math


class snake_inductor(DloGen):

    @classmethod
    def defineParamSpecs(self, specs):

        techparams = specs.tech.getTechParams()
        CDFVersion = techparams['CDFVersion']

        # --------------------------------------------------------------
        # Default parameters
        # --------------------------------------------------------------

        def_radius        = '5u'
        def_height_turn   = '12u'
        def_width         = '100u'
        def_trace_width   = '3u'
        def_num_turns     = 3
        def_num_points    = 10
        def_initial_height = '5u'
        def_final_height   = '5u'
        def_initial_width  = '50u'
        def_final_width    = '50u'

        specs(
            'cdf_version',
            CDFVersion,
            'CDF Version'
        )

        specs(
            'Display',
            'Selected',
            'Display',
            ChoiceConstraint(['All', 'Selected'])
        )

        specs(
            'radius',
            def_radius,
            'Corner radius'
        )

        specs(
            'height_turn',
            def_height_turn,
            'Height of one turn'
        )

        specs(
            'width',
            def_width,
            'Overall width'
        )

        specs(
            'trace_width',
            def_trace_width,
            'Metal trace width'
        )

        specs(
            'num_turns',
            def_num_turns,
            'Number of turns'
        )

        specs(
            'num_points_curve',
            def_num_points,
            'Points per 90 degree curve'
        )

        specs(
            'initial_height',
            def_initial_height,
            'Initial vertical length'
        )

        specs(
            'final_height',
            def_final_height,
            'Final vertical length'
        )

        specs(
            'initial_width',
            def_initial_width,
            'Initial width'
        )

        specs(
            'final_width',
            def_final_width,
            'Final width'
        )

        specs(
            'blockqrc',
            True,
            'Block QRC layer'
        )

        specs(
            'subE',
            False,
            'Substrate Etching'
        )

    # ------------------------------------------------------------------
    # Parameter setup
    # ------------------------------------------------------------------

    def setupParams(self, params):

        self.params = params

        self.radius = params['radius']
        self.height_turn = params['height_turn']
        self.width = params['width']
        self.trace_width = params['trace_width']

        self.num_turns = params['num_turns']
        self.num_points_curve = params['num_points_curve']

        self.initial_height = params['initial_height']
        self.final_height = params['final_height']

        self.initial_width = params['initial_width']
        self.final_width = params['final_width']

        self.blockqrc = params['blockqrc']
        self.subE = params['subE']

    # ------------------------------------------------------------------
    # Geometry helper functions
    # ------------------------------------------------------------------

    @staticmethod
    def is_greater(x, y, grid):
        return x - y >= grid

    @staticmethod
    def is_lower(x, y, grid):
        return y - x >= grid

    @staticmethod
    def is_equal(x, y, grid):
        return abs(x - y) < grid

    # ------------------------------------------------------------------
    # Find the sharp corner points of the snake
    # ------------------------------------------------------------------

    def find_corner_points(self):

        radius = self.radius
        height_turn = self.height_turn
        width = self.width
        num_turns = self.num_turns
        initial_height = self.initial_height
        final_height = self.final_height
        initial_width = self.initial_width
        final_width = self.final_width

        # Same allocation as the original NumPy implementation
        corner_points = [
            [0.0, 0.0]
            for _ in range(4 * num_turns + 6)
        ]

        # First three points
        corner_points[0] = [
            initial_width,
            0.0
        ]

        corner_points[1] = [
            initial_width,
            initial_height
        ]

        corner_points[2] = [
            initial_width + radius,
            initial_height + radius
        ]

        corner_points[3] = [
            width - radius,
            initial_height + radius
        ]

        prev = "upleft-up"

        for index in range(3, len(corner_points) - 4):

            # up right
            if prev == "upleft-up":

                corner_points[index + 1] = [
                    corner_points[index][0] + radius,
                    corner_points[index][1] + radius
                ]

                prev = "up-upright"

            # up
            elif prev == "up-upright":

                corner_points[index + 1] = [
                    corner_points[index][0],
                    corner_points[index][1]
                    + (height_turn - 2 * radius)
                ]

                prev = "upright-right"

            # up left
            elif prev == "upright-right":

                corner_points[index + 1] = [
                    corner_points[index][0] - radius,
                    corner_points[index][1] + radius
                ]

                prev = "right-upright"

            # left
            elif prev == "right-upright":

                corner_points[index + 1] = [
                    corner_points[index][0]
                    - width + 2 * radius,
                    corner_points[index][1]
                ]

                prev = "upright-up"

            # up left
            elif prev == "upright-up":

                corner_points[index + 1] = [
                    corner_points[index][0] - radius,
                    corner_points[index][1] + radius
                ]

                prev = "up-upleft"

            # up
            elif prev == "up-upleft":

                corner_points[index + 1] = [
                    corner_points[index][0],
                    corner_points[index][1]
                    + (height_turn - 2 * radius)
                ]

                prev = "upleft-left"

            # up right
            elif prev == "upleft-left":

                corner_points[index + 1] = [
                    corner_points[index][0] + radius,
                    corner_points[index][1] + radius
                ]

                prev = "left-upleft"

            # right
            elif prev == "left-upleft":

                corner_points[index + 1] = [
                    corner_points[index][0]
                    + width - 2 * radius,
                    corner_points[index][1]
                ]

                prev = "upleft-up"

        # Last three points
        if num_turns % 2 != 0:

            corner_points[-3] = [
                width - final_width + radius,
                corner_points[-4][1]
            ]

        else:

            corner_points[-3] = [
                final_width - radius,
                corner_points[-4][1]
            ]

        corner_points[-2] = [
            final_width,
            corner_points[-4][1] + radius
        ]

        corner_points[-1] = [
            final_width,
            corner_points[-4][1]
            + radius
            + final_height
        ]

        return corner_points

    # ------------------------------------------------------------------
    # Fill one 90-degree corner
    # ------------------------------------------------------------------

    def fill_curve(
        self,
        start,
        index_corner,
        corner_points,
        polygon_points_right,
        polygon_points_left,
        angles,
        typ
    ):

        radius = self.radius
        trace_width = self.trace_width

        x = lambda i: corner_points[i][0]
        y = lambda i: corner_points[i][1]

        for i in range(self.num_points_curve):

            angle = math.radians(angles[i])

            if typ == "up-upright":

                polygon_points_right[start + i] = [
                    x(index_corner + 1)
                    - math.cos(angle)
                    * (radius - trace_width / 2),

                    y(index_corner)
                    + math.sin(angle)
                    * (radius - trace_width / 2)
                ]

                polygon_points_left[start + i] = [
                    x(index_corner + 1)
                    - math.cos(angle)
                    * (radius + trace_width / 2),

                    y(index_corner)
                    + math.sin(angle)
                    * (radius + trace_width / 2)
                ]

            elif typ == "right-upright":

                polygon_points_right[start + i] = [
                    x(index_corner)
                    + math.sin(angle)
                    * (radius + trace_width / 2),

                    y(index_corner + 1)
                    - math.cos(angle)
                    * (radius + trace_width / 2)
                ]

                polygon_points_left[start + i] = [
                    x(index_corner)
                    + math.sin(angle)
                    * (radius - trace_width / 2),

                    y(index_corner + 1)
                    - math.cos(angle)
                    * (radius - trace_width / 2)
                ]

            elif typ == "up-upleft":

                polygon_points_right[start + i] = [
                    x(index_corner + 1)
                    + math.cos(angle)
                    * (radius + trace_width / 2),

                    y(index_corner)
                    + math.sin(angle)
                    * (radius + trace_width / 2)
                ]

                polygon_points_left[start + i] = [
                    x(index_corner + 1)
                    + math.cos(angle)
                    * (radius - trace_width / 2),

                    y(index_corner)
                    + math.sin(angle)
                    * (radius - trace_width / 2)
                ]

            elif typ == "left-upleft":

                polygon_points_right[start + i] = [
                    x(index_corner)
                    - math.sin(angle)
                    * (radius - trace_width / 2),

                    y(index_corner + 1)
                    - math.cos(angle)
                    * (radius - trace_width / 2)
                ]

                polygon_points_left[start + i] = [
                    x(index_corner)
                    - math.sin(angle)
                    * (radius + trace_width / 2),

                    y(index_corner + 1)
                    - math.cos(angle)
                    * (radius + trace_width / 2)
                ]

    # ------------------------------------------------------------------
    # Generate polygon centerline boundaries
    # ------------------------------------------------------------------

    def generate_polygon_points(self, corner_points):

        radius = self.radius
        trace_width = self.trace_width
        num_turns = self.num_turns
        num_points_curve = self.num_points_curve

        angles = [
            90.0 * i / (num_points_curve - 1)
            for i in range(num_points_curve)
        ]

        num_points = (
            2 * num_points_curve * num_turns
            + 2 * num_points_curve
            + 2
        )

        polygon_points_right = [
            [0.0, 0.0]
            for _ in range(num_points)
        ]

        polygon_points_left = [
            [0.0, 0.0]
            for _ in range(num_points)
        ]

        polygon_points_right[0] = [
            corner_points[0][0] + trace_width / 2,
            corner_points[0][1]
        ]

        polygon_points_right[-1] = [
            corner_points[-1][0] + trace_width / 2,
            corner_points[-1][1]
        ]

        polygon_points_left[0] = [
            corner_points[0][0] - trace_width / 2,
            corner_points[0][1]
        ]

        polygon_points_left[-1] = [
            corner_points[-1][0] - trace_width / 2,
            corner_points[-1][1]
        ]

        start_index_curve_points = 1

        grid = self.grid

        for index in range(1, len(corner_points) - 1):

            x0 = corner_points[index - 1][0]
            y0 = corner_points[index - 1][1]

            x1 = corner_points[index][0]
            y1 = corner_points[index][1]

            x2 = corner_points[index + 1][0]
            y2 = corner_points[index + 1][1]

            if (
                self.is_equal(x0, x1, grid)
                and self.is_lower(y0, y1, grid)
                and self.is_greater(x2, x1, grid)
            ):

                self.fill_curve(
                    start_index_curve_points,
                    index,
                    corner_points,
                    polygon_points_right,
                    polygon_points_left,
                    angles,
                    "up-upright"
                )

                start_index_curve_points += num_points_curve

            elif (
                self.is_equal(y0, y1, grid)
                and self.is_lower(x0, x1, grid)
                and self.is_greater(y2, y1, grid)
            ):

                self.fill_curve(
                    start_index_curve_points,
                    index,
                    corner_points,
                    polygon_points_right,
                    polygon_points_left,
                    angles,
                    "right-upright"
                )

                start_index_curve_points += num_points_curve

            elif (
                self.is_equal(x0, x1, grid)
                and self.is_lower(y0, y1, grid)
                and self.is_lower(x2, x1, grid)
            ):

                self.fill_curve(
                    start_index_curve_points,
                    index,
                    corner_points,
                    polygon_points_right,
                    polygon_points_left,
                    angles,
                    "up-upleft"
                )

                start_index_curve_points += num_points_curve

            elif (
                self.is_equal(y0, y1, grid)
                and self.is_greater(x0, x1, grid)
                and self.is_greater(y2, y1, grid)
            ):

                self.fill_curve(
                    start_index_curve_points,
                    index,
                    corner_points,
                    polygon_points_right,
                    polygon_points_left,
                    angles,
                    "left-upleft"
                )

                start_index_curve_points += num_points_curve

        # Right side followed by reversed left side
        polygon_points = (
            polygon_points_right
            + list(reversed(polygon_points_left))
        )

        return polygon_points

    # ------------------------------------------------------------------
    # Main layout generation
    # ------------------------------------------------------------------

    def genLayout(self):

        # --------------------------------------------------------------
        # Convert parameters to PyCell database units.
        #
        # IHP CNI geometry is expressed in micrometers.
        # --------------------------------------------------------------

        self.radius = GridFix(Numeric(self.radius) * 1e6)
        self.height_turn = GridFix(Numeric(self.height_turn) * 1e6)
        self.width = GridFix(Numeric(self.width) * 1e6)
        self.trace_width = GridFix(Numeric(self.trace_width) * 1e6)

        self.initial_height = GridFix(
            Numeric(self.initial_height) * 1e6
        )

        self.final_height = GridFix(
            Numeric(self.final_height) * 1e6
        )

        self.initial_width = GridFix(
            Numeric(self.initial_width) * 1e6
        )

        self.final_width = GridFix(
            Numeric(self.final_width) * 1e6
        )

        self.num_turns = int(self.num_turns)
        self.num_points_curve = int(self.num_points_curve)

        # --------------------------------------------------------------
        # Grid
        # --------------------------------------------------------------

        techparams = self.tech.getTechParams()

        self.grid = 0.005

        # --------------------------------------------------------------
        # Parameter checks
        # --------------------------------------------------------------

        if self.num_turns < 1:
            raise ValueError(
                "snake_inductor: num_turns must be >= 1"
            )

        if self.num_points_curve < 2:
            raise ValueError(
                "snake_inductor: num_points_curve must be >= 2"
            )

        if self.radius <= 0:
            raise ValueError(
                "snake_inductor: radius must be > 0"
            )

        if self.height_turn < 2 * self.radius:
            raise ValueError(
                "snake_inductor: height_turn must be >= 2 * radius"
            )

        if self.trace_width <= 0:
            raise ValueError(
                "snake_inductor: trace_width must be > 0"
            )

        if self.width <= 2 * self.radius:
            raise ValueError(
                "snake_inductor: width is too small for radius"
            )

        if self.initial_height <= 0:
            raise ValueError(
                "snake_inductor: initial_height must be > 0"
            )

        if self.final_height <= 0:
            raise ValueError(
                "snake_inductor: final_height must be > 0"
            )

        if self.initial_width <= 0:
            raise ValueError(
                "snake_inductor: initial_width must be > 0"
            )

        if self.final_width <= 0:
            raise ValueError(
                "snake_inductor: final_width must be > 0"
            )

        if self.initial_width > self.width:
            raise ValueError(
                "snake_inductor: initial_width cannot exceed width"
            )

        if self.final_width > self.width:
            raise ValueError(
                "snake_inductor: final_width cannot exceed width"
            )

        # --------------------------------------------------------------
        # Layers
        # --------------------------------------------------------------

        TM2 = Layer('TopMetal2', 'drawing')
        TM2p = Layer('TopMetal2', 'pin')

        IND = Layer('IND', 'drawing')
        INDp = Layer('IND', 'pin')

        PWellBlock = Layer('PWell', 'block')
        NoActFiller = Layer('Activ', 'nofill')
        NoGatFiller = Layer('GatPoly', 'nofill')
        NoMet1Filler = Layer('Metal1', 'nofill')
        NoMet2Filler = Layer('Metal2', 'nofill')
        NoMet3Filler = Layer('Metal3', 'nofill')
        NoMet4Filler = Layer('Metal4', 'nofill')
        NoMet5Filler = Layer('Metal5', 'nofill')
        NoTMet1Filler = Layer('TopMetal1', 'nofill')
        NoTMet2Filler = Layer('TopMetal2', 'nofill')

        NoRCX = Layer('NoRCX', 'drawing')
        substrateE = Layer('LBE', 'drawing')

        # --------------------------------------------------------------
        # Generate geometry
        # --------------------------------------------------------------

        corner_points = self.find_corner_points()

        polygon_points = self.generate_polygon_points(
            corner_points
        )

        # --------------------------------------------------------------
        # Grid snap
        # --------------------------------------------------------------

        polygon_points = [
            [
                GridFix(x),
                GridFix(y)
            ]
            for x, y in polygon_points
        ]

        # --------------------------------------------------------------
        # Convert to CNI PointList
        # --------------------------------------------------------------

        polyPoints = PointList([
            Point(x, y)
            for x, y in polygon_points
        ])

        # --------------------------------------------------------------
        # Main TopMetal2 polygon
        # --------------------------------------------------------------

        dbCreatePolygon(
            self,
            TM2,
            polyPoints
        )

        # --------------------------------------------------------------
        # Pins
        #
        # The snake has one port at each vertical end.
        # --------------------------------------------------------------

        start_x = self.initial_width
        start_y = 0.0

        end_x = self.final_width
        end_y = (
            corner_points[-1][1]
        )

        pin_length = self.trace_width

        # Start pin
        start_pin = dbCreateRect(
            self,
            TM2p,
            Box(
                start_x - self.trace_width / 2,
                start_y - pin_length / 2,
                start_x + self.trace_width / 2,
                start_y + pin_length / 2
            )
        )

        start_ind_pin = dbCreateRect(
            self,
            INDp,
            Box(
                start_x - self.trace_width / 2,
                start_y - pin_length / 2,
                start_x + self.trace_width / 2,
                start_y + pin_length / 2
            )
        )

        dbCreatePin(
            self,
            'LA',
            start_pin
        )

        dbCreateLabel(
            self,
            Layer('IND', 'text'),
            Point(start_x, start_y),
            'LA',
            'centerCenter',
            'R0',
            Font.EURO_STYLE,
            self.trace_width / 2
        )

        # End pin
        end_pin = dbCreateRect(
            self,
            TM2p,
            Box(
                end_x - self.trace_width / 2,
                end_y - pin_length / 2,
                end_x + self.trace_width / 2,
                end_y + pin_length / 2
            )
        )

        end_ind_pin = dbCreateRect(
            self,
            INDp,
            Box(
                end_x - self.trace_width / 2,
                end_y - pin_length / 2,
                end_x + self.trace_width / 2,
                end_y + pin_length / 2
            )
        )

        dbCreatePin(
            self,
            'LB',
            end_pin
        )

        dbCreateLabel(
            self,
            Layer('IND', 'text'),
            Point(end_x, end_y),
            'LB',
            'centerCenter',
            'R0',
            Font.EURO_STYLE,
            self.trace_width / 2
        )

        # --------------------------------------------------------------
        # IND extraction layer
        # --------------------------------------------------------------

        dbCreatePolygon(
            self,
            IND,
            polyPoints
        )

        # --------------------------------------------------------------
        # No-fill layers
        # --------------------------------------------------------------

        filler_layers = [
            PWellBlock,
            NoActFiller,
            NoGatFiller,
            NoMet1Filler,
            NoMet2Filler,
            NoMet3Filler,
            NoMet4Filler,
            NoMet5Filler,
            NoTMet1Filler,
            NoTMet2Filler
        ]

        for layer in filler_layers:

            dbCreatePolygon(
                self,
                layer,
                polyPoints
            )

        # --------------------------------------------------------------
        # QRC blocking
        # --------------------------------------------------------------

        if self.blockqrc:

            dbCreatePolygon(
                self,
                NoRCX,
                polyPoints
            )

        # --------------------------------------------------------------
        # Substrate etching
        # --------------------------------------------------------------

        if self.subE:

            dbCreatePolygon(
                self,
                substrateE,
                polyPoints
            )

        # --------------------------------------------------------------
        # Cell label
        # --------------------------------------------------------------

        cellName = self.__class__.__name__

        xs = [point[0] for point in polygon_points]
        ys = [point[1] for point in polygon_points]

        x_left = min(xs)
        y_bottom = min(ys)
        y_top = max(ys)

        label_text = (
            'width={0:.3f}um\n'
            'height_turn={1:.3f}um\n'
            'radius={2:.3f}um\n'
            'trace_width={3:.3f}um\n'
            'turns={4:d}'
        ).format(
            self.width,
            self.height_turn,
            self.radius,
            self.trace_width,
            self.num_turns
        )

        dbCreateLabel(
            self,
            Layer('TEXT', 'drawing'),
            Point(
                x_left,
                y_top + 2.0
            ),
            label_text,
            'leftCenter',
            'R0',
            Font.EURO_STYLE,
            2.0
        )
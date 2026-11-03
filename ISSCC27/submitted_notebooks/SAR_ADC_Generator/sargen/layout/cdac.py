"""Common-centroid binary MIM CDAC generator for SKY130 (gLayout / gdsfactory).

Physical plan (sky130 layer names; gLayout calls them one metal higher because it counts li1 as met1):
  * unit capacitor  = gLayout `mimcap`: capm over a met3 bottom plate, met4 top plate through via3
  * top plate       = met4 straps: one per row through the unit centres plus one vertical spine
                      -> the comparator node, the plate with the least substrate parasitic
  * bottom plates   = per unit a met3 tab down into the routing channel under its row, a via2 onto the
                      met2 track of its bit; each bit's tracks meet a vertical met3 trunk left of the array
Every bit group is a set of point-symmetric unit pairs, so all group centroids coincide with the array
centre (linear gradients cancel); pairs are interleaved with a ruler sequence instead of concentric rings.
"""

from math import floor

GRID = 0.005                      # um, manufacturing grid
# sky130 layers (GDS layer, datatype)
MET2, MET3, MET4 = (69, 20), (70, 20), (71, 20)
VIA2 = (69, 44)
LBL = {MET2: (69, 5), MET3: (70, 5), MET4: (71, 5), (72, 20): (72, 5)}
PIN = {MET2: (69, 16), MET3: (70, 16), MET4: (71, 16), (72, 20): (72, 16)}

# routing geometry (um) from the sky130 rules: via2 0.2 sq., met2 enc. 0.085, met3 enc. 0.065
VIA = 0.20
M2_PAD = VIA + 2 * 0.085          # 0.37
M3_PAD = VIA + 2 * 0.065          # 0.33
TRACK_W = 0.30                    # met2 track width
TRACK_PITCH = 0.70
TAB_W = 0.40                      # met3 tab width (>= 0.30)
TRUNK_W = 0.50                    # met3 trunk width
TRUNK_PITCH = 1.10
CH_MARGIN = 0.60                  # channel margin under the row whose tabs come down (same net: no rule)
CH_MARGIN_LOW = 1.30              # margin above the next row: its capm needs 1.34 um to these met3 pads
CAP_GAP = 1.25                    # met3 gap between units: capm.11 needs capm >= 1.34 um from unrelated met3
TRUNK_CLEAR = 1.45                # array edge (met3) to the first trunk, same rule
STRAP_W = 0.80                    # met4 top-plate strap width


def snap(x):
    return round(round(x / GRID) * GRID, 3)


def array_shape(bits):
    """Rows x columns holding 2^N unit capacitors (square for even N, 1:2 for odd N)."""
    r = 2 ** (bits // 2)
    return r, 2**bits // r


def _ruler(k, bits):
    """Bit index for the k-th symmetric pair (k >= 1): MSB on odd k, next bit on k = 2 mod 4, ..."""
    tz = (k & -k).bit_length() - 1
    return bits - 1 - tz


def centroid_grid(bits):
    """Grid of group labels: int bit index, or 'd' for the termination (dummy) unit.

    Point-symmetric cell pairs are ordered by distance from the centre; the closest pair holds the LSB and the
    termination unit, the remaining 2^(N-1)-1 pairs are dealt out with a ruler sequence (b_{N-1}, b_{N-2},
    b_{N-1}, b_{N-3}, ...) so that every bit is spread from the centre to the edge.
    """
    R, C = array_shape(bits)
    cy, cx = (R - 1) / 2, (C - 1) / 2
    pairs, seen = [], set()
    for r in range(R):
        for c in range(C):
            if (r, c) in seen:
                continue
            m = (R - 1 - r, C - 1 - c)
            seen |= {(r, c), m}
            pairs.append(((r - cy) ** 2 + (c - cx) ** 2, (r, c), m))
    pairs.sort()
    grid = [[None] * C for _ in range(R)]
    _, a, b = pairs[0]
    grid[a[0]][a[1]], grid[b[0]][b[1]] = 0, "d"
    for k, (_, a, b) in enumerate(pairs[1:], start=1):
        g = _ruler(k, bits)
        grid[a[0]][a[1]] = grid[b[0]][b[1]] = g
    return grid


def group_centroids(grid):
    """Centroid (row, col) of every group - all equal the array centre except the two single units."""
    acc = {}
    for r, row in enumerate(grid):
        for c, g in enumerate(row):
            s = acc.setdefault(g, [0, 0, 0])
            s[0] += r
            s[1] += c
            s[2] += 1
    return {g: (s[0] / s[2], s[1] / s[2], s[2]) for g, s in acc.items()}


def net_name(g):
    return "bd" if g == "d" else f"b{g}"


def reference_netlist(bits, side, cell="cdac"):
    """LVS reference: one MIM device per unit capacitor."""
    grid = centroid_grid(bits)
    pins = " ".join(["top"] + [f"b{i}" for i in range(bits)] + ["bd"])
    lines = [f".subckt {cell} {pins}"]
    k = 0
    for row in grid:
        for g in row:
            lines.append(f"XC{k} top {net_name(g)} sky130_fd_pr__cap_mim_m3_1 W={side} L={side} MF=1")
            k += 1
    lines.append(f".ends {cell}")
    return "\n".join(lines) + "\n"


def build_cdac(bits, side, name=None):
    """Draw the CDAC; returns (gdsfactory Component, info dict). Requires gLayout."""
    from gdsfactory import Component
    from gdsfactory.components import rectangle
    from glayout import mimcap, sky130

    grid = centroid_grid(bits)
    R, C = array_shape(bits)
    groups = list(range(bits)) + ["d"]
    unit = mimcap(sky130, (side, side))
    ux0, uy0 = unit.bbox[0]
    ux1, uy1 = unit.bbox[1]
    uw, uh = ux1 - ux0, uy1 - uy0
    ch_h = CH_MARGIN + CH_MARGIN_LOW + (len(groups) - 1) * TRACK_PITCH + TRACK_W
    px, py = snap(uw + CAP_GAP), snap(uh + ch_h)
    top = Component(name or f"cdac{bits}b")

    def rect(x0, y0, x1, y1, layer):
        x0, y0, x1, y1 = (snap(v) for v in (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        ref = top << rectangle(size=(snap(x1 - x0), snap(y1 - y0)), layer=layer)
        ref.move((x0, y0))
        return ref

    def via2(x, y):
        rect(x - M2_PAD / 2, y - M2_PAD / 2, x + M2_PAD / 2, y + M2_PAD / 2, MET2)
        rect(x - VIA / 2, y - VIA / 2, x + VIA / 2, y + VIA / 2, VIA2)
        rect(x - M3_PAD / 2, y - M3_PAD / 2, x + M3_PAD / 2, y + M3_PAD / 2, MET3)

    # ---- unit capacitors (centre of row r, column c at (c*px, -r*py))
    centers = {}
    for r in range(R):
        for c in range(C):
            ref = top << unit
            ref.move((snap(c * px), snap(-r * py)))
            centers[(r, c)] = (snap(c * px), snap(-r * py))

    # ---- top plate: met4 strap per row + vertical spine in the middle column
    for r in range(R):
        y = -r * py
        rect(-STRAP_W / 2 + 0, y - STRAP_W / 2, (C - 1) * px + STRAP_W / 2, y + STRAP_W / 2, MET4)
    xs = (C // 2) * px if C > 1 else 0
    rect(xs - STRAP_W / 2, -(R - 1) * py, xs + STRAP_W / 2, 0, MET4)

    # ---- bottom plates: tabs -> met2 tracks in the channel below each row -> met3 trunks on the left
    track_y = {}            # (row, group) -> y of the track in the channel under that row
    for r in range(R):
        y_ch_top = -r * py + uy0                      # bottom edge of this row's met3 plates
        for gi, g in enumerate(groups):
            track_y[(r, g)] = snap(y_ch_top - CH_MARGIN - TRACK_W / 2 - gi * TRACK_PITCH)
    trunk_x = {g: snap(ux0 - TRUNK_CLEAR - gi * TRUNK_PITCH - TRUNK_W / 2) for gi, g in enumerate(groups)}
    used = {}               # group -> list of rows that have a track
    for r in range(R):
        right = {}
        for c in range(C):
            g = grid[r][c]
            x, y = centers[(r, c)]
            xt = snap(x - uw / 2 + 0.35 + TAB_W / 2)  # tab near the left edge of the unit
            yt = track_y[(r, g)]
            rect(xt - TAB_W / 2, y + uy0 + 0.3, xt + TAB_W / 2, yt - M3_PAD / 2, MET3)
            via2(xt, yt)
            right[g] = max(right.get(g, -1e9), xt)
        for g, xr in right.items():
            yt = track_y[(r, g)]
            rect(trunk_x[g] - M2_PAD / 2, yt - TRACK_W / 2, xr + M2_PAD / 2, yt + TRACK_W / 2, MET2)
            via2(trunk_x[g], yt)
            used.setdefault(g, []).append(r)
    for g, rows in used.items():
        y_hi = track_y[(min(rows), g)] + M3_PAD / 2
        y_lo = track_y[(max(rows), g)] - M3_PAD / 2
        y_hi = max(y_hi, uy1)                          # trunk reaches above the array for the pin
        rect(trunk_x[g] - TRUNK_W / 2, y_lo, trunk_x[g] + TRUNK_W / 2, y_hi, MET3)
        lx, ly = trunk_x[g], snap(y_hi - 0.3)
        rect(lx - TRUNK_W / 2, ly - 0.25, lx + TRUNK_W / 2, ly + 0.25, PIN[MET3])
        top.add_label(text=net_name(g), position=(lx, ly), layer=LBL[MET3])
    rect(xs - 0.3, -0.3, xs + 0.3, 0.3, PIN[MET4])
    top.add_label(text="top", position=(xs, 0), layer=LBL[MET4])

    bbox = top.bbox
    info = dict(bits=bits, side=side, rows=R, cols=C, grid=grid, pitch=(px, py),
                width=float(bbox[1][0] - bbox[0][0]), height=float(bbox[1][1] - bbox[0][1]),
                centroids={str(k): v for k, v in group_centroids(grid).items()})
    return top, info

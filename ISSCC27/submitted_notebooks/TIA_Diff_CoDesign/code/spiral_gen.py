# Parametric 2-port spiral inductor (L1 and Lb of the TIA) for SG13G2:
# TopMetal2 spiral, TopMetal1 underpass, Metal4 ground ring, via ports Metal4->TopMetal2.
# Usage: python spiral_gen.py start end seed
import gdspy
import cairosvg
import os
import random
import sys

TM1, TV2, TM2, M4 = 126, 133, 134, 50
PORT1, PORT2 = 201, 202
GND_MARGIN = 20   # coil bbox to ground ring spacing (um)
GND_WIDTH = 30
PORT_LEN = 4
D_MAX = 150

data_path = os.path.dirname(os.path.abspath(__file__)) + '/'
gdspy.library.use_current_library = False
lib = gdspy.GdsLibrary(name='BatchGen_SpiralL')
lib.precision = 5e-9


def via_array(cx, cy, sx, sy, size=0.9, space=1.06, enc=0.5, layer=TV2):
	nx = int((sx - 2 * enc + space) // (size + space))
	ny = int((sy - 2 * enc + space) // (size + space))
	x0 = cx - (nx * (size + space) - space) / 2
	y0 = cy - (ny * (size + space) - space) / 2
	return [gdspy.Rectangle((x0 + i * (size + space), y0 + j * (size + space)),
							(x0 + i * (size + space) + size, y0 + j * (size + space) + size), layer=layer)
			for i in range(nx) for j in range(ny)]


def via_stack(cx, cy, w):
	return [gdspy.Rectangle((cx - w / 2, cy - w / 2), (cx + w / 2, cy + w / 2), layer=l) for l in (TM1, TM2)] \
		+ via_array(cx, cy, w, w)


def spiral_points(Dx, Dy, p, n):
	pts = [(0.0, 0.0)]
	for t in range(n):
		pts += [(Dx - t * p, t * p), (Dx - t * p, Dy - t * p), (t * p, Dy - t * p), (t * p, (t + 1) * p)]
	return pts


def is_valid(w, s, n, Dx, Dy):
	p = w + s
	return w >= 3 and s >= 2 and n >= 1 and Dx >= (2 * n + 1) * p and Dy >= (2 * n + 1) * p


def create_spiral(w, s, n, Dx, Dy):
	"""Outer terminal (port 1) exits left at y=0; inner terminal (port 2) exits right via TM1 underpass."""
	p = w + s
	shapes = [gdspy.FlexPath(spiral_points(Dx, Dy, p, n), w, gdsii_path=True, layer=TM2).to_polygonset()]

	ex, ey = (n - 1) * p, n * p   # inner end
	xo = Dx + p                   # underpass exit, one pitch outside the outer turn
	shapes += via_stack(ex, ey, w) + via_stack(xo, ey, w)
	shapes.append(gdspy.Rectangle((ex, ey - w / 2), (xo, ey + w / 2), layer=TM1))

	bx0, by0, bx1, by1 = -w / 2, -w / 2, xo + w / 2, Dy + w / 2
	opening = gdspy.Rectangle((bx0 - GND_MARGIN, by0 - GND_MARGIN), (bx1 + GND_MARGIN, by1 + GND_MARGIN))
	outer = gdspy.Rectangle((bx0 - GND_MARGIN - GND_WIDTH, by0 - GND_MARGIN - GND_WIDTH),
							(bx1 + GND_MARGIN + GND_WIDTH, by1 + GND_MARGIN + GND_WIDTH))
	shapes.append(gdspy.boolean(outer, opening, 'not', layer=M4))

	xp1 = bx0 - GND_MARGIN - GND_WIDTH / 2
	xp2 = bx1 + GND_MARGIN + GND_WIDTH / 2
	shapes.append(gdspy.Rectangle((xp1 - PORT_LEN / 2, -w / 2), (0, w / 2), layer=TM2))
	shapes.append(gdspy.Rectangle((xo, ey - w / 2), (xp2 + PORT_LEN / 2, ey + w / 2), layer=TM2))
	shapes.append(gdspy.Rectangle((xp1 - PORT_LEN / 2, -w / 2), (xp1 + PORT_LEN / 2, w / 2), layer=PORT1))
	shapes.append(gdspy.Rectangle((xp2 - PORT_LEN / 2, ey - w / 2), (xp2 + PORT_LEN / 2, ey + w / 2), layer=PORT2))
	return shapes


def sample_params():
	while True:
		# w=2 leaves a single 0.9 um via that the 1 um EM mesh drops (open circuit)
		w = random.randint(3, 10)
		s = random.randint(2, 8)
		n = random.randint(1, 3)
		lo = (2 * n + 1) * (w + s)
		if lo > D_MAX:
			continue
		Dx = random.randint(max(lo, 20), D_MAX)
		Dy = random.randint(max(lo, 20), D_MAX)
		if is_valid(w, s, n, Dx, Dy):
			return [w, s, n, Dx, Dy]


def merge_layer(cell, layer):
	polys = cell.get_polygons((layer, 0))
	if not polys:
		return
	cell.remove_polygons(lambda pts, l, d: l == layer)
	cell.add(gdspy.boolean([gdspy.Polygon(p) for p in polys], None, 'or', layer=layer))


def one_sample(index, geo):
	cell = lib.new_cell(str(index))
	cell.add(create_spiral(*geo))
	for layer in (TM1, TM2):
		merge_layer(cell, layer)

	svg_name = data_path + f'SVG_TEMP/spiral_{os.getpid()}.svg'
	cell.write_svg(svg_name)
	cairosvg.svg2png(bytestring=open(svg_name).read().encode('utf-8'), write_to=data_path + f'PNG/{index}.png', scale=0.1)
	lib.write_gds(data_path + f'GDS/{index}.gds', [cell])
	with open(data_path + f'INFO/{index}.log', 'w') as f:
		f.write(str(list(geo)) + '\nspiral\n')
	lib.remove(cell)


def focus_params(centres):
	"""Active-learning sample: random perturbation of one of the co-design optimum geometries."""
	while True:
		w, s, n, Dx, Dy = random.choice(centres)
		w = min(max(w + random.randint(-2, 2), 3), 10)
		s = min(max(s + random.randint(-2, 2), 2), 8)
		n = min(max(n + random.choice([0, 0, 0, -1, 1]), 1), 3)
		Dx = int(round(Dx * random.uniform(0.75, 1.25)))
		Dy = int(round(Dy * random.uniform(0.75, 1.25)))
		if max(Dx, Dy) <= D_MAX and is_valid(w, s, n, Dx, Dy):
			return [w, s, n, Dx, Dy]


if __name__ == '__main__':
	start_num = int(sys.argv[1]) if len(sys.argv) > 1 else 0
	end_num = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
	random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 42)
	# optional: co-design result json -> half of the samples are drawn around its top geometries
	centres = None
	if len(sys.argv) > 4:
		import json
		best = json.load(open(sys.argv[4]))
		centres = [[r['params'][k] for k in ('w', 's', 'n', 'Dx', 'Dy')] for r in best['top5']]
	os.chdir(data_path)
	for index in range(start_num, end_num):
		if index % 100 == 0:
			print('Generating sample:', index)
		one_sample(index, focus_params(centres) if centres and index % 2 else sample_params())

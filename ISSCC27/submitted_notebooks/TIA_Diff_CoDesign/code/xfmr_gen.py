# Parametric planar transformer (interleaved or stacked broadside) for SG13G2.
# Secondary S: ns full turns + a partial turn of square TopMetal2 spiral. Primary P: m half-turn TopMetal2 rings
# (m = 1 single winding, m = 2 double winding, the two rings in parallel) interleaved with the outer secondary turns
# (tracks from outside: S0, P0, S1, P1, ..., then the remaining S turns).
# P and S start on the left side (P just above S); the windings stop on the RIGHT side and Pbar / Sbar leave straight
# to the right through short TopMetal1 underpasses below the outer secondary turns. Metal4 ground ring, 4 via ports
# Metal4->TopMetal2:  1 = P (-> Q1 emitter), 2 = Pbar (-> R2), 3 = S (-> Q1 base), 4 = Sbar (-> Vb).
# Current flows S -> Sbar counter-clockwise and P -> Pbar clockwise (opposite senses).
# Geometry: [w, s, ns, m, D, pb, sb, u, wp]  (secondary track width, spacing, secondary full turns, parallel primary rings, outer side
# [um], pb = Pbar leaves right (0) / down (1), sb = 1: stacked (broadside) variant, primary rings on TM1 directly below
# the outer secondary turns on TM2 (same centre lines), Pbar and Sbar both leave downwards (needs pb = 1), u = position of
# the Pbar end in % of D, wp = primary track width (optional, default = w); the track pitch is max(w, wp) + s)
# Usage: python xfmr_gen.py start end seed [geometry.json [--all-focus]]
import gdspy
import json
import cairosvg
import os
import random
import sys

TM1, TV2, TM2, M4 = 126, 133, 134, 50
PORT_LAYERS = (201, 202, 203, 204)
GND_MARGIN = 20   # coil bbox to ground ring spacing (um)
GND_WIDTH = 30
PORT_LEN = 4
D_MIN, D_MAX = 30, 200
U_MIN, U_MAX = 10, 70
W_MIN, W_MAX = 3, 20
KEYS = ('w', 's', 'ns', 'm', 'D', 'pb', 'sb', 'u', 'wp')

data_path = os.path.dirname(os.path.abspath(__file__)) + '/'
gdspy.library.use_current_library = False
lib = gdspy.GdsLibrary(name='BatchGen_Xfmr')
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


def offsets(w, s, ns, m, stack=0, wp=None):
	"""Pitch p, secondary turn offsets o[t] and primary ring offsets q[k] (distance of the centre line from the outer edge).
	stack = 1: the primary rings (TM1) lie directly below the outer secondary turns (TM2), same offsets."""
	p = max(w, w if wp is None else wp) + s
	if stack:
		return p, [t * p for t in range(int(ns))], [k * p for k in range(int(m))]
	kinds = []
	for t in range(int(ns)):
		kinds.append('S')
		if t < m:
			kinds.append('P')
	o = [i * p for i, c in enumerate(kinds) if c == 'S']
	q = [i * p for i, c in enumerate(kinds) if c == 'P']
	return p, o, q


def is_valid(w, s, ns, m, D, pb=0, sb=0, u=50, wp=None):
	wp = w if wp is None else wp
	p, o, q = offsets(w, s, ns, m, sb, wp)
	if not (W_MIN <= w <= W_MAX and W_MIN <= wp <= W_MAX and s >= 2 and 1 <= ns <= 3 and 1 <= m <= min(2, ns)
			and D_MIN <= D <= D_MAX and pb in (0, 1) and sb in (0, 1) and U_MIN <= u <= U_MAX):
		return False
	if sb and not pb:      # stacked variants: Pbar and Sbar both leave downwards
		return False
	fr = frame(w, s, ns, m, D, pb, sb, u, wp)
	if D - 2 * fr['oe'] < max(3 * p, 10):         # hole inside the last (partial) secondary turn
		return False
	if sb:          # Sbar bar left of the lowest Pbar bar and clear of the inner secondary turn
		return fr['x_se'] >= fr['oe'] + 2 * p and min(fr['x_pe']) >= q[-1] + 2 * p and max(fr['x_pe']) <= D - q[-1] - 2 * p
	if pb == 0:     # lowest Pbar end clear of the Sbar route (3 pitches) and below the top edge of its ring
		return fr['y_pe'][-1] >= fr['y_e'] + 3 * p and fr['y_pe'][0] <= D - q[-1] - 2 * p
	# Pbar ends on the bottom edge: right of the P start bar, left of the right edge
	return fr['x_pe'][0] >= q[-1] + 2 * p and fr['x_pe'][-1] <= D - q[-1] - 2 * p


def frame(w, s, ns, m, D, pb=0, sb=0, u=50, wp=None):
	"""Offsets, terminal positions and bounding box of the coil (without ground ring). sb = 1: stacked primary on TM1.
	pb = 0: P rings end on the right edge at heights y_pe; pb = 1: they continue along the bottom edge and end at x_pe."""
	wm = max(w, w if wp is None else wp)
	p, o, q = offsets(w, s, ns, m, sb, wp)
	oe = o[-1] + p                                  # offset of the last, partial secondary turn
	bx0, bx1, by0, by1 = -p - wm / 2, D + p + wm / 2, (-p - wm / 2 if pb else -wm / 2), D + wm / 2
	g = GND_MARGIN + GND_WIDTH / 2
	sg = -1 if sb else 1                            # stacked: inner ring ends further left (its TM1 bar must not cross the outer ring)
	x_pe = [u / 100 * D + sg * 2 * p * j for j in range(m)]
	return dict(p=p, o=o, q=q, oe=oe, bbox=(bx0, by0, bx1, by1), xpl=bx0 - g, xpr=bx1 + g, ypb=by0 - g,
				y_u=oe + 3 * p, y_e=oe + 2 * p, y_pe=[u / 100 * D - 2 * p * j for j in range(m)], x_pe=x_pe,
				x_se=min(x_pe) - 3 * p)


def xfmr_area(geo):
	"""Bounding box of the transformer (without ground ring), um^2."""
	bx0, by0, bx1, by1 = frame(*geo)['bbox']
	return (bx1 - bx0) * (by1 - by0)


def lead(layer, a, b, w):
	"""TopMetal2 lead from a to port centre b (axis-parallel) plus the port rectangle on `layer`."""
	h = PORT_LEN / 2
	(x0, y0), (x1, y1) = a, b
	if y0 == y1:
		sg = 1 if x1 > x0 else -1
		xa, xb = sorted((x0, x1 + sg * h))
		return [gdspy.Rectangle((xa, y0 - w / 2), (xb, y0 + w / 2), layer=TM2),
				gdspy.Rectangle((x1 - h, y0 - w / 2), (x1 + h, y0 + w / 2), layer=layer)]
	sg = 1 if y1 > y0 else -1
	ya, yb = sorted((y0, y1 + sg * h))
	return [gdspy.Rectangle((x0 - w / 2, ya), (x0 + w / 2, yb), layer=TM2),
			gdspy.Rectangle((x0 - w / 2, y1 - h), (x0 + w / 2, y1 + h), layer=layer)]


def create_xfmr(w, s, ns, m, D, pb=0, sb=0, u=50, wp=None):
	wp = w if wp is None else wp
	fr = frame(w, s, ns, m, D, pb, sb, u, wp)
	p, o, q, oe, y_u, y_e = fr['p'], fr['o'], fr['q'], fr['oe'], fr['y_u'], fr['y_e']
	shapes = []
	bar = lambda x0, y0, x1, y1: gdspy.Rectangle((x0, y0), (x1, y1), layer=TM1)

	# secondary spiral (TopMetal2), outer end S at (0, 0); after the last full turn a partial turn (bottom + right edge)
	# ends on the right side at (D - oe, y_e) = Sbar
	pts = [(0.0, 0.0)]
	for t, ot in enumerate(o):
		nxt = o[t + 1] if t + 1 < len(o) else oe
		pts += [(D - ot, ot), (D - ot, D - ot), (ot, D - ot), (ot, nxt)]
	pts += [(fr['x_se'], oe)] if sb else [(D - oe, oe), (D - oe, y_e)]
	shapes.append(gdspy.FlexPath(pts, w, gdsii_path=True, layer=TM2).to_polygonset())

	# primary rings (TopMetal2): P at the left edge (height y_u, just above the S start), clockwise over the top and down
	# the right edge. pb = 0: the ring ends there (heights y_pe, ring k ends 2 pitches lower than ring k-1) and Pbar leaves
	# to the right; pb = 1: the ring continues left along the bottom edge and Pbar leaves downwards (x_pe).
	# Pbar always leaves through a short TM1 underpass below the outer secondary turns.
	x_pe, y_pe = fr['x_pe'], fr['y_pe']
	ring_layer = TM1 if sb else TM2
	for k, qk in enumerate(q):
		if pb == 0:
			end = (D - qk, y_pe[k])
			route = [(D - qk, D - qk), end]
		else:
			end = (x_pe[k], qk)
			route = [(D - qk, D - qk), (D - qk, qk), end]
		shapes.append(gdspy.FlexPath([(qk, y_u), (qk, D - qk)] + route, wp, gdsii_path=True, layer=ring_layer).to_polygonset())
		if not sb:
			shapes += via_stack(qk, y_u, wp) + via_stack(*end, wp)
		if pb == 0:
			shapes.append(bar(end[0] - wp / 2, end[1] - wp / 2, D + p + wp / 2, end[1] + wp / 2))
			shapes += via_stack(D + p, end[1], wp)
		else:
			shapes.append(bar(end[0] - wp / 2, -p - wp / 2, end[0] + wp / 2, end[1] + wp / 2))
			shapes += via_stack(end[0], -p, wp)
	if m > 1 and pb == 0:
		shapes.append(gdspy.Rectangle((D + p - wp / 2, y_pe[-1] - wp / 2), (D + p + wp / 2, y_pe[0] + wp / 2), layer=TM2))
	if m > 1 and pb == 1:
		shapes.append(gdspy.Rectangle((min(x_pe) - wp / 2, -p - wp / 2), (max(x_pe) + wp / 2, -p + wp / 2), layer=TM2))
	lead_pb = lead(PORT_LAYERS[1], (D + p, y_pe[0]), (fr['xpr'], y_pe[0]), wp) if pb == 0 \
		else lead(PORT_LAYERS[1], (x_pe[0], -p), (x_pe[0], fr['ypb']), wp)

	# P: TM1 bar under the outer secondary turns to the left, joins the ring starts
	shapes += via_stack(-p, y_u, wp)
	shapes.append(bar(-p, y_u - wp / 2, max(q) + wp / 2, y_u + wp / 2))
	lead_p = lead(PORT_LAYERS[0], (-p, y_u), (fr['xpl'], y_u), wp)
	# S outer lead (left); Sbar: TM1 underpass from the inner end straight out to the right
	lead_s = lead(PORT_LAYERS[2], (0.0, 0.0), (fr['xpl'], 0.0), w)
	if sb:       # stacked: Sbar leaves downwards next to Pbar
		x_se = fr['x_se']
		shapes += via_stack(x_se, oe, w) + via_stack(x_se, -p, w)
		shapes.append(bar(x_se - w / 2, -p - w / 2, x_se + w / 2, oe + w / 2))
		lead_sb = lead(PORT_LAYERS[3], (x_se, -p), (x_se, fr['ypb']), w)
	else:
		shapes += via_stack(D - oe, y_e, w)
		shapes.append(bar(D - oe - w / 2, y_e - w / 2, D + p + w / 2, y_e + w / 2))
		shapes += via_stack(D + p, y_e, w)
		lead_sb = lead(PORT_LAYERS[3], (D + p, y_e), (fr['xpr'], y_e), w)
	shapes += lead_p + lead_pb + lead_s + lead_sb

	# Metal4 ground ring
	bx0, by0, bx1, by1 = fr['bbox']
	opening = gdspy.Rectangle((bx0 - GND_MARGIN, by0 - GND_MARGIN), (bx1 + GND_MARGIN, by1 + GND_MARGIN))
	outer = gdspy.Rectangle((bx0 - GND_MARGIN - GND_WIDTH, by0 - GND_MARGIN - GND_WIDTH),
							(bx1 + GND_MARGIN + GND_WIDTH, by1 + GND_MARGIN + GND_WIDTH))
	shapes.append(gdspy.boolean(outer, opening, 'not', layer=M4))
	return shapes


def repair(geo):
	"""Nearest valid layout for an optimiser proposal: fix m/pb, then enlarge D until the design rules hold."""
	geo = [int(round(v)) for v in geo]
	w, s, ns, m, D, pb, sb, u = geo[:8]
	wp = geo[8] if len(geo) > 8 else w
	m = min(m, ns, 2)
	pb = 1 if sb else pb
	for d in range(max(D, D_MIN), D_MAX + 1, 2):
		if is_valid(w, s, ns, m, d, pb, sb, u, wp):
			return [w, s, ns, m, d, pb, sb, u, wp]
	return [w, s, ns, m, D, pb, sb, u, wp]


def integer_return_positions(geo):
    """Require both return positions to lie on integer percentage points."""
    w, s, ns, m, D, pb, sb, u, *rest = geo
    if isinstance(u, bool) or u != int(u):
        return False
    fr = frame(w, s, ns, m, D, pb, sb, u, rest[0] if rest else w)
    us = 100 * (fr['x_se'] if sb else fr['y_e']) / D
    return abs(us - round(us)) <= 1e-9


def sample_params(stack_ok=True, max_attempts=100000):
	for _ in range(max_attempts):
		# w=2 leaves a single 0.9 um via that the 1 um EM mesh drops (open circuit)
		w = random.randint(W_MIN, W_MAX)
		wp = random.randint(W_MIN, W_MAX)
		s = random.randint(2, 6)
		ns = random.randint(1, 3)
		m = random.randint(1, min(2, ns))
		sb = random.randint(0, 1) if stack_ok else 0
		p, o, q = offsets(w, s, ns, m, sb, wp)
		oe = o[-1] + p
		lo = max(2 * oe + max(3 * p, 10), (oe + 5 * p + 2 * p * (m - 1)) / U_MAX * 100 + 1, D_MIN)
		if lo > D_MAX:
			continue
		D = random.randint(int(lo), D_MAX)
		pb = 1 if sb else random.randint(0, 1)
		u = random.randint(U_MIN, U_MAX)
		if is_valid(w, s, ns, m, D, pb, sb, u, wp) and integer_return_positions([w, s, ns, m, D, pb, sb, u, wp]):
			return [w, s, ns, m, D, pb, sb, u, wp]

	raise RuntimeError('No valid integer-position sample within the requested attempt budget')


def focus_params(centres, max_attempts=100000):
	"""Active-learning sample: random perturbation of one of the co-design optimum geometries."""
	for _ in range(max_attempts):
		w, s, ns, m, D, pb, sb, u, *rest = random.choice(centres)
		wp = rest[0] if rest else w
		w = min(max(w + random.randint(-2, 2), W_MIN), W_MAX)
		wp = min(max(wp + random.randint(-2, 2), W_MIN), W_MAX)
		s = min(max(s + random.randint(-1, 1), 2), 6)
		ns = min(max(ns + random.choice([0, 0, 0, -1, 1]), 1), 3)
		m = min(max(m + random.choice([0, 0, 0, -1, 1]), 1), min(2, ns))
		D = int(round(D * random.uniform(0.8, 1.2)))
		pb = pb if random.random() > 0.15 else 1 - pb
		sb = sb if random.random() > 0.1 else random.randint(0, 1)
		pb = 1 if sb else pb
		u = min(max(int(round(u)) + random.randint(-10, 10), U_MIN), U_MAX)
		if is_valid(w, s, ns, m, D, pb, sb, u, wp) and integer_return_positions([w, s, ns, m, D, pb, sb, u, wp]):
			return [w, s, ns, m, D, pb, sb, u, wp]
	raise RuntimeError('No valid integer-position focus sample within the requested attempt budget')


def merge_layer(cell, layer):
	polys = cell.get_polygons((layer, 0))
	if not polys:
		return
	cell.remove_polygons(lambda pts, l, d: l == layer)
	cell.add(gdspy.boolean([gdspy.Polygon(p) for p in polys], None, 'or', layer=layer))


def one_sample(index, geo, *, integer_positions=False):
	if integer_positions and not integer_return_positions(geo):
		raise ValueError('New samples require integer u and us percentages')
	cell = lib.new_cell(str(index))
	cell.add(create_xfmr(*geo))
	for layer in (TM1, TM2):
		merge_layer(cell, layer)

	svg_name = data_path + f'SVG_TEMP/xfmr_{os.getpid()}.svg'
	cell.write_svg(svg_name)
	cairosvg.svg2png(bytestring=open(svg_name).read().encode('utf-8'), write_to=data_path + f'PNG/{index}.png', scale=0.1)
	lib.write_gds(data_path + f'GDS/{index}.gds', [cell])
	if integer_positions:
		from generate_gds import integer_layout_inputs
		import xfmr_schema as schema
		metadata = schema.record(geo, generator='xfmr_gen.py', gds_file=f'{index}.gds')
		metadata['physical_inputs'] = integer_layout_inputs(data_path + f'GDS/{index}.gds', geo)
		metadata['parameters']['u'] = metadata['physical_inputs']['u']
		with open(data_path + f'INFO/{index}.json', 'w') as stream:
			json.dump(metadata, stream, indent=2)
	with open(data_path + f'INFO/{index}.log', 'w') as f:
		f.write(str(list(geo)) + '\nxfmr\n')
	lib.remove(cell)


if __name__ == '__main__':
	start_num = int(sys.argv[1]) if len(sys.argv) > 1 else 0
	end_num = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
	random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 42)
	# optional: co-design result json -> half of the samples are drawn around its top transformer geometries
	centres = None
	if len(sys.argv) > 4 and not sys.argv[4].startswith('--'):
		import json
		best = json.load(open(sys.argv[4]))
		centres = [[r['params']['x_' + k] for k in KEYS] for r in best['top5']]
	all_focus = '--all-focus' in sys.argv
	os.chdir(data_path)
	if '--geos' in sys.argv:      # geometries from an explicit geometry file
		import json
		geos = json.load(open(sys.argv[sys.argv.index('--geos') + 1]))
		for j, geo in enumerate(geos):
			if (start_num + j) % 100 == 0:
				print('Generating sample:', start_num + j)
			one_sample(start_num + j, geo)
		sys.exit()
	for index in range(start_num, end_num):
		if index % 100 == 0:
			print('Generating sample:', index)
		one_sample(index, focus_params(centres) if centres and (all_focus or index % 2) else sample_params(), integer_positions=True)

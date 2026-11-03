"""Stacked transformer with a continuous series spiral primary on TopMetal1."""
import argparse
import json
import os

import gdspy
import numpy as np

import xfmr_gen as X
import xfmr_model as M

HERE = os.path.dirname(os.path.abspath(__file__))
M5, TV1 = 67, 125
gdspy.library.use_current_library = False
lib = gdspy.GdsLibrary(name='SeriesPrimary')
lib.precision = 5e-9


def valid(w, s, np_, ns, D):
	p = w + s
	return (5 <= w <= 10 and s >= 3 and 1 <= np_ <= 3 and 1 <= ns <= 3 and 30 <= D <= 200
			and D >= max(2 * ns + 3, 2 * np_ + 1) * p)


def via_m5_stack(cx, cy, w):
	return [gdspy.Rectangle((cx - w / 2, cy - w / 2), (cx + w / 2, cy + w / 2), layer=layer)
			for layer in (X.TM1, X.TM2, M5)] + X.via_array(cx, cy, w, w) + X.via_array(cx, cy, w, w, layer=TV1)


def paths(w, s, np_, ns, D):
	"""Return primary and secondary conductor segments for the partial-inductance screen."""
	p = w + s
	left = -2 * p - w / 2 - X.GND_MARGIN - X.GND_WIDTH / 2
	right = D + 2 * p + w / 2 + X.GND_MARGIN + X.GND_WIDTH / 2
	primary = [(left, D, -2 * p, D, 0.0, 1.0, w), (-2 * p, D, 0, D, -M.DZ, 1.0, w)]
	points = [(0, D)]
	for turn in range(np_):
		o = turn * p
		points.extend([(o, D - o), (D - o, D - o), (D - o, o), (o + p, o)])
	primary.extend([(*a, *b, -M.DZ, 1.0, w) for a, b in zip(points[:-1], points[1:])])
	primary.extend([(np_ * p, (np_ - 1) * p, np_ * p, -p, -M.DZ, 1.0, w),
						(np_ * p, -p, -2 * p, -p, -M.DZ, 1.0, w),
						(-2 * p, -p, left, -p, 0.0, 1.0, w)])

	oe = ns * p
	cx, cy, jump_x = D / 2, D / 2, D + 2 * p
	points = [(left, 0), (0, 0)]
	for turn in range(ns):
		o = turn * p
		nxt = (turn + 1) * p
		points.extend([(D - o, o), (D - o, D - o), (o, D - o), (o, nxt)])
	points.extend([(D - oe, oe), (cx, cy)])
	secondary = [(*a, *b, 0.0, 1.0, w) for a, b in zip(points[:-1], points[1:])]
	secondary.extend([(cx, cy, jump_x, cy, -M.DZ - 2.095, 1.0, w), (jump_x, cy, right, cy, 0.0, 1.0, w)])
	return primary, secondary


def estimate(geo):
	p, s = paths(*geo)
	def inductance(a, b):
		return sum(M.selfl(x) for x in a) + sum(M.mutual(a[i], a[j]) for i in range(len(a)) for j in range(len(a)) if i != j) if a is b \
			else sum(M.mutual(x, y) for x in a for y in b)
	lp, ls, mutual = inductance(p, p), inductance(s, s), inductance(p, s)
	return dict(Lp_nH=lp * 1e9, Ls_nH=ls * 1e9, k=abs(mutual) / np.sqrt(abs(lp * ls)))


def create_xfmr(w, s, np_, ns, D):
	p = w + s
	primary, secondary = paths(w, s, np_, ns, D)
	primary_points = [(-2 * p, D), (0, D)]
	for turn in range(np_):
		o = turn * p
		primary_points.extend([(o, D - o), (D - o, D - o), (D - o, o), (o + p, o)])
	primary_points.extend([(np_ * p, -p), (-2 * p, -p)])
	oe = ns * p
	cx, cy, jump_x = D / 2, D / 2, D + 2 * p
	left = -2 * p - w / 2 - X.GND_MARGIN - X.GND_WIDTH / 2
	right = D + 2 * p + w / 2 + X.GND_MARGIN + X.GND_WIDTH / 2
	secondary_points = [(left, 0), (0, 0)]
	for turn in range(ns):
		o = turn * p
		secondary_points.extend([(D - o, o), (D - o, D - o), (o, D - o), (o, o + p)])
	secondary_points.extend([(D - oe, oe), (cx, cy)])
	shapes = [gdspy.FlexPath(primary_points, w, gdsii_path=True, layer=X.TM1).to_polygonset(),
		  gdspy.FlexPath(secondary_points, w, gdsii_path=True, layer=X.TM2).to_polygonset(),
		  gdspy.FlexPath([(cx, cy), (jump_x, cy)], w, gdsii_path=True, layer=M5).to_polygonset()]
	shapes.extend(X.via_stack(-2 * p, D, w) + X.via_stack(-2 * p, -p, w))
	shapes.extend(via_m5_stack(cx, cy, w) + via_m5_stack(jump_x, cy, w))
	shapes.extend(X.lead(X.PORT_LAYERS[0], (-2 * p, D), (left, D), w))
	shapes.extend(X.lead(X.PORT_LAYERS[1], (-2 * p, -p), (left, -p), w))
	shapes.extend(X.lead(X.PORT_LAYERS[2], (0, 0), (left, 0), w))
	shapes.extend(X.lead(X.PORT_LAYERS[3], (jump_x, cy), (right, cy), w))
	bx0, by0, bx1, by1 = -2 * p - w / 2, -p - w / 2, D + 2 * p + w / 2, D + w / 2
	opening = gdspy.Rectangle((bx0 - X.GND_MARGIN, by0 - X.GND_MARGIN), (bx1 + X.GND_MARGIN, by1 + X.GND_MARGIN))
	outer = gdspy.Rectangle((bx0 - X.GND_MARGIN - X.GND_WIDTH, by0 - X.GND_MARGIN - X.GND_WIDTH),
							(bx1 + X.GND_MARGIN + X.GND_WIDTH, by1 + X.GND_MARGIN + X.GND_WIDTH))
	shapes.append(gdspy.boolean(outer, opening, 'not', layer=X.M4))
	return shapes


def write_sample(index, geo):
	cell = lib.new_cell(str(index))
	cell.add(create_xfmr(*geo))
	for layer in (X.TM1, X.TM2, M5):
		X.merge_layer(cell, layer)
	cell.write_svg(f'{HERE}/SVG_TEMP/xfmr_series_{index}.svg')
	import cairosvg
	cairosvg.svg2png(url=f'{HERE}/SVG_TEMP/xfmr_series_{index}.svg', write_to=f'{HERE}/PNG/{index}.png', scale=0.1)
	lib.write_gds(f'{HERE}/GDS/{index}.gds', [cell])
	with open(f'{HERE}/INFO/{index}.log', 'w') as f:
		f.write(str(list(geo)) + '\nxfmr\nseries_primary\n')
	lib.remove(cell)


def scan():
	candidates = []
	for w in (5, 7, 10):
		for s in (3, 5, 8):
			for np_ in (2, 3):
				for ns in (2, 3):
					for D in range(50, 151, 2):
						geo = [w, s, np_, ns, D]
						if not valid(*geo):
							continue
						m = estimate(geo)
						m['geo'] = geo
						p = w + s
						m['area_um2'] = (D + 4 * p + w) * (D + p + w)
						m['score'] = ((m['Lp_nH'] - 0.442) / 0.12) ** 2 + ((m['Ls_nH'] - 0.511) / 0.15) ** 2 + ((m['k'] - 0.433) / 0.10) ** 2 + 0.15 * m['area_um2'] / 23556
						candidates.append(m)
	candidates.sort(key=lambda r: r['score'])
	with open(f'{HERE}/results/series_candidates.json', 'w') as f:
		json.dump(candidates, f, indent=1)
	for row in candidates[:20]:
		print(row)
	for w in (5, 7, 10):
		for np_ in (2, 3):
			for ns in (2, 3):
				group = [r for r in candidates if r['geo'][:4] == [w, r['geo'][1], np_, ns]]
				if group:
					print('representative', group[0])


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--scan', action='store_true')
	parser.add_argument('--generate', type=int, default=0)
	parser.add_argument('--start', type=int, default=93000)
	args = parser.parse_args()
	os.chdir(HERE)
	if args.scan:
		scan()
	if args.generate:
		candidates = json.load(open(f'{HERE}/results/series_candidates.json'))
		rows = []
		for w in (5, 7, 10):
			for np_ in (2, 3):
				for ns in (2, 3):
					group = [r for r in candidates if r['geo'][0] == w and r['geo'][2:4] == [np_, ns]]
					if group:
						rows.append(group[0])
		rows = rows[:args.generate]
		for i, row in enumerate(rows):
			index = args.start + i
			write_sample(index, row['geo'])
			print(index, row)
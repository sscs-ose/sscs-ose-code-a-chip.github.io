# Quasi-static (partial-inductance) estimate of Lp, Ls, k of a layout from xfmr_gen.py geometry.
# Filament model: every centre-line segment carries its current, TM1 bars lie DZ below TM2. Parallel segments only (orthogonal M = 0).
# The distance of two segments is the geometric mean distance (GMD) of their strip cross-sections (widths wp / w).
import os
import sys
import numpy as np
import xfmr_gen as X

MU0 = 4e-7 * np.pi
DZ = 4.0        # um, TM2 -> TM1 centre distance
TH = 3.0        # um, metal thickness used in the self term


def paths(w, s, ns, m, D, pb=0, sb=0, u=50, wp=None):
	"""-> (P segments, S segments); segment = (x0, y0, x1, y1, z, current weight, track width).
	P current flows P -> Pbar, S current S -> Sbar."""
	wp = w if wp is None else wp
	fr = X.frame(w, s, ns, m, D, pb, sb, u, wp)
	if sb == 2:        # full-overlap loops: S clockwise (TM2) from S to Sbar, P counter-clockwise (TM1) from P to Pbar
		x1, x2, dx, yj, ypb = fr['x1'], fr['x2'], fr['dx'], fr['yj'], fr['ypb']
		sp = [(x1, ypb), (x1, 0), (0, 0), (0, D), (D, D), (D, 0), (x2, 0), (x2, ypb)]
		S = [(*a, *b, 0.0, 1.0, w) for a, b in zip(sp[:-1], sp[1:])]
		pp = [((x2 + dx, ypb), (x2 + dx, yj), 0.0), ((x2 + dx, yj), (x2, yj), -DZ), ((x2, yj), (x2, 0), -DZ), ((x2, 0), (D, 0), -DZ),
			  ((D, 0), (D, D), -DZ), ((D, D), (0, D), -DZ), ((0, D), (0, 0), -DZ), ((0, 0), (x1, 0), -DZ), ((x1, 0), (x1, yj), -DZ),
			  ((x1, yj), (x1 - dx, yj), -DZ), ((x1 - dx, yj), (x1 - dx, ypb), 0.0)]
		return [(*a, *b, z, 1.0, wp) for a, b, z in pp], S
	p, o, q, oe, y_u, y_e, y_pe = fr['p'], fr['o'], fr['q'], fr['oe'], fr['y_u'], fr['y_e'], fr['y_pe']
	S, P = [], []
	pts = [(0.0, 0.0)]
	for t, ot in enumerate(o):
		nxt = o[t + 1] if t + 1 < len(o) else oe
		pts += [(D - ot, ot), (D - ot, D - ot), (ot, D - ot), (ot, nxt)]
	pts += [(fr['x_se'], oe)] if sb else [(D - oe, oe), (D - oe, y_e)]
	for a, b in zip(pts[:-1], pts[1:]):
		S.append((*a, *b, 0.0, 1.0, w))
	if sb:
		S.append((fr['x_se'], oe, fr['x_se'], -p, -DZ, 1.0, w))             # Sbar underpass (TM1), downwards
	else:
		S.append((D - oe, y_e, D + p, y_e, -DZ, 1.0, w))                   # Sbar underpass (TM1)
	for k, qk in enumerate(q):
		zr = -DZ if sb else 0.0                                     # stacked variant: rings on TM1 below the secondary
		if pb == 0:
			r = [(qk, y_u), (qk, D - qk), (D - qk, D - qk), (D - qk, y_pe[k])]
		else:
			r = [(qk, y_u), (qk, D - qk), (D - qk, D - qk), (D - qk, qk), (fr['x_pe'][k], qk)]
		for a, b in zip(r[:-1], r[1:]):
			P.append((*a, *b, zr, 1.0 / m, wp))
		if pb == 0:                                                 # Pbar underpass (TM1)
			P.append((D - qk, y_pe[k], D + p, y_pe[k], -DZ, 1.0 / m, wp))
		else:
			P.append((fr['x_pe'][k], qk, fr['x_pe'][k], -p, -DZ, 1.0 / m, wp))
	for j in range(m - 1):                                          # TM2 strap that merges the ring ends
		if pb == 0:
			P.append((D + p, y_pe[j + 1], D + p, y_pe[j], 0.0, (m - 1 - j) / m, wp))
		else:
			P.append((fr['x_pe'][j + 1], -p, fr['x_pe'][j], -p, 0.0, (m - 1 - j) / m, wp))
	# P bar (TM1): current of ring j enters at x = q_j, so the weight decreases inwards
	xs = [-p] + sorted(q)
	for j in range(len(q)):
		P.append((xs[j], y_u, xs[j + 1], y_u, -DZ, 1.0 - j / m, wp))
	# port leads (TM2): current enters at P / S and leaves at Pbar / Sbar
	P.append((fr['xpl'], y_u, -p, y_u, 0.0, 1.0, wp))
	S.append((fr['xpl'], 0.0, 0.0, 0.0, 0.0, 1.0, w))
	P.append((D + p, y_pe[0], fr['xpr'], y_pe[0], 0.0, 1.0, wp) if pb == 0 else (fr['x_pe'][0], -p, fr['x_pe'][0], fr['ypb'], 0.0, 1.0, wp))
	S.append((fr['x_se'], -p, fr['x_se'], fr['ypb'], 0.0, 1.0, w) if sb else (D + p, y_e, fr['xpr'], y_e, 0.0, 1.0, w))
	return P, S


def _G(u, d):
	return u * np.arcsinh(u / d) - np.sqrt(u * u + d * d)


def _phi(t, z):
	r = t * t + z * z + 1e-18
	return 0.25 * r * np.log(r) - 0.25 * r - 0.5 * t * t + z * t * np.arctan(t / z) - 0.5 * z * z * np.log(r)


def gmd(wa, wb, lat, z):
	"""Geometric mean distance [um] of two strips: widths wa, wb, centre offset lat (lateral) and z (vertical)."""
	z = max(abs(z), 1e-6)
	b0 = lat - wb / 2                      # strip a spans [-wa/2, wa/2], strip b spans [b0, b0 + wb]
	f = lambda t: _phi(t, z)
	ln_gmd = (f(wa / 2 - b0) - f(-wa / 2 - b0) - f(wa / 2 - b0 - wb) + f(-wa / 2 - b0 - wb)) / (wa * wb)
	return float(np.exp(ln_gmd))


def mutual(a, b):
	"""Partial mutual inductance [H] of two segments (signed by direction and weights)."""
	ax0, ay0, ax1, ay1, za, ia, wa = a
	bx0, by0, bx1, by1, zb, ib, wb = b
	adx, ady, bdx, bdy = ax1 - ax0, ay1 - ay0, bx1 - bx0, by1 - by0
	horiz_a, horiz_b = abs(adx) > abs(ady), abs(bdx) > abs(bdy)
	if horiz_a != horiz_b:
		return 0.0
	if horiz_a:
		sa, sb_ = np.sign(adx), np.sign(bdx)
		a1, a2 = sorted((ax0, ax1)); b1, b2 = sorted((bx0, bx1)); lat = by0 - ay0
	else:
		sa, sb_ = np.sign(ady), np.sign(bdy)
		a1, a2 = sorted((ay0, ay1)); b1, b2 = sorted((by0, by1)); lat = bx0 - ax0
	d = gmd(wa, wb, lat, za - zb)
	g = _G(a2 - b1, d) - _G(a1 - b1, d) - _G(a2 - b2, d) + _G(a1 - b2, d)
	return MU0 / (4 * np.pi) * g * 1e-6 * sa * sb_ * ia * ib


def selfl(seg):
	l = (abs(seg[2] - seg[0]) + abs(seg[3] - seg[1])) * 1e-6
	if l == 0:
		return 0.0
	wt = (seg[6] + TH) * 1e-6
	return MU0 / (2 * np.pi) * l * (np.log(2 * l / wt) + 0.5 + 0.2235 * wt / l) * seg[5] ** 2


def lmat(geo):
	P, S = paths(*geo)
	def tot(A, B):
		if A is B:
			return sum(selfl(a) for a in A) + sum(mutual(A[i], A[j]) for i in range(len(A)) for j in range(len(A)) if i != j)
		return sum(mutual(a, b) for a in A for b in B)
	return tot(P, P), tot(S, S), tot(P, S)


def k_model(geo):
	"""Lp, Ls [H] and k(P,Sbar) (positive for the opposite winding senses of xfmr_gen)."""
	lp, ls, m = lmat(geo)
	return lp, ls, -m / np.sqrt(lp * ls)


if __name__ == '__main__':
	data = [([4, 6, 1, 1, 78, 0, 0, 50], .275, .349, -.022), ([4, 5, 1, 1, 95, 1, 0, 46], .340, .434, .219), ([6, 6, 1, 1, 93, 0, 0, 50], .305, .392, -.016),
			([4, 2, 3, 2, 121, 0, 0, 50], .381, 2.089, .317), ([6, 4, 1, 1, 78, 1, 1, 47], .239, .270, .184)]
	for g, lp, ls, k in data:
		a, b, c = k_model(g)
		print(g, f'EM Lp {lp:.3f} Ls {ls:.3f} k {k:+.3f} | model Lp {a*1e9:.3f} Ls {b*1e9:.3f} k {c:+.3f}')

# ngspice testbench of the transformer-based RGC TIA in SG13G2, VCC = 2.5 V.
# Stage 1 (transformer RGC input): Iin || Cpd -> L1 -> Q1 emitter; transformer primary Lp (P = e1, Pbar = r2) to R2;
#   secondary Ls (S = Q1 base, next to P; Sbar = Vb), S->Sbar flows opposite to P->Pbar, so k(P,Sbar) > 0 -> gm' = (1 + n k) gm.
#   R1 = Q1 collector load. EM 4-port order: 1 = P (e1), 2 = Pbar (r2), 3 = S (b1), 4 = Sbar (vb).
# Stage 2 (optional, '123'): Q2 common emitter with shunt feedback Rf (node A = c1 -> node B = b2), R4 load,
#   emitter R3 || C1 (MIM).
# Stage 3 (output buffer): single-ended -> differential pair Q3/Q4 (Nx = N3) with tail current IT; Q4 base = low-pass
#   replica of the Q3 base (offset free), loads VCC - R (50 ohm back termination) - Lb - collector, AC-coupled 50 ohm.
# Passive models: None | ('ideal', ...) | ('sp', f, S): 2-port spiral (L1, Lb) or 4-port transformer surrogate/EM data.
import os
import re
import shutil
import subprocess
import tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NGSPICE = os.path.join(HERE, 'run_ngspice.sh')

VCC = 2.5
CPD = 220e-15                       # 150 fF photodiode + 70 fF pad
R_LOAD = 50.0                       # buffer back-termination resistor
RPPD_RSH = 260.0
CMIM_AREA = 1.5e-15                 # F/um^2 (cornerCAP.lib cap_carea)
F_REF = 1e9
LE = 0.9                            # emitter length of one npn13G2 emitter [um]
JC_WIN = (1.0, 3.0)                 # mA/um; collector-current-density design window
BV_CE = 1.7                         # npn13G2 BVceo

# differential Zt (single-ended PD input, 2 x 50 ohm load), input-referred noise current, total power
SPEC = dict(zt_dbohm=59.0, bw_ghz=32.0, peak_db=1.0, gd_pp_ps=10.0, noise_pa=21.3, power_mw=28.2)
MARGIN = dict(zt_dbohm=0.1, peak_db=0.1, gd_pp_ps=0.5, noise_pa=0.3, power_mw=0.3)   # optimisation target margins


def rppd_wl(r_ohm):
	"""rppd width/length for r_ohm: R ~ rsh*L/W + 2*rzspec/W (rzspec = 35e-6 ohm*m); wider for small R (L >= ~2 um)."""
	w = float(np.clip(2e-6 * 300.0 / r_ohm, 2e-6, 20e-6))
	return w, max((r_ohm - 2 * 35e-6 / w) * w / RPPD_RSH, 0.5e-6)


def res(name, a, b, r_ohm):
	w, l = rppd_wl(r_ohm)
	return f'X{name} {a} {b} 0 rppd w={w:.4e} l={l:.4e}'


def cmim(name, a, b, c):
	side = np.sqrt(max(c, 10e-15) / CMIM_AREA)
	return f'X{name} {a} {b} cap_cmim w={side:.3f}u l={side:.3f}u'


def sp_subckt(name, f, s):
	"""N-port S-parameter table -> ngspice XSPICE xfer subckt (pins: p1..pN ref); helper resistors are noiseless."""
	n = s.shape[1]
	ref = f'n{n + 1}'
	out = [f'.subckt {name} ' + ' '.join(f'n{i + 1}' for i in range(n)) + f' {ref}']
	for i in range(n):
		out += [f'R{i+1}N n{i+1} a{i+1}_0 -50 noisy=0', f'R{i+1}P a{i+1}_0 a{i+1}_1 100 noisy=0']
	for i in range(n):
		for j in range(n):
			nxt = ref if j == n - 1 else f'a{i+1}_{j+2}'
			k = i * n + j + 1
			out.append(f'A{i+1}_{j+1} %vd(a{j+1}_0 {ref}) %vd(a{i+1}_{j+1} {nxt}) xfer{k}')
			out.append(f'.model xfer{k} xfer R_I=true table=[')
			out += [f'+ {fk:.6e}Hz {s[q, i, j].real:.6e} {s[q, i, j].imag:.6e}' for q, fk in enumerate(f)]
			out.append('+ ]')
	out.append('.ends')
	return '\n'.join(out)


def sp_instance(tag, subckt, nodes, dc_pairs):
	"""xfer blocks have no DC path -> DC through 1 mH between the winding ends, xfer AC-coupled via 1 uF."""
	out = [f'Ldc{tag}{k} {a} {b} 1m' for k, (a, b) in enumerate(dc_pairs)]
	for k, nd in enumerate(nodes, 1):
		out += [f'Cb{tag}{k} {nd} lp{tag}{k} 1u', f'Rg{tag}{k} lp{tag}{k} 0 1G noisy=0']
	out.append(f'X{tag} ' + ' '.join(f'lp{tag}{k}' for k in range(1, len(nodes) + 1)) + f' 0 {subckt}')
	return out


def inductor(tag, a, b, model):
	"""Two-terminal coil a -> b (a = spiral port 1 = outer end)."""
	if model is None:
		return [f'V{tag} {a} {b} dc 0']
	if model[0] == 'ideal':
		return [f'L{tag} {a} {b} {model[1]:.4e}']
	return sp_instance(tag, f'sp{tag}', (a, b), [(a, b)])


def stage_nodes(stages):
	return 'b2' if '2' in stages else 'c1'


def netlist(p, xf=None, l1=None, lb=None, stages='13'):
	"""p: dict(N1, R1, R2, VB, N3, IT [, N2, R4, RF, R3, C1]); xf: None | ('ideal', Lp, Ls, k) | ('sp', f, S4)."""
	bin_ = stage_nodes(stages)
	lines = ['* SG13G2 transformer-RGC TIA', '.LIB cornerRES.lib res_typ', '.LIB cornerHBT.lib hbt_typ',
			 '.LIB cornerCAP.lib cap_typ', '']
	if xf is not None and xf[0] == 'sp':
		lines += [sp_subckt('spXF', xf[1], xf[2]), '']
	for tag, mdl in (('L1', l1), ('LBn', lb), ('LBp', lb)):
		if mdl is not None and mdl[0] == 'sp':
			lines += [sp_subckt(f'sp{tag}', mdl[1], mdl[2]), '']
	lines += [f'VCC vcc 0 dc {VCC}', f'VB vb 0 dc {p["VB"]:.4f}', 'Iin 0 pd dc 0 ac 1', f'Cpd pd 0 {CPD}']
	# stage 1: L1, Q1 (CB), transformer, R1, R2
	lines += inductor('L1', 'pd', 'e1', l1)
	lines += ['VQ1 c1 c1q dc 0', f'XQ1 c1q b1 e1 0 npn13G2 Nx={int(p["N1"])}',
			  res('R1', 'vcc', 'c1', p['R1']), res('R2', 'r2', '0', p['R2'])]
	if xf is None:
		lines += ['VXP e1 r2 dc 0', 'VXS vb b1 dc 0']
	elif xf[0] == 'ideal':
		lines += [f'LXP e1 r2 {xf[1]:.4e}', f'LXS vb b1 {xf[2]:.4e}', f'KX LXP LXS {xf[3]:.4f}']
	else:
		lines += sp_instance('XF', 'spXF', ('e1', 'r2', 'b1', 'vb'), [('e1', 'r2'), ('b1', 'vb')])
	# stage 2: shunt-feedback CE gain stage
	if '2' in stages:
		lines += ['VQ2 b2 b2q dc 0', f'XQ2 b2q c1 e2 0 npn13G2 Nx={int(p["N2"])}',
				  res('R4', 'vcc', 'b2', p['R4']), res('RF', 'c1', 'b2', p['RF']), res('R3', 'e2', '0', p['R3']),
				  cmim('C1', 'e2', '0', p['C1'])]
	# stage 3: differential output buffer (Q3 input side drives outn); Q4 base = buffered low-pass replica of the Q3 base
	lines += [f'Rlp {bin_} vlp 1k', 'Clp vlp 0 1u', 'Ebuf vbuf 0 vlp 0 1',
			  'VQ3 cn cnq dc 0', f'XQ3 cnq {bin_} t 0 npn13G2 Nx={int(p["N3"])}',
			  'VQ4 cp cpq dc 0', f'XQ4 cpq vbuf t 0 npn13G2 Nx={int(p["N3"])}',
			  f'IT t 0 dc {p["IT"]:.4e}',
			  res('RLn', 'vcc', 'rn', R_LOAD), res('RLp', 'vcc', 'rp', R_LOAD)]
	lines += inductor('LBn', 'rn', 'cn', lb) + inductor('LBp', 'rp', 'cp', lb)
	lines += ['Coutn cn outn 1n', 'RLDn outn 0 50', 'Coutp cp outp 1n', 'RLDp outp 0 50']
	nodes = ['pd', 'e1', 'b1', 'c1', 'r2', 't', 'cn', 'cp', 'vbuf'] + (['b2', 'e2'] if '2' in stages else [])
	currents = ['vcc', 'vb', 'vq1', 'vq3', 'vq4'] + (['vq2'] if '2' in stages else [])
	lines += ['', '.control', 'set filetype=ascii', 'op',
			  'print ' + ' '.join(f'v({n})' for n in nodes) + ' ' + ' '.join(f'i({c})' for c in currents),
			  'ac lin 199 1G 100G', 'wrdata tia_ac.txt v(outp,outn)',
			  'noise v(outp,outn) Iin lin 99 1G 50G', 'setplot noise1',
			  'wrdata tia_noise.txt inoise_spectrum', 'quit', '.endc', '.end']
	return '\n'.join(lines)


def run(p, xf=None, l1=None, lb=None, stages='13', keep=None):
	with tempfile.TemporaryDirectory(dir=os.environ.get('TIA_TMP', '/tmp')) as d:
		cir = os.path.join(d, 'tia.cir')
		shutil.copy(os.path.join(HERE, '.spiceinit'), d)
		txt = netlist(p, xf, l1, lb, stages)
		with open(cir, 'w') as fo:
			fo.write(txt)
		r = subprocess.run(['bash', NGSPICE, cir], cwd=d, capture_output=True, text=True, timeout=600)
		if keep:
			with open(keep, 'w') as fo:
				fo.write(txt + '\n\n* ---- log ----\n* ' + r.stdout.replace('\n', '\n* '))
		try:
			ac = np.loadtxt(os.path.join(d, 'tia_ac.txt'))
			nz = np.loadtxt(os.path.join(d, 'tia_noise.txt'))
		except (OSError, ValueError):
			return None
	op = {k: float(v) for k, v in re.findall(r'^((?:v|i)\(\w+\)) = ([-+0-9.eE]+)', r.stdout, re.M)}
	m = evaluate(ac[:, 0], ac[:, 1] + 1j * ac[:, 2], nz[:, 0], nz[:, 1], op)
	m['stages'] = stages
	return m


def evaluate(f, zt, fn, inoise, op):
	mag = np.abs(zt)
	z0 = np.interp(F_REF, f, mag)
	above = np.where((f > F_REF) & (mag < z0 / np.sqrt(2)))[0]
	if len(above):
		k = above[0]
		bw = np.interp(z0 / np.sqrt(2), [mag[k], mag[k - 1]], [f[k], f[k - 1]])
	else:
		bw = f[-1]
	peak = 20 * np.log10(mag[f <= bw].max() / z0)
	ph = np.unwrap(np.angle(zt))
	gd = -np.gradient(ph, 2 * np.pi * f)
	band = (f >= F_REF) & (f <= min(bw, 26.0e9))
	gd_pp = (gd[band].max() - gd[band].min()) if band.sum() > 2 else np.inf
	nb = (fn <= min(bw, fn[-1]))
	in_avg = np.sqrt(np.trapz(inoise[nb] ** 2, fn[nb]) / (fn[nb][-1] - fn[nb][0])) if nb.sum() > 2 else np.inf
	power = VCC * abs(op.get('i(vcc)', np.nan)) + abs(op.get('i(vb)', 0.0)) * op.get('v(b1)', 0.0)
	return dict(zt_dbohm=20 * np.log10(z0), bw_ghz=bw / 1e9, peak_db=peak, gd_pp_ps=gd_pp * 1e12,
				noise_pa=in_avg * 1e12, power_mw=power * 1e3, op=op, f=f, zt=zt, fn=fn, inoise=inoise)


def headroom(op):
	"""Bias violation [V]: no saturation (Vbc <= 0.2 V), Vce <= BVceo, tail current source headroom >= 0.5 V."""
	v = lambda n: op.get(f'v({n})', 0.0)
	two = 'v(b2)' in op
	bin_ = v('b2') if two else v('c1')
	viol = [v('b1') - v('c1') - 0.2, v('c1') - v('e1') - BV_CE,
			bin_ - v('cn') - 0.2, v('cn') - v('t') - BV_CE, v('cp') - v('t') - BV_CE, 0.5 - v('t')]
	if two:
		viol += [v('c1') - v('b2') - 0.2, v('b2') - v('e2') - BV_CE]
	return sum(max(0.0, x) for x in viol)


def jc_of(p, op):
	"""Collector current densities [mA/um] of Q1, (Q2), Q3, Q4 from the collector sense sources."""
	out = [abs(op.get('i(vq1)', 0.0)) * 1e3 / (p['N1'] * LE)]
	if 'i(vq2)' in op:
		out.append(abs(op['i(vq2)']) * 1e3 / (p['N2'] * LE))
	out += [abs(op.get(f'i({q})', 0.0)) * 1e3 / (p['N3'] * LE) for q in ('vq3', 'vq4')]
	return [max(j, 1e-6) for j in out]


def bias_penalty(p, op):
	"""Log-distance of the current densities outside JC_WIN (0 inside)."""
	return sum(max(0.0, np.log(JC_WIN[0] / j), np.log(j / JC_WIN[1])) for j in jc_of(p, op))


def violations(m):
	"""Spec violations with optimisation margins (all >= 0, 0 = met)."""
	t = {k: SPEC[k] + (MARGIN.get(k, 0) if k == 'zt_dbohm' else -MARGIN.get(k, 0)) for k in SPEC}
	return dict(zt=max(0, t['zt_dbohm'] - m['zt_dbohm']), peak=max(0, m['peak_db'] - t['peak_db']),
				gd=max(0, m['gd_pp_ps'] - t['gd_pp_ps']), noise=max(0, m['noise_pa'] - t['noise_pa']),
				power=max(0, m['power_mw'] - t['power_mw']), bw=max(0, SPEC['bw_ghz'] - m['bw_ghz']))


def cost(m):
	"""Maximize bandwidth subject to the spec constraints (lower is better)."""
	if m is None or not np.isfinite(m['gd_pp_ps']):
		return 1e3
	v = violations(m)
	pen = (20 * v['zt'] + 30 * v['peak'] + 3 * v['gd'] + 2 * v['noise'] + 5 * v['power'] + 50 * headroom(m['op']))
	return -m['bw_ghz'] - 0.5 * (m['zt_dbohm'] - SPEC['zt_dbohm']) + pen


def meets(m, tol=0.0):
	"""True if every spec (incl. BW) is met without the optimisation margins."""
	if m is None:
		return False
	return (m['zt_dbohm'] >= SPEC['zt_dbohm'] - tol and m['bw_ghz'] > SPEC['bw_ghz'] - tol
			and m['peak_db'] <= SPEC['peak_db'] + tol and m['gd_pp_ps'] <= SPEC['gd_pp_ps'] + tol
			and m['noise_pa'] <= SPEC['noise_pa'] + tol and m['power_mw'] <= SPEC['power_mw'] + tol
			and headroom(m['op']) < 1e-3)


def summary(m):
	return ' '.join(f'{k}={m[k]:.2f}' for k in SPEC) if m else 'FAILED'


if __name__ == '__main__':
	# quick self-test: stage 1 + 3 and 1 + 2 + 3 with ideal passives
	p = dict(N1=2, R1=300, R2=500, VB=1.3, N3=4, IT=8e-3, N2=2, R4=300, RF=800, R3=200, C1=500e-15)
	for st in ('13', '123'):
		for xf in (None, ('ideal', 0.28e-9, 1.09e-9, 0.7)):
			m = run(p, xf, ('ideal', 0.3e-9), ('ideal', 0.4e-9), st)
			print(st, 'xfmr' if xf else 'none ', summary(m), 'headroom', round(headroom(m['op']), 3) if m else '-',
				  'Jc', np.round(jc_of(p, m['op']), 2) if m else '-')

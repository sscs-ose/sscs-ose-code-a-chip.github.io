# Surrogates for the passive devices of the transformer-RGC TIA:
#   kind 'xfmr'  : unified, topology-tagged transformer geometry -> 4-port S (s4p; reciprocity -> 10 entries)
#                  legacy checkpoints retain their original nine-parameter features exactly.
#   kind 'spiral': spiral geometry [w, s, n, Dx, Dy]   -> 2-port S (s2p in ../TIA_work; 3 entries)
# Models: plain MLP or pre-LN residual MLP (ResMLP), ensemble average.
# Training: min-max [-1,1] normalisation, L1 loss, AdamW, OneCycle, 70/20/10 split.
# Train from prepared arrays: python code/train_models.py --kind transformer --data runs/transformer_data.npz --output runs/transformer_training
# Use --kind spiral --data runs/spiral_data.npz --output runs/spiral_training for the spiral model and epoch R² records.
import argparse
import ast
import copy
import glob
import hashlib
import json
import os
import time
import numpy as np
import skrf as rf
import torch
import torch.nn as nn
import xfmr_schema as XG

HERE = os.path.dirname(os.path.abspath(__file__))
F_IDX = np.arange(10, 1001, 10)          # 1..100 GHz (1 GHz step) of the 1001-point EM sweep
FREQ = F_IDX * 1e8
N_F = len(F_IDX)
K10 = int(np.argmin(np.abs(FREQ - 10e9)))


# ----------------------------------------------------------------------------- geometry features
def track_offsets(w, s, ns, m, stack=0, wp=None):
	"""Same track order as xfmr_gen.offsets: S0, P0, S1, P1, ..., remaining S turns (stack = 1: P rings under S0, S1)."""
	p = max(w, w if wp is None else wp) + s
	if stack:
		return p, [t * p for t in range(int(ns))], [k * p for k in range(int(m))]
	kinds = []
	for t in range(int(ns)):
		kinds.append('S')
		if t < m:
			kinds.append('P')
	return p, [i * p for i, c in enumerate(kinds) if c == 'S'], [i * p for i, c in enumerate(kinds) if c == 'P']


def xfmr_features(geo):
	"""Raw geometry (pb = Pbar exit mode: right edge / bottom edge, u = Pbar end position) + winding lengths of the
	secondary (ns turns + partial turn) and of one primary ring, TM1 exit lengths, area, inner hole (same frame as xfmr_gen.frame)."""
	rows = []
	for row in np.atleast_2d(np.asarray(geo, float)):
		w, s, ns, m, D, pb, sb, u = row[:8]
		wp = row[8] if len(row) > 8 else w
		if sb == 2:        # full-overlap loops: both windings are one turn of length 4 D, terminal leads ~ 40 um each
			rows.append([w, s, 1, 1, D, 1, 2, u, wp, 4 * D, 4 * D, 4 * D / w, 4 * D / wp, wp / w, D * D, (D - max(w, wp)) ** 2, 1, 0, 0, 0])
			continue
		p, o, q = track_offsets(w, s, ns, m, sb, wp)
		oe = o[-1] + p
		y_u, y_e = oe + 3 * p, oe + 2 * p
		xe = u / 100 * D
		ls = sum(4 * (D - 2 * ot) for ot in o) + ((xe - 3 * p - oe) if sb else (D - 2 * oe) + (y_e - oe))   # full turns + partial turn
		lp = float(np.mean([(D - qk - y_u) + (D - 2 * qk)                              # left edge up, top edge
							+ ((D - qk - xe) if not pb else (D - 2 * qk) + (D - qk - xe))   # right edge (+ bottom edge back to x_pe)
							for qk in q]))
		hole = D - 2 * oe
		rows.append([w, s, ns, m, D, pb, sb, u, wp, ls, lp, ls / w, lp / (m * wp), wp / w, D * D, hole * hole, ns / m, oe, y_u, y_e])
	return np.array(rows)


def geometry_rows(geo):
	"""Accept one geometry or a batch, including dictionaries and mixed vector lengths."""
	if isinstance(geo, dict):
		return [geo]
	rows = list(geo)
	if not rows:
		return []
	return [rows] if np.isscalar(rows[0]) else rows


def unified_xfmr_features(geo, feature_version=2):
	"""Canonical parameters plus a versioned topology one-hot."""
	rows = [XG.vector(g) for g in geometry_rows(geo)]
	if not rows:
		return np.empty((0, len(XG.KEYS) + (3 if feature_version == 1 else 4)), dtype=float)
	g = np.asarray(rows, dtype=float)
	topology = g[:, XG.KEYS.index('topology')].astype(int)
	classes = 3 if feature_version == 1 else 4
	if np.any(topology >= classes):
		raise ValueError('This unified checkpoint predates direct-exit geometry; retrain with feature version 2')
	return np.column_stack([g, np.eye(classes)[topology]])



def spiral_length(w, s, n, Dx, Dy):
	"""TopMetal2 centre-line length of the spiral (same path as spiral_gen.spiral_points)."""
	p = w + s
	pts = [(0.0, 0.0)]
	for t in range(int(n)):
		pts += [(Dx - t * p, t * p), (Dx - t * p, Dy - t * p), (t * p, Dy - t * p), (t * p, (t + 1) * p)]
	return float(np.abs(np.diff(np.array(pts), axis=0)).sum())


def spiral_features(geo):
	g = np.atleast_2d(np.asarray(geo, float))
	w, s, n, Dx, Dy = g.T
	p = w + s
	length = np.array([spiral_length(*row) for row in g])
	return np.column_stack([w, s, n, Dx, Dy, length, length / w, Dx * Dy, (Dx - 2 * n * p) * (Dy - 2 * n * p)])


# ----------------------------------------------------------------------------- device figures
def spiral_figures(f, s):
	"""Series-branch L/Q of the pi-equivalent (Zs = -1/Y21) and SRF of port 1 with port 2 grounded."""
	y = rf.network.s2y(s, 50)
	zs = -1 / y[:, 1, 0]
	k10 = np.argmin(np.abs(f - 10e9))
	L10 = zs[k10].imag / (2 * np.pi * f[k10])
	q = np.where(zs.real > 0.05, zs.imag / np.maximum(zs.real, 0.05), 0.0)
	x11 = (1 / y[:, 0, 0]).imag
	cross = np.where((x11[:-1] > 0) & (x11[1:] <= 0))[0]
	srf = f[cross[0]] if len(cross) else f[-1]
	ok = f < srf
	return dict(L10=L10, Q10=q[k10], Qmax=q[ok].max() if ok.any() else 0.0, SRF=srf)


def xfmr_z2(s):
	"""(F,4,4) -> Z (F,2,2) of the 2-port (P, Sbar) = dotted ends (P->Pbar and S->Sbar circulate oppositely), Pbar and S grounded."""
	y = rf.network.s2y(s, 50)[:, [0, 3]][:, :, [0, 3]]
	return np.linalg.inv(y)


def xfmr_curves(f, s):
	"""Lp, Ls [H], k, Qp, Qs versus frequency (k > 0 for the dot convention of xfmr_gen)."""
	z = xfmr_z2(s)
	w = 2 * np.pi * f
	Lp, Ls, M = z[:, 0, 0].imag / w, z[:, 1, 1].imag / w, z[:, 0, 1].imag / w
	k = M / np.sqrt(np.abs(Lp * Ls))
	qp = z[:, 0, 0].imag / np.maximum(z[:, 0, 0].real, 1e-3)
	qs = z[:, 1, 1].imag / np.maximum(z[:, 1, 1].real, 1e-3)
	return Lp, Ls, k, qp, qs


def xfmr_figures(f, s):
	Lp, Ls, k, qp, qs = xfmr_curves(f, s)
	k10 = np.argmin(np.abs(f - 10e9))
	cross = np.where((Lp[:-1] > 0) & (Lp[1:] <= 0))[0]
	srf = f[cross[0]] if len(cross) else f[-1]
	return dict(Lp10=Lp[k10], Ls10=Ls[k10], k10=k[k10], n=np.sqrt(abs(Ls[k10] / Lp[k10])), Qp10=qp[k10], Qs10=qs[k10],
				SRF=srf)


# ----------------------------------------------------------------------------- kinds
class Kind:
	def __init__(self, name, nport, ext, data_dir, features, figures, keys, geometry_schema=None):
		self.name, self.nport, self.ext, self.data_dir = name, nport, ext, data_dir
		self.features, self.figures, self.keys = features, figures, keys
		self.geometry_schema = geometry_schema
		self.sel = [(i, j) for i in range(nport) for j in range(i + 1)]    # lower triangle, reciprocity
		self.ns = len(self.sel)

	def geometry(self, geo, family=None):
		"""Adapt public inputs to this checkpoint's geometry schema before feature extraction."""
		if self.name != 'xfmr':
			return np.atleast_2d(np.asarray(geo, dtype=float))
		convert = XG.vector if self.geometry_schema == 'unified' else XG.legacy_vector
		return np.asarray([convert(XG.normalize(g, family=family)) for g in geometry_rows(geo)], dtype=float).reshape(-1, len(self.keys))

	def s_to_vec(self, s):
		v = np.stack([s[:, :, i, j] for i, j in self.sel], axis=-1)
		return np.concatenate([v.real, v.imag], axis=-1).reshape(len(s), -1)

	def vec_to_s(self, v):
		v = v.reshape(len(v), N_F, 2 * self.ns)
		c = v[..., :self.ns] + 1j * v[..., self.ns:]
		s = np.zeros((len(v), N_F, self.nport, self.nport), complex)
		for k, (i, j) in enumerate(self.sel):
			s[..., i, j] = c[..., k]
			s[..., j, i] = c[..., k]
		return s

	def broken(self, s):
		"""Open circuit at 1 GHz in one of the windings (e.g. a via dropped by the EM mesh)."""
		if self.nport == 2:
			return np.abs(s[0, 1, 0]) < 0.5
		return np.abs(s[0, 1, 0]) < 0.5 or np.abs(s[0, 3, 2]) < 0.5

	def load_dataset(self, data_dir=None, max_index=8000):
		"""Load recognized geometry/S pairs below an explicit index ceiling; do not mix arbitrary five-tuples.

		The default ceiling keeps the original verification IDs out of training. Increasing it is an
		explicit opt-in. Touchstone ports, the complete frequency grid and the 50-ohm reference must match.
		"""
		if max_index <= 0:
			raise ValueError('max_index must be positive')
		d = data_dir or self.data_dir
		geo, sp, idx = [], [], []
		skipped = {}
		def reject(reason):
			skipped[reason] = skipped.get(reason, 0) + 1
		for fn in glob.glob(f'{d}/SPData/*.{self.ext}'):
			b = os.path.basename(fn)[:-len(self.ext) - 1]
			if not b.isdigit():
				continue
			i = int(b)
			info = f'{d}/INFO/{i}.log'
			if i >= max_index:
				continue
			if not os.path.exists(info):
				info = f'{d}/INFO/{i}.json'
			if not os.path.exists(info):
				reject('missing geometry metadata')
				continue
			try:
				if self.name == 'xfmr':
					params = XG.read_info(info)
					if params['topology'] in (2, 3) and not params['port_backing']:
						raise ValueError('Unbacked v3 ports are visual geometry, not valid EM training data')
					g = self.geometry(params)[0]
				else:
					with open(info) as fi:
						g = ast.literal_eval(fi.readline())
					if len(g) != len(self.keys) or not np.all(np.isfinite(g)):
						raise ValueError('invalid spiral geometry')
				n = rf.Network(fn)
			except (ValueError, TypeError, KeyError, OSError, SyntaxError) as exc:
				reject(f'incompatible metadata or Touchstone ({type(exc).__name__})')
				continue
			if n.nports != self.nport:
				reject('wrong number of ports')
				continue
			if len(n.f) != 1001 or not np.allclose(n.f, np.arange(1001) * 1e8, rtol=1e-9, atol=1.0):
				reject('wrong frequency grid (expected 0..100 GHz at 0.1 GHz spacing)')
				continue
			if not np.all(np.isfinite(n.s)) or not np.all(np.isfinite(n.z0)) or not np.allclose(n.z0, 50.0, rtol=0, atol=1e-6):
				reject('non-finite data or non-50-ohm reference')
				continue
			s = n.s[F_IDX]
			s = 0.5 * (s + np.swapaxes(s, -1, -2))   # enforce reciprocity
			if self.broken(s):
				reject('open-circuit winding')
				continue
			geo.append(g)
			sp.append(s)
			idx.append(i)
		if skipped:
			print('Dataset exclusions: ' + '; '.join(f'{reason}: {count}' for reason, count in sorted(skipped.items())), flush=True)
		order = np.argsort(idx)
		return (np.asarray(geo, float).reshape(-1, len(self.keys))[order],
				np.asarray(sp, complex).reshape(-1, N_F, self.nport, self.nport)[order], np.asarray(idx, int)[order])


KINDS = dict(
	xfmr=Kind('xfmr', 4, 's4p', HERE, xfmr_features, xfmr_figures, ('w', 's', 'ns', 'm', 'D', 'pb', 'sb', 'u', 'wp'), 'legacy'),
	spiral=Kind('spiral', 2, 's2p', os.path.join(HERE, '..', 'TIA_work'), spiral_features, spiral_figures,
				('w', 's', 'n', 'Dx', 'Dy')),
)


def kind_for(name, geometry_schema='legacy', feature_version=2):
	"""Keep KINDS['xfmr'] compatible with existing callers; choose unified training explicitly here."""
	if name != 'xfmr':
		return KINDS[name]
	if geometry_schema == 'legacy':
		return KINDS[name]
	if geometry_schema != 'unified':
		raise ValueError(f'Unknown transformer geometry schema: {geometry_schema!r}')
	if feature_version not in (1, 2, 3):
		raise ValueError(f'Unsupported unified feature version {feature_version}')
	if feature_version == 3:
		from features14 import physical14_features
		features = physical14_features
	else:
		features = lambda geo: unified_xfmr_features(geo, feature_version)
	kind = Kind('xfmr', 4, 's4p', HERE, features, xfmr_figures, XG.KEYS, 'unified')
	kind.feature_version = feature_version
	if feature_version == 3:
		from features14 import FEATURE_KEYS, FEATURE_SCHEMA
		kind.feature_keys, kind.feature_schema = FEATURE_KEYS, FEATURE_SCHEMA
	return kind


# ----------------------------------------------------------------------------- networks
class MLP(nn.Module):
	def __init__(self, n_in, n_out, hidden=(256, 512, 1024, 1024), drop=0.05):
		super().__init__()
		layers, d = [], n_in
		for h in hidden:
			layers += [nn.Linear(d, h), nn.SiLU(), nn.Dropout(drop)]
			d = h
		layers.append(nn.Linear(d, n_out))
		self.net = nn.Sequential(*layers)

	def forward(self, x):
		return self.net(x)


class ResBlock(nn.Module):
	def __init__(self, d, drop):
		super().__init__()
		self.ln = nn.LayerNorm(d)
		self.f1 = nn.Linear(d, 2 * d)
		self.f2 = nn.Linear(2 * d, d)
		self.drop = nn.Dropout(drop)

	def forward(self, x):
		return x + self.f2(self.drop(nn.functional.silu(self.f1(self.ln(x)))))


class ResMLP(nn.Module):
	"""Pre-LN residual MLP."""

	def __init__(self, n_in, n_out, width=256, depth=4, drop=0.0):
		super().__init__()
		self.inp = nn.Linear(n_in, width)
		self.blocks = nn.Sequential(*[ResBlock(width, drop) for _ in range(depth)])
		self.ln = nn.LayerNorm(width)
		self.head = nn.Linear(width, n_out)

	def forward(self, x):
		return self.head(self.ln(self.blocks(self.inp(x))))


def build_model(n_in, n_out, cfg, drop=None):
	d = cfg.get('drop', 0.05) if drop is None else drop
	if cfg['arch'] == 'mlp':
		return MLP(n_in, n_out, tuple(cfg['hidden']), d)
	return ResMLP(n_in, n_out, cfg['width'], cfg['depth'], d)


class Surrogate:
	"""Ensemble surrogate. predict(geo (N,5)) -> S (N, 100, nport, nport) at FREQ."""

	def __init__(self, path, device=None):
		ck = torch.load(path, map_location='cpu', weights_only=False)
		self.geometry_schema = ck.get('geometry_schema', 'legacy')
		self.augmentation = ck.get('augmentation')
		if self.augmentation is not None:
			raise ValueError('This workflow accepts unaugmented checkpoints only')
		self.kind = kind_for(ck['kind'], self.geometry_schema, ck.get('feature_version', 1))
		if 'geometry_keys' in ck and ck['geometry_keys'] != list(self.kind.keys):
			raise ValueError('Checkpoint geometry schema does not match this code; use its original feature schema or retrain')
		if ck.get('feature_version') == 3:
			from features14 import FEATURE_KEYS, FEATURE_SCHEMA
			if ck.get('feature_keys') != list(FEATURE_KEYS) or ck.get('feature_schema') != FEATURE_SCHEMA or len(ck['xmin']) != 14:
				raise ValueError('Checkpoint does not use the exact physical fourteen-input schema')
		self.device = device or 'cpu'
		self.xmin, self.xmax, self.ymin, self.ymax = (ck[k] for k in ('xmin', 'xmax', 'ymin', 'ymax'))
		self.cfg = ck['cfg']
		self.models = []
		for sd in ck['states']:
			m = build_model(len(self.xmin), len(self.ymin), self.cfg, 0.0)
			m.load_state_dict(sd)
			self.models.append(m.to(self.device).eval())
		self.freq = FREQ

	def predict(self, geo, family=None):
		"""Predict canonical S parameters from the checkpoint's source geometry interface."""
		geo = self.kind.geometry(geo, family=family)
		if not len(geo):
			return np.empty((0, N_F, self.kind.nport, self.kind.nport), dtype=complex)
		x = self.kind.features(geo)
		x = (x - self.xmin) / (self.xmax - self.xmin) * 2 - 1
		xt = torch.from_numpy(x).float().to(self.device)
		with torch.no_grad():
			y = np.mean([m(xt).cpu().numpy() for m in self.models], axis=0)
		return self.kind.vec_to_s((y + 1) / 2 * (self.ymax - self.ymin) + self.ymin)


# ----------------------------------------------------------------------------- training
def s_mae(pred, y, scale, ns):
	"""Mean complex |S_pred - S_true| from normalised output vectors (scale = (ymax - ymin) / 2)."""
	d = ((pred - y) * scale).reshape(len(y), N_F, 2 * ns)
	return torch.sqrt(d[..., :ns] ** 2 + d[..., ns:] ** 2).mean().item()


def train_one(xtr, ytr, xva, yva, cfg, epochs, lr, bs, device, seed, log=True, yscale=None, ns=None, epoch_callback=None):
	"""Returns (best state dict, history of [epoch, train loss, val loss, train S-MAE, val S-MAE])."""
	torch.manual_seed(seed)
	m = build_model(xtr.shape[1], ytr.shape[1], cfg).to(device)
	opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-4)
	sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=epochs * int(np.ceil(len(xtr) / bs)))
	crit = nn.L1Loss()
	xtr, ytr, xva, yva = (torch.from_numpy(a).float().to(device) for a in (xtr, ytr, xva, yva))
	sc = torch.from_numpy(np.ones(ytr.shape[1]) if yscale is None else yscale).float().to(device)
	best, best_sd, hist = np.inf, None, []
	for ep in range(epochs):
		m.train()
		perm = torch.randperm(len(xtr), device=device)
		for k in range(0, len(xtr), bs):
			b = perm[k:k + bs]
			opt.zero_grad()
			loss = crit(m(xtr[b]), ytr[b])
			loss.backward()
			nn.utils.clip_grad_norm_(m.parameters(), 1.0)
			opt.step()
			sch.step()
		m.eval()
		with torch.no_grad():
			ptr, pva = m(xtr), m(xva)
			v = crit(pva, yva).item()
			row = [ep, crit(ptr, ytr).item(), v]
			if ns:
				row += [s_mae(ptr, ytr, sc, ns), s_mae(pva, yva, sc, ns)]
		if epoch_callback is not None:
			with torch.no_grad():
				epoch_callback(ep, ptr, pva, tuple(row))
		hist.append(row)
		if v < best:
			best, best_sd = v, {k: t.detach().cpu().clone() for k, t in m.state_dict().items()}
		if log and (ep % 200 == 0 or ep == epochs - 1):
			print(f'  seed {seed} epoch {ep:5d} train {loss.item():.5f} val {v:.5f} (best {best:.5f})', flush=True)
	return best_sd, hist


def prepare(kind, seed=42, data_dir=None, max_index=8000, split=None):
	"""Prepare canonical responses with geometry-disjoint saved or seeded partitions."""
	geo, s, idx = kind.load_dataset(data_dir=data_dir, max_index=max_index)
	if split is not None:
		if set(split) != {'train', 'val', 'test'}:
			raise ValueError('Source split must contain train, val and test IDs')
		requested = np.concatenate([np.asarray(split[k]) for k in ('train', 'val', 'test')])
		if len(np.unique(requested)) != len(requested) or len(np.setdiff1d(requested, idx)):
			raise ValueError('Saved split is overlapping or references unavailable samples')
		selected = np.isin(idx, requested)
		geo, s, idx = geo[selected], s[selected], idx[selected]
	if len(geo) < 10:
		raise ValueError('Need at least ten compatible physical layouts')
	X, Y = kind.features(geo), kind.s_to_vec(s)
	_, groups = np.unique(geo, axis=0, return_inverse=True)
	if split is None:
		order = np.random.default_rng(seed).permutation(groups.max() + 1)
		nt, nv = int(.7 * len(order)), int(.2 * len(order))
		tr, va, te = (np.flatnonzero(np.isin(groups, selection))
			for selection in (order[:nt], order[nt:nt+nv], order[nt+nv:]))
	else:
		tr, va, te = (np.flatnonzero(np.isin(idx, split[k])) for k in ('train','val','test'))
	partitions = [set(groups[selection]) for selection in (tr, va, te)]
	if any(not part for part in partitions) or any(partitions[i] & partitions[j] for i in range(3) for j in range(i)):
		raise ValueError('Geometry groups must occupy nonempty, disjoint partitions')
	xmin, xmax = X[tr].min(0), X[tr].max(0)
	xmax = np.where(xmax-xmin < 1e-9, xmin+1, xmax)
	ymin, ymax = Y[tr].min(0), Y[tr].max(0)
	ymax = np.where(ymax-ymin < 1e-9, ymin+1, ymax)
	return dict(geo=geo, s=s, idx=idx, tr=tr, va=va, te=te, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,
		data_dir=data_dir or kind.data_dir, max_index=max_index,
		xn=(X-xmin)/(xmax-xmin)*2-1, yn=(Y-ymin)/(ymax-ymin)*2-1)


def export_prepared(path, kind, data, source_checkpoint=None):
	"""Save the actual prepared representations and their auditable sample counts."""
	stem = os.path.splitext(path)[0] + '_data'
	if os.path.exists(stem + '.npz') or os.path.exists(stem + '.json'):
		raise FileExistsError('Prepared data already exist; use a fresh output path')
	os.makedirs(os.path.dirname(os.path.abspath(stem)), exist_ok=True)
	arrays = {key: value for key, value in data.items() if isinstance(value, np.ndarray)}
	np.savez_compressed(stem + '.npz', **arrays)
	counts = {}
	for name, key in (('train', 'tr'), ('validation', 'va'), ('test', 'te')):
		selection = data[key]
		counts[name] = dict(records=len(np.unique(data['idx'][selection])),
						   geometries=len(np.unique(data['geo'][selection], axis=0)),
						   representations=len(selection))
	report = dict(kind=kind.name, augmentation=data.get('augmentation'),
				  n_records=len(np.unique(data['idx'])), n_unique_geometries=len(np.unique(data['geo'], axis=0)),
				  n_representations=len(data['geo']), n_input_features=data['xn'].shape[1],
				  split=counts, data_dir=data['data_dir'], max_index=data['max_index'],
				  arrays=os.path.basename(stem + '.npz'), training_status='prepared_not_trained',
				  source_checkpoint=os.path.abspath(source_checkpoint) if source_checkpoint else None)
	if source_checkpoint:
		with open(source_checkpoint, 'rb') as fi:
			report['source_checkpoint_sha256'] = hashlib.sha256(fi.read()).hexdigest()
	with open(stem + '.json', 'w') as fo:
		json.dump(report, fo, indent=2)
	return report


# ----------------------------------------------------------------------------- evaluation
def freq_errors(kind, s_true, s_pred, f=FREQ):
	"""Per-sample error curves over frequency: mean |dS|, plus |dL| in % of L(10 GHz) (both windings for xfmr), |dk|."""
	out = dict(dS=np.abs(s_pred - s_true).mean(axis=(2, 3)))
	if kind.name == 'spiral':
		dL, dQ = [], []
		for a, b in zip(s_true, s_pred):
			za, zb = -1 / rf.network.s2y(a, 50)[:, 1, 0], -1 / rf.network.s2y(b, 50)[:, 1, 0]
			La, Lb = za.imag / (2 * np.pi * f), zb.imag / (2 * np.pi * f)
			Qa = np.where(za.real > 0.05, za.imag / np.maximum(za.real, 0.05), 0.0)
			Qb = np.where(zb.real > 0.05, zb.imag / np.maximum(zb.real, 0.05), 0.0)
			dL.append(np.abs(Lb - La) / abs(La[K10]) * 100)
			dQ.append(np.abs(Qb - Qa))
		out.update(dL=np.array(dL), dQ=np.array(dQ))
	else:
		dLp, dLs, dk = [], [], []
		for a, b in zip(s_true, s_pred):
			ca, cb = xfmr_curves(f, a), xfmr_curves(f, b)
			dLp.append(np.abs(cb[0] - ca[0]) / abs(ca[0][K10]) * 100)
			dLs.append(np.abs(cb[1] - ca[1]) / abs(ca[1][K10]) * 100)
			dk.append(np.abs(cb[2] - ca[2]))
		out.update(dLp=np.array(dLp), dLs=np.array(dLs), dk=np.array(dk))
	return out


def test_metrics(sur, geo, s):
	"""Scalar (figures at 10 GHz) and per-frequency test metrics of a Surrogate on held-out devices."""
	kind = sur.kind
	sp = sur.predict(geo)
	maxe = np.abs(sp - s).max(axis=(1, 2, 3))
	out = dict(kind=kind.name, n_test=len(s), dS_mean=float(np.abs(sp - s).mean()), dS_max_median=float(np.median(maxe)),
			   dS_max_p90=float(np.percentile(maxe, 90)), freq_ghz=(FREQ / 1e9).tolist())
	ft = [kind.figures(FREQ, a) for a in s]
	fp = [kind.figures(FREQ, b) for b in sp]
	for key in ft[0]:
		if key in ('k10',):
			e = np.array([abs(b[key] - a[key]) for a, b in zip(ft, fp)])
			out[f'{key}_abserr_median'], out[f'{key}_abserr_p90'] = float(np.median(e)), float(np.percentile(e, 90))
		else:
			e = np.array([abs(b[key] / a[key] - 1) * 100 for a, b in zip(ft, fp)])
			out[f'{key}_err_median'], out[f'{key}_err_p90'] = float(np.median(e)), float(np.percentile(e, 90))
			out[f'{key}_err_max'] = float(e.max())
	for name, e in freq_errors(kind, s, sp).items():
		out[f'{name}_f_median'] = np.median(e, axis=0).tolist()
		out[f'{name}_f_p90'] = np.percentile(e, 90, axis=0).tolist()
		out[f'{name}_band_mean'] = float(e.mean())
	return out


def report_text(r):
	lines = [f"[{r['kind']}] test samples {r['n_test']} | |dS| mean {r['dS_mean']:.4f}, max-per-sample median "
			 f"{r['dS_max_median']:.4f} p90 {r['dS_max_p90']:.4f}"]
	for key in [k[:-11] for k in r if k.endswith('_err_median') and not k.endswith('abserr_median')]:
		lines.append(f"{key} err %: median {r[key + '_err_median']:.2f} p90 {r[key + '_err_p90']:.2f} "
					 f"max {r[key + '_err_max']:.2f}")
	for key in [k[:-14] for k in r if k.endswith('_abserr_median')]:
		lines.append(f"{key} abs err: median {r[key + '_abserr_median']:.4f} p90 {r[key + '_abserr_p90']:.4f}")
	curves = [k[:-9] for k in r if k.endswith('_f_median')]
	lines.append('over frequency (mean of per-frequency medians): ' +
				 ', '.join(f"{c} {np.mean(r[c + '_f_median']):.4f}" for c in curves))
	return '\n'.join(lines)


def save_checkpoint(path, kind, states, cfg, d):
	os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
	torch.save(dict(kind=kind.name, geometry_schema=kind.geometry_schema, geometry_keys=list(kind.keys),
					augmentation=d.get('augmentation'),
					feature_version=getattr(kind, 'feature_version', None),
					feature_keys=list(kind.feature_keys) if hasattr(kind, 'feature_keys') else None,
					feature_schema=getattr(kind, 'feature_schema', None),
					data_dir=d.get('data_dir', kind.data_dir), max_index=d.get('max_index', 8000),
					states=states, cfg=cfg, xmin=d['xmin'], xmax=d['xmax'], ymin=d['ymin'],
					ymax=d['ymax'], split={name: d['idx'][d[key]] for name, key in (('train', 'tr'), ('val', 'va'), ('test', 'te'))}),
			   path)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('--kind', default='xfmr', choices=list(KINDS))
	ap.add_argument('--geometry-schema', choices=['unified', 'legacy'], default='unified',
					help='Transformer feature schema; unified supports legacy and tagged series families (spiral unaffected)')
	ap.add_argument('--data-dir', default=None, help='Directory containing SPData/ and INFO/')
	ap.add_argument('--feature-version', choices=(1, 2, 3), type=int, default=3,
					help='v1/v2 retain historical features; v3 uses fourteen physical input scalars')
	ap.add_argument('--max-index', type=int, default=8000,
					help='Only train on numeric sample IDs below this value; increase explicitly to include higher-ID training samples')
	ap.add_argument('--arch', default='res', choices=['res', 'mlp'])
	ap.add_argument('--epochs', type=int, default=2000)
	ap.add_argument('--ens', type=int, default=5)
	ap.add_argument('--lr', type=float, default=2e-3)
	ap.add_argument('--bs', type=int, default=64)
	ap.add_argument('--hidden', default='256,512,1024,1024')
	ap.add_argument('--width', type=int, default=256)
	ap.add_argument('--depth', type=int, default=4)
	ap.add_argument('--drop', type=float, default=0.05)
	ap.add_argument('--out', default=None)
	ap.add_argument('--source-checkpoint', help='Freeze the source sample IDs and its geometry-disjoint split')
	ap.add_argument('--prepare-only', action='store_true', help='Export real prepared arrays and counts without training')
	ap.add_argument('--ensemble-jobs', type=int, default=1, help='Parallel CPU ensemble members')
	a = ap.parse_args()
	kind = kind_for(a.kind, a.geometry_schema, a.feature_version)
	default_name = 'xfmr_unified' if a.kind == 'xfmr' and a.geometry_schema == 'unified' else a.kind
	out = a.out or f'{HERE}/models/{default_name}.pt'
	if a.source_checkpoint and (os.path.realpath(out) == os.path.realpath(a.source_checkpoint)
			or os.path.exists(out)):
		raise FileExistsError('Use a fresh output; source checkpoints cannot be overwritten')
	if a.ensemble_jobs < 1:
		ap.error('--ensemble-jobs must be positive')
	if a.arch == 'mlp':
		cfg = dict(arch='mlp', hidden=[int(h) for h in a.hidden.split(',')], drop=a.drop)
	else:
		cfg = dict(arch='res', width=a.width, depth=a.depth, drop=a.drop)
	device = 'cuda' if torch.cuda.is_available() else 'cpu'

	source = torch.load(a.source_checkpoint, map_location='cpu', weights_only=False) if a.source_checkpoint else None
	if source is not None and source['kind'] != kind.name:
		raise ValueError('Source checkpoint device kind does not match the requested dataset')
	d = prepare(kind, data_dir=a.data_dir, max_index=a.max_index,
				split=source['split'] if source is not None else None)
	if a.prepare_only:
		counts = export_prepared(out, kind, d, a.source_checkpoint)
		print(json.dumps(counts, indent=2), flush=True)
		if a.prepare_only:
			return
	print(f"[{kind.name}] schema={kind.geometry_schema} {len(d['geo'])} valid samples, device {device}, cfg {cfg}")
	tr, va, te = d['tr'], d['va'], d['te']
	t0 = time.time()
	states, hists = [], []
	if a.ensemble_jobs > 1:
		if device != 'cpu':
			raise ValueError('Parallel ensemble jobs are supported only on CPU')
		from concurrent.futures import ProcessPoolExecutor
		import multiprocessing
		with ProcessPoolExecutor(max_workers=min(a.ensemble_jobs, a.ens),
				mp_context=multiprocessing.get_context('spawn')) as pool:
			jobs = [pool.submit(train_one, d['xn'][tr], d['yn'][tr], d['xn'][va], d['yn'][va],
				cfg, a.epochs, a.lr, a.bs, device, seed, True, (d['ymax'] - d['ymin']) / 2, kind.ns)
				for seed in range(a.ens)]
			for job in jobs:
				sd, h = job.result()
				states.append(sd)
				hists.append(h)
	else:
		for seed in range(a.ens):
			sd, h = train_one(d['xn'][tr], d['yn'][tr], d['xn'][va], d['yn'][va], cfg, a.epochs, a.lr, a.bs, device, seed,
							  yscale=(d['ymax'] - d['ymin']) / 2, ns=kind.ns)
			states.append(sd)
			hists.append(h)
	save_checkpoint(out, kind, states, cfg, d)
	print(f'training time {time.time() - t0:.0f}s -> {out}')

	sur = Surrogate(out)
	r = test_metrics(sur, d['geo'][te], d['s'][te])
	r['n_samples'] = len(np.unique(d['idx']))
	r['n_representations'] = len(d['geo'])
	r['augmentation'] = d.get('augmentation')
	r['geometry_schema'] = kind.geometry_schema
	r['geometry_keys'] = list(kind.keys)
	r['feature_version'] = getattr(kind, 'feature_version', None)
	r['data_dir'], r['max_index'] = d['data_dir'], d['max_index']
	r['n_split'] = [len(np.unique(d['idx'][selection])) for selection in (tr, va, te)]
	r['n_split_representations'] = [len(selection) for selection in (tr, va, te)]
	r['cfg'] = cfg
	r['history'] = hists[0]
	r['history_all'] = hists
	tri = lambda a: np.stack([a[:, :, i, j] for i, j in kind.sel], -1)     # independent entries, as in the training curves
	for name, sel in (('train', tr), ('val', va), ('test', te)):
		r[f'mae_{name}'] = float(np.abs(tri(sur.predict(d['geo'][sel]) - d['s'][sel])).mean())
	r['mae_f_test'] = np.abs(tri(sur.predict(d['geo'][te]) - d['s'][te])).mean(axis=(0, 2)).tolist()
	report = report_text(r)
	report += f"\nS-parameter MAE (mean |dS|): train {r['mae_train']:.4f} val {r['mae_val']:.4f} test {r['mae_test']:.4f}"
	print(report)
	with open(out.replace('.pt', '_report.txt'), 'w') as fo:
		fo.write(report + '\n')
	with open(out.replace('.pt', '_report.json'), 'w') as fo:
		json.dump(r, fo, default=float)


if __name__ == '__main__':
	main()

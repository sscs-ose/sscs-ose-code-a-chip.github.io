"""Figures for the reproduction notebook (ep_cim_loop.ipynb). Each function saves a PNG under <WORK>/figs and shows it inline.
Colors: accent Aggie Maroon #500000 (light #E3BDBD), secondary blue / purple / slate. No orange/red.
GDS pictures: KLayout LayoutView with the open SKY130 layer properties (sky130A.lyp), text labels hidden."""
import csv
import json
import math
import os
import re
import subprocess
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

MAROON, LIGHT, BLUE, PURPLE, SLATE, GREY = '#500000', '#E3BDBD', '#2F5D8A', '#6A4C93', '#5F7484', '#9AA5AE'
plt.rcParams.update({'figure.dpi': 120, 'savefig.dpi': 120, 'font.size': 10, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.3})
FIGS = None


def setup(work):
    global FIGS
    FIGS = Path(work) / 'figs'
    FIGS.mkdir(parents=True, exist_ok=True)


def _show(fig, name):
    from IPython.display import Image, display
    p = FIGS / f'{name}.png'
    fig.savefig(p, bbox_inches='tight')
    plt.close(fig)
    display(Image(filename=str(p), width=1000))
    print(f'[figure] {p.name}: {os.path.getsize(p) / 1e3:.0f} kB')


# ── ② training curve ─────────────────────────────────────────────
def training_curve(ep, train, tag, n_train=17507):
    runs = []
    if train in ('quick', 'full'):
        runs.append(('this run (seed 0)', Path(ep) / 'out/runs' / tag / 'log.csv'))
    else:
        runs += [(f'saved run, seed {s}', Path(ep) / f'out/runs/nobz5_seed{s}/log.csv') for s in range(3)]
    runs = [(l, p) for l, p in runs if p.exists()]
    if not runs:
        print('No training log available (TRAIN=load and no saved log.csv in the bundle) — training curve skipped.')
        return
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    for (lab, p), c in zip(runs, (MAROON, BLUE, PURPLE)):
        rows = [r for r in csv.DictReader(open(p)) if r['epoch'] not in ('best', 'final') and r['val_acc']]
        x = [int(r['step']) / n_train for r in rows]
        y = [100 * float(r['val_acc']) for r in rows]
        ax.plot(x, y, '-', color=c, lw=1.4, label=lab)
        b = [r for r in csv.DictReader(open(p)) if r['epoch'] == 'best']
        if b:
            ax.plot([int(b[0]['step']) / n_train], [100 * float(b[0]['val_acc'])], 'o', color=c, ms=5)
    ax.set_xlabel('Training epochs (online, one sample per update)')
    ax.set_ylabel('Validation accuracy (%)')
    ax.set_title('EP training of the 1T1R crossbar circuit (5-bit cells, digits 0/1/4)')
    ax.legend(frameon=False, loc='lower right')
    _show(fig, 'train_curve')


# ── ③ accuracy + confusion matrix ────────────────────────────────
def accuracy(eval_json, pred_npz):
    J = json.loads(Path(eval_json).read_text())
    keys = [k for k in J if isinstance(J[k], dict)]
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={'width_ratios': [1.3, 1]})
    ax = axs[0]
    xs = np.arange(len(keys))
    ax.bar(xs, [100 * J[k]['test'] for k in keys], color=MAROON, width=0.55, label='this notebook')
    for x, k in zip(xs, keys):
        ax.hlines(100 * J[k]['saved'], x - 0.35, x + 0.35, color=BLUE, lw=2, label='saved value' if x == 0 else None)
        ax.text(x, 100 * J[k]['test'] + 0.3, f"{100 * J[k]['test']:.2f}", ha='center', fontsize=9)
    ax.set_xticks(xs, [f"seed {k.split('_s')[-1]}" for k in keys])
    ax.set_ylim(90, 100)
    ax.set_ylabel('Test accuracy (%)')
    ax.set_title('Saved 5-bit weights, 3,097 test images')
    ax.legend(frameon=False, loc='upper center', ncol=2, fontsize=9)   # above the bars (they end near 96 %)
    P = np.load(pred_npz)
    y, p = P['y'], P['pred']
    C = np.zeros((3, 3), int)
    for a, b in zip(y, p):
        C[a, b] += 1
    ax = axs[1]
    ax.grid(False)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list('m', ['#FFFFFF', LIGHT, MAROON])
    ax.imshow(C, cmap=cmap)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, C[i, j], ha='center', va='center', color='white' if C[i, j] > C.max() / 2 else 'black')
    lab = [str(d) for d in P['digits']]
    ax.set_xticks(range(3), lab)
    ax.set_yticks(range(3), lab)
    ax.set_xlabel('Predicted digit')
    ax.set_ylabel('True digit')
    ax.set_title(f'Confusion matrix, seed 0 ({100 * (y == p).mean():.2f} %)')
    _show(fig, 'accuracy')


# ── ④ WU block decisions, RRAM write waveform ────────────────────
def _meas(path):
    return {k.lower(): float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*([-+]?[0-9.]+(?:[eE][-+]?\d+)?)', open(path, errors='ignore').read(), re.M)}


def wu_decisions(ref_json, mt0):
    R = json.load(open(ref_json))
    M = _meas(mt0)
    d = np.array([c['d'] for c in R['cells']]) * 1e6
    want = np.array([bool(c['set_exact']) for c in R['cells']])
    lq = np.array([M.get(f'lq{n}', np.nan) for n in range(len(d))])
    ok = (lq > 0) == want
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    for m, c, lab in ((want, MAROON, 'expected SET'), (~want, BLUE, 'expected RESET')):
        ax.scatter(d[m], lq[m], s=22, color=c, label=lab, zorder=3)
    if (~ok).any():
        ax.scatter(d[~ok], lq[~ok], s=70, facecolors='none', edgecolors='black', label='mismatch')
    ax.axhline(0, color=GREY, lw=0.8)
    ax.set_xscale('symlog', linthresh=30)
    ax.set_xlabel('Update criterion  δ = |ΔV_nudge| − |ΔV_free|  (µV)')
    ax.set_ylabel('Latch output (V)')
    ax.set_title(f'Weight-update block in Xyce: {ok.sum()}/{len(ok)} decisions match the expected sign')
    ax.legend(frameon=False, loc='upper left')
    _show(fig, 'wu_decisions')


def rram_wave(d, ngspice, osdi, amp=1.8):
    """1R ReRAM cell (SkyWater VA via OSDI): SET pulse on TE (low-G start) and RESET pulse on BE (high-G start), 10 ns, then 0.1 V read."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    pw = lambda v: f'PWL(0 0 5n 0 6n {v} 16n {v} 17n 0 27n 0 28n 0.1)'
    L = ['* 1R write waveform (SET and RESET), ngspice + OSDI', '.options reltol=1e-4 abstol=1e-15 vntol=1e-10 method=gear', '.temp 27', '.options tnom=25',
         '.model rlo sky130_fd_pr_reram__reram_cell Tfilament_0=3.934877e-09 t_step=1e-11',
         '.model rhi sky130_fd_pr_reram__reram_cell Tfilament_0=4.899531e-09 t_step=1e-11',
         f'Vte0 te0 0 {pw(amp)}', 'Vbe0 bes0 0 0', 'Vs0 bes0 be0 0', 'N0 te0 be0 rlo',
         'Vte1 tes1 0 PWL(0 0 27n 0 28n 0.1)', f'Vbe1 be1 0 PWL(0 0 5n 0 6n {amp} 16n {amp} 17n 0)', 'Vs1 tes1 te1 0', 'N1 te1 be1 rhi',
         '.control', 'tran 20p 47n', 'wrdata wave.txt v(te0)-v(be0) i(Vs0) v(te1)-v(be1) i(Vs1)', '.endc', '.end']
    (d / 'wave.cir').write_text('\n'.join(L) + '\n')
    (d / '.spiceinit').write_text(f'set ngbehavior=hsa\nosdi {osdi}\n')
    subprocess.run([str(ngspice), '-b', 'wave.cir'], cwd=d, stdout=open(d / 'wave.log', 'w'), stderr=subprocess.STDOUT, check=True)
    A = np.loadtxt(d / 'wave.txt')
    t = A[:, 0] * 1e9
    fig, axs = plt.subplots(2, 2, figsize=(10, 4.6), sharex=True)
    for col, (vi, ii, name, sgn) in enumerate(((1, 3, f'SET: +{amp} V on top electrode', 1), (5, 7, f'RESET: +{amp} V on bottom electrode', -1))):
        v, i = A[:, vi], A[:, ii] * sgn
        axs[0, col].plot(t, v, color=MAROON)
        axs[0, col].set_title(name)
        axs[1, col].plot(t, np.abs(i) * 1e6, color=BLUE)
        axs[1, col].set_yscale('log')
        k = np.searchsorted(t, 46)
        g0, g1 = abs(i[np.searchsorted(t, 4)]), abs(i[k])
        axs[1, col].set_xlabel('Time (ns)')
        axs[1, col].text(0.98, 0.05, f'read at 0.1 V: G = {g1 / 0.1 * 1e6:.1f} µS', transform=axs[1, col].transAxes, ha='right', fontsize=9)
    axs[0, 0].set_ylabel('Cell voltage (V)')
    axs[1, 0].set_ylabel('|Cell current| (µA)')
    fig.suptitle('SkyWater ReRAM Verilog-A model (OSDI) in ngspice: write pulse 10 ns, then read')
    _show(fig, 'rram_wave')


# ── GDS pictures ─────────────────────────────────────────────────
def render(gds, top, out, width=1400, lyp=None):
    import klayout.lay as lay
    lv = lay.LayoutView()
    for k, v in (('background-color', '#000000'), ('text-visible', 'false'), ('grid-visible', 'false'),
                 ('cell-box-visible', 'false'), ('no-stipple', 'false')):
        lv.set_config(k, v)
    cv = lv.load_layout(str(gds), True)
    lv.load_layer_props(str(lyp))
    lv.cellview(cv).cell_name = top
    lv.max_hier()
    lv.zoom_fit()
    bb = lv.cellview(cv).cell.dbbox()
    h = int(round(width * bb.height() / bb.width()))
    lv.save_image(str(out), width, h)
    return bb.width(), bb.height()


def gds_grid(items, lyp, name, title, cols=2, width=900):
    """items = [(gds, top cell, caption)]: render each, then tile with matplotlib."""
    imgs = []
    for g, top, cap in items:
        p = FIGS / f'{name}_{top}.png'
        w, h = render(g, top, p, width, lyp)
        imgs.append((plt.imread(p), f'{cap}  ({w:.0f} × {h:.0f} µm)'))
    rows = math.ceil(len(imgs) / cols)
    fig, axs = plt.subplots(rows, cols, figsize=(5.2 * cols, 4.4 * rows))
    for ax in np.ravel(axs):
        ax.axis('off')
    for ax, (im, cap) in zip(np.ravel(axs), imgs):
        ax.imshow(im)
        ax.set_title(cap, fontsize=10)
    fig.suptitle(title)
    _show(fig, name)


def gds_one(gds, top, lyp, name, title, width=1400):
    from IPython.display import Image, display
    p = FIGS / f'{name}.png'
    w, h = render(gds, top, p, width, lyp)
    print(f'{title}: {w:.1f} × {h:.1f} µm (layer colors = open SKY130 KLayout properties, text hidden)')
    display(Image(filename=str(p), width=1000))
    print(f'[figure] {p.name}: {os.path.getsize(p) / 1e3:.0f} kB')


# ── ⑥ floorplan ──────────────────────────────────────────────────
NICE = {'arr_w3s_128x64': '1T1R array 128×64', 'input_drive': 'input drive', 'row_blk': 'row control', 'col_blk': 'column control',
        'data_blk': 'data register', 'glob_dig': 'global digital', 'wu': 'weight update', 'wbuf': 'write buffer',
        'nudge_inj': 'nudge injector', 'bias_beta': 'β bias', 'tg_n2': 'readout switch', 'sky130_fd_sc_hvl__inv_2': 'inv'}


def floorplan(place_json):
    P = json.load(open(place_json))
    W, H = P['core']['w'], P['core']['h']
    fig, ax = plt.subplots(figsize=(9, 9 * H / W))
    ax.grid(False)
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, ec=GREY, lw=1))
    dig = {'row_blk', 'col_blk', 'data_blk', 'glob_dig'}
    for n, v in P['instances'].items():
        c = v['cell']
        if c.startswith('tp_') or c.startswith('sky130_fd_sc_hvl'):
            continue
        col = SLATE if c in dig else (MAROON if c.startswith('arr') else PURPLE if c in ('wu',) else BLUE)
        half = ' (nudge)' if v.get('group', '').startswith('nudge') else ' (free)' if v.get('group', '').startswith('free') else ''
        ax.add_patch(plt.Rectangle((v['x'], v['y']), v['w'], v['h'], fc=col, ec='black', lw=0.5, alpha=0.75))
        if v['w'] * v['h'] > 3000:
            ax.text(v['x'] + v['w'] / 2, v['y'] + v['h'] / 2, NICE.get(c, c) + (half if c.startswith('arr') else ''),
                    ha='center', va='center', fontsize=7 if v['w'] < 120 else 9, color='white', rotation=90 if v['h'] > 2.5 * v['w'] else 0)
    for n, v in P['test_areas'].items():
        x0, y0, x1, y1 = v['rect']
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc=LIGHT, ec='black', lw=0.5))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, 'test\npattern', ha='center', va='center', fontsize=7)
    ax.set_xlim(-10, W + 10)
    ax.set_ylim(-10, H + 10)
    ax.set_aspect('equal')
    ax.set_xlabel('x (µm)')
    ax.set_ylabel('y (µm)')
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=MAROON, label='crossbar array'), Patch(fc=BLUE, label='analog blocks (generators)'),
                       Patch(fc=PURPLE, label='weight update'), Patch(fc=SLATE, label='digital (saved GDS)'),
                       Patch(fc=LIGHT, ec='black', label='test patterns')], frameon=False, fontsize=8, loc='upper center',
              bbox_to_anchor=(0.5, -0.08), ncol=5)
    ax.set_title(f'Chip core floorplan, {W:.0f} × {H:.0f} µm (free half top, nudge half bottom, 180° rotated)')
    _show(fig, 'floorplan')


# ── ⑨ DRC bars, LVS table ────────────────────────────────────────
WAIVED = {'nwell.8': 'same-net HV n-well (false positive)', 'LU.2': 'test-pattern diffusion, no transistor', 'LU.3': 'test-pattern diffusion, no transistor',
          'rpm.1': 'Magic-regenerated RPM layer', 'hvntm.1': 'Magic-regenerated HVNTM layer'}


def drc_bars(drc_jsons):
    """drc_jsons = [(label, path)]: Magic DRC boxes per rule, waived (judged false positive) vs not."""
    fig, axs = plt.subplots(1, len(drc_jsons), figsize=(5.2 * len(drc_jsons), 3.8), squeeze=False)
    for ax, (lab, p) in zip(axs[0], drc_jsons):
        if not Path(p).exists():
            ax.set_title(f'{lab}: not run')
            ax.axis('off')
            continue
        R = json.load(open(p)).get('rules', {})
        if not R:
            ax.text(0.5, 0.5, f'{lab}\n0 violations', ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.axis('off')
            continue
        top = sorted(R.items(), key=lambda kv: -kv[1])[:12]
        names = [k for k, _ in top]
        ax.barh(names, [v for _, v in top], color=[SLATE if k in WAIVED else MAROON for k in names])
        ax.invert_yaxis()
        ax.set_xscale('log')
        ax.set_xlabel('Magic DRC error boxes')
        ax.set_title(f'{lab}: {sum(R.values()):,} boxes')
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(fc=SLATE, label='waived (rule-interpretation difference, see opensrc/README)'),
                        Patch(fc=MAROON, label='not waived')], frameon=False, loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.06))
    _show(fig, 'drc')


def lvs_table(items):
    from IPython.display import Markdown, display
    L = ['| Netlist comparison | Netgen result | Top-cell devices (layout / source) | Top-cell nets (layout / source) |', '|---|---|---|---|']
    for lab, p in items:
        if not Path(p).exists():
            L.append(f'| {lab} | not run | | |')
            continue
        j = json.load(open(p))
        t = j.get('top_cell') or {}
        L.append(f"| {lab} | {j.get('final')} | {' / '.join(map(str, t.get('dev') or []))} | {' / '.join(map(str, t.get('nets') or []))} |")
    display(Markdown('\n'.join(L)))


# ── ⑩ time bars ──────────────────────────────────────────────────
GCOL = {'setup': GREY, 'train': MAROON, 'sim': BLUE, 'layout': PURPLE, 'route': SLATE, 'verify': '#1F3B57'}
GNAME = {'setup': 'install', 'train': 'training', 'sim': 'simulation', 'layout': 'layout', 'route': 'routing', 'verify': 'verification'}
EN = [('경로 맞추기', 'fix paths'), ('설치: ', 'install: '), ('도구 판 확인', 'tool versions'), ('MNIST 받기', 'download MNIST'), ('학습', 'training'),
      ('추론: 저장 가중치 3 seed', 'inference: saved weights'), ('추론: 방금 학습한 가중치', 'inference: new weights'),
      ('시뮬: WU 블록 덱 생성 + Xyce', 'Xyce: weight-update block'), ('시뮬: RRAM 셀 쓰기 (OpenVAF → OSDI → ngspice)', 'ngspice: RRAM write grid'),
      ('시뮬: 칩 덱 sys2 (Xyce, 약 20 분)', 'Xyce: chip deck'), ('블록: arr', 'block: 1T1R array'), ('블록: analog', 'block: analog (4 blocks)'), ('블록: tg_n2', 'block: readout switch'), ('블록: HOG', 'block: HOG op-amp'), ('블록: wu', 'block: weight update'), ('블록: test pattern', 'block: test patterns'), ('블록: pad frame', 'block: pad frame'), ('연결표: 칩 덱 v3 + mk_top', 'netlist'), ('배치: mk_lef + place_real', 'placement'),
      ('배선: prewire (Python)', 'pre-wiring (Python)'), ('배선: OpenROAD global + detailed route', 'OpenROAD routing'), ('배선: DEF → GDS + 검사', 'DEF → GDS'),
      ('패드: die 조립 + 연결 검사', 'pad ring + die'), ('검증: RRAM Magic tech 다시 만들기', 'Magic RRAM tech'), ('검증: core 추출 + antenna (Magic)', 'core extraction'),
      ('검증: core LVS (Netgen)', 'core LVS'), ('검증: die 추출 (Magic, LVS 판)', 'die extraction'), ('검증: die LVS (Netgen, 패드 black box)', 'die LVS'),
      ('검증: core DRC (Magic, 약 12 분)', 'core DRC'), ('검증: die DRC (Magic, 약 22 분)', 'die DRC'), ('검증: 블록 DRC arr_w3s_128x64 (Magic, quick 판)', 'array DRC'),
      ('그림: 학습 곡선', 'figure: training curve'), ('그림: test 정확도·혼동 행렬', 'figure: accuracy'), ('그림: WU 블록 판정', 'figure: WU decisions'),
      ('그림: RRAM 쓰기 파형', 'figure: RRAM waveform'), ('그림: 블록 GDS', 'figure: block GDS'), ('그림: 배치도', 'figure: floorplan'),
      ('그림: 배선 뒤 core GDS', 'figure: routed core GDS'), ('그림: die GDS', 'figure: die GDS'), ('그림: DRC 규칙별·LVS 표', 'figure: DRC / LVS')]


def _en(n):
    for a, b in EN:
        if n.startswith(a):
            return b + (n[len(a):] if a == '설치: ' else '')
    return n


def time_bars(rows):
    rows = [r for r in rows if r.get('sec', 0) >= 1]
    fig, ax = plt.subplots(figsize=(9, 0.28 * len(rows) + 1.2))
    ax.barh([_en(r['name']) for r in rows], [r['sec'] / 60 for r in rows], color=[GCOL.get(r['group'], GREY) for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel('Wall-clock time (min)')
    ax.tick_params(axis='y', labelsize=8)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=c, label=GNAME[g]) for g, c in GCOL.items()], frameon=False, fontsize=8, loc='lower right')
    ax.set_title(f'Wall-clock time per step, total {sum(r["sec"] for r in rows) / 60:.1f} min')
    _show(fig, 'time_bars')

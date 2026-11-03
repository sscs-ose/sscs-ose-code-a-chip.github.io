"""dig_wave.py — digital timing diagrams of the operating modes (FORM, READ, SENSING, WRITE) from the tb_modes VCD.

Use (notebook):  import dig_wave as W;  W.mode_waves('tb_modes.vcd', 'form', 'fig_wave_form.png')
                 mode = 'form' | 'read' | 'sense' | 'write'
Command line:    python dig_wave.py tb_modes.vcd <out_dir>     (all four figures, fig_wave_<mode>.png)

The VCD comes from digital_oss/wave/tb_modes.v (RTL of global control, DATA, row control and column control wired as in
the chip netlist). The testbench marks each scenario with `scen` (1 FORM, 2 READ, 3 SENSING, 4 WRITE) and each step with `seg`;
the step names below are the bands at the top of each figure. Line states (row, word line, column) are decoded from the
decoder outputs: the switch that is on names the voltage on the line. Only the VCD reader from the standard library + matplotlib.
"""
import bisect
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib import font_manager                               # noqa: E402
from matplotlib.patches import Polygon, Rectangle                 # noqa: E402

MAROON, MAROON_L, NAVY, NAVY_L, GREY = '#500000', '#F1E2E2', '#001C54', '#E3E8F1', '#8C8C8C'
for _f in ('/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf', '/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf'):
    if os.path.exists(_f):
        font_manager.fontManager.addfont(_f)
plt.rcParams.update({'font.family': ['Nimbus Sans', 'DejaVu Sans'], 'font.size': 9, 'axes.unicode_minus': True})

NR_IN = 98                       # rows 0-97 = input rows (input i -> rows 2i (x+) and 2i+1 (x-)), 98-99 = bias rows
NC_HID = 60                      # columns 0-59 = hidden columns with diode clamps


# ------------------------------------------------------------------ VCD reader
class Vcd:
    def __init__(self, path):
        self.sig = {}            # name -> (times_ns, values)   value = '0'/'1'/'x' or bit string MSB first
        self.width = {}
        ids, scale, t = {}, 1.0, 0.0
        units = {'s': 1e9, 'ms': 1e6, 'us': 1e3, 'ns': 1.0, 'ps': 1e-3, 'fs': 1e-6}
        tok = iter(open(path).read().split())
        for w in tok:
            if w == '$timescale':
                s = ''
                for w2 in tok:
                    if w2 == '$end':
                        break
                    s += w2
                num = ''.join(ch for ch in s if ch.isdigit()) or '1'
                scale = float(num) * units[s[len(num):]]
            elif w == '$var':
                _typ, wid, i, name = next(tok), int(next(tok)), next(tok), next(tok)
                for w2 in tok:
                    if w2 == '$end':
                        break
                if i not in ids:                     # an id may be shared by two names; keep the first
                    ids[i] = name
                    self.sig[name] = ([], [])
                    self.width[name] = wid
            elif w.startswith('#'):
                t = int(w[1:]) * scale
            elif w[0] in 'bB':
                v, i = w[1:].lower(), next(tok)
                self._put(ids.get(i), t, v)
            elif w[0] in 'rR':
                next(tok)
            elif w[0] in '01xXzZ' and len(w) > 1:
                self._put(ids.get(w[1:]), t, w[0].lower())
        self.t_end = t

    def _put(self, name, t, v):
        if name is None:
            return
        wid = self.width[name]
        if len(v) < wid:
            v = (v[0] if v[0] in 'xz' else '0') * (wid - len(v)) + v
        ts, vs = self.sig[name]
        if ts and ts[-1] == t:
            vs[-1] = v
        else:
            ts.append(t); vs.append(v)

    def at(self, name, t):
        ts, vs = self.sig[name]
        k = bisect.bisect_right(ts, t) - 1
        return vs[k] if k >= 0 else 'x' * self.width[name]

    def changes(self, t0, t1):
        out = set()
        for ts, _ in self.sig.values():
            out.update(ts[bisect.bisect_left(ts, t0):bisect.bisect_right(ts, t1)])
        return sorted(out)


class State:
    """Signal values at one time; vectors are indexed by bit number (bit 0 = right end of the VCD string)."""
    def __init__(self, vcd, t):
        self.v, self.t = vcd, t

    def b(self, name, k=None):
        s = self.v.at(name, self.t)
        c = s[-1] if k is None else s[len(s) - 1 - k]
        return 1 if c == '1' else (0 if c == '0' else None)

    def ones(self, name):
        s = self.v.at(name, self.t)
        return [len(s) - 1 - j for j, c in enumerate(s) if c == '1'][::-1]

    def all1(self, name):
        return set(self.v.at(name, self.t)) == {'1'}


# ------------------------------------------------------------------ decoding helpers (names as in notebook 4.3 / 6.3 / 6.4)
CFGN = ['m1', 'm0', 'pv', 'pol', 'wu_en', 'rd_out', 'dload', 'ts_data', 'ts_row1', 'ts_row2', 'ts_col1', 'ts_col2']


def cfgbit(S, n):
    return S.b('cfg_latch', CFGN.index(n))


def mode_name(S):
    m1, m0, pv, wu = cfgbit(S, 'm1'), cfgbit(S, 'm0'), cfgbit(S, 'pv'), cfgbit(S, 'wu_en')
    if None in (m1, m0):
        return '?'
    return {(0, 0): 'IDLE', (0, 1): 'FORM', (1, 0): 'WRITE verify' if pv else 'WRITE program',
            (1, 1): 'READ + sensing' if wu else 'READ'}[(m1, m0)]


def clock_enable(S):
    names = [('ts_data', 'data'), ('ts_row1', 'row'), ('ts_row2', 'output row'), ('ts_col1', 'column'), ('ts_col2', 'column 2')]
    on = [lab for n, lab in names if cfgbit(S, n)]
    return ' + '.join(on) if on else 'none'


def token(name):
    def f(S):
        k = S.ones(name)
        return ', '.join(str(x) for x in k) if k else '–'
    return f


def write_bus(S):
    if not S.b('WP'):
        return '0 V'
    if S.b('VER_f'):
        return '+0.2 V (verify)'
    if mode_name(S) == 'FORM':
        return '+2.3 V (form)'
    return '−1.8 V (RESET)' if S.b('pol_f') else '+2.0 V (SET)'


def row_line(r):
    def f(S):
        if S.b('wsel', r):
            return 'write bus'
        if S.b('rsns', r):
            return 'sense bus'
        if S.b('rwz', r):
            return '0 V'
        if S.b('READ_f') and r < NR_IN:
            i = r // 2
            up = S.b('ga', i) if r % 2 == 0 else S.b('gb', i)
            dn = S.b('gb', i) if r % 2 == 0 else S.b('ga', i)
            return '+a (input driver)' if up else ('−a (input driver)' if dn else 'off')
        return 'off'
    return f


def word_line(r):
    def f(S):
        if S.b('wlw', r):
            return 'VWL (write)'
        if S.b('wlv', r):
            return 'VDD'
        if S.b('wl0', r):
            return 'VSS'
        return '?'
    return f


def all_word_lines(S):
    if S.all1('wlv'):
        return 'VDD (all)'
    if S.all1('wl0'):
        return 'VSS (all)'
    return 'mixed'


def col_line(c):
    def f(S):
        if S.b('cwz', c):
            return '0 V'
        if S.b('vfy', c):
            return 'verify bus'
        if S.b('sns1', c):
            return 'sense bus 1'
        if S.b('sns2', c):
            return 'sense bus 2'
        if S.b('wvw', c):
            return 'write bus'
        if S.b('READ_f') and c < NC_HID:
            return 'diode clamp'
        return 'off'
    return f


def dig(name, k=None):
    return lambda S: S.b(name, k)


def cfgdig(n):
    return lambda S: cfgbit(S, n)


# ------------------------------------------------------------------ figure contents
# row: (label, kind 'd' digital / 'b' bus, function, colour 'k' | 'm' (selected line, maroon) | 'n' (navy))
R, C = 3, 5
PADS = [('serial clock (SCK)', 'd', dig('SCK'), 'k'), ('serial data (SDI)', 'd', dig('SDI'), 'k'),
        ('settings load (SLD)', 'd', dig('SLD'), 'k')]
GLOB = [('mode', 'b', mode_name, 'n'), ('register clock enable', 'b', clock_enable, 'k')]
TOK = [('row register clock', 'd', dig('row1_clk_f'), 'k'), ('column register clock', 'd', dig('col1_clk_f'), 'k'),
       ('row token position', 'b', token('row_token'), 'k'), ('column token position', 'b', token('col_token'), 'k'),
       (f'row {R}: selected_line_bit', 'd', dig('row_token', R), 'm'), (f'column {C}: selected_line_bit', 'd', dig('col_token', C), 'm')]
SELWP = [('select_enable (SEL_EN)', 'd', dig('SEL_EN'), 'k'), ('write pulse (WP)', 'd', dig('WP'), 'k'),
         ('write bus', 'b', write_bus, 'n')]
LINES_W = [(f'row line {R}', 'b', row_line(R), 'm'), (f'row line {R + 1}', 'b', row_line(R + 1), 'k'),
           (f'word line {R}', 'b', word_line(R), 'm'), (f'word line {R + 1}', 'b', word_line(R + 1), 'k'),
           (f'column line {C}', 'b', col_line(C), 'm'), (f'column line {C + 1}', 'b', col_line(C + 1), 'k')]

MODES = {
    'form': dict(
        scen=1, title='FORM — set the mode, shift the row and column tokens to cell (3, 5), one forming pulse',
        segs={1: 'IDLE', 2: 'mode setting (FORM, row + column registers)', 3: 'token shift', 4: 'setting (column register only)',
              5: 'token shift', 6: 'program'},
        cut={4: (22, 22)}, stretch={6: 2.5},
        groups=[('pads', PADS), ('global\ncontrol', GLOB + [('program', 'd', dig('PROG_f'), 'k'),
                                                          ('program_or_verify', 'd', dig('WRANY_f'), 'k')]),
                ('token\nregisters', TOK), ('select,\nwrite pulse', SELWP),
                (f'row {R}\ndecoder', [(f'row {R}: row_to_write_bus', 'd', dig('wsel', R), 'm'),
                                      (f'row {R}: wl_to_write_voltage', 'd', dig('wlw', R), 'm')]),
                ('lines', LINES_W)]),
    'read': dict(
        scen=2, title='READ — set the mode, shift 52 input bits into the DATA register, one load applies them to every input row',
        segs={1: 'IDLE', 2: 'mode setting (READ, DATA register)', 3: 'input data shift (52 bits); rows keep the previous input', 4: 'setting (load on)',
              5: 'inference'},
        cut={3: (32, 42), 4: (20, 30)},
        groups=[('pads', PADS), ('global\ncontrol', GLOB + [('input load', 'd', cfgdig('dload'), 'm'), ('read', 'd', dig('READ_f'), 'k')]),
                ('DATA\nblock', [('data register clock', 'd', dig('data_clk_f'), 'k'),
                                 ('data register bit 1', 'd', dig('data_reg', 1), 'n'), ('data register bit 2', 'd', dig('data_reg', 2), 'n'),
                                 ('input latch 1', 'd', dig('data_lat', 1), 'm'), ('input latch 2', 'd', dig('data_lat', 2), 'm')]),
                ('lines', [('row line 3 (input 1, x−)', 'b', row_line(3), 'm'), ('row line 4 (input 2, x+)', 'b', row_line(4), 'm'),
                           ('word lines', 'b', all_word_lines, 'k'), ('column line 5', 'b', col_line(5), 'k')])]),
    'sense': dict(
        scen=3, title='SENSING — inputs stay applied; the tokens pick cell (3, 5), then the column token moves to cell (3, 6)',
        segs={1: 'READ', 2: 'setting (sensing on, row + column registers)', 3: 'token shift', 4: 'setting (column only)',
              5: 'token shift', 6: 'sense cell (3, 5)', 7: 'next column', 8: 'sense cell (3, 6)'},
        cut={2: (20, 28), 4: (20, 28), 6: (60, 40), 8: (60, 40)}, stretch={7: 3},
        groups=[('pads', PADS), ('global\ncontrol', GLOB + [('sense', 'd', dig('SENSE_f'), 'k'), ('read', 'd', dig('READ_f'), 'k')]),
                ('token\nregisters', TOK), ('select', [SELWP[0]]),
                (f'row {R}\ndecoder', [(f'row {R}: row_to_sense_bus', 'd', dig('rsns', R), 'm'),
                                      (f'row {R}: wl_to_VDD', 'd', dig('wlv', R), 'm')]),
                ('lines', [(f'row line {R}', 'b', row_line(R), 'm'), (f'row line {R + 1}', 'b', row_line(R + 1), 'k'),
                           (f'word line {R}', 'b', word_line(R), 'm'),
                           (f'column line {C}', 'b', col_line(C), 'm'), (f'column line {C + 1}', 'b', col_line(C + 1), 'n')])]),
    'write': dict(
        scen=4, title='WRITE — same start as FORM (mode, tokens to cell (3, 5)), one SET pulse, then verify',
        segs={1: 'IDLE', 2: 'mode setting (WRITE program)', 3: 'token shift', 4: 'setting (column only)', 5: 'token shift',
              6: 'program', 7: 'setting (verify)', 8: 'verify'},
        cut={2: (20, 28), 4: (20, 22), 7: (20, 28)}, stretch={6: 2.5, 8: 1.5},
        groups=[('pads', PADS), ('global\ncontrol', GLOB + [('program', 'd', dig('PROG_f'), 'k'), ('verify', 'd', dig('VER_f'), 'k'),
                                                          ('program_or_verify', 'd', dig('WRANY_f'), 'k')]),
                ('token\nregisters', TOK[:4]), ('select,\nwrite pulse', SELWP),
                (f'row {R}\ndecoder', [(f'row {R}: row_to_write_bus', 'd', dig('wsel', R), 'm'),
                                      (f'row {R}: wl_to_write_voltage', 'd', dig('wlw', R), 'm'),
                                      (f'row {R}: wl_to_VDD', 'd', dig('wlv', R), 'm')]),
                ('lines', LINES_W)]),
}


# ------------------------------------------------------------------ time axis with breaks
class Axis:
    """Real time placed left to right. A cut step keeps its head and tail and shows a break of width GAP in between;
    a stretched step (short pulses) is drawn k times wider. Tick labels always give the real time."""
    GAP = 7.0

    def __init__(self, t0, t1, seg_spans, cut, stretch=None):
        stretch, parts = stretch or {}, []
        for code, (a, b) in seg_spans:
            if code in cut and b - a > sum(cut[code]) + 2 * self.GAP:
                h, tl = cut[code]
                parts += [(a, a + h, 1.0), (a + h, b - tl, None), (b - tl, b, 1.0)]
            else:
                parts.append((a, b, float(stretch.get(code, 1.0))))
        if parts and parts[0][0] > t0:
            parts.insert(0, (t0, parts[0][0], 1.0))
        self.parts, self.gaps, x = [], [], 0.0          # (t_start, t_end, scale or None, x_start or gap centre)
        for a, b, k in parts:
            if k is None:
                self.gaps.append(x + self.GAP / 2)
                self.parts.append((a, b, None, x + self.GAP / 2)); x += self.GAP
            else:
                self.parts.append((a, b, k, x)); x += (b - a) * k
        self.x_end = x
        self.pieces = []                                   # visible stretches of time without a break
        for a, b, k, _ in self.parts:
            if k is None:
                self.pieces.append(None)
            elif self.pieces and self.pieces[-1] is not None:
                self.pieces[-1] = (self.pieces[-1][0], b)
            else:
                self.pieces.append((a, b))
        self.pieces = [p for p in self.pieces if p is not None]
        self.t0 = t0

    def x(self, t):
        for a, b, k, x0 in self.parts:
            if t <= b:
                if k is None:
                    return x0
                return x0 + (max(t, a) - a) * k
        return self.x_end


# ------------------------------------------------------------------ drawing
def _bus_box(ax, xs, xe, y, h, text, col, fs, inch_per_x):
    d = min(1.2, (xe - xs) / 3)
    poly = [(xs, y), (xs + d, y - h / 2), (xe - d, y - h / 2), (xe, y), (xe - d, y + h / 2), (xs + d, y + h / 2)]
    idle = text in ('off', '–', '0 V', 'none', 'IDLE', 'VSS', 'VSS (all)')
    face = 'white' if idle else (MAROON_L if col == 'm' else (NAVY_L if col == 'n' else '#EFEFEF'))
    edge = MAROON if col == 'm' else (NAVY if col == 'n' else 'black')
    ax.add_patch(Polygon(poly, closed=True, facecolor=face, edgecolor=edge, lw=0.8, zorder=2))
    wid_in = (xe - xs - 2 * d) * inch_per_x
    for f in (fs, fs - 1, fs - 2):
        if len(text) * f * 0.55 / 72 < wid_in:
            ax.text((xs + xe) / 2, y, text, ha='center', va='center', fontsize=f, color=edge, zorder=3)
            break


def mode_waves(vcd, mode, out_png, dpi=200, width=13.0, title=False):
    """Draw the timing diagram of one mode ('form' | 'read' | 'sense' | 'write') from the tb_modes VCD into out_png."""
    V = vcd if isinstance(vcd, Vcd) else Vcd(vcd)
    M = MODES[mode]
    # window of this scenario and its steps
    ts, vs = V.sig['scen']
    code = format(M['scen'], '08b')
    k = vs.index(code)
    t0, t1 = ts[k], (ts[k + 1] if k + 1 < len(ts) else V.t_end)
    sts, svs = V.sig['seg']
    marks = [(t, int(v, 2)) for t, v in zip(sts, svs) if t0 <= t < t1 and int(v, 2) > 0]
    spans = [(c, (t, marks[j + 1][0] if j + 1 < len(marks) else t1)) for j, (t, c) in enumerate(marks)]
    ax_t = Axis(t0, t1, spans, M['cut'], M.get('stretch'))
    events = [t0] + [t for t in V.changes(t0, t1) if t0 < t < t1]
    states = [State(V, t) for t in events]

    rows = [(g, r) for g, rs in M['groups'] for r in rs]
    n = len(rows)
    RH = 0.30                                              # inch per signal row
    top_in, bot_in = (0.95 if title else 0.6), 0.55
    H = n * RH + top_in + bot_in
    fig = plt.figure(figsize=(width, H))
    left_in, right_in = 3.05, 0.15
    ax = fig.add_axes([left_in / width, bot_in / H, 1 - (left_in + right_in) / width, (n * RH + 0.55) / H])
    ax.set_xlim(-1.0, ax_t.x_end + 1.0)
    ax.set_ylim(n, -1.85)                                  # rows 0..n-1, band at -1.8 .. -0.3
    ax.axis('off')
    inch_per_x = (width - left_in - right_in) / (ax_t.x_end + 2.0)

    # step bands
    for j, (c, (a, b)) in enumerate(spans):
        xa, xb = ax_t.x(a), ax_t.x(b)
        ax.add_patch(Rectangle((xa, -1.75), xb - xa, 1.25, facecolor='#E9E9E9' if j % 2 == 0 else 'white',
                               edgecolor=GREY, lw=0.6, zorder=1))
        name = M['segs'].get(c, '')
        wid = (xb - xa) * inch_per_x
        words, lines = name.split(), ['']
        for w in words:                                    # wrap into lines that fit the band width
            if lines[-1] and len(lines[-1] + ' ' + w) * 8 * 0.5 / 72 > wid - 0.06:
                lines.append(w)
            else:
                lines[-1] = (lines[-1] + ' ' + w).strip()
        fs = 8 if len(lines) <= 2 else 7
        ax.text((xa + xb) / 2, -1.12, '\n'.join(lines[:3]), ha='center', va='center', fontsize=fs, zorder=3, linespacing=1.0)
        if j > 0:
            ax.plot([xa, xa], [-0.3, n - 0.1], color='#BDBDBD', lw=0.6, ls=(0, (2, 2)), zorder=0)

    # signal rows
    gstart = 0
    for g, rs in M['groups']:
        y0, y1 = gstart - 0.45, gstart + len(rs) - 0.55
        ax.text(-1.0 - 2.75 / inch_per_x, (y0 + y1) / 2, g, ha='left', va='center', fontsize=8.5, fontweight='bold',
                color='#333333', clip_on=False)
        ax.plot([-1.0 - 1.95 / inch_per_x] * 2, [y0 + 0.08, y1 - 0.08], color=GREY, lw=0.8, clip_on=False)
        if gstart > 0:
            ax.plot([-1.0 - 2.75 / inch_per_x, ax_t.x_end + 1.0], [y0, y0], color='#D0D0D0', lw=0.6, clip_on=False, zorder=0)
        gstart += len(rs)

    for i, (g, (label, kind, fn, col)) in enumerate(rows):
        c = MAROON if col == 'm' else (NAVY if col == 'n' else 'black')
        ax.text(-1.0 - 0.06 / inch_per_x, i, label, ha='right', va='center', fontsize=9, color=c, clip_on=False)
        vals = [fn(S) for S in states]
        # merge into intervals
        iv = []
        for t, v in zip(events, vals):
            if iv and iv[-1][2] == v:
                continue
            if iv:
                iv[-1][1] = t
            iv.append([t, t1, v])
        for (a, b) in ax_t.pieces:
            seg_iv = [(max(s, a), min(e, b), v) for s, e, v in iv if e > a and s < b]
            if kind == 'd':
                xs, ys = [], []
                for s, e, v in seg_iv:
                    if v is None:
                        ax.add_patch(Rectangle((ax_t.x(s), i - 0.3), ax_t.x(e) - ax_t.x(s), 0.6, facecolor='#DDDDDD',
                                               edgecolor='none', zorder=1))
                        continue
                    y = i + 0.3 - 0.6 * v
                    xs += [ax_t.x(s), ax_t.x(e)]; ys += [y, y]
                ax.plot(xs, ys, color=c, lw=1.5 if col == 'm' else 1.1, solid_joinstyle='miter', zorder=3)
            else:
                for s, e, v in seg_iv:
                    _bus_box(ax, ax_t.x(s), ax_t.x(e), i, 0.62, v, col, 8, inch_per_x)

    # breaks
    for xg in ax_t.gaps:
        for i in range(n):
            for dx in (-1.0, 1.0):
                ax.plot([xg + dx - 0.9, xg + dx + 0.9], [i + 0.38, i - 0.38], color='#555555', lw=0.8, zorder=4)
        for dx in (-1.0, 1.0):
            ax.plot([xg + dx - 0.9, xg + dx + 0.9], [n - 0.05, n - 0.55], color='#555555', lw=0.8, zorder=4, clip_on=False)

    # time axis (ns from the start of the figure)
    ya = n - 0.3
    ax.plot([0, ax_t.x_end], [ya, ya], color='black', lw=0.8, clip_on=False)
    placed = []
    for (a, b, k, x0) in ax_t.parts:
        if k is None:
            continue
        step = next(st for st in (5, 10, 20, 50, 100, 200, 500) if st * k * inch_per_x >= 0.42)
        tk = -(-(a - t0) // step) * step
        while tk <= b - t0 + 1e-6:
            x = ax_t.x(t0 + tk)
            far = all(abs(x - p) * inch_per_x > 0.40 for p in placed) and all(abs(x - g) * inch_per_x > 0.22 for g in ax_t.gaps)
            if far:
                placed.append(x)
                ax.plot([x, x], [ya, ya + 0.15], color='black', lw=0.8, clip_on=False)
                ax.text(x, ya + 0.25, f'{tk:g}', ha='center', va='top', fontsize=8, clip_on=False)
            tk += step
    if M.get('stretch'):
        names = ', '.join(M['segs'][c] for c in M['stretch'])
        ax.text(0, ya + 0.95, f'{names}: drawn wider than the time scale (tick labels give the real time)',
                ha='left', va='top', fontsize=7.5, color='#555555', clip_on=False)
    ax.text(ax_t.x_end, ya + 0.95, 'time (ns)', ha='right', va='top', fontsize=8.5, clip_on=False)
    if title:
        fig.text(left_in / width, 1 - 0.12 / H, M['title'], ha='left', va='top', fontsize=10.5, fontweight='bold')
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)
    return out_png


def all_modes(vcd, out_dir):
    V = Vcd(vcd)
    return [mode_waves(V, m, os.path.join(out_dir, f'fig_wave_{m}.png')) for m in ('form', 'read', 'sense', 'write')]


if __name__ == '__main__':
    for p in all_modes(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '.'):
        print(p)

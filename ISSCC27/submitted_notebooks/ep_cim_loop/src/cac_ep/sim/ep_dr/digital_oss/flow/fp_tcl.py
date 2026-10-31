"""fp.json + pins.cfg → OpenROAD 가 source 하는 Tcl 값 (pnr.tcl). 쓰임: python3 fp_tcl.py <blocks/blk> <out.tcl>"""
import json
import sys
from pathlib import Path
d, out = Path(sys.argv[1]), sys.argv[2]
f = json.loads((d / 'fp.json').read_text())
p = f['pdn']; v = p['via']
L = [f"set TOP {f['top']}", f"set DIE_W {f['die'][2]}", f"set DIE_H {f['die'][3]}", f"set SITE {f['site']}",
     f"set ROW_X {f['row_x']}", f"set ROW_Y0 {f['row_y0']}", f"set ROW_H {f['row_h']}", f"set NROWS {f['nrows']}",
     f"set NSITES {f['nsites']}", f"set SITE_W {f['site_w']}", f"set FIRST_OR {f['first_orient']}",
     f"set PDN_BAND_W {p['band_w']}", f"set PDN_STRIPE_LAYER {p['stripe_layer']}", f"set PDN_STRIPE_W {p['stripe_w']}",
     f"set PDN_STRIPE_SP {p['stripe_sp']}", f"set PDN_STRIPE_PITCH {p['stripe_pitch']}", f"set PDN_STRIPE_OFF {p['stripe_off']}",
     f"set PDN_STRIPE_EXT {p['stripe_ext']}", f"set VIA_CUT {{{v['cut'][0]} {v['cut'][1]}}}", f"set VIA_CUTSP {{{v['cutsp'][0]} {v['cutsp'][1]}}}",
     f"set VIA_ENC {{{' '.join(map(str, v['enc']))}}}", f"set VIA_ROWCOL {{{v['rowcol'][0]} {v['rowcol'][1]}}}"]
L.append('set TRACKS {' + ' '.join(f"{{{lay} {t['X'][0]} {t['X'][1]} {t['Y'][0]} {t['Y'][1]}}}"
                                   for lay, t in f['tracks'].items() if lay in ('li1', 'met1', 'met2', 'met3', 'met4', 'met5')) + '}')
pins = []
for l in (d / 'pins.cfg').read_text().splitlines():
    if not l.strip() or l.startswith('#'):
        continue
    nm, dr, lay, *xy = l.split()
    pins.append(f"{{{{{nm}}} {dr} {lay} " + ' '.join(str(round(float(c) * 1000)) for c in xy) + '}')
L.append('set PINS [list ' + ' '.join(pins) + ']')
if 'row_list' in f:
    rl = f['row_list']
    core = f.get('core') or [min(r[0] for r in rl), min(r[1] for r in rl), max(r[0] + r[3] * f['site_w'] for r in rl),
                             max([r[1] + f['row_h'] for r in rl] + [b[3] for b in f.get('place_blockages', [])])]
    L.append('set CORE {' + ' '.join(map(str, core)) + '}')
    L.append('set ROW_LIST {' + ' '.join('{%d %d %s %d}' % tuple(r) for r in rl) + '}')
if 'macros' in f:
    L.append('set MACROS {' + ' '.join('{%s %s %d %d %s}' % tuple(m) for m in f['macros']) + '}')
if 'place_blockages' in f:
    L.append('set PLACE_BLK {' + ' '.join('{%d %d %d %d}' % tuple(b) for b in f['place_blockages']) + '}')
rb = [tuple(b) for b in f.get('route_blockages', [])]
if (d / 'keepout.json').exists():            # 칩 전원 drop stack 자리 (mk_keepout.py)
    rb += [tuple(b) for b in json.loads((d / 'keepout.json').read_text())['rects']]
# 핀 옆 비움 (block.env CLEAR_PINS 정규식에 맞는 경계 핀만): 칩 배선이 핀에 대는 선·via pad 는 핀보다 조금 넓고 칩 LEF 의 OBS 는 핀 둘레 halo 만큼 비어 있어,
# 블록 안 신호선이 핀 바로 옆을 지나면 칩에서 met2.2·met3.2 간격 위반 (10/30 full 시험: data_blk 서쪽 sp·sm, row_blk 동쪽 제어·북쪽 vwl, col_blk 서쪽 제어 핀).
# → 핀 길이 (경계 ~ 핀 안쪽 끝) 동안만 양옆에 폭 w (met3 0.35 / met2 0.2 µm, 이웃 핀과는 겹치지 않게) 막기. 안쪽 끝은 열어 둠 (블록 배선이 핀에 닿는 자리).
import os
import re as _re
pat = os.environ.get('CLEAR_PINS', '')
WCL = {'met2': 200, 'met3': 350}
die = f['die']
pl = [(nm, lay, *[round(float(c) * 1000) for c in xy]) for nm, dr, lay, *xy in
      (l.split() for l in (d / 'pins.cfg').read_text().splitlines() if l.strip() and not l.startswith('#'))]
nclr = 0
for nm, lay, x1, y1, x2, y2 in (pl if pat else []):
    if not _re.match(pat, nm) or lay not in WCL:
        continue
    side = 'W' if x1 <= die[0] else 'E' if x2 >= die[2] else 'S' if y1 <= die[1] else 'N' if y2 >= die[3] else None
    if side is None:
        continue
    horiz = side in 'WE'
    gap = min([(o[3] - y2 if o[3] > y2 else y1 - o[5]) if horiz else (o[2] - x2 if o[2] > x2 else x1 - o[4])
               for o in pl if o[0] != nm and o[1] == lay and ((o[2] < x2 and o[4] > x1) if horiz else (o[3] < y2 and o[5] > y1))] + [10 ** 6])
    w = min(WCL[lay], (gap - 300) // 2)
    if w < 100:
        continue
    if horiz:
        rb += [(lay, x1, y2, x2, y2 + w), (lay, x1, y1 - w, x2, y1)]
    else:
        rb += [(lay, x2, y1, x2 + w, y2), (lay, x1 - w, y1, x1, y2)]
    nclr += 1
if rb:
    L.append('set ROUTE_BLK {' + ' '.join('{%s %d %d %d %d}' % b for b in rb) + '}')
if 'vias' in f:
    vd = []
    for n, v in f['vias'].items():
        if 'rects' in v:
            vd.append('{%s rect {%s}}' % (n, ' '.join('{%s %d %d %d %d}' % tuple(r) for r in v['rects'])))
        else:
            vd.append('{%s gen {%d %d %s %s %s %d %d %d %d %d %d %d %d}}' % (n, *v['cut'], *v['layers'], *v['cutsp'], *v['enc'], *v['rowcol']))
    L.append('set VIADEFS {' + ' '.join(vd) + '}')
if 'special' in f:
    sp = []
    for p in f['special']:
        sp.append('{{%s} VIA %s %d %d %s}' % (p[0], *p[2:]) if p[1] == 'VIA' else '{{%s} %s %d %d %d %d %s}' % tuple(p))
    L.append('set SPECIAL [list ' + ' '.join(sp) + ']')
if 'ndr' in f:
    um = lambda d: '{' + ' '.join(f'{k} {v / 1000:g}' for k, v in d.items()) + '}'
    L.append('set NDRS [list ' + ' '.join('{%s %s %s {%s}}' % (r['name'], um(r['width']), um(r['spacing']), ' '.join('{%s}' % n for n in r['nets'])) for r in f['ndr']) + ']')
open(out, 'w').write('\n'.join(L) + '\n')
print('fp tcl', out, 'pins', len(pins), 'pin clearances', nclr)

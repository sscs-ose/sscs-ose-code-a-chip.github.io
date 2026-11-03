"""블록 LEF abstract + 핀 좌표 표 + 원점 맞춘 GDS 사본 (10/28, 칩 core 조립 `place/` 담당).
사용자 지시 (10/28): "에이전트는 최대한 많이 써서 작업을 해 보게", "각 블럭 길이 연결하는 것과 lvs 통과와 DRC 통과가 되면은 CaC 제출 기준에 만족".

규칙 (layout/top/README.md §1, place 지시):
  - 핀: GDS 이름표 (X/5) 가 붙은 금속 (X/20) 의 같은 넷 도형 (flatten 후 merge, 이름표 점을 품은 polygon).
    블록 경계에 닿는 polygon 은 경계 안쪽 EW = 1.4 µm 띠로 자른 조각 (접근 stub), 닿지 않으면 이름표 둘레 ±3 µm 조각, 작은 패드 (≤ 6 µm) 는 통째.
  - OBS: 블록이 쓰는 금속 met1–met3 (+met4 있으면) 의 실제 도형 − (핀 사각형 + 층 최소 간격 halo). 핀을 OBS 에서 빼는 것은
    li1 은 블록 전체를 막는다 (top 은 li1 을 쓰지 않음). 배열 = met3·met4 블록 전체 (덧대기 자리). WU = met4 실제 도형 + wu.json met4_keepout.
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python mk_lef.py   → lef/<cell>.lef, lef/pins_all.json, gds/<cell>.gds, lef/lef_report.txt
"""
import json
import re
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent                       # layout/top/place
L = H.parents[1]                                          # layout
EP = L.parent                                             # ep_dr
OUT, GOUT = H / 'lef', H / 'gds'
TLEF = Path.home() / 'pdk/volare/sky130A/libs.ref/sky130_fd_sc_hvl/techlef/sky130_fd_sc_hvl__nom.tlef'

MET = {'li1': (67, 20), 'met1': (68, 20), 'met2': (69, 20), 'met3': (70, 20), 'met4': (71, 20)}
LBL = {(67, 5): 'li1', (68, 5): 'met1', (69, 5): 'met2', (70, 5): 'met3', (71, 5): 'met4'}
EW, TOL, SMALL, NEAR = 1400, 500, 6000, 3000                 # nm: 핀 stub 깊이, 경계 닿음 허용, 작은 패드, 이름표 둘레
HALO = {'met1': 140, 'met2': 140, 'met3': 300, 'met4': 300}  # 핀 둘레 OBS 를 비우는 폭 = 층 최소 간격 (m1.2·m2.2 0.14, m3.2·m4.2 0.30)

DIR = {
    'input_drive': lambda p: 'INPUT' if re.match(r'g[ab]\d+$|READ$', p) else 'INOUT',
    'wbuf': lambda p: {'wp': 'INPUT', 'pol': 'INPUT', 'out': 'OUTPUT'}.get(p, 'INOUT'),
    'nudge_inj': lambda p: 'INPUT' if re.match(r'(sp|spb|sm|smb)\d$|pref$|nref$', p) else 'OUTPUT' if re.match(r'y[pm]\d$', p) else 'INOUT',
    'bias_beta': lambda p: {'vbn': 'INPUT', 'vbp': 'INPUT', 'vbpc': 'INPUT', 'pref': 'OUTPUT', 'nref': 'OUTPUT'}.get(p, 'INOUT'),
    'wu': lambda p: ('INPUT' if p in ('ck', 'ck3', 'lat', 'latb', 'lq', 'sen', 'vbn', 'vbp', 'vbnc', 'vbpc')
                     else 'OUTPUT' if p in ('absf', 'absn', 'q1', 'q2') else 'INOUT'),
    'tg_n2': lambda p: 'INPUT' if p in ('ctl', 'ctlb') else 'INOUT',
}
ARR_SIDES = lambda p: 'WE' if re.match(r'(row|wl)_\d+$', p) else 'S' if re.match(r'col_\d+$', p) else 'WESN'   # 배열 핀이 나가는 변
BLOCKS = [
    dict(cell='arr_w3_128x64', gds=L / 'blocks/arr_w3_128x64.gds', full=('met3', 'met4'), sides=ARR_SIDES),
    dict(cell='arr_w3s_128x64', gds=L / 'top/strap/arr_w3s_128x64.gds', full=('met3', 'met4'), sides=ARR_SIDES,   # 덧댄 판 (strap/README.md, 칩 정본)
         add_pins=lambda: STRAP_PINS(), windows=lambda: STRAP_WIN()),
    dict(cell='input_drive', gds=L / 'blk_analog/out/input_drive.gds', js=L / 'blk_analog/out/input_drive.json'),
    dict(cell='wbuf', gds=L / 'blk_analog/out/wbuf.gds', js=L / 'blk_analog/out/wbuf.json'),
    dict(cell='nudge_inj', gds=L / 'blk_analog/out/nudge_inj.gds', js=L / 'blk_analog/out/nudge_inj.json'),
    dict(cell='bias_beta', gds=L / 'blk_analog/out/bias_beta.gds', js=L / 'blk_analog/out/bias_beta.json'),
    dict(cell='wu', gds=L / 'blk_wu/out/wu.gds', js=L / 'blk_wu/out/wu.json', keepout=True),
    dict(cell='tg_n2', gds=L / 'blocks/tg_n2.gds'),
    dict(cell='row_blk', gds=EP / 'digital/row_blk/out/row_blk/row_blk_lbl.gds', deff=EP / 'digital/row_blk/out/row_blk/row_blk_pnr.def'),
    dict(cell='col_blk', gds=EP / 'digital/col_blk/out/col_blk/col_blk_lbl.gds', deff=EP / 'digital/col_blk/out/col_blk/col_blk_pnr.def'),
    # data_blk = ga·gb 핀을 input_drive 와 같은 y (met2) 에 고정한 판 (place/data_blk_repin, 잡 721298: DRC 밀도만, LVS MATCH). 원본 = L / 'blk_digital/out/'
    dict(cell='data_blk', gds=H / 'data_blk_repin/out/data_blk_lbl.gds', deff=H / 'data_blk_repin/out/data_blk_pnr.def'),
    dict(cell='glob_dig', gds=L / 'blk_digital/out/glob_dig_lbl.gds', deff=L / 'blk_digital/out/glob_dig_pnr.def'),
] + [  # test pattern 네 블록 (testpat/, 잡 721328 DRC 밀도만 + LVS MATCH). 핀 = json 의 met3 패드, VDD·VSS = json power 의 위·아래 met3 띠 (조정 세션 10/28)
    dict(cell=f'tp_{t}', gds=L / f'top/testpat/out/tp_{t}.gds', tpjs=L / f'top/testpat/out/tp_{t}.json') for t in ('tl', 'br', 'bandl', 'bandr')
]


# 덧댄 배열 (strap/README.md「배치·배선 쪽에 알릴 것」, 셀 원점 좌표 µm): WL 동쪽 met2 landing·열 아래 끝 met2 landing 을 핀에 더하고,
# met3 전면 OBS 에서 WL 접근 창을 연다 (via2 를 landing 위에 놓을 자리, 창 안에는 met3 가 없음 → 아래에서 GDS 로 확인).
NR, NC, PX, PY = 128, 64, 5.115, 3.41


def STRAP_PINS():
    d = {f'wl_{r}': [('met2', db.DBox(325.05, r * PY + 2.05, 326.41, r * PY + 2.47))] for r in range(NR)}
    d.update({f'col_{c}': [('met2', db.DBox(c * PX - 1.2, -2.2, c * PX + 1.7, -0.83))] for c in range(NC)})
    return d


def STRAP_WIN():
    return {'met3': [db.DBox(324.9, r * PY + 0.85, 326.41, r * PY + 2.47) for r in range(NR)]}


def use_of(p):
    return 'POWER' if p.upper() == 'VDD' else 'GROUND' if p.upper() == 'VSS' else 'SIGNAL'


def boxes(reg):
    """Manhattan region → db.Box 목록 (가로 사다리꼴 분해 = 사각형)."""
    out = []
    for poly in reg.each():
        for sp in poly.decompose_trapezoids(db.Polygon.TD_htrapezoids):
            b = sp.bbox()
            assert db.Polygon(b).area() == sp.area(), 'non-Manhattan 도형'
            out.append(b)
    return out


def tlef_layers():
    return set(re.findall(r'^LAYER (\S+)', TLEF.read_text(), re.M))


ORI = {'N': lambda x, y: (x, y), 'S': lambda x, y: (-x, -y), 'W': lambda x, y: (-y, x), 'E': lambda x, y: (y, -x),
       'FN': lambda x, y: (-x, y), 'FS': lambda x, y: (x, -y), 'FW': lambda x, y: (y, x), 'FE': lambda x, y: (-y, -x)}


def read_def(path):
    t = path.read_text()
    die = [int(v) for v in re.search(r'DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', t).groups()]
    pins = {}
    sec = t[t.index('\nPINS '):t.index('END PINS')]
    for ent in sec.split('\n- ')[1:]:
        nm = ent.split()[0]
        d = re.search(r'DIRECTION (\w+)', ent); u = re.search(r'USE (\w+)', ent)
        lay = re.search(r'LAYER (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ent)
        pl = re.search(r'(?:FIXED|PLACED) \( (-?\d+) (-?\d+) \) (\w+)', ent)
        assert lay and pl and 'PORT' not in ent, ('DEF 핀 형식', nm)
        x1, y1, x2, y2 = map(int, lay.groups()[1:]); px, py = int(pl.group(1)), int(pl.group(2)); f = ORI[pl.group(3)]
        c = [f(x1, y1), f(x2, y2)]
        r = db.Box(px + min(a for a, _ in c), py + min(b for _, b in c), px + max(a for a, _ in c), py + max(b for _, b in c))
        pins[nm] = dict(dir=d.group(1) if d else 'INOUT', use=u.group(1) if u else 'SIGNAL', shapes=[(lay.group(1), r)])
    # SPECIALNETS: RECT 와 폭 있는 경로 (끝 연장 0, DEF special wire). 폭 0 + via 는 건넘.
    ss = t[t.index('\nSPECIALNETS'):t.index('END SPECIALNETS')]
    for ent in ss.split('\n- ')[1:]:
        nm = ent.split()[0]
        shp = []
        for m in re.finditer(r'RECT (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ent):
            shp.append((m.group(1), db.Box(*map(int, m.groups()[1:]))))
        for m in re.finditer(r'(?:ROUTED|NEW) (\S+) (\d+) \+ SHAPE \w+ \( (-?\d+) (-?\d+) \) \( (\*|-?\d+) (\*|-?\d+) \)', ent):
            lay, w, x1, y1 = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
            x2 = x1 if m.group(5) == '*' else int(m.group(5)); y2 = y1 if m.group(6) == '*' else int(m.group(6))
            if w == 0:
                continue
            h = w // 2
            shp.append((lay, db.Box(min(x1, x2) - (h if x1 == x2 else 0), min(y1, y2) - (h if y1 == y2 else 0),
                                    max(x1, x2) + (h if x1 == x2 else 0), max(y1, y2) + (h if y1 == y2 else 0))))
        pins[nm] = dict(dir='INOUT', use='POWER' if nm == 'VDD' else 'GROUND', shapes=shp)
    return db.Box(*die), pins


# ── GDS 핀 (이름표 → 같은 넷 금속)
def gds_pins(ly, top, bnd, flat, sides=lambda p: 'WESN'):
    pins, warn = {}, []
    win_all = {}
    for (l, d), lay in LBL.items():
        li = ly.find_layer(l, d)
        if li is None:
            continue
        for s in top.shapes(li).each():
            if not s.is_text():
                continue
            nm, p = s.text_string, db.Point(s.text.x, s.text.y)
            poly = flat[lay].interacting(db.Region(db.Box(p.x - 1, p.y - 1, p.x + 1, p.y + 1)))
            if poly.is_empty():
                warn.append(f'{nm}: 이름표 ({p.x / 1000:.3f}, {p.y / 1000:.3f}) 밑에 {lay} 도형 없음')
                continue
            bb = poly.bbox()
            sd = sides(nm)
            if bb.width() <= SMALL and bb.height() <= SMALL:
                piece = poly
            else:
                w = db.Region()
                if bb.left - bnd.left <= TOL and 'W' in sd:
                    w.insert(db.Box(bnd.left, bnd.bottom, bnd.left + EW, bnd.top))
                if bnd.right - bb.right <= TOL and 'E' in sd:
                    w.insert(db.Box(bnd.right - EW, bnd.bottom, bnd.right, bnd.top))
                if bb.bottom - bnd.bottom <= TOL and 'S' in sd:
                    w.insert(db.Box(bnd.left, bnd.bottom, bnd.right, bnd.bottom + EW))
                if bnd.top - bb.top <= TOL and 'N' in sd:
                    w.insert(db.Box(bnd.left, bnd.top - EW, bnd.right, bnd.top))
                piece = poly & w if not w.is_empty() else db.Region()
                if piece.is_empty():
                    piece = poly & db.Region(db.Box(p.x - NEAR, p.y - NEAR, p.x + NEAR, p.y + NEAR))
            ent = pins.setdefault(nm, dict(dir=None, use=use_of(nm), shapes=[]))
            seen = {(a, b.left, b.bottom, b.right, b.top) for a, b in ent['shapes']}
            for b in boxes(piece.merged()):
                if (lay, b.left, b.bottom, b.right, b.top) not in seen:
                    ent['shapes'].append((lay, b))
    return pins, warn


def write_lef(cell, bnd, pins, obs, full, keep, win=None):
    ox, oy = bnd.left, bnd.bottom
    u = lambda v: f'{v / 1000:.3f}'
    R = lambda b: f'RECT {u(b.left - ox)} {u(b.bottom - oy)} {u(b.right - ox)} {u(b.top - oy)} ;'
    o = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', '',
         f'MACRO {cell}', '  CLASS BLOCK ;', f'  FOREIGN {cell} 0 0 ;', '  ORIGIN 0 0 ;',
         f'  SIZE {u(bnd.width())} BY {u(bnd.height())} ;', '  SYMMETRY X Y ;']
    for pn in sorted(pins, key=lambda s: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]):
        P = pins[pn]
        o += [f'  PIN {pn}', f'    DIRECTION {P["dir"]} ;', f'    USE {P["use"]} ;', '    PORT']
        for lay in ('met1', 'met2', 'met3', 'met4', 'li1'):
            bl = [b for a, b in P['shapes'] if a == lay]
            if bl:
                o += [f'      LAYER {lay} ;'] + [f'        {R(b)}' for b in bl]
        o += ['    END', f'  END {pn}']
    o += ['  OBS', '    LAYER li1 ;', f'      {R(bnd)}']
    for lay in ('met1', 'met2', 'met3', 'met4'):
        if lay in full and win and win.get(lay):                     # 전면 막음 − 창
            o += [f'    LAYER {lay} ;'] + [f'      {R(b)}' for b in boxes(db.Region(bnd) - win[lay])]
        elif lay in full:
            o += [f'    LAYER {lay} ;', f'      {R(bnd)}']
        elif lay in obs and obs[lay]:
            o += [f'    LAYER {lay} ;'] + [f'      {R(b)}' for b in obs[lay]]
        if lay == 'met4' and keep:
            if not (lay in obs and obs[lay]):
                o += ['    LAYER met4 ;']
            o += [f'      {R(b)}' for b in keep]
    o += ['  END', f'END {cell}', '', 'END LIBRARY', '']
    (OUT / f'{cell}.lef').write_text('\n'.join(o))


def main():
    OUT.mkdir(exist_ok=True); GOUT.mkdir(exist_ok=True)
    tl = tlef_layers()
    assert {'li1', 'met1', 'met2', 'met3', 'met4'} <= tl, ('tech LEF 층 이름', tl)
    ALL, REP = {}, []
    for B in BLOCKS:
        cell = B['cell']
        if not B['gds'].exists():
            if B.get('optional'):
                REP.append(f'{cell}: {B["gds"]} 아직 없음 → 건넘 (배열 LEF 와 핀·크기가 같다는 약속, 생기면 다시 돈다)')
                continue
            raise FileNotFoundError(B['gds'])
        ly = db.Layout(); ly.read(str(B['gds']))
        top = ly.cell(cell) or ly.top_cells()[0]
        assert top.name == cell, (cell, top.name)
        flat = {k: db.Region(top.begin_shapes_rec(ly.layer(*v))).merged() for k, v in MET.items()}
        pb = ly.find_layer(235, 4)
        warn = []
        if B.get('deff'):
            bnd, pins = read_def(B['deff']); src = 'DEF DIEAREA'
            gb = top.bbox()
            if not bnd.contains(gb.p1) or not bnd.contains(gb.p2):
                warn.append(f'GDS bbox {gb} 가 DIEAREA 밖으로 나옴')
            gp, gw = gds_pins(ly, top, bnd, flat)                           # 대조용 (이름표와 DEF 핀이 같은 자리인지)
            for nm, P in gp.items():
                if nm in ('VDD', 'VSS'):
                    continue
                if nm not in pins:
                    warn.append(f'GDS 이름표 {nm} 가 DEF 핀에 없음')
                elif not any(a == c and b.overlaps(d) for a, b in P['shapes'] for c, d in pins[nm]['shapes']):
                    warn.append(f'{nm}: GDS 이름표 도형과 DEF 핀 사각형이 안 겹침')
            miss = [p for p in pins if p not in gp and p not in ('VDD', 'VSS')]
            if miss:
                warn.append(f'DEF 핀 중 GDS 이름표 없는 것 {len(miss)}: {miss[:5]}')
        else:
            if pb is not None and not db.Region(top.begin_shapes_rec(pb)).is_empty():
                bnd = db.Region(top.begin_shapes_rec(pb)).bbox(); src = 'prBoundary 235/4'
            else:
                bnd = top.bbox(); src = 'GDS bbox'
            pins, warn = gds_pins(ly, top, bnd, flat, B.get('sides', lambda p: 'WESN'))
            if B.get('tpjs'):                                                # test pattern: 핀 = json 사각형 (GDS 이름표 넷 도형과 대조)
                TJ = json.loads(B['tpjs'].read_text())
                assert abs(TJ['w'] - bnd.width() / 1000) < 1e-6 and abs(TJ['h'] - bnd.height() / 1000) < 1e-6, ('test 크기', cell)
                tsrc = dict(TJ['pins']); tsrc.update(TJ['power'])
                if set(tsrc) != set(pins):
                    warn.append(f'json 핀 {len(tsrc)} ≠ GDS 이름표 {len(pins)}: {sorted(set(tsrc) ^ set(pins))[:6]}')
                new = {}
                for nm, q in tsrc.items():
                    bx = db.DBox(*q['box']).to_itype(ly.dbu); lay = q['layer']
                    if not (db.Region(bx) - flat[lay]).is_empty():
                        warn.append(f'{nm}: json 사각형이 {lay} 금속으로 다 덮이지 않음')
                    if nm in pins and not any(a == lay and b.overlaps(bx) for a, b in pins[nm]['shapes']):
                        warn.append(f'{nm}: json 사각형과 GDS 이름표 넷 도형이 안 겹침')
                    new[nm] = dict(dir=None, use=use_of(nm), shapes=[(lay, bx)])
                pins = new
            f = DIR.get(cell, lambda p: 'INOUT')
            for nm, P in pins.items():
                P['dir'] = f(nm)
            if B.get('add_pins'):                                            # 더하는 핀 사각형: 그 넷의 금속 안에 있어야 함
                nadd = 0
                for nm, lst in B['add_pins']().items():
                    for lay, dbx in lst:
                        bx = dbx.to_itype(ly.dbu)
                        netpoly = flat[lay].interacting(db.Region(bx))
                        if (db.Region(bx) - flat[lay]).is_empty() and not netpoly.is_empty():
                            pins[nm]['shapes'].append((lay, bx)); nadd += 1
                        else:
                            warn.append(f'{nm}: 더할 {lay} 사각형 {dbx} 이 금속으로 다 덮이지 않음 → 뺌')
                warn.append(f'(정보) strap landing 핀 사각형 {nadd} 개 더함') if nadd else None
            if B.get('js') and B['js'].exists():                             # 생성기 json 의 핀 사각형과 대조
                J = json.loads(B['js'].read_text()).get('pins', {})
                for nm, lst in J.items():
                    lst = lst if isinstance(lst, list) else [lst]
                    if nm not in pins:
                        warn.append(f'json 핀 {nm} 이 GDS 이름표에 없음'); continue
                    ok = any(a == q['layer'] and b.overlaps(db.DBox(*q['rect']).to_itype(ly.dbu))
                             for q in lst for a, b in pins[nm]['shapes'])
                    if not ok:
                        warn.append(f'{nm}: json 사각형 {lst[0]["rect"]} 과 GDS 핀 도형이 안 겹침')
        # OBS: 실제 도형 − (핀 + halo)
        obs = {}
        for lay in ('met1', 'met2', 'met3', 'met4'):
            r = flat[lay]
            pr = db.Region([b for P in pins.values() for a, b in P['shapes'] if a == lay])
            if lay in B.get('full', ()) and not pr.is_empty():
                warn.append(f'{lay} 를 통째로 막았는데 그 층에 핀이 있음 ({pr.count()} 개)')
            if r.is_empty() or lay in B.get('full', ()):
                continue
            obs[lay] = boxes((r & db.Region(bnd)) - pr.sized(HALO[lay]))
        keep = []
        if B.get('keepout'):
            for k in json.loads(B['js'].read_text())['met4_keepout']:
                keep.append(db.DBox(*k).to_itype(ly.dbu))
        win = {}
        if B.get('windows'):
            for lay, lst in B['windows']().items():
                wr = db.Region([b.to_itype(ly.dbu) for b in lst])
                if not (wr & flat[lay]).is_empty():
                    warn.append(f'{lay} 창 안에 금속이 있음 ({(wr & flat[lay]).area() / 1e6:.3f} µm²)')
                win[lay] = wr
            warn.append(f'(정보) OBS 창: ' + ', '.join(f'{k} {v.count()} 곳' for k, v in win.items()))
        write_lef(cell, bnd, pins, obs, B.get('full', ()), keep, win)
        # 원점 맞춘 GDS 사본
        gds_use = str(B['gds'])
        if bnd.left != 0 or bnd.bottom != 0:
            top.transform(db.Trans(-bnd.left, -bnd.bottom))
            so = db.SaveLayoutOptions(); so.add_cell(top.cell_index())
            ly.write(str(GOUT / f'{cell}.gds'), so)
            gds_use = str(GOUT / f'{cell}.gds')
        ox, oy = bnd.left, bnd.bottom
        ALL[cell] = dict(size=[bnd.width() / 1000, bnd.height() / 1000], boundary=src, gds=gds_use, gds_src=str(B['gds']),
                         shift_um=[-ox / 1000, -oy / 1000],
                         pins={nm: dict(dir=P['dir'], use=P['use'],
                                        shapes=[[a, (b.left - ox) / 1000, (b.bottom - oy) / 1000, (b.right - ox) / 1000, (b.top - oy) / 1000]
                                                for a, b in P['shapes']]) for nm, P in pins.items()})
        n_obs = sum(len(v) for v in obs.values())
        layers_used = sorted(k for k, v in flat.items() if not v.is_empty())
        REP.append(f'{cell}: {bnd.width() / 1000:.3f} × {bnd.height() / 1000:.3f} µm ({src}), 핀 {len(pins)}, OBS 사각형 {n_obs}'
                   f' (+ 전체 막음 {list(B.get("full", ())) or "-"}{", met4 keepout " + str(len(keep)) if keep else ""}), 금속 {layers_used},'
                   f' GDS 원점 이동 {(-ox / 1000, -oy / 1000) if (ox or oy) else "없음"}')
        REP += [f'   ! {w}' for w in warn]
        print(REP[-1 - len(warn)])
    (OUT / 'pins_all.json').write_text(json.dumps(ALL, indent=0))
    (OUT / 'lef_report.txt').write_text('\n'.join(REP) + '\n')
    print('\n'.join(r for r in REP if r.startswith('   !')) or '경고 없음')


if __name__ == '__main__':
    main()

"""test pattern 블록 4 개 조립 (10/28) — tp_tl · tp_br · tp_bandl · tp_bandr.
사용자: "test pattern 넣어서 decap이 최대한 없게", "그려만 놓고 pad 연결은 안해놓아도 되지 뭐", "ring 오실레이터는 들어가야하고 … Sheet 저항 보기 위한 것도 넣을까?".
영역 = ../../floorplan_opt_D3.json 의 test 사각형 (블록은 그 안, 줄어도 됨).

블록 모양 (블록 좌표, 원점 = 왼쪽 아래):
  - 위 끝 VDD · 아래 끝 VSS = met3 띠 (블록 전폭, 높이 BAND_H) = 블록 전원 핀.
  - 칸 (column) 마다 구조 셀을 아래→위로 쌓음 (틈 GAP). 신호 핀 = 구조 셀의 met3 패드가 블록 변에 닿은 것 (라벨 = <구조 별칭>_<포트>).
    두 칸 블록: 왼쪽 칸 신호 = 서쪽 변, 오른쪽 칸은 좌우로 뒤집어 신호 = 동쪽 변. 한 칸 블록: SIG_SIDE 변.
  - 가운데 (또는 안쪽) 전원 기둥 = met2 세로 (VSS 칸마다 하나, VDD 하나). 구조 셀의 전원 패드 → met3 가지 → via2 로 기둥.
    VSS 기둥 → 아래 VSS 띠, VDD 기둥 → 위 VDD 띠 (via2). 칸끼리 가지가 엇갈리지 않게 기둥 순서 = [왼 칸] VSS_L · VDD · VSS_R [오른 칸].
낸다: out/tp_*.gds (top = 블록 이름), out/tp_*.cdl (구조 subckt + hvl subckt + 블록 subckt), out/tp_*.json (크기·핀·구조 목록).
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python gen_tp.py [블록 …] [--run]
"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpcommon import OUT, LAY, g, nm, db, run                    # noqa: E402

TP = Path(__file__).resolve().parent
FP = json.load(open(TP.parents[1] / 'floorplan_opt_D3.json'))
AREA = {b['cell'][2:] if b['cell'].startswith('B_') else b['cell']: b['rect'] for b in FP['blocks'] if b['kind'] == 'test'}
BAND_H, GAP, SP_W = 1.6, 2.5, 1.0            # 전원 띠 높이, 구조 사이 틈, 기둥 폭

# 구조 별칭 (핀 이름 앞머리) — 없으면 셀 이름에서 tp_ 를 뗀 것
SHORT = {'tp_1t1r': 'rr', 'tp_nacc': 'nacc', 'tp_pair': 'pair', 'tp_ro': 'ro'}
# 핀 이름 = <별칭>_<블록 안 번호>_<포트>  (예 ro_1_en, rr_2_te, kv_m1_l_1_s1, ch_via1_1_a)

# 블록 구성: 칸마다 (꼭 넣을 구조 목록, 남는 높이를 채울 구조 목록 (돌려 가며)).  'x*' = 이름이 x 로 시작하는 구조 전부.
KV_L = [f'tp_kv_{k}_l' for k in ('hpo0p35', 'hpo1p41', 'xpo0p35', 'xpo1p41', 'nd', 'pd', 'm1', 'm2', 'm3')]
KV_S = [k[:-1] + 's' for k in KV_L]
CH = [f'tp_ch_{k}' for k in ('poly', 'ndiff', 'pdiff', 'mcon', 'via1', 'via2')]
BLOCKS = {
    'tp_tl': dict(cols=[('W', ['tp_ro'] + KV_L + KV_S, CH),
                        ('E', ['tp_1t1r'] * 4 + ['tp_nacc'] * 2 + ['tp_pair'] * 2 + CH, ['tp_1t1r', 'tp_nacc'])]),
    'tp_br': dict(cols=[('W', ['tp_ro'] + KV_S + KV_L, CH),
                        ('E', ['tp_1t1r'] * 4 + ['tp_nacc'] * 2 + ['tp_pair'] * 2 + CH, ['tp_1t1r', 'tp_nacc', 'tp_pair'])]),
    'tp_bandl': dict(cols=[('W', CH + ['tp_1t1r'] * 2 + ['tp_nacc'] * 2, KV_L)]),
    'tp_bandr': dict(cols=[('E', KV_L, CH + ['tp_nacc'])]),
}
MODS = ['s_dev', 's_ro', 's_kelvin', 's_chain']


def load_structs(ly):
    S = {}
    for m in MODS:
        try:
            mod = importlib.import_module(m)
        except ModuleNotFoundError as e:
            print(f'  (아직 없음: {m} — {e})')
            continue
        for s in mod.build(ly):
            s.check()
            assert s.name not in S, s.name
            S[s.name] = s
    return S


def expand(names, S):
    out = []
    for n in names:
        if n.endswith('*'):
            out += sorted(k for k in S if k.startswith(n[:-1]))
        elif n in S:
            out.append(n)
        else:
            print(f'  (건너뜀: {n} 없음)')
    return out


def build_block(ly, S, name, spec):
    x0a, y0a, x1a, y1a = AREA[name]
    WA, HA = x1a - x0a, y1a - y0a
    ncol = len(spec['cols'])
    W = g(min(WA, 88.0 if ncol == 2 else 47.0) - 0.0)
    H = g(HA - 0.1)
    T = ly.create_cell(name)
    L = {k: ly.layer(*v) for k, v in LAY.items()}

    def box(lay, a, b, c, d):
        T.shapes(L[lay]).insert(db.Box(nm(g(min(a, c))), nm(g(min(b, d))), nm(g(max(a, c))), nm(g(max(b, d)))))

    # 칸·기둥 x 범위
    if ncol == 2:
        spines = {'VSS_L': 41.0, 'VDD': 43.0, 'VSS_R': 45.0}       # 기둥 왼쪽 끝
        cols = [dict(side='W', x0=0.0, x1=40.0, vss='VSS_L'), dict(side='E', x0=47.0, x1=W, vss='VSS_R')]
    else:
        side = spec['cols'][0][0]
        if side == 'W':
            spines = {'VSS_L': 43.0, 'VDD': 45.0}
            cols = [dict(side='W', x0=0.0, x1=42.0, vss='VSS_L')]
        else:
            spines = {'VDD': 1.0, 'VSS_R': 3.0}
            cols = [dict(side='E', x0=5.0, x1=W, vss='VSS_R')]
    ytop_free = H - BAND_H - GAP
    placed, count = [], {}
    for col, (side, must, fill) in zip(cols, spec['cols']):
        assert col['side'] == side
        y = BAND_H + GAP
        cw = col['x1'] - col['x0']
        seq = expand(must, S)
        cyc = expand(fill, S)
        k, miss = 0, 0
        while True:
            if seq:
                n = seq.pop(0); forced = True
            elif cyc and miss < len(cyc):
                n = cyc[k % len(cyc)]; k += 1; forced = False
            else:
                break
            s = S[n]
            bx = s.bbox()
            w, h = bx[2], bx[3] - bx[1]
            if w > cw + 1e-6 or y + h > ytop_free + 1e-6:
                assert not forced, (name, n, '꼭 넣을 구조가 안 들어감', w, cw, y + h, ytop_free)
                miss += 1
                continue
            miss = 0
            sh = SHORT.get(n, n[3:])
            count[sh] = count.get(sh, 0) + 1
            pre = f'{sh}_{count[sh]}'
            dy = g(y - bx[1])
            if side == 'W':
                t = db.Trans(0, False, nm(g(col['x0'])), nm(dy))
            else:                                                   # 좌우 뒤집기: x → x1 − x
                t = db.Trans(db.Trans.M90, nm(g(col['x1'])), nm(dy))
            T.insert(db.CellInstArray(s.c.cell_index(), t))
            placed.append(dict(s=s, pre=pre, t=t, col=col, y0=g(y), y1=g(y + h)))
            y = g(y + h + GAP)
    # 핀 라벨·전원 가지
    pins, power, body, used_s = {}, {'VDD': [], 'VSS': []}, [], []
    dt = lambda t, b: db.DBox(*b).transformed(db.DCplxTrans(t.to_dtype(ly.dbu)))
    for p in placed:
        s, t, col = p['s'], p['t'], p['col']
        conn = []
        for port in s.ports:
            if port in ('VDD', 'VSS'):
                conn.append(port)
                sp = spines[col['vss']] if port == 'VSS' else spines['VDD']
                xc = sp + SP_W / 2
                for b in s.pins[port]['boxes']:
                    bb = dt(t, b)
                    yc = g((bb.bottom + bb.top) / 2)
                    xe = bb.right if col['side'] == 'W' else bb.left        # 패드의 기둥 쪽 끝
                    box('met3', xe + (-0.5 if col['side'] == 'W' else 0.5), yc - 0.25, xc + (0.4 if col['side'] == 'W' else -0.4), yc + 0.25)
                    for dx in (-0.2, 0.2):
                        box('via2', xc + dx - 0.1, yc - 0.1, xc + dx + 0.1, yc + 0.1)
                    power[port].append([round(bb.left, 3), round(bb.bottom, 3), round(bb.right, 3), round(bb.top, 3)])
            else:
                pn = f"{p['pre']}_{port}"
                assert pn not in pins, pn
                bb = dt(t, s.pins[port]['box'])
                T.shapes(L['lbl_met3']).insert(db.Text(pn, db.Trans(nm(g(bb.center().x)), nm(g(bb.center().y)))))
                edge = 'W' if col['side'] == 'W' else 'E'
                assert (abs(bb.left) < 1e-6) if edge == 'W' else (abs(bb.right - W) < 1e-6), (pn, bb, W)
                pins[pn] = dict(layer='met3', side=edge, box=[round(bb.left, 3), round(bb.bottom, 3), round(bb.right, 3), round(bb.top, 3)],
                                struct=s.name, port=port)
                conn.append(pn)
        body.append(f"X{p['pre']} " + ' '.join(conn) + f' {s.name}')
        if s not in used_s:
            used_s.append(s)
    # 전원 기둥 (met2) + 띠 (met3)
    yb1, yt0 = BAND_H, H - BAND_H
    box('met3', 0.0, 0.0, W, yb1); box('met3', 0.0, yt0, W, H)
    for k, x in spines.items():
        if k == 'VDD':
            box('met2', x, yb1 + 0.6, x + SP_W, H - 0.2); yv = H - BAND_H / 2
        else:
            box('met2', x, 0.2, x + SP_W, yt0 - 0.6); yv = BAND_H / 2
        for dx in (-0.2, 0.2):
            for dy in (-0.4, 0.0, 0.4):
                xc = x + SP_W / 2
                box('via2', xc + dx - 0.1, yv + dy - 0.1, xc + dx + 0.1, yv + dy + 0.1)
    T.shapes(L['lbl_met3']).insert(db.Text('VSS', db.Trans(nm(g(W / 2)), nm(g(BAND_H / 2)))))
    T.shapes(L['lbl_met3']).insert(db.Text('VDD', db.Trans(nm(g(W / 2)), nm(g(H - BAND_H / 2)))))
    bb = T.dbbox()
    assert bb.left > -1e-6 and bb.bottom > -1e-6 and bb.right < W + 1e-6 and bb.top < H + 1e-6, (name, bb, W, H)
    assert W <= WA + 1e-6 and H <= HA + 1e-6
    # 파일
    so = db.SaveLayoutOptions(); so.add_cell(T.cell_index())
    ly.write(str(OUT / f'{name}.gds'), so)
    ports = list(pins) + ['VDD', 'VSS']
    extra = []
    for s in used_s:
        for e in s.extra:
            if e not in extra:
                extra.append(e)
    lines = [f'* {name} — test pattern 블록 (testpat/gen_tp.py, 10/28). 패드 연결 없음, 핀 = 블록 변 met3.'] + extra
    for s in used_s:
        lines += s.subckt()
    lines += ['', f'.subckt {name} ' + ' '.join(ports)] + body + [f'.ends {name}']
    (OUT / f'{name}.cdl').write_text('\n'.join(lines) + '\n')
    info = dict(cell=name, w=W, h=H, d3_rect=AREA[name], d3_size=[round(WA, 3), round(HA, 3)],
                origin_note='블록 좌표 원점 = 왼쪽 아래. D3 사각형 왼쪽 아래에 놓으면 들어감 (w ≤ D3 폭, h ≤ D3 높이)',
                power=dict(VDD=dict(layer='met3', box=[0.0, round(yt0, 3), W, H], note='위 끝 띠'),
                           VSS=dict(layer='met3', box=[0.0, 0.0, W, round(yb1, 3)], note='아래 끝 띠')),
                pins=pins, cdl_ports=ports, lvs_deck='signoff/sky130_chip.lvs.pvl (= testpat/sky130_tp.lvs.pvl 와 주석만 다름)',
                structures=[dict(inst='X' + p['pre'], cell=p['s'].name, prefix=p['pre'], mirrored=p['col']['side'] == 'E',
                                 y0=p['y0'], y1=p['y1'], contents=p['s'].contents, source=p['s'].source) for p in placed],
                metals='met1–met3 (met4·met5 없음)')
    json.dump(info, open(OUT / f'{name}.json', 'w'), indent=1, ensure_ascii=False)
    print(f'{name}: {W} × {H} µm (D3 {WA:.2f} × {HA:.2f}), 구조 {len(placed)}, 신호 핀 {len(pins)}')
    return info


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ly = db.Layout(); ly.dbu = 0.001
    S = load_structs(ly)
    names = args or list(BLOCKS)
    for n in names:
        build_block(ly, S, n, BLOCKS[n])
    if '--run' in sys.argv:
        for n in names:
            run(n)

"""입력 구동 블록 생성기 (10/28) — 배열 반쪽마다 하나. netlist 기준 = real_circuit/gen_chip_deck3.py "입력 구동 레일" 줄:
  입력 i (49) 마다 행 x+ (= 2i) · x− (= 2i+1), 행마다 NMOS 둘: Dp (행 ↔ vrailp, 게이트 x+ 는 ga_i / x− 는 gb_i), Dm (행 ↔ vrailm, x+ 는 gb_i / x− 는 ga_i),
  bias 행 98 (vrailp)·99 (vrailm) 은 NMOS 하나 (게이트 READ). 모두 nfet_g5v0d10v5 W 1000 L 0.5, body vss → 198 개.
  행 번호 = train.LAY_NS (r_x 0–97, r_b 98–99). 출력 핀 y = 배열 생성기 (gen_arr_1t1r_w3.py) 의 행 띠 가운데 r·3.41 − 0.46 µm (배열과 같은 y 원점).

구조 (정수 nm):
  층(tier) 20 개, 층마다 행 5 개 = 소자 10 개 (가로로 나란히, 소자 = 핑거 50 × 20 µm, 핑거 피치 0.79 = devlib 와 같은 규칙).
  netlist 는 nf 200 (핑거 5 µm) — 핑거 수만 다르고 W·L 같음 (LVS 는 병렬 핑거를 합쳐 W 1000 으로 비교).
  S/D 줄 (met1 세로) 위로 바로 via1·via2 → met3 가로 띠: 층마다 vrailp 띠 3.0 µm · 행 띠 5 개 1.95 µm · vrailm 띠 3.0 µm · 게이트선 6 개 0.34 µm.
  source 줄 → 자기 레일 띠, drain 줄 → 자기 행 띠, 게이트 = poly 막대 → li1 → met1 → via1 → met2 짧은 세로 → via2 → met3 게이트선.
  층 사이 p-tap 띠 (li1, 왼쪽 met1 VSS 줄기로). 왼쪽: met3 줄기 vrailm·vrailp (6 µm), 게이트선·vrailm 띠는 met2 로 줄기 밑을 지남.
  오른쪽 fan: 층 안 행 띠 (피치 ≈ 4.34 µm) → 배열 피치 3.41 µm. 행마다 세로 met2+met1 (1 µm) 한 줄, 같은 줄은 겹치지 않는 행끼리 나눠 씀.
  출력 핀 = 오른쪽 끝 met2 (배열 행 띠와 같은 y 범위 r·3.41 − 0.67 … − 0.25).
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python gen_input_drive.py      (NT=2 → 시험판 input_drive_t2, 행 10 개)
낸다: out/<NAME>.gds · .cdl · .json (핀 좌표 µm, 행 경로 저항 어림)
"""
import json
import os
import time
from pathlib import Path

import klayout.db as db

from blk_common import Blk, finish_hvi, netcheck, precheck, via_cells, write_pins_json

H = Path(__file__).resolve().parent
NT = int(os.environ.get('NT', '20'))
NAME = os.environ.get('NAME', 'input_drive' if NT == 20 else f'input_drive_t{NT}')
NROW = min(100, 5 * NT)
BIAS = NROW == 100                                                   # 행 98·99 = bias (READ)

# ── 소자 (core 셀 좌표, diff 왼쪽 아래 = 0)
P, SDW, LG, NF, WF = 790, 290, 500, 50, 20000
DW = NF * P + SDW                                                     # 39 790
GY = WF + 400                                                         # 게이트 poly 막대 가운데 (poly licon–diff 0.315 ≥ 0.19)
# ── 층 (tier 좌표, tap 가운데 = 0)
T, Y0 = 21700, -1600
YD = 650                                                              # diff 아래 (ndiff–ptap 0.40 ≥ 0.37)
STRIP = dict(rp=(150, 3150), r0=(3450, 5400), r1=(5700, 7650), r2=(7950, 9900), rm=(10200, 13200), r3=(13500, 15450), r4=(15750, 17700))
GSLOT = [(18000 + 640 * m, 18340 + 640 * m) for m in range(6)]
VIA_RAIL = dict(p=(1000, 700, 3), m=(10900, 800, 3))                 # (첫 y, 간격, 개수) — 레일 띠 위 비아 쌓기
DGAP = 400
DPITCH = DW + DGAP
# ── 왼쪽 (x)
X_VSS = (500, 1500)
X_J = (1900, 2500)                                                    # 두 층에 걸친 입력의 게이트 이음 (met1 세로)
X_VM = (3000, 9000)
X_VP = (9500, 15500)                                                  # huge met3 (> 3 µm) 끼리 간격 0.40 → 0.50
X_M3L = 16000                                                         # vrailm 띠 met3 시작 (줄기와 0.50)
X_G3 = 16300                                                          # 게이트선 met3 시작 (줄기 옆 vrailp 띠 모서리와 huge 간격 0.40, 10/28 첫 판 m3.3c)
X_UP = 16500                                                          # 게이트 met2 → met3 비아
X_RMV = (16200, 16600)                                                # vrailm 띠 via2 (met3 띠 → met2 밑길)
XD0 = 17200
# ── 오른쪽 fan
WJ, PL = 1000, 1300
ROWP, ROWC = 3410, -460                                               # 배열 행 띠 가운데 = r·3.41 − 0.46 µm
WE = 1000                                                             # 나가는 met3 선 폭 (1.95 면 들어오는 선과 겹치는 짝이 늘어 fan 줄 38 개, 1.0 이면 25 개)
RS = dict(m1=0.125, m2=0.125, m3=0.047)                               # Ω/sq (SKY130 대표값, 어림)


def tier_rows(t):
    return [r for r in range(5 * t, 5 * t + 5) if r < NROW]


def devices_of(t):
    """층 t 의 소자 목록 (왼쪽부터): dict(name, row, pol, gate, slot)."""
    out = []
    for r in tier_rows(t):
        j = r - 5 * t
        if BIAS and r >= 98:
            out.append(dict(name=f'Db{r}', row=r, pol='p' if r == 98 else 'm', gate='READ', slot=j))
            continue
        i, xp = r // 2, r % 2 == 0
        out.append(dict(name=f'Dp{r}', row=r, pol='p', gate=f'ga{i}' if xp else f'gb{i}', slot=j))
        out.append(dict(name=f'Dm{r}', row=r, pol='m', gate=f'gb{i}' if xp else f'ga{i}', slot=j))
    return out


def build():
    t0 = time.time()
    ly = db.Layout(); ly.dbu = 0.001
    B = Blk(ly, NAME)
    V = via_cells(B)
    # ── core 셀 (diff·poly·S/D 줄·게이트 막대) — 198 개 모두 같은 셀
    core = ly.create_cell('nsw_w1000_f50')
    cb = lambda lay, *a: B.box(lay, *a, cell=core)
    cb('diff', 0, 0, DW, WF)
    nct = (WF - 290) // 360 + 1
    y00 = 145 + ((WF - 290) - (nct - 1) * 360) // 2
    for k in range(NF + 1):
        xc = 145 + k * P
        cb('li1', xc - 85, -20, xc + 85, WF + 20)
        cb('m1', xc - 115, 0, xc + 115, WF)
        for t in range(nct):
            yc = y00 + t * 360
            cb('licon', xc - 85, yc - 85, xc + 85, yc + 85); cb('mcon', xc - 85, yc - 85, xc + 85, yc + 85)
    gxs = [540 + k * P for k in range(NF)]
    for gx in gxs:
        cb('poly', gx - 250, -200, gx + 250, GY)
        cb('licon', gx - 85, GY - 85, gx + 85, GY + 85)
    cb('poly', gxs[0] - 250, GY - 180, gxs[-1] + 250, GY + 180)
    cb('npc', gxs[0] - 185, GY - 185, gxs[-1] + 185, GY + 185)
    cb('li1', gxs[0] - 250, GY - 180, gxs[-1] + 250, GY + 180)
    # 게이트 패드 (첫 핑거 위): mcon + v12
    cb('mcon', gxs[0] - 85, GY - 85, gxs[0] + 85, GY + 85)
    core.insert(db.CellInstArray(V['v12'].cell_index(), db.Trans(gxs[0], GY)))
    XG = gxs[0]

    ndev_max = max(len(devices_of(t)) for t in range(NT))
    XD_END = XD0 + (ndev_max - 1) * DPITCH + DW
    X_F0 = XD_END + 700
    yB = lambda t: Y0 + t * T
    gate_lines = {}                                                   # net → [(tier, slot y 범위, 가장 오른쪽 x)]
    row_in = {}                                                       # 행 → (met3 띠 y0, y1, 시작 x)
    devs_all = []
    for t in range(NT):
        b = yB(t)
        dv = devices_of(t)
        nets = []
        for d in dv:
            if d['gate'] not in nets:
                nets.append(d['gate'])
        assert len(nets) <= len(GSLOT), (t, nets)
        x_last = XD0 + (len(dv) - 1) * DPITCH + DW
        B.box('nsd', XD0 - 125, b + YD - 125, x_last + 125, b + YD + WF + 125)
        for i, d in enumerate(dv):
            x0 = XD0 + i * DPITCH; y0 = b + YD
            B.inst(core, x0, y0)
            fy, dy, n = VIA_RAIL[d['pol']]
            B.inst(V['v123'], x0 + 145, b + fy, nx=NF // 2 + 1, ny=n, dx=2 * P, dy=dy)       # source 줄 → 레일 띠
            a, c = STRIP[f"r{d['slot']}"]
            B.inst(V['v123'], x0 + 145 + P, b + (a + c) // 2 - 400, nx=NF // 2, ny=2, dx=2 * P, dy=800)   # drain 줄 → 행 띠
            m = nets.index(d['gate']); ga, gc = GSLOT[m]; yg = b + (ga + gc) // 2
            xg = x0 + XG
            B.box('m2', xg - 150, min(yg, y0 + GY), xg + 150, max(yg, y0 + GY))              # 게이트 세로 met2
            B.inst(V['v2'], xg, yg)
            gate_lines.setdefault(d['gate'], {}).setdefault(t, [m, 0])
            gate_lines[d['gate']][t][1] = max(gate_lines[d['gate']][t][1], xg)
            if d['row'] not in row_in:
                row_in[d['row']] = (b + a, b + c, x0)
            devs_all.append(dict(d, tier=t, x=x0, y=y0))
        # 레일 띠
        B.box('m3', X_VP[0], b + STRIP['rp'][0], XD_END + 200, b + STRIP['rp'][1])         # 끝 source via2 를 0.065 이상 감쌈
        B.box('m3', X_M3L, b + STRIP['rm'][0], XD_END + 200, b + STRIP['rm'][1])
        B.box('m2', X_VM[0], b + STRIP['rm'][0], X_RMV[1] + 200, b + STRIP['rm'][1])          # vrailm 밑길
        ys = list(range(b + STRIP['rm'][0] + 300, b + STRIP['rm'][1] - 299, 400))
        for x in list(range(X_VM[0] + 300, X_VM[1] - 299, 400)) + list(X_RMV):
            for y in ys:
                B.sq('via2', x, y, 200)
    # ── tap 띠 (층 경계마다, li1 만) + 왼쪽 VSS 줄기 (met1)
    XT0, XT1 = 400, XD_END + 300
    for t in range(NT + 1):
        b = yB(t)
        B.box('tap', XT0, b - 250, XT1, b + 250); B.box('psd', XT0 - 125, b - 375, XT1 + 125, b + 375)
        B.box('li1', XT0, b - 250, XT1, b + 250)
        for x in range(XT0 + 300, XT1 - 299, 1000):
            B.sq('licon', x, b, 170)
        for x in (750, 1250):
            B.sq('mcon', x, b, 170)
    B.box('m1', X_VSS[0], yB(0) - 250, X_VSS[1], yB(NT) + 250)
    vss_pin = (X_VSS[0], yB(0) + 1200, X_VSS[1], yB(0) + 1800)
    B.box('m2', *vss_pin)
    for x in (750, 1250):
        B.sq('via', x, yB(0) + 1500, 150)
    B.text('lbl_m2', 'vss', 1000, yB(0) + 1500)
    # ── 레일 줄기 (met3)
    ytop = yB(NT) + 250
    B.box('m3', X_VM[0], yB(0) - 250, X_VM[1], ytop)
    B.box('m3', X_VP[0], yB(0) - 250, X_VP[1], ytop)
    B.text('lbl_m3', 'vrailm', (X_VM[0] + X_VM[1]) // 2, ytop - 1000)
    B.text('lbl_m3', 'vrailp', (X_VP[0] + X_VP[1]) // 2, ytop - 1000)
    # ── 게이트선: met3 (줄기 오른쪽 → 소자), met2 밑길 (왼쪽 끝 핀 → X_UP), 두 층에 걸치면 met1 이음
    pins = {}
    jl = 0
    for net, tiers in gate_lines.items():
        ts = sorted(tiers)
        assert len(ts) <= 2 and (len(ts) == 1 or ts[1] == ts[0] + 1), (net, ts)
        ycs = []
        for k, t in enumerate(ts):
            m, xr = tiers[t]; ga, gc = GSLOT[m]; b = yB(t)
            yc = b + (ga + gc) // 2; ycs.append(yc)
            B.box('m3', X_G3, b + ga, xr + 300, b + gc)
            xl = 0 if k == 0 else X_J[jl] - 200
            B.box('m2', xl, b + ga, X_UP + 185, b + gc)
            B.inst(V['v2'], X_UP, yc)
        if len(ts) == 2:
            xj = X_J[jl]
            B.box('m1', xj - 150, ycs[0] - 165, xj + 150, ycs[1] + 165)
            B.inst(V['v12'], xj, ycs[0]); B.inst(V['v12'], xj, ycs[1])
            jl = 1 - jl
        b = yB(ts[0]); ga, gc = GSLOT[tiers[ts[0]][0]]
        B.text('lbl_m2', net, 200, b + (ga + gc) // 2)
        pins[net] = [('met2', 0, b + ga, 400, b + gc)]
    # ── fan: 행 띠 (y_in) → 배열 피치 (y_out)
    yin = {r: (v[0] + v[1]) // 2 for r, v in row_in.items()}
    yout = {r: r * ROWP + ROWC for r in row_in}
    lane, occ = {}, {}
    for r in sorted(row_in):
        lb = max([lane[k] + 1 for k in lane if abs(yin[k] - yout[r]) < WE // 2 + 975 + 300] + [0])
        lo, hi = min(yin[r], yout[r]) - 750, max(yin[r], yout[r]) + 750
        ell = lb
        while any(not (hi < a or lo > c) for a, c in occ.get(ell, [])):
            ell += 1
        lane[r] = ell; occ.setdefault(ell, []).append((lo, hi))
    nl = max(lane.values()) + 1
    xl = lambda ell: X_F0 + WJ // 2 + ell * PL
    X_E = xl(nl - 1) + WJ // 2 + 1700
    rpath = {}
    for r in sorted(row_in):
        y0_, y1_, xs = row_in[r]
        xc = xl(lane[r])
        B.box('m3', xs, y0_, xc + WJ // 2, y1_)                                             # 행 띠 (소자 → 줄)
        lo, hi = min(yin[r], yout[r]), max(yin[r], yout[r])
        for lay in ('m1', 'm2'):
            B.box(lay, xc - WJ // 2, lo - 600, xc + WJ // 2, hi + 600)
        for y in range(lo - 400, hi + 401, 600):
            for dx in (-250, 250):
                B.sq('via', xc + dx, y, 150)
        v2y = []
        for y in sorted((yin[r] - 400, yin[r] + 400, yout[r] - 200, yout[r] + 200)):   # 나가는 선 1.0 µm → via2 는 ±0.2   # 겹치는 via2 는 하나만 (10/28 첫 판 via2.1a)
            if not v2y or y - v2y[-1] >= 400:
                v2y.append(y)
        for y in v2y:
            for dx in (-250, 250):
                B.sq('via2', xc + dx, y, 200)
        yo = yout[r]
        B.box('m3', xc - WJ // 2, yo - WE // 2, X_E, yo + WE // 2)                          # 나가는 선
        if hi - lo - 975 - WE // 2 < 600:                                                   # 들어오는·나가는 선 틈이 좁으면 줄 위에서 met3 로 메움 (같은 넷 간격 0.30)
            B.box('m3', xc - WJ // 2, lo - 975, xc + WJ // 2, hi + 975)
        B.box('m2', X_E - 1400, yo - 210, X_E, yo + 210)                                    # 핀 (배열 행 띠와 같은 y)
        for x in (X_E - 1100, X_E - 500):
            B.sq('via2', x, yo, 200)
        B.text('lbl_m2', f'row_{r}', X_E - 200, yo)
        pins[f'row_{r}'] = [('met2', X_E - 1400, yo - 210, X_E, yo + 210)]
        # 경로 저항 어림: 소자 오른쪽 끝 → 줄 (met3 1.95) + 세로 (met1‖met2 1.0) + 나가는 선 (met3 1.0)
        dvx = max(d['x'] for d in devs_all if d['row'] == r) + DW
        r3a = (xc - dvx) / 1950 * RS['m3']; rj = (hi - lo) / WJ * (RS['m2'] / 2); r3b = (X_E - xc) / WE * RS['m3']
        rpath[r] = round(r3a + rj + r3b, 2)
    pins['vrailp'] = [('met3', X_VP[0], ytop - 5000, X_VP[1], ytop)]
    pins['vrailm'] = [('met3', X_VM[0], ytop - 5000, X_VM[1], ytop)]
    pins['vss'] = [('met2',) + vss_pin]
    bb = finish_hvi(B)
    # ── CDL (기준 = SPICE 덱 소자, W 1000 L 0.5 한 개씩; 핑거는 LVS 가 합침)
    rows = sorted(row_in)
    gnets = sorted({d['gate'] for d in devs_all if d['gate'] != 'READ'}, key=lambda s: (s[:2], int(s[2:])))
    ports = [f'row_{r}' for r in rows] + gnets + (['READ'] if BIAS else []) + ['vrailp', 'vrailm', 'vss']
    cdl = [f".subckt {NAME} " + ' '.join(ports)]
    for d in sorted(devs_all, key=lambda d: (d['row'], d['name'])):
        cdl.append(f"M{d['name']} row_{d['row']} {d['gate']} vrail{d['pol']} vss nfet_g5v0d10v5 w=1000u l=0.5u")
    cdl.append(f".ends {NAME}")
    out = H / 'out'; out.mkdir(exist_ok=True)
    so = db.SaveLayoutOptions(); so.add_cell(B.c.cell_index())
    ly.write(str(out / f'{NAME}.gds'), so)
    (out / f'{NAME}.cdl').write_text('\n'.join(cdl) + '\n')
    tb = time.time() - t0
    pc = precheck(ly, B.c)
    nc = netcheck(ly, B.c)
    info = dict(devices=len(devs_all), tiers=NT, lanes=nl, fan_um=round((X_E - X_F0) / 1000, 2), device_region_um=[XD0 / 1000, XD_END / 1000],
                row_pitch_um=ROWP / 1000, row_center_um='r*3.41-0.46 (gen_arr_1t1r_w3 행 띠 가운데와 같은 y)',
                row_path_ohm=dict(min=min(rpath.values()), max=max(rpath.values()), mean=round(sum(rpath.values()) / len(rpath), 2)),
                rail_trunk_ohm=round((ytop - yB(0)) / 6000 * RS['m3'], 2),
                precheck=pc, netcheck=dict(nc, shorts=nc['shorts'][:10], opens=nc['opens'][:10]), build_s=round(tb, 1))
    write_pins_json(out / f'{NAME}.json', NAME, (bb.left, bb.bottom, bb.right, bb.top), pins, dict(info=info))
    print(f"{NAME}: {len(devs_all)} 소자, {(bb.right - bb.left) / 1000:.2f} × {(bb.top - bb.bottom) / 1000:.2f} µm, 층 {NT}, fan 줄 {nl} "
          f"({(X_E - X_F0) / 1000:.1f} µm), 행 경로 {info['row_path_ohm']} Ω, 생성 {tb:.1f} s")
    print('precheck', pc)
    print('netcheck', info['netcheck'])


if __name__ == '__main__':
    build()

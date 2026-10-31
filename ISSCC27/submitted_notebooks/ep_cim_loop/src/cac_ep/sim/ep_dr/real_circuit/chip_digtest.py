"""chip_lib.py (v2) 디지털 부품 단독 시험 (10/25): DFFR 8 단 시프트 + DLATCH, ROWL·COLL decoder 진리표 (동작 6 가지 × 선택 / 비선택),
쓰기 펄스 buffer WBUF (SET: 0 → +1.8 V, RESET: 0 → −1.8 V). 디지털 전원 ±2.5 V (VSS–VDD).
쓰임: python chip_digtest.py write → decks/digtest2.sp   /   python chip_digtest.py check (out/digtest2.lis 를 읽음)
"""
import re
import sys
from pathlib import Path

from chip_lib import global_decode, lib
from wu_lib import primitives

HERE = Path(__file__).resolve().parent
OLY = '/home/grads/s/seokjindaveoh/work'
TC = 10e-9                                   # 클록 주기, 올라가는 모서리 = 칸 시작 + 5 ns
BITS = [1, 0, 1, 1, 0, 0, 1, 0]              # 먼저 넣은 bit 가 끝 (q7) 으로 간다
MODES = [  # (이름, m1, m0, pv, wu_en)
    ('IDLE', 0, 0, 0, 0), ('READ+sense', 1, 1, 0, 1), ('FORM', 0, 1, 0, 0), ('WRITE prog', 1, 0, 0, 0), ('WRITE verify', 1, 0, 1, 0)]
T0M, TM = 200e-9, 20e-9                      # 동작 시험 시작, 동작마다 20 ns
ROW_OUT = ['wsel', 'wz', 'sns', 'wlv', 'wlw', 'wl0']
COL_OUT = ['wvw', 'wz', 'vfy', 'sns1', 'sns2']
T0B = T0M + len(MODES) * TM + 10e-9          # buffer 시험: SET 칸, RESET 칸 (각 40 ns, 펄스 10 ns)
HI, LO = 2.5, -2.5


def expect(m1, m0, pv, wu, s, s2=0):
    READ, WR, FORM = m1 and m0, m1 and not m0, (not m1) and m0
    PROG, VER, SENSE = FORM or (WR and not pv), WR and pv, READ and wu
    row = dict(wsel=(PROG or VER) and s, wz=(PROG or VER) and not s, sns=SENSE and s, wlv=READ or (VER and s), wlw=PROG and s)
    row['wl0'] = not (row['wlv'] or row['wlw'])
    col = dict(wvw=(PROG or VER) and not s, wz=PROG and s, vfy=VER and s, sns1=SENSE and s, sns2=SENSE and s2)
    return {k: int(bool(v)) for k, v in row.items()}, {k: int(bool(v)) for k, v in col.items()}


def pwl(pts):
    return "PWL(" + " ".join(f"{t:.4e} {v:g}" for t, v in pts) + ")"


def step(times_vals, hi=HI, lo=LO):
    pts = [(0.0, lo)]
    for t, b in times_vals:
        pts += [(t, pts[-1][1]), (t + 0.2e-9, hi if b else lo)]
    return pts


if sys.argv[1] == 'write':
    L = ['* digtest2: chip_lib v2 DFFR·DLATCH·ROWL·COLL·WBUF 단독 시험 (디지털 ±2.5 V)', '.option post=0 ingold=2 numdgt=8 measdgt=8',
         '.temp 25', f".lib '{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice' tt", 'Vdd vdd 0 2.5', 'Vss vss 0 -2.5']
    L += primitives() + lib()
    L += [f"Vrst rst 0 {pwl(step([(2e-9, 1), (12e-9, 0)]))}"]
    d = [(20e-9 + j * TC, BITS[j]) for j in range(len(BITS))]
    ck = []
    for j in range(len(BITS)):
        t = 20e-9 + j * TC
        ck += [(t + 5e-9, 1), (t + 8e-9, 0)]
    L += [f"Vd din 0 {pwl(step(d))}", f"Vck clk 0 {pwl(step(ck))}"]
    tl = 20e-9 + len(BITS) * TC + 5e-9
    L += [f"Vld ld 0 {pwl(step([(tl, 1), (tl + 8e-9, 0)]))}", "XIld ld ldb vdd vss INV"]
    prev = 'din'
    for k in range(len(BITS)):
        L += [f"XF{k} {prev} clk rst rstb q{k} vdd vss DFFR", f"XL{k} q{k} ld ldb dl{k} dlb{k} vdd vss DLATCH"]
        prev = f'q{k}'
    tq = tl + 20e-9
    L += [f".meas tran q{k} find v(q{k}) at={tq:.4e}" for k in range(len(BITS))]
    L += [f".meas tran dl{k} find v(dl{k}) at={tq:.4e}" for k in range(len(BITS))]
    L += [".meas tran q0rst find v(q0) at=15e-9"]
    sig = {n: [] for n in ('m1', 'm0', 'pv', 'wu_en')}
    for i, (_, *v) in enumerate(MODES):
        for n, b in zip(sig, v):
            sig[n].append((T0M + i * TM, b))
    L += [f"V{n} {n} 0 {pwl(step(v))}" for n, v in sig.items()]
    L += [f"Vsel sel_en 0 {HI}", f"Vt1 tone 0 {HI}", f"Vt0 tzero 0 {LO}"] + global_decode()
    for tag, t in (('a', 'tone'), ('b', 'tzero')):
        L.append(f"XR{tag} {t} sel_en PROG VER SENSE READb WRANY " + ' '.join(f'r{tag}{o} r{tag}{o}b' for o in ROW_OUT) + " vdd vss ROWL")
        L.append(f"XC{tag} {t} {t} sel_en PROG VER SENSE WRANY " + ' '.join(f'c{tag}{o} c{tag}{o}b' for o in COL_OUT) + " vdd vss COLL")
    for i in range(len(MODES)):
        tm = T0M + i * TM + 15e-9
        for tag in 'ab':
            L += [f".meas tran r{tag}{o}_{i} find v(r{tag}{o}) at={tm:.4e}" for o in ROW_OUT]
            L += [f".meas tran c{tag}{o}_{i} find v(c{tag}{o}) at={tm:.4e}" for o in COL_OUT]
    # ── 쓰기 펄스 buffer: SET 칸 (pol 0, vwh +1.8, vwl 0), RESET 칸 (pol 1, vwh 0, vwl −1.8), 2 pF 부하
    ts, tr = T0B, T0B + 40e-9
    L += [f"Vwp wp 0 {pwl(step([(ts + 15e-9, 1), (ts + 25e-9, 0), (tr + 15e-9, 1), (tr + 25e-9, 0)]))}",
          f"Vpol pol 0 {pwl(step([(tr, 1)]))}",
          f"Vvwh vwh 0 {pwl([(0, 1.8), (tr - 1e-9, 1.8), (tr, 0)])}", f"Vvwl vwl 0 {pwl([(0, 0), (tr - 1e-9, 0), (tr, -1.8)])}",
          "XWB wp pol vwbus vwh vwl vdd vss WBUF", "Cvw vwbus 0 2p", "Rvw vwbus 0 10k"]
    L += [f".meas tran b_set_idle find v(vwbus) at={ts + 10e-9:.4e}", f".meas tran b_set_on find v(vwbus) at={ts + 22e-9:.4e}",
          f".meas tran b_rst_idle find v(vwbus) at={tr + 10e-9:.4e}", f".meas tran b_rst_on find v(vwbus) at={tr + 22e-9:.4e}",
          f".meas tran b_rise trig v(vwbus) val=0.18 rise=1 td={ts:.4e} targ v(vwbus) val=1.62 rise=1 td={ts:.4e}"]
    L += [f".tran 0.05n {tr + 40e-9:.4e}", '.end']
    (HERE / 'decks').mkdir(exist_ok=True)
    (HERE / 'decks' / 'digtest2.sp').write_text('\n'.join(L) + '\n')
    print('decks/digtest2.sp', len(L), '줄')
else:
    M = {k.lower(): float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*([-+]?[0-9.]+(?:[eE][-+]?\d+)?)', (HERE / 'out' / 'digtest2.lis').read_text(), re.M)}
    want = BITS[::-1]
    q = [int(M[f'q{k}'] > 0) for k in range(len(BITS))]; dl = [int(M[f'dl{k}'] > 0) for k in range(len(BITS))]
    print(f"reset 중 q0 = {M['q0rst']:.3f} V (−2.5 이어야), 시프트 q = {q} (기대 {want}), latch = {dl}", 'OK' if q == want == dl else '틀림')
    bad = 0
    for i, (nm, *v) in enumerate(MODES):
        for tag, s in (('a', 1), ('b', 0)):
            er, ec = expect(*v, s, s)
            gr = {o: int(M[f'r{tag}{o}_{i}'.lower()] > 0) for o in ROW_OUT}
            gc = {o: int(M[f'c{tag}{o}_{i}'.lower()] > 0) for o in COL_OUT}
            ok = gr == er and gc == ec
            bad += not ok
            print(f"  {nm:13s} {'선택' if s else '비선택'}: 행 " + ' '.join(f"{o}={gr[o]}" for o in ROW_OUT)
                  + " | 열 " + ' '.join(f"{o}={gc[o]}" for o in COL_OUT) + ('' if ok else f'  ← 기대 행 {er} 열 {ec}'))
    print('decoder 진리표', '모두 맞음' if not bad else f'{bad} 칸 틀림')
    print(f"쓰기 buffer (2 pF): SET 쉴 때 {M['b_set_idle']:+.3f} V, 펄스 {M['b_set_on']:+.3f} V (상승 10→90 % {M.get('b_rise', float('nan'))*1e9:.2f} ns) | "
          f"RESET 쉴 때 {M['b_rst_idle']:+.3f} V, 펄스 {M['b_rst_on']:+.3f} V")

"""chip_lib v3 (10/26 핀 줄이기) 단독 시험: 설정 레지스터 12 bit (SLD·SCK·SDI) + 레지스터 다섯 개가 SCK·SDI 공유 (TSEL) + β 미러.
① 설정 A (TSEL 다섯 개 모두) → SDI 1,0,1 을 밀면 다섯 레지스터가 같이 [1,0,1,0] (q0 = 마지막 bit)
② 설정 B (TSEL = ROW1·COL2, 나머지 bit 는 무늬) — 미는 동안 설정 출력은 A 그대로, SLD 가 내려가면 B, 레지스터는 그대로
③ SDI 1,1 을 밀면 ROW1·COL2 만 [1,1,1,0], 나머지 셋은 [1,0,1,0]
④ β 미러 DC: HOG bias (5 µA) 단위 소자 m=8 (beta_size.py 로 고른 폭) → 주입기 (MP·MN, 출력 0 V) 전류를 Python β 38.12 µA 와 비교
레지스터 길이는 전체 칩과 같게 (DATA 52, ROW1 100, ROW2 6, COL 60) — 클록 부하를 같게. nobuf = 클록 buffer 없는 판 (chip_write2 첫 판 원인 확인).
쓰임: python chip_digtest3.py write [nobuf] → decks/digtest3[_nobuf].sp   /   python chip_digtest3.py check [nobuf]
"""
import re
import sys
from pathlib import Path

from chip_lib import CFG, NF, PF, REGS, beta_mirror, config_block, global_decode, lib
from wu_lib import primitives

HERE = Path(__file__).resolve().parent
OLY = '/home/grads/s/seokjindaveoh/work'
TC, NQ, BETA = 10e-9, 4, 3.812e-05
NLEN = dict(data=52, row1=100, row2=6, col1=60, col2=60)   # 전체 칩과 같은 길이 (부하), 앞 NQ 개만 본다
BUF = 'nobuf' not in sys.argv
DECK = 'digtest3' + ('' if BUF else '_nobuf')
CFG_A = dict(ts_data=1, ts_row1=1, ts_row2=1, ts_col1=1, ts_col2=1)
CFG_B = dict(m1=1, pv=1, pol=1, rd_out=1, dload=1, ts_row1=1, ts_col2=1)
wv = {}


def put(nm, t0, v):
    s_ = wv.setdefault(nm, [(0.0, 0)])
    if s_[-1][1] != v:
        s_ += [(t0, s_[-1][1]), (t0 + 0.2e-9, v)]


def shift(t0, bits):
    for j, b in enumerate(bits):
        put('sdi', t0 + j * TC, b); put('sck', t0 + j * TC + TC / 2, 1); put('sck', t0 + j * TC + 0.8 * TC, 0)
    t1 = t0 + len(bits) * TC
    put('sdi', t1, 0)
    return t1


def cfg_write(t0, d):
    put('sld', t0, 1)
    t1 = shift(t0 + 2e-9, [int(d.get(n, 0)) for n in CFG][::-1])
    put('sld', t1, 0)
    return t1 + 5e-9


put('rst', 2e-9, 1); put('rst', 15e-9, 0)
t = cfg_write(20e-9, CFG_A)
t = shift(t, [1, 0, 1]) + 5e-9
tB0 = t
t = cfg_write(t, CFG_B)
t_mid, t_after = tB0 + 2e-9 + 6 * TC, t                          # B 를 미는 중간, SLD 내린 뒤
t = shift(t, [1, 1]) + 10e-9
tend = t

if sys.argv[1] == 'write':
    L = ['* digtest3: chip_lib v3 설정 레지스터 + 공유 SCK·SDI + β 미러', '.option post=0 ingold=2 numdgt=8 measdgt=8',
         '.temp 25', f".lib '{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice' tt", f".include '{OLY}/sern_hog/char/decks/hog_tr.spice'",
         'Vdd vdd 0 2.5', 'Vss vss 0 -2.5', 'Xbias vbn vbp vbpc vdd vss HOG_BIAS', 'Vbpc vbpc 0 0.7']
    L += primitives() + lib()
    L += [f"V{n} {n} 0 PWL(" + " ".join(f"{x:.5e} {2.5 if b else -2.5}" for x, b in w) + ")" for n, w in sorted(wv.items())]
    L += global_decode() + config_block(BUF)
    for r in REGS:
        prev = 'sdi'
        for k in range(NLEN[r]):
            L.append(f"XF{r}{k} {prev} {r}_clk rst rstb {r}q{k} vdd vss DFFR")
            prev = f'{r}q{k}'
    L += [f".meas tran {n}_mid find v({n}) at={t_mid:.5e}" for n in CFG]
    L += [f".meas tran {n}_aft find v({n}) at={t_after + 5e-9:.5e}" for n in CFG]
    L += [f".meas tran {r}{k}_b find v({r}q{k}) at={t_after:.5e}" for r in REGS for k in range(NQ)]
    L += [f".meas tran {r}{k}_e find v({r}q{k}) at={tend - 2e-9:.5e}" for r in REGS for k in range(NQ)]
    # β 미러 + 주입기 한 쌍 (출력 0 V 전류계)
    L += beta_mirror() + [f"XMP0 ip0 pref vdd vdd {PF} w=42 l=2 nf=8", "Vip ip0 0 0", f"XMN0 in0 nref vss vss {NF} w=15 l=2 nf=3", "Vin in0 0 0"]
    L += [f".meas tran ibp find i(Vbm_p) at={tend - 2e-9:.5e}", f".meas tran ibn find i(Vbm_n) at={tend - 2e-9:.5e}",
          f".meas tran iinp find i(Vip) at={tend - 2e-9:.5e}", f".meas tran iinn find i(Vin) at={tend - 2e-9:.5e}",
          f".meas tran vpref find v(pref) at={tend - 2e-9:.5e}", f".meas tran vnref find v(nref) at={tend - 2e-9:.5e}"]
    L += [f".meas tran ck_{r} trig v({r}_clk) val=-1.5 rise=1 td=150n targ v({r}_clk) val=1.5 rise=1 td=150n" for r in REGS]
    L += [f".tran 0.05n {tend:.5e}", '.end']
    (HERE / 'decks').mkdir(exist_ok=True)
    (HERE / 'decks' / f'{DECK}.sp').write_text('\n'.join(L) + '\n')
    print(f'decks/{DECK}.sp', len(L), '줄', f't_end {tend*1e9:.0f} ns')
else:
    M = {k.lower(): float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*([-+]?[0-9.]+(?:[eE][-+]?\d+)?)', (HERE / 'out' / f'{DECK}.lis').read_text(), re.M)}
    b = lambda x: int(x > 0)
    mid = {n: b(M[f'{n}_mid']) for n in CFG}; aft = {n: b(M[f'{n}_aft']) for n in CFG}
    wa, wb = {n: CFG_A.get(n, 0) for n in CFG}, {n: CFG_B.get(n, 0) for n in CFG}
    print('설정 B 를 미는 중:', ''.join(map(str, mid.values())), '(A 여야', ''.join(map(str, wa.values())) + ')', 'OK' if mid == wa else '틀림')
    print('SLD 내린 뒤     :', ''.join(map(str, aft.values())), '(B 여야', ''.join(map(str, wb.values())) + ')', 'OK' if aft == wb else '틀림')
    bad = 0
    for r in REGS:
        qb = [b(M[f'{r}{k}_b']) for k in range(NQ)]; qe = [b(M[f'{r}{k}_e']) for k in range(NQ)]
        we = [1, 1, 1, 0] if r in ('row1', 'col2') else [1, 0, 1, 0]
        ok = qb == [1, 0, 1, 0] and qe == we
        bad += not ok
        print(f"  {r:4s}: 설정 B 뒤 {qb}, 끝 {qe} (기대 [1, 0, 1, 0] → {we})", '' if ok else '← 틀림')
    print('레지스터', '모두 맞음' if not bad else f'{bad} 개 틀림', '| 클록 상승 (−1.5 → +1.5 V):',
          ' '.join(f"{r} {M.get(f'ck_{r}', float('nan'))*1e9:.2f} ns" for r in REGS))
    print(f"β 미러: 기준 가지 PMOS diode {abs(M['ibp'])*1e6:.2f} µA, NMOS diode {abs(M['ibn'])*1e6:.2f} µA → 주입기 (출력 0 V) "
          f"MP {abs(M['iinp'])*1e6:.2f} µA / MN {abs(M['iinn'])*1e6:.2f} µA (Python β {BETA*1e6:.2f} µA), pref {M['vpref']:.3f} V, nref {M['vnref']:.3f} V")

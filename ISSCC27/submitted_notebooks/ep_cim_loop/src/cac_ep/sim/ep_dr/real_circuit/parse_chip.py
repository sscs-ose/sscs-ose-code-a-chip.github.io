"""gen_chip_deck2.py (v3) 결과 읽기: out/<name>.lis + decks/<name>_ref.json.
READ : 설정 bit·DATA latch bit, free·nudge 출력 (Python 대조), VBUS 패드 판독 (같은 시각 행 전압·Python 대조), ROW2 token 복귀,
       β 기준 가지 전류, 감지 칸 갱신 bit, 전력. WRITE: verify 전류 (free·nudge), 펄스 중 셀 양단 전압 (선택·이웃·같은 열·대각).
쓰임: python parse_chip.py chip_read2 / chip_write2
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
name = sys.argv[1]
txt = (HERE / 'out' / f'{name}.lis').read_text()
M = {k.lower(): float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*([-+]?[0-9.]+(?:[eE][-+]?\d+)?)', txt, re.M)}
bad = re.findall(r'^\s*(\w+)\s*=\s*failed', txt, re.M)
R = json.load(open(HERE / 'decks' / f'{name}_ref.json'))
print(f"{name}: test {R['test']}, 설정 쓰기 {R['n_cfg']} 번, t_end {R['tend']*1e9:.0f} ns", f"| meas 실패 {bad[:5]}" if bad else '')
b = lambda x: int(x > 0)
if R['test'] == 'read':
    want = dict(m1=1, m0=1, dload=1, wu_en=1, rd_out=1, ts_row2=1)
    got = {n: b(M[f'cf_{n}']) for n in R['cfg_names']}
    print('설정 (READ 중):', ' '.join(f"{n}={v}" for n, v in got.items()), 'OK' if all(got[n] == want.get(n, 0) for n in got) else '← 틀림')
    dl = [b(M[f'dl{k}']) for k in range(len(R['bits']))]
    print(f"DATA latch {len(dl)} bit:", '모두 맞음' if dl == R['bits'] else f"틀림 {sum(x != y for x, y in zip(dl, R['bits']))} bit")
    fy = np.array([M[f'fy{j}'] for j in range(6)]); ny = np.array([M[f'ny{j}'] for j in range(6)])
    pf, pn = np.array(R['vy_f']), np.array(R['vy_n'])
    print('free 출력 SPICE', np.round(fy * 1e3, 2), 'mV | Python', np.round(pf * 1e3, 2), f'| 최대 차 {np.abs(fy - pf).max()*1e3:.2f} mV')
    print('nudge 출력 SPICE', np.round(ny * 1e3, 2), 'mV | Python', np.round(pn * 1e3, 2), f'| 최대 차 {np.abs(ny - pn).max()*1e3:.2f} mV')
    d = fy[0::2] - fy[1::2]
    print('예측 SPICE', int(np.argmax(d)), 'Python', R['pred'], 'label', R['label'], '| 입력 행', [round(M[f'fx{k}'], 4) for k in range(4)])
    rof = np.array([M[f'ro{j}f'] for j in range(6)]); ryf = np.array([M[f'ry{j}f'] for j in range(6)])
    ron = np.array([M[f'ro{j}n'] for j in range(6)]); ryn = np.array([M[f'ry{j}n'] for j in range(6)])
    print('VBUS_F 판독', np.round(rof * 1e3, 2), 'mV | 그때 행', np.round(ryf * 1e3, 2), f'| 판독 − 행 최대 {np.abs(rof - ryf).max()*1e3:.3f} mV'
          f' | 판독 − Python 최대 {np.abs(rof - pf).max()*1e3:.2f} mV | 판독 예측 {int(np.argmax(rof[0::2] - rof[1::2]))}')
    print('VBUS_N 판독', np.round(ron * 1e3, 2), 'mV | 그때 행', np.round(ryn * 1e3, 2), f'| 판독 − 행 최대 {np.abs(ron - ryn).max()*1e3:.3f} mV')
    print('판독 칸에서 행 전압 − 추론 끝 (t_inf) 최대', f'free {np.abs(ryf - fy).max()*1e3:.3f} mV, nudge {np.abs(ryn - ny).max()*1e3:.3f} mV')
    tok = [b(M[f'r2tok{k}']) for k in range(6)]
    print('판독 뒤 ROW2 token', tok, 'OK' if tok == [1, 0, 0, 0, 0, 0] else '← 틀림')
    print(f"β 기준 가지: pref {abs(M['ibp'])*1e6:.2f} µA, nref {abs(M['ibn'])*1e6:.2f} µA (Python β {R['beta']*1e6:.2f} µA)")
    for k, key in ((1, 'cells1'), (2, 'cells2')):
        ok, s = 0, []
        for n, cl in enumerate(R[key]):
            hw = M[f'lq{k}_{n}'] < 0
            ok += hw == cl['reset']
            s.append(f"({cl['row']},{cl['col']}) δ {cl['delta']*1e3:+.3f} mV {'RESET' if cl['reset'] else 'SET'}/{'RESET' if hw else 'SET'}")
        print(f"감지 stage {k}: {ok}/{len(R[key])} |", ' · '.join(s))
    print(f"전력 (READ 시작 → 끝, VDD·VSS): {2.5 * (M['iss'] - M['idd'])*1e3:.2f} mW")
else:
    for tag in [t for k, t, _ in R['meas_w'] if k == 'i']:
        print(f"verify {tag}: free {M[f'i_{tag}_f']*1e6:7.2f} µA, nudge {M[f'i_{tag}_n']*1e6:7.2f} µA")
    for tag in [t for k, t, _ in R['meas_w'] if k == 'v']:
        for p in 'fn':
            print(f"펄스 {tag:4s} {p}: 셀 양단 선택 {M[f'v_{tag}_{p}_t']:+.3f} V, 같은 행 이웃 {M[f'v_{tag}_{p}_nb']*1e3:+.1f} mV, "
                  f"같은 열 {M[f'v_{tag}_{p}_cm']*1e3:+.1f} mV, 대각 {M[f'v_{tag}_{p}_dg']*1e3:+.1f} mV | 행 {M[f'vrow_{tag}_{p}']:+.3f} 열 "
                  f"{M[f'vcol_{tag}_{p}']:+.3f} 비선택 열 {M[f'vcolu_{tag}_{p}']:+.3f} WL {M[f'vwl_{tag}_{p}']:+.2f} 비선택 WL {M[f'vwlu_{tag}_{p}']:+.2f} V")
        print(f"   V_W 버스 {M[f'vbus_{tag}']:+.3f} V")

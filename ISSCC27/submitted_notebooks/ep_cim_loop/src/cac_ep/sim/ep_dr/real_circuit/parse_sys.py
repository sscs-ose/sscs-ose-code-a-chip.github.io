"""gen_sys_deck.py 덱의 SPICE 결과 → (1) select 전 노드 전압 대 Python, (2) 셀마다 버스에서 본 셀 전압 대 Python,
(3) 갱신 bit (latch) 대 Python 정답, stage 별. 쓰임: python parse_sys.py sys0 [sys0_sa ...]
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

here = Path(__file__).parent
for name in sys.argv[1:]:
    R = json.load(open(here / 'decks' / f'{name}_ref.json'))
    f = here / 'out' / f'{name}.lis'
    txt = (f if f.exists() else here / 'out' / f'{name}.log').read_text(errors='ignore')   # SPICE .lis / ngspice .log
    M = {k.lower(): float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*([-+]?[0-9.]+(?:[eE][-+]?\d+)?)', txt, re.M)}
    print(f"== {name}: label {R['label']}, e {R['e']}, 시간 칸 {len(R['cells1'])}/{len(R['cells2'])}, "
          f"칸당 {R['t_slot_ns']:.0f} ns")
    err = []
    for p, (hk, yk) in (('f', ('vh_f', 'vy_f')), ('n', ('vh_n', 'vy_n'))):
        err += [M[f'{p}h{j}'] - v for j, v in enumerate(R[hk])] + [M[f'{p}y{j}'] - v for j, v in enumerate(R[yk])]
    print(f"   select 전 노드 (hidden 60 + 출력 6, × 2): SPICE − Python 최대 {np.max(np.abs(err))*1e6:.2f} µV")
    for k, key in ((1, 'cells1'), (2, 'cells2')):
        if not R[key]:
            continue
        ok, dv, dd = 0, [], []
        lines = []
        for n, cl in enumerate(R[key]):
            vf = M[f'b{k}rf_{n}'] - M[f'b{k}cf_{n}']; vn = M[f'b{k}rn_{n}'] - M[f'b{k}cn_{n}']
            dv += [vf - cl['vf'], vn - cl['vn']]
            dd.append((abs(vn) - abs(vf)) - cl['delta'])
            reset_hw = M[f'lq{k}_{n}'] < 0                                     # lq 높음 = SET
            ok += reset_hw == cl['reset']
            lines.append(f"{cl['delta']*1e6:+9.1f}{'' if reset_hw == cl['reset'] else '×'}")
        stage = 'first' if k == 1 else 'last'
        print(f"   {stage} stage: bit 일치 {ok}/{len(R[key])} | 버스에서 본 셀 전압 − Python: 최대 {np.max(np.abs(dv))*1e6:.1f} µV, "
              f"δ 오차 최대 {np.max(np.abs(dd))*1e6:.2f} µV")
        print(f"     δ [µV] (× = 틀림): " + ' '.join(lines))
    p = -2.5 * M.get('idd', np.nan) + 2.5 * M.get('iss', np.nan)
    print(f"   평균 전력 {p*1e3:.2f} mW (weight update 회로 2 벌 + 크로스바 2 벌 + 바이어스)")

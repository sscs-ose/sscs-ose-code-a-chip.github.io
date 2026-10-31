"""gen_wu_block.py 덱의 SPICE 결과 (.lis 의 .meas) → 판정 일치·실효 offset·|ΔV| 경로 오차·전력.
쓰임: python parse_wu_block.py wu_blk0 [wu_blk0_sa ...]   (out/<name>.lis, decks/<name>_ref.json)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

here = Path(__file__).parent
for name in sys.argv[1:]:
    ref = json.load(open(here / 'decks' / f'{name}_ref.json'))
    txt = (here / 'out' / f'{name}.lis').read_text(errors='ignore')
    M = {k.lower(): float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*([-+]?[0-9.]+(?:[eE][-+]?\d+)?)', txt, re.M)}
    cells = ref['cells']
    rows = []
    for n, c in enumerate(cells):
        g = lambda k: M.get(f'{k}{n}'.lower(), np.nan)
        rows.append(dict(c, absf=g('absf'), absn=g('absn'), sen=g('sen'), q1=g('q1_'), q2=g('q2_'), lq=g('lq')))
    ok = lambda r: (r['lq'] > 0) == bool(r['set_exact'])
    q_ok = [((r['q1'] > 0) == (r['dvf'] > 0)) and ((r['q2'] > 0) == (r['dvn'] > 0)) for r in rows]
    ef = np.array([r['absf'] - abs(r['dvf']) for r in rows]) * 1e3
    en = np.array([r['absn'] - abs(r['dvn']) for r in rows]) * 1e3
    p = 2.5 * M.get('idd', np.nan) * -1 + 2.5 * M.get('iss', np.nan)           # 전원에서 나가는 전류 (SPICE 부호)
    print(f"== {name}: 셀 {len(rows)}, 판정 일치 {sum(map(ok, rows))}/{len(rows)}, COMP1/2 부호 일치 {sum(q_ok)}/{len(rows)}, "
          f"측정 없음 {sum(np.isnan(r['lq']) for r in rows)}")
    print(f"   |ΔV_f| 경로 오차 중앙 {np.nanmedian(ef):+.3f} mV (범위 {np.nanmin(ef):+.3f} … {np.nanmax(ef):+.3f}), "
          f"|ΔV_n| 경로 {np.nanmedian(en):+.3f} mV, 두 경로 차 (f − n) 중앙 {np.nanmedian(ef - en)*1e3:+.1f} µV")
    print(f"   평균 전력 {p*1e3:.3f} mW (idd {M.get('idd', np.nan):.3e}, iss {M.get('iss', np.nan):.3e} A), "
          f"셀당 {ref['t_cell_ns']:.0f} ns → {p*ref['t_cell_ns']*1e-9*1e9:.1f} nJ/셀")
    print("   ΔV_f mV | δ = |ΔV_n|−|ΔV_f| µV 별 결과 (S = SET, R = RESET, 소문자 = 틀림)")
    for dvf in sorted({r['dvf'] for r in rows}):
        line = []
        for r in sorted([r for r in rows if r['dvf'] == dvf], key=lambda r: (r['d'], r['flip'])):
            s = 'S' if r['lq'] > 0 else 'R'
            line.append(f"{r['d']*1e6:+.0f}{'f' if r['flip'] < 0 else ''}:{s if ok(r) else s.lower()}")
        print(f"   {dvf*1e3:+7.1f} | " + ' '.join(line))

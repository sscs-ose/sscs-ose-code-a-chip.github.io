"""오픈소스 회로 시뮬 결과를 덱 생성기의 Python 정답 (_ref.json) 과 맞춰 본다 (SPICE 결과 없이).
판정식은 real_circuit/parse_wu_block.py · parse_sys.py 와 같다 (그 파일들은 SPICE .lis 를 읽어서 여기 따로 둠).
쓰임: python3 sim_check.py wu  <deck>_ref.json <Xyce .mt0>         → 판정 (lq > 0 = SET) 일치 수, COMP1/2 부호, 경로 오차, 전력
      python3 sim_check.py sys <deck>_ref.json <Xyce .mt0>         → select 전 노드 대 Python, 갱신 bit 일치 (stage 별), 전력
      python3 sim_check.py p1r <rows.json> <ngspice -o 로그> [기준 로그] → 1R 쓰기 격자: G 가 5 % 넘게 바뀐 행 수, 기준과 ird 비
마지막 줄 = json 요약."""
import json
import math
import re
import sys

NUM = r'([-+]?[0-9.]+(?:[eE][-+]?\d+)?)'


def meas(path):
    return {k.lower(): float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*' + NUM, open(path, errors='ignore').read(), re.M)}


mode, refp, mp = sys.argv[1:4]
R = json.load(open(refp))
M = meas(mp)
J = dict(mode=mode, n_meas=len(M))
if mode == 'wu':
    rows = []
    for n, c in enumerate(R['cells']):
        g = lambda k: M.get(f'{k}{n}', math.nan)
        rows.append(dict(c, absf=g('absf'), absn=g('absn'), q1=g('q1_'), q2=g('q2_'), lq=g('lq')))
    have = [r for r in rows if not math.isnan(r['lq'])]
    ok = sum((r['lq'] > 0) == bool(r['set_exact']) for r in have)
    qok = sum(((r['q1'] > 0) == (r['dvf'] > 0)) and ((r['q2'] > 0) == (r['dvn'] > 0)) for r in have)
    gain = R.get('args', {}).get('gain', 1.0)                  # A1–A4 gain of the deck (chip configuration: 2)
    ef = sorted((r['absf'] - gain * abs(r['dvf'])) * 1e3 for r in have)
    p = -2.5 * M.get('idd', math.nan) + 2.5 * M.get('iss', math.nan)
    J.update(cells=len(rows), measured=len(have), decision_ok=ok, comp12_ok=qok,
             path_err_med_mV=round(ef[len(ef) // 2], 4) if ef else None, power_mW=round(p * 1e3, 4))
    print(f"WU block: cells {len(have)}/{len(rows)}, decisions match {ok}/{len(have)}, COMP1/2 sign {qok}/{len(have)}, "
          f"|ΔV_f| path error median {J['path_err_med_mV']} mV, power {J['power_mW']} mW")
elif mode == 'sys':
    err = []
    for p_, (hk, yk) in (('f', ('vh_f', 'vy_f')), ('n', ('vh_n', 'vy_n'))):
        err += [M.get(f'{p_}h{j}', math.nan) - v for j, v in enumerate(R[hk])] + [M.get(f'{p_}y{j}', math.nan) - v for j, v in enumerate(R[yk])]
    J['node_err_max_uV'] = round(max(abs(e) for e in err) * 1e6, 3)
    for k, key in ((1, 'cells1'), (2, 'cells2')):
        ok = sum((M.get(f'lq{k}_{n}', math.nan) < 0) == cl['reset'] for n, cl in enumerate(R[key]))
        J[f'stage{k}_bits_ok'] = [ok, len(R[key])]
    J['power_mW'] = round((-2.5 * M.get('idd', math.nan) + 2.5 * M.get('iss', math.nan)) * 1e3, 4)
    print(f"chip deck: all select nodes − Python max {J['node_err_max_uV']} µV, first stage bit {J['stage1_bits_ok']}, "
          f"last stage bit {J['stage2_bits_ok']}, power {J['power_mW']} mW")
elif mode == 'p1r':
    TOX, TFREF, IK1, VREF, VRD = 5.0e-9, 4.7249e-9, 6.140e-5, 0.430, 0.1      # opensrc/spice/cmp_p1r.py 와 같은 상수 (VA 기본값)
    g_of_tf = lambda tf: IK1 * math.exp(-(TOX - tf) / (TOX - TFREF)) * math.sinh(VRD / VREF) / VRD
    rows = R['rows']
    ird = [M.get(f'ird_{k}', math.nan) for k in range(len(rows))]
    sw = [abs(i / 0.1 - g_of_tf(r[0])) > 0.05 * g_of_tf(r[0]) for r, i in zip(rows, ird)]
    J.update(rows=len(rows), measured=sum(not math.isnan(i) for i in ird), switched=sum(sw))
    if len(sys.argv) > 4:
        B = meas(sys.argv[4])
        rb = [i / B[f'ird_{k}'] for k, i in enumerate(ird) if B.get(f'ird_{k}')]
        J.update(ratio_vs_ref=[round(min(rb), 6), round(max(rb), 6)])
    print(f"1R write grid: rows {J['measured']}/{len(rows)}, rows with G changed by > 5 %: {J['switched']} (reference: 143)"
          + (f", ird ratio vs reference log {J['ratio_vs_ref']}" if 'ratio_vs_ref' in J else ''))
print(json.dumps(J, ensure_ascii=False))

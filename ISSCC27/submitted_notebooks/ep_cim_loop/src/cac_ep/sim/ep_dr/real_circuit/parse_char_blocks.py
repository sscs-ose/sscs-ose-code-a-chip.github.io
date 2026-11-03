"""char_blocks.py 덱 결과 (.lis 의 .meas) → out/char_blocks.json + 화면 표 (10/30). 노트북 §5.5–5.8 성능 표의 숫자 원본.
전력 = 5 V (VDD − VSS) × 전류. 에너지 = 5 V × ∫ I dt (한 클록 주기). TG 저항 = 10 mV / I.
몬테카를로 offset 은 out/mc_block.json (mc_block.py, 199 표본) 에서 가져온다."""
import json
import re
from pathlib import Path

H = Path(__file__).resolve().parent


def meas(name):
    t = (H / 'out' / f'{name}.lis').read_text()
    return {k: float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*([-+]?\d\.\d+e[-+]\d+)', t, re.M)}


R = {}
for cm in ('06', '02'):
    m = meas(f'char_pre_cm{cm}')
    R[f'pre_cm{cm}'] = dict(gain_db=m['a0'], gain=10 ** (m['a0'] / 20), f3db_MHz=m['f3db'] / 1e6, ugf_MHz=m['ugf'] / 1e6,
                            current_uA=abs(m['iq']) * 1e6, power_uW=5 * abs(m['iq']) * 1e6)
m = meas('char_sa')
R['sa'] = dict(delay_ns=(m['td1'] * 1e9, m['td2'] * 1e9), energy_pJ=(m['ea'] * 1e12, m['eb'] * 1e12), idle_nA=abs(m['idle']) * 1e9, idle_power_uW=5 * abs(m['idle']) * 1e6)
m = meas('char_lat')
R['latch'] = dict(tdq_rise_ns=m['tdq_r'] * 1e9, tdq_fall_ns=m['tdq_f'] * 1e9, q_hold_V=m['q_hold'], idle_nA=abs(m['idle']) * 1e9, idle_power_uW=5 * abs(m['idle']) * 1e6)
m = meas('char_tg')
R['tg'] = {k[2:]: 0.01 / abs(v) for k, v in m.items() if k.startswith('i_')}
m = meas('char_nudge')
a, b, c, d = (abs(m[k]) * 1e6 for k in 'abcd')
R['nudge'] = dict(ref_n_uA=a, inj_p_uA=b, ref_p_uA=c, inj_n_uA=d, ref_power_mW=5 * (a + c) / 1e3, inj_power_mW=2.5 * (b + d) / 1e3)
mc = json.loads((H / 'out' / 'mc_block.json').read_text())
R['mc'] = {k: dict(mean_mV=mc[k]['mean'] * 1e3, std_mV=mc[k]['std'] * 1e3, n=mc['n']) for k in ('mc_c1_cm01', 'mc_c3_cm06', 'mc_c3_cm02')}
(H / 'out' / 'char_blocks.json').write_text(json.dumps(R, indent=1))
print(json.dumps(R, indent=1))

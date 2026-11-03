"""β 미러 크기 고르기 (10/26, chip_lib.beta_mirror): HOG bias (5 µA) 를 단위 소자 m 개로 미러해 주입기 (출력 0 V) 전류가 β 38.12 µA 가 되는 폭.
가지마다 기준 diode·미러·주입기 복사본을 따로 둔다 (서로 독립). NMOS 쪽 = vbn 미러 → pref diode → 주입기 MP,
PMOS 쪽 = vbp·vbpc cascode 미러 → nref diode → 주입기 MN. 단일 소자 W×ratio (digtest3 판) 와 m 개 단위 소자 판을 같이 본다.
쓰임: python beta_size.py write → decks/beta_size.sp / python beta_size.py check
"""
import re
import sys
from pathlib import Path

from chip_lib import NF, PF

HERE = Path(__file__).resolve().parent
OLY = '/home/grads/s/seokjindaveoh/work'
BETA, R = 3.812e-05, 3.812e-05 / 5e-6
CASES = [('1개 W×7.624', 1, 1.0, 1.0)] + [(f'm=8 폭 ×{k:.3f}', 8, k, k) for k in (0.85, 0.9, 0.953, 1.0)] \
        + [(f'm=8 N×{kn:.3f} P×{kp:.3f}', 8, kn, kp) for kn, kp in ((0.77, 0.87), (0.78, 0.875), (0.785, 0.88), (0.79, 0.885), (0.80, 0.89))]
if sys.argv[1] == 'write':
    L = ['* beta_size', '.option post=0 ingold=2 numdgt=8 measdgt=8', '.temp 25', f".lib '{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice' tt",
         f".include '{OLY}/sern_hog/char/decks/hog_tr.spice'", 'Vdd vdd 0 2.5', 'Vss vss 0 -2.5', 'Xbias vbn vbp vbpc vdd vss HOG_BIAS', 'Vbpc vbpc 0 0.7']
    for i, (_, m, kn, kp) in enumerate(CASES):
        wn, wp, wpc = (0.9 * R, 2 * R, 1.5 * R) if m == 1 else (0.9 * kn, 2 * kp, 1.5 * kp)
        L += [f"XPd{i} pr{i} pr{i} vdd vdd {PF} w=42 l=2 nf=8", f"Vpb{i} pr{i} pd{i} 0", f"XNm{i} pd{i} vbn vss vss {NF} w={wn:.4f} l=1 m={m}",
              f"XMP{i} ip{i} pr{i} vdd vdd {PF} w=42 l=2 nf=8", f"Vip{i} ip{i} 0 0",
              f"XNd{i} nr{i} nr{i} vss vss {NF} w=15 l=2 nf=3", f"Vnb{i} nd{i} nr{i} 0",
              f"XPm{i} bx{i} vbp vdd vdd {PF} w={wp:.4f} l=0.8 m={m}", f"XPc{i} nd{i} vbpc bx{i} vdd {PF} w={wpc:.4f} l=0.5 m={m}",
              f"XMN{i} in{i} nr{i} vss vss {NF} w=15 l=2 nf=3", f"Vin{i} in{i} 0 0"]
    L += ['.op'] + [f".print dc i(Vpb{i}) i(Vip{i}) i(Vnb{i}) i(Vin{i})" for i in range(len(CASES))]
    L += ['.dc Vdd 2.5 2.5 1'] + [f".meas dc a{i} find i(Vpb{i}) at=2.5" for i in range(len(CASES))] \
        + [f".meas dc b{i} find i(Vip{i}) at=2.5" for i in range(len(CASES))] + [f".meas dc c{i} find i(Vnb{i}) at=2.5" for i in range(len(CASES))] \
        + [f".meas dc d{i} find i(Vin{i}) at=2.5" for i in range(len(CASES))] + ['.end']
    (HERE / 'decks' / 'beta_size.sp').write_text('\n'.join(L) + '\n')
    print('decks/beta_size.sp', len(CASES), '가지')
else:
    M = {k.lower(): float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*([-+]?[0-9.]+(?:[eE][-+]?\d+)?)', (HERE / 'out' / 'beta_size.lis').read_text(), re.M)}
    print(f'가지 | NMOS 미러 → pref diode → 주입기 MP | PMOS cascode 미러 → nref diode → 주입기 MN   (β {BETA*1e6:.2f} µA)')
    for i, (nm, *_) in enumerate(CASES):
        print(f"{nm:14s} | {abs(M[f'a{i}'])*1e6:6.2f} → {abs(M[f'b{i}'])*1e6:6.2f} µA ({(abs(M[f'b{i}'])/BETA-1)*100:+5.1f} %) | "
              f"{abs(M[f'c{i}'])*1e6:6.2f} → {abs(M[f'd{i}'])*1e6:6.2f} µA ({(abs(M[f'd{i}'])/BETA-1)*100:+5.1f} %)")

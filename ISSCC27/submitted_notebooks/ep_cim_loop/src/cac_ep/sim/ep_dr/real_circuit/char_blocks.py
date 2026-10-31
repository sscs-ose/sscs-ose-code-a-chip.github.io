"""weight update 회로 부품 단독 특성 덱 (10/30, 사용자 "빠진 항목 시뮬 돌려서 채워줘"): 노트북 §5.5–5.8 성능 표용.
  char_pre_cm06 / char_pre_cm02 : PRE (COMP3 전치 증폭기) 이득 (AC), 3 dB 대역, 단위이득 주파수, 전류 (공통 0.6 / 0.2 V, MC 덱과 같음)
  char_sa  : StrongARM (+ inverter 분리 + NOR latch) 판정 지연, 판정마다 에너지, reset 구간 누설 전류 (입력차 ±10 mV 교대)
  char_lat : dynamic D latch D→Q 지연 (상승·하강), 클록 낮음에서 450 ns 유지, 대기 전류
  char_tg  : TG (N 2/0.5 ∥ P 4/0.5) 켜짐 저항 (입력 −2.5…2.5 V 쓸기, 10 mV 강하)
  char_nudge : β 미러 + 주입기 (출력 0 V) 가지 전류 → 전력
회로는 wu_lib.py·chip_lib.py 의 것을 그대로 쓴다 (새로 그리지 않음). 입력·클록 모양은 mc_block.py 의 comp 덱과 같다.
쓰임: python char_blocks.py → decks/char_*.sp  (Olympus: sbatch ../run_spice.sbatch <dir> char_pre_cm06 …) → python parse_char_blocks.py
"""
from pathlib import Path

from chip_lib import NF, PF, beta_mirror
from wu_lib import primitives

HERE = Path(__file__).resolve().parent
OLY = '/home/grads/s/seokjindaveoh/work'
LIB = f"{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice"
HOG = f"{OLY}/sern_hog/char/decks/hog_tr.spice"
HEAD = ['.option post=0 ingold=2 numdgt=8 measdgt=8', '.temp 25', f".lib '{LIB}' tt", f".include '{HOG}'",
        'Vdd vdd 0 2.5', 'Vss vss 0 -2.5', 'Xbias vbn vbp vbpc vdd vss HOG_BIAS', 'Vbnc vbnc 0 -1.0', 'Vbpc vbpc 0 0.7']
(HERE / 'decks').mkdir(exist_ok=True)


def write(name, lines):
    (HERE / 'decks' / f'{name}.sp').write_text('\n'.join(lines) + '\n')
    print('decks/' + name + '.sp')


# ---- PRE: 차동 AC 이득 = |V(op) − V(on)| / 1 V (입력 ±0.5 V ac), 전류는 전용 전류계
for cm in ('06', '02'):
    L = [f'* char_pre_cm{cm}: PRE gain, bandwidth, current (common-mode 0.{cm[1]} V)'] + HEAD + primitives()
    L += ['Vamm vdd vddp 0', f'Vcm cmn 0 0.{cm[1]}', 'Vp inp cmn dc 0 ac 0.5', 'Vn inn cmn dc 0 ac -0.5',
          'XP inp inn op on vbn vddp vss PRE', 'Cop op 0 20f', 'Con on 0 20f', 'Ed d 0 op on 1',
          '.ac dec 20 1k 10G',
          '.meas ac a0 find vdb(d) at=1k', ".meas ac f3db when vdb(d)='a0-3' fall=1", '.meas ac ugf when vdb(d)=0 fall=1',
          '.dc Vdd 2.5 2.5 1', '.meas dc iq find i(Vamm) at=2.5', '.end']
    write(f'char_pre_cm{cm}', L)

# ---- SA: 클록 40 ns (낮음 20 ns = reset, 높음 20 ns = 판정), 입력차 +10, −10, +10, −10 mV
T, VD = 40e-9, 10e-3
L = ['* char_sa: StrongARM decision delay, energy per decision, idle current'] + HEAD + primitives()
pts = [(0.0, VD)]
for i in range(1, 5):
    t = i * T + T / 4
    pts += [(t, VD * (-1) ** (i - 1)), (t + 0.2e-9, VD * (-1) ** i)]
ck = [(0.0, -2.5)]
for i in range(5):
    ck += [(i * T + T / 2, -2.5), (i * T + T / 2 + 0.2e-9, 2.5), ((i + 1) * T - 0.2e-9, 2.5), ((i + 1) * T, -2.5)]
L += ['Vd vd 0 PWL(' + ' '.join(f'{t:.5e} {v:.6e}' for t, v in pts) + ')', 'Vcm cmn 0 0.1', 'Ep inp cmn vd 0 0.5', 'En inn cmn vd 0 -0.5',
      'Rip inp inpx 3k', 'Rin inn innx 3k', 'Cip inpx 0 20f', 'Cin innx 0 20f',
      'Vck ck 0 PWL(' + ' '.join(f'{t:.5e} {v:.3f}' for t, v in ck) + ')', 'Vamm vdd vddp 0',
      'XSA inpx innx ck q qb vddp vss SA', 'Cq q 0 20f', 'Cqb qb 0 20f',
      f'.tran 0.01n {5 * T:.3e}',
      # 칸 1 (입력차 +) → q 올라감, 칸 2 (−) → qb 올라감
      '.meas tran td1 trig v(ck) val=0 rise=3 targ v(q) val=0 rise=1',   # q 는 시작 때 이미 1 이라 칸 3 (입력차 +) 에서 다시 올라갈 때를 잼
      '.meas tran td2 trig v(ck) val=0 rise=2 targ v(qb) val=0 rise=1',
      f'.meas tran qa integ i(Vamm) from={2 * T:.3e} to={3 * T:.3e}', f'.meas tran qb2 integ i(Vamm) from={3 * T:.3e} to={4 * T:.3e}',
      ".meas tran ea param='5*qa'", ".meas tran eb param='5*qb2'",
      f'.meas tran idle find i(Vamm) at={2 * T + T / 2 - 1e-9:.3e}', '.end']
write('char_sa', L)

# ---- D latch: 투명 (clk 2.5 V) 0–100 ns, 낮음 100 ns 이후. D: 20 ns 올라감, 60 ns 내려감, 120 ns 올라가려 함 (TG 꺼짐)
L = ['* char_lat: dynamic D latch D->Q delay, hold, idle current'] + HEAD + primitives()
L += ['Vamm vdd vddp 0', 'Vd d 0 PWL(0 -2.5 20n -2.5 20.1n 2.5 60n 2.5 60.1n -2.5 120n -2.5 120.1n 2.5 450n 2.5)',
      'Vck clk 0 PWL(0 2.5 100n 2.5 100.1n -2.5)', 'Vckb clkb 0 PWL(0 -2.5 100n -2.5 100.1n 2.5)',
      'XL d clk clkb q qb vddp vss DLATCH', 'Cq q 0 20f', 'Cqb qb 0 20f', '.tran 0.01n 450n',
      '.meas tran tdq_r trig v(d) val=0 rise=1 targ v(q) val=0 rise=1', '.meas tran tdq_f trig v(d) val=0 fall=1 targ v(q) val=0 fall=1',
      '.meas tran q_hold find v(q) at=440n', '.meas tran s_hold find v(XL.s) at=440n', '.meas tran idle find i(Vamm) at=300n', '.end']
write('char_lat', L)

# ---- TG: a → b, b 는 a − 10 mV 로 끌고 전류 측정
L = ['* char_tg: TG on resistance'] + HEAD + primitives()
L += ['Vin a 0 0', 'Eb c 0 a 0 1', 'Vb b c -0.01', 'Xtg a b vdd vss vdd vss TG', '.dc Vin -2.5 2.5 0.05']
for tag, v in (('m25', -2.5), ('m2', -2.0), ('m1', -1.0), ('m03', -0.3), ('z', 0.0), ('p03', 0.3), ('p1', 1.0), ('p2', 2.0), ('p25', 2.5)):
    L.append(f'.meas dc i_{tag} find i(Vb) at={v}')
write('char_tg', L + ['.end'])

# ---- β 미러 + 주입기 (출력 0 V). 기준 가지 a (NMOS 미러 → pref), c (PMOS 미러 → nref), 주입기 b (MP), d (MN)
L = ['* char_nudge: beta mirror + injector branch currents'] + HEAD + primitives()
L += beta_mirror() + [f"XMP ip pref vdd vdd {PF} w=42 l=2 nf=8", 'Vip ip 0 0', f"XMN in nref vss vss {NF} w=15 l=2 nf=3", 'Vin in 0 0',
                      '.dc Vdd 2.5 2.5 1', '.meas dc a find i(Vbm_p) at=2.5', '.meas dc b find i(Vip) at=2.5',
                      '.meas dc c find i(Vbm_n) at=2.5', '.meas dc d find i(Vin) at=2.5', '.end']
write('char_nudge', L)

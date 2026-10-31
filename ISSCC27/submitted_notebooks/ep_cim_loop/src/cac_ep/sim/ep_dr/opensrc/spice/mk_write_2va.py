"""칩 쓰기 덱 (SPICE, RRAM 340 개 = .hdl Verilog-A) → 쓰는 셀만 VA, 나머지는 상태 없는 수동 소자인 SPICE 덱 (10/30, 사용자 "Write는 딱 2개의 cell만 하고, 나머지는 그냥 passive 저항으로").
쓰는 셀 = ref json 의 args.rc (행, 열) 의 free·nudge 두 개 (XfR<r>_<c>, XnR<r>_<c>). 나머지 RRAM 은 그 셀의 초기 상태 (Tfilament_0) 로 고정:
  --static lin  : 선형 저항 R = 1/G0,  G0 = dI/dV(0) = I_k1·exp(−(Tox − Tf0)/(Tox − Tfilament_ref)) / V_ref   (작은 전압 G)
  --static sinh : 같은 셀의 정적 I–V 를 그대로 둔 전류원  I = I_k1·exp(…)·sinh(V/V_ref)  (|V/V_ref| ≤ 40 로 자름 = 17 V, 동작점 반복 중 넘침 막기. 상태 없음, VA 의 전류 식과 같음 → 0.2 V verify 도 같음)
VA parameter 기본값 (I_k1·Tox·Tfilament_ref·V_ref·Tfilament_min/max) 은 덱의 .hdl 이 가리키는 VA 파일 (없으면 --va) 에서 읽고, 인스턴스 줄의 값이 있으면 그것을 쓴다.
회로의 다른 부분 (레지스터·decoder·MUX TG·write buffer·1T1R nFET·.meas·.tran) 은 한 글자도 안 바꾼다. 결과 덱은 SPICE 로도 돌고, spice2ng_osdi.py 로 ngspice 덱이 된다.
--bs : 남길 셀도 VA 대신 같은 식의 행동 모형 subckt (rram_bs, G CUR 식 + C·R, 상태 = node tf [nm]·th [K]) 로 → VA 를 못 읽는 Xyce 용.
       식은 va/sky130_fd_pr_reram__reram_cell_osdi_t0.va 와 같다 (ramp = min(time/1 ps, 1), 경계 멈춤 = stp 곱, 동작점에서 tf = Tfilament_0 으로 강하게 묶고 1 ps 뒤 gpin 1/s).
       $bound_step(t_step) 는 subckt 로 못 하므로 덱의 .tran 에 tmax 를 붙인다 (돌리는 쪽).
--keep_all : 모든 RRAM 을 남김 (--bs 와 함께 셀 하나 시험 cws 덱을 바꿀 때).
쓰임: python mk_write_2va.py <chip_write3.sp> <out.sp> [--ref chip_write3_ref.json] [--static lin|sinh] [--keep XfR2_1 XnR2_1 | --keep_all] [--bs] [--va <VA 파일>]"""
import argparse
import json
import math
import re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('deck')
ap.add_argument('out')
ap.add_argument('--ref', help='생성기의 _ref.json (args.rc 로 쓰는 셀을 정함). 없으면 <deck>_ref.json')
ap.add_argument('--static', choices=['lin', 'sinh'], default='lin')
ap.add_argument('--keep', nargs='*', help='VA 로 남길 인스턴스 이름 (주면 --ref 대신)')
ap.add_argument('--keep_all', action='store_true')
ap.add_argument('--bs', action='store_true', help='남길 셀을 행동 모형 subckt 로 (Xyce)')
ap.add_argument('--va', help='VA 파일 (parameter 기본값). 없으면 덱의 .hdl 경로, 그것도 없으면 옆의 va/orig_… 사본')
a = ap.parse_args()

deck = Path(a.deck)
L = deck.read_text().splitlines()
meas_w = []
if a.keep_all:
    keep = set()
elif a.keep is not None:                                            # --keep 만 (이름 없이) = VA 없음 (모두 고정, 시험용)
    keep = {k.lower() for k in a.keep}
else:
    ref = Path(a.ref) if a.ref else deck.with_name(deck.stem + '_ref.json')
    r, c = json.loads(ref.read_text())['args']['rc']
    keep = {f'xfr{r}_{c}', f'xnr{r}_{c}'}
    meas_w = json.loads(ref.read_text()).get('meas_w', [])

SI = {'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3}


def num(v):
    m = re.fullmatch(r'([-+]?[0-9.]+(?:[eE][-+]?\d+)?)([fpnumk]?)', v)
    return float(m.group(1)) * SI.get(m.group(2), 1.0) if m else None


cands = [a.va] if a.va else []
cands += [re.search(r'"([^"]+)"|\'([^\']+)\'', l).group(0).strip('"\'') for l in L if l.lower().startswith('.hdl')]
cands += [str(Path(__file__).resolve().parent / 'va' / 'orig_sky130_fd_pr_reram__reram_cell.va')]
va = next(p for p in cands if p and Path(p).exists())
P = {k.lower(): float(v) for k, v in re.findall(r'parameter\s+real\s+(\w+)\s*=\s*([-+0-9.eE]+)', Path(va).read_text())}



def bs_subckt(p):
    """RRAM 쓰기 모형의 행동 subckt (SPICE 문법: spice2xyce·spice2ng 가 G CUR → B 로 바꿈). 내부 node tf = Tfilament [nm], th = 온도 [K], 용량 C = 1 pF 로 크기 맞춤."""
    C = 1e-12
    tox, tmin, tmax, tfr = p['tox'], p['tfilament_min'], p['tfilament_max'], p['tfilament_ref']
    v = 'v(te,be)'
    tfm = 'v(tf)*1e-9'
    tfu = f'min(max({tfm},{tmin:.6e}),{tmax:.6e})'
    kT = f'({8.617333262e-5:.10e}*max(v(th),1))'
    gam = f"({p['gamma_k0']:.6e}+({p['gamma_k1']:.6e})*pwr(({tox:.6e}-{tfu})/1e-9,3))"
    vx = f'min(max({v},-5),5)'                                            # 변화율 식의 지수 넘침 막기 (|V| ≤ 5 V 안은 그대로)
    a0 = 0.25e-9
    rate = (f"{p['velocity_k1']:.6e}*(exp(-{p['eact_generation']:.6e}/{kT})*exp({gam}*{a0 / tox:.6e}*{vx}/{kT})"
            f"-exp(-{p['eact_recombination']:.6e}/{kT})*exp(-{gam}*{a0 / tox:.6e}*{vx}/{kT}))")
    st = lambda x: f'(0.5+0.5*sgn({x}))'
    rate_c = f"({rate})*(1-{st(f'{tfm}-{tmax:.6e}')}*{st(rate)})*(1-{st(f'{tmin:.6e}-{tfm}')}*{st(f'-({rate})')})"
    ramp = 'min(time/1e-12,1)'
    icell = f"{p['i_k1']:.6e}*exp(-({tox:.6e}-{tfu})/{tox - tfr:.6e})*sinh(max(min({v}/{p['v_ref']:.6e},40),-40))"
    return ['* mk_write_2va --bs: RRAM 쓰기 행동 모형 (= va/sky130_fd_pr_reram__reram_cell_osdi_t0.va 식)',
            '.subckt rram_bs te be tf0=4.708847e-9',
            f"Gcell te be CUR='{icell}'",
            f"Ctf tf 0 {C:g} IC='tf0*1e9'",          # UIC 시작 상태 = Tfilament_0 (Xyce 는 subckt 안 node 의 .ic 를 무시함, 10/30)
            f"Gtf 0 tf CUR='{C:g}*({ramp}*1e9*{rate_c}+(1e12*(1-{ramp})+1)*(tf0*1e9-v(tf)))'",
            f"Cth th 0 {C:g} IC={p['temperature_0']:g}",
            f"Rth th th0 {p['tau_thermal'] / C:.6e}",
            f"Vth0 th0 0 {p['temperature_0']:g}",
            f"Gth 0 th CUR='{C:g}*{ramp}*abs({v}*{icell})/{p['c_thermal']:.6e}'",
            '.ends rram_bs']


n_va, n_st, out, G0s, kept = 0, 0, [], set(), []
for l in L:
    m = re.match(r'^X(\S+)\s+(\S+)\s+(\S+)\s+sky130_fd_pr_reram__reram_cell\b(.*)$', l.strip(), re.I)
    if not m:
        out.append(l)
        continue
    if a.keep_all or f'x{m.group(1)}'.lower() in keep:
        if a.keep_all:
            keep.add(f'x{m.group(1)}'.lower())
        if a.bs:
            p = dict(P)
            for k, v in re.findall(r'(\w+)\s*=\s*(\S+)', m.group(4)):
                if num(v) is not None:
                    p[k.lower()] = num(v)
            l = f"X{m.group(1)} {m.group(2)} {m.group(3)} rram_bs tf0={p['tfilament_0']:.9e}"
        out.append(l)
        n_va += 1
        kept.append((m.group(1), m.group(2), m.group(3)))
        continue
    p = dict(P)
    for k, v in re.findall(r'(\w+)\s*=\s*(\S+)', m.group(4)):
        x = num(v)
        if x is not None:
            p[k.lower()] = x
    tf = min(max(p['tfilament_0'], p['tfilament_min']), p['tfilament_max'])
    i0 = p['i_k1'] * math.exp(-(p['tox'] - tf) / (p['tox'] - p['tfilament_ref']))
    G0s.add(round(i0 / p['v_ref'], 15))
    if a.static == 'lin':
        out.append(f"R{m.group(1)} {m.group(2)} {m.group(3)} {p['v_ref'] / i0:.9e}")
    else:
        out.append(f"G{m.group(1)} {m.group(2)} {m.group(3)} CUR='{i0:.9e}*sinh(max(min(v({m.group(2)},{m.group(3)})/{p['v_ref']:.9e},40),-40))'")
    n_st += 1
# 측정 더하기 (회로는 그대로): verify 때 쓰는 셀 양단 전압 vc_<v0…>_<f|n> → 셀 G = i_<v…> / vc (parse 쪽에서). vn 은 이웃 셀 verify 라 뺌
ex = [f".meas tran vc_{nm}_{inst[0].lower()} find v({te},{be}) at={t:.5e}" for k, nm, t in meas_w if k == 'i' and nm != 'vn' for inst, te, be in kept]
if ex:
    i_end = max(i for i, l in enumerate(out) if l.lower().startswith('.meas')) + 1
    out[i_end:i_end] = ['* mk_write_2va: verify 때 쓰는 셀 양단 전압'] + ex
assert n_va == len(keep), f'VA 로 남길 셀 {sorted(keep)} 중 {n_va} 개만 찾음'
if a.bs:
    out = [l for l in out if not l.lower().startswith('.hdl')]
    i_sub = next(i for i, l in enumerate(out) if l.strip() and not l.startswith('*') and not l.lower().startswith(('.option', '.lib', '.include', '.temp', '.param', '+')))
    out[i_sub:i_sub] = bs_subckt(P)
if out[0].startswith('*'):
    out[0] += f' | 2va: VA {n_va} ({",".join(sorted(keep))}), other {n_st} RRAM = {a.static}'
Path(a.out).write_text('\n'.join(out) + '\n')
print(f"{a.out}: VA {n_va} {sorted(keep)}, {a.static} {n_st}, G0 = {', '.join(f'{g * 1e6:.4f} uS' for g in sorted(G0s))} (VA 기본값 {va})")

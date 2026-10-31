"""SKY130 5 V 소자 모형의 Monte Carlo (소자 부정합) 사본을 만든다 — 원본은 건드리지 않는다 (10/25 사용자 "모테카를로도 하긴 해야지").

SPICE 에서 소자마다 따로 흔들리게 하려고, 각 소자 subckt 안에 같은 이름의 .param 을
덱은 `.lib '<dst>/sky130_5v_tt_mc.lib.spice' tt` 뒤에 `.param mc_mm_switch=1` (끄려면 0) 을 둔다.
쓰임 (Olympus): python3 make_mc_models.py <src models 폴더> <dst 폴더> <원본 lib (ep_demo/char/models/sky130_5v_tt.lib.spice)>
"""
import re
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
NAMES = ('toxe', 'vth0', 'voff', 'nfactor')
for dev in ('nfet', 'pfet'):
    base = f'sky130_fd_pr__{dev}_g5v0d10v5'
    txt = (src / f'{base}__tt.pm3.spice').read_text()
    # SPICE 는 식 안의 agauss 를 받지 않는다 → 먼저 .param 으로 뽑고 곱한다
    local = ''.join(f".param mcr_{n} = agauss(0,1,1)\n.param {base}__{n}_slope_spectre = 'mc_mm_switch*mcr_{n}'\n" for n in NAMES)
    # subckt 머리의 '.param  l = 1 w = 1 ...' 줄 바로 뒤에 넣는다 (subckt 는 파일에 하나)
    pat = re.compile(r'(\.subckt\s+' + base + r'\s[^\n]*\n(?:\+[^\n]*\n)*\.param\s+l\s*=[^\n]*\n)')
    assert len(pat.findall(txt)) == 1, f'{base}: subckt 머리를 못 찾음'
    out = pat.sub(lambda m: m.group(1) + '* 소자 부정합 (make_mc_models.py): 인스턴스마다 agauss\n' + local, txt)
    # 같은 이름의 전역 .param (= 0.0) 을 지운다: SPICE 기본 parhier=global 이면 전역이 subckt 안 정의를 이긴다
    for n in NAMES:
        g = re.compile(r'^\.param\s+' + base + '__' + n + r'_slope_spectre\s*=\s*0\.0\s*$', re.M)
        assert len(g.findall(out)) == 1, f'{base} {n}: 전역 .param 이 하나가 아님'
        out = g.sub(f'* (make_mc_models.py) 전역 {n}_slope_spectre 지움 → subckt 안에서 정함', out)
    (dst / f'{base}__tt_mc.pm3.spice').write_text(out)
    cor = (src / f'{base}__tt.corner.spice').read_text()
    n_inc = len(re.findall(r'\.include\s+"[^"]*__tt\.pm3\.spice"', cor))
    assert n_inc == 1, f'{base}: corner 의 pm3 include {n_inc} 개'
    cor = re.sub(r'\.include\s+"[^"]*__tt\.pm3\.spice"', f'.include "{dst}/{base}__tt_mc.pm3.spice"', cor)
    (dst / f'{base}__tt_mc.corner.spice').write_text(cor)
# lib: 원본 lib (argv[3]) 를 그대로 옮기고 tt corner include 2 줄만 사본으로, mc_mm_switch 줄은 뺌 (덱에서 정함)
lib = ["* make_mc_models.py: 아래 원본 lib 와 같고 nfet·pfet 5 V pm3 만 부정합 사본. mc_mm_switch 는 덱에서 정한다"]
for ln in Path(sys.argv[3]).read_text().splitlines():
    if re.match(r'\.param\s+mc_mm_switch', ln):
        continue
    for dev in ('nfet', 'pfet'):
        base = f'sky130_fd_pr__{dev}_g5v0d10v5'
        if re.search(base + r'__tt\.corner\.spice', ln):
            ln = f'.include "{dst}/{base}__tt_mc.corner.spice"'
    lib.append(ln)
assert sum('_tt_mc.corner' in ln for ln in lib) == 2
(dst / 'sky130_5v_tt_mc.lib.spice').write_text('\n'.join(lib) + '\n')
print('written', sorted(p.name for p in dst.iterdir()))

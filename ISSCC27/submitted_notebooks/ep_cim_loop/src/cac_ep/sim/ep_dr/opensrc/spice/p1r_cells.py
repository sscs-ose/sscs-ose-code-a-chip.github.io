"""1R (ReRAM 단독) 쓰기 격자 SPICE 덱 (ep_demo/char/decks/p1r_pw*.sp, `.data` sweep) → ngspice·VACASK 덱.
SPICE 는 `.data` 행마다 따로 푼다 → 여기서는 행마다 같은 회로를 한 덱 안에 따로 (서로 이어지지 않음) 둔다. 회로·펄스·측정 시각은 그대로:
  Vte ─ Rd1 (1 mΩ) ─ Vsns ─ te ─[ReRAM]─ be ─ Rd2 ─ Vbe,  SET = te 에 +V, RESET = be 에 +V, 쓰기 뒤 te 0.1 V 로 읽음 (ird).
ReRAM = OpenVAF 로 컴파일한 .osdi (ngspice: N 소자 + .model, `pre_osdi` 는 .spiceinit / VACASK: load).
Tfilament_0 는 모형 parameter (instance 아님) → tf0 값마다 .model 하나.
쓰임: python p1r_cells.py <SPICE p1r 덱> <outdir> <osdi 파일 이름> [행 수 (기본 전부)]
  → <outdir>/p1r_ng.cir, <outdir>/p1r_vc.sim, <outdir>/rows.json"""
import json
import re
import sys
from pathlib import Path

src, out, osdi = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
nmax = int(sys.argv[4]) if len(sys.argv) > 4 else None
txt = src.read_text()
out.mkdir(parents=True, exist_ok=True)
tstep = float(re.search(r'^\.param tstep=(\S+)', txt, re.M).group(1))
pw = re.search(r'^Vte tes 0 PWL\((.*)\)$', txt, re.M).group(1).split()
pb = re.search(r'^Vbe bes 0 PWL\((.*)\)$', txt, re.M).group(1).split()
meas = {m.group(1): m.group(0) for m in re.finditer(r'^\.measure tran (ird|vrd|iwmax|vwmax) .*$', txt, re.M)}
t_rd = float(re.search(r'ird find i\(vsns\) at=(\S+)', meas['ird']).group(1))
t0, t1 = [float(x) for x in re.search(r'iwmax max .* from=(\S+) to=(\S+)', meas['iwmax']).groups()]
tend = float(re.search(r'^\.tran \S+ (\S+)', txt, re.M).group(1))
data = re.search(r'^\.data dw\n\+ tf0 vte vbe\n(.*?)^\.enddata', txt, re.M | re.S).group(1)
rows = [tuple(float(v) for v in l[1:].split()) for l in data.strip().splitlines()]
if nmax:
    rows = rows[:nmax]
tfs = sorted({r[0] for r in rows})


def wave(p, val):
    return [(float(p[i]), val if p[i + 1] in ('vte', 'vbe') else float(p[i + 1])) for i in range(0, len(p), 2)]


ng = [f"* {src.stem}: ngspice + OSDI, {len(rows)} 행 ({src.name} 의 .data 를 회로로 펼침)",
      ".options reltol=1e-4 abstol=1e-15 vntol=1e-10 method=gear", ".temp 27", ".options tnom=25"]
vc = [f"{src.stem}: VACASK + OSDI, {len(rows)} rows",          # 제목은 ASCII (vacask rawfile.py 가 ascii 로 읽음) f'load "{osdi}"', 'load "resistor.osdi"',
      "model vsource vsource", "model r resistor"]
for j, tf in enumerate(tfs):
    ng.append(f".model rr{j} sky130_fd_pr_reram__reram_cell Tfilament_0={tf:.6e} t_step={tstep:g}")
    vc.append(f"model rr{j} sky130_fd_pr_reram__reram_cell tfilament_0={tf:.6e} t_step={tstep:g}")   # VACASK: OSDI parameter 이름은 소문자
for k, (tf, vte, vbe) in enumerate(rows):
    j = tfs.index(tf)
    wt, wb = wave(pw, vte), wave(pb, vbe)
    ng += [f"Vte{k} tes{k} 0 PWL(" + " ".join(f"{t:.4e} {v:g}" for t, v in wt) + ")",
           f"Vbe{k} bes{k} 0 PWL(" + " ".join(f"{t:.4e} {v:g}" for t, v in wb) + ")",
           f"Rd1_{k} tes{k} te1_{k} 0.001", f"Vsns{k} te1_{k} te{k} 0", f"Nr{k} te{k} be{k} rr{j}", f"Rd2_{k} be{k} bes{k} 0.001",
           f".meas tran ird_{k} find i(vsns{k}) at={t_rd:.4e}",
           f".meas tran imx_{k} max i(vsns{k}) from={t0:.4e} to={t1:.4e}",
           f".meas tran imn_{k} min i(vsns{k}) from={t0:.4e} to={t1:.4e}"]
    vc += [f"vte{k} (tes{k} 0) vsource type=\"pwl\" wave=[" + ", ".join(f"{t:.4e}, {v:g}" for t, v in wt) + "]",
           f"vbe{k} (bes{k} 0) vsource type=\"pwl\" wave=[" + ", ".join(f"{t:.4e}, {v:g}" for t, v in wb) + "]",
           f"rd1_{k} (tes{k} te1_{k}) r r=0.001", f"vsns{k} (te1_{k} te{k}) vsource dc=0", f"xr{k} (te{k} be{k}) rr{j}",
           f"rd2_{k} (be{k} bes{k}) r r=0.001"]
ng += [f".tran 10p {tend:.4e}", ".end"]
vc += ["control", "  options tnom=25 temp=27",
       "  save " + " ".join(f"i(vsns{k})" for k in range(len(rows))),
       f"  analysis tran1 tran step=10p stop={tend:.4e} maxstep={tstep:g}", "endc"]
(out / 'p1r_ng.cir').write_text('\n'.join(ng) + '\n')
(out / 'p1r_vc.sim').write_text('\n'.join(vc) + '\n')
json.dump(dict(src=str(src), rows=rows, t_rd=t_rd, t0=t0, t1=t1, tend=tend, tstep=tstep), open(out / 'rows.json', 'w'))
print(out, len(rows), 'rows,', len(tfs), 'tf0 values, t_rd', t_rd, 'tend', tend)

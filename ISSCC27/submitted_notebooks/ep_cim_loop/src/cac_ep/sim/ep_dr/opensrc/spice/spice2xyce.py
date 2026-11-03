"""SPICE 덱 → Xyce 덱 (회로는 그대로, 문법만). 따옴표 식 'a*b' → {a*b}, .option 줄 버림, .temp → .options device temp,
SPICE 기본 TNOM 25 (Xyce 기본 27) → tnom=25. `G… CUR='식'` (RRAM 셀) → `B… I={식}`. .lib/.include 파일은 모두 같은 규칙 + 줄 끝 `$ 주석` 지우기 (Xyce 는 `0.0 $ All devices` 를
식 `{0.0$Alldevices}` 로 읽어 실패) 로 바꾼 사본을 <outdir>/inc/ 에 만들어 그쪽을 부른다 (값은 그대로). Xyce 는 `-hspice-ext all` 로 돌린다
(`.option scale=1.0u`, `.lib` 절 등). 환경 NF2M=0 이면 nf→m 바꿈을 끈다 (아래 nf2m).
쓰임: python spice2xyce.py <in.sp> <out.cir> [RELTOL] ["추가 .options 줄 (Xyce 문법)"]"""
import re
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
rt = sys.argv[3] if len(sys.argv) > 3 else '1e-4'
import os
NF2M_ENV = os.environ.get('NF2M', '1') == '1'
extra = sys.argv[4] if len(sys.argv) > 4 else ''
out_dir = dst.parent


def unq(l):
    return re.sub(r"'([^']*)'", r"{\1}", l)


NF2M = True


def nf2m(l):
    """sky130 fet 의 nf>1 → w=W/nf, nf=1, m=nf (X 줄 배수). Xyce 7.10 은 bin 을 전체 W 로 골라 (SPICE 는 손가락 폭 W/nf 로 고르는 것으로 보임 — 이렇게 바꾸면 WU 블록 전력이 SPICE 와 같아짐)
    (w=1000 nf=200 은 "no valid model card", w=3.6 nf=4 는 다른 bin) 같은 소자가 다른 모형 값을 쓴다. ad·as=0 이 넘어가 접합 면적 차이는 없음."""
    if not NF2M_ENV or not re.match(r'^X\S+ .*sky130_fd_pr__[np]fet\S* ', l, re.I):
        return l
    mw = re.search(r'\bw=([0-9.eE+-]+)\b', l); mn = re.search(r'\bnf=([0-9.]+)\b', l)
    if not (mw and mn) or float(mn.group(1)) <= 1:
        return l
    nf = float(mn.group(1)); w = float(mw.group(1)) / nf
    l = re.sub(r'\bw=[0-9.eE+-]+\b', f'w={w:g}', l); l = re.sub(r'\bnf=[0-9.]+\b', 'nf=1', l)
    return l + f' m={nf:g}'


def conv_file(f):
    f = Path(f)
    cp = out_dir / 'inc' / (f.parent.name + '__' + f.name)
    if not cp.exists():
        cp.parent.mkdir(exist_ok=True)
        cp.write_text('\n'.join(conv_lines(f.read_text().splitlines(), False)[0]) + '\n')
    return str(cp)


def conv_lines(lines, top):
    out, temp = [], None
    for l in lines:
        s = l.strip()
        low = s.lower()
        if low.startswith('.option'):
            m = re.match(r'\.options?\s+scale\s*=\s*(\S+)', low)            # 모형 파일의 .option scale = 1.0u → Xyce PARSER SCALE
            if m:
                out.append(f".options parser scale={m.group(1).replace('u', 'e-6')}")
            continue
        if low.startswith('.temp'):
            temp = s.split()[1]
            continue
        if low.startswith('.lib ') or low.startswith('.include ') or low.startswith('.inc '):
            parts = s.split()
            if len(parts) > 1 and (Path(parts[1].strip("'\"")).is_file()):
                out.append(' '.join([parts[0], conv_file(parts[1].strip("'\""))] + parts[2:]))
                continue
        if s.startswith('*'):
            out.append(l)
            continue
        l = re.sub(r'\s\$.*$', '', l)                                         # 줄 끝 $ 주석
        m = re.match(r"^G(\S+) (\S+) (\S+) CUR='(.*)'$", l)                  # SPICE 식 VCCS (RRAM 셀 sinh) → Xyce B 소스
        if m:
            l = f"B{m.group(1)} {m.group(2)} {m.group(3)} I={{{m.group(4)}}}"
            out.append(l)
            continue
        out.append(nf2m(unq(l)))
    return out, temp


L, temp = conv_lines(src.read_text().splitlines(), True)
hdr = [f".options timeint method=gear reltol={rt}", f".options device tnom=25" + (f" temp={temp}" if temp else ''),
       ".options parser model_binning=true"]                              # sky130 모형은 bin (.model x.0 … x.87) → Xyce 는 켜야 고름
if extra:
    hdr.append(extra)
dst.write_text('\n'.join(L[:1] + hdr + L[1:]) + '\n')
print(dst, len(L), 'lines, reltol', rt, 'temp', temp)

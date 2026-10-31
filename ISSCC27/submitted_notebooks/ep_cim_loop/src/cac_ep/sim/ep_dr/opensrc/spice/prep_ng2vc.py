"""ngspice 덱을 VACASK 변환기 (vacask.ng2vc) 에 넣기 전 손질: .lib/.include 파일을 <outdir>/inc/ 로 복사하며
`level = 54.0` → `level = 54` (ng2vc 가 정수만 받음, 10/28 ValueError), 경로를 사본으로 바꿈, `.lib 파일 절` 은 그 절 내용을 펼침. 값은 그대로.
쓰임: python prep_ng2vc.py <in.cir> <out.cir>"""
import re
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
inc = dst.parent / 'inc'; inc.mkdir(parents=True, exist_ok=True)
done = {}


def conv(lines):
    out = []
    for l in lines:
        ml = re.match(r'^\s*\.lib\s+(\S+)\s+(\w+)\s*$', l, re.I)          # `.lib 파일 절` → 그 절의 내용을 그 자리에 (ng2vc 가 절 안 subckt bin 을 못 찾음)
        if ml and Path(ml.group(1).strip('\'"')).is_file():
            body = Path(ml.group(1).strip('\'"')).read_text().splitlines()
            sec = ml.group(2).lower()
            i0 = [i for i, x in enumerate(body) if re.match(rf'^\s*\.lib\s+{sec}\s*$', x, re.I)][0]
            i1 = [i for i, x in enumerate(body) if re.match(rf'^\s*\.endl\b', x, re.I) and i > i0][0]
            out += conv(body[i0 + 1:i1])
            continue
        m = re.match(r'^\s*\.(lib|include|inc)\s+(\S+)(.*)$', l, re.I)
        if m and Path(m.group(2).strip('\'"')).is_file():
            f = Path(m.group(2).strip('\'"'))
            if f not in done:
                cp = inc / f"{f.parent.name}__{f.name}"; done[f] = cp
                cp.write_text('\n'.join(conv(f.read_text().splitlines())) + '\n')
            l = f".{m.group(1)} {done[f]}{m.group(3)}"
        l = re.sub(r'\blevel\s*=\s*(\d+)\.0\b', r'level = \1', l, flags=re.I)
        out.append(l)
    return out


dst.write_text('\n'.join(conv(src.read_text().splitlines())) + '\n')
print(dst, 'includes copied:', len(done))

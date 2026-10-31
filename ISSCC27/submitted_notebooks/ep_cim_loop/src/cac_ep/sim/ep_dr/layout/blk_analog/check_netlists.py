"""LVS 기준 CDL (out/*.cdl) 이 SPICE 덱 소자와 같은지 확인 (10/28) — 생성기의 CDL 은 손으로 옮긴 것이라, 옮기다 틀리면 LVS 가 MATCH 여도 회로가 다르다.
덱 쪽은 원본 함수·줄에서 바로 만든다: real_circuit/chip_lib.py (WBUF, beta_mirror), wu_lib.primitives() (NAND2·INV·TG),
gen_chip_deck3.py 의 입력 구동·주입기 줄 (같은 식을 circuit.Layout 로 다시 계산), hog_tr.spice 의 HOG_BIAS.
비교: 소자마다 (형, W, L, 게이트 넷, {S, D} 넷, body) 의 다중집합. 내부 넷 이름은 맞춤표로 바꾼다.
W 는 그리기 격자 (5 nm) 로 맞춘 값 차이를 따로 표시 (bias_beta 의 m=8 단위 소자).
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python check_netlists.py
"""
import re
import sys
from collections import Counter
from pathlib import Path

H = Path(__file__).resolve().parent
EP = H.parents[1]
sys.path.insert(0, str(EP)); sys.path.insert(0, str(EP / 'real_circuit'))
import chip_lib                                                     # noqa: E402
import wu_lib                                                       # noqa: E402
from circuit import Layout                                          # noqa: E402

HOG = Path('/home/dave/work/projects/sern_hog_classab_opamp/sim/char/decks/hog_tr.spice')


def parse_subckts(lines):
    subs, cur = {}, None
    for ln in lines:
        t = ln.split()
        if not t:
            continue
        if t[0].lower() == '.subckt':
            cur = t[1]; subs[cur] = dict(ports=t[2:], body=[])
        elif t[0].lower().startswith('.ends'):
            cur = None
        elif cur:
            subs[cur]['body'].append(ln)
    return subs


def kv(t):
    return {k.lower(): v for k, v in (x.split('=') for x in t if '=' in x)}


def num(v):
    return float(re.sub(r'u$', '', v))


def flatten(subs, name, conn, pre=''):
    """subckt name 을 conn (포트 → 넷) 으로 펼침. 반환 [(형, W, L, g, frozenset(s,d), b)]."""
    s = subs[name]; m = dict(zip(s['ports'], conn))
    net = lambda n: m.get(n, n if n in ('0', 'vdd', 'vss') else f'{pre}{n}')
    out = []
    for ln in s['body']:
        t = ln.split()
        nodes = [x for x in t[1:] if '=' not in x]
        if t[0][0] in 'Xx' and nodes[-1].startswith('sky130_fd_pr__'):
            d, g, so, b = map(net, nodes[:4]); p = kv(t)
            typ = 'n' if 'nfet' in nodes[-1] else 'p'
            mult = int(p.get('m', 1))
            out.append((typ, round(num(p['w']) * mult, 4), num(p['l']), g, frozenset((so, d)), b))
        elif t[0][0] in 'Xx':
            out += flatten(subs, nodes[-1], [net(x) for x in nodes[:-1]], pre=f'{pre}{t[0]}.')
    return out


def read_cdl(path):
    out = []
    for ln in Path(path).read_text().splitlines():
        t = ln.split()
        if t and t[0][0] == 'M':
            d, g, s, b, model = t[1:6]; p = kv(t)
            out.append(('n' if 'nfet' in model else 'p', round(num(p['w']), 4), num(p['l']), g, frozenset((s, d)), b))
    return out


def merge(devs):
    """같은 (형, L, g, {S,D}, b) 병렬 소자는 W 를 더함 (LVS 병렬 축약과 같게)."""
    acc = Counter()
    for typ, w, l, g, sd, b in devs:
        acc[(typ, l, g, sd, b)] += w
    return {k: round(v, 4) for k, v in acc.items()}


def compare(tag, ref, lay, ren=None, tol=0.0):
    ren = ren or {}
    rn = lambda n: ren.get(n, n)
    ref = [(t, w, l, rn(g), frozenset(map(rn, sd)), rn(b)) for t, w, l, g, sd, b in ref]
    a, b = merge(ref), merge(lay)
    bad = []
    for k in set(a) | set(b):
        wa, wb = a.get(k), b.get(k)
        if wa is None or wb is None or abs(wa - wb) > tol * max(wa, wb) + 1e-9:
            bad.append((k, wa, wb))
    dev = [(k, a[k], b[k], f'{(b[k] - a[k]) / a[k] * 100:+.2f} %') for k in a if k in b and abs(a[k] - b[k]) > 1e-9]
    print(f"{tag}: 덱 {len(ref)} 소자 → 병렬 축약 {len(a)}, CDL {len(lay)} → {len(b)}, 다른 것 {len(bad)}")
    for x in bad[:12]:
        print('   ', x)
    for x in dev:
        print('    W 차이 (격자):', x)
    return not bad


def main():
    lib = wu_lib.primitives() + chip_lib.lib()
    lines = [ln.replace('{NF}', chip_lib.NF) for ln in lib]
    subs = parse_subckts(lines)
    ok = True
    # ── write buffer
    ref = flatten(subs, 'WBUF', ['wp', 'pol', 'out', 'vwh', 'vwl', 'vdd', 'vss'])
    ren = {'XN1.n1': 's1', 'XN2.n1': 's2', 'XN3.n1': 's3', 'XN4.n1': 's4'}
    ok &= compare('wbuf', ref, read_cdl(H / 'out' / 'wbuf.cdl'), ren)
    # ── bias_beta: beta_mirror() + HOG_BIAS (Vbm_p·Vbm_n 0 V 전압원 = 단락: pm_d → pref, nm_d → nref)
    bm = [ln for ln in chip_lib.beta_mirror() if ln.split()[0][0] in 'Xx']
    hog = parse_subckts(HOG.read_text().splitlines())
    subs2 = dict(BM=dict(ports=[], body=bm), HB=dict(ports=hog['HOG_BIAS']['ports'], body=[ln for ln in hog['HOG_BIAS']['body'] if ln.split()[0][0] in 'Xx']))
    ref = flatten(subs2, 'BM', []) + flatten(subs2, 'HB', ['vbn', 'vbp', 'vbpc', 'vdd', 'vss'], pre='')
    ren = {'pm_d': 'pref', 'nm_d': 'nref'}
    ok &= compare('bias_beta', ref, read_cdl(H / 'out' / 'bias_beta.cdl'), ren, tol=0.003)
    # ── nudge_inj: 덱 줄 (j = 0…2), yp/ym = nr{r_y[2j]} / nr{r_y[2j+1]}
    LAY = Layout(n_in=49, n_hid=30, n_out=3, rows=128, cols=64, stab=False)
    NF, PF = chip_lib.NF, chip_lib.PF
    L = []
    for j in range(LAY.n_out):
        yp, ym = f'nr{LAY.r_y[2 * j]}', f'nr{LAY.r_y[2 * j + 1]}'
        L += [f"XMP{j} ip{j} pref vdd vdd {PF} w=42 l=2 nf=8", f"XMN{j} in{j} nref vss vss {NF} w=15 l=2 nf=3",
              f"XSW1_{j} ip{j} {yp} sp{j} spb{j} vdd vss TG", f"XSW2_{j} ip{j} {ym} sm{j} smb{j} vdd vss TG",
              f"XSW3_{j} in{j} {ym} sp{j} spb{j} vdd vss TG", f"XSW4_{j} in{j} {yp} sm{j} smb{j} vdd vss TG"]
    subs3 = dict(subs, INJ=dict(ports=[], body=L))
    ref = flatten(subs3, 'INJ', [])
    ren = {f'nr{LAY.r_y[2 * j]}': f'yp{j}' for j in range(3)}
    ren.update({f'nr{LAY.r_y[2 * j + 1]}': f'ym{j}' for j in range(3)})
    ok &= compare('nudge_inj', ref, read_cdl(H / 'out' / 'nudge_inj.cdl'), ren)
    # ── input_drive: gen_chip_deck3.py 의 입력 구동 레일 줄 (p 접두 없이, rn(r) = row_r)
    L = []
    for i in range(LAY.n_in):
        for r, gu, gd in ((LAY.r_x[2 * i], f'ga{i}', f'gb{i}'), (LAY.r_x[2 * i + 1], f'gb{i}', f'ga{i}')):
            L += [f"XDp{r} row_{r} {gu} vrailp vss {NF} w=1000 l=0.5 nf=200", f"XDm{r} row_{r} {gd} vrailm vss {NF} w=1000 l=0.5 nf=200"]
    for r, rail in ((LAY.r_b[0], 'vrailp'), (LAY.r_b[1], 'vrailm')):
        L.append(f"XDb{r} row_{r} READ {rail} vss {NF} w=1000 l=0.5 nf=200")
    ref = flatten(dict(ID=dict(ports=[], body=L)), 'ID', [])
    ok &= compare('input_drive', ref, read_cdl(H / 'out' / 'input_drive.cdl'))
    print('모두 같음' if ok else '다른 것 있음')


if __name__ == '__main__':
    main()

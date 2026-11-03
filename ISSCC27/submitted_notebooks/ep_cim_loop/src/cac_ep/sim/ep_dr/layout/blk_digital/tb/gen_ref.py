#!/usr/bin/env python3
"""SPICE 검증 netlist (real_circuit/chip_lib.py·wu_lib.py, gen_chip_deck3.py 의 DATA 줄) → Verilog 기준 모형 두 개.
  tb/ref_data_blk.v : DATA 레지스터·latch·입력 구동 게이트·nudge SW 게이트 (gen_chip_deck3.py 「레지스터」·「입력 구동 게이트」·「nudge 주입기 SW」 줄)
  tb/ref_glob_dig.v : chip_lib.global_decode() + config_block(buf=True) (설정 레지스터·latch·decode·클록 gating + CKBUF)
RTL (rtl/*.v) 과 따로 만든 모형 → testbench 가 둘을 맞대 보면 RTL 이 SPICE 로 검증한 트랜지스터 netlist 의 논리와 같은지 확인된다.

옮기는 법 (줄 하나 = 인스턴스 하나):
  NAND2·NOR2·INV → Verilog nand·nor·not.  CKBUF → subckt 줄 그대로 (INV 1 + PMOS·NMOS 짝 3 = inverter 3) 를 not 4 개로.
  DFFR·DLATCH (TG 로 만든 저장 소자) → 행동 모형 ref_dffr (상승 에지, rst 높음 = 비동기 0) · ref_dlatch (clk 높음 = 투명).
  이 두 행동 모형이 트랜지스터 netlist 와 같은지는 아래 check_seq() 가 subckt 줄을 스위치 수준 (TG = clk 에 따라 a → b, 안 켜진 node 는 값 유지)
  으로 정상 상태까지 풀어서 확인한다 (무작위 입력 열 2,000 단계). 어긋나면 파일을 만들지 않고 멈춘다.
DATA 줄: gen_chip_deck3.py 는 import 하면 덱 전체를 만들므로 (torch·가중치 필요) 그 반복문 세 개를 아래 data_lines() 에 그대로 옮겼다
  (LAY.n_in = 49, LAY.n_out = 3: train.py LAY_NS = Layout(n_in=49, n_hid=30, n_out=3)). 원본 줄은 docstring 에 적었다.
real_circuit/ 은 읽기만 한다 (python -B).
쓰임: python3 -B tb/gen_ref.py
"""
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
H = Path(__file__).resolve().parent
RC = H.parents[2] / 'real_circuit'                        # ep_dr/real_circuit
sys.path.insert(0, str(RC))
import chip_lib                                            # noqa: E402
import wu_lib                                              # noqa: E402

N_IN, N_OUT = 49, 3
SUPPLY = {'vdd', 'vss'}


def subckts():
    """subckt 이름 → (포트, 본문 줄). wu_lib.primitives() 와 chip_lib 의 DFFR·CKBUF."""
    S, cur = {}, None
    for ln in wu_lib.primitives() + chip_lib.DFFR + chip_lib.CKBUF:
        t = ln.split()
        if t[0].lower() == '.subckt':
            cur = t[1]; S[cur] = (t[2:], [])
        elif t[0].lower() == '.ends':
            cur = None
        elif cur:
            S[cur][1].append(ln)
    return S


SUB = subckts()
GATE = {'INV': ('not', 1), 'NAND2': ('nand', 2), 'NOR2': ('nor', 2)}


def mos_inverters(body):
    """CKBUF 본문의 PMOS·NMOS 짝 (같은 drain·gate, source = vdd / vss) → (입력, 출력) inverter 목록. 짝이 안 맞으면 멈춤."""
    P, N, inv = {}, {}, []
    for ln in body:
        t = ln.split()
        if t[-1] in SUB:                                   # 하위 subckt (INV)
            assert t[-1] == 'INV', ln
            inv.append((t[1], t[2])); continue
        name, d, g, s, b, model = t[:6]
        if 'pfet' in model:
            assert s == 'vdd' and b == 'vdd', ln; P[(d, g)] = ln
        else:
            assert 'nfet' in model and s == 'vss' and b == 'vss', ln; N[(d, g)] = ln
    assert P.keys() == N.keys(), (P.keys(), N.keys())
    inv += [(g, d) for d, g in P]
    return inv


# ── 스위치 수준 정상 상태 풀이 (DFFR·DLATCH 확인용)
def flat(name, conn):
    """subckt 하나를 기본 소자 목록으로: ('g', 종류, 입력들, 출력) / ('tg', a, b, en, enb). conn = 포트 → 바깥 node."""
    ports, body = SUB[name]
    out = []
    for ln in body:
        t = ln.split()
        cell = t[-1]
        nodes = [conn.get(x, f'{name}.{x}') if x not in SUPPLY else x for x in t[1:-1]]
        if cell in GATE:
            k = GATE[cell][1]
            assert nodes[k + 1:k + 3] == ['vdd', 'vss'], ln
            out.append(('g', cell, nodes[:k], nodes[k]))
        elif cell == 'TG':
            out.append(('tg', *nodes[:4]))
        else:
            raise ValueError(ln)
    return out


def solve(prims, val):
    """val: node → 0/1 (입력 + 이전 상태). 게이트·켜진 TG 를 고정점까지 되풀이. 켜진 TG 가 없는 node 는 값 유지 (저장)."""
    for _ in range(100):
        new = dict(val)
        for p in prims:
            if p[0] == 'g':
                a = [val.get(x) for x in p[2]]
                if None in a:
                    new[p[3]] = None; continue
                y = {'INV': lambda v: 1 - v[0], 'NAND2': lambda v: 1 - (v[0] & v[1]), 'NOR2': lambda v: 1 - (v[0] | v[1])}[p[1]](a)
                new[p[3]] = y
        drv = {}
        for p in prims:
            if p[0] == 'tg':
                _, a, b, en, enb = p
                if val.get(en) == 1 and val.get(enb) == 0:     # en·enb 가 아직 반대가 아니면 (clkb 가 한 번 늦음) 꺼진 것으로 = 겹침 없는 클록
                    drv.setdefault(b, set()).add(val.get(a))
        for b, vs in drv.items():
            assert len(vs) == 1, f'{b} 를 다른 값으로 둘 이상이 구동 {vs}'
            new[b] = vs.pop()
        if new == val:
            for p in prims:
                if p[0] == 'tg':
                    assert val.get(p[3]) is not None and val.get(p[3]) != val.get(p[4]), f'TG {p[1]}->{p[2]}: en·enb 가 반대가 아님'
            return val
        val = new
    raise RuntimeError('정상 상태로 수렴하지 않음 (발진)')


def check_seq(n=2000, seed=1):
    """DFFR: 상승 에지에서 d, rst 높음이면 비동기 0. DLATCH: clk 높음이면 q = d (qb = 반대), 낮음이면 유지."""
    rnd = random.Random(seed)
    P = flat('DFFR', {p: p for p in SUB['DFFR'][0]})
    v = {'d': 0, 'clk': 0, 'rst': 1, 'rstb': 0}
    v = solve(P, v)
    ref_q, clk_prev, nchk = 0, 0, 0
    for _ in range(n):
        kind = rnd.random()
        if kind < 0.4:
            v['clk'] = 1 - v['clk']
        elif kind < 0.9:
            v['d'] = rnd.randint(0, 1)
        else:
            v['rst'] = int(rnd.random() < 0.3); v['rstb'] = 1 - v['rst']
        v = solve(P, v)
        if v['rst']:
            ref_q = 0
        elif v['clk'] == 1 and clk_prev == 0:
            ref_q = v['d']
        clk_prev = v['clk']
        assert v['q'] == ref_q, f'DFFR q {v["q"]} 기대 {ref_q} ({v})'
        nchk += 1
    L = flat('DLATCH', {p: p for p in SUB['DLATCH'][0]})
    v = solve(L, {'d': 0, 'clk': 1, 'clkb': 0})
    ref = 0
    for _ in range(n):
        if rnd.random() < 0.4:
            v['clk'] = 1 - v['clk']; v['clkb'] = 1 - v['clk']
        else:
            v['d'] = rnd.randint(0, 1)
        v = solve(L, v)
        if v['clk']:
            ref = v['d']
        assert v['q'] == ref and v['qb'] == 1 - ref, f'DLATCH {v}'
        nchk += 1
    a = 0
    inv = mos_inverters(SUB['CKBUF'][1])
    for a in (0, 1, 0, 1):                                 # CKBUF: y = a (반전 짝수 번)
        val = {'a': a}
        for _ in range(len(inv) + 1):
            for i, o in inv:
                if i in val:
                    val[o] = 1 - val[i]
        assert val['y'] == a, ('CKBUF', a, val)
    return nchk, len(inv)


# ── 덱 줄 → Verilog
def data_lines():
    """gen_chip_deck3.py 의 세 반복문 (원본):
    prev = 'sdi'
    for k in range(LAY.n_in + LAY.n_out):                             # DATA: q_k = bits[k], latch 투명 = DLOAD
        L += [f"XFd{k} {prev} data_clk rst rstb dq{k} vdd vss DFFR", f"XLd{k} dq{k} dload dload_b dl{k} dlb{k} vdd vss DLATCH"]
        prev = f'dq{k}'
    for i in range(LAY.n_in):                                         # 입력 구동 게이트 (공유): a_i = READ·D_i, b_i = READ·D̄_i
        L += and2('READ', f'dl{i}', f'ga{i}', f'gab{i}', f'g{i}a') + and2('READ', f'dlb{i}', f'gb{i}', f'gbb{i}', f'g{i}b')
    for k in range(LAY.n_out):                                        # nudge 주입기 SW: SW1·SW3 = READ·Din, SW2·SW4 = READ·D̄in
        L += and2('READ', f'dl{LAY.n_in + k}', f'sp{k}', f'spb{k}', f'n{k}p') + and2('READ', f'dlb{LAY.n_in + k}', f'sm{k}', f'smb{k}', f'n{k}m')
    """
    and2 = chip_lib.and2
    L = []
    prev = 'sdi'
    for k in range(N_IN + N_OUT):
        L += [f"XFd{k} {prev} data_clk rst rstb dq{k} vdd vss DFFR", f"XLd{k} dq{k} dload dload_b dl{k} dlb{k} vdd vss DLATCH"]
        prev = f'dq{k}'
    for i in range(N_IN):
        L += and2('READ', f'dl{i}', f'ga{i}', f'gab{i}', f'g{i}a') + and2('READ', f'dlb{i}', f'gb{i}', f'gbb{i}', f'g{i}b')
    for k in range(N_OUT):
        L += and2('READ', f'dl{N_IN + k}', f'sp{k}', f'spb{k}', f'n{k}p') + and2('READ', f'dlb{N_IN + k}', f'sm{k}', f'smb{k}', f'n{k}m')
    return L


def to_verilog(mod, lines, ins, outs):
    drv, body = {}, []
    for ln in lines:
        t = ln.split()
        name, cell, nodes = t[0], t[-1], t[1:-1]
        assert nodes[-2:] == ['vdd', 'vss'], ln
        nodes = nodes[:-2]
        if cell in GATE:
            prim, k = GATE[cell]
            a, y = nodes[:k], nodes[k]
            body.append(f'    {prim} {name} ({y}, {", ".join(a)});'); outs_ = [y]
        elif cell == 'DFFR':
            d, clk, rst, rstb, q = nodes
            body.append(f'    ref_dffr {name} (.d({d}), .clk({clk}), .rst({rst}), .rstb({rstb}), .q({q}));'); outs_ = [q]
        elif cell == 'DLATCH':
            d, clk, clkb, q, qb = nodes
            body.append(f'    ref_dlatch {name} (.d({d}), .clk({clk}), .clkb({clkb}), .q({q}), .qb({qb}));'); outs_ = [q, qb]
        elif cell == 'CKBUF':
            a, y = nodes
            body.append(f'    ref_ckbuf {name} (.a({a}), .y({y}));'); outs_ = [y]
        else:
            raise ValueError(ln)
        for y in outs_:
            assert y not in drv and y not in ins, f'{y} 를 두 번 구동: {ln}'
            drv[y] = ln
    used = set()
    for b in body:
        inner = b[b.index('(') + 1:b.rindex(')')]
        used |= {x.split('(')[-1].rstrip(')') for x in inner.replace(' ', '').split(',')}
    for o in outs:
        assert o in drv, f'{mod}: 출력 {o} 를 구동하는 소자가 없음'
    internal = sorted(used - set(ins) - set(outs))
    for n in internal:
        assert n in drv, f'{mod}: 내부 node {n} 이 떠 있음'
    low = {}
    for n in used | set(ins) | set(outs):                  # SPICE 는 대소문자를 가리지 않음 → Verilog 에서 둘로 갈리면 안 됨
        assert low.setdefault(n.lower(), n) == n, f'대소문자만 다른 node: {n} / {low[n.lower()]}'
    v = [f'module {mod} ({", ".join(ins + outs)});', f'    input {", ".join(ins)};', f'    output {", ".join(outs)};']
    v += [f'    wire {", ".join(internal[i:i + 16])};' for i in range(0, len(internal), 16)]
    return v + body + ['endmodule', ''], len(body)


def ckbuf_module():
    inv = mos_inverters(SUB['CKBUF'][1])
    nodes = sorted({n for p in inv for n in p} - {'a', 'y'})
    v = ['module ref_ckbuf (a, y);', '    input a;', '    output y;', f'    wire {", ".join(nodes)};']
    v += [f'    not ({o}, {i});' for i, o in inv]
    return v + ['endmodule', '']


BEH = ['// 행동 모형 (check_seq 로 subckt 줄과 맞춤): DFFR = 상승 에지, rst 높음 → 비동기 0. rstb 는 rst 의 반대로만 쓰인다',
       'module ref_dffr (d, clk, rst, rstb, q);', '    input d, clk, rst, rstb;', '    output reg q;',
       '    always @(posedge clk or posedge rst) if (rst) q <= 1\'b0; else q <= d;', 'endmodule', '',
       '// DLATCH = clk 높음 (clkb 낮음) 이면 투명 q = d, qb = ~d. 낮으면 유지 (원본은 동적 latch: TG + INV 2)',
       'module ref_dlatch (d, clk, clkb, q, qb);', '    input d, clk, clkb;', '    output reg q;', '    output qb;',
       '    always @(*) if (clk) q = d;', '    assign qb = ~q;', 'endmodule', '']

if __name__ == '__main__':
    nchk, ninv = check_seq()
    hdr = '// {} — GENERATED by tb/gen_ref.py from real_circuit/chip_lib.py·wu_lib.py{} (손으로 고치지 말 것)'
    D_IN = ['sdi', 'data_clk', 'dload', 'dload_b', 'READ', 'rst', 'rstb']
    D_OUT = ([f'ga{i}' for i in range(N_IN)] + [f'gb{i}' for i in range(N_IN)]
             + [f'{s}{k}' for s in ('sp', 'spb', 'sm', 'smb') for k in range(N_OUT)])
    vd, nd = to_verilog('ref_data_blk', data_lines(), D_IN, D_OUT)
    bus = [f'module ref_data_bus (sdi, data_clk, dload, dload_b, READ, rst, rstb, ga, gb, sp, spb, sm, smb);  // testbench 용 bus 포장',
           '    input sdi, data_clk, dload, dload_b, READ, rst, rstb;', f'    output [{N_IN - 1}:0] ga, gb;', f'    output [{N_OUT - 1}:0] sp, spb, sm, smb;',
           '    ref_data_blk u (' + ', '.join([f'.{n}({n})' for n in D_IN] + [f'.{n}({n.rstrip("0123456789")}[{n[len(n.rstrip("0123456789")):]}])' for n in D_OUT]) + ');',
           'endmodule', '']
    (H / 'ref_data_blk.v').write_text('\n'.join([hdr.format('ref_data_blk.v', ' + gen_chip_deck3.py DATA 줄'), ''] + BEH + vd + bus))
    G_IN = ['sck', 'sdi', 'sld', 'rst']
    G_OUT = (chip_lib.CFG + [f'{n}_b' for n in chip_lib.CFG]
             + ['READ', 'READb', 'PROG', 'PROGb', 'VER', 'VERb', 'SENSE', 'WRANY', 'FORM', 'rstb', 'cfg_clk', 'sck_r']
             + [f'{r}_clk' for r in chip_lib.REGS])
    vg, ng = to_verilog('ref_glob_dig', chip_lib.global_decode() + chip_lib.config_block(buf=True), G_IN, G_OUT)
    (H / 'ref_glob_dig.v').write_text('\n'.join([hdr.format('ref_glob_dig.v', ''), ''] + BEH + ckbuf_module() + vg))
    print(f'check_seq: DFFR·DLATCH {nchk} 단계 일치, CKBUF inverter {ninv} 단')
    print(f'ref_data_blk.v: 인스턴스 {nd}, 입력 {len(D_IN)}, 출력 {len(D_OUT)}')
    print(f'ref_glob_dig.v: 인스턴스 {ng}, 입력 {len(G_IN)}, 출력 {len(G_OUT)}')

#!/usr/bin/env python3
"""core 최상위 netlist (chip_core) 만들기 — (d3) floorplan, 블록 CDL 의 .subckt 핀이 정본 (10/28).

내는 파일 (모두 이 폴더 = layout/top/net/):
  chip_core.v        구조 Verilog (블록마다 빈 module + chip_core). PG 핀은 빼고 chip_core_pg.tcl 로 잇는다.
  chip_core_top.v    같은 것에서 빈 module 만 뺀 판 (Innovus 가 빈 module 을 LEF 셀 대신 계층 module 로 볼 때 쓴다)
  chip_core_pg.tcl   Innovus connect_global_net (PG 핀 + 1'b0 = tie_lo → VSS)
  chip_core.cdl      블록 CDL .INCLUDE (Olympus 절대경로) + .SUBCKT chip_core … .ENDS (LVS source)
  lib/               nested .INCLUDE 를 주석으로 바꾼 블록 CDL 사본 (hvl 셀 CDL 이 네 번 include 되지 않게), test pattern 빈 subckt
  pins.json          core 핀 → 패드 이름·변·좌표 (패드 = ../../floorplan_opt_D3.json 'pads')
  deck_map.tsv       덱 v3 node ↔ core 넷 대응표 (+ 비교 결과)
  check_report.txt   확인 결과 (안 쓰는 핀, 출력 둘 이상, 패드, 덱 비교, 인스턴스·넷 수)
  DEVIATIONS.md      덱 v3 와 다른 연결·추가·삭제와 그 이유 (+ 비교 결과 숫자)
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python mk_top.py   (옵션은 --help)
"""
import argparse
import collections
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

NET = Path(__file__).resolve().parent              # layout/top/net
TOPD = NET.parent                                  # layout/top
LAYOUT = TOPD.parent                               # layout
EPDR = LAYOUT.parent                               # ep_dr (로컬)
OLY = '/home/grads/s/seokjindaveoh/work/ep_dr'     # Olympus 의 같은 폴더
sys.path.insert(0, str(EPDR / 'real_circuit'))
from chip_lib import CFG                           # noqa: E402  (설정 bit 순서: dload·pol·rd_out 의 latch 번호)

ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
ap.add_argument('--col', default='digital/col_blk/out/col_blk', help='col_blk 폴더 (ep_dr 기준). 정본 = 잡 721186 판 (조정 세션 10/28)')
ap.add_argument('--arr', default='auto', help="배열 CDL. auto = ../place/place_real.json 의 arr_f cell 을 따름 "
                "(arr_w3_128x64 → layout/blocks/, arr_w3s_128x64 (덧대기) → layout/top/strap/)")
ap.add_argument('--deck', default='real_circuit/decks/chip_write3.sp', help='비교할 덱 v3 (gen_chip_deck3.py 가 쓴 것)')
ap.add_argument('--vbp-pad', default='SPARE17', help="bias vbp (HOG_BIAS 의 Ibp) 를 받을 예비 패드. 'none' = core 핀 없이 내부 넷")
ap.add_argument('--pg', default='VDD,VSS', help='Verilog 에서 빼고 connect_global_net 으로 잇는 넷')
ap.add_argument('--cdl-root', default=OLY, help='chip_core.cdl 의 .INCLUDE 경로 앞부분 (Pegasus 가 도는 곳)')
ap.add_argument('--tag', default='', help='판 이름 (머리말에 적음)')
ap.add_argument('--push', action='store_true', help='끝나면 net/ 결과를 Olympus ~/work/ep_dr/layout/top/net/ 로 scp')
ap.add_argument('--mutate', default='', help="검사 자체 시험: 연결 하나를 일부러 틀리게 하고 검사만 (파일 안 씀). 'all' = 모두 차례로")
A = ap.parse_args()

# ── 덱 v3 의 배열 쓰임 (gen_chip_deck3.py LAY: train.layout_of(nostab_5bit.npz), 10/28 확인)
NR, NRX, NC = 106, 100, 64            # 쓰는 행 (0–105), ROW1 행 (입력 98 + bias 2), 열
R_X, R_B, R_Y = list(range(98)), [98, 99], list(range(100, 106))
C_H = list(range(60))                 # hidden 열 (δ clamp), 60–63 = 남는 열 (col_blk 안 SP TG)
N_IN, N_OUT = 49, 3
ARR_ROWS, ARR_COLS = 128, 64

TIE0 = '__TIE0__'                     # Verilog 1'b0, CDL = VSS
HALF = {'f': 'free', 'n': 'nudge'}
VBUS = {'f': 'VBUS_F', 'n': 'VBUS_N'}
PG_POS = {'VDD', 'vdd', 'VPWR', 'VPB'}
PG_NEG = {'VSS', 'vss', 'VGND', 'VNB'}
PG_NETS = [s for s in A.pg.split(',') if s]
VBP_NET = 'IBIASP' if A.vbp_pad.lower() != 'none' else 'vbp'
INV = 'sky130_fd_sc_hvl__inv_2'


def P(rel):
    return EPDR / rel


# ── 블록 표: cell → CDL (로컬, ep_dr 기준), 방향을 읽을 Verilog
COLD = A.col.rstrip('/')
ARRS = {'arr_w3_128x64': 'layout/blocks/arr_w3_128x64.cdl', 'arr_w3s_128x64': 'layout/top/strap/arr_w3s_128x64.cdl'}
PLACE = TOPD / 'place' / 'place_real.json'
PLJ = json.loads(PLACE.read_text()) if PLACE.exists() else None
if A.arr == 'auto':
    A.arr = ARRS[PLJ['instances']['arr_f']['cell']] if PLJ and PLJ.get('instances', {}).get('arr_f', {}).get('cell') in ARRS else ARRS['arr_w3_128x64']
ARR = Path(A.arr).stem
BLK = {
    ARR: dict(cdl=A.arr),
    'row_blk': dict(cdl='digital/row_blk/out/row_blk/row_blk.cdl', v='digital/row_blk/out/row_blk/row_blk_pnr.v'),
    'col_blk': dict(cdl=f'{COLD}/col_blk.cdl', v=f'{COLD}/col_blk_pnr.v'),
    'input_drive': dict(cdl='layout/blk_analog/out/input_drive.cdl'),
    'data_blk': dict(cdl='layout/blk_digital/out/data_blk.cdl', v='layout/blk_digital/out/data_blk_pnr.v'),
    'glob_dig': dict(cdl='layout/blk_digital/out/glob_dig.cdl', v='layout/blk_digital/out/glob_dig_pnr.v'),
    'wu': dict(cdl='layout/blk_wu/out/wu.cdl'),
    'wbuf': dict(cdl='layout/blk_analog/out/wbuf.cdl'),
    'nudge_inj': dict(cdl='layout/blk_analog/out/nudge_inj.cdl'),
    'bias_beta': dict(cdl='layout/blk_analog/out/bias_beta.cdl'),
    'tg_n2': dict(cdl='layout/blocks/tg_n2.cdl'),
    INV: dict(cdl='digital/pdk/sky130_fd_sc_hvl_u.cdl', std=True),
}
TPS = ['tp_tl', 'tp_br', 'tp_bandl', 'tp_bandr']
TP_SRC = {}
for t in TPS:                         # testpat/ 에이전트 결과가 있으면 그것, 없으면 VDD·VSS 만 가진 빈 subckt
    c = next((q for q in (TOPD / 'testpat' / f'{t}.cdl', TOPD / 'testpat' / 'out' / f'{t}.cdl') if q.exists()), None)
    if c is not None:
        BLK[t] = dict(cdl=str(c.relative_to(EPDR)))
        TP_SRC[t] = 'testpat'
    else:
        BLK[t] = dict(cdl=None, stub=['VDD', 'VSS'])
        TP_SRC[t] = 'stub'

# 아날로그 블록 핀 방향 (CDL 에 방향이 없어 덱의 쓰임으로 정함). 디지털 블록은 *_pnr.v 에서 읽음
ADIR = {
    ARR: {'row': 'inout', 'wl': 'input', 'col': 'inout'},
    'input_drive': {'row': 'inout', 'ga': 'input', 'gb': 'input', 'READ': 'input', 'vrailp': 'inout', 'vrailm': 'inout'},
    'wu': {'fp': 'input', 'fm': 'input', 'np': 'input', 'nm': 'input', 'ck': 'input', 'ck3': 'input', 'lat': 'input',
           'latb': 'input', 'lq': 'output', 'sen': 'output', 'absf': 'output', 'absn': 'output', 'q1': 'output',
           'q2': 'output', 'vbn': 'input', 'vbp': 'input', 'vbnc': 'input', 'vbpc': 'input', 'vcm': 'inout'},
    'wbuf': {'wp': 'input', 'pol': 'input', 'out': 'output', 'vwh': 'inout', 'vwl': 'inout'},
    'nudge_inj': {'yp': 'inout', 'ym': 'inout', 'pref': 'input', 'nref': 'input', 'sp': 'input', 'spb': 'input',
                  'sm': 'input', 'smb': 'input'},
    'bias_beta': {'vbn': 'inout', 'vbp': 'inout', 'vbpc': 'input', 'pref': 'output', 'nref': 'output'},
    'tg_n2': {'a': 'inout', 'b': 'inout', 'ctl': 'input', 'ctlb': 'input'},
    INV: {'A': 'input', 'Y': 'output'},
}


# ── CDL 읽기
def cdl_lines(path):
    out = []
    for ln in Path(path).read_text().splitlines():
        if ln.startswith('+') and out:
            out[-1] += ' ' + ln[1:]
        else:
            out.append(ln)
    return out


def loc(p):
    """Olympus 절대경로 → 로컬."""
    return Path(p.replace(OLY, str(EPDR))) if p.startswith(OLY) else Path(p)


def subckts(path, seen=None):
    """{name: (pins, body_text, file)} — .INCLUDE 를 따라감."""
    seen = set() if seen is None else seen
    path = Path(path)
    out, cur = {}, None
    for ln in cdl_lines(path):
        t = ln.split()
        if not t:
            continue
        k = t[0].lower()
        if k in ('.include', '.inc'):
            q = loc(t[1].strip('\'"'))
            if q.resolve() not in seen:
                seen.add(q.resolve())
                out.update({n: v for n, v in subckts(q, seen).items()})
        elif k == '.subckt':
            cur = [t[1], [x for x in t[2:] if '=' not in x], [], path]
        elif k == '.ends' and cur:
            out[cur[0]] = (cur[1], '\n'.join(cur[2]), cur[3])
            cur = None
        elif cur:
            cur[2].append(ln)
    return out


def includes(path):
    return [loc(ln.split()[1].strip('\'"')) for ln in cdl_lines(path) if ln.split()[:1] and ln.split()[0].lower() in ('.include', '.inc')]


def vdirs(path):
    """구조 Verilog 의 port 방향 {base: dir}."""
    d = {}
    if not path or not P(path).exists():
        return d
    for m in re.finditer(r'^\s*(input|output|inout)\s*(\[\s*\d+\s*:\s*\d+\s*\])?\s*([^;]+);', P(path).read_text(), re.M):
        for n in m.group(3).split(','):
            d[n.strip()] = m.group(1)
    return d


def split_pin(p):
    """'row[5]' → ('row', 5, True), 'row_5' → ('row', 5, False), 'ga5' → ('ga', 5, False), 'R1' → ('R1', None, False)."""
    m = re.match(r'^(.+)\[(\d+)\]$', p)
    if m:
        return m.group(1), int(m.group(2)), True
    m = re.match(r'^(row|wl|col)_(\d+)$', p)
    if m:
        return m.group(1), int(m.group(2)), False
    m = re.match(r'^(ga|gb|yp|ym|spb|smb|sp|sm)(\d+)$', p)
    if m:
        return m.group(1), int(m.group(2)), False
    return p, None, False


CELL = {}          # cell → dict(pins, file, dirs)
for cell, b in BLK.items():
    if b.get('stub') is not None:
        CELL[cell] = dict(pins=list(b['stub']), file=None, dirs={q: 'pg' for q in b['stub']})
        continue
    sc = subckts(P(b['cdl']))
    if cell not in sc:
        sys.exit(f'{b["cdl"]}: .subckt {cell} 없음')
    vd = vdirs(b.get('v'))
    dirs = {}
    for p in sc[cell][0]:
        base, idx, bus = split_pin(p)
        if p in PG_POS | PG_NEG:
            dirs[p] = 'pg'
        elif base in vd:
            dirs[p] = vd[base]
        elif cell in ADIR and (p in ADIR[cell] or base in ADIR[cell]):
            dirs[p] = ADIR[cell].get(p, ADIR[cell].get(base))
        else:
            dirs[p] = 'inout'
    CELL[cell] = dict(pins=sc[cell][0], file=P(b['cdl']), dirs=dirs, sub=sc)


# ── 연결 규칙: (인스턴스, 핀) → core 넷. 규칙에 없는 핀은 멈춤 (블록 핀이 바뀌면 바로 보이게)
class Unmapped(Exception):
    pass


def pg(pin):
    if pin in PG_POS:
        return 'VDD'
    if pin in PG_NEG:
        return 'VSS'
    return None


GLOB_IN = {'sck': 'SCK', 'sdi': 'SDI', 'sld': 'SLD', 'rst': 'RST'}


def rule(inst, cell, pin):
    g = pg(pin)
    if g:
        return g
    base, i, _ = split_pin(pin)
    p = inst[-1] if inst[-2:] in ('_f', '_n') else None
    if cell == ARR:
        if base == 'row':
            return f'row_{p}_{i}' if i < NR else None             # 106–127 행: row 떠 있음
        if base == 'wl':
            return f'wl_{p}_{i}' if i < NR else TIE0              # 106–127 행: WL = VSS (접근 nFET 꺼짐)
        if base == 'col':
            return f'col_{p}_{i}'
    if cell == 'row_blk':
        m = {'row': lambda: f'row_{p}_{i}', 'wl': lambda: f'wl_{p}_{i}', 'sdi': lambda: 'SDI', 'sel_en': lambda: 'SEL_EN',
             'vw': lambda: f'vw_{p}', 'vwl': lambda: 'VWL', 'vzero': lambda: 'VCM', 'R1': lambda: f'R1_{p}', 'R2': lambda: f'R2_{p}'}
        if base in m:
            return m[base]()
        if base in ('row1_clk', 'row2_clk', 'rstb', 'PROG', 'VER', 'SENSE', 'READb', 'WRANY'):
            return f'{base}_{p}'
    if cell == 'col_blk':
        m = {'col': lambda: f'col_{p}_{i}', 'vw': lambda: f'vw_{p}', 'vbus': lambda: VBUS[p], 'C1': lambda: f'C1_{p}',
             'C2': lambda: f'C2_{p}', 'vzero': lambda: 'VCM', 'vrailp': lambda: 'VRAILP', 'vrailm': lambda: 'VRAILM',
             'sdi': lambda: 'SDI', 'sel_en': lambda: 'SEL_EN', 'lo': lambda: TIE0}
        if base in m:
            return m[base]()
        if base in ('rstb', 'col1_clk', 'col2_clk', 'PROG', 'VER', 'SENSE', 'WRANY', 'READ', 'READb'):
            return f'{base}_{p}'
    if cell == 'input_drive':
        m = {'row': lambda: f'row_{p}_{i}', 'ga': lambda: f'ga_{p}_{i}', 'gb': lambda: f'gb_{p}_{i}', 'READ': lambda: f'READ_{p}',
             'vrailp': lambda: 'VRAILP', 'vrailm': lambda: 'VRAILM'}
        if base in m:
            return m[base]()
    if cell == 'data_blk':
        if base in ('ga', 'gb'):
            return f'{base}_{p}_{i}'
        if base in ('sp', 'spb', 'sm', 'smb'):
            return f'{base}_n_{i}' if p == 'n' else None          # 주입기는 nudge 배열만 → free DATA 의 sp/sm 은 안 씀
        if base == 'sdi':
            return 'SDI'
        if base in ('data_clk', 'dload', 'READ', 'rstb'):
            return f'{base}_{p}'
    if cell == 'glob_dig':
        if pin in GLOB_IN:
            return GLOB_IN[pin]
        if re.search(r'_[fn]$', pin):
            return pin                                            # READ_f … 그대로 넷 이름
    if cell == 'wu':
        k = inst[-1]
        m = dict(zip(['fp', 'fm', 'np', 'nm'], [f'{b}{k}_{h}' for h in 'fn' for b in 'RC']))   # wu1: R1_f C1_f R1_n C1_n
        m.update(ck='CK', ck3='CK3', lat='LAT', latb=f'latb_{k}', lq=f'LQ{k}', vbn='IBIAS', vbp=VBP_NET, vbnc='VBNC',
                 vbpc='VBPC', vcm='VCM', sen=None, absf=None, absn=None, q1=None, q2=None)
        if pin in m:
            return m[pin]
    if cell == INV:
        k = inst[-1]
        m = {'A': 'LAT', 'Y': f'latb_{k}'}
        if pin in m:
            return m[pin]
    if cell == 'wbuf':
        m = {'wp': 'WP', 'pol': f'pol_{p}', 'out': f'vw_{p}', 'vwh': 'VWH', 'vwl': 'VWLO'}
        if pin in m:
            return m[pin]
    if cell == 'tg_n2':
        m = {'a': f'R2_{p}', 'b': VBUS[p], 'ctl': f'rd_out_{p}', 'ctlb': f'rd_out_b_{p}'}
        if pin in m:
            return m[pin]
    if cell == 'bias_beta':
        m = {'vbn': 'IBIAS', 'vbp': VBP_NET, 'vbpc': 'VBPC', 'pref': 'pref', 'nref': 'nref'}
        if pin in m:
            return m[pin]
    if cell == 'nudge_inj':
        if base == 'yp':
            return f'row_n_{R_Y[2 * i]}'
        if base == 'ym':
            return f'row_n_{R_Y[2 * i + 1]}'
        if base in ('pref', 'nref'):
            return base
        if base in ('sp', 'spb', 'sm', 'smb'):
            return f'{base}_n_{i}'
    if cell in TPS:
        tj = P(BLK[cell]['cdl']).with_suffix('.json') if BLK[cell].get('cdl') else Path('/nonexistent')
        if tj.exists():
            j = json.loads(tj.read_text())
            for key in ('connect', 'nets', 'pin_nets'):
                if isinstance(j.get(key), dict) and pin in j[key]:
                    return j[key][pin]
        cp = {c.lower(): c for c in CORE_SIG}
        if pin.lower() in cp:
            return cp[pin.lower()]
        return None
    raise Unmapped(f'{inst} ({cell}) 핀 {pin}: 연결 규칙 없음')


# ── 인스턴스 (README §2 이름) — 위치는 place/ 가 정함
INST = []
for pre, cell in (('arr', ARR), ('idrv', 'input_drive'), ('rowb', 'row_blk'), ('colb', 'col_blk'), ('data', 'data_blk'),
                  ('wbuf', 'wbuf'), ('rotg', 'tg_n2')):
    INST += [(f'{pre}_{p}', cell) for p in 'fn']
INST += [('wu1', 'wu'), ('wu2', 'wu'), ('glob', 'glob_dig'), ('bias', 'bias_beta'), ('ninj', 'nudge_inj')]
INST += [(t, t) for t in TPS]
INST += [('ilatb1', INV), ('ilatb2', INV)]                       # 덱 XIlat (LATB = 칩 안 inverter) — WU 마다 하나

# ── core 핀 (= 패드 이름). 같은 이름 패드 여럿 = core 핀 하나
FP = json.loads((LAYOUT / 'floorplan_opt_D3.json').read_text())
PADS = FP['pads']
CORE_SIG = ['SCK', 'SDI', 'SLD', 'RST', 'SEL_EN', 'WP', 'CK', 'CK3', 'LAT', 'LQ1', 'LQ2',
            'VRAILP', 'VRAILM', 'VWH', 'VWLO', 'VWL', 'VBUS_F', 'VBUS_N', 'IBIAS', 'VBNC', 'VBPC'] + (['IBIASP'] if VBP_NET == 'IBIASP' else [])
CORE_PWR = ['VDD', 'VSS', 'VCM']
CORE = CORE_SIG + CORE_PWR
CORE_DIR = {n: 'input' for n in ['SCK', 'SDI', 'SLD', 'RST', 'SEL_EN', 'WP', 'CK', 'CK3', 'LAT']}
CORE_DIR.update({n: 'output' for n in ['LQ1', 'LQ2']})
SPARE_MAP = {A.vbp_pad: 'IBIASP'} if VBP_NET == 'IBIASP' else {}
PAD_ONLY = ['VDDL', 'VSSL']                                       # 1.8 V pad ring (VCCD·VSSD) — core 에 안 들어옴

# ── 연결 표
CONN = collections.OrderedDict()    # inst → (cell, [(pin, net)])
for inst, cell in INST:
    CONN[inst] = (cell, [(pin, rule(inst, cell, pin)) for pin in CELL[cell]['pins']])

MUT = {   # 검사가 잡아야 하는 틀린 연결 (이름: [(인스턴스, 핀, 새 넷)])
    'wu_fpfm': [('wu1', 'fp', 'C1_f'), ('wu1', 'fm', 'R1_f')], 'wu2_r1': [('wu2', 'fp', 'R1_f')],
    'col_shift': [('colb_f', 'col[5]', 'col_f_6')], 'ga_gb': [('idrv_f', 'ga3', 'gb_f_3'), ('idrv_f', 'gb3', 'ga_f_3')],
    'vzero_vss': [('rowb_f', 'vzero', 'VSS')], 'rotg_bus': [('rotg_f', 'b', 'VBUS_N')],
    'ninj_row': [('ninj', 'yp0', 'row_n_101'), ('ninj', 'ym0', 'row_n_100')],
    'clk_swap': [('rowb_n', 'row1_clk', 'row2_clk_n'), ('rowb_n', 'row2_clk', 'row1_clk_n')],
    'vrail_swap': [('idrv_n', 'vrailp', 'VRAILM'), ('idrv_n', 'vrailm', 'VRAILP')], 'wbuf_vw': [('wbuf_f', 'vwh', 'VWLO'), ('wbuf_f', 'vwl', 'VWH')],
    'data_f_sp': [('data_f', 'sp[0]', 'sp_n_0')], 'pref_nref': [('ninj', 'pref', 'nref'), ('ninj', 'nref', 'pref')],
    'wl_row': [('arr_n', 'wl_7', 'row_n_7')], 'r2_r1': [('rowb_n', 'R2', 'R1_n')], 'latb_lat': [('wu2', 'latb', 'LAT')],
    'pol_half': [('wbuf_f', 'pol', 'pol_n')], 'pg_swap': [('wu1', 'vss', 'VDD')], 'tp_vss': [('tp_br', 'VSS', 'VCM')],
    'lo_vcm': [('colb_n', 'lo', 'VCM')], 'ninj_dataf': [('ninj', 'sm1', 'sm_f_1')], 'c2_c1': [('colb_f', 'C2', 'C1_f')], 'ibias_vbp': [('bias', 'vbp', 'IBIAS')],
}
if A.mutate and A.mutate != 'all':
    for inst, pin, n in MUT[A.mutate]:
        cell, pl = CONN[inst]
        assert pin in dict(pl), (inst, pin)
        CONN[inst] = (cell, [(q, n if q == pin else m) for q, m in pl])

nets = collections.OrderedDict()    # net → [(inst, pin)]
for inst, (cell, pl) in CONN.items():
    for pin, n in pl:
        if n is None:
            continue
        nn = 'VSS' if n == TIE0 else n
        nets.setdefault(nn, []).append((inst, pin))
for n in CORE:
    nets.setdefault(n, [])

# ── 확인
R = []                               # check_report 줄
W = []                               # 경고 (요약에 올림)


def rep(s=''):
    R.append(s)


def dir_of(inst, pin):
    cell = CONN[inst][0]
    return CELL[cell]['dirs'].get(pin, 'inout')


# (1) 안 쓰는 핀
unused = collections.OrderedDict()
ties = collections.OrderedDict()
for inst, (cell, pl) in CONN.items():
    for pin, n in pl:
        if n is None:
            unused.setdefault(inst, []).append(pin)
        elif n == TIE0:
            ties.setdefault(inst, []).append(pin)
dangling = [n for n, m in nets.items() if len(m) == 1 and n not in CORE]
nopin_core = [n for n in CORE if not nets[n]]

# (2) 한 넷에 출력 둘 이상
multi = {n: [(i, p) for i, p in m if dir_of(i, p) == 'output'] for n, m in nets.items()}
multi = {n: v for n, v in multi.items() if len(v) + (1 if CORE_DIR.get(n) == 'input' else 0) > 1}
nodrv = [n for n, m in nets.items() if n not in CORE and all(dir_of(i, p) == 'input' for i, p in m)]

# (3) 대소문자만 다른 넷 (SPICE·LVS 는 대소문자를 가리지 않는다)
lc = collections.defaultdict(set)
for n in nets:
    lc[n.lower()].add(n)
case_clash = [sorted(v) for v in lc.values() if len(v) > 1]

# (4) 패드
pad_names = collections.OrderedDict()
for pd in PADS:
    pad_names.setdefault(pd['name'], []).append(pd)
core_vs_pad = []
for n in CORE:
    src = [k for k, v in SPARE_MAP.items() if v == n]
    if n not in pad_names and not (src and src[0] in pad_names):
        core_vs_pad.append(f'core 핀 {n}: 패드 없음')
pads_no_core = [n for n in pad_names if n not in CORE and n not in SPARE_MAP and not n.startswith('SPARE') and n not in PAD_ONLY]
spares_left = [n for n in pad_names if n.startswith('SPARE') and n not in SPARE_MAP]


# ── 덱 v3 비교 (블록 경계 넷)
def parse_deck(path):
    lines = []
    for ln in Path(path).read_text().splitlines():
        if ln.startswith('+') and lines:
            lines[-1] += ' ' + ln[1:]
        else:
            lines.append(ln)
    subs, top, cur = {}, [], None
    for ln in lines:
        t = ln.split()
        if not t or t[0].startswith('*'):
            continue
        k = t[0].lower()
        if k == '.subckt':
            cur = (t[1].lower(), [x.lower() for x in t[2:] if '=' not in x], [])
            continue
        if k.startswith('.ends'):
            subs[cur[0]] = (cur[1], cur[2])
            cur = None
            continue
        if k.startswith('.'):
            continue
        (cur[2] if cur else top).append(t)
    return subs, top


def elem_nodes(t):
    nm = t[0].lower()
    c = nm[0]
    if c == 'x':
        nt = [x.lower() for x in t[1:] if '=' not in x and "'" not in x]
        return nt[:-1], nt[-1]
    if c == 'm':
        return [x.lower() for x in t[1:5]], t[5].lower()
    return [x.lower() for x in t[1:3]], c


HOG_BIAS_PORTS = ['vbn', 'vbp', 'vbpc', 'vdd', 'vss']            # hog_tr.spice (덱 밖 include)


def deck_compare():
    subs, top = parse_deck(P(A.deck))
    subs.setdefault('hog_bias', (HOG_BIAS_PORTS, []))
    uses0 = {}

    def u0(s):
        if s in uses0:
            return uses0[s]
        uses0[s] = False
        if s not in subs:
            return False
        r = False
        for t in subs[s][1]:
            ns, cl = elem_nodes(t)
            if '0' in ns or (t[0][0].lower() == 'x' and u0(cl)):
                r = True
        uses0[s] = r
        return r

    rules = [  # 덱 소자 이름 → (블록, 반쪽) : 반쪽 '*' = 덱에서 두 배열이 같이 쓰는 것
        (r'^xbias$|^xmpref$|^vbm_[pn]$|^xmbn$|^xmnref$|^xmbp$|^xmbpc$', ('bias', None)),
        (r'^xilat$', ('ilatb', None)), (r'^vlo$', ('tie0', None)),
        (r'^xwb([fn])$', ('wbuf', 1)), (r'^xwu1$', ('wu1', None)), (r'^xwu2$', ('wu2', None)), (r'^xro([fn])$', ('rotg', 1)),
        (r'^x([fn])rm\d+$', ('rowb', 1)), (r'^x([fn])cm\d+$', ('colb', 1)), (r'^x([fn])sp\d+$', ('colb', 1)),
        (r'^x([fn])d[pmb]\d+$', ('idrv', 1)),
        (r'^r([fn])da_', ('colb', 1)), (r'^d([fn])[ab]_', ('colb', 1)), (r'^r([fn])db_', ('colb', 1)),
        (r'^x([fn])r\d+_\d+$', ('arr', 1)), (r'^x([fn])a\d+_\d+$', ('arr', 1)), (r'^r([fn])_\d+_\d+$', ('arr', 1)),
        (r'^g([fn])_\d+_\d+$', ('arr', 1)),
        (r'^x(mp|mn)\d+$', ('ninj', None)), (r'^xsw[1-4]_\d+$', ('ninj', None)),
        (r'^xrl\d+$', ('rowb', '*')), (r'^xfrow[12]\d+$', ('rowb', '*')), (r'^xcl\d+$', ('colb', '*')), (r'^xfcol[12]\d+$', ('colb', '*')),
        (r'^xfd\d+$', ('data', '*')), (r'^xld\d+$', ('data', '*')), (r'^x[ni]ag\d+[ab]$', ('data', '*')), (r'^x[ni]an\d+[pm]$', ('data', '*')),
        (r'^(xim1|xim0|xipv|xirs|xnpg|xipg|xnwa|xisld|xfc\d+|xlc\d+|xcb\w+|x[ni]a\w+)$', ('glob', None)),
    ]
    ignore = r'^(c|v|r[fn]pad)'    # 용량 (parasitic·부하), 밖의 전원·계측기, 패드 모형
    # 0 V 계측기 Vbm_p·Vbm_n = 단락 → node 합치기
    par = {}

    def f(x):
        while par.get(x, x) != x:
            x = par[x]
        return x
    for t in top:
        if t[0].lower() in ('vbm_p', 'vbm_n'):
            a, b = t[1].lower(), t[2].lower()
            par[f(b)] = f(a)
    touch = collections.defaultdict(set)
    elem = {}
    unk = []
    for t in top:
        nm = t[0].lower()
        if nm in ('vbm_p', 'vbm_n'):
            continue
        ns, cl = elem_nodes(t)
        ns = [f(x) for x in ns]
        cls = None
        for rx, (bt, h) in rules:
            m = re.match(rx, nm)
            if m:
                cls = (bt, m.group(1) if h == 1 else h)
                break
        if cls is None:
            if re.match(ignore, nm):
                continue
            unk.append(nm)
            continue
        if cls[0] == 'tie0':
            touch[ns[0]].add(cls)
            continue
        elem[nm] = (ns, cl)
        for x in set(ns):
            touch[x].add(cls)
        if nm[0] == 'x' and u0(cl):
            touch['0'].add(cls)          # subckt 안에서 전역 node 0 을 씀 (ROWM XT3, COLM XT1, WU)
    pad_of = {'sck': 'SCK', 'sdi': 'SDI', 'sld': 'SLD', 'rst': 'RST', 'sel_en': 'SEL_EN', 'wp': 'WP', 'ck': 'CK', 'ck3': 'CK3',
              'lat': 'LAT', 'lq1': 'LQ1', 'lq2': 'LQ2', 'vrailp': 'VRAILP', 'vrailm': 'VRAILM', 'vwh': 'VWH', 'vwlo': 'VWLO',
              'vwl': 'VWL', 'vbusf': 'VBUS_F', 'vbusn': 'VBUS_N', 'vbn': 'IBIAS', 'vbnc': 'VBNC', 'vbpc': 'VBPC',
              'vdd': 'VDD', 'vss': 'VSS', '0': 'VCM'}
    if VBP_NET == 'IBIASP':
        pad_of['vbp'] = 'IBIASP'
    for d, pn in pad_of.items():
        touch[d].add(('pad', pn))

    def port(en, pn):
        ns, cl = elem[en]
        if isinstance(pn, int):
            return ns[pn]
        ports = subs[cl][0]
        return ns[ports.index(pn.lower())]
    cfgk = {n: k for k, n in enumerate(CFG)}

    def dref(inst, cell, pin):
        """(인스턴스, 핀) → 덱 node (소문자) / None (덱에 없음)."""
        if pin in PG_POS:
            return 'vdd'
        if pin in PG_NEG:
            return 'vss'
        base, i, _ = split_pin(pin)
        p = inst[-1] if inst[-2:] in ('_f', '_n') else None
        try:
            if cell == ARR:
                if i is not None and ((base in ('row', 'wl') and i >= NR)):
                    return None
                return {'row': f'{p}r{i}', 'wl': f'{p}wl{i}', 'col': f'{p}c{i}'}[base]
            if cell == 'row_blk':
                m = {'row': (f'x{p}rm{i}', 'row'), 'wl': (f'x{p}rm{i}', 'wl'), 'R1': (f'x{p}rm0', 'bus'),
                     'R2': (f'x{p}rm{NRX}', 'bus'), 'vw': (f'x{p}rm0', 'vw'), 'vwl': (f'x{p}rm0', 'vwl'),
                     'sdi': ('xfrow10', 'd'), 'row1_clk': ('xfrow10', 'clk'), 'row2_clk': ('xfrow20', 'clk'), 'rstb': ('xfrow10', 'rstb')}
                if base == 'vzero':
                    return '0'
                return port(*m[base]) if base in m else port('xrl0', base)
            if cell == 'col_blk':
                m = {'col': (f'x{p}cm{i}', 'col'), 'vw': (f'x{p}cm0', 'vw'), 'vbus': (f'x{p}cm0', 'vbus'), 'C1': (f'x{p}cm0', 'c1'),
                     'C2': (f'x{p}cm0', 'c2'), 'vrailp': (f'd{p}b_{p}c0', 0), 'vrailm': (f'd{p}a_{p}c0', 1),
                     'sdi': ('xfcol10', 'd'), 'rstb': ('xfcol10', 'rstb'), 'col1_clk': ('xfcol10', 'clk'), 'col2_clk': ('xfcol20', 'clk'),
                     'lo': (f'xcl{NC - 1}', 't1'), 'READ': (f'x{p}sp{NC - 1}', 'en'), 'READb': (f'x{p}sp{NC - 1}', 'enb')}
                if base == 'vzero':
                    return '0'
                return port(*m[base]) if base in m else port('xcl0', base)
            if cell == 'input_drive':
                if base == 'row':
                    return port(f'x{p}dp{i}', 0) if i in R_X else port(f'x{p}db{i}', 0)
                m = {'ga': (f'x{p}dp{2 * (i or 0)}', 1), 'gb': (f'x{p}dm{2 * (i or 0)}', 1), 'READ': (f'x{p}db{R_B[0]}', 1),
                     'vrailp': (f'x{p}dp0', 2), 'vrailm': (f'x{p}dm0', 2)}
                return port(*m[base])
            if cell == 'data_blk':
                m = {'sdi': ('xfd0', 'd'), 'data_clk': ('xfd0', 'clk'), 'dload': ('xld0', 'clk'), 'READ': ('xnag0a', 'a'),
                     'rstb': ('xfd0', 'rstb'), 'ga': (f'xiag{i}a', 'y'), 'gb': (f'xiag{i}b', 'y'), 'sp': (f'xian{i}p', 'y'),
                     'spb': (f'xnan{i}p', 'y'), 'sm': (f'xian{i}m', 'y'), 'smb': (f'xnan{i}m', 'y')}
                return port(*m[base])
            if cell == 'glob_dig':
                b = re.sub(r'_[fn]$', '', pin)
                m = {'sck': ('xnacc', 'a'), 'sdi': ('xfc0', 'd'), 'sld': ('xisld', 'a'), 'rst': ('xirs', 'a'),
                     'data_clk': ('xcbdata', 'y'), 'row1_clk': ('xcbrow1', 'y'), 'row2_clk': ('xcbrow2', 'y'),
                     'col1_clk': ('xcbcol1', 'y'), 'col2_clk': ('xcbcol2', 'y'), 'rstb': ('xirs', 'y'), 'READ': ('xiard', 'y'),
                     'READb': ('xnard', 'y'), 'PROG': ('xnpg', 'y'), 'VER': ('xiave', 'y'), 'SENSE': ('xiase', 'y'),
                     'WRANY': ('xnwa', 'y'), 'dload': (f'xlc{cfgk["dload"]}', 'q'), 'pol': (f'xlc{cfgk["pol"]}', 'q'),
                     'rd_out': (f'xlc{cfgk["rd_out"]}', 'q'), 'rd_out_b': (f'xlc{cfgk["rd_out"]}', 'qb')}
                return port(*m[b])
            if cell == 'wu':
                return '0' if pin == 'vcm' else port(f'xwu{inst[-1]}', pin)
            if cell == 'wbuf':
                return port(f'xwb{p}', pin)
            if cell == 'tg_n2':
                return port(f'xro{p}', {'a': 'a', 'b': 'b', 'ctl': 'en', 'ctlb': 'enb'}[pin])
            if cell == 'bias_beta':
                m = {'vbn': ('xbias', 0), 'vbp': ('xbias', 1), 'vbpc': ('xbias', 2), 'pref': ('xmpref', 0), 'nref': ('xmnref', 0)}
                return port(*m[pin])
            if cell == 'nudge_inj':
                m = {'yp': (f'xsw1_{i}', 'b'), 'ym': (f'xsw2_{i}', 'b'), 'pref': ('xmp0', 1), 'nref': ('xmn0', 1),
                     'sp': (f'xsw1_{i}', 'en'), 'spb': (f'xsw1_{i}', 'enb'), 'sm': (f'xsw2_{i}', 'en'), 'smb': (f'xsw2_{i}', 'enb')}
                return port(*m[base])
            if cell == INV:
                return port('xilat', {'A': 'a', 'Y': 'y'}[pin])
        except (KeyError, ValueError) as e:
            raise SystemExit(f'덱 대응 실패: {inst}.{pin} ({e})')
        return None

    btype = {}
    for inst, cell in INST:
        b = re.sub(r'(_[fn]|\d)$', '', inst)
        b = {'wu': inst}.get(b, b)
        if b.startswith('tp'):
            b = inst
        btype[inst] = (b, inst[-1] if inst[-2:] in ('_f', '_n') else None)
    # 배열 셀이 덱 대응 (행 = TE, WL = 게이트, 열 = 소스) 과 같은지
    cell_bad = 0
    for en, (ns, cl) in elem.items():
        m = re.match(r'^x([fn])a(\d+)_(\d+)$', en)
        if m:
            p, r, c = m.group(1), int(m.group(2)), int(m.group(3))
            cell_bad += ns[1] != f'{p}wl{r}' or ns[2] != f'{p}c{c}' or ns[3] != 'vss'
        m = re.match(r'^x([fn])r(\d+)_(\d+)$', en)
        if m:
            cell_bad += ns[0] != f'{m.group(1)}r{m.group(2)}'
    # 칩 넷 → 덱 node
    chip_d = {}
    for n, mem in nets.items():
        ds = collections.OrderedDict()
        for inst, pin in mem:
            d = dref(inst, CONN[inst][0], pin)
            if d is not None:
                ds.setdefault(d, []).append((inst, pin))
        chip_d[n] = ds
    by_d = collections.defaultdict(list)
    for n, ds in chip_d.items():
        for d in ds:
            by_d[d].append(n)
    ctouch = {}
    for n, mem in nets.items():
        s = {btype[i] for i, _ in mem}
        if n in CORE:
            s.add(('pad', n))
        ctouch[n] = s

    def bt_set(s):
        return {b for b, _ in s}
    # 덱의 블록 경계 node = 블록 둘 이상 (패드 포함) 이 닿는 node
    bnd = sorted(d for d, s in touch.items() if len(bt_set(s)) >= 2)
    rows = []
    expect = EXPECT
    n_ok = n_exp = n_bad = 0
    issues = []
    for d in sorted(set(bnd) | set(by_d)):
        ds = touch.get(d, set())
        cn = by_d.get(d, [])
        cs = set()
        for n in cn:
            cs |= ctouch[n]
        # 덱 쪽 (블록, 반쪽) 이 칩에서 덮이는지: '*' 는 f·n 둘 다
        miss = []
        for b, h in sorted(ds, key=str):
            if b == 'tie0':
                ok = any(CONN[i][0] for n in cn for i, _ in nets[n]) and any(n == 'VSS' for n in cn)
            elif h == '*':
                ok = (b, 'f') in cs and (b, 'n') in cs
            else:
                ok = (b, h) in cs
            if not ok:
                miss.append(f'{b}{"_" + h if h else ""}')
        extra = []
        for n in cn:
            if len(chip_d[n]) > 1:
                continue                      # 덱 node 여럿이 한 넷 → 아래 short 로
            for b, h in sorted(ctouch[n], key=str):
                if b == 'pad':
                    ok = ('pad', h) in ds
                else:
                    ok = (b, h) in ds or (b, '*') in ds or (h is None and any(x == b for x, _ in ds))
                if not ok:
                    extra.append(f'{b}{"_" + h if h else ""}@{n}')
        shorts = [n for n in cn if len(chip_d[n]) > 1]
        sig = (' '.join(sorted(miss)), ' '.join(sorted(extra)), ' '.join(f'{n}={"+".join(chip_d[n])}' for n in sorted(shorts)))
        st, why = 'ok', ''
        if miss or extra or shorts or (d in bnd and not cn):
            hit = [e for e in expect if re.fullmatch(e[0], d) and tuple(e[1]) == sig]
            if hit:
                st, why = 'expected', hit[0][2]
                n_exp += 1
            else:
                st = 'MISMATCH'
                n_bad += 1
                issues.append((d,) + sig)
        else:
            n_ok += 1
        rows.append((d, ','.join(cn) or '-', ' '.join(sorted({f'{b}{"_" + h if h else ""}' for b, h in ds})),
                     ' '.join(sorted({f'{b}{"_" + h if h else ""}' for n in cn for b, h in ctouch[n]})),
                     st + (f' [{why}]' if why else '')) + sig)
    return dict(rows=rows, n_bnd=len(bnd), n_ok=n_ok, n_exp=n_exp, n_bad=n_bad, issues=issues, unk=unk, cell_bad=cell_bad,
                n_elem=len(elem), n_top=len(top))


# 덱과 일부러 다르게 한 것: (덱 node 정규식, (덱에만 있는 블록, 칩에만 있는 블록@넷, 한 넷에 묶인 덱 node), DEVIATIONS 항목)
# 서명이 정확히 같을 때만 '일부러 다름' — 같은 node 라도 다른 차이가 더 생기면 MISMATCH
TPX = ' '.join(f'{t}@VDD' for t in sorted(TPS))
EXPECT = [
    (r'rst', ('colb_* data_* rowb_*', '', ''), 'D4'),
    (r'dload_b', ('data_* glob', '', ''), 'D5'),
    (r'lo|vss', ('', '', 'VSS=vss+lo'), 'D6'),
    (r'vdd', ('', TPX, ''), 'D13'),
    (r'(sp|spb|sm|smb)[0-2]', ('data_*', '', ''), 'D10'),
]

DK = deck_compare()

# ── place/ 와 맞춰 보기: LEF 핀 이름 (= CDL 핀), 인스턴스 이름·cell
lef_chk = []
for cell in dict.fromkeys(c for _, c in INST):
    lf = TOPD / 'place' / 'lef' / f'{cell}.lef'
    if BLK[cell].get('std'):
        continue
    if not lf.exists():
        lef_chk.append(f'{cell}: place/lef 에 LEF 없음')
        continue
    txt = lf.read_text()
    m = re.search(rf'^MACRO\s+{re.escape(cell)}\b(.*?)^END\s+{re.escape(cell)}\b', txt, re.M | re.S)
    lp = re.findall(r'^\s*PIN\s+(\S+)', m.group(1) if m else txt, re.M)
    a, b = set(CELL[cell]['pins']), set(lp)
    if a != b:
        lef_chk.append(f'{cell}: CDL 에만 {sorted(a - b)[:8]}{"…" if len(a - b) > 8 else ""} / LEF 에만 {sorted(b - a)[:8]}')
place_chk = []
if PLJ:
    pi = PLJ.get('instances', {})
    for inst, cell in INST:
        if inst in pi:
            if pi[inst].get('cell') != cell:
                place_chk.append(f'{inst}: place cell {pi[inst].get("cell")} ≠ net cell {cell}')
        elif inst in PLJ.get('test_areas', {}):
            place_chk.append(f'{inst}: place 는 자리 (test_areas) 만')
        else:
            place_chk.append(f'{inst}: place_real.json 에 없음')
    for inst in pi:
        if inst not in dict(INST):
            place_chk.append(f'{inst}: place 에만 있음')

if A.mutate:
    if A.mutate == 'all':
        import subprocess
        bad = 0
        for k in MUT:
            o = subprocess.run([sys.executable, __file__, '--mutate', k], capture_output=True, text=True).stdout.strip().splitlines()[-1]
            print(o)
            bad += 'MISSED' in o
        print(f'돌연변이 {len(MUT)} 개 중 놓친 것 {bad}')
        sys.exit(1 if bad else 0)
    why = [f'덱 예상 밖 {DK["n_bad"]}'] * (DK['n_bad'] > 0) + [f'핀 하나 넷 {len(dangling)}'] * bool(dangling) + \
          [f'출력 둘 이상 {len(multi)}'] * bool(multi) + [f'구동 없음 {len(nodrv)}'] * bool(nodrv)
    print(f'MUT {A.mutate}: ' + ('caught — ' + ', '.join(why) if why else 'MISSED'))
    sys.exit(0)

# ── 인스턴스·넷 수
n_inst = len(CONN)
n_nets = len(nets)
n_nc = sum(len(v) for v in unused.values())
n_conn_pins = sum(len(m) for m in nets.values())

# ── 파일 쓰기
STAMP = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
HDR = f'chip_core {A.tag} — mk_top.py {STAMP}, col_blk = {COLD}, arr = {A.arr}'
(NET / 'lib').mkdir(exist_ok=True)


def wrap(s, w=120):
    out, cur = [], ''
    for tok in s.split(' '):
        if cur and len(cur) + len(tok) + 1 > w:
            out.append(cur)
            cur = '    ' + tok
        else:
            cur = (cur + ' ' + tok) if cur else tok
    return '\n'.join(out + [cur])


def vname(n):
    return "1'b0" if n == TIE0 else n


def vports(cell):
    """Verilog port 목록 [(name, dir, (hi, lo) | None)] — PG 빼고, CDL 순서."""
    out, seen = [], {}
    for p in CELL[cell]['pins']:
        if CELL[cell]['dirs'][p] == 'pg':
            continue
        base, i, bus = split_pin(p)
        if bus:
            if base in seen:
                e = out[seen[base]]
                out[seen[base]] = (base, e[1], (max(e[2][0], i), min(e[2][1], i)))
            else:
                seen[base] = len(out)
                out.append((base, CELL[cell]['dirs'][p], (i, i)))
        else:
            out.append((p, CELL[cell]['dirs'][p], None))
    return out


def write_verilog(stubs):
    L = [f'// {HDR}', '// 구조 Verilog. 블록 = LEF macro (place/lef). PG 핀 (VDD VSS vdd vss VPWR VGND VPB VNB) 은 chip_core_pg.tcl 로 잇는다.',
         "// 1'b0 = VSS 에 묶음 (col_blk lo, 배열 wl_106–127): connect_global_net VSS -type tie_lo", '']
    if stubs:
        for cell in dict.fromkeys(c for _, c in INST):
            if BLK[cell].get('std'):
                continue                                  # hvl 표준 셀은 lib·LEF 셀 (빈 module 을 쓰지 않음)
            ps = vports(cell)
            L.append(wrap(f'module {cell} (' + ', '.join(p for p, _, _ in ps) + ');'))
            for p, d, w in ps:
                L.append(f'  {d} {"[%d:%d] " % w if w else ""}{p};')
            L += ['endmodule', '']
    sig = [n for n in CORE if n not in PG_NETS]
    L.append(wrap('module chip_core (' + ', '.join(sig) + ');'))
    for n in sig:
        L.append(f'  {CORE_DIR.get(n, "inout")} {n};')
    for n in nets:
        if n not in CORE and n not in PG_NETS:
            L.append(f'  wire {n};')
    L.append('')
    for inst, (cell, pl) in CONN.items():
        net = dict(pl)
        items = []
        for p, d, w in vports(cell):
            if w:
                bits = [net[f'{p}[{k}]'] for k in range(w[0], w[1] - 1, -1)]
                if all(b is None for b in bits):
                    items.append(f'.{p}()')
                else:
                    if any(b is None for b in bits):
                        raise SystemExit(f'{inst}.{p}: 버스 일부만 떠 있음 (nc wire 필요)')
                    items.append(f'.{p}({{' + ', '.join(vname(b) for b in bits) + '})')
            else:
                b = net[p]
                items.append(f'.{p}({vname(b) if b is not None else ""})')
        if not items:
            L.append(f'  {cell} {inst} ();')
            continue
        L.append(f'  {cell} {inst} (')
        L.append(',\n'.join('    ' + s for s in items))
        L.append('  );')
    L += ['endmodule', '']
    return '\n'.join(L)


(NET / 'chip_core.v').write_text(write_verilog(True))
(NET / 'chip_core_top.v').write_text(write_verilog(False))

# PG tcl
T = [f'# {HDR}', '# Innovus (Stylus) — chip_core.v 를 읽은 뒤. 블록 LEF 의 VDD·VSS·vdd·vss 는 USE POWER/GROUND 여야 한다.']
for n, ps in (('VDD', ['VDD', 'vdd', 'VPWR', 'VPB']), ('VSS', ['VSS', 'vss', 'VGND', 'VNB'])):
    for p in ps:
        T.append(f'connect_global_net {n} -type pg_pin -pin_base_name {p} -all')
T.append("connect_global_net VSS -type tie_lo -all   ;# 1'b0: " + ', '.join(f'{i}.{"/".join(v) if len(v) < 4 else v[0] + "…" + v[-1]}' for i, v in ties.items()))
if 'VCM' in PG_NETS:
    T += [f'connect_global_net VCM -type pg_pin -pin_base_name {p} -all' for p in ('vzero', 'vcm')]
(NET / 'chip_core_pg.tcl').write_text('\n'.join(T) + '\n')

# CDL: include 정리 (같은 내용 파일은 한 번, nested include 는 사본에서 주석)
inc_files = collections.OrderedDict()   # 원본 (로컬) → lib/ 사본
blk_inc = collections.OrderedDict()     # cell → (원본, lib/ 사본)
hash_seen = {}
for old in (NET / 'lib').glob('*.cdl'):
    old.unlink()                        # 지난 판 사본 (이번 판에 없는 것이 남지 않게)


def oly(p):
    s = str(Path(p).resolve())
    return s.replace(str(EPDR.resolve()), A.cdl_root)


DEFS = {}        # subckt 이름 (소문자) → (내용 hash, 처음 정의한 파일)
DROPPED = []     # 앞 파일과 같은 내용이라 사본에서 뺀 subckt
CONFLICT = []    # 이름은 같은데 내용이 다른 subckt (사본에서 빼고 앞 정의를 씀 — check_report 에 남김)


def body_hash(lines):
    return hashlib.md5('\n'.join(re.sub(r'\s+', ' ', x.strip()).lower() for x in lines
                                  if x.strip() and not x.lstrip().startswith('*')).encode()).hexdigest()


def to_lib(src, note):
    """src CDL 을 lib/ 에 복사: .INCLUDE 는 주석, 앞에서 이미 정의한 subckt 는 뺀다 (test pattern 마다 tp_nacc·hvl 셀을 다시 정의하는 것 등).
    Olympus 와 로컬 폴더 구성이 달라도 net/ 하나만 옮기면 되게."""
    cp = NET / 'lib' / src.name
    if cp.exists():
        cp = NET / 'lib' / f'{src.parent.name}__{src.name}'
    out, blk = [], None
    for ln in cdl_lines(src):
        t = ln.split()
        k = t[0].lower() if t else ''
        if k in ('.include', '.inc'):
            out.append('*(chip_core.cdl 이 한 번만 include) ' + ln)
        elif k == '.subckt':
            blk = [ln]
        elif blk is not None:
            blk.append(ln)
            if k.startswith('.ends'):
                name = blk[0].split()[1]
                h = body_hash(blk)
                if name.lower() in DEFS:
                    h0, f0 = DEFS[name.lower()]
                    (DROPPED if h0 == h else CONFLICT).append(f'{name} ({src.name}, 앞 정의 {f0})')
                    out.append(f'* subckt {name} 뺌 — 앞 include {f0} 에 {"같은 내용" if h0 == h else "**다른 내용**"} 이 있음')
                else:
                    DEFS[name.lower()] = (h, src.name)
                    out += blk
                blk = None
        else:
            out.append(ln)
    cp.write_text(f'* {cp.name} — 사본 ({note}), 원본 {src.relative_to(EPDR) if str(src).startswith(str(EPDR)) else src}, mk_top.py {STAMP}\n'
                  + '\n'.join(out) + '\n')
    return cp


for cell in dict.fromkeys(c for _, c in INST):
    b = BLK[cell]
    if b.get('stub') is not None:
        continue
    f = P(b['cdl'])
    for q in ([f] if b.get('std') else includes(f)):
        h = hashlib.md5(q.read_bytes()).hexdigest()
        if h in hash_seen:
            continue
        hash_seen[h] = q
        inc_files[q] = to_lib(q, 'include 를 한 번만')
    if not b.get('std'):
        blk_inc[cell] = (f, to_lib(f, '.INCLUDE 주석' if includes(f) else '그대로'))
stub_cells = [t for t in TPS if TP_SRC[t] == 'stub']
if stub_cells:
    sp_ = NET / 'lib' / 'tp_stub.cdl'
    sp_.write_text(f'* test pattern 빈 subckt (testpat/ 결과 전, mk_top.py {STAMP})\n'
                   + ''.join(f'.SUBCKT {t} VDD VSS\n.ENDS {t}\n' for t in stub_cells))
    blk_inc['tp_stub'] = (sp_, sp_)
# 이름 겹침 검사 (include 를 모두 풀어서)
alldef = collections.defaultdict(list)
for lp in list(inc_files.values()) + [c for _, c in blk_inc.values()]:
    for n, v in subckts(lp).items():                     # lib/ 사본은 nested include 가 주석이라 자기 정의만
        alldef[n].append((lp, hashlib.md5(v[1].encode()).hexdigest()))
dup = {n: v for n, v in alldef.items() if len(v) > 1}
dup_conflict = {n: v for n, v in dup.items() if len({h for _, h in v}) > 1}

C = [f'* {HDR}', '* LVS source. 블록 CDL 의 .SUBCKT 핀 순서대로 연결. 1\'b0 (lo, wl_106–127) = VSS.', '']
C += [f'.INCLUDE {oly(c)}' for c in inc_files.values()]
C += [f'.INCLUDE {oly(c)}' for _, c in blk_inc.values()]
C.append('')
C.append('.SUBCKT chip_core ' + ' '.join(CORE))
for inst, (cell, pl) in CONN.items():
    ns = []
    for pin, n in pl:
        if n is None:
            ns.append(re.sub(r'[\[\]]', '_', f'nc_{inst}_{pin}').rstrip('_'))
        else:
            ns.append('VSS' if n == TIE0 else n)
    s = f'X{inst} ' + ' '.join(ns) + f' {cell}'
    # 줄 나누기 (+ 이음)
    out, cur = [], ''
    for tok in s.split():
        if len(cur) + len(tok) > 200:
            out.append(cur)
            cur = '+ ' + tok
        else:
            cur = (cur + ' ' + tok) if cur else tok
    out.append(cur)
    C += out
C += ['.ENDS chip_core', '']
(NET / 'chip_core.cdl').write_text('\n'.join(C))

# pins.json
OX, OY = FP['core']['offset_in_die']
CW, CH = FP['core']['w'], FP['core']['h']


def edge_pt(pd):
    x0, y0, x1, y1 = pd['rect']
    cx, cy = (x0 + x1) / 2 - OX, (y0 + y1) / 2 - OY
    cl = lambda v, hi: round(min(max(v, 1.0), hi - 1.0), 3)
    return {'top': (cl(cx, CW), CH), 'bottom': (cl(cx, CW), 0.0), 'left': (0.0, cl(cy, CH)), 'right': (CW, cl(cy, CH))}[pd['side']], (round(cx, 3), round(cy, 3))


PJ = {'note': '(d3) core 핀 = 패드 이름. 좌표: pad_rect·pad_center = die µm, label_core = core 좌표 µm (core 왼쪽 아래 원점) 에서 패드 가운데를 그 변에 내린 점 '
              '(이름표 자리 제안, 끝 1 µm 안쪽으로 자름). 패드 ↔ core 배선은 하지 않음 (범위 (a)).',
      'made': STAMP, 'floorplan': 'layout/floorplan_opt_D3.json',
      'core': {'w': CW, 'h': CH, 'offset_in_die': [OX, OY]}, 'pins': collections.OrderedDict(),
      'renamed_spare': SPARE_MAP, 'pad_only_no_core_pin': PAD_ONLY, 'spare_unused': spares_left}
for n in CORE:
    src = n if n in pad_names else next((k for k, v in SPARE_MAP.items() if v == n), None)
    ent = []
    for pd in pad_names.get(src, []):
        lab, cc = edge_pt(pd)
        ent.append({'pad': pd['name'], 'cell': pd['cell'], 'side': pd['side'], 'pad_rect_die': pd['rect'],
                    'pad_center_core': cc, 'label_core': lab})
    PJ['pins'][n] = {'dir': CORE_DIR.get(n, 'inout'), 'kind': 'power' if n in CORE_PWR else
                     ('digital' if n in CORE_DIR else 'analog'), 'verilog_port': n not in PG_NETS,
                     'pads': ent, 'blocks': sorted({f'{i}.{p}' for i, p in nets[n]})}
    if n in SPARE_MAP.values():
        PJ['pins'][n]['from_spare'] = src
(NET / 'pins.json').write_text(json.dumps(PJ, indent=1, ensure_ascii=False))

# deck_map.tsv
with open(NET / 'deck_map.tsv', 'w') as fh:
    fh.write('# 덱 v3 node ↔ core 넷 — 덱 = ' + A.deck + f' ({STAMP}). 덱 블록·칩 블록: 그 넷에 닿는 블록 (_f/_n = 반쪽, _* = 덱에서 두 배열 공용)\n')
    fh.write('deck_node\tcore_net\tdeck_blocks\tcore_blocks\tstatus\tdeck_only\tcore_only\tshort\n')
    for r in DK['rows']:
        fh.write('\t'.join(r) + '\n')

# check_report.txt
rep(f'# check_report — {HDR}')
rep(f'인스턴스 {n_inst} (블록 {n_inst - 2} + hvl inv_2 2), 넷 {n_nets} (core 핀 {len(CORE)} 포함), 연결된 핀 {n_conn_pins}, 안 쓰는 핀 {n_nc}, VSS 에 묶은 핀 {sum(len(v) for v in ties.values())}')
rep('cell 별 인스턴스: ' + ', '.join(f'{c} ×{k}' for c, k in collections.Counter(c for _, c in INST).items()))
rep('')
rep('## 1. 안 쓰는 핀 (CDL 은 nc_<inst>_<pin> 넷, Verilog 는 빈 연결)')
for i, v in unused.items():
    rep(f'- {i} ({CONN[i][0]}): {len(v)} 개 — ' + (' '.join(v) if len(v) <= 12 else f'{v[0]} … {v[-1]}'))
rep('## 1b. VSS 에 묶은 핀 (Verilog 1\'b0)')
for i, v in ties.items():
    rep(f'- {i}: {len(v)} 개 — ' + (' '.join(v) if len(v) <= 6 else f'{v[0]} … {v[-1]}'))
rep(f'## 1c. 핀 하나만 닿는 넷 (core 핀 빼고): {len(dangling)} ' + ' '.join(dangling))
rep(f'## 1d. 블록이 안 닿는 core 핀: {len(nopin_core)} ' + ' '.join(nopin_core))
rep('')
rep(f'## 2. 한 넷에 출력 둘 이상 (core 입력 핀은 구동으로 셈): {len(multi)}')
for n, v in multi.items():
    rep(f'- {n}: ' + ' '.join(f'{i}.{p}' for i, p in v))
rep(f'## 2b. 구동 없는 넷 (입력만, core 핀 빼고): {len(nodrv)} ' + ' '.join(nodrv))
rep(f'## 2c. 대소문자만 다른 넷: {len(case_clash)} ' + ' '.join('/'.join(x) for x in case_clash))
rep('')
rep('## 3. core 핀 ↔ 패드 (floorplan_opt_D3.json pads 59)')
rep(f'- core 핀 {len(CORE)}: ' + ' '.join(CORE))
rep(f'- 패드 없는 core 핀: {len(core_vs_pad)} ' + '; '.join(core_vs_pad))
rep(f'- core 핀 없는 패드 이름 (예비·1.8 V 빼고): {len(pads_no_core)} ' + ' '.join(pads_no_core))
rep(f'- 예비 → core 핀: {SPARE_MAP}, 1.8 V pad ring 만 (core 핀 아님): {PAD_ONLY}, 남는 예비 {len(spares_left)}: ' + ' '.join(spares_left))
rep('- 같은 이름 패드 여럿: ' + ', '.join(f'{k} ×{len(v)}' for k, v in pad_names.items() if len(v) > 1))
rep('')
rep(f'## 4. 덱 v3 비교 ({A.deck}: 최상위 줄 {DK["n_top"]}, 블록에 넣은 소자 {DK["n_elem"]})')
rep(f'- 덱의 블록 경계 node {DK["n_bnd"]} 개 (블록 둘 이상·패드가 닿는 node). 같음 {DK["n_ok"]}, 덱과 일부러 다름 (DEVIATIONS) {DK["n_exp"]}, 예상 밖 {DK["n_bad"]}')
rep(f'- 배열 셀 (행 = TE, WL = 게이트, 열 = 소스, body = vss) 대응이 다른 셀: {DK["cell_bad"]}')
rep(f'- 덱 소자 중 블록을 못 정한 것: {len(DK["unk"])} ' + ' '.join(DK['unk'][:20]))
for r in DK['rows']:
    if not r[4].startswith('ok'):
        rep(f'  {r[0]:10s} → {r[1]:28s} {r[4]}  덱만: {r[5] or "-"}  칩만: {r[6] or "-"}  {("short: " + r[7]) if r[7] else ""}')
rep('')
rep(f'## 4b. place/ 와 맞춰 보기 (LEF 핀 = CDL 핀, 인스턴스): LEF {len(lef_chk)}, 인스턴스 {len(place_chk)}')
for x in lef_chk + place_chk:
    rep(f'- {x}')
rep('')
rep('## 5. CDL include')
rep('- chip_core.cdl 은 lib/ 사본만 include (Olympus ' + oly(NET / 'lib') + '). 원본:')
rep('  - 한 번씩 include: ' + ', '.join(str(q.relative_to(EPDR)) for q in inc_files))
rep('  - 블록: ' + ', '.join(f'{c}={o.relative_to(EPDR)}' for c, (o, _) in blk_inc.items()))
rep(f'- 사본에서 뺀 겹친 subckt (앞과 같은 내용): {len(DROPPED)} ' + ', '.join(DROPPED[:12]) + (' …' if len(DROPPED) > 12 else ''))
rep(f'- 이름 같고 내용 다른 subckt (앞 정의를 씀): {len(CONFLICT)} ' + ', '.join(CONFLICT))
rep(f'- lib/ 사본끼리 subckt 이름 겹침: {len(dup)} ' + ' '.join(dup))
(NET / 'check_report.txt').write_text('\n'.join(R) + '\n')

# DEVIATIONS.md (항목 본문은 아래 표, 숫자는 이번 실행)
DEV = [
    ('D1', '반쪽마다 한 벌 (d3)', '덱은 row token·ROWL decoder (`XFrow*`, `XRL*`), 열 token·COLL (`XFcol*`, `XCL*`), DATA (`XFd*`·`XLd*`·and2) 를 한 벌 두고 두 배열의 MUX·입력 구동이 같이 씀.',
     '`rowb_f`·`rowb_n`, `colb_f`·`colb_n`, `data_f`·`data_n` 이 각자 한 벌. SDI 는 같은 넷, 클록·제어는 glob_dig 의 `_f`·`_n` (같은 논리, 구동만 둘) → 두 벌이 같은 bit 를 가짐.',
     'floorplan (d3) 가 두 배열을 위·아래로 떼어 놓아 공용 decoder 출력 (행마다 12 가닥) 을 넘길 수 없음.'),
    ('D2', 'glob_dig 출력 `_f`·`_n`', '덱 node 하나 (`READ`, `PROG`, `row1_clk` …, 16 개).', 'core 넷 둘 (`READ_f`·`READ_n` …, 32 개). 반쪽 넷끼리는 이어지지 않음.',
     '반쪽마다 구동 셀 따로 (glob_dig README), 배선 길이·부하를 반쪽으로 나눔.'),
    ('D3', 'write buffer 배열마다', '덱 v3 도 `XWBf`·`XWBn` 두 개 (같은 wp·pol·VWH·VWLO).', '`wbuf_f`·`wbuf_n`, pol 은 `pol_f`·`pol_n` (D2).', '덱과 같음 (pol 만 D2 로 나뉨).'),
    ('D4', 'rst', '덱 DFFR 는 rst·rstb 둘 다 받음 → node `rst` 가 row·col·DATA 레지스터에 닿음.', 'RST 패드 → glob_dig `rst` 만. 다른 블록은 `rstb_f`·`rstb_n` 만.',
     'hvl `dfrtp` 는 RESET_B 하나뿐 (블록 LVS MATCH 판).'),
    ('D5', 'dload_b', '덱: glob latch qb → DATA latch clkb.', '넷 없음 (data_blk 의 `dlxtp` 는 GATE = dload 하나).', 'hvl latch 셀이 반대 클록을 셀 안에서 만듦.'),
    ('D6', 'col_blk `lo`', '덱 `Vlo lo 0 -2.5` (VSS 와 같은 전압의 따로 전원).', '`colb_f.lo`·`colb_n.lo` = VSS (Verilog `1\'b0` → `connect_global_net VSS -type tie_lo`).',
     'col_blk README: 남는 열 decoder 입력, VSS 에 묶음 (conb tie 셀은 LVS 가 깨져 안 씀).'),
    ('D7', 'LATB inverter', '덱 `XIlat lat latb vdd vss INV` (칩 안 inverter, 블록 없음).',
     '최상위 hvl `sky130_fd_sc_hvl__inv_2` 두 개 `ilatb1`·`ilatb2` (A = LAT, Y = `latb_1`/`latb_2` → `wu1`/`wu2` latb). place/ 가 WU lat·latb 핀 옆에 놓는다.',
     'wu 블록에 latb 입력 핀만 있고 inverter 를 가진 블록이 없음. WU 마다 하나면 latb 선이 짧고 두 WU 의 lat↔latb 어긋남이 같음. **조정 세션 확인 10/28** (추천안 채택). 뒤에 wu 블록 안으로 옮기면 (wu CDL 에 latb 핀이 없어지면) 이 둘을 지운다.'),
    ('D8', 'bias 전류 두 개', '덱 HOG_BIAS 안 이상 전류원 Ibn (vdd → vbn 5 µA), Ibp (vbp → vss 5 µA).',
     f'IBIAS 패드 = `vbn` (bias_beta·wu1·wu2), **새 core 핀 `IBIASP` = `vbp`, 예비 패드 {A.vbp_pad} 자리** (bias 블록에 가장 가까운 아래 변 예비).',
     'bias_beta 는 vbn·vbp 둘 다 핀으로 받고 칩 안에 Ibp 를 만드는 소자가 없음 → 패드 하나로는 두 전류를 못 줌. **조정 세션 확인 10/28** (추천안 채택: 밖에서 vbp 로부터 5 µA 를 뽑는 전류원을 IBIASP 에). floorplan 의 SPARE17 이름은 IBIASP 로 읽는다. (쓰지 않은 안: bias_beta 안 vbn 게이트 NMOS 미러 → `--vbp-pad none`)'),
    ('D9', '0 V (덱 node 0)', '덱 전역 node 0 (ROWM XT3, COLM XT1·SP TG, WU 의 저항·Cabs).', '`VCM` 패드 넷: `rowb_*.vzero`, `colb_*.vzero`, `wu*.vcm`.', 'VCM = 0 V 아날로그 기준 (layout README).'),
    ('D10', 'free DATA 의 sp/spb/sm/smb', '덱: DATA 한 벌의 sp/sm → nudge 주입기.', '`ninj` ← `data_n` 만. `data_f` 의 sp/spb/sm/smb 12 핀은 뜬 출력.',
     '주입기는 nudge 배열만 (같은 data_blk 를 두 번 쓰려고 그대로 둠, blk_digital README).'),
    ('D11', 'WU 관측 출력', '덱 `sen1 absf1 absn1 q1a q2a` 등 (측정용 node).', 'wu1·wu2 의 `sen absf absn q1 q2` 10 핀 뜬 출력 (패드 없음).', '패드에 낼 자리가 없고 동작에 필요 없음.'),
    ('D12', '배열의 안 쓰는 행·열', '덱은 행 0–105 만 (128 중), 열 0–63 모두.',
     '배열 행 106–127: `wl_106`–`wl_127` = VSS (접근 nFET 꺼짐), `row_106`–`row_127` = 떠 있음 (nc). 열 64 개 모두 col_blk (hidden 0–59 = clamp, 60–63 = col_blk 안 SP TG 가 READ 때 VCM).',
     'row_blk·input_drive 핀이 106·100 행뿐. 꺼진 nFET 뒤 셀은 전압이 걸리지 않음.'),
    ('D13', 'test pattern 4 개', '덱에 없음.', '`tp_tl tp_br tp_bandl tp_bandr`: testpat/ 결과가 없으면 VDD·VSS 만 가진 빈 subckt (`lib/tp_stub.cdl`), 있으면 그 CDL 핀으로 (패드 이름과 같은 핀은 그 core 핀, 나머지 nc).',
     '신호 핀 (구조 셀 단자) 은 패드에 잇지 않음 — 사용자 (testpat/gen_tp.py): 「그려만 놓고 pad 연결은 안해놓아도 되지 뭐」. 같은 이름 구조 subckt (tp_nacc 등) 는 lib/ 사본에서 한 번만.'),
    ('D14', '패드 ↔ core 핀', '덱: 패드 21 개 + 전원.', 'core 핀 = 패드 이름 (같은 이름 패드 여럿은 core 핀 하나: VRAILP·VRAILM ×2, VCM ×2, VDD·VSS 여럿). VDDL·VSSL (1.8 V pad ring) 은 core 핀 아님. floorplan 의 「global digital (1.8 V)」 사각형은 인스턴스 없음.',
     '범위 (a): 패드 ↔ core 배선 안 함. core 안은 모두 VDD/VSS (±2.5 V) hvl.'),
    ('D15', '덱의 모형·계측 소자', '`C*` (선 부하·패드), `Cb*`·`Cvw*`, `Vver*`, `Cpad`·`Rpad`, 셀 sinh/VA 모형, 이상 전원.', '없음 (실제 블록이 대신).', '시뮬레이션용.'),
    ('D16', 'PG (Verilog)', '—', 'Verilog 에 VDD·VSS 핀 없음 (`chip_core_pg.tcl` 의 connect_global_net). VCM 은 신호 넷 (`--pg VDD,VSS,VCM` 이면 PG 로).', 'row_blk·col_blk Innovus 흐름과 같은 방식.'),
]
D = [f'# DEVIATIONS — chip_core netlist vs 덱 v3 (`real_circuit/gen_chip_deck3.py`)', '',
     f'만든 때 {STAMP} (`mk_top.py`, 손으로 고치지 않음). 비교 덱 = `{A.deck}` (gen_chip_deck3.py 출력, 칩 회로 줄은 read·write 시험이 같음).', '',
     f'**덱 비교 결과**: 덱의 블록 경계 node {DK["n_bnd"]} 개 중 같음 {DK["n_ok"]}, 아래 항목대로 일부러 다름 {DK["n_exp"]}, **예상 밖 {DK["n_bad"]}**. '
     f'배열 셀 대응 틀림 {DK["cell_bad"]}. 표 = `deck_map.tsv`, 자세히 = `check_report.txt` §4.', '',
     '| # | 무엇 | 덱 v3 | core netlist | 이유 |', '|---|---|---|---|---|']
D += [f'| {a} | {b} | {c} | {d} | {e} |' for a, b, c, d, e in DEV]
D += ['', '## 이번 실행에서 덱과 다르게 나온 node (모두 위 항목)', '']
D += [f'- `{r[0]}` → {r[1]}: {r[4]} — 덱만 {r[5] or "-"} / 칩만 {r[6] or "-"}' + (f' / 한 넷: {r[7]}' if r[7] else '') for r in DK['rows'] if not r[4].startswith('ok')]
D += ['', '## 안 쓰는 블록 핀', ''] + [f'- `{i}`: {len(v)} — ' + (' '.join(v) if len(v) <= 12 else f'{v[0]} … {v[-1]}') for i, v in unused.items()]
(NET / 'DEVIATIONS.md').write_text('\n'.join(D) + '\n')

# 요약
print(HDR)
print(f'인스턴스 {n_inst}, 넷 {n_nets}, 안 쓰는 핀 {n_nc}, VSS 묶음 {sum(len(v) for v in ties.values())}, 핀 하나 넷 {len(dangling)}, 출력 둘 이상 {len(multi)}, 구동 없음 {len(nodrv)}, 대소문자 겹침 {len(case_clash)}')
print(f'패드 없는 core 핀 {len(core_vs_pad)}, core 핀 없는 패드 {len(pads_no_core)}, lib/ subckt 겹침 {len(dup)}, 뺀 중복 {len(DROPPED)}, 내용 다른 중복 {len(CONFLICT)}')
print('place/ 대조: ' + ('; '.join(lef_chk + place_chk) or '모두 같음'))
print(f'deck check: boundary nodes {DK["n_bnd"]}, same {DK["n_ok"]}, intentionally different {DK["n_exp"]}, unexpected {DK["n_bad"]}, wrong cell mapping {DK["cell_bad"]}, unclassified devices {len(DK["unk"])}')
for k in DK['issues']:
    print('  MISMATCH', k)
if A.push:
    import subprocess
    fl = ['chip_core.v', 'chip_core_top.v', 'chip_core.cdl', 'chip_core_pg.tcl', 'pins.json', 'deck_map.tsv', 'check_report.txt',
          'DEVIATIONS.md', 'mk_top.py', 'README.md', 'lib']
    dst = A.cdl_root.replace('/home/grads/s/seokjindaveoh/', '~/') + '/layout/top/net/'
    subprocess.run(['ssh', '-o', 'BatchMode=yes', 'olympus', f'mkdir -p {dst} && rm -f {dst}lib/*.cdl'], check=True, timeout=120)
    subprocess.run(['scp', '-q', '-r'] + [str(NET / f) for f in fl if (NET / f).exists()] + [f'olympus:{dst}'], check=True, timeout=300)
    print(f'push → olympus:{dst}')

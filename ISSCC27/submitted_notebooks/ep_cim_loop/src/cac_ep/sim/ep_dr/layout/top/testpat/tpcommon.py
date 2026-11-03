"""testpat 공통부 (10/28) — 층 표, 5 nm 격자, 상자·라벨·via 쌓기, 구조 셀 약속 (Struct), 단독 시험 GDS·CDL 쓰기.

구조 셀 약속 (s_*.py 생성기가 지킴, gen_tp.py 가 블록으로 조립):
  - 셀 이름은 'tp_' 로 시작 (칩 GDS 합칠 때 다른 블록 셀과 이름이 겹치지 않게). hvl 표준 셀 (sky130_fd_sc_hvl__*) 은 그대로 둔다.
  - 모든 도형 (well·implant·hvi 포함) 이 [0, W] × [0, H] 안 (서쪽 끝 = x 0, 아래 끝은 y ≥ 0).
  - 신호 단자 = 서쪽 변 (x = 0) 에 닿는 met3 패드 (Struct.sig_pin). 높이 0.5, 폭 PIN_W, 중심 간격 ≥ PIN_PITCH.
  - 전원 단자 (VDD·VSS) = 동쪽 변 (x = W) 에 닿는 met3 패드 (Struct.pwr_pin). 조립기가 동쪽에 met3 줄을 이어 블록 전원 기둥 (met2) 에 via2 로 붙인다.
  - 셀 안에는 라벨을 두지 않는다 (라벨은 블록 top 에서). 단독 시험은 write_standalone() 이 감싸는 셀에 라벨을 붙인다.
  - 기판 (p-sub) 은 VSS: 소자가 있는 셀은 p-tap 을 두고 VSS 패드에 잇는다.
  - CDL: Struct.cdl = 소자 줄 (포트 이름 = Struct.ports), Struct.extra = 같이 넣을 subckt 정의 (hvl 셀 등).
쓰임: from tpcommon import *
"""
import json
import re
import subprocess
import time
from pathlib import Path

import klayout.db as db

TP = Path(__file__).resolve().parent
OUT = TP / 'out'
REMOTE = 'olympus'
RTP = '~/work/ep_dr/layout/top/testpat'
HVL_CDL = TP.parents[2] / 'digital' / 'pdk' / 'sky130_fd_sc_hvl_u.cdl'     # w/l 에 u 붙인 사본 (digital/mk_pdk.py)
HVL_GDS = Path('/home/dave/pdk/volare/sky130A/libs.ref/sky130_fd_sc_hvl/gds/sky130_fd_sc_hvl.gds')

LAY = dict(nwell=(64, 20), diff=(65, 20), tap=(65, 44), poly=(66, 20), licon=(66, 44), li1=(67, 20), mcon=(67, 44),
           met1=(68, 20), via1=(68, 44), met2=(69, 20), via2=(69, 44), met3=(70, 20), via3=(70, 44), met4=(71, 20),
           nsdm=(93, 44), psdm=(94, 20), npc=(95, 20), hvi=(75, 20), rpm=(86, 20), urpm=(79, 20),
           poly_res=(66, 13), diff_res=(65, 13), met1_res=(68, 13), met2_res=(69, 13), met3_res=(70, 13),
           reram=(230, 20), areaid_de=(81, 23),
           lbl_li1=(67, 5), lbl_met1=(68, 5), lbl_met2=(69, 5), lbl_met3=(70, 5))
GRID = 0.005
PIN_W, PIN_H, PIN_PITCH = 1.0, 0.5, 1.0        # 신호 패드 (met3) 폭·높이·최소 중심 간격
PWR_W = 1.0                                    # 전원 패드 폭 (동쪽 변)

# via 쌓기 크기 (DRC rev 0.0_2.12): cut, 아래 금속 둘레, 위 금속 둘레 (한 변 쪽 큰 값으로 사방을 덮어 단순하게)
VIA = {('li1', 'met1'): ('mcon', 0.17, 0.0, 0.06),     # li 는 mcon 을 0 이상 감쌈, met1 0.03 / 한쪽 0.06
       ('met1', 'met2'): ('via1', 0.15, 0.085, 0.085),
       ('met2', 'met3'): ('via2', 0.20, 0.085, 0.065),
       ('met3', 'met4'): ('via3', 0.20, 0.09, 0.065)}
STACK = ['li1', 'met1', 'met2', 'met3', 'met4']
MINW = dict(li1=0.17, met1=0.14, met2=0.14, met3=0.30, met4=0.30)
MINAREA = dict(li1=0.0561, met1=0.083, met2=0.067, met3=0.24, met4=0.24)


def g(v):
    """µm → 5 nm 격자."""
    return round(round(v / GRID) * GRID, 3)


def nm(v):
    n = int(round(v * 1000))
    assert n % 5 == 0, f'off-grid {v}'
    return n


class Struct:
    """test 구조 셀 하나. 좌표는 µm (5 nm 격자 위여야 함)."""

    def __init__(self, ly, name, contents='', source=''):
        assert name.startswith('tp_'), name
        self.ly, self.name, self.contents, self.source = ly, name, contents, source
        self.c = ly.create_cell(name)
        self.ports, self.pins, self.cdl, self.extra = [], {}, [], []
        self.L = {k: ly.layer(*v) for k, v in LAY.items()}

    # 도형
    def box(self, lay, x0, y0, x1, y1):
        b = db.Box(nm(g(min(x0, x1))), nm(g(min(y0, y1))), nm(g(max(x0, x1))), nm(g(max(y0, y1))))
        self.c.shapes(self.L[lay]).insert(b)
        return b

    def cut(self, lay, x, y, s):
        self.box(lay, x - s / 2, y - s / 2, x + s / 2, y + s / 2)

    def via(self, x, y, lo, hi, pad=None):
        """(x, y) 에 lo 금속 → hi 금속 via 쌓기 + 금속 패드 (최소 면적을 맞춘 정사각). lo 가 li1 이면 li1 패드도 그림."""
        i0, i1 = STACK.index(lo), STACK.index(hi)
        for k in range(i0, i1):
            a, b = STACK[k], STACK[k + 1]
            cutl, s, ea, eb = VIA[(a, b)]
            self.cut(cutl, x, y, s)
            for m, e in ((a, ea), (b, eb)):
                h = max(s / 2 + e, MINW[m] / 2, (MINAREA[m] ** 0.5) / 2 + 0.005)
                if pad and m in pad:
                    h = max(h, pad[m] / 2)
                h = g(h + 0.0025) if g(h) < h else g(h)
                self.box(m, x - h, y - h, x + h, y + h)

    def inst(self, cell, x=0.0, y=0.0, rot=0, mirror=False):
        t = db.Trans(rot, mirror, nm(g(x)), nm(g(y)))
        self.c.insert(db.CellInstArray(cell.cell_index(), t))

    # 단자
    def sig_pin(self, port, y, w=PIN_W):
        """서쪽 변 신호 패드 (met3) — 중심 y. 안쪽 연결은 생성기가 met3 로 패드에 닿게 그린다."""
        assert port not in self.pins, port
        self.box('met3', 0.0, y - PIN_H / 2, w, y + PIN_H / 2)
        self.ports.append(port)
        self.pins[port] = dict(side='W', layer='met3', box=[0.0, g(y - PIN_H / 2), g(w), g(y + PIN_H / 2)])

    def pwr_pin(self, port, xr, y, h=1.0):
        """동쪽 변 전원 패드 (met3), x = xr 이 셀 동쪽 끝이 되게. port = 'VDD' 또는 'VSS'. 같은 이름 여러 개 가능."""
        assert port in ('VDD', 'VSS'), port
        self.box('met3', xr - PWR_W, y - h / 2, xr, y + h / 2)
        if port not in self.ports:
            self.ports.append(port)
        self.pins.setdefault(port, dict(side='E', layer='met3', boxes=[]))['boxes'].append(
            [g(xr - PWR_W), g(y - h / 2), g(xr), g(y + h / 2)])

    def bbox(self):
        b = self.c.dbbox()
        return [round(b.left, 3), round(b.bottom, 3), round(b.right, 3), round(b.top, 3)]

    def check(self):
        """약속 확인: 원점 (0, 0), 서쪽 패드 x = 0, 동쪽 패드 x = W, 패드 간격."""
        x0, y0, x1, y1 = self.bbox()
        assert abs(x0) < 1e-6 and y0 > -1e-6, (self.name, 'bbox 가 x = 0 에서 시작하지 않거나 y < 0', self.bbox())
        ys = sorted((p['box'][1] + p['box'][3]) / 2 for p in self.pins.values() if p['side'] == 'W')
        for a, b in zip(ys, ys[1:]):
            assert b - a >= PIN_PITCH - 1e-6, (self.name, '신호 패드 간격', a, b)
        for k in ('VDD', 'VSS'):
            for bx in self.pins.get(k, {}).get('boxes', []):
                assert abs(bx[2] - x1) < 1e-6, (self.name, k, '전원 패드가 동쪽 끝에 없음', bx, x1)
        return self

    def subckt(self):
        return [f'.subckt {self.name} ' + ' '.join(self.ports)] + self.cdl + [f'.ends {self.name}']

    def info(self):
        x0, y0, x1, y1 = self.bbox()
        return dict(cell=self.name, w=x1, h=y1, ports=self.ports, pins=self.pins, contents=self.contents, source=self.source)


def load_hvl(ly):
    """hvl 표준 셀 GDS 를 ly 에 한 번만 읽음 (이미 있으면 그대로). 반환: 이름 → Cell ('inv_1' 등 접두어 없이)."""
    if not ly.has_cell('sky130_fd_sc_hvl__inv_1'):
        o = db.LoadLayoutOptions(); o.cell_conflict_resolution = db.LoadLayoutOptions.SkipNewCell
        ly.read(str(HVL_GDS), o)
    return {c.name[len('sky130_fd_sc_hvl__'):]: c for c in ly.each_cell() if c.name.startswith('sky130_fd_sc_hvl__')}


def hvl_subckts(names):
    """hvl CDL 사본에서 필요한 subckt 정의만 (이름: 'inv_1' 등)."""
    t = HVL_CDL.read_text()
    out = []
    for n in names:
        m = re.search(r'^\.SUBCKT sky130_fd_sc_hvl__%s .*?^\.ENDS sky130_fd_sc_hvl__%s\s*$' % (n, n), t, re.M | re.S)
        assert m, n
        out.append(m.group(0))
    return out


def write_standalone(ly, structs, name, extra_cells=()):
    """단독 시험: 구조 셀들을 세로로 쌓은 감싸는 셀 name (라벨 포함) → out/name.gds, .cdl.
    라벨 이름 = <구조 이름>.<포트> 대신 포트 이름 앞에 구조 번호를 붙임 (s0_te …). 전원 패드는 동쪽 끝 met3 기둥으로 묶음."""
    T = ly.create_cell(name)
    L = {k: ly.layer(*v) for k, v in LAY.items()}
    y, top_ports, body, extra = 0.0, [], [], []
    xmax = max(s.bbox()[2] for s in structs)
    xp = g(xmax + 2.0)                                            # 전원 기둥 (met3 세로) x
    rails = {'VSS': (xp, xp + 1.0), 'VDD': (xp + 2.0, xp + 3.0)}
    used = set()
    for i, s in enumerate(structs):
        s.check()
        T.insert(db.CellInstArray(s.c.cell_index(), db.Trans(0, nm(g(y)))))
        conn = []
        for p in s.ports:
            if p in ('VDD', 'VSS'):
                conn.append(p); used.add(p)
                for bx in s.pins[p]['boxes']:
                    # 패드 → 기둥: VSS 는 met3 로 바로, VDD 는 VSS 기둥을 met2 로 넘음
                    ra, rb = rails[p]
                    yc = (bx[1] + bx[3]) / 2 + y
                    if p == 'VSS':
                        T.shapes(L['met3']).insert(db.Box(nm(bx[2]), nm(g(yc - 0.25)), nm(rb), nm(g(yc + 0.25))))
                    else:
                        T.shapes(L['met3']).insert(db.Box(nm(g(bx[2] - 0.6)), nm(g(yc - 0.25)), nm(g(bx[2] + 0.7)), nm(g(yc + 0.25))))
                        xv1, xv2 = g(bx[2] + 0.4), g((ra + rb) / 2)          # via2 는 셀 밖 (셀 안 met2 와 닿지 않게)
                        for xv in (xv1, xv2):
                            T.shapes(L['via2']).insert(db.Box(nm(g(xv - 0.1)), nm(g(yc - 0.1)), nm(g(xv + 0.1)), nm(g(yc + 0.1))))
                        T.shapes(L['met2']).insert(db.Box(nm(g(xv1 - 0.185)), nm(g(yc - 0.185)), nm(g(xv2 + 0.185)), nm(g(yc + 0.185))))
            else:
                lbl = f's{i}_{p}'
                conn.append(lbl); top_ports.append(lbl)
                bx = s.pins[p]['box']
                T.shapes(L['lbl_met3']).insert(db.Text(lbl, db.Trans(nm(g((bx[0] + bx[2]) / 2)), nm(g((bx[1] + bx[3]) / 2 + y)))))
        body.append(f'X{i} ' + ' '.join(conn) + f' {s.name}')
        for e in s.extra:
            if e not in extra:
                extra.append(e)
        y = g(y + s.bbox()[3] + 3.0)
    for p in sorted(used):
        ra, rb = rails[p]
        T.shapes(L['met3']).insert(db.Box(nm(ra), 0, nm(rb), nm(g(y))))
        T.shapes(L['lbl_met3']).insert(db.Text(p, db.Trans(nm(g((ra + rb) / 2)), nm(g(y - 1.0)))))
        top_ports.append(p)
    ly.write(str(OUT / f'{name}.gds'), _save_opts(ly, T))
    lines = ['* testpat 단독 시험 ' + name] + extra
    for s in structs:
        lines += s.subckt()
    lines += [f'.subckt {name} ' + ' '.join(top_ports)] + body + [f'.ends {name}']
    (OUT / f'{name}.cdl').write_text('\n'.join(lines) + '\n')
    return T


def _save_opts(ly, top):
    so = db.SaveLayoutOptions()
    so.add_cell(top.cell_index())
    return so


# ── Olympus 제출·결과 (scp → sbatch → 기다림 → 요약)
DENS = re.compile(r'^(CDR|CDRW)\.[\w]+\.(local|global)\.(min|max|low|high)$')


def submit(name, deck=None, no_lvs=False, t='00:20:00'):
    subprocess.run(['scp', '-q', str(OUT / f'{name}.gds'), str(OUT / f'{name}.cdl'), f'{REMOTE}:{RTP}/out/'], check=True)
    subprocess.run(['scp', '-q', str(TP / 'signoff_tp.sbatch'), str(TP / 'sky130_tp.lvs.pvl'), f'{REMOTE}:{RTP}/'], check=True)
    env = f'NAME={name}' + (f' LVS_DECK={deck}' if deck else '') + (' NO_LVS=1' if no_lvs else '')
    r = subprocess.run(['ssh', REMOTE, f'cd {RTP} && {env} sbatch -t {t} signoff_tp.sbatch'], check=True, capture_output=True, text=True)
    return r.stdout.strip().split()[-1]


def wait(jid, poll=60, tmax=1800):          # 상태 확인 60 s 간격 이상 (조정 세션 10/28 07:15)
    t0 = time.time()
    while time.time() - t0 < tmax:
        r = subprocess.run(['ssh', REMOTE, f'squeue -h -j {jid} 2>/dev/null | wc -l'], capture_output=True, text=True)
        if r.stdout.strip() == '0':
            break
        time.sleep(poll)
    r = subprocess.run(['ssh', REMOTE, f'cat {RTP}/logs/tp_sign_{jid}.out'], capture_output=True, text=True)
    return r.stdout


def summary(log):
    """로그 → (밀도 말고 DRC 규칙 목록, LVS 결과 문자열)."""
    bad = []
    for ln in log.splitlines():
        m = re.match(r'^RULECHECK (\S+) \.+ Total Result\s+(\d+)', ln)
        if m and int(m.group(2)) > 0 and not DENS.match(m.group(1)):
            bad.append((m.group(1), int(m.group(2))))
    m = re.search(r'Run Result\s*:\s*(\S+)', log)
    return bad, (m.group(1) if m else 'none')


def run(name, **kw):
    jid = submit(name, **kw)
    log = wait(jid)
    bad, lvs = summary(log)
    print(f'[{name}] job {jid}: DRC 밀도 말고 {len(bad)} 규칙 {bad[:20]} | LVS {lvs}')
    return jid, bad, lvs, log


if __name__ == '__main__':
    import sys
    run(sys.argv[1])

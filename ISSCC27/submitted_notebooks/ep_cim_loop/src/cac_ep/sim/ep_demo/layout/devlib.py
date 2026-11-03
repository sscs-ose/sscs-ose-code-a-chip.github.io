#!/usr/bin/env python3
"""5 V 소자(g5v0d10v5) 그리기 공통부 — SERN 11_layout/04_drc_clean/scripts/gen_neuron.py 의 소자 규칙을 옮긴 것.

규칙 (gen_neuron.py 에서 그대로, Magic drc(full) 0 건 이력):
  poly 핑거 세로, 폭 = L, 핑거 피치 = L + 0.290, 인접 핑거가 S/D 컬럼 공유
  S/D: li1 0.170, met1 0.230, licon·mcon 0.170, 컨택 세로 피치 0.360
  소스 스트랩(met1)은 블록 아래, 드레인 스트랩은 위, 게이트 버스(poly)는 드레인 스트랩 위
         hvi(75/20) — 셀 전체. hvntm 은 쓰지 않는다 (PDK 1T1R 셀도 없음)
좌표는 µm, 5 nm 격자로 맞춘다. 출력 GDS dbu = 1 nm.
"""
import klayout.db as pya

GRID = 0.005
SD, POH, STRAP, ENDM = 0.290, 0.285, 0.34, 0.25
SDW, M1SD, CPIT, CT = 0.170, 0.230, 0.360, 0.170
GSTRAP, M1G = (0.500, 0.360), (0.340, 0.340)
VIA1, P1 = 0.150, 0.330
BOT, GTOP, DTOP, BTAIL = 0.72, 0.86, 0.34, 0.30
NPC_ENC = 0.10
LAY = dict(nw=(64, 20), diff=(65, 20), tap=(65, 44), poly=(66, 20), licon=(66, 44), li1=(67, 20), mcon=(67, 44),
           m1=(68, 20), via=(68, 44), m2=(69, 20), via2=(69, 44), m3=(70, 20), nsd=(93, 44), psd=(94, 20),
           npc=(95, 20), hvi=(75, 20), diode=(81, 23), lbl_m1=(68, 5), lbl_m2=(69, 5), pin_m1=(68, 16),
           pin_m2=(69, 16), lbl_li=(67, 5), lbl_m3=(70, 5))


def g(v):
    return round(v / GRID) * GRID


class Cell:
    """도형 + 넷 기록. 같은 층 서로 다른 넷 겹침을 스스로 검사한다."""

    def __init__(self, ly, name):
        self.ly, self.c = ly, ly.create_cell(name)
        self.li = {k: ly.layer(*v) for k, v in LAY.items()}
        self.net = {}

    def um(self, v):
        return int(round(g(v) * 1000))

    def box(self, net, lay, x1, y1, x2, y2):
        b = pya.Box(self.um(min(x1, x2)), self.um(min(y1, y2)), self.um(max(x1, x2)), self.um(max(y1, y2)))
        self.c.shapes(self.li[lay]).insert(b)
        if net: self.net.setdefault(net, {}).setdefault(lay, pya.Region()).insert(b)
        return b

    def cut(self, net, lay, x, y, s=CT):
        return self.box(net, lay, x - s / 2, y - s / 2, x + s / 2, y + s / 2)

    def label(self, text, lay, x, y):
        self.c.shapes(self.li[lay]).insert(pya.Text(text, pya.Trans(self.um(x), self.um(y))))

    def via1(self, net, x, y):                          # met1 패드 + via + met2 패드
        self.box(net, 'm1', x - P1 / 2, y - P1 / 2, x + P1 / 2, y + P1 / 2)
        self.cut(net, 'via', x, y, VIA1)
        self.box(net, 'm2', x - P1 / 2, y - P1 / 2, x + P1 / 2, y + P1 / 2)

    def shorts(self):
        bad = []
        for lay in ('li1', 'm1', 'm2', 'poly', 'diff'):
            ns = [n for n in self.net if lay in self.net[n]]
            for i in range(len(ns)):
                for j in range(i + 1, len(ns)):
                    if not (self.net[ns[i]][lay] & self.net[ns[j]][lay]).is_empty():
                        bad.append((lay, ns[i], ns[j]))
        return bad


def plan(W, L, wmax):
    """셀 폭 wmax 안에 들어가는 최대 핑거 수 → (nf, 핑거 폭)."""
    p = L + SD
    nf = max(1, int((wmax - SD) // p))
    return nf, W / nf


def mos(C, typ, x0, y0, W, L, nf, s, d, gnet):
    """핑거 nf 개 소자. (x0, y0) = 블록 왼쪽 아래. 소스 스트랩 아래, 드레인 스트랩 위, 게이트 버스는 드레인 위.
    반환: dict(블록 범위, ys=소스 스트랩 y, yd=드레인 스트랩 y, gy=게이트 버스 y, 소자 정보)"""
    p = L + SD; Wf = W / nf
    dw = nf * p + SD
    yb = y0 + BOT; yt = yb + Wf
    C.box(None, 'diff', x0, yb, x0 + dw, yt)
    C.box(None, 'nsd' if typ == 'n' else 'psd', x0 - 0.125, yb - 0.125, x0 + dw + 0.125, yt + 0.125)
    srcs, drns = [], []
    usable = Wf - 0.12 - 0.17; nct = max(1, int(usable / CPIT) + 1)
    y00 = yb + 0.145 + (usable - (nct - 1) * CPIT) / 2
    for k in range(nf + 1):
        xc = x0 + SD / 2 + k * p
        net = s if k % 2 == 0 else d
        (srcs if k % 2 == 0 else drns).append(xc)
        C.box(net, 'li1', xc - SDW / 2, yb - 0.02, xc + SDW / 2, yt + 0.02)
        C.box(net, 'm1', xc - M1SD / 2, yb, xc + M1SD / 2, yt)
        for t in range(nct):
            yy = y00 + t * CPIT
            C.cut(net, 'licon', xc, yy); C.cut(net, 'mcon', xc, yy)
    gxs = [x0 + SD + p * k + L / 2 for k in range(nf)]
    for gx in gxs:
        C.box(gnet, 'poly', gx - L / 2, yb - POH, gx + L / 2, yt + POH)
    ys = y0 + BOT / 2                                   # 소스 스트랩 (아래)
    for xc in srcs: C.box(s, 'm1', xc - M1SD / 2, ys - STRAP / 2, xc + M1SD / 2, yb)
    C.box(s, 'm1', min(srcs) - M1SD / 2, ys - STRAP / 2, max(srcs) + M1SD / 2, ys + STRAP / 2)
    yd = yt + DTOP                                      # 드레인 스트랩 (위)
    if drns:
        for xc in drns: C.box(d, 'm1', xc - M1SD / 2, yt, xc + M1SD / 2, yd + STRAP / 2)
        C.box(d, 'm1', min(drns) - M1SD / 2, yd - STRAP / 2, max(drns) + M1SD / 2, yd + STRAP / 2)
    gy = yt + GTOP                                      # 게이트 버스 (poly 가로) + licon + npc + li1
    C.box(gnet, 'poly', min(gxs) - L / 2, gy - 0.18, max(gxs) + L / 2, gy + 0.18)
    for gx in gxs:
        C.box(gnet, 'poly', gx - L / 2, yt, gx + L / 2, gy)
        C.cut(gnet, 'licon', gx, gy)
    C.box(None, 'npc', min(gxs) - CT / 2 - NPC_ENC, gy - CT / 2 - NPC_ENC, max(gxs) + CT / 2 + NPC_ENC, gy + CT / 2 + NPC_ENC)
    C.box(gnet, 'li1', min(gxs) - GSTRAP[0] / 2, gy - GSTRAP[1] / 2, max(gxs) + GSTRAP[0] / 2, gy + GSTRAP[1] / 2)
    h = BOT + Wf + GTOP + BTAIL + 0.18
    return dict(x0=x0, x1=x0 + dw, y0=y0, y1=y0 + h, yb=yb, yt=yt, ys=ys, yd=yd, gy=gy, gxs=gxs,
                srcs=srcs, drns=drns, typ=typ, W=W, L=L, nf=nf, Wf=Wf, s=s, d=d, g=gnet)


def gate_pad(C, dev, x):
    """게이트 li1 스트랩 위 x 에 mcon + met1 패드 (스트랩 범위 안이어야 함)."""
    gy = dev['gy']
    C.cut(dev['g'], 'mcon', x, gy)
    C.box(dev['g'], 'm1', x - M1G[0] / 2, gy - M1G[1] / 2, x + M1G[0] / 2, gy + M1G[1] / 2)
    return x, gy


def tap(C, kind, x1, x2, yc, net):
    """기판/우물 탭 띠: kind 'p' = psub(VSS), 'n' = nwell(VDD). 컨택 + li1 + met1."""
    C.box(net, 'tap', x1, yc - 0.25, x2, yc + 0.25)
    C.box(None, 'psd' if kind == 'p' else 'nsd', x1 - 0.125, yc - 0.375, x2 + 0.125, yc + 0.375)
    C.box(net, 'li1', x1, yc - 0.25, x2, yc + 0.25)
    C.box(net, 'm1', x1, yc - 0.25, x2, yc + 0.25)
    n = max(1, int((x2 - x1 - 0.4) / CPIT) + 1)
    xs0 = x1 + (x2 - x1 - (n - 1) * CPIT) / 2
    for t in range(n):
        C.cut(net, 'licon', xs0 + t * CPIT, yc); C.cut(net, 'mcon', xs0 + t * CPIT, yc)


def finish(C):
    """hvi 를 셀 전체에. 반환 bbox (µm)."""
    r = pya.Region()
    for li in C.ly.layer_indexes(): r.insert(C.c.begin_shapes_rec(li))
    bb = r.bbox().enlarged(60, 60)                      # hvdifftap.22: hvi 가 diff/tap 을 0.18 이상 (implant 0.125 + 0.06)
    C.c.shapes(C.li['hvi']).insert(bb)
    return bb.left / 1000, bb.bottom / 1000, bb.right / 1000, bb.top / 1000


def cdl_mos(name, d, gnet, s, b, typ, W, L, nf):
    m = 'nfet_g5v0d10v5' if typ == 'n' else 'pfet_g5v0d10v5'
    return [f"M{name}_{k} {d} {gnet} {s} {b} {m} w={W/nf:.3f}u l={L:.3f}u" for k in range(nf)]

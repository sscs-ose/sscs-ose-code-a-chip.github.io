#!/usr/bin/env python3
"""WU 부품 셀 — netlist 정본 real_circuit/wu_lib.py primitives() (SA·PRE·DLATCH·TG) 와 wu_subckt() 의 R·C.

  sa    : StrongARM + inverter 분리 + SR NOR latch (트랜지스터 23 개, 크기는 wu_lib 그대로)
  pre   : COMP3 앞 전치 증폭기 (tail 4 × 0.9/1, 입력쌍 4/1 ABBA, PMOS 다이오드 부하 1/1)
  dlat  : dynamic D latch (TG + INV 2)
  tg3   : 증폭기 하나의 TG 3 개 (입력 + 쪽 · − 쪽 · 출력), 게이트 ctl/ctlb 공유. TG = N 2/0.5 (핑거 2 × 1.0) + P 4/0.5 (2 × 2.0)
  rbank : 증폭기 하나의 저항 4 개 (1 MΩ 2 + 2 MΩ 2) = res_xhigh_po_0p35 줄 18 개 (333.33 kΩ 씩, li1 로 직렬)
  mim   : cap_mim_m3_1 (met3 아랫판 + capm + met4 윗판, via3 로 윗판을 met3 착지 패드에 내림)
셀마다 build_*(ly) → (Cell, info).  info['cdl'] = subckt 줄, info['pins'] = 핀 (x, y) 와 레인.
"""
import math
import klayout.db as pya
import rowcell as RC
from rowcell import isl
from devlib import Cell, CPIT, g as gs

NAMES = dict(sa="wu_sa", pre="wu_pre", dlat="wu_dlat", tg3="wu_tg3", rbank="wu_rbank")

# ---------------- StrongARM (wu_lib SA) ----------------
SA_DEV = {  # 소자 → ('d g s', 형, W, L)
    "Mt": ("tl clk vss", "n", 1.0, 1.0), "M1": ("sp inp tl", "n", 4.0, 1.0), "M2": ("sn inn tl", "n", 4.0, 1.0),
    "M3": ("xo yo sp", "n", 2.0, 0.5), "M4": ("yo xo sn", "n", 2.0, 0.5),
    "M5": ("xo yo vdd", "p", 4.0, 0.5), "M6": ("yo xo vdd", "p", 4.0, 0.5),
    "S1": ("xo clk vdd", "p", 1.0, 0.5), "S2": ("yo clk vdd", "p", 1.0, 0.5),
    "S3": ("sp clk vdd", "p", 1.0, 0.5), "S4": ("sn clk vdd", "p", 1.0, 0.5),
    "B1n": ("xb xo vss", "n", 1.0, 0.5), "B1p": ("xb xo vdd", "p", 2.0, 0.5),
    "B2n": ("yb yo vss", "n", 1.0, 0.5), "B2p": ("yb yo vdd", "p", 2.0, 0.5),
    # NOR2 XL1 (a = yb, b = qb, y = q): XP1 m a vdd, XP2 y b m, XN1 y a vss, XN2 y b vss ; XL2 (a = xb, b = q, y = qb)
    "L1p1": ("m1 yb vdd", "p", 4.0, 0.5), "L1p2": ("q qb m1", "p", 4.0, 0.5),
    "L1n1": ("q yb vss", "n", 1.0, 0.5), "L1n2": ("q qb vss", "n", 1.0, 0.5),
    "L2p1": ("m2 xb vdd", "p", 4.0, 0.5), "L2p2": ("qb q m2", "p", 4.0, 0.5),
    "L2n1": ("qb xb vss", "n", 1.0, 0.5), "L2n2": ("qb q vss", "n", 1.0, 0.5),
}
SA_ROWS = [
    ("n_in", "n", [isl(1.0, 1.0, ["vss", "tl"], ["clk"], ["Mt"]),
                   isl(1.0, 2.0, ["sp", "tl", "sn", "tl", "sp"], ["inp", "inn", "inn", "inp"], ["M1", "M2", "M2", "M1"])],
     {"vss", "tl"}, "both"),
    ("n_log", "n", [isl(0.5, 2.0, ["sp", "xo"], ["yo"], ["M3"]), isl(0.5, 2.0, ["yo", "sn"], ["xo"], ["M4"]),
                    isl(0.5, 1.0, ["xb", "vss", "yb"], ["xo", "yo"], ["B1n", "B2n"]),
                    isl(0.5, 1.0, ["vss", "q", "vss", "qb", "vss"], ["yb", "qb", "q", "xb"], ["L1n1", "L1n2", "L2n2", "L2n1"])],
     {"vss"}, "both"),
    ("p_cc", "p", [isl(0.5, 1.0, ["sp", "vdd", "xo"], ["clk", "clk"], ["S3", "S1"]),
                   isl(0.5, 2.0, ["xo", "vdd", "xo"], ["yo", "yo"], ["M5", "M5"]),
                   isl(0.5, 2.0, ["yo", "vdd", "yo"], ["xo", "xo"], ["M6", "M6"]),
                   isl(0.5, 1.0, ["yo", "vdd", "sn"], ["clk", "clk"], ["S2", "S4"])],
     {"vdd"}, "both"),
    ("p_nor", "p", [isl(0.5, 2.0, ["xb", "vdd", "yb"], ["xo", "yo"], ["B1p", "B2p"]),
                    isl(0.5, 2.0, ["q", "m1", "vdd", "m1", "q"], ["qb", "yb", "yb", "qb"], ["L1p2", "L1p1", "L1p1", "L1p2"]),
                    isl(0.5, 2.0, ["qb", "m2", "vdd", "m2", "qb"], ["q", "xb", "xb", "q"], ["L2p2", "L2p1", "L2p1", "L2p2"])],
     {"vdd"}, "both"),
]
SA_PORTS = ["inp", "inn", "clk", "q", "qb", "vdd", "vss"]
SA_EXITS = {"inp": "top", "inn": "top", "q": "top", "qb": "top", "clk": "bot"}

# ---------------- 전치 증폭기 (wu_lib PRE) ----------------
PRE_DEV = {"Mt": ("tl vbn vss", "n", 3.6, 1.0), "M1": ("on inp tl", "n", 4.0, 1.0), "M2": ("op inn tl", "n", 4.0, 1.0),
           "L1": ("on on vdd", "p", 1.0, 1.0), "L2": ("op op vdd", "p", 1.0, 1.0)}
PRE_ROWS = [
    ("n_tail", "n", [isl(1.0, 0.9, ["vss", "tl", "vss", "tl", "vss"], ["vbn"] * 4, ["Mt"] * 4)], {"vss"}, "both"),
    ("n_pair", "n", [isl(1.0, 2.0, ["on", "tl", "op", "tl", "on"], ["inp", "inn", "inn", "inp"], ["M1", "M2", "M2", "M1"])], {"tl"}, None),
    ("p_load", "p", [isl(1.0, 1.0, ["on", "vdd", "op"], ["on", "op"], ["L1", "L2"])], {"vdd"}, "both"),
]
PRE_PORTS = ["inp", "inn", "op", "on", "vbn", "vdd", "vss"]
PRE_EXITS = {n: "top" for n in ("inp", "inn", "op", "on", "vbn")}

# ---------------- dynamic D latch (wu_lib DLATCH: TG d→s (clk / clkb) + INV s→qb + INV qb→q) ----------------
DL_DEV = {"Tn": ("s clk d", "n", 2.0, 0.5), "Tp": ("s clkb d", "p", 4.0, 0.5),
          "I1n": ("qb s vss", "n", 1.0, 0.5), "I1p": ("qb s vdd", "p", 2.0, 0.5),
          "I2n": ("q qb vss", "n", 1.0, 0.5), "I2p": ("q qb vdd", "p", 2.0, 0.5)}
DL_ROWS = [
    ("n", "n", [isl(0.5, 1.0, ["s", "d", "s"], ["clk", "clk"], ["Tn", "Tn"]),
                isl(0.5, 1.0, ["qb", "vss", "q"], ["s", "qb"], ["I1n", "I2n"])], {"vss", "d"}, "both"),
    ("p", "p", [isl(0.5, 2.0, ["s", "d", "s"], ["clkb", "clkb"], ["Tp", "Tp"]),
                isl(0.5, 2.0, ["qb", "vdd", "q"], ["s", "qb"], ["I1p", "I2p"])], {"vdd", "d"}, "both"),
]
DL_PORTS = ["d", "clk", "clkb", "q", "qb", "vdd", "vss"]
DL_EXITS = {"d": "top", "clk": "bot", "clkb": "bot", "q": "bot"}

# ---------------- TG 3 개 (wu_lib TG: XN a en b vss W2, XP a enb b vdd W4) ----------------
TG3_DEV = {}
for k, (a, b) in enumerate((("vp", "akx"), ("vm", "aky"), ("ako", "abs"))):
    TG3_DEV[f"T{k}n"] = (f"{b} ctl {a}", "n", 2.0, 0.5)
    TG3_DEV[f"T{k}p"] = (f"{b} ctlb {a}", "p", 4.0, 0.5)
TG3_ROWS = [
    ("n", "n", [isl(0.5, 1.0, ["vp", "akx", "vp"], ["ctl"] * 2, ["T0n"] * 2), isl(0.5, 1.0, ["vm", "aky", "vm"], ["ctl"] * 2, ["T1n"] * 2),
                isl(0.5, 1.0, ["ako", "abs", "ako"], ["ctl"] * 2, ["T2n"] * 2)], {"vp", "vm", "ako"}, None),
    ("p", "p", [isl(0.5, 2.0, ["vp", "akx", "vp"], ["ctlb"] * 2, ["T0p"] * 2), isl(0.5, 2.0, ["vm", "aky", "vm"], ["ctlb"] * 2, ["T1p"] * 2),
                isl(0.5, 2.0, ["ako", "abs", "ako"], ["ctlb"] * 2, ["T2p"] * 2)], {"vp", "vm", "ako"}, None),
]
TG3_PORTS = ["vp", "vm", "akx", "aky", "ako", "abs", "ctl", "ctlb", "vdd", "vss"]
TG3_EXITS = {"akx": "top", "aky": "top", "ako": "top", "vp": "bot", "vm": "bot", "abs": "bot", "ctl": "bot", "ctlb": "bot"}
HOG_OUT_X = 2.70            # HOG out 레인 x (셀 중심 기준) — tg3 의 ako 레인을 같은 x 에 두어 곧게 잇는다

XE_SA, XE_PRE, XE_DL, XE_TG3 = 6.2, 4.215, 3.6, 4.215


NOCONT = ("left",)          # 비교기 줄은 맞붙인다 → 왼쪽 경계 탭 컨택 없음 (오른쪽 이웃 셀의 컨택과 mcon.2)


def build_sa(ly, force=None, name=NAMES["sa"]):
    return RC.build(ly, name, XE_SA, SA_ROWS, SA_DEV, SA_PORTS, exits=SA_EXITS, local={"tl", "m1", "m2"}, force=force, nocont=NOCONT,
                    search=True)


def build_pre(ly, force=None, name=NAMES["pre"]):
    return RC.build(ly, name, XE_PRE, PRE_ROWS, PRE_DEV, PRE_PORTS, exits=PRE_EXITS, force=force, nocont=NOCONT)


def build_dlat(ly, force=None, name=NAMES["dlat"]):
    return RC.build(ly, name, XE_DL, DL_ROWS, DL_DEV, DL_PORTS, exits=DL_EXITS, force=force, nocont=NOCONT)


def build_tg3(ly, force=None, name=NAMES["tg3"]):
    return RC.build(ly, name, XE_TG3, TG3_ROWS, TG3_DEV, TG3_PORTS, exits=TG3_EXITS, lanes={"ako": HOG_OUT_X}, force=force)


# ---------------- 저항 bank: res_xhigh_po_0p35 ----------------
# 모형 (sky130_fd_pr__res_xhigh_po__base): R = rcon + 2000·L/W, rcon(W 0.35) = −46.62/W² + 331.73/W + 20.576 = 587.79 Ω
R_W, R_PITCH, R_HEAD = 0.35, 0.70, 2.16      # 줄 폭 · 피치 (bar licon 옆 간격 0.51 → 0.19 + 0.51) · 머리 (bar licon 2.0 + 0.08 × 2)
RCON = -46.62 / R_W ** 2 + 331.73 / R_W + 20.576
R_SEG = 1e6 / 3                              # 1 MΩ = 3 줄, 2 MΩ = 6 줄
R_L = round((R_SEG - RCON) / (2000.0 / R_W) / 0.005) * 0.005     # 몸통 길이 58.230 µm
R_Y0 = 1.25                                  # poly 아래 끝 (p 탭 띠 0.25–0.75 에서 poly.9a 0.48 이상)
R_N = 18


def r_seg_ohm():
    return RCON + 2000.0 / R_W * R_L


def build_rbank(ly, name=NAMES["rbank"]):
    """줄 i (0…17) x = 0.7·i, poly y R_Y0 … R_Y0 + 2·HEAD + R_L.
    R1 = 줄 0–2 (akx 아래 → akp 위), R2 = 3–8 (akp 위 → vcm 위), R3 = 9–11 (aky 아래 → akm 위), R4 = 12–17 (akm 위 → ako 위).
    머리 잇기 (li1): 아래 1–2, 3–4, 5–6, 7–8, 10–11, 12–13, 14–15, 16–17 / 위 0–1, 2–3 (akp), 4–5, 6–7, 9–10, 11–12 (akm), 13–14, 15–16."""
    C = Cell(ly, name)
    for k, v in dict(pres=(66, 13), urpm=(79, 20), lbl_m3=(70, 5)).items():
        C.li[k] = ly.layer(*v)
    xs = [gs(R_PITCH * i) for i in range(R_N)]
    y0, Lt = R_Y0, 2 * R_HEAD + R_L
    yb1, yt0, y1 = y0 + R_HEAD, y0 + R_HEAD + R_L, y0 + Lt
    bot_j = [(1, 2), (3, 4), (5, 6), (7, 8), (10, 11), (12, 13), (14, 15), (16, 17)]
    top_j = [(0, 1), (2, 3), (4, 5), (6, 7), (9, 10), (11, 12), (13, 14), (15, 16)]
    # 줄마다 넷 이름 (아래 머리 넷, 위 머리 넷) — 직렬 사이 넷 r<i>
    chains = [("akx", [0, 1, 2], "akp"), ("akp", [3, 4, 5, 6, 7, 8], "vcm"), ("aky", [9, 10, 11], "akm"), ("akm", [12, 13, 14, 15, 16, 17], "ako")]
    hb, ht = {}, {}
    cdl_r = []
    for a, idx, b in chains:
        end = a
        side = "b" if a in ("akx", "aky") else "t"     # 시작 머리 쪽
        for j, i in enumerate(idx):
            n_from = end
            n_to = b if j == len(idx) - 1 else f"r{i}"
            if side == "b":
                hb[i], ht[i] = n_from, n_to
            else:
                ht[i], hb[i] = n_from, n_to
            cdl_r.append(f"R{i} {n_from} {n_to} $SUB=vss $[res_xhigh_po_0p35] w={R_W:.3f}u l={R_L:.3f}u")
            side = "t" if side == "b" else "b"
            end = n_to
    for (i, j) in bot_j:
        assert hb[i] == hb[j], (i, j, hb[i], hb[j])
    for (i, j) in top_j:
        assert ht[i] == ht[j], (i, j, ht[i], ht[j])
    for i, x in enumerate(xs):
        C.box(f"rp{i}", "poly", x - R_W / 2, y0, x + R_W / 2, y1)
        C.box(None, "pres", x - R_W / 2, yb1, x + R_W / 2, yt0)
        for (ya, yb_, n) in ((y0, yb1, hb[i]), (yt0, y1, ht[i])):
            C.box(None, "licon", x - 0.095, ya + 0.08, x + 0.095, ya + 2.08)
            C.box(n, "li1", x - R_W / 2, ya, x + R_W / 2, yb_)
    for (i, j) in bot_j:
        C.box(hb[i], "li1", xs[i] - R_W / 2, y0, xs[j] + R_W / 2, yb1)
    for (i, j) in top_j:
        C.box(ht[i], "li1", xs[i] - R_W / 2, yt0, xs[j] + R_W / 2, y1)
    C.box(None, "urpm", xs[0] - R_W / 2 - 0.20, y0 - 0.20, xs[-1] + R_W / 2 + 0.20, y1 + 0.20)
    C.box(None, "psd", xs[0] - R_W / 2 - 0.20, 0.125, xs[-1] + R_W / 2 + 0.20, y1 + 0.20)   # 아래 p 탭 psd 와 한 덩어리 (psd 간격), x 는 urpm 과 같게
    C.box(None, "npc", xs[0] - R_W / 2 - 0.10, y0 - 0.10, xs[-1] + R_W / 2 + 0.10, y1 + 0.10)
    # 단자: (넷, x, 아래 'b' / 위 't') — 머리 안쪽 (몸통 쪽) 에 mcon 2 + met1 패드 + via1 + met2 패드
    terms = {"akx": (xs[0], "b"), "aky": (xs[9], "b"), "akp": ((xs[2] + xs[3]) / 2, "t"), "vcm": (xs[8], "t"),
             "akm": ((xs[11] + xs[12]) / 2, "t"), "ako": (xs[17], "t")}
    pins = {}
    for n, (x, s) in terms.items():
        if s == "t":                                        # 머리의 몸통 쪽 (위 머리 바깥쪽은 HOG VDD 띠가 지나감)
            yc = gs(yt0 + 0.70)
        else:
            yc = gs(yb1 - 0.70)
        for dy in (-0.18, 0.18):
            C.cut(n, "mcon", x, yc + dy)
        C.box(n, "m1", x - 0.17, yc - 0.18 - 0.145, x + 0.17, yc + 0.18 + 0.145)
        C.cut(n, "via", x, yc, 0.15)
        C.box(n, "m2", x - 0.165, yc - 0.165, x + 0.165, yc + 0.165)
        pins[n] = dict(x=round(x, 3), y=round(yc, 3), side=s)
    # 기판 p 탭 띠 (vss): y 0.25–0.75, 저항 줄 범위
    xa, xb = xs[0] - R_W / 2 - 0.075, xs[-1] + R_W / 2 + 0.075        # 탭 psd (±0.125) 가 urpm 폭 안에
    C.box("vss", "tap", xa, 0.25, xb, 0.75)
    C.box("vss", "li1", xa, 0.25, xb, 0.75)
    C.box("vss", "m1", xa, 0.25, xb, 0.75)
    nn = int((xb - xa - 0.4) / CPIT) + 1
    x0 = gs((xa + xb) / 2 - (nn - 1) * CPIT / 2)
    for t in range(nn):
        C.cut("vss", "licon", x0 + t * CPIT, 0.5); C.cut("vss", "mcon", x0 + t * CPIT, 0.5)
    ports = ["akx", "akp", "vcm", "aky", "akm", "ako", "vss"]
    for n, p in pins.items():
        C.label(n, "lbl_m2", p["x"], p["y"])
    C.label("vss", "lbl_m1", (xa + xb) / 2, 0.5)
    cdl = [f".subckt {name} " + " ".join(ports)] + cdl_r + [f".ends {name}"]
    info = dict(name=name, x0=round(xa, 3), x1=round(xb, 3), y_top=round(y1 + 0.20, 3), y_poly=(y0, y1), xs=xs, pins=pins,
                cdl=cdl, r_seg=r_seg_ohm(), r_l=R_L, ports=ports, head_top=(yt0, y1), head_bot=(y0, yb1))
    return C, info


# ---------------- MIM (cap_mim_m3_1 → LVS cap_mim_m3__base) ----------------
CAMIM, CPMIM, M3DW = 2.00, 0.19, -0.025     # fF/µm², fF/µm, µm (sky130 r+c 모형)
MIM_E = 0.20                                 # met3 가 capm 을 감싸는 폭 (≥ 0.14)
MIM_CLR = 1.40                               # capm → 윗판 착지 met3 (아랫판 = capm + 0.14 에서 1.2 이상)


def mim_c(w):
    wc = w + M3DW
    return CAMIM * wc * wc + CPMIM * 4 * wc


def mim_side(cf):
    w = 1.0
    while mim_c(w) < cf:
        w = round(w + 0.005, 3)
    return w


def build_mim(ly, name, cf):
    """정사각 capm 한 변 w (C ≥ cf fF). 원점 = capm 왼쪽 아래 − (E, E).
    bot 핀 = 아랫판 왼쪽 혀 via2 + met2 패드, top 핀 = 윗판 met4 → via3 → met3 착지 → via2 → met2 패드 (capm 위쪽)."""
    C = Cell(ly, name)
    for k, v in dict(capm=(89, 44), m4=(71, 20), via3=(70, 44), via2=(69, 44), lbl_m3=(70, 5)).items():
        C.li[k] = ly.layer(*v)
    w = mim_side(cf); E = MIM_E
    cx0, cy0, cx1, cy1 = E, E, E + w, E + w
    C.box("top", "capm", cx0, cy0, cx1, cy1)
    C.box("bot", "m3", -0.50, 0, cx1 + E, cy1 + E)          # 아랫판 + 왼쪽 혀
    C.box("top", "m4", cx0 + 0.06, cy0 + 0.06, cx1 - 0.06, cy1 - 0.06)
    n = int((w - 0.28 - 0.20) / 0.40) + 1
    off = (w - (n - 1) * 0.40) / 2
    for i in range(n):
        for j in range(n):
            C.cut("top", "via3", cx0 + off + i * 0.40, cy0 + off + j * 0.40, 0.20)
    yb = gs((cy0 + cy1) / 2)                                    # bot: 혀 위 via2
    xbp = -0.19
    C.cut("bot", "via2", xbp, yb, 0.20)
    C.box("bot", "m2", xbp - 0.185, yb - 0.185, xbp + 0.185, yb + 0.185)
    xt = gs(cx1 - 0.26)                                         # top: met4 를 위로 → 착지
    yl = gs(cy1 + MIM_CLR + 0.26)
    C.box("top", "m4", xt - 0.26, cy1 - 0.06 - 0.30, xt + 0.26, yl + 0.26)
    C.cut("top", "via3", xt, yl, 0.20)
    C.box("top", "m3", xt - 0.26, yl - 0.26, xt + 0.26, yl + 0.26)
    C.cut("top", "via2", xt, yl, 0.20)
    C.box("top", "m2", xt - 0.185, yl - 0.185, xt + 0.185, yl + 0.185)
    C.label("top", "lbl_m2", xt, yl); C.label("bot", "lbl_m2", xbp, yb)
    cdl = [f".subckt {name} top bot", f"C0 top bot cap_mim_m3__base w={w:.3f}u l={w:.3f}u", f".ends {name}"]
    info = dict(name=name, w=w, c_ff=round(mim_c(w), 3), pins=dict(top=dict(x=xt, y=yl), bot=dict(x=xbp, y=yb)),
                bbox=(-0.50, 0.0, cx1 + E, yl + 0.26), capm=(cx0, cy0, cx1, cy1), cdl=cdl)
    return C, info

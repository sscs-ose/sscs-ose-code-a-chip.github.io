#!/usr/bin/env python3
"""WU (weight update) 블록 한 벌 — real_circuit/wu_lib.py wu_subckt(1e6, 20e-15, 'pa_sa', 20e-15, 2.0) 의 레이아웃.

배치 (아래 → 위, 원점 = 블록 왼쪽 아래, µm):
  VSS met3 띠 (아래 끝) → 통로 C (ck·ck3·lat·latb·lq, met3 가로 → 왼쪽 끝 핀)
  → 비교기 줄: [COMP1 SA][PRE][COMP3 SA][DLATCH][COMP2 SA] 맞붙임 (띠 높이 같게) + Cabs MIM 20 fF × 2 (오른쪽)
  → 통로 A (fp fm np nm q1 q1b q2 q2b absf absn vcm vbn pa3p pa3n sen, met3 가로 + met2 세로, 왼쪽 끝 핀)
  → 증폭기 칸 4 개 (A1–A4, 칸 피치 22.9): 아래 TG3 + 위 HOG (사용자 셀, 그대로) / 오른쪽 저항 bank (줄 18 개)
     칸 안: TG3 → (통로 B) → bank 아래 단자 (akx·aky), bank 위 단자 akp·akm → met2 로 내려 met3 로 HOG inp·inn 레인,
     ako = bank 위 단자 → met3 → HOG out 레인 위 끝, HOG out 레인 아래 끝 → met2 로 TG3 의 ako 레인 (같은 x),
     Cf 10 fF MIM (bank 위, 아랫판 akm · 윗판 ako)
  → vcm met3 (bank R2 끝 4 개) → VDD met3 띠 (위 끝).
  bias vbnc·vbn·vbpc·vbp = HOG 줄을 가로지르는 met3 (HOG 레인에 via2), 왼쪽 끝 핀. vbn·vcm 은 왼쪽 여백 met2 로 통로 A 까지.
  전원: 줄마다 met1 rail (셀 띠와 겹침) → 왼쪽 여백 met2 VSS·VDD 세로 띠 → 아래 VSS · 위 VDD met3 띠.
금속: 이 생성기가 그리는 것은 met1–met3 (+ MIM 윗판 met4, PDK MIM 구조상). HOG 셀 안에도 MIM (met4) 이 있다.
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python gen_wu.py → out/wu.gds·.cdl·.json
"""
import json, os, sys
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import klayout.db as pya          # noqa: E402
import rowcell as RC              # noqa: E402
import wu_cells as W              # noqa: E402
from devlib import Cell, g as gs  # noqa: E402

HOGD = "/home/dave/work/projects/sern_hog_classab_opamp/sim/layout/out"
OUT = os.path.join(H, "out")
TOP = os.environ.get("NAME", "wu")
um = lambda v: int(round(gs(v) * 1000))

# ---------------- 치수 ----------------
X_VSS, X_VDD = (0.30, 1.10), (1.50, 2.30)       # 왼쪽 여백 met2 전원 띠
X_FT = dict(vcm=2.90, vbn=3.50)                 # 왼쪽 여백 met2 세로 (칸 줄 → 통로 A)
XS0, SL_P = 3.40, 22.10                         # 첫 칸 왼쪽 끝 · 칸 피치 (bank psd ↔ 다음 칸 HOG·TG3 경계 탭 psd 0.38 = psd.2)
HOG_HW = 4.625                                  # HOG hvi 반폭
BANK_DX = 5.10                                  # 칸 중심 → bank 줄 0 x (bank psd ↔ HOG·TG3 경계 탭 psd 0.385, 22.0/5.05 는 잡 721160 psd.2)
NSL = 4
BLK_W = gs(XS0 + NSL * SL_P)
TP, TW = 0.70, 0.34                             # 통로 met3 track 피치 · 폭
P2 = 0.37                                       # via2 met2 패드
# HOG 레인 (sern_hog layout out/hog.json, VER 3) — 셀 중심 기준 x, HOG 원점 기준 y
HJ = json.load(open(os.path.join(HOGD, "hog.json")))
HL, HS = HJ["lanes"], HJ["spans"]
HOGV = dict(vbnc=12.36, vbn=15.23, vbpc=41.96, vbp=44.30, akp=23.50, akm=25.60, ako=45.30)   # HOG 기준 met3 y (ako 45.6 은 HOG out via1 패드 46.0 과 met2 0.05 — 잡 721152 m2.2)
for n, hn in (("vbnc", "vbnc"), ("vbn", "vbn"), ("vbpc", "vbpc"), ("vbp", "vbp"), ("akp", "inp"), ("akm", "inn"), ("ako", "out")):
    a, b = HS[hn]
    assert a - 0.01 <= HOGV[n] <= b + 0.01, (n, HOGV[n], HS[hn])
HOG_PIN_X = dict(vbnc=HL["vbnc"], vbn=HL["vbn"], vbpc=HL["vbpc"], vbp=HL["vbp"], akp=HL["inp"], akm=HL["inn"], ako=HL["out"])
assert abs(HL["out"] - W.HOG_OUT_X) < 1e-6

ly = pya.Layout(); ly.dbu = 0.001
ly.read(os.path.join(HOGD, "hog.gds"))
hog = ly.cell("hog")
T = Cell(ly, TOP)
for k, v in dict(lbl_m3=(70, 5), via2=(69, 44), m4=(71, 20), capm=(89, 44), via3=(70, 44)).items():
    T.li[k] = ly.layer(*v)

# ---------------- 부품 셀 (비교기 줄은 띠 높이를 맞춘다) ----------------
def nat(fn):
    l2 = pya.Layout(); l2.dbu = 0.001
    _, i = fn(l2)
    return i["bands"]
nb = {k: nat(f) for k, f in (("sa", W.build_sa), ("pre", W.build_pre), ("dlat", W.build_dlat))}
NB1 = max(b["NBAND1"] for b in nb.values())
PB0 = gs(NB1 + 0.25 + RC.NW_SP + 0.63)
PB1 = gs(PB0 + max(b["PBAND1"] - b["PBAND0"] for b in nb.values()))
FORCE = dict(NBAND1=gs(NB1), PBAND1=PB1)
CEL = {}
for k, f in (("sa", W.build_sa), ("pre", W.build_pre), ("dlat", W.build_dlat)):
    CEL[k] = f(ly, force=FORCE)
    assert abs(CEL[k][1]["bands"]["PBAND1"] - PB1) < 1e-6 and abs(CEL[k][1]["bands"]["NBAND1"] - gs(NB1)) < 1e-6
CEL["tg3"] = W.build_tg3(ly)
CEL["rbank"] = W.build_rbank(ly)
CEL["mim10"] = W.build_mim(ly, "wu_mim10", 10.0)
CEL["mim20"] = W.build_mim(ly, "wu_mim20", 20.0)
STRIP_H = CEL["sa"][1]["ytop"]
TG3_H = CEL["tg3"][1]["ytop"]
TG3_PB1 = CEL["tg3"][1]["bands"]["PBAND1"]
RB = CEL["rbank"][1]

# ---------------- 넷 기록 (단락 검사용): 부품 셀 넷 → 블록 넷 ----------------
NETS = {}                                    # 층 → 넷 → Region (블록 좌표)
INSTS = []


def add_net_shapes(C, mapping, prefix, dx, dy):
    t = pya.Trans(pya.Point(um(dx), um(dy)))
    for n, lays in C.net.items():
        tn = mapping.get(n, f"{prefix}.{n}")
        for lay, reg in lays.items():
            NETS.setdefault(lay, {}).setdefault(tn, pya.Region()).insert(reg.transformed(t))


def place(key, iname, x, y, mapping):
    C, info = CEL[key]
    T.c.insert(pya.CellInstArray(C.c.cell_index(), pya.Trans(pya.Point(um(x), um(y)))))
    add_net_shapes(C, mapping, iname, x, y)
    INSTS.append((iname, info["name"], x, y, mapping))


def place_hog(iname, x, y, mapping):
    T.c.insert(pya.CellInstArray(hog.cell_index(), pya.Trans(pya.Point(um(x), um(y)))))
    for n, lx in HL.items():                 # HOG met2 레인 (json) → 넷 (단락 검사 근사)
        if n not in HS:
            continue
        a, b = HS[n]
        tn = mapping.get(n, f"{iname}.{n}")
        NETS.setdefault("m2", {}).setdefault(tn, pya.Region()).insert(pya.Box(um(x + lx - 0.14), um(y + a), um(x + lx + 0.14), um(y + b)))
    for (x0, y0, x1, y1, n) in ((-3.515, 0.9, 3.515, 9.94, "cmid"), (1.24, 11.34, 1.76, 11.86, "s1_out")):
        NETS.setdefault("m3", {}).setdefault(f"{iname}.{n}", pya.Region()).insert(pya.Box(um(x + x0), um(y + y0), um(x + x1), um(y + y1)))
    INSTS.append((iname, "hog", x, y, mapping))


def via2(net, x, y, pad3=True):
    T.cut(net, "via2", x, y, 0.20)
    T.box(net, "m2", x - P2 / 2, y - P2 / 2, x + P2 / 2, y + P2 / 2)
    if pad3:
        T.box(net, "m3", x - P2 / 2, y - P2 / 2, x + P2 / 2, y + P2 / 2)


def via1(net, x, y):
    T.box(net, "m1", x - 0.165, y - 0.165, x + 0.165, y + 0.165)
    T.cut(net, "via", x, y, 0.15)
    T.box(net, "m2", x - 0.165, y - 0.165, x + 0.165, y + 0.165)


def m2v(net, x, ya, yb, w=0.28):
    T.box(net, "m2", x - w / 2, min(ya, yb), x + w / 2, max(ya, yb))


def m3h(net, xa, xb, y, w=TW):
    T.box(net, "m3", min(xa, xb), y - w / 2, max(xa, xb), y + w / 2)


# ---------------- 통로 배선기: 왼쪽 끝 + 수직 제약 (위 핀 넷이 같은 x 의 아래 핀 넷보다 위) ----------------
def chan_assign(pins, edge, x_edge=0.0):
    nets = {}
    for n, x, s in pins:
        nets.setdefault(n, [1e9, -1e9])
        nets[n][0] = min(nets[n][0], x); nets[n][1] = max(nets[n][1], x)
    for n in edge:
        nets.setdefault(n, [x_edge, x_edge])
        nets[n][0] = x_edge
    pred = {n: set() for n in nets}
    for n1, x1, s1 in pins:
        for n2, x2, s2 in pins:
            if n1 == n2 or abs(x1 - x2) >= 0.595:
                continue
            if s1 == s2:
                raise RuntimeError(f"같은 쪽 핀 겹침 {n1}@{x1} {n2}@{x2} ({s1})")
            if s1 == "top" and s2 == "bot":
                pred[n2].add(n1)
    tr = {}
    t = 0
    while len(tr) < len(nets):
        done = {n for n, k in tr.items() if k < t}
        av = sorted([n for n in nets if n not in tr and pred[n] <= done], key=lambda n: nets[n][0])
        cur = []
        for n in av:
            a, b = nets[n]
            if all(b + 0.2 + 0.3 + 0.2 <= nets[m][0] or nets[m][1] + 0.7 <= a for m in cur):
                cur.append(n)
        if not cur:
            raise RuntimeError(f"수직 제약 고리: {[(n, pred[n] - done) for n in nets if n not in tr]}")
        for n in cur:
            tr[n] = t
        t += 1
    return tr, t, nets


def chan_draw(pins, edge, ybot, ytop, tr, ntr, iv, x_edge=0.0, off=0.50):
    ys = {n: gs(ybot + off + (ntr - 1 - k) * TP) for n, k in tr.items()}
    assert ys and max(ys.values()) <= ytop - off + 1e-6, (ybot, ytop, ntr)
    for n, (a, b) in iv.items():
        xa = x_edge if n in edge else a - 0.2
        m3h(n, xa, b + 0.2, ys[n])
    for n, x, s in pins:
        y = ys[n]
        m2v(n, x, ytop if s == "top" else ybot, y)
        via2(n, x, y, pad3=False)
    return ys


# =====================================================================
# 칸 줄 세로 위치 (칸 줄 원점 = yR0 기준)
yB1 = gs(TG3_H + 0.35)                           # 통로 B: aky
yB2 = gs(yB1 + TP)                               # akx
YH = gs(max(yB2 + TW / 2 - 0.06,                 # HOG MIM (capm 아래 끝 HOG y 1.40) 에서 met3 1.34 이상
            RB["pins"]["vcm"]["y"] + 0.325 + 0.14 - 51.37))   # HOG VDD 띠 rail 이 bank 위 단자 met1 패드와 0.14 이상
YH = max(YH, 13.45)
Y_VCM = gs(max(RB["y_top"], YH + 52.31 - 1.5) + 0.60)
RAIL_R = dict(vss_bot=(0.25, 0.75), vdd_tg=(TG3_PB1 - 0.25, TG3_PB1 + 0.25), vss_hog=(YH + 0.25, YH + 0.75), vdd_hog=(YH + 51.37, YH + 51.87))
Y_TOPSTRAP = gs(max(YH + 52.31, Y_VCM + TW / 2 + 0.30) + 0.0)
ROW_H = gs(Y_TOPSTRAP + 0.80)

# 칸마다 핀 x (통로 A 위 핀)
TGL = CEL["tg3"][1]["lanes"]
SLICES = []
for k in range(NSL):
    xs = XS0 + k * SL_P
    xc = gs(xs + HOG_HW)
    bx0 = gs(xc + BANK_DX)
    vp, vm = (("fp", "fm"), ("fm", "fp"), ("np", "nm"), ("nm", "np"))[k]
    ctl, ctlb = (("q1", "q1b"), ("q1b", "q1"), ("q2", "q2b"), ("q2b", "q2"))[k]
    ab = "absf" if k < 2 else "absn"
    SLICES.append(dict(k=k, xs=xs, xc=xc, bx0=bx0, vp=vp, vm=vm, ctl=ctl, ctlb=ctlb, abs=ab))
TOP_PINS_A = []
for s in SLICES:
    for ln, net in (("vp", s["vp"]), ("vm", s["vm"]), ("abs", s["abs"]), ("ctl", s["ctl"]), ("ctlb", s["ctlb"])):
        TOP_PINS_A.append((net, gs(s["xc"] + TGL[ln]), "top"))
TOP_PINS_A += [("vcm", X_FT["vcm"], "top"), ("vbn", X_FT["vbn"], "top")]
EDGE_A = ["fp", "fm", "np", "nm", "q1", "q2", "absf", "absn", "sen"]
EDGE_C = ["ck", "ck3", "lat", "latb", "lq"]

# 비교기 줄 (맞붙임): 이름, 셀, 핀 대응
GROUP = [("XC1", "sa", dict(inp="fp", inn="fm", clk="ck", q="q1", qb="q1b")),
         ("XP3", "pre", dict(inp="absf", inn="absn", op="pa3p", on="pa3n", vbn="vbn")),
         ("XC3", "sa", dict(inp="pa3p", inn="pa3n", clk="ck3", q="sen", qb="senb")),
         ("XLAT", "dlat", dict(d="sen", clk="lat", clkb="latb", q="lq", qb="lqb")),
         ("XC2", "sa", dict(inp="np", inn="nm", clk="ck", q="q2", qb="q2b"))]
XEK = dict(sa=W.XE_SA, pre=W.XE_PRE, dlat=W.XE_DL)
GW = sum(2 * XEK[c] for _, c, _ in GROUP)
M20 = CEL["mim20"][1]
MIM_GAP = 5.50


def group_pins(gx0):
    """gx0 = 줄 왼쪽 탭 끝. 반환 (셀 중심 목록, 통로 A 아래 핀, 통로 C 위 핀, MIM 원점)"""
    x = gx0
    cen, pa, pc = [], [], []
    for iname, c, mp in GROUP:
        xc = gs(x + XEK[c])
        cen.append(xc)
        inf = CEL[c][1]
        for p, net in mp.items():
            if p not in inf["pins"]:
                continue
            ex = {"sa": W.SA_EXITS, "pre": W.PRE_EXITS, "dlat": W.DL_EXITS}[c].get(p)
            px = gs(xc + inf["lanes"][p])
            if ex in ("top", "both") and net not in ("senb",):
                pa.append((net, px, "bot"))
            if ex in ("bot", "both"):
                pc.append((net, px, "top"))
        x += 2 * XEK[c]
    mx = gs(x + 1.50 + 0.50)                    # MIM 원점 (혀 왼쪽 끝 −0.5)
    mims = [(mx, "absf"), (gs(mx + M20["bbox"][2] + MIM_GAP), "absn")]
    for ox, net in mims:
        pa.append((net, gs(ox + M20["pins"]["top"]["x"]), "bot"))
        pa.append(("vcm", gs(ox + M20["pins"]["bot"]["x"]), "bot"))
    return cen, pa, pc, mims


best = None
gx = 5.0
while gx + GW + 2.0 + 2 * M20["bbox"][2] + MIM_GAP <= BLK_W - 0.5:
    try:
        cen, pa, pc, mims = group_pins(gs(gx))
        tr, ntr, iv = chan_assign(TOP_PINS_A + pa, EDGE_A)
        trc, ntrc, ivc = chan_assign(pc, EDGE_C)
        cost = ntr * 10 + sum(b - a for a, b in iv.values()) / 100
        if best is None or cost < best[0]:
            best = (cost, gs(gx), ntr, ntrc)
    except RuntimeError:
        pass
    gx += 0.05
assert best, "통로 A 배정 실패"
GX0 = best[1]
cen, PINS_A_BOT, PINS_C, MIMS = group_pins(GX0)
PINS_A = TOP_PINS_A + PINS_A_BOT
trA, ntrA, ivA = chan_assign(PINS_A, EDGE_A)
trC, ntrC, ivC = chan_assign(PINS_C, EDGE_C)
print(f"비교기 줄 왼쪽 끝 x {GX0:.2f}, 통로 A track {ntrA}, 통로 C track {ntrC}")

# 세로 위치 (블록)
Y_VSSTRAP = (0.0, 0.80)
yC0 = Y_VSSTRAP[1]                           # 첫 track 아래 끝이 VSS 띠에서 0.33
yS0 = gs(yC0 + 2 * 0.50 + (ntrC - 1) * TP)
yS1 = gs(yS0 + STRIP_H)
yR0 = gs(yS1 + 2 * 0.50 + (ntrA - 1) * TP)
BLK_H = gs(yR0 + ROW_H)

# ---------------- 비교기 줄 ----------------
for (iname, c, mp), xc in zip(GROUP, cen):
    mapping = dict(mp, vdd="vdd", vss="vss")
    place(c, iname, xc, yS0, mapping)
for (ox, net) in MIMS:
    oy = gs(yS1 - M20["bbox"][3] - 0.40)
    place("mim20", f"XCab_{net}", ox, oy, dict(top=net, bot="vcm"))
    for p in ("top", "bot"):
        px, py = ox + M20["pins"][p]["x"], oy + M20["pins"][p]["y"]
        m2v(net if p == "top" else "vcm", px, py, yS1)
# 줄 rail (met1): 셀 띠를 왼쪽 여백 전원 띠까지
RAILS = []
for nm_, yc in (("NBAND0", 0.5), ("NBAND1", FORCE["NBAND1"]), ("PBAND0", PB0), ("PBAND1", PB1)):
    net = "vss" if nm_.startswith("N") else "vdd"
    RAILS.append((net, X_VSS[0] if net == "vss" else X_VDD[0], GX0 + 0.5, yS0 + yc - 0.25, yS0 + yc + 0.25))
# 줄 위 nwell 이어 붙임 없음 (셀이 맞붙어 nwell 이 겹친다)

# ---------------- 통로 A·C ----------------
YA = chan_draw(PINS_A, EDGE_A, yS1, yR0, trA, ntrA, ivA)
YC = chan_draw(PINS_C, EDGE_C, yC0, yS0, trC, ntrC, ivC)

# ---------------- 증폭기 칸 ----------------
TP_PINS = RB["pins"]
for s in SLICES:
    k, xc, bx0 = s["k"] + 1, s["xc"], s["bx0"]
    a = f"a{k}"
    nets = dict(akx=f"{a}x", aky=f"{a}y", akp=f"{a}p", akm=f"{a}m", ako=f"{a}o")
    place("tg3", f"XT{k}", xc, yR0, dict(vp=s["vp"], vm=s["vm"], akx=nets["akx"], aky=nets["aky"], ako=nets["ako"],
                                          abs=s["abs"], ctl=s["ctl"], ctlb=s["ctlb"], vdd="vdd", vss="vss"))
    place("rbank", f"XR{k}", bx0, yR0, dict(akx=nets["akx"], aky=nets["aky"], akp=nets["akp"], akm=nets["akm"], ako=nets["ako"],
                                            vcm="vcm", vss="vss"))
    yh = yR0 + YH
    place_hog(f"XA{k}", xc, yh, dict(inp=nets["akp"], inn=nets["akm"], out=nets["ako"], vbn="vbn", vbp="vbp", vbnc="vbnc",
                                      vbpc="vbpc", vdd="vdd", vss="vss"))
    # 통로 B: TG3 위 → bank 아래 단자
    for nk, yb in (("akx", yB2), ("aky", yB1)):
        n = nets[nk]
        xt = gs(xc + TGL[nk])
        xb = gs(bx0 + TP_PINS[nk]["x"])
        m2v(n, xt, yR0 + TG3_H, yR0 + yb); via2(n, xt, yR0 + yb, pad3=False)
        m3h(n, xt - 0.2, xb + 0.2, yR0 + yb)
        via2(n, xb, yR0 + yb, pad3=False); m2v(n, xb, yR0 + yb, yR0 + TP_PINS[nk]["y"])
    # ako: TG3 레인 위 끝 → HOG out 레인 아래 끝 (같은 x)
    xo = gs(xc + W.HOG_OUT_X)
    m2v(nets["ako"], xo, yR0 + TG3_H, yh + HS["out"][0] + 0.15)
    # bank 위 단자 → HOG 입력·출력 (met2 내림 → met3 → HOG 레인 via2)
    for nk in ("akp", "akm", "ako"):
        n = nets[nk]
        xb = gs(bx0 + TP_PINS[nk]["x"]); yt = yR0 + TP_PINS[nk]["y"]
        yy = yh + HOGV[nk]
        m2v(n, xb, yt, yy); via2(n, xb, yy, pad3=False)
        xl = gs(xc + HOG_PIN_X[nk])
        m3h(n, xl - 0.2, xb + 0.2, yy)
        via2(n, xl, yy, pad3=False)
    # Cf (10 fF): 아랫판 혀 = akm met2 내림 위, 윗판 = ako (착지에서 met2 로 ako met3 까지)
    M10 = CEL["mim10"][1]
    xakm = gs(bx0 + TP_PINS["akm"]["x"])
    ox = gs(xakm - M10["pins"]["bot"]["x"])
    oy = gs(yh + HOGV["akm"] + TW / 2 + 1.40 - M10["capm"][1])
    place("mim10", f"XF{k}", ox, oy, dict(top=nets["ako"], bot=nets["akm"]))
    xt = gs(ox + M10["pins"]["top"]["x"])
    m2v(nets["ako"], xt, oy + M10["pins"]["top"]["y"], yh + HOGV["ako"])
    via2(nets["ako"], xt, yh + HOGV["ako"], pad3=False)
    assert xt < bx0 + TP_PINS["ako"]["x"] - 0.6
    # vcm: bank 위 단자 → vcm met3
    xv = gs(bx0 + TP_PINS["vcm"]["x"])
    m2v("vcm", xv, yR0 + TP_PINS["vcm"]["y"], yR0 + Y_VCM); via2("vcm", xv, yR0 + Y_VCM, pad3=False)
    # VDD 잇기: HOG 위 VDD rail → 위 VDD met3 띠
    for dx in (-2.4, 2.4):
        x = gs(xc + dx)
        via1("vdd", x, yR0 + YH + 51.62)
        m2v("vdd", x, yR0 + YH + 51.62, yR0 + Y_TOPSTRAP + 0.40, w=0.33)
        via2("vdd", x, yR0 + Y_TOPSTRAP + 0.40, pad3=False)
# bias met3 (HOG 줄 가로) + HOG 레인 via2
last = SLICES[-1]
for n in ("vbnc", "vbn", "vbpc", "vbp"):
    yy = yR0 + YH + HOGV[n]
    xe = max(gs(s["xc"] + HOG_PIN_X[n]) for s in SLICES)
    m3h(n, 0.0, xe + 0.2, yy)
    for s in SLICES:
        via2(n, gs(s["xc"] + HOG_PIN_X[n]), yy, pad3=False)
# vcm met3 (칸 줄 위)
xe = max(gs(s["bx0"] + TP_PINS["vcm"]["x"]) for s in SLICES)
m3h("vcm", 0.0, xe + 0.2, yR0 + Y_VCM)
# 왼쪽 여백 세로 (vcm·vbn → 통로 A 위 핀)
for n, yy in (("vcm", yR0 + Y_VCM), ("vbn", yR0 + YH + HOGV["vbn"])):
    via2(n, X_FT[n], yy, pad3=False)
    m2v(n, X_FT[n], yy, yR0)
# 칸 줄 rail (met1)
for nm_, (a, b) in RAIL_R.items():
    net = "vss" if nm_.startswith("vss") else "vdd"
    RAILS.append((net, X_VSS[0] if net == "vss" else X_VDD[0], BLK_W, yR0 + a, yR0 + b))

# ---------------- 전원 ----------------
for net, xa, xb, ya, yb in RAILS:
    T.box(net, "m1", xa, ya, xb, yb)
    xs_ = X_VSS if net == "vss" else X_VDD
    yc = (ya + yb) / 2
    for x in (xs_[0] + 0.2, xs_[0] + 0.6):
        T.cut(net, "via", x, yc, 0.15)
T.box("vss", "m2", X_VSS[0], 0.0, X_VSS[1], BLK_H - 1.2)
T.box("vdd", "m2", X_VDD[0], 1.2, X_VDD[1], BLK_H)
T.box("vss", "m3", 0.0, Y_VSSTRAP[0], BLK_W, Y_VSSTRAP[1])
yv0 = yR0 + Y_TOPSTRAP
T.box("vdd", "m3", 0.0, yv0, BLK_W, BLK_H)
for x in (X_VSS[0] + 0.2, X_VSS[0] + 0.6):
    T.cut("vss", "via2", x, 0.40, 0.20)
for x in (X_VDD[0] + 0.2, X_VDD[0] + 0.6):
    T.cut("vdd", "via2", x, (yv0 + BLK_H) / 2, 0.20)
# hvi 블록 전체 (셀마다 있는 hvi 를 하나로; hvi.2 간격 문제 없앰)
T.box(None, "hvi", 0.0, 0.0, BLK_W, BLK_H)

# ---------------- 핀 (왼쪽 끝 met3) ----------------
PINS = {}
for n, y in list(YA.items()) + list(YC.items()):
    if n in EDGE_A or n in EDGE_C:
        T.label(n, "lbl_m3", 0.15, y)
        PINS[n] = dict(layer="met3", edge="left", x=0.0, y=round(y, 3), rect=[0.0, round(y - TW / 2, 3), 0.6, round(y + TW / 2, 3)])
for n in ("vbnc", "vbn", "vbpc", "vbp"):
    y = yR0 + YH + HOGV[n]
    T.label(n, "lbl_m3", 0.15, y)
    PINS[n] = dict(layer="met3", edge="left", x=0.0, y=round(y, 3), rect=[0.0, round(y - TW / 2, 3), 0.6, round(y + TW / 2, 3)])
T.label("vcm", "lbl_m3", 0.15, yR0 + Y_VCM)
PINS["vcm"] = dict(layer="met3", edge="left", x=0.0, y=round(yR0 + Y_VCM, 3), rect=[0.0, round(yR0 + Y_VCM - TW / 2, 3), 0.6, round(yR0 + Y_VCM + TW / 2, 3)])
T.label("vss", "lbl_m3", BLK_W / 2, 0.40)
T.label("vdd", "lbl_m3", BLK_W / 2, (yv0 + BLK_H) / 2)
PINS["vss"] = dict(layer="met3", edge="bottom", rect=[0.0, 0.0, BLK_W, 0.80])
PINS["vdd"] = dict(layer="met3", edge="top", rect=[0.0, round(yv0, 3), BLK_W, BLK_H])

# ---------------- 단락 검사 (블록 met1–met3 + 부품 셀 넷 + HOG 레인 근사) ----------------
for lay, d in T.net.items():
    for n, reg in d.items():
        NETS.setdefault(lay, {}).setdefault(n, pya.Region()).insert(reg)
bad = []
for lay in ("m1", "m2", "m3", "m4"):
    d = NETS.get(lay, {})
    ks = list(d)
    regs = {n: d[n].merged() for n in ks}
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            if regs[ks[i]].bbox().overlaps(regs[ks[j]].bbox()) and not (regs[ks[i]] & regs[ks[j]]).is_empty():
                bad.append((lay, ks[i], ks[j]))
print("단락:", bad or "없음")

# ---------------- 쓰기 ----------------
os.makedirs(OUT, exist_ok=True)
ly.write(os.path.join(OUT, TOP + ".gds"))
hog_cdl = open(os.path.join(HOGD, "hog.cdl")).read().strip().splitlines()
PORTS = ["fp", "fm", "np", "nm", "ck", "ck3", "lat", "latb", "lq", "sen", "absf", "absn", "q1", "q2", "vbn", "vbp", "vbnc", "vbpc",
         "vdd", "vss", "vcm"]
cdl = ["* WU 블록 (gen_wu.py). 정본 netlist: real_circuit/wu_lib.py wu_subckt(1e6, 20e-15, 'pa_sa', 20e-15, 2.0)",
       "* 바꾼 것: 이상 R 1/2 MΩ → res_xhigh_po_0p35 333.33 kΩ 줄 3/6 개 직렬, C 10·20 fF → cap_mim_m3 (w=l), 노드 0 → 핀 vcm, Rabs 1 TΩ (수치용) 뺌"]
seen = set()
for key in ("sa", "pre", "dlat", "tg3", "rbank", "mim10", "mim20"):
    cdl += CEL[key][1]["cdl"]
cdl += hog_cdl
cdl.append(f".subckt {TOP} " + " ".join(PORTS))
for iname, cell, x, y, mp in INSTS:
    if cell == "hog":
        order = ["inp", "inn", "out", "vbn", "vbp", "vbnc", "vbpc", "vdd", "vss"]
    elif cell in ("wu_mim10", "wu_mim20"):
        order = ["top", "bot"]
    elif cell == "wu_rbank":
        order = RB["ports"]
    else:
        key = {"wu_sa": "sa", "wu_pre": "pre", "wu_dlat": "dlat", "wu_tg3": "tg3"}[cell]
        order = {"sa": W.SA_PORTS, "pre": W.PRE_PORTS, "dlat": W.DL_PORTS, "tg3": W.TG3_PORTS}[key]
    cdl.append(f"X{iname} " + " ".join(mp.get(p, f"{iname}_{p}") for p in order) + f" {cell}")
cdl.append(f".ends {TOP}")
open(os.path.join(OUT, TOP + ".cdl"), "w").write("\n".join(cdl) + "\n")
m4 = pya.Region(T.c.begin_shapes_rec(ly.layer(71, 20))).merged()
M4KEEP = sorted([[round(b.left / 1000, 3), round(b.bottom / 1000, 3), round(b.right / 1000, 3), round(b.top / 1000, 3)]
                 for b in (p.bbox() for p in m4.each())], key=lambda r: (r[1], r[0]))
info = dict(cell=TOP, w=BLK_W, h=BLK_H, origin="lower-left (0,0)", pins=PINS, met4_keepout=M4KEEP,
            y=dict(chanC=[yC0, yS0], strip=[yS0, yS1], chanA=[yS1, yR0], slice_row=[yR0, BLK_H], hog_y0=[yR0 + YH]),
            slices=[dict(k=s["k"] + 1, xc=s["xc"], bank_x0=s["bx0"]) for s in SLICES], strip_x0=GX0,
            tracks=dict(A=ntrA, C=ntrC), r_seg_ohm=round(RB["r_seg"], 1), r_l=RB["r_l"],
            mim=dict(cf=CEL["mim10"][1]["c_ff"], cf_w=CEL["mim10"][1]["w"], cabs=M20["c_ff"], cabs_w=M20["w"]), shorts=bad,
            metals="met1-met3 (route) + met4 (MIM top plates, also inside hog)")
json.dump(info, open(os.path.join(OUT, TOP + ".json"), "w"), indent=1)
print(f"{TOP}: {BLK_W:.2f} × {BLK_H:.2f} µm (비교기 줄 y {yS0:.2f}–{yS1:.2f}, 칸 줄 y {yR0:.2f}–{BLK_H:.2f}, HOG y0 {yR0 + YH:.2f})")

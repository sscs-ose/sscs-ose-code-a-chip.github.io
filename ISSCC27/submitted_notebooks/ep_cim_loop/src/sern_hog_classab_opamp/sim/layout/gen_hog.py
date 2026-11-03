#!/usr/bin/env python3
"""HOG class-AB op-amp 셀 (folded cascode + Hogervorst class-AB, SKY130 5 V) — EP 뉴런 열 피치 8.43 µm 에 세로로 쌓는다.

바탕(사본): cac_ep/sim/ep_demo/layout/devlib.py — 소자 그리기 규칙(세로 poly, 핑거 피치 L+0.29, S/D li1 0.17·met1 0.23,
            컨택 피치 0.36, npc, hvi) — 와 gen_otacs.py 의 방식(넷마다 met2 세로 레인, met1 가로 스트랩, Rz·Cc 그리기).
회로: ../char/decks/hog_tr.spice (SKY130_OTA_HOG_TR, Cc 100 fF, Rz 3 kΩ) + 정합쌍 양끝 dummy.

레이아웃 기법 (Palermo ECEN 474 Lecture 3 · Lab 3–4, 위키 raw palermo-2026-ecen474):
  1. 정합쌍(입력쌍 Md1/2 · 미러 Mm1/2 · 전류원 Iref1/2)은 두 행 2-D common-centroid (A A B B / B B A A),
     양끝 dummy 핑거(게이트를 옆 컬럼 넷에 묶어 끈다), 모든 핑거 같은 방향, 드레인은 안쪽 컬럼
  2. 짝 넷(e1/e2, d1/d2, c1/s1_out, inn/inp)의 레인을 셀 중심 ±0.3 · ±0.9 · ±1.5 에 대칭으로
  3. NMOS·PMOS 영역마다 guard ring = 위·아래 탭 띠 + 셀 경계 세로 탭(이웃 셀과 맞붙어 이어진다).
     두 영역 사이는 p+ 띠(VSS) / n-well 띠(VDD) 가 나란한 이중 링. 세로 탭이 모든 diff 를 4 µm 안에 두므로
     gen_otacs 처럼 13 µm 마다 래치업 탭 띠를 따로 넣지 않는다
  4. 전류원 비율 = 단위 소자 개수: NMOS W0.9/L1 (tail 4, Inbias 1), PMOS W2/L0.8 (Iref 4+4, Ipbias 1)
  5. Cc = MIM. 고임피던스 s1_out 을 윗판(met4)에, 아랫판(met3) = cmid 가 밑 배선을 가린다. 소자 위에 겹쳐 높이를 쓰지 않는다
  6. Rz = res_high_po_0p35, bar licon 0.19×2.0, rpm ≥ 1.27, 몸통 2.165 µm (590 + 1112.41·L ≈ 3.0 kΩ)
사용: python gen_hog.py   → out/hog.gds · out/hog.cdl · out/hog.json
"""
import itertools, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klayout.db as pya
from devlib import Cell, SD, POH, SDW, M1SD, CPIT, CT, GSTRAP, M1G, VIA1, P1, NPC_ENC, finish, g as gsnap

NAME = os.environ.get("NAME", "hog")
OUTD = os.environ.get("OUTDIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
VER = int(os.environ.get("VER", "3"))   # 1 = 첫 판, 2 = 차폐·행 순서, 3 = PEX 보상 재조정 (Rz xhigh 4.47 kΩ)
PX = 8.430                       # EP 뉴런 열 피치 (otacs · SERN 뉴런과 같다)
XE = PX / 2                      # 셀 경계 x = ±XE (중심 0)
TAPW = 0.34                      # 경계 세로 탭 폭 (셀 안쪽)
XU = XE - TAPW - 0.40            # diff 가 들어갈 수 있는 |x| 한계 (탭과 0.40)
NW_SP = 1.07                     # p+ 탭 가장자리 ↔ n-well 가장자리 (otacs 와 같은 거리)
ISO = 0.65                       # 같은 행 섬 사이 diff 간격 (implant 0.125 둘 + nsdm 간격 0.38 ≤)
LV = 0.60                        # 스트랩 층 간격
GSTEP = 0.56                     # 게이트 버스 층 간격
W_LANE = 0.28
VIA2, VIA3, P2 = 0.200, 0.200, 0.370
CAP_INS, CAP_CLR, CAP_AREA = 0.50, 1.40, 48.48          # gen_otacs 와 같은 MIM 값 (100 fF)
RZ_L = 2.170                                            # 590 + 1112.41·2.17 = 3004 Ω (절반이 5 nm 격자에 맞아야 LVS 길이가 같다)
# v3 (2차 PEX 뒤 보상 재조정): post-layout netlist 로 Rz sweep → 4.5 kΩ 근처가 최적 (Cc 100 fF: PM 66.7°, 1 % settling 4.1 ns).
#   high-poly 로는 몸통 3.52 + 머리 4.32 = 7.84 µm 라 셀 폭을 넘는다 → xhigh-poly (588 + 5714.3·L, urpm 마커) L 0.68 → 4473 Ω
RZ_DEV, RZ_MARK, RZ_R = ("res_xhigh_po_0p35", "urpm", lambda L: 588.0 + 2000.0 / 0.35 * L) if VER >= 3 else \
                        ("res_high_po_0p35", "rpm", lambda L: 590.0 + 1112.41 * L)
if VER >= 3:
    RZ_L = 0.680
HEAD = 2.08                                             # 모델의 머리 길이 (siml + 2·2.08)

# 넷 → met2 레인 x. 같은 x 를 쓰는 넷은 세로 구간이 겹치지 않아야 한다 (아래에서 검사)
LANE = {"e1": -0.3, "e2": 0.3, "d1": -0.3, "d2": 0.3, "c1": -0.9, "s1_out": 0.9,
        "inn": -1.5, "inp": 1.5, "stail": -2.1, "pdrv": -2.1, "ndrv": 2.1,
        "cmid": -2.7, "out": 2.7, "vbnc": -3.3, "vss": -3.3, "vbp": -3.3,
        "vbn": 3.3, "vdd": 3.3, "vbpc": 3.3}
PINS = ("inp", "inn", "out", "vbn", "vbp", "vbnc", "vbpc")
# v2 (1차 PEX 뒤): d1/d2 레인은 ±0.3 그대로(2-D CC 배선에 필요), 그 바깥 ±0.9 에 VSS 차폐선 —
#   1차 PEX 에서 d1–d2 2.86 fF, d2–s1_out 2.12 fF, d1–c1 2.19 fF 결합 → folding 노드 극점이 내려와 PM 69° → 58°.
#   c1/s1_out 은 ±1.5, 입력 inn/inp 는 ±2.1, stail −2.7 로 옮긴다.
if VER >= 2:
    LANE.update({"c1": -1.5, "s1_out": 1.5, "inn": -2.1, "inp": 2.1, "stail": -2.7, "vss": -2.7})
SHIELD_X = (-0.9, 0.9) if VER >= 2 else ()


def isl(L, Wf, cols, gates, devs):
    assert len(gates) == len(cols) - 1 == len(devs)
    return dict(L=L, Wf=Wf, cols=cols, gates=gates, devs=devs)


D = "~"   # dummy 게이트 = 옆 컬럼 넷
# (이름, 종류, 섬들, 아래로 내리는 넷, 레일 방향)
ROWS = [
    ("NBAND0", "pband"),
    ("Rz", "res"),
    ("mirror_a", "n", [isl(0.5, 0.75, ["vss", "vss", "e1", "vss", "e2", "vss", "vss"], [D, "c1", "c1", "c1", "c1", D],
                           ["DUM", "Mm1", "Mm1", "Mm2", "Mm2", "DUM"])], {"vss"}, "both"),
    ("mirror_b", "n", [isl(0.5, 0.75, ["vss", "vss", "e2", "vss", "e1", "vss", "vss"], [D, "c1", "c1", "c1", "c1", D],
                           ["DUM", "Mm2", "Mm2", "Mm1", "Mm1", "DUM"])], {"vss"}, "both"),
    ("casn", "n", [isl(0.5, 1.5, ["e1", "c1", "e1"], ["vbnc", "vbnc"], ["Mcasn1"] * 2),
                   isl(0.5, 1.5, ["e2", "s1_out", "e2"], ["vbnc", "vbnc"], ["Mcasn2"] * 2)], {"e1", "e2"}, None),
    ("tail_inb", "n", [isl(1.0, 0.9, ["vss", "stail", "vss", "stail", "vss", "ndrv"], ["vbn"] * 5,
                           ["Mtail"] * 4 + ["Minb"])], {"vss"}, "both"),
    ("pair_a", "n", [isl(0.5, 0.75, ["stail", "stail", "d1", "stail", "d2", "stail", "stail"], [D, "inn", "inn", "inp", "inp", D],
                         ["DUM", "Md1", "Md1", "Md2", "Md2", "DUM"])], {"stail"}, None),
    ("pair_b", "n", [isl(0.5, 0.75, ["stail", "stail", "d2", "stail", "d1", "stail", "stail"], [D, "inp", "inp", "inn", "inn", D],
                         ["DUM", "Md2", "Md2", "Md1", "Md1", "DUM"])], {"stail"}, None),
    ("ncs_nls", "n", [isl(0.5, 1.5, ["vss", "out", "vss"], ["ndrv", "ndrv"], ["Mncs"] * 2),
                      isl(0.5, 1.5, ["ndrv", "vdd", "ndrv"], ["s1_out", "s1_out"], ["Mnls"] * 2)], {"vss", "ndrv"}, "left"),
    ("NBAND1", "pband"),
    ("PBAND0", "nband"),
    ("pls", "p", [isl(0.5, 1.5, ["pdrv", "vss", "pdrv"], ["s1_out", "s1_out"], ["Mpls"] * 2)], {"pdrv"}, None),
    ("pcs_ipb", "p", [isl(0.8, 2.0, ["vdd", "pdrv"], ["vbp"], ["Mipb"]),
                      isl(0.5, 2.5, ["vdd", "out", "vdd"], ["pdrv", "pdrv"], ["Mpcs"] * 2)], {"vdd"}, "both"),
    ("casp", "p", [isl(0.5, 1.5, ["d1", "c1", "d1"], ["vbpc", "vbpc"], ["Mcasp1"] * 2),
                   isl(0.5, 1.5, ["d2", "s1_out", "d2"], ["vbpc", "vbpc"], ["Mcasp2"] * 2)], {"d1", "d2"}, None),
    ("iref_a", "p", [isl(0.8, 2.0, ["vdd", "vdd", "d1", "vdd", "d2", "vdd", "vdd"], [D, "vbp", "vbp", "vbp", "vbp", D],
                         ["DUM", "Miref1", "Miref1", "Miref2", "Miref2", "DUM"])], {"vdd"}, "both"),
    ("iref_b", "p", [isl(0.8, 2.0, ["vdd", "vdd", "d2", "vdd", "d1", "vdd", "vdd"], [D, "vbp", "vbp", "vbp", "vbp", D],
                         ["DUM", "Miref2", "Miref2", "Miref1", "Miref1", "DUM"])], {"vdd"}, "both"),
    ("PBAND1", "nband"),
]
if VER >= 2:
    _r = {r[0]: r for r in ROWS}
    ROWS = [_r[k] for k in ("NBAND0", "Rz", "mirror_a", "mirror_b", "casn", "tail_inb", "ncs_nls", "pair_a", "pair_b",
                            "NBAND1", "PBAND0", "iref_a", "iref_b", "casp", "pcs_ipb", "pls", "PBAND1")]
# CDL 기준 (hog_tr.spice 와 같은 연결; W 는 레이아웃 핑거 합과 대조한다)
CDLDEV = {"Mm1": ("e1 c1 VSS VSS", "n", 3.0, 0.5), "Mm2": ("e2 c1 VSS VSS", "n", 3.0, 0.5),
          "Mcasn1": ("c1 vbnc e1 VSS", "n", 3.0, 0.5), "Mcasn2": ("s1_out vbnc e2 VSS", "n", 3.0, 0.5),
          "Mtail": ("stail vbn VSS VSS", "n", 3.6, 1.0), "Minb": ("ndrv vbn VSS VSS", "n", 0.9, 1.0),
          "Md1": ("d1 inn stail VSS", "n", 3.0, 0.5), "Md2": ("d2 inp stail VSS", "n", 3.0, 0.5),
          "Mncs": ("out ndrv VSS VSS", "n", 3.0, 0.5), "Mnls": ("VDD s1_out ndrv VSS", "n", 3.0, 0.5),
          "Mpls": ("VSS s1_out pdrv VDD", "p", 3.0, 0.5), "Mpcs": ("out pdrv VDD VDD", "p", 5.0, 0.5),
          "Mipb": ("pdrv vbp VDD VDD", "p", 2.0, 0.8),
          "Mcasp1": ("c1 vbpc d1 VDD", "p", 3.0, 0.5), "Mcasp2": ("s1_out vbpc d2 VDD", "p", 3.0, 0.5),
          "Miref1": ("d1 vbp VDD VDD", "p", 8.0, 0.8), "Miref2": ("d2 vbp VDD VDD", "p", 8.0, 0.8)}

ly = pya.Layout(); ly.dbu = 0.001
C = Cell(ly, NAME)
for k, v in dict(pres=(66, 13), rpm=(86, 20), urpm=(79, 20), capm=(89, 44), m4=(71, 20), via3=(70, 44), m3=(70, 20)).items():
    C.li[k] = ly.layer(*v)
TOUCH = {}                                   # 넷 → 레인에 비아를 내린 y 목록


def touch(n, y): TOUCH.setdefault(n, []).append(y)


def lane_via(n, y):                          # met1 위 (LANE[n], y) 에 via1 + met2 패드
    x = LANE[n]
    C.box(n, "m1", x - P1 / 2, y - P1 / 2, x + P1 / 2, y + P1 / 2)
    C.cut(n, "via", x, y, VIA1)
    C.box(n, "m2", x - P1 / 2, y - P1 / 2, x + P1 / 2, y + P1 / 2)
    touch(n, y)


# ---------------- 행 계획: 섬 x 위치, 컬럼·핑거 좌표 ----------------
def place(row):
    _, typ, isls, down, rail = row
    dws = [sum([i["L"]] * len(i["gates"])) + len(i["cols"]) * SD for i in isls]
    W = sum(dws) + ISO * (len(isls) - 1)
    x = -W / 2
    assert W / 2 <= XU + 1e-6, f"{row[0]}: 폭 {W:.3f} > {2*XU:.3f}"
    out = []
    for i, dw in zip(isls, dws):
        cx = [x + SD / 2 + k * (i["L"] + SD) for k in range(len(i["cols"]))]
        gx = [x + SD + k * (i["L"] + SD) + i["L"] / 2 for k in range(len(i["gates"]))]
        out.append(dict(i, x0=x, x1=x + dw, cx=cx, gx=gx))
        x += dw + ISO
    return out


def rail_ext(rail):
    xs = []
    if rail in ("both", "left"): xs.append(-XE + TAPW / 2)
    if rail in ("both", "right"): xs.append(XE - TAPW / 2)
    return xs


def strap_intervals(isls, side, down, rtyp, rail):
    """넷 → (구간 [x1,x2], 컬럼 x 목록). side='d' 아래 / 'u' 위."""
    rnet = "vss" if rtyp == "n" else "vdd"
    res = {}
    for i in isls:
        for x, n in zip(i["cx"], i["cols"]):
            if (n in down) != (side == "d"): continue
            res.setdefault(n, [[], []])[1].append(x)
    for n, (iv, xs) in res.items():
        a, b = min(xs) - M1SD / 2, max(xs) + M1SD / 2
        if n == rnet and side == "d":
            for xr in rail_ext(rail): a, b = min(a, xr), max(b, xr)
        else:
            a, b = min(a, LANE[n] - P1 / 2), max(b, LANE[n] + P1 / 2)
        res[n][0] = [a, b]
    return res


def assign_levels(ivs, margin=0.20, cross=0.26):
    """스트랩 층 배정. 같은 층 구간은 겹치지 않고, 낮은 층(소자에 가까운 쪽) 구간이 높은 층 넷의 세로 줄기를 덮지 않는다."""
    nets = list(ivs)
    blk = {n: (v[2] if len(v) > 2 else v[0]) for n, v in ivs.items()}   # 세로 줄기를 막는 구간 (게이트는 poly 버스만)
    best = None
    for perm in itertools.permutations(nets):
        lev = {}
        ok = True
        for n in perm:
            a, b = ivs[n][0]
            for k in range(len(nets)):
                same = [m for m in lev if lev[m] == k]
                if any(not (b + margin <= ivs[m][0][0] or ivs[m][0][1] + margin <= a) for m in same): continue
                lower = [m for m in lev if lev[m] < k]
                if any(blk[m][0] - cross < x < blk[m][1] + cross for m in lower for x in ivs[n][1]): continue
                higher = [m for m in lev if lev[m] > k]
                if any(blk[n][0] - cross < x < blk[n][1] + cross for m in higher for x in ivs[m][1]): continue
                lev[n] = k
                break
            else:
                ok = False; break
        if ok and (best is None or max(lev.values()) < max(best.values())):
            best = lev
    assert best is not None or not nets, f"층 배정 실패 {ivs}"
    return best or {}


def gate_intervals(isls):
    res = {}
    for i in isls:
        for x, g in zip(i["gx"], i["gates"]):
            if g == D: continue
            r = res.setdefault(g, [[], [], i["L"]])
            r[1].append(x)
    for g, r in res.items():
        L = r[2]
        bx1, bx2 = min(r[1]) - L / 2, max(r[1]) + L / 2
        r[0] = [min(bx1 - 0.25 + L / 2, LANE[g] - M1G[0] / 2), max(bx2 + 0.25 - L / 2, LANE[g] + M1G[0] / 2)]
    return res


# ---------------- 그리기 ----------------
y = 0.0
BANDS = {}
ROWINFO = []
FING = {}                                     # 소자 → [(Wf, L)] (CDL 대조)
DUMS = []


def band(kind, yc):
    net = "vss" if kind == "p" else "vdd"
    C.box(net, "tap", -XE, yc - 0.25, XE, yc + 0.25)
    C.box(None, "psd" if kind == "p" else "nsd", -XE - 0.125, yc - 0.375, XE + 0.125, yc + 0.375)
    C.box(net, "li1", -XE, yc - 0.25, XE, yc + 0.25)
    C.box(net, "m1", -XE, yc - 0.25, XE, yc + 0.25)
    xr = XE - TAPW - 0.15                                  # 컨택은 세로 탭 안쪽만 (모서리에서 탭 컨택과 겹치지 않게)
    n = int(2 * xr / CPIT) + 1; x0 = gsnap(-(n - 1) * CPIT / 2)
    for t in range(n):
        C.cut(net, "licon", x0 + t * CPIT, yc); C.cut(net, "mcon", x0 + t * CPIT, yc)


def strips(kind, ya, yb_):
    net = "vss" if kind == "p" else "vdd"
    for s in (-1, 1):
        xa, xb = (XE - TAPW, XE) if s > 0 else (-XE, -XE + TAPW)
        C.box(net, "tap", xa, ya, xb, yb_)
        C.box(None, "psd" if kind == "p" else "nsd", xa - 0.125, ya - 0.125, xb + 0.125, yb_ + 0.125)
        C.box(net, "li1", xa, ya, xb, yb_); C.box(net, "m1", xa, ya, xb, yb_)
        n = int((yb_ - ya - 0.4) / CPIT) + 1; y0 = gsnap((ya + yb_) / 2 - (n - 1) * CPIT / 2)
        for t in range(n):
            C.cut(net, "licon", (xa + xb) / 2, y0 + t * CPIT); C.cut(net, "mcon", (xa + xb) / 2, y0 + t * CPIT)


def draw_row(row, y0):
    name, typ, _, down, rail = row
    isls = place(row)
    dn = strap_intervals(isls, "d", down, typ, rail); dlev = assign_levels(dn)
    up = strap_intervals(isls, "u", down, typ, rail); ulev = assign_levels(up)
    gt = gate_intervals(isls)
    # 게이트: li1 구간 겹침 금지 + 낮은 층 버스가 높은 층 넷의 세로 poly 를 덮지 않게
    glev = assign_levels({g: [v[0], v[1], [min(v[1]) - v[2] / 2, max(v[1]) + v[2] / 2]] for g, v in gt.items()},
                         margin=0.24, cross=0.21 + 0.25)
    ndl = max(dlev.values()) + 1 if dlev else 1
    nul = max(ulev.values()) + 1 if ulev else 0
    yb = y0 + 0.72 + LV * (ndl - 1)
    ys = {n: yb - 0.36 - LV * k for n, k in dlev.items()}
    wfmax = max(i["Wf"] for i in isls)
    yt = yb + wfmax
    yd = {n: yt + 0.34 + LV * k for n, k in ulev.items()}
    gbase = (yt + 0.34 + LV * (nul - 1)) if nul else (yt - 0.18)
    gy = {g: gbase + 0.52 + GSTEP * k for g, k in glev.items()}
    top = (max(gy.values()) if gy else (max(yd.values()) if yd else yt)) + 0.30 + 0.18
    for i in isls:
        ytl = yb + i["Wf"]
        C.box(None, "diff", i["x0"], yb, i["x1"], ytl)
        C.box(None, "nsd" if typ == "n" else "psd", i["x0"] - 0.125, yb - 0.125, i["x1"] + 0.125, ytl + 0.125)
        usable = i["Wf"] - 0.12 - 0.17; nct = max(1, int(usable / CPIT) + 1)
        yc0 = gsnap(yb + 0.145 + (usable - (nct - 1) * CPIT) / 2)
        for x, n in zip(i["cx"], i["cols"]):
            C.box(n, "li1", x - SDW / 2, yb - 0.02, x + SDW / 2, ytl + 0.02)
            C.box(n, "m1", x - M1SD / 2, yb, x + M1SD / 2, ytl)
            for t in range(nct):
                C.cut(n, "licon", x, yc0 + t * CPIT); C.cut(n, "mcon", x, yc0 + t * CPIT)
            if n in down:
                C.box(n, "m1", x - M1SD / 2, ys[n] - 0.17, x + M1SD / 2, yb)
            else:
                C.box(n, "m1", x - M1SD / 2, ytl, x + M1SD / 2, yd[n] + 0.17)
        for k, (x, g, dv) in enumerate(zip(i["gx"], i["gates"], i["devs"])):
            L = i["L"]
            if g == D:                                      # dummy: 아래로 늘려 옆 컬럼 넷에 묶는다
                tn = i["cols"][k] if k == 0 else i["cols"][k + 1]
                assert dlev.get(tn) == 0, f"{name}: dummy 넷 {tn} 은 아래 0층이어야 한다"
                yy = ys[tn]
                C.box(tn, "poly", x - L / 2, yy - 0.135, x + L / 2, ytl + POH)
                C.cut(tn, "licon", x, yy)
                C.box(None, "npc", x - CT / 2 - NPC_ENC, yy - CT / 2 - NPC_ENC, x + CT / 2 + NPC_ENC, yy + CT / 2 + NPC_ENC)
                ca, cb = i["cx"][k], i["cx"][k + 1]
                C.box(tn, "li1", ca - SDW / 2, yy - 0.135, cb + SDW / 2, yb)
                DUMS.append((tn, typ, i["Wf"], L))
            else:
                C.box(g, "poly", x - L / 2, yb - POH, x + L / 2, ytl + POH)
                C.box(g, "poly", x - L / 2, ytl, x + L / 2, gy[g])
                FING.setdefault(dv, []).append((i["Wf"], L))
    rnet = "vss" if typ == "n" else "vdd"
    for n, (iv, _) in dn.items():
        C.box(n, "m1", iv[0], ys[n] - 0.17, iv[1], ys[n] + 0.17)
        if not (n == rnet): lane_via(n, ys[n])
    for n, (iv, _) in up.items():
        C.box(n, "m1", iv[0], yd[n] - 0.17, iv[1], yd[n] + 0.17)
        lane_via(n, yd[n])
    for g, (iv, xs, L) in gt.items():
        yy = gy[g]
        C.box(g, "poly", min(xs) - L / 2, yy - 0.18, max(xs) + L / 2, yy + 0.18)
        for x in xs: C.cut(g, "licon", x, yy)
        C.box(None, "npc", min(xs) - CT / 2 - NPC_ENC, yy - CT / 2 - NPC_ENC, max(xs) + CT / 2 + NPC_ENC, yy + CT / 2 + NPC_ENC)
        C.box(g, "li1", iv[0], yy - GSTRAP[1] / 2, iv[1], yy + GSTRAP[1] / 2)
        x = LANE[g]
        C.cut(g, "mcon", x, yy)
        C.box(g, "m1", x - M1G[0] / 2, yy - M1G[1] / 2, x + M1G[0] / 2, yy + M1G[1] / 2)
        C.cut(g, "via", x, yy, VIA1); C.box(g, "m2", x - P1 / 2, yy - P1 / 2, x + P1 / 2, yy + P1 / 2); touch(g, yy)
    ROWINFO.append(dict(name=name, typ=typ, y0=round(y0, 3), y1=round(top, 3), h=round(top - y0, 3),
                        levels=dict(down=dlev, up=ulev, gate=glev),
                        islands=[dict(x0=round(i["x0"], 3), x1=round(i["x1"], 3), L=i["L"], Wf=i["Wf"],
                                      cols=i["cols"], gates=i["gates"], devs=i["devs"]) for i in isls]))
    return top


def draw_rz(y0):
    """res_high_po_0p35 가로: 왼쪽 머리 = cmid, 오른쪽 머리 = out."""
    # LVS 인식 (sky130.lvs prec_resistor): 단자 = poly∩li1, 몸통 = poly∩psdm∩npc − 단자, 몸통·단자 경계 길이 = 0.35.
    # 그래서 li1 이 머리에서 poly 폭 전체를 덮고, 몸통 길이(li1 사이) = pres 길이 = RZ_L 이 되게 한다.
    ry = y0 + 0.635 + 0.30
    xb = RZ_L / 2; xp = xb + HEAD + 0.08                   # bar licon 2.0 + li1·poly 감싸기 0.08 씩
    C.box("rz", "poly", -xp, ry - 0.175, xp, ry + 0.175)
    C.box("rz", "pres", -xb, ry - 0.175, xb, ry + 0.175)
    C.box(None, RZ_MARK, -xp - 0.20, ry - 0.635, xp + 0.20, ry + 0.635)
    C.box(None, "psd", -(XE - TAPW + 0.05), ry - 0.635, XE - TAPW + 0.05, ry + 0.635)   # 세로 p 탭의 psd 와 이어 붙인다 (psd.2)
    C.box(None, "npc", -xp - 0.10, ry - 0.535, xp + 0.10, ry + 0.535)
    for s, n in ((-1, "cmid"), (1, "out")):
        a, b = sorted((s * (xb + 0.08), s * (xb + 2.08)))
        C.box(n, "licon", a, ry - 0.095, b, ry + 0.095)
        C.box(n, "li1", min(a, b) - 0.08, ry - 0.205, max(a, b) + 0.08, ry + 0.205)
        m = int((b - a - 0.17) / CPIT) + 1; xm0 = gsnap((a + b) / 2 - (m - 1) * CPIT / 2)
        for t in range(m): C.cut(n, "mcon", xm0 + t * CPIT, ry)
        C.box(n, "m1", min(a - 0.03, LANE[n] - P1 / 2), ry - 0.17, max(b + 0.03, LANE[n] + P1 / 2), ry + 0.17)  # 머리가 레인에 못 닿으면 met1 로 잇는다
        C.cut(n, "via", LANE[n], ry, VIA1)
        C.box(n, "m2", LANE[n] - P1 / 2, ry - P1 / 2, LANE[n] + P1 / 2, ry + P1 / 2); touch(n, ry)
    ROWINFO.append(dict(name="Rz", typ="res", y0=round(y0, 3), y1=round(ry + 1.035, 3), h=round(ry + 1.035 - y0, 3), ohm=round(RZ_R(RZ_L)), dev=RZ_DEV))
    return ry + 0.635 + 0.40


REG = {}
for row in ROWS:
    kind = row[1]
    if kind in ("pband", "nband"):
        k = "p" if kind == "pband" else "n"
        if row[0] == "PBAND0":                              # n-well 시작: p+ 띠에서 NW_SP 띄운다
            y = BANDS["NBAND1"] + 0.25 + NW_SP + 0.63 - 0.5
        band(k, y + 0.5); BANDS[row[0]] = y + 0.5
        y += 1.0
        continue
    if kind == "res":
        y = draw_rz(y); continue
    y = draw_row(row, y)
    y += 0.0

yN0, yN1, yP0, yP1 = BANDS["NBAND0"], BANDS["NBAND1"], BANDS["PBAND0"], BANDS["PBAND1"]
strips("p", yN0 - 0.25, yN1 + 0.25)
strips("n", yP0 - 0.25, yP1 + 0.25)
C.box("vdd", "nw", -XE - 0.35, yP0 - 0.63, XE + 0.35, yP1 + 0.63)    # hvdifftap.19: HV n 탭을 0.33 이상 감싼다
# 영역 사이 레인: nls 드레인 VDD → PMOS 아래 n 띠, pls 드레인 VSS → NMOS 위 p 띠
lane_via("vdd", yP0); lane_via("vss", yN1)
# VSS 차폐선 (critical node shielding, Lecture 3): d1/d2 레인을 따라 입력쌍 아래에서 casp 위까지, NMOS 위 p 띠에서 VSS
if SHIELD_X:
    _ri = {r["name"]: r for r in ROWINFO}
    ya, yb2 = _ri["pair_a"]["y0"] + 0.2, _ri["casp"]["y1"] - 0.2
    for xs in SHIELD_X:
        C.box("vss", "m2", xs - W_LANE / 2, ya, xs + W_LANE / 2, yb2)
        C.box("vss", "m1", xs - P1 / 2, yN1 - P1 / 2, xs + P1 / 2, yN1 + P1 / 2)
        C.cut("vss", "via", xs, yN1, VIA1)
        C.box("vss", "m2", xs - P1 / 2, yN1 - P1 / 2, xs + P1 / 2, yN1 + P1 / 2)

# ---------------- Cc (MIM): 아랫판 met3 = cmid, 윗판 capm/met4 = s1_out — NMOS 아래쪽 소자 위에 겹친다 ----------------
pw = PX - 1.40; ph = CAP_AREA / (pw - 2 * CAP_INS) + 2 * CAP_INS
cy0 = yN0 + 0.40; px0 = -pw / 2
C.box("cmid", "m3", px0, cy0, px0 + pw, cy0 + ph)
C.box("s1_out", "capm", px0 + CAP_INS, cy0 + CAP_INS, px0 + pw - CAP_INS, cy0 + ph - CAP_INS)
C.box("s1_out", "m4", px0 + CAP_INS + 0.06, cy0 + CAP_INS + 0.06, px0 + pw - CAP_INS - 0.06, cy0 + ph - CAP_INS - 0.06)
nx3 = int((pw - 2 * CAP_INS - 0.5) / 0.40); ny3 = int((ph - 2 * CAP_INS - 0.5) / 0.40)
for i in range(nx3):
    for j in range(ny3): C.cut("s1_out", "via3", px0 + CAP_INS + 0.31 + i * 0.40, cy0 + CAP_INS + 0.31 + j * 0.40, VIA3)
vy = cy0 + CAP_INS / 2                                      # cmid 아랫판 → met2 (capm 에서 INS/2)
x = LANE["cmid"]
C.cut("cmid", "via2", x, vy, VIA2); C.box("cmid", "m2", x - P2 / 2, vy - P2 / 2, x + P2 / 2, vy + P2 / 2); touch("cmid", vy)
x = LANE["s1_out"]; ytop = cy0 + ph                         # s1_out 윗판 → met4 라이저 → capm.11 을 넘긴 뒤 met3 패드
C.box("s1_out", "m4", x - 0.26, cy0 + ph - CAP_INS - 0.06, x + 0.26, ytop + CAP_CLR + 0.52)
py3 = ytop + CAP_CLR + 0.26
C.box("s1_out", "m3", x - 0.26, py3 - 0.26, x + 0.26, py3 + 0.26); C.cut("s1_out", "via3", x, py3, VIA3)
C.box("s1_out", "m2", x - P2 / 2, py3 - P2 / 2, x + P2 / 2, py3 + P2 / 2); C.cut("s1_out", "via2", x, py3, VIA2); touch("s1_out", py3)

# ---------------- met2 레인 + 같은 x 레인끼리 구간 검사 ----------------
SPAN = {n: (min(v) - 0.18, max(v) + 0.18) for n, v in TOUCH.items()}
for n, (a, b) in SPAN.items():
    C.box(n, "m2", LANE[n] - W_LANE / 2, a, LANE[n] + W_LANE / 2, b)
clash = []
for n1, n2 in itertools.combinations(SPAN, 2):
    if abs(LANE[n1] - LANE[n2]) < 0.59 and not (SPAN[n1][1] + 0.20 <= SPAN[n2][0] or SPAN[n2][1] + 0.20 <= SPAN[n1][0]):
        clash.append((n1, n2, SPAN[n1], SPAN[n2]))
for n in PINS:
    C.label(n, "lbl_m2", LANE[n], SPAN[n][1] - 0.18)
C.label("VDD", "lbl_m1", XE - TAPW / 2, (yP0 + yP1) / 2)
C.label("VSS", "lbl_m1", XE - TAPW / 2, (yN0 + yN1) / 2)

bb = finish(C)
os.makedirs(OUTD, exist_ok=True)
ly.write(os.path.join(OUTD, NAME + ".gds"))

# ---------------- 검사 · CDL · 요약 ----------------
bad = C.shorts()
for lay in ("m3", "m4", "capm"):
    ns = [n for n in C.net if lay in C.net[n]]
    for i in range(len(ns)):
        for j in range(i + 1, len(ns)):
            if not (C.net[ns[i]][lay] & C.net[ns[j]][lay]).is_empty(): bad.append((lay, ns[i], ns[j]))
wchk = {}
for dv, fs in FING.items():
    W = round(sum(f[0] for f in fs), 3); L = fs[0][1]
    wchk[dv] = (W, L, CDLDEV[dv][2], CDLDEV[dv][3])
    assert abs(W - CDLDEV[dv][2]) < 1e-6 and abs(L - CDLDEV[dv][3]) < 1e-6, (dv, W, L, CDLDEV[dv])
assert set(FING) == set(CDLDEV), set(CDLDEV) ^ set(FING)
cw = round((pw - 2 * CAP_INS) / 0.005) * 0.005; ch = round((ph - 2 * CAP_INS) / 0.005) * 0.005
mod = {"n": "nfet_g5v0d10v5", "p": "pfet_g5v0d10v5"}
cdl = [f".subckt {NAME} inp inn out vbn vbp vbnc vbpc VDD VSS"]
for dv, (conn, t, W, L) in CDLDEV.items():
    cdl.append(f"MX{dv} {conn} {mod[t]} w={W:g}u l={L:g}u")
for k, (n, t, Wf, L) in enumerate(DUMS):
    nn = n.upper() if n in ("vdd", "vss") else n
    cdl.append(f"MXDUM{k} {nn} {nn} {nn} {'VSS' if t == 'n' else 'VDD'} {mod[t]} w={Wf:g}u l={L:g}u")
cdl += [f"CCc s1_out cmid cap_mim_m3__base w={cw:.3f}u l={ch:.3f}u",
        f"RRz cmid out $SUB=VSS $[{RZ_DEV}] w=0.350u l={RZ_L:.3f}u",
        f".ends {NAME}"]
open(os.path.join(OUTD, NAME + ".cdl"), "w").write("\n".join(cdl) + "\n")
W_, H_ = bb[2] - bb[0], bb[3] - bb[1]
info = dict(cell=NAME, ver=VER, shields=list(SHIELD_X), pitch=PX, bbox=[round(v, 3) for v in bb], w=round(W_, 3), h=round(H_, 3),
            core_h=round(yP1 + 0.25 - (yN0 - 0.25), 3), bands=BANDS, rows=ROWINFO, lanes=LANE,
            spans={n: [round(a, 3), round(b, 3)] for n, (a, b) in SPAN.items()},
            cap=dict(w=cw, l=ch, y0=round(cy0, 3), y1=round(cy0 + ph, 3)), rz_l=RZ_L, rz_dev=RZ_DEV, rz_ohm=round(RZ_R(RZ_L), 1),
            dummies=len(DUMS), shorts=bad, lane_clash=clash, wcheck=wchk)
json.dump(info, open(os.path.join(OUTD, NAME + ".json"), "w"), indent=1)
print(f"{NAME}: bbox {W_:.3f} x {H_:.3f} um (pitch {PX}), core {info['core_h']:.3f}, dummies {len(DUMS)}")
for r in ROWINFO:
    print(f"   {r['name']:9s} y {r['y0']:7.3f} – {r['y1']:7.3f}  h {r['h']:.3f}" + (f"  lev {r['levels']}" if 'levels' in r else ""))
print("   shorts:", bad or "none")
print("   lane clash:", clash or "none")

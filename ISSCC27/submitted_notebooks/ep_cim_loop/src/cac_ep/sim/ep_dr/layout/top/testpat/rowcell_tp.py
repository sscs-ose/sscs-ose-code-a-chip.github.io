#!/usr/bin/env python3
"""[testpat 사본 10/28: layout/blk_wu/rowcell.py (md5 169dea53f9f426fa48ccc5d4269ee726) 를 그대로 복사, 고친 곳 없음 — 원본이 바뀌어도 test pattern 이 그대로이게]
row-stack 아날로그·논리 셀 엔진 — sern_hog_classab_opamp/sim/layout/gen_hog.py 의 행 그리기를 일반화한 사본 (원본은 읽기만).

gen_hog 에서 그대로: 세로 poly 핑거, 핑거 피치 L + 0.29, S/D li1 0.17·met1 0.23, 컨택 피치 0.36, 섬(island) 단위 diff,
  소스·드레인 스트랩 = met1 가로 (아래 = down 넷, 위 = up 넷, 층 LV 0.60), 게이트 = poly 버스 + li1 스트랩 (층 GSTEP),
  넷마다 met2 세로 레인 (via1 로 스트랩·게이트를 내린다), 아래 = NMOS 영역 (p 탭 띠 둘 + 경계 세로 p 탭),
  위 = PMOS 영역 (n-well, n 탭 띠 둘 + 경계 세로 n 탭), hvi 셀 전체.
바꾼 것:
  1. 셀 폭 XE, 레인, 행, 소자를 인자로 (함수 build()), 레인 자동 배정 (넷 도형 x 평균에 가까운 빈 칸)
  2. 스트랩·게이트 층 배정 = 되돌이 탐색 (gen_hog 의 순열 탐색은 넷 8 개 이상에서 느림)
  3. 한 행 안에서만 쓰는 넷 (local) 은 레인 없이 스트랩만
  4. 핀 레인을 셀 위·아래 끝까지 늘림 (exits) — 같은 x 레인 겹침 검사 포함
  5. 띠 위치 강제 (같은 줄 셀끼리 VSS·VDD 띠 높이를 맞춰 맞붙인다)
  6. GSTEP 0.56 → 0.65 (층이 다른 게이트 버스가 x 로 겹칠 때 poly.2 0.21·npc.2 0.27 — 0.60 은 잡 721140 에서 npc.2)
좌표 µm, 셀 중심 x = 0, 맨 아래 p 탭 띠 아래 끝 y = 0.25.
"""
import sys
sys.path.insert(0, '/home/dave/work/projects/sern_hog_classab_opamp/sim/layout')   # devlib (cut 격자 맞춤 사본), 읽기만
import klayout.db as pya                                                              # noqa: E402
from devlib import Cell, SD, POH, SDW, M1SD, CPIT, CT, GSTRAP, M1G, VIA1, P1, NPC_ENC, g as gsnap   # noqa: E402,F401

TAPW = 0.34            # 경계 세로 탭 폭
NW_SP = 1.07           # p 탭 띠 ↔ n-well 가장자리
ISO = 0.65             # 같은 행 섬 사이 diff 간격
LV = 0.60              # 스트랩 층 간격
GSTEP = 0.65           # 게이트 버스 층 간격 (npc 상자 0.37 → 간격 0.28 ≥ npc.2 0.27)
W_LANE = 0.28
LANE_P = 0.60          # 레인 칸 간격
D = "~"                # dummy 게이트 (쓰지 않음, gen_hog 호환)
MOD = {"n": "nfet_g5v0d10v5", "p": "pfet_g5v0d10v5"}


def isl(L, Wf, cols, gates, devs):
    assert len(gates) == len(cols) - 1 == len(devs), (cols, gates, devs)
    return dict(L=L, Wf=Wf, cols=list(cols), gates=list(gates), devs=list(devs))


def solve_levels(ivs, margin, cross):
    """ivs: 넷 → (구간 [a, b], 세로 줄기 x 목록, 막는 구간 [c, d]).  같은 층 구간은 margin 띄우고,
    낮은 층 (소자에 가까운 쪽) 넷의 막는 구간이 높은 층 넷의 줄기 x 를 덮지 않는다. 최대 층 최소화 (되돌이 탐색)."""
    nets = sorted(ivs, key=lambda n: -(ivs[n][0][1] - ivs[n][0][0]))

    def ok(n, k, lev):
        a, b = ivs[n][0]
        for m, km in lev.items():
            if km == k:
                c, d = ivs[m][0]
                if not (b + margin <= c or d + margin <= a):
                    return False
            elif km < k:
                c, d = ivs[m][2]
                if any(c - cross < x < d + cross for x in ivs[n][1]):
                    return False
            else:
                c, d = ivs[n][2]
                if any(c - cross < x < d + cross for x in ivs[m][1]):
                    return False
        return True

    for K in range(1, len(nets) + 1):
        lev = {}

        def bt(i):
            if i == len(nets):
                return True
            for k in range(K):
                if ok(nets[i], k, lev):
                    lev[nets[i]] = k
                    if bt(i + 1):
                        return True
                    del lev[nets[i]]
            return False
        if bt(0):
            return dict(lev)
    if not nets:
        return {}
    raise RuntimeError(f"층 배정 실패 {ivs}")


def place_row(isls, XU):
    dws = [i["L"] * len(i["gates"]) + len(i["cols"]) * SD for i in isls]
    W = sum(dws) + ISO * (len(isls) - 1)
    assert W / 2 <= XU + 1e-6, f"행 폭 {W:.3f} > {2 * XU:.3f}"
    x = -W / 2
    out = []
    for i, dw in zip(isls, dws):
        cx = [gsnap(x + SD / 2 + k * (i["L"] + SD)) for k in range(len(i["cols"]))]
        gx = [gsnap(x + SD + k * (i["L"] + SD) + i["L"] / 2) for k in range(len(i["gates"]))]
        out.append(dict(i, x0=gsnap(x), x1=gsnap(x + dw), cx=cx, gx=gx))
        x += dw + ISO
    return out


def build(ly, name, XE, rows, cdldev, ports, exits=None, local=(), lanes=None, force=None, label=True, nocont=(), search=False):
    """rows: [(행 이름, 'n'|'p', [isl…], down 넷 집합, rail 'both'|'left'|'right'|None)] (n 행 먼저).
    cdldev: 소자 → (연결 'd g s', 'n'|'p', W, L).  ports: CDL subckt 핀 순서 (vdd·vss 포함).
    exits: 넷 → 'top'|'bot'|'both' (레인을 셀 끝까지).  lanes: 넷 → x 고정 (나머지는 자동).
    force: dict(NBAND1=…, PBAND1=…) 띠 위치 강제 (자연값보다 작으면 무시).
    search: 섬 순서·뒤집기도 탐색 (행 높이 합 최소).
    nocont: 컨택을 넣지 않을 경계 세로 탭 ('left'·'right') — 셀을 맞붙이면 두 탭의 컨택이 0.34 간격이라 mcon.2 (0.19) 위반 (잡 721152).
    반환 (Cell, info)."""
    exits = exits or {}
    local = set(local)
    rows = list(rows)
    XU = XE - TAPW - 0.40
    C = Cell(ly, name)
    for k, v in dict(lbl_m3=(70, 5)).items():
        C.li[k] = ly.layer(*v)
    nrows = [r for r in rows if r[1] == "n"]
    prows = [r for r in rows if r[1] == "p"]
    placed = {r[0]: place_row(r[2], XU) for r in rows}

    # ---------- 레인 자동 배정: 넷마다 도형 x 평균 → 가장 가까운 빈 칸 ----------
    feats = {}
    for r in rows:
        for i in placed[r[0]]:
            for x, n in zip(i["cx"], i["cols"]):
                feats.setdefault(n, []).append(x)
            for x, gn in zip(i["gx"], i["gates"]):
                feats.setdefault(gn, []).append(x)
    rails = {"vss", "vdd"}
    LANE = dict(lanes or {})
    nslot = int((XU - 0.15) // LANE_P)
    slots = [gsnap(k * LANE_P) for k in range(-nslot, nslot + 1)]
    used = set(LANE.values())
    need = [n for n in feats if n not in LANE and n not in local and n not in rails]
    need += [n for n in ports if n not in feats and n not in LANE and n not in rails]
    for n in sorted(need, key=lambda n: len(feats.get(n, [])), reverse=True):
        mx = sum(feats.get(n, [0])) / max(1, len(feats.get(n, [0])))
        free = [s for s in slots if all(abs(s - u) > LANE_P - 0.011 for u in used)]
        s = min(free, key=lambda s: abs(s - mx))
        LANE[n] = s; used.add(s)
    movable = [n for n in LANE if n not in (lanes or {})]

    TOUCH = {}

    def touch(n, y):
        TOUCH.setdefault(n, []).append(y)

    def lane_via(n, y):
        x = LANE[n]
        C.box(n, "m1", x - P1 / 2, y - P1 / 2, x + P1 / 2, y + P1 / 2)
        C.cut(n, "via", x, y, VIA1)
        C.box(n, "m2", x - P1 / 2, y - P1 / 2, x + P1 / 2, y + P1 / 2)
        touch(n, y)

    def rail_ext(rail):
        xs = []
        if rail in ("both", "left"):
            xs.append(-XE + TAPW / 2)
        if rail in ("both", "right"):
            xs.append(XE - TAPW / 2)
        return xs

    def strap_iv(isls, side, down, rtyp, rail):
        rnet = "vss" if rtyp == "n" else "vdd"
        res = {}
        for i in isls:
            for x, n in zip(i["cx"], i["cols"]):
                if (n in down) != (side == "d"):
                    continue
                res.setdefault(n, [[], []])[1].append(x)
        for n, (iv, xs) in res.items():
            a, b = min(xs) - M1SD / 2, max(xs) + M1SD / 2
            if n == rnet and side == "d":
                for xr in rail_ext(rail):
                    a, b = min(a, xr), max(b, xr)
                assert rail, f"{name}: {n} 이 아래 넷인데 rail 이 없음"
            elif n in local:
                pass
            else:
                a, b = min(a, LANE[n] - P1 / 2), max(b, LANE[n] + P1 / 2)
            res[n] = [[a, b], xs, [a, b]]
        return res

    def gate_iv(isls):
        res = {}
        for i in isls:
            for x, gn in zip(i["gx"], i["gates"]):
                r = res.setdefault(gn, [None, [], i["L"]])
                r[1].append(x)
        out = {}
        for gn, (_, xs, L) in res.items():
            bx1, bx2 = min(xs) - L / 2, max(xs) + L / 2
            a = min(bx1 - 0.25 + L / 2, LANE[gn] - M1G[0] / 2)
            b = max(bx2 + 0.25 - L / 2, LANE[gn] + M1G[0] / 2)
            out[gn] = [[a, b], xs, [bx1, bx2], L]
        return out

    # ---------- 레인 최적화: 행 높이 합이 가장 작게 (한 넷 옮기기 / 두 넷 바꾸기, 가장 좋은 수부터) ----------
    def row_h(row):
        rname, typ, _, down, rail = row
        isls = placed[rname]
        try:
            dl = solve_levels(strap_iv(isls, "d", down, typ, rail), 0.20, 0.26)
            ul = solve_levels(strap_iv(isls, "u", down, typ, rail), 0.20, 0.26)
            gl = solve_levels({k: v[:3] for k, v in gate_iv(isls).items()}, 0.24, 0.21 + 0.25)
        except RuntimeError:
            return 1e9
        ndl = max(dl.values()) + 1 if dl else 1
        nul = max(ul.values()) + 1 if ul else 0
        ngl = max(gl.values()) + 1 if gl else 1
        wf = max(i["Wf"] for i in isls)
        return 0.72 + LV * (ndl - 1) + wf + ((0.34 + LV * (nul - 1)) if nul else -0.18) + 0.52 + GSTEP * (ngl - 1) + 0.48

    def total():
        return sum(row_h(r) for r in rows)

    def lane_climb(best):
      for _ in range(60):
        cand = None
        occ = {round(v, 3) for v in LANE.values()}
        for n in movable:
            old = LANE[n]
            for s in slots:
                if any(abs(s - u) < LANE_P - 0.011 for u in occ if abs(u - old) > 1e-6):
                    continue
                LANE[n] = s
                c = total()
                if c < best - 1e-6 and (cand is None or c < cand[0]):
                    cand = (c, ((n, s),))
            LANE[n] = old
            for m in movable:
                if m <= n:
                    continue
                LANE[n], LANE[m] = LANE[m], LANE[n]
                c = total()
                if c < best - 1e-6 and (cand is None or c < cand[0]):
                    cand = (c, ((n, LANE[n]), (m, LANE[m])))
                LANE[n], LANE[m] = LANE[m], LANE[n]
        if cand is None:
            break
        best = cand[0]
        for n, s in cand[1]:
            LANE[n] = s
      return best

    def flip(i):
        return dict(i, cols=i["cols"][::-1], gates=i["gates"][::-1], devs=i["devs"][::-1])

    best = lane_climb(total())
    if search:                     # 섬 순서·좌우 뒤집기 탐색 ↔ 레인 최적화를 번갈아
        import itertools as _it
        for _ in range(6):
            improved = False
            for r in rows:
                base = r[2]
                cur = row_h(r)
                bestp = None
                for perm in _it.permutations(range(len(base))):
                    for fl in _it.product((0, 1), repeat=len(base)):
                        isl2 = [flip(base[p]) if f else base[p] for p, f in zip(perm, fl)]
                        try:
                            placed[r[0]] = place_row(isl2, XU)
                        except AssertionError:
                            continue
                        h = row_h(r)
                        if h < cur - 1e-6:
                            cur, bestp = h, isl2
                placed[r[0]] = place_row(bestp or base, XU)
                if bestp:
                    rows[rows.index(r)] = (r[0], r[1], bestp, r[3], r[4])
                    improved = True
            nb = lane_climb(total())
            if not improved and nb >= best - 1e-6:
                break
            best = nb
        nrows[:] = [r for r in rows if r[1] == "n"]
        prows[:] = [r for r in rows if r[1] == "p"]

    FING = {}
    ROWINFO = []

    def draw_row(row, y0):
        rname, typ, _, down, rail = row
        isls = placed[rname]
        dn = strap_iv(isls, "d", down, typ, rail)
        up = strap_iv(isls, "u", down, typ, rail)
        dlev = solve_levels(dn, 0.20, 0.26)
        ulev = solve_levels(up, 0.20, 0.26)
        gt = gate_iv(isls)
        glev = solve_levels({k: v[:3] for k, v in gt.items()}, 0.24, 0.21 + 0.25)
        ndl = max(dlev.values()) + 1 if dlev else 1
        nul = max(ulev.values()) + 1 if ulev else 0
        yb = y0 + 0.72 + LV * (ndl - 1)
        ys = {n: yb - 0.36 - LV * k for n, k in dlev.items()}
        wfmax = max(i["Wf"] for i in isls)
        yt = yb + wfmax
        yd = {n: yt + 0.34 + LV * k for n, k in ulev.items()}
        gbase = (yt + 0.34 + LV * (nul - 1)) if nul else (yt - 0.18)
        gy = {gn: gbase + 0.52 + GSTEP * k for gn, k in glev.items()}
        top = max(gy.values()) + 0.30 + 0.18
        for i in isls:
            ytl = yb + i["Wf"]
            C.box(None, "diff", i["x0"], yb, i["x1"], ytl)
            C.box(None, "nsd" if typ == "n" else "psd", i["x0"] - 0.125, yb - 0.125, i["x1"] + 0.125, ytl + 0.125)
            usable = i["Wf"] - 0.12 - 0.17
            nct = max(1, int(usable / CPIT) + 1)
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
            for x, gn, dv in zip(i["gx"], i["gates"], i["devs"]):
                L = i["L"]
                C.box(gn, "poly", x - L / 2, yb - POH, x + L / 2, ytl + POH)
                C.box(gn, "poly", x - L / 2, ytl, x + L / 2, gy[gn])
                FING.setdefault(dv, []).append((i["Wf"], L))
        rnet = "vss" if typ == "n" else "vdd"
        for n, (iv, _, _) in dn.items():
            C.box(n, "m1", iv[0], ys[n] - 0.17, iv[1], ys[n] + 0.17)
            if n != rnet and n not in local:
                lane_via(n, ys[n])
        for n, (iv, _, _) in up.items():
            C.box(n, "m1", iv[0], yd[n] - 0.17, iv[1], yd[n] + 0.17)
            if n not in local:
                lane_via(n, yd[n])
        for gn, (iv, xs, _, L) in gt.items():
            yy = gy[gn]
            C.box(gn, "poly", min(xs) - L / 2, yy - 0.18, max(xs) + L / 2, yy + 0.18)
            for x in xs:
                C.cut(gn, "licon", x, yy)
            C.box(None, "npc", min(xs) - CT / 2 - NPC_ENC, yy - CT / 2 - NPC_ENC, max(xs) + CT / 2 + NPC_ENC, yy + CT / 2 + NPC_ENC)
            C.box(gn, "li1", iv[0], yy - GSTRAP[1] / 2, iv[1], yy + GSTRAP[1] / 2)
            x = LANE[gn]
            C.cut(gn, "mcon", x, yy)
            C.box(gn, "m1", x - M1G[0] / 2, yy - M1G[1] / 2, x + M1G[0] / 2, yy + M1G[1] / 2)
            C.cut(gn, "via", x, yy, VIA1)
            C.box(gn, "m2", x - P1 / 2, yy - P1 / 2, x + P1 / 2, yy + P1 / 2)
            touch(gn, yy)
        ROWINFO.append(dict(name=rname, typ=typ, y0=round(y0, 3), y1=round(top, 3), levels=dict(down=dlev, up=ulev, gate=glev)))
        return top

    BANDS = {}

    def band(kind, yc):
        net = "vss" if kind == "p" else "vdd"
        C.box(net, "tap", -XE, yc - 0.25, XE, yc + 0.25)
        C.box(None, "psd" if kind == "p" else "nsd", -XE - 0.125, yc - 0.375, XE + 0.125, yc + 0.375)
        C.box(net, "li1", -XE, yc - 0.25, XE, yc + 0.25)
        C.box(net, "m1", -XE, yc - 0.25, XE, yc + 0.25)
        xr = XE - TAPW - 0.15
        nn = int(2 * xr / CPIT) + 1
        x0 = gsnap(-(nn - 1) * CPIT / 2)
        for t in range(nn):
            C.cut(net, "licon", x0 + t * CPIT, yc); C.cut(net, "mcon", x0 + t * CPIT, yc)

    def strips(kind, ya, yb_):
        net = "vss" if kind == "p" else "vdd"
        for s in (-1, 1):
            xa, xb = (XE - TAPW, XE) if s > 0 else (-XE, -XE + TAPW)
            C.box(net, "tap", xa, ya, xb, yb_)
            C.box(None, "psd" if kind == "p" else "nsd", xa - 0.125, ya - 0.125, xb + 0.125, yb_ + 0.125)
            C.box(net, "li1", xa, ya, xb, yb_); C.box(net, "m1", xa, ya, xb, yb_)
            if ("left" if s < 0 else "right") in nocont:
                continue
            nn = int((yb_ - ya - 0.4) / CPIT) + 1
            y0 = gsnap((ya + yb_) / 2 - (nn - 1) * CPIT / 2)
            for t in range(nn):
                C.cut(net, "licon", (xa + xb) / 2, y0 + t * CPIT); C.cut(net, "mcon", (xa + xb) / 2, y0 + t * CPIT)

    force = force or {}
    y = 0.0
    band("p", y + 0.5); BANDS["NBAND0"] = y + 0.5; y += 1.0
    for r in nrows:
        y = draw_row(r, y)
    yn1 = max(gsnap(y + 0.5), force.get("NBAND1", 0))
    band("p", yn1); BANDS["NBAND1"] = yn1
    yp0 = gsnap(yn1 + 0.25 + NW_SP + 0.63)
    band("n", yp0); BANDS["PBAND0"] = yp0
    y = yp0 + 0.5
    for r in prows:
        y = draw_row(r, y)
    yp1 = max(gsnap(y + 0.5), force.get("PBAND1", 0))
    band("n", yp1); BANDS["PBAND1"] = yp1
    strips("p", BANDS["NBAND0"] - 0.25, yn1 + 0.25)
    strips("n", yp0 - 0.25, yp1 + 0.25)
    C.box("vdd", "nw", -XE - 0.35, yp0 - 0.63, XE + 0.35, yp1 + 0.63)
    # rail 이 아닌 vdd (NMOS 행) / vss (PMOS 행) 레인 → 반대쪽 띠에 비아
    if "vdd" in TOUCH:
        lane_via("vdd", yp0)
    if "vss" in TOUCH:
        lane_via("vss", yn1)

    # ---------- 레인 + 핀 끝 늘림 ----------
    ybot, ytop = 0.0, gsnap(yp1 + 0.69)          # 셀 위·아래 끝 (hvi 와 같게)
    SPAN = {n: [min(v) - 0.18, max(v) + 0.18] for n, v in TOUCH.items()}
    for n in ports:
        if n in rails:
            continue
        if n not in SPAN:
            raise RuntimeError(f"{name}: 핀 {n} 레인이 없음")
        e = exits.get(n)
        if e in ("top", "both"):
            SPAN[n][1] = ytop
        if e in ("bot", "both"):
            SPAN[n][0] = ybot
    for n, (a, b) in SPAN.items():
        C.box(n, "m2", LANE[n] - W_LANE / 2, a, LANE[n] + W_LANE / 2, b)
    clash = []
    ks = list(SPAN)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            n1, n2 = ks[i], ks[j]
            if abs(LANE[n1] - LANE[n2]) < 0.59 and not (SPAN[n1][1] + 0.20 <= SPAN[n2][0] or SPAN[n2][1] + 0.20 <= SPAN[n1][0]):
                clash.append((n1, n2))
    assert not clash, f"{name}: 레인 겹침 {clash}"
    if label:
        for n in ports:
            if n in rails:
                continue
            C.label(n, "lbl_m2", LANE[n], (SPAN[n][0] + SPAN[n][1]) / 2)
        C.label("vdd", "lbl_m1", 0.0, yp1)
        C.label("vss", "lbl_m1", 0.0, BANDS["NBAND0"])
    r = pya.Region()
    for li in ly.layer_indexes():
        r.insert(C.c.begin_shapes_rec(li))
    C.c.shapes(C.li["hvi"]).insert(pya.Box(C.um(-XE - 0.41), C.um(ybot + 0.065), C.um(XE + 0.41), C.um(ytop)))
    bad = C.shorts()
    assert not bad, f"{name}: 단락 {bad}"
    # ---------- 핑거 합 ↔ CDL ----------
    for dv, fs in FING.items():
        W = round(sum(f[0] for f in fs), 3); L = fs[0][1]
        assert dv in cdldev, f"{name}: CDL 에 없는 소자 {dv}"
        assert abs(W - cdldev[dv][2]) < 1e-6 and abs(L - cdldev[dv][3]) < 1e-6, (name, dv, W, L, cdldev[dv])
    assert set(FING) == set(cdldev), set(cdldev) ^ set(FING)
    cdl = [f".subckt {name} " + " ".join(ports)]
    for dv, (conn, t, W, L) in cdldev.items():
        b = "vss" if t == "n" else "vdd"
        cdl.append(f"M{dv} {conn} {b} {MOD[t]} w={W:g}u l={L:g}u")
    cdl.append(f".ends {name}")
    pins = {n: dict(x=LANE[n], y0=round(SPAN[n][0], 3), y1=round(SPAN[n][1], 3)) for n in SPAN if n in ports}
    info = dict(name=name, XE=XE, ybot=ybot, ytop=ytop, bands=BANDS, lanes=LANE, pins=pins, rows=ROWINFO,
                spans={n: [round(a, 3), round(b, 3)] for n, (a, b) in SPAN.items()}, cdl=cdl,
                nat=dict(NBAND1=gsnap(BANDS["NBAND1"]), PBAND1_minus_PBAND0=None))
    return C, info

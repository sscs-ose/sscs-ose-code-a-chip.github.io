"""weight update 회로 부품 정의 (SPICE subckt 줄) — gen_wu_block.py (블록 시험) 와 gen_sys_deck.py (어레이 연결) 가 같이 쓴다.

Oh 2023 Fig. 3a / 학위 발표 2023-12-11 14장 구성:
  COMP1·COMP2 = StrongARM + inverter 분리 + SR NOR latch, A1–A4 = HOG + 저항 4개 차동 증폭기 (이득 1),
  COMP3 = HOG 개방 루프 (학위대로) 또는 StrongARM, latch = dynamic D latch.
"""
NF, PF = 'sky130_fd_pr__nfet_g5v0d10v5', 'sky130_fd_pr__pfet_g5v0d10v5'


def primitives():
    """TG, INV, NAND2, NOR2, SA (StrongARM), DLATCH."""
    return [
        ".subckt TG a b en enb vdd vss", f"XN a en b vss {NF} w=2 l=0.5", f"XP a enb b vdd {PF} w=4 l=0.5", ".ends",
        ".subckt INV a y vdd vss", f"XN y a vss vss {NF} w=1 l=0.5", f"XP y a vdd vdd {PF} w=2 l=0.5", ".ends",
        ".subckt NAND2 a b y vdd vss", f"XP1 y a vdd vdd {PF} w=2 l=0.5", f"XP2 y b vdd vdd {PF} w=2 l=0.5",
        f"XN1 y a n1 vss {NF} w=2 l=0.5", f"XN2 n1 b vss vss {NF} w=2 l=0.5", ".ends",
        ".subckt NOR2 a b y vdd vss", f"XP1 m a vdd vdd {PF} w=4 l=0.5", f"XP2 y b m vdd {PF} w=4 l=0.5",
        f"XN1 y a vss vss {NF} w=1 l=0.5", f"XN2 y b vss vss {NF} w=1 l=0.5", ".ends",
        # StrongARM (clk 낮음 = reset, 높음 = 평가) → inverter 로 분리 → SR NOR latch. inp > inn 이면 xo 가 내려가 q = 1
        # (10/25 1차판은 xo·yo 를 NAND latch 에 바로 연결 → latch 상태에 따라 두 출력 부하가 달라 늘 같은 쪽이 이김, dbg_sa)
        # 크기 (10/25 2차): tail 작게·입력쌍 L 1 µm → 적분 시간 늘림 (1차 w8/l0.5 는 p·n 이 0.2 ns 에 다 빠짐)
        ".subckt SA inp inn clk q qb vdd vss",
        f"XMt tl clk vss vss {NF} w=1 l=1", f"XM1 p inp tl vss {NF} w=4 l=1", f"XM2 n inn tl vss {NF} w=4 l=1",
        f"XM3 xo yo p vss {NF} w=2 l=0.5", f"XM4 yo xo n vss {NF} w=2 l=0.5",
        f"XM5 xo yo vdd vdd {PF} w=4 l=0.5", f"XM6 yo xo vdd vdd {PF} w=4 l=0.5",
        f"XS1 xo clk vdd vdd {PF} w=1 l=0.5", f"XS2 yo clk vdd vdd {PF} w=1 l=0.5",
        f"XS3 p clk vdd vdd {PF} w=1 l=0.5", f"XS4 n clk vdd vdd {PF} w=1 l=0.5",
        "XB1 xo xb vdd vss INV", "XB2 yo yb vdd vss INV",
        "XL1 yb qb q vdd vss NOR2", "XL2 xb q qb vdd vss NOR2", ".ends",
        # COMP3 앞 전치 증폭기 (10/25): NMOS 차동쌍 + PMOS 다이오드 부하 (이득 약 3), tail = HOG vbn 단위 4 개 (약 20 µA).
        # StrongARM kickback 이 abs_f·abs_n (TG 를 거친 HOG 출력, ns 에서 사실상 뜬 노드) 으로 넘어가지 않게 게이트로 막는다.
        # inp 가 높으면 on 이 내려가고 op 가 올라감 → SA(inp = op, inn = on) 이 q = 1.
        ".subckt PRE inp inn op on vbn vdd vss", f"XMt tl vbn vss vss {NF} w=3.6 l=1 nf=4",
        f"XM1 on inp tl vss {NF} w=4 l=1", f"XM2 op inn tl vss {NF} w=4 l=1",
        f"XL1 on on vdd vdd {PF} w=1 l=1", f"XL2 op op vdd vdd {PF} w=1 l=1", ".ends",
        # dynamic D latch: clk 높음 = 투명, 낮음 = 게이트 C 에 유지
        ".subckt DLATCH d clk clkb q qb vdd vss", "XT d s clk clkb vdd vss TG", "XI1 s qb vdd vss INV", "XI2 qb q vdd vss INV", ".ends"]


def diff_amp(k, vp, vm, ctl, ctlb, out, r_diff, cf, gain=1.0):
    """A_k = gain·(V(vp) − V(vm)), 입력 TG 2개 + 출력 TG 1개를 ctl 로 켬 (학위 그림은 gain 1).
    귀환 C 는 cf/gain (귀환 극점 R4·Cf 를 gain 과 무관하게)."""
    R = r_diff
    return [f"XTi{k}p {vp} a{k}x {ctl} {ctlb} vdd vss TG", f"XTi{k}m {vm} a{k}y {ctl} {ctlb} vdd vss TG",
            f"Ra{k}1 a{k}x a{k}p {R:g}", f"Ra{k}2 a{k}p 0 {gain * R:g}", f"Ra{k}3 a{k}y a{k}m {R:g}", f"Ra{k}4 a{k}m a{k}o {gain * R:g}",
            f"Ca{k}f a{k}m a{k}o {cf / gain:g}",
            f"XA{k} a{k}p a{k}m a{k}o vbn vbp vbnc vbpc vdd vss SKY130_OTA_HOG_TR",
            f"XTo{k} a{k}o {out} {ctl} {ctlb} vdd vss TG"]


def wu_core(r_diff, cf, comp3, c_abs=20e-15, gain=1.0):
    """fp·fm (free 셀 행·열), np·nm (nudge 셀) 노드에서 시작하는 회로 몸체 (subckt 안·밖 어디서나 쓰는 줄).
    c_abs: COMP3 입력 노드 (abs_f·abs_n) C. 20 fF 면 StrongARM 평가 순간 kickback 이 135 mV 라 δ 250 µV 판정이
    시간 간격에 따라 바뀐다 (dbg_sys_x1, 10/25) → 전체 덱은 1 pF."""
    L = ["XC1 fp fm ck q1 q1b vdd vss SA", "XC2 np nm ck q2 q2b vdd vss SA"]
    L += diff_amp(1, 'fp', 'fm', 'q1', 'q1b', 'absf', r_diff, cf, gain) + diff_amp(2, 'fm', 'fp', 'q1b', 'q1', 'absf', r_diff, cf, gain)
    L += diff_amp(3, 'np', 'nm', 'q2', 'q2b', 'absn', r_diff, cf, gain) + diff_amp(4, 'nm', 'np', 'q2b', 'q2', 'absn', r_diff, cf, gain)
    L += [f"Cabsf absf 0 {c_abs:g}", f"Cabsn absn 0 {c_abs:g}", "Rabsf absf 0 1e12", "Rabsn absn 0 1e12"]
    if comp3 == 'hog':
        L += ["XC3 absf absn sen vbn vbp vbnc vbpc vdd vss SKY130_OTA_HOG_TR"]
    elif comp3 == 'sa':
        L += ["XC3 absf absn ck3 sen senb vdd vss SA"]
    else:                                                     # 'pa_sa': 전치 증폭기 + StrongARM
        L += ["XP3 absf absn pa3p pa3n vbn vdd vss PRE", "XC3 pa3p pa3n ck3 sen senb vdd vss SA"]
    L += ["XLAT sen lat latb lq lqb vdd vss DLATCH"]
    return L


def wu_subckt(r_diff, cf, comp3, c_abs=20e-15, gain=1.0):
    """WU fp fm np nm ck ck3 lat latb lq sen absf absn q1 q2 vbn vbp vbnc vbpc vdd vss"""
    return ([".subckt WU fp fm np nm ck ck3 lat latb lq sen absf absn q1 q2 vbn vbp vbnc vbpc vdd vss"]
            + wu_core(r_diff, cf, comp3, c_abs, gain) + [".ends WU"])

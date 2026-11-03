"""칩 제어 부품 (SPICE subckt 줄) — README §13 (10/25): 큰 동작 3 개 (FORM / WRITE / READ), 줄마다 MUX, 레지스터 5 개.
v2 (10/25 밤, §13 갱신): 1T1R 쓰기 — SET·RESET 은 같은 연결, 쓰기 펄스 극성만 밖에서 (V_W 버스 하나), V/2 없음.
  선택 행 → V_W, 선택 열 → 0 V, 선택 안 된 열 → V_W, 선택 안 된 행 → 0 V, WL: READ = VDD, 쓰기 = 선택 행만 V_WL, verify = 선택 행만 VDD,
  나머지 WL = VSS (−2.5 V, RESET 때 열이 −V_W 로 내려가도 nFET 이 꺼져 있게).
  칩 안 디지털 전체 = VSS–VDD (±2.5 V, 10/25 사용자 "트랜스미션 게이트도 그 큰 전압으로 동작하는 vdd vss") → 게이트 −2.5 / +2.5 V.
  쓰기 펄스: WP (타이밍) → XNOR(WP, POL) → inverter 체인 → 마지막 단 전원 = 패드 V_WH / V_WL (크기·극성) → V_W 버스.
gen_chip_deck.py·chip_digtest.py 가 쓴다. wu_lib.primitives() 의 TG·INV·NAND2·NOR2·DLATCH 를 쓴다 (전원 포트에 vdd vss 를 준다).
v1 (디지털 0 / VDD, V/2) 은 chip_read0 덱이 쓴 판.
v3 (10/26 핀 줄이기): 아래 CFG·config_block (설정 레지스터 12 bit, 레지스터 다섯 개 SCK·SDI 공유), beta_mirror (β = HOG bias 미러) 를 더함.
  v2b 부품은 그대로. gen_chip_deck2.py·chip_digtest3.py 가 쓴다.
"""
NF, PF = 'sky130_fd_pr__nfet_g5v0d10v5', 'sky130_fd_pr__pfet_g5v0d10v5'

DFFR = [  # 양 모서리 DFF, rst 높음 = q 0 (비동기). 마스터 = clk 낮을 때 투명 (NAND 로 reset), 슬레이브 = clk 높을 때 (NOR 로 reset)
    ".subckt DFFR d clk rst rstb q vdd vss",
    "XI0 clk clkb vdd vss INV",
    "XT1 d m clkb clk vdd vss TG", "XN1 m rstb mb vdd vss NAND2", "XI1 mb mf vdd vss INV", "XT2 mf m clk clkb vdd vss TG",
    "XT3 mb s clk clkb vdd vss TG", "XR1 s rst q vdd vss NOR2", "XI2 q sf vdd vss INV", "XT4 sf s clkb clk vdd vss TG",
    ".ends DFFR"]

TGW = [  # 쓰기 전류가 지나는 넓은 TG (셀 전류 ≈ 200 µA 에서 수십 mV)
    ".subckt TGW a b en enb vdd vss", f"XN a en b vss {NF} w=20 l=0.5 nf=4", f"XP a enb b vdd {PF} w=40 l=0.5 nf=8", ".ends TGW"]


def and2(a, b, y, yb, k):
    """y = a·b, yb = 그 반대 (NAND2 + INV)."""
    return [f"XNa{k} {a} {b} {yb} vdd vss NAND2", f"XIa{k} {yb} {y} vdd vss INV"]


# 행 하나의 decoder: t = token bit, 전역 PROG (FORM + WRITE-program), VER, SENSE, READb, WRANY (= PROG + VER)
#   wsel: V_W (선택, 쓰기·verify) · wz: 0 V (선택 안 됨, 쓰기·verify) · sns: sense
#   WL: wlv = VDD (READ 또는 선택 verify) · wlw = V_WL (선택, 쓰기) · wl0 = VSS (그 밖)
ROWL = (  # v2b: verify 도 쓰기와 같은 연결 (선택 행 → V_W 버스, 밖에서 V_W = V_RD) → vrd 출력 없음
    [".subckt ROWL t sel_en PROG VER SENSE READb WRANY wsel wselb wz wzb sns snsb wlv wlvb wlw wlwb wl0 wl0b vdd vss"]
    + and2('t', 'sel_en', 's', 'sb', 's')
    + and2('WRANY', 's', 'wsel', 'wselb', 'ws')
    + and2('WRANY', 'sb', 'wz', 'wzb', 'wz')
    + and2('SENSE', 's', 'sns', 'snsb', 'sn')
    + ["XNvs VER s vsb vdd vss NAND2", "XNlv READb vsb wlv vdd vss NAND2", "XIlv wlv wlvb vdd vss INV"]   # WL VDD: READ + 선택 verify
    + and2('PROG', 's', 'wlw', 'wlwb', 'lw')                                                            # WL V_WL: 선택 쓰기
    + ["XRl0 wlv wlw wl0 vdd vss NOR2", "XIl0 wl0 wl0b vdd vss INV", ".ends ROWL"])

# 열 하나의 decoder: t1 = COL1 bit (감지 → C1, 쓰기·verify 선택), t2 = COL2 bit (감지 → C2)
#   wvw: V_W (선택 안 됨, 쓰기·verify = 억제) · wz: 0 V (선택, 쓰기) · vfy: verify 버스 (선택 verify) · sense C1·C2
#   (SPICE 는 대소문자를 가리지 않아 전역 입력 VER 와 출력 이름이 겹치면 안 된다)
COLL = (
    [".subckt COLL t1 t2 sel_en PROG VER SENSE WRANY wvw wvwb wz wzb vfy vfyb sns1 sns1b sns2 sns2b vdd vss"]
    + and2('t1', 'sel_en', 's', 'sb', 's') + and2('t2', 'sel_en', 's2', 's2b', 's2')
    + and2('WRANY', 'sb', 'wvw', 'wvwb', 'wv')                     # v2b: verify 때도 선택 안 된 열 = V_W 버스 (= V_RD)
    + and2('PROG', 's', 'wz', 'wzb', 'wz')
    + and2('VER', 's', 'vfy', 'vfyb', 'vr')
    + and2('SENSE', 's', 'sns1', 'sns1b', 'n1') + and2('SENSE', 's2', 'sns2', 'sns2b', 'n2')
    + [".ends COLL"])

# 행 한 줄의 MUX (배열마다). 읽기 구동 (NMOS 2:1, bias 스위치) 은 덱에서 따로. V_W 쪽은 넓은 TG (선택 셀 전류)
ROWM = [
    ".subckt ROWM row wl bus vw vwl wsel wselb wz wzb sns snsb wlv wlvb wlw wlwb wl0 wl0b vdd vss",
    "XT1 vw row wsel wselb vdd vss TGW", "XT3 0 row wz wzb vdd vss TG", "XT5 row bus sns snsb vdd vss TG",
    "XW1 vdd wl wlv wlvb vdd vss TG", "XW2 vwl wl wlw wlwb vdd vss TG", "XW3 vss wl wl0 wl0b vdd vss TG",
    ".ends ROWM"]

# 열 한 줄의 MUX (배열마다). 0 V 쪽은 넓은 TG (선택 셀 전류)
COLM = [
    ".subckt COLM col vw vbus c1 c2 wvw wvwb wz wzb vfy vfyb sns1 sns1b sns2 sns2b vdd vss",
    "XT1 0 col wz wzb vdd vss TGW", "XT2 vw col wvw wvwb vdd vss TG",
    "XT4 col vbus vfy vfyb vdd vss TG", "XT5 col c1 sns1 sns1b vdd vss TG", "XT6 col c2 sns2 sns2b vdd vss TG",
    ".ends COLM"]

# 쓰기 펄스 buffer: f = XNOR(WP, POL) (SET: f = WP 반대, RESET: f = WP) → INV 2 단 (×4, ×16) → 마지막 단 (vwh / vwl 전원)
#   SET (vwl 0, vwh +V): 쉴 때 f 높음 → 0 V, 펄스 때 f 낮음 → +V.  RESET (vwl −V, vwh 0): 쉴 때 f 낮음 → 0 V, 펄스 때 f 높음 → −V
WBUF = [
    ".subckt WBUF wp pol out vwh vwl vdd vss",
    "XN1 wp pol n1 vdd vss NAND2", "XN2 wp n1 n2 vdd vss NAND2", "XN3 pol n1 n3 vdd vss NAND2", "XN4 n2 n3 xr vdd vss NAND2",
    "XI0 xr f0 vdd vss INV",                                            # f0 = XNOR
    f"XP1 f1 f0 vdd vdd {PF} w=8 l=0.5 nf=2", f"XM1 f1 f0 vss vss {NF} w=4 l=0.5",
    f"XP2 f2 f1 vdd vdd {PF} w=32 l=0.5 nf=8", f"XM2 f2 f1 vss vss {NF} w=16 l=0.5 nf=4",
    f"XPo out f2 vwh vdd {PF} w=400 l=0.5 nf=80", f"XMo out f2 vwl vss {NF} w=200 l=0.5 nf=40",
    ".ends WBUF"]


def lib():
    return DFFR + TGW + ROWL + COLL + ROWM + COLM + WBUF + CKBUF


def global_decode():
    """패드 신호 (레벨 변환 뒤 ±2.5 V) m1 m0 pv wu_en rst → 전역 신호. MODE: 00 IDLE, 01 FORM, 10 WRITE, 11 READ."""
    L = ["XIm1 m1 m1b vdd vss INV", "XIm0 m0 m0b vdd vss INV", "XIpv pv pvb vdd vss INV", "XIrs rst rstb vdd vss INV"]
    L += and2('m1', 'm0', 'READ', 'READb', 'rd')
    L += and2('m1', 'm0b', 'WRm', 'WRmb', 'wr')
    L += and2('m1b', 'm0', 'FORM', 'FORMb', 'fm')
    L += and2('WRm', 'pvb', 'WRP', 'WRPb', 'wp')
    L += ["XNpg FORMb WRPb PROG vdd vss NAND2", "XIpg PROG PROGb vdd vss INV"]         # FORM + WRITE-program
    L += and2('WRm', 'pv', 'VER', 'VERb', 've')
    L += ["XNwa PROGb VERb WRANY vdd vss NAND2"]                                     # PROG + VER
    L += and2('READ', 'wu_en', 'SENSE', 'SENSEb', 'se')
    return L


# ── v3 (10/26 핀 줄이기, README §13): 설정 레지스터 12 bit + 레지스터 다섯 개가 SCK·SDI 하나를 같이 씀
#   SLD 높음: SCK 가 설정 레지스터를 민다 (그동안 latch 는 닫혀 이전 설정 유지). SLD 낮음: latch 투명 → 설정 적용,
#   SCK 는 TSEL 이 고른 레지스터만 민다 ({reg}_clk = SCK·SLD̄·TSEL_reg). 레지스터 입력은 모두 SDI.
#   SLD·TSEL 은 SCK 가 낮을 때만 바꾼다 (클록 gating 글리치 없음). RST = 모든 DFF 0 → 설정 0 = IDLE.
CFG = ['m1', 'm0', 'pv', 'pol', 'wu_en', 'rd_out', 'dload', 'ts_data', 'ts_row1', 'ts_row2', 'ts_col1', 'ts_col2']
REGS = ['data', 'row1', 'row2', 'col1', 'col2']


CKBUF = [  # 클록 buffer: y = a (INV 4 단, 폭 1 → 4 → 16 → 64). 레지스터 하나 (DFF 52–100 개, 클록 게이트 폭 약 15 µm × 개수) 를 구동
    ".subckt CKBUF a y vdd vss", "XI1 a y1 vdd vss INV",
    f"XP2 y2 y1 vdd vdd {PF} w=8 l=0.5 nf=2", f"XN2 y2 y1 vss vss {NF} w=4 l=0.5",
    f"XP3 y3 y2 vdd vdd {PF} w=32 l=0.5 nf=8", f"XN3 y3 y2 vss vss {NF} w=16 l=0.5 nf=4",
    f"XP4 y y3 vdd vdd {PF} w=128 l=0.5 nf=32", f"XN4 y y3 vss vss {NF} w=64 l=0.5 nf=16", ".ends CKBUF"]


def config_block(buf=True):
    """패드 sck sdi sld (rstb 는 global_decode) → 설정 출력 노드 CFG[k] 와 그 반대 CFG[k]_b, 레지스터 클록 <reg>_clk.
    설정 bit k 는 마지막에서 k 번째로 넣은 bit (먼저 넣은 bit 가 끝 = cq11 = ts_col2).
    buf: 레지스터 클록마다 CKBUF (10/26 chip_write2 첫 판: 최소 크기 and2 가 DFF 52–100 개를 직접 구동 → token 이 안 들어감)."""
    L = ["XIsld sld sldb vdd vss INV"] + and2('sck', 'sld', 'cfg_clk', 'cfg_clkb', 'cc') + and2('sck', 'sldb', 'sck_r', 'sck_rb', 'cr')
    prev = 'sdi'
    for k, n in enumerate(CFG):
        L += [f"XFc{k} {prev} cfg_clk rst rstb cq{k} vdd vss DFFR", f"XLc{k} cq{k} sldb sld {n} {n}_b vdd vss DLATCH"]
        prev = f'cq{k}'
    for r in REGS:
        if buf:
            L += and2('sck_r', f'ts_{r}', f'{r}_ck0', f'{r}_ck0b', f'k{r}') + [f"XCB{r} {r}_ck0 {r}_clk vdd vss CKBUF"]
        else:
            L += and2('sck_r', f'ts_{r}', f'{r}_clk', f'{r}_clkb', f'k{r}')
    return L


def beta_mirror(m=8, kn=0.796, kp=0.882):
    """nudge 전류 β = HOG bias 기준 (Ibn·Ibp 5 µA, 패드 IBIAS 하나로 보는 것) 을 HOG 단위 소자 m 개로 미러. 주입기 기준 노드 pref·nref 를 만든다.
    pref: PMOS diode (주입기 MP 와 같은 크기) ← NMOS (vbn 미러, HOG XBN 0.9/1 폭 × kn, m 개) 가 β 를 끌어냄.
    nref: NMOS diode (주입기 MN 과 같은 크기) ← PMOS cascode (vbp·vbpc 미러, HOG XBP 2/0.8 · XBPC 1.5/0.5 폭 × kp, m 개) 가 β 를 넣음.
    크기는 beta_size.py (10/26) 로 골랐다: 주입기 (출력 0 V) 전류 = β 38.12 µA (±0.1 %). 한 소자를 W×7.624 로 키우면 W 구간 모형 차이로
    −19 / +20 %, 단위 소자 m=8 이면 PMOS 쪽 +1 % · NMOS 쪽 +10 % (Vds 3.7 V 대 기준 1.2 V) → kn·kp 로 맞춤. β 를 바꾸면 다시 고른다.
    전류계 Vbm_p·Vbm_n (0 V) 로 기준 가지 전류를 잰다."""
    return [f"XMPref pref pref vdd vdd {PF} w=42 l=2 nf=8", "Vbm_p pref pm_d 0", f"XMbn pm_d vbn vss vss {NF} w={0.9 * kn:.4f} l=1 m={m}",
            f"XMNref nref nref vss vss {NF} w=15 l=2 nf=3", "Vbm_n nm_d nref 0",
            f"XMbp bx vbp vdd vdd {PF} w={2 * kp:.4f} l=0.8 m={m}", f"XMbpc nm_d vbpc bx vdd {PF} w={1.5 * kp:.4f} l=0.5 m={m}"]

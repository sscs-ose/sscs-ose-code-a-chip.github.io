"""test pattern 소자 셀 (10/28) — 단일 1T1R, 접근 nFET 단독, 짝 소자 (5 V n·p 쌍).
사용자 요청: "test pattern 넣어서 decap이 최대한 없게", "그려만 놓고 pad 연결은 안해놓아도 되지 뭐".

  tp_1t1r : 배열 셀 c1t1r_w3 (layout/gen_arr_1t1r_w3.py, 128 × 64 배열 DRC·LVS MATCH 잡 721085) 의 도형을 그대로 옮긴 단일 1T1R.
            접근 nFET nfet_g5v0d10v5 W 3 (핑거 2 × 1.5, drain 공유) L 0.5 + RRAM (via1 + 230/20 표지, LVS = R(reram) met2 → met1).
            단자 te (RRAM 윗전극 = 배열의 행, met2 riser), wl (게이트), s (source = 배열의 열), 기판 = VSS.
  tp_nacc : 같은 도형에서 RRAM 표지만 뺀 것 → via1 이 그냥 이음 → 접근 nFET 단독 (단자 d, g, s).
  tp_pair : rowcell 엔진 (rowcell_tp.py = blk_wu/rowcell.py 사본, WU 비교기에서 DRC·LVS 깨끗) 으로 그린 짝 소자.
            n 쌍 (N1·N2) · p 쌍 (P1·P2) 각 W 4 / L 1 (핑거 2 × 2.0), ABBA 섞어 놓기, source 공유.
            단자 nd1 nd2 ng1 ng2 ns pd1 pd2 pg1 pg2 ps, 몸통 n = VSS, p = VDD (n-well 탭).
약속은 tpcommon.py (서쪽 met3 신호 패드, 동쪽 met3 전원 패드, 셀 안 라벨 없음).
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python s_dev.py   (단독 시험 tp_dev_t → Olympus DRC·LVS)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpcommon import Struct, g, db, write_standalone, run          # noqa: E402
import rowcell_tp as RC                                             # noqa: E402


# ── 1T1R 셀 도형 (nm, 배열 셀 원점) — gen_arr_1t1r_w3.py 의 셀 부분을 줄마다 그대로 옮김
def _c1t1r_shapes(rram=True):
    S = []
    b = lambda k, x0, y0, x1, y1: S.append((k, x0, y0, x1, y1))
    G1, G2 = (445, 945), (1235, 1735)
    b('diff', 180, 180, 2000, 1680); b('nsdm', 55, 55, 2125, 1805); b('hvi', 0, -780, 2180, 1860)
    for g0, g1 in (G1, G2):
        b('poly', g0, 50, g1, 1810)
    b('poly', G1[0], 1810, G2[1], 1960)
    b('poly', 525, 1855, 855, 2185); b('npc', 505, 1835, 875, 2205)
    b('licon', 605, 1935, 775, 2105); b('li1', 525, 1855, 855, 2185); b('mcon', 605, 1935, 775, 2105)
    b('met1', 530, 1860, 850, 2180); b('via1', 615, 1945, 765, 2095); b('met2', 505, 1820, 875, 2470)
    YS = ((240, 410), (580, 750), (920, 1090), (1260, 1430))
    for x0, x1, ym in ((220, 390, (405, 575)), (1005, 1175, (1205, 1375)), (1790, 1960, (405, 575))):
        for y0, y1 in YS:
            b('licon', x0, y0, x1, y1)
        b('li1', x0, 160, x1, 1510); b('mcon', x0, ym[0], x1, ym[1])
    b('met1', -460, 345, 2020, 635)                 # 두 source → VS 패드
    b('met1', 945, 1145, 2665, 1435)                # drain → RRAM BE
    b('met1', 2345, 1160, 2665, 1420)               # BE 패드
    b('via1', 2430, 1215, 2580, 1365)
    if rram:
        b('reram', 2380, 1165, 2630, 1415)          # RRAM 표지 (via1 + 230/20)
    b('met2', 2375, 1130, 2635, 1450)               # TE
    b('met2', 2345, -620, 2665, 1300)               # riser
    b('tap', 180, -600, 2000, -190); b('psdm', 55, -725, 2125, 35)
    for x0 in (415, 890, 1365, 1790):
        b('licon', x0, -480, x0 + 170, -310)
    b('li1', 270, -480, 2105, -310)
    for x0 in (350, 830, 1310, 1790):
        b('mcon', x0, -480, x0 + 170, -310)
    b('met1', 180, -940, 2000, -190)                # GND (body)
    return S


def build_1t1r(ly, name, rram=True):
    """단일 1T1R (rram=True) 또는 접근 nFET 단독 (rram=False). 셀 원점 (0.0) 을 (OX, OY) 에."""
    OX, OY = 5.0, 2.5
    p = ('te', 'wl', 's') if rram else ('d', 'g', 's')
    s = Struct(ly, name, contents=('단일 1T1R: nfet_g5v0d10v5 W 3 (2 × 1.5) / L 0.5 + RRAM (배열 셀 c1t1r_w3 와 같은 도형)' if rram
                                   else '접근 nFET 단독: nfet_g5v0d10v5 W 3 (2 × 1.5) / L 0.5 (1T1R 셀에서 RRAM 표지만 뺌)'),
               source='layout/gen_arr_1t1r_w3.py 셀 도형 그대로')
    for k, x0, y0, x1, y1 in _c1t1r_shapes(rram):
        s.box(k, OX + x0 / 1000, OY + y0 / 1000, OX + x1 / 1000, OY + y1 / 1000)
    # source: VS 막대 (met1, y 2.845–3.135) 를 서쪽으로 늘려 via 쌓기 → met3 → 서쪽 패드
    ys = OY + 0.49
    s.box('met1', 3.2, OY + 0.345, OX - 0.46, OY + 0.635)
    s.via(3.45, ys, 'met1', 'met3')
    s.box('met3', 0.0, ys - 0.25, 3.70, ys + 0.25)
    s.sig_pin(p[2], ys)
    # drain / TE: riser (met2, x 7.345–7.665) 를 아래로 → via2 → met3 → 서쪽 패드
    xr, yt = OX + 2.505, 0.8
    s.box('met2', OX + 2.345, yt - 0.185, OX + 2.665, OY - 0.62)
    s.via(xr, yt, 'met2', 'met3')
    s.box('met3', 0.0, yt - 0.25, xr + 0.25, yt + 0.25)
    s.sig_pin(p[0], yt)
    # gate / WL: 게이트 met2 패드 (x 5.505–5.875, 위 끝 4.97) 를 위로 → via2 → met3 → 서쪽 패드
    xg, yg = OX + 0.69, 6.2
    s.box('met2', OX + 0.505, OY + 2.47 - 0.1, OX + 0.875, yg + 0.185)
    s.via(xg, yg, 'met2', 'met3')
    s.box('met3', 0.0, yg - 0.25, xg + 0.25, yg + 0.25)
    s.sig_pin(p[1], yg)
    # body: GND (met1, y 1.56–2.31) → via 쌓기 → met3 → 동쪽 VSS 패드
    xv, yv, XE = OX + 1.2, OY - 0.565, 9.5
    s.via(xv, yv, 'met1', 'met3')
    s.box('met3', xv - 0.25, yv - 0.25, XE, yv + 0.25)
    s.pwr_pin('VSS', XE, yv)
    if rram:
        s.cdl = ['R0 te dn $[reram]',
                 'M1 dn wl s VSS nfet_g5v0d10v5 w=1.5u l=0.5u', 'M2 dn wl s VSS nfet_g5v0d10v5 w=1.5u l=0.5u']
    else:
        s.cdl = ['M1 d g s VSS nfet_g5v0d10v5 w=1.5u l=0.5u', 'M2 d g s VSS nfet_g5v0d10v5 w=1.5u l=0.5u']
    return s.check()


# ── 짝 소자 (rowcell)
PAIR_W, PAIR_L, PAIR_WF = 4.0, 1.0, 2.0


def build_pair(ly, name='tp_pair', W=PAIR_W, L=PAIR_L, Wf=PAIR_WF):
    nf = int(round(W / Wf))
    assert nf == 2, '이 판은 ABBA (소자마다 핑거 2) 만'
    rows = [('n', 'n', [RC.isl(L, Wf, ['nd1', 'ns', 'nd2', 'ns', 'nd1'], ['ng1', 'ng2', 'ng2', 'ng1'], ['N1', 'N2', 'N2', 'N1'])], {'ns'}, None),
            ('p', 'p', [RC.isl(L, Wf, ['pd1', 'ps', 'pd2', 'ps', 'pd1'], ['pg1', 'pg2', 'pg2', 'pg1'], ['P1', 'P2', 'P2', 'P1'])], {'ps'}, None)]
    dev = {'N1': ('nd1 ng1 ns', 'n', W, L), 'N2': ('nd2 ng2 ns', 'n', W, L),
           'P1': ('pd1 pg1 ps', 'p', W, L), 'P2': ('pd2 pg2 ps', 'p', W, L)}
    nsig = ['nd1', 'nd2', 'ng1', 'ng2', 'ns']
    psig = ['pd1', 'pd2', 'pg1', 'pg2', 'ps']
    exits = {**{n: 'bot' for n in nsig}, **{n: 'top' for n in psig}}
    XE = 4.5
    rc, info = RC.build(ly, name + '_rc', XE, rows, dev, nsig + psig + ['vdd', 'vss'], exits=exits, label=False)
    s = Struct(ly, name, contents=f'짝 소자: nfet·pfet_g5v0d10v5 쌍 W {W:g} / L {L:g} (핑거 2 × {Wf:g}, ABBA, source 공유)',
               source='rowcell_tp.py (blk_wu/rowcell.py 사본)')
    TR = 1.0                                                       # 신호 줄 간격 (met3)
    ox = g(XE + 3.0)                                               # rowcell 중심 x
    oy = g(len(nsig) * TR + 1.0)                                   # rowcell 아래 끝 y
    s.inst(rc.c, ox, oy)
    ytop = oy + info['ytop']
    pins = info['pins']
    # 아래로 나가는 n 넷: 레인 met2 를 줄 y 까지 늘려 via2 → met3 → 서쪽
    for k, n in enumerate(sorted(nsig, key=lambda n: pins[n]['x'])):
        x, yk = ox + pins[n]['x'], g(0.5 + k * TR)
        s.box('met2', x - 0.14, yk - 0.185, x + 0.14, oy + 0.3)
        s.via(x, yk, 'met2', 'met3')
        s.box('met3', 0.0, yk - 0.25, x + 0.25, yk + 0.25)
        s.sig_pin(n, yk)
    for k, n in enumerate(sorted(psig, key=lambda n: pins[n]['x'])):
        x, yk = ox + pins[n]['x'], g(ytop + 1.0 + k * TR)
        s.box('met2', x - 0.14, ytop - 0.3, x + 0.14, yk + 0.185)
        s.via(x, yk, 'met2', 'met3')
        s.box('met3', 0.0, yk - 0.25, x + 0.25, yk + 0.25)
        s.sig_pin(n, yk)
    # 전원: 오른쪽 경계 세로 탭 (met1, x XE−0.34…XE) 위 띠 높이에서 via 쌓기 → met3 → 동쪽 패드
    xe = g(ox + XE + 2.0)
    xt = g(ox + XE - 0.17)
    for net, band in (('VSS', 'NBAND0'), ('VDD', 'PBAND1')):
        yb = g(oy + info['bands'][band])
        s.via(xt, yb, 'met1', 'met3')
        s.box('met3', xt - 0.25, yb - 0.25, xe, yb + 0.25)
        s.pwr_pin(net, xe, yb)
    body = []
    for ln in info['cdl'][1:-1]:
        t = ln.split()
        t[4] = {'vss': 'VSS', 'vdd': 'VDD'}[t[4]]
        body.append(' '.join(t))
    s.cdl = body
    return s.check()


def build(ly):
    return [build_1t1r(ly, 'tp_1t1r', True), build_1t1r(ly, 'tp_nacc', False), build_pair(ly)]


if __name__ == '__main__':
    ly = db.Layout(); ly.dbu = 0.001
    S = build(ly)
    for s in S:
        print(s.name, s.bbox(), s.ports)
    write_standalone(ly, S, 'tp_dev_t')
    run('tp_dev_t')

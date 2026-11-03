#!/usr/bin/env python3
"""5 V transmission gate 셀 (쓰기 구동·선택 스위치 공통 부품).
  nfet W (게이트 ctl, body VSS) + pfet 2W (게이트 ctlb, body VDD), 둘 다 a ↔ b.
  아래부터: p-tap(VSS) → nfet → nwell[pfet → n-tap(VDD)].  a·b 는 met2 세로 레인, 게이트는 met1 패드.
사용: WN=10 WMAX=4.6 NAME=tg_w10 python gen_tg.py   (WMAX = 셀 안 소자 폭 한도, 열 피치에 맞춤)
라이브러리로: build(C, x0, y0, wn, wmax, nets) → 셀 안 좌표 정보"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klayout.db as pya
from devlib import Cell, mos, plan, gate_pad, tap, finish, cdl_mos, P1

L5 = 0.5


def build(C, x0, y0, wn, wmax, nets=None, nw_x=None, nf_max=None, rail_x=None):
    """(x0, y0) 왼쪽 아래에 TG 하나. nets = dict(a, b, ctl, ctlb, vdd, vss). nw_x = nwell 좌우 (셀 전폭 병합용).
    nf_max = 핑거 수 상한 (작은 W 는 핑거 폭이 너무 얇아지지 않게). rail_x = 탭 met1 을 이 범위로 늘림 (옆 셀과 이음)."""
    n = dict(a='a', b='b', ctl='ctl', ctlb='ctlb', vdd='VDD', vss='VSS'); n.update(nets or {})
    nfn, _ = plan(wn, L5, wmax); nfp, _ = plan(2 * wn, L5, wmax)
    if nf_max: nfn, nfp = min(nfn, nf_max), min(nfp, nf_max)
    tap(C, 'p', x0, x0 + wmax, y0 + 0.25, n['vss'])
    dn = mos(C, 'n', x0, y0 + 0.55, wn, L5, nfn, n['a'], n['b'], n['ctl'])
    nw0 = dn['y1'] + 0.30
    dp = mos(C, 'p', x0, nw0 + 0.10, 2 * wn, L5, nfp, n['a'], n['b'], n['ctlb'])
    yt = dp['y1'] + 0.25
    tap(C, 'n', x0, x0 + wmax, yt, n['vdd'])
    if rail_x:                                          # 탭 met1 을 셀 전폭으로 (옆 셀 탭과 맞닿음)
        C.box(n['vss'], 'm1', rail_x[0], y0, rail_x[1], y0 + 0.50)
        C.box(n['vdd'], 'm1', rail_x[0], yt - 0.25, rail_x[1], yt + 0.25)
    xl, xr = nw_x or (x0 - 0.40, x0 + max(dp['x1'] - x0, wmax) + 0.40)
    C.box(None, 'nw', xl, nw0, xr, yt + 0.60)
    # a: 두 소스 스트랩 → 왼쪽 레인, b: 두 드레인 스트랩 → 오른쪽 레인 (met2)
    xa = dn['srcs'][0]; xb = max(dn['drns'][-1], dp['drns'][-1])
    for dv in (dn, dp):
        C.via1(n['a'], xa, dv['ys'])
        C.box(n['b'], 'm1', dv['drns'][-1], dv['yd'] - 0.17, xb + P1 / 2, dv['yd'] + 0.17)
        C.via1(n['b'], xb, dv['yd'])
    C.box(n['a'], 'm2', xa - 0.15, y0 + 0.25, xa + 0.15, yt)
    C.box(n['b'], 'm2', xb - 0.15, y0 + 0.25, xb + 0.15, yt)
    gn = gate_pad(C, dn, dn['gxs'][len(dn['gxs']) // 2]); gp = gate_pad(C, dp, dp['gxs'][len(dp['gxs']) // 2])
    cdl = cdl_mos('n', n['b'], n['ctl'], n['a'], n['vss'], 'n', wn, L5, nfn) + \
          cdl_mos('p', n['b'], n['ctlb'], n['a'], n['vdd'], 'p', 2 * wn, L5, nfp)
    return dict(dn=dn, dp=dp, xa=xa, xb=xb, gn=gn, gp=gp, y1=yt + 0.60, ytap_p=y0 + 0.25, ytap_n=yt, cdl=cdl, nf=(nfn, nfp))


if __name__ == '__main__':
    wn = float(os.environ.get('WN', '10')); wmax = float(os.environ.get('WMAX', '4.6'))
    name = os.environ.get('NAME', f"tg_w{wn:g}")
    ly = pya.Layout(); ly.dbu = 0.001
    C = Cell(ly, name)
    r = build(C, 0.0, 0.0, wn, wmax)
    C.label('a', 'lbl_m2', r['xa'], 1.0); C.label('b', 'lbl_m2', r['xb'], 1.0)
    C.label('ctl', 'lbl_m1', *r['gn']); C.label('ctlb', 'lbl_m1', *r['gp'])
    C.label('VSS', 'lbl_m1', 0.3, 0.25); C.label('VDD', 'lbl_m1', 0.3, r['y1'] - 0.60)
    bb = finish(C)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blocks')
    os.makedirs(out, exist_ok=True)
    ly.write(os.path.join(out, name + '.gds'))
    open(os.path.join(out, name + '.cdl'), 'w').write(
        f".subckt {name} a b ctl ctlb VDD VSS\n" + "\n".join(r['cdl']) + f"\n.ends {name}\n")
    print(f"{name}: nf n/p = {r['nf']}, bbox {bb[2]-bb[0]:.3f} x {bb[3]-bb[1]:.3f} um, shorts {C.shorts() or 'none'}")

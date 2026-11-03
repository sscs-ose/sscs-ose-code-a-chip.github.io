#!/usr/bin/env python3
"""open_pdks Magic tech (sky130A.tech) 사본에 RRAM 소자를 더한다 — LVS 추출 전용 (DRC 는 원본 tech 로). Pegasus 쪽 make_lvs_1r.py 와 같은 뜻:
230/20 표시와 겹치는 via1 은 met1–met2 연결에서 빼고, 그 자리를 2 단자 소자 sky130_rram (TE = met2, BE = met1) 으로 뽑는다.
바꾸는 곳 6 군데 (모두 assert 로 원문 확인):
  ① types    : metal2 면에 새 type `rram`
  ② styles   : rram 표시 색 (metal3 + mems 무늬, 화면용)
  ③ connect  : rram ↔ *m2 (TE 쪽 net 은 그대로 이어짐)
  ④ cifinput : via1 (m2c) 만들 때 RRAMMK 를 뺌 + `layer rram RRAMMK and MET2` (m2 위에 덮어 칠함) + `calma RRAMMK 230 20`
  ⑤ extract  : `device csubcircuit sky130_rram rram metal1` — MiM cap (`*mimcap *m3`) 과 같은 세로 소자 방식 (윗판 = rram 타일 net, 아랫판 = 밑 met1)
쓰임: python make_magic_rram_tech.py <원본 sky130A.tech> <사본 .tech>   (옆에 같은 이름 .magicrc 도 씀)
"""
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
s = src.read_text()


def rep(a, b, count=1):
    global s
    n = s.count(a)
    assert n == count, (a, n)
    s = s.replace(a, b)


rep("  metal2 rmetal2,rm2,rmet2\n", "  metal2 rmetal2,rm2,rmet2\n  metal2 rram\n")                                  # ①
rep("  rm2       metal3         poly_resist_stripes\n",
    "  rm2       metal3         poly_resist_stripes\n  rram      metal3         mems\n")                                # ②
rep("  *m2,m2fill\t*m2,m2fill\n", "  *m2,m2fill\t*m2,m2fill\n  rram\t*m2,rram\n")                                     # ③
rep(" templayer m2cbase VIA1\n and-not COREID\n grow 5\n or VIA1\n grow 50\n",
    " templayer m2cbase VIA1\n and-not COREID\n grow 5\n or VIA1\n and-not RRAMMK\n grow 50\n")                         # ④ via1 에서 RRAM 뺌
rep(" layer m2 MET2,MET2TXT,MET2PIN\n and-not MET2RES,MET2SHORT\n labels MET2\n labels MET2PIN port\n labels MET2TXT text\n",
    " layer m2 MET2,MET2TXT,MET2PIN\n and-not MET2RES,MET2SHORT\n labels MET2\n labels MET2PIN port\n labels MET2TXT text\n\n"
    " layer rram RRAMMK\n and MET2\n")
rep(" calma VIA1 68 44\n", " calma VIA1 68 44\n calma RRAMMK 230 20\n")
rep(" device resistor sky130_fd_pr__res_generic_m2 rmetal2 *metal2\n",
    " device resistor sky130_fd_pr__res_generic_m2 rmetal2 *metal2\n device csubcircuit sky130_rram rram metal1\n", count=2)  # ⑤ 두 extract variant 묶음
# 아랫판 type 은 `*m1` 이 아니라 `metal1`: `*m1` 에는 via1 (m2c, metal2 면에도 있음) 이 들어가 Magic 이 "다른 면의 단자" 로 보지 않고
# 같은 면 둘레만 찾는다 → "device missing 1 terminal" (ExtBasic.c 의 TTMaskIntersect(tmask, DBPlaneTypes[pnum]) 조건)
dst.write_text(s)

rc = (src.parent / 'sky130A.magicrc').read_text()
a = "tech load $PDK_ROOT/sky130A/libs.tech/magic/sky130A.tech"
assert a in rc
rc = rc.replace(a, f"tech load [file join [file dirname [file normalize [info script]]] {dst.name}]")
dst.with_suffix('.magicrc').write_text(rc)
print('wrote', dst, dst.with_suffix('.magicrc'))

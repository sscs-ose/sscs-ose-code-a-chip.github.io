"""col_blk top RTL (오픈소스 합성 입력): col_ctrl (RTL) + 열 MUX·clamp 매크로 384 개 (digital/col_blk/col_macros.vh, gen_colblk.py 출력 그대로).
핀 = 상용 판 col_blk 과 같은 이름 (col[63:0], 아날로그 7, 디지털 12). 쓰임: python3 mk_colblk_v.py <col_macros.vh> <out.v>"""
import sys
mac, out = sys.argv[1:3]
A = ['vw', 'vbus', 'C1', 'C2', 'vzero', 'vrailp', 'vrailm']
D = ['sdi', 'rstb', 'col1_clk', 'col2_clk', 'sel_en', 'PROG', 'VER', 'SENSE', 'WRANY', 'lo', 'READ', 'READb']
O = ['wvw', 'wvwb', 'wz', 'wzb', 'vfy', 'vfyb', 'sns1', 'sns1b', 'sns2', 'sns2b']
L = ['// col_blk top — mk_colblk_v.py (col_ctrl + col_macros.vh)',
     '(* blackbox *) module cb_tg_n2 (inout a, inout b, input ctl, input ctlb); endmodule',
     '(* blackbox *) module cb_tgw_n20 (inout a, inout b, input ctl, input ctlb); endmodule',
     '(* blackbox *) module clamp_d2r (inout col, inout vrailp, inout vrailm); endmodule',
     f'module col_blk (col, {", ".join(A)}, {", ".join(D)});',
     '  inout [63:0] col;', f'  inout {", ".join(A)};', f'  input {", ".join(D)};',
     f'  wire [63:0] {", ".join(O)};',
     '  col_ctrl u_ctrl (' + ', '.join(f'.{p}({p})' for p in D[:10] + O) + ');']
L += [open(mac).read().rstrip(), 'endmodule', '']
open(out, 'w').write('\n'.join(L))
print('col_blk top', out)

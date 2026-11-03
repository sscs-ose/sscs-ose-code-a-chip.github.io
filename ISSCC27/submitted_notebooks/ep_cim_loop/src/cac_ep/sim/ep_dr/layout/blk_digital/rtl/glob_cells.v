//   ckdrv: chip_lib.py config_block(buf=True) 의 and2 (NAND2 + INV) + CKBUF (INV 4 단) 자리.
//          nand2_1 → inv_2 (= sck_r·ts) → 반쪽마다 inv_4 → inv_8. 극성: 반전 4 번 = y = a·en.
//          hvl dfrtp CLK 입력 2.7 fF × DFF 52–100 개 + 배선 → 반쪽마다 inv_8 (최대 부하 3.0 pF, ff 5.5 V).
//          (자작 DFFR 은 클록이 TG 4 개를 직접 구동해 CKBUF 가 64 배까지 필요했다. hvl dfrtp 는 셀 안에 클록 buffer 가 있다)
//   obuf4 / obuf8: 같은 신호를 반쪽마다 따로 구동 (buf_4 둘 / buf_8 둘). rstb 는 RESET_B 7.9 fF × DFF 약 280 개 (반쪽) → buf_8
module ckdrv (input wire a, input wire en, output wire yf, output wire yn);
    wire nb, p, nf, nn;
    sky130_fd_sc_hvl__nand2_1 u_nd  (.A(a), .B(en), .Y(nb));
    sky130_fd_sc_hvl__inv_2   u_i0  (.A(nb), .Y(p));
    sky130_fd_sc_hvl__inv_4   u_if1 (.A(p),  .Y(nf));
    sky130_fd_sc_hvl__inv_8   u_if2 (.A(nf), .Y(yf));
    sky130_fd_sc_hvl__inv_4   u_in1 (.A(p),  .Y(nn));
    sky130_fd_sc_hvl__inv_8   u_in2 (.A(nn), .Y(yn));
endmodule

module obuf4 (input wire a, output wire yf, output wire yn);
    sky130_fd_sc_hvl__buf_4 u_f (.A(a), .X(yf));
    sky130_fd_sc_hvl__buf_4 u_n (.A(a), .X(yn));
endmodule

module obuf8 (input wire a, output wire yf, output wire yn);
    sky130_fd_sc_hvl__buf_8 u_f (.A(a), .X(yf));
    sky130_fd_sc_hvl__buf_8 u_n (.A(a), .X(yn));
endmodule

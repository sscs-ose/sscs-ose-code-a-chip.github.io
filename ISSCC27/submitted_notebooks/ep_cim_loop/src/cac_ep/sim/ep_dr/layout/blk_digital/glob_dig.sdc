# glob_dig: 클록 sck (패드 SCK, 레벨 변환 뒤). 설정 레지스터 클록 cfg_clk = sck·sld, 레지스터 클록 = sck·sld̄·ts (밖으로).
# timing 은 상관없고 (SCK 주기 ≥ 10 ns, 덱은 10 ns) 합성·배치가 돌게만 준다
create_clock -name sck -period 100.0 [get_ports sck]
# sdi·sld 는 sck 가 낮을 때만 바뀐다 (chip_lib 「SLD·TSEL 은 SCK 가 낮을 때만 바꾼다」, 덱 cfg()·shift()) → 하강 에지 기준.
#   (첫 판 잡 721125 은 상승 에지 기준이라 cfg_clk = sck·sld 의 clock gating hold 가 −45 ns 로 나옴)
set_input_delay 5.0 -clock sck -clock_fall [get_ports {sdi sld}]
set_output_delay 5.0 -clock sck [all_outputs]
set_false_path -from [get_ports rst]
set_driving_cell -lib_cell sky130_fd_sc_hvl__buf_4 [all_inputs]
# 출력 부하 (반쪽마다, 어림): 클록 = DFF 52–100 개 CLK 2.7 fF + 블록 안 배선 + 전역 배선 ≈ 0.8 pF,
#   rstb = 반쪽 DFF 약 280 개 RESET_B 7.9 fF ≈ 2.2 pF + 배선 → 2.5 pF (받는 블록이 buffer 를 넣으면 더 작다), 나머지 ≈ 0.5 pF
set_load 0.8 [get_ports {*_clk_f *_clk_n}]
set_load 2.5 [get_ports {rstb_f rstb_n}]
set_load 0.5 [get_ports {READ_* READb_* PROG_* VER_* SENSE_* WRANY_* dload_* pol_* rd_out_*}]
set_max_transition 3.0 [current_design]
set_max_fanout 20 [current_design]

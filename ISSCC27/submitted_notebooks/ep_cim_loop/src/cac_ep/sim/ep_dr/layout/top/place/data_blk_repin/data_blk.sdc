# data_blk: 클록 data_clk (칩에서는 SCK·SLD̄·TSEL_DATA 를 전역 블록 ckdrv 가 구동, 느림). timing 은 상관없고 합성·배치가 돌게만 준다
create_clock -name data_clk -period 100.0 [get_ports data_clk]
set_input_delay 5.0 -clock data_clk [get_ports {sdi dload READ}]
set_output_delay 5.0 -clock data_clk [all_outputs]
# rstb = 비동기 reset
set_false_path -from [get_ports rstb]
# 입력은 전역 블록 buf_4 / inv_8 이 구동 (배선 길이는 모름)
set_driving_cell -lib_cell sky130_fd_sc_hvl__buf_4 [get_ports {sdi dload READ rstb}]
set_driving_cell -lib_cell sky130_fd_sc_hvl__inv_8 [get_ports data_clk]
# ga·gb: 반쪽마다 입력 구동 NMOS 둘 (W 1,000 µm, L 0.5 µm, g5v0d10v5) 의 게이트 ≈ 2 pF × 2 → 4 pF (어림)
set_load 4.0 [get_ports {ga[*] gb[*]}]
# sp·spb·sm·smb: 주입기 TG 둘 (N 2 µm / P 4 µm) + 배선 (주입기 블록까지 약 0.3 mm) ≈ 0.2 pF
set_load 0.2 [get_ports {sp[*] spb[*] sm[*] smb[*]}]
set_max_transition 3.0 [current_design]
# ga·gb 는 READ 가 바뀔 때만 움직이고 (추론 전 설정 뒤 120 ns 여유, gen_chip_deck3) 4 pF 를 끄는 데 10 ns 까지 허용 → buf_8 급으로 충분
set_max_fanout 20 [current_design]
set_max_transition 10.0 [get_ports {ga[*] gb[*]}]

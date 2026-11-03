# [col_blk 사본: digital/row.sdc 를 고침] col_ctrl: token 레지스터 클록 둘 (칩에서는 SCK 를 TSEL 로 고른 것, 느림).
# timing 은 상관없고 합성·배치가 돌게만 준다
create_clock -name col1_clk -period 100.0 [get_ports col1_clk]
create_clock -name col2_clk -period 100.0 [get_ports col2_clk]
set_input_delay 5.0 -clock col1_clk [get_ports {sdi sel_en PROG VER SENSE WRANY lo}]
set_output_delay 5.0 -clock col1_clk [all_outputs]
# rstb = 비동기 reset (클록과 무관하게 바뀜)
set_false_path -from [get_ports rstb]

# row_ctrl: token 레지스터 클록 둘 (칩에서는 SCK 를 TSEL 로 고른 것, 느림). timing 은 상관없고 합성·배치가 돌게만 준다
create_clock -name row1_clk -period 100.0 [get_ports row1_clk]
create_clock -name row2_clk -period 100.0 [get_ports row2_clk]
set_input_delay 5.0 -clock row1_clk [get_ports {sdi sel_en PROG VER SENSE READb WRANY}]
set_output_delay 5.0 -clock row1_clk [all_outputs]
# rstb = 비동기 reset (클록과 무관하게 바뀜)
set_false_path -from [get_ports rstb]

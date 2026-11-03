# col_blk (2 단계) SDC: col.sdc 와 같은 클록·입력 (decoder 출력은 블록 안 넷 → output delay 없음).
# READ·READb 는 남는 열 SP TG 의 ctl·ctlb 로만 감 (std 셀 없음, timing 없음)
create_clock -name col1_clk -period 100.0 [get_ports col1_clk]
create_clock -name col2_clk -period 100.0 [get_ports col2_clk]
set_input_delay 5.0 -clock col1_clk [get_ports {sdi sel_en PROG VER SENSE WRANY lo}]
set_false_path -from [get_ports rstb]

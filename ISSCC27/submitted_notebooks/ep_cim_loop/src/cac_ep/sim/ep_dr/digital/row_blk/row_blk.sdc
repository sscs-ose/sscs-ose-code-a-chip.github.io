# [row_blk 사본 10/28: ../row.sdc 에서 출력 지연만 뺌 (row_ctrl 의 출력 1,272 개는 이제 블록 안에서 매크로 ctl 로 감)]
# token 레지스터 클록 둘 (칩에서는 SCK 를 TSEL 로 고른 것, 느림). timing 은 상관없고 배치가 돌게만 준다
create_clock -name row1_clk -period 100.0 [get_ports row1_clk]
create_clock -name row2_clk -period 100.0 [get_ports row2_clk]
set_input_delay 5.0 -clock row1_clk [get_ports {sdi sel_en PROG VER SENSE READb WRANY}]
# rstb = 비동기 reset (클록과 무관하게 바뀜)
set_false_path -from [get_ports rstb]

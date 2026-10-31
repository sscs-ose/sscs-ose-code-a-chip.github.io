# Yosys 합성 (yosys -c synth.tcl). 환경: TOP, RTL (빈칸 목록), LIBF (쓸 셀만 남긴 liberty), OUT (netlist), STAT (보고서)
yosys -import
set top $::env(TOP)
set lib $::env(LIBF)
read_liberty -lib $lib
foreach f $::env(RTL) { read_verilog -defer $f }
hierarchy -check -top $top
synth -top $top -flatten
# latch (dlxtp, D·GATE·Q) 와 비동기 reset DFF (dfrtp) 는 dfflibmap 이 liberty 에서 고름
dfflibmap -liberty $lib
abc -liberty $lib
opt_clean -purge
# 상수 출력이 생기면 conb_1 이 필요하지만 conb_1 은 쓰지 않음 (LVS) → 있으면 멈춤
hilomap -hicell sky130_fd_sc_hvl__conb_1 HI -locell sky130_fd_sc_hvl__conb_1 LO
opt_clean -purge
tee -o $::env(STAT) stat -liberty $lib
check -assert
write_verilog -noattr -noexpr -nohex -nodec -defparam $::env(OUT)

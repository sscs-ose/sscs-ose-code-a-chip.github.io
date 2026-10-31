* Xyce MC probe: per-instance agauss (SKY130 5V mismatch lib)
.temp 25
.option scale=1.0u
.lib "/home/grads/s/seokjindaveoh/work/ep_dr/layout/top/postsim/models/sky130_5v_tt_mc.lib.spice" tt
.param mc_mm_switch=1
vd d 0 2.5
vg g 0 1.5
vd1 d d1 0
vd2 d d2 0
x1 d1 g 0 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5
x2 d2 g 0 0 sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5
.dc vd 2.5 2.5 1
.print dc i(vd1) i(vd2)
.end

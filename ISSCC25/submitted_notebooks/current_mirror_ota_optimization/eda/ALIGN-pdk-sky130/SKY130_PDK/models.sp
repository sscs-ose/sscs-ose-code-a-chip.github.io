.model sky130_fd_pr__pfet_01v8 pmos w=1 l=1
.model sky130_fd_pr__nfet_01v8 nmos w=1 l=1
.model nmos_rvt nmos l=1 w=1 nfin=1 nf=1 m=1  stack=1 parallel=1
.model pmos_rvt pmos l=1 w=1 nfin=1 nf=1 m=1  stack=1 parallel=1
.model nmos_lvt nmos l=1 w=1 nfin=1 nf=1 m=1  stack=1 parallel=1
.model pmos_lvt pmos l=1 w=1 nfin=1 nf=1 m=1  stack=1 parallel=1
.model nmos_hvt nmos l=1 w=1 nfin=1 nf=1 m=1  stack=1 parallel=1
.model pmos_hvt pmos l=1 w=1 nfin=1 nf=1 m=1  stack=1 parallel=1
.model nfet nmos nfin=1 nf=1 l=1 m=1  stack=1 parallel=1
.model pfet pmos nfin=1 nf=1 l=1 m=1  stack=1 parallel=1
.model resistor res r=1
.model sky130_fd_pr__cap_mim_m3_1 cap l=1 w=1 m=1
.model inductor ind ind=1


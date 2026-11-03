* ============================================================
* Fixed Testbench: nand_dcdl 4-stage characterization
* ============================================================

* --- Technology models ---
.lib "__PDK_ROOT__/sky130A/libs.tech/ngspice/sky130.lib.spice" tt

* --- Post-layout extracted netlist ---
.include "__NETLIST_PATH__"

* ============================================================
* Parameters & Supplies
* ============================================================
.param vdd_val = 1.8
Vdd  VPWR 0 DC vdd_val
Vss  VGND 0 DC 0

* Input Signal A: 10ns period
Va   A    VGND PULSE(0 vdd_val 1n 50p 50p 5n 10n)

* ============================================================
* 0-25n:  Q=0001 (1 stage)
* 25-50n: Q=0010 (2 stages)
* 50-75n: Q=0100 (3 stages)
* 75-100n:Q=1000 (4 stages)
* ============================================================
Vq0  Q0_node  VGND PWL(0 vdd_val 24.9n vdd_val 25n 0)
Vq1  Q1_node  VGND PWL(0 0       24.9n 0       25n vdd_val 49.9n vdd_val 50n 0)
Vq2  Q2_node  VGND PWL(0 0       49.9n 0       50n vdd_val 74.9n vdd_val 75n 0)
Vq3  Q3_node  VGND PWL(0 0       74.9n 0       75n vdd_val)

* ============================================================
* DUT Instantiation
* Correct Port Order: A Q[0] Q[1] Q[2] Q[3] VGND VPWR Y
* ============================================================
Xdut  A Q0_node Q1_node Q2_node Q3_node VGND VPWR Y nand_dcdl
Cload Y VGND 5f

.tran 10p 100n

.control
run

wrdata __RESULTS_DIR__/nand_dcdl_results.csv v(A) v(Y) v(Q0_node) v(Q1_node) v(Q2_node) v(Q3_node)

quit
.endc
.end
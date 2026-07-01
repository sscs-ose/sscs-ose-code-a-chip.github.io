* ============================================================
* Fixed Testbench: inv_dcdl 64-stage characterization
* ============================================================

* --- Technology models ---
.lib "/Users/shreyas/.ciel/ciel/sky130/versions/0fe599b2afb6708d281543108caf8310912f54af/sky130A/libs.tech/ngspice/sky130.lib.spice" tt

* --- Post-layout extracted netlist ---
* (Make sure this path points to your extracted inverter DCDL)
.include "/Users/shreyas/Code/CaC_Spring26/spice/netlists/inv_dcdl.spice"

* ============================================================
* Parameters & Supplies
* ============================================================
.param vdd_val = 1.8
Vdd  VPWR 0 DC vdd_val
Vss  VGND 0 DC 0

* Input Signal A: 10ns period
Va   A    VGND PULSE(0 vdd_val 1n 50p 50p 4.9n 10n)

* ============================================================
* Binary Control Signals (0 to 63)
* Each state lasts 20ns. Total sim time for 64 states = 1280ns.
* Using PULSE(V1 V2 TD TR TF PW PER) to create a binary counter
* ============================================================
* Q0 toggles every 20ns (Period = 40ns)
Vq0  Q0_node  VGND PULSE(0 vdd_val 20n 50p 50p 19.9n 40n)

* Q1 toggles every 40ns (Period = 80ns)
Vq1  Q1_node  VGND PULSE(0 vdd_val 40n 50p 50p 39.9n 80n)

* Q2 toggles every 80ns (Period = 160ns)
Vq2  Q2_node  VGND PULSE(0 vdd_val 80n 50p 50p 79.9n 160n)

* Q3 toggles every 160ns (Period = 320ns)
Vq3  Q3_node  VGND PULSE(0 vdd_val 160n 50p 50p 159.9n 320n)

* Q4 toggles every 320ns (Period = 640ns)
Vq4  Q4_node  VGND PULSE(0 vdd_val 320n 50p 50p 319.9n 640n)

* Q5 toggles every 640ns (Period = 1280ns)
Vq5  Q5_node  VGND PULSE(0 vdd_val 640n 50p 50p 639.9n 1280n)

* ============================================================
* DUT Instantiation
* Correct Port Order: A Q[0] Q[1] Q[2] Q[3] Q[4] Q[5] VGND VPWR Y
* ============================================================
Xdut  A Q0_node Q1_node Q2_node Q3_node Q4_node Q5_node VGND VPWR Y inv_dcdl

Cload Y VGND 5f

* Simulate for 1280ns to capture all 64 states (0 through 63)
.tran 10p 1280n

.control
run

wrdata /Users/shreyas/Code/CaC_Spring26/spice/results/inv_dcdl_results.csv v(A) v(Y) v(Q0_node) v(Q1_node) v(Q2_node) v(Q3_node) v(Q4_node) v(Q5_node)

quit
.endc
.end
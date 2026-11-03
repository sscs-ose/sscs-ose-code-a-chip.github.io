* ============================================================
* Testbench: DLL (zdb_top)
* Drive CLK_IN, observe CLK_OUT
* ============================================================

.lib "/Users/phevos/.ciel/ciel/sky130/versions/0fe599b2afb6708d281543108caf8310912f54af/sky130A/libs.tech/ngspice/sky130.lib.spice" tt
.include "../netlists/zdb_top.spice"

* ============================================================
* Parameters
* ============================================================
.param vdd_val     = 1.8
.param clk_period  = 10n
.param half_period = {clk_period / 2}
.param rise_fall   = 50p
.param rst_width   = 50n

* ============================================================
* Power Supplies
* ============================================================
Vdd  VPWR 0 DC {vdd_val}
Vss  VGND 0 DC 0

* ============================================================
* Reset -- held high for 30ns then released
* ============================================================
Vrst RST 0 PWL(
+   0n                 {vdd_val}
+   {rst_width - 0.1n} {vdd_val}
+   {rst_width}        0
+ )

* ============================================================
* Input Clock
* ============================================================
Vclk_in CLK_IN 0 PULSE(
+   0           {vdd_val}
+   {rst_width} {rise_fall}
+   {rise_fall} {half_period} {clk_period}
+ )

* ============================================================
* DUT
* ============================================================
Xdut
+   VGND VPWR
+   CLK_IN CLK_OUT
+   CTRL_DBG_0 CTRL_DBG_1 CTRL_DBG_2 CTRL_DBG_3 CTRL_DBG_4 CTRL_DBG_5
+   DOWN_DBG
+   RST
+   SHIFT_LEFT_DBG SHIFT_RIGHT_DBG
+   UP_DBG
+   zdb_top

* ============================================================
* Simulation
* ============================================================
.tran 10p 200n

.control
run
shell mkdir -p ../results
wrdata ../results/zdb_top_results.csv v(CLK_IN) v(CLK_OUT) v(SHIFT_LEFT_DBG) v(SHIFT_RIGHT_DBG) v(UP_DBG) v(DOWN_DBG) 
quit
.endc

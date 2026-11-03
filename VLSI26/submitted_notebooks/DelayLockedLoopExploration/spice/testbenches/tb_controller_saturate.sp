* ============================================================
* Testbench: Saturating Controller SPICE Characterization
* ============================================================

* --- Technology models ---
.lib "__PDK_ROOT__/sky130A/libs.tech/ngspice/sky130.lib.spice" tt

* --- Post-layout extracted netlist ---
.include "__NETLIST_PATH__"

* ============================================================
* Parameters & Supplies
* ============================================================
.param vdd_val     = 1.8
.param clk_period  = 2n
.param half_period = {clk_period / 2}
.param rise_fall   = 50p
.param vthresh     = {vdd_val / 2}

Vdd  VPWR 0 DC vdd_val
Vss  VGND 0 DC 0

* ============================================================
* Clock Signal
* ============================================================
Vclk clk_node VGND PULSE(0 vdd_val 0 rise_fall rise_fall half_period clk_period)

* ============================================================
* Reset Signal
* ============================================================
* High for first 4ns (2 clock cycles), then released.

Vrst rst_node VGND PWL(
+   0.0n  vdd_val
+   3.9n  vdd_val
+   4.0n  0
+ )

* ============================================================
* Stimulus: UP/DOWN sequences (2ns clock, same cycle counts)
* ============================================================
* Saturating controller behavior (INIT_CTRL=32, MAX=63, MIN=0):
*   up=1, down=0 -> ctrl increments by 1, saturates at 63
*   up=0, down=1 -> ctrl decrements by 1, saturates at 0
*   up=down       -> hold
*
* Phase 1 ( 4- 44ns):  UP=1   — 20 cycles sustained UP
*   ctrl: 32->33->34->...->52
*
* Phase 2 (44- 64ns):  IDLE   — 10 cycles, ctrl holds
*
* Phase 3 (64-104ns):  DOWN=1 — 20 cycles sustained DOWN
*   ctrl: 52->51->...->32
*
* Phase 4 (104-114ns): IDLE   — 5 cycles
*
* Phase 5 (114-134ns): Alternating UP/DOWN every 3 cycles
*   Tests hold behavior — ctrl should stay constant
*
* Phase 6 (134-174ns): UP=1   — 20 cycles sustained UP
*   Continue incrementing from held value
*
* Phase 7 (174-180ns): IDLE

Vup   up_node   VGND PWL(
+   0       0
+   3.9n    0
+   4n      vdd_val
+   43.9n   vdd_val
+   44n     0
+   63.9n   0
+   64n     0
+   113.9n  0
+   114n    vdd_val
+   119.9n  vdd_val
+   120n    0
+   125.9n  0
+   126n    vdd_val
+   131.9n  vdd_val
+   132n    0
+   133.9n  0
+   134n    vdd_val
+   173.9n  vdd_val
+   174n    0 )

Vdown down_node VGND PWL(
+   0       0
+   63.9n   0
+   64n     vdd_val
+   103.9n  vdd_val
+   104n    0
+   113.9n  0
+   114n    0
+   119.9n  0
+   120n    vdd_val
+   125.9n  vdd_val
+   126n    0
+   131.9n  0
+   132n    vdd_val
+   133.9n  vdd_val
+   134n    0 )

* ============================================================
* DUT Instantiation
* ============================================================
* IMPORTANT: Verify port order against your extracted netlist.
*   .subckt line in the netlist defines the actual order.
*   The resulting spice list from LibreLane orders ports in alphabetical order

Xdut VGND VPWR clk_node ctrl0 ctrl1 ctrl2 ctrl3 ctrl4 ctrl5 down_node rst_node up_node controller

* Small load caps on each output bit (wiring + downstream gate cap)
Cload0 ctrl0 VGND 5f
Cload1 ctrl1 VGND 5f
Cload2 ctrl2 VGND 5f
Cload3 ctrl3 VGND 5f
Cload4 ctrl4 VGND 5f
Cload5 ctrl5 VGND 5f

* ============================================================
* Simulation Control
* ============================================================
.tran 500p 180n

* ============================================================
* Output & Control
* ============================================================
.control
run

wrdata __RESULTS_DIR__/__RESULT_NAME__ v(clk_node) v(rst_node) v(up_node) v(down_node) v(ctrl0) v(ctrl1) v(ctrl2) v(ctrl3) v(ctrl4) v(ctrl5)

quit
.endc
.end

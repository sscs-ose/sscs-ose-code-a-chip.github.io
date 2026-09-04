* ============================================================
* Testbench: Acquire/Track Controller SPICE Characterization
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
* Stimulus: UP/DOWN sequences (2ns clock)
* ============================================================
* Acquire/track controller behavior:
*   ACQUIRE_STEP=4, TRACK_STEP=1, QUIET_CYCLES=8, INIT_CTRL=32
*   Starts in acquire mode (step=4).
*   After 8 consecutive idle cycles, switches to track mode (step=1).
*   Any UP/DOWN resets quiet_count but does NOT revert to acquire.
*
* Phase 1 ( 4- 24ns):  UP=1   — 10 cycles in acquire mode
*   ctrl: 32->36->40->44->48->52->56->60->63(sat) (step=4)
*
* Phase 2 (24- 44ns):  IDLE   — 10 cycles
*   quiet_count reaches 8 → switches to track mode
*
* Phase 3 (44- 84ns):  UP=1   — 20 cycles in track mode
*   ctrl increments by 1 each cycle (already at 63, saturates)
*
* Phase 4 (84-124ns):  DOWN=1 — 20 cycles in track mode
*   ctrl: 63->62->61->...->43 (step=1)
*
* Phase 5 (124-144ns): IDLE   — 10 cycles
*
* Phase 6 (144-164ns): DOWN=1 — 10 cycles in track mode
*   ctrl: 43->42->...->33
*
* Phase 7 (164-180ns): IDLE

Vup   up_node   VGND PWL(
+   0       0
+   3.9n    0
+   4n      vdd_val
+   23.9n   vdd_val
+   24n     0
+   43.9n   0
+   44n     vdd_val
+   83.9n   vdd_val
+   84n     0 )

Vdown down_node VGND PWL(
+   0       0
+   83.9n   0
+   84n     vdd_val
+   123.9n  vdd_val
+   124n    0
+   143.9n  0
+   144n    vdd_val
+   163.9n  vdd_val
+   164n    0 )

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
set ngbehavior=ps
run

wrdata __RESULTS_DIR__/__RESULT_NAME__ v(clk_node) v(rst_node) v(up_node) v(down_node) v(ctrl0) v(ctrl1) v(ctrl2) v(ctrl3) v(ctrl4) v(ctrl5)

quit
.endc
.end

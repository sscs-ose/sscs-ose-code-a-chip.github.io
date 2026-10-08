* ============================================================
* Testbench: Phase Detector SPICE Characterization
* ============================================================

* --- Technology models ---
.lib "/Users/phevos/.ciel/ciel/sky130/versions/0fe599b2afb6708d281543108caf8310912f54af/sky130A/libs.tech/ngspice/sky130.lib.spice" tt

* --- Post-layout extracted netlist ---
.include "../netlists/phase_detector_syn_pfd.spice"





* ============================================================
* Parameters & Supplies
* ============================================================
.param vdd_val     = 1.8
.param clk_period  = 10n
.param half_period = {clk_period / 2}
.param rise_fall   = 50p
.param vthresh     = {vdd_val / 2}

Vdd  VPWR 0 DC vdd_val
Vss  VGND 0 DC 0

* ============================================================
* Reset Signal
* ============================================================
* High for first 20ns, then released.
* Clocks start after reset deasserts so DUT sees clean edges.

Vrst RST VGND PWL(
+   0.0n  vdd_val
+  19.9n  vdd_val
+  20.0n  0
+ )

* ============================================================
* Clock Signals
* ============================================================
* Plain PULSE sources — delay values set by the Python runner.
* Both clocks run at the same frequency; only the start time
* (and thus phase relationship) differs per test.

Vclk_in  CLK_IN  VGND PULSE(0 vdd_val 20n  rise_fall rise_fall half_period clk_period)
Vclk_out CLK_OUT VGND PULSE(0 vdd_val 22n rise_fall rise_fall half_period clk_period)

* ============================================================
* DUT Instantiation
* ============================================================
* IMPORTANT: Verify port order against your extracted netlist.
*   .subckt line in the netlist defines the actual order.
*   The resulting spice list from LibreLane orders ports in alphabetical order

Xdut VGND VPWR CLK_IN CLK_OUT DOWN RST UP phase_detector

* Small output loads (wiring + charge pump gate cap)
Cload_up   UP   VGND 5f
Cload_down DOWN VGND 5f

* ============================================================
* Simulation Control
* ============================================================
.tran 10p 100n

* ============================================================
* Output & Control
* ============================================================
.control
run

wrdata ../results/pd_syn_pfd_clkin_lead_results.csv v(CLK_IN) v(CLK_OUT) v(RST) v(UP) v(DOWN)
quit
.endc
 
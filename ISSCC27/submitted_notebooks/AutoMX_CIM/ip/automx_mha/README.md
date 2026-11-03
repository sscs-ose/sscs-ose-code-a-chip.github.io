# AutoMX MHA RTL IP

Copyright 2026 EDABK Laboratory.

`automx_mha_ip` implements a complete two-token, four-channel, two-head MHA datapath. Four programmable 4×4 ternary weight matrices and two MXFP4 activation rows feed Q/K/V projections, digital QKᵀ, normalized two-element softmax, digital A×V, MXFP4 context quantization and O projection. The eight four-column projection transactions use the existing CIM–SAR readout protocol. No real-number arithmetic, DPI, Python callback or simulation-only calculation appears in the synthesizable IP.

One signed 18×18 multiplier serves QKᵀ, sigmoid interpolation and A×V. Two-token softmax equals sigmoid of the score difference. A 65-entry Q0.15 LUT at 1/8 intervals, linear interpolation and clipping at magnitude 8 replace runtime exponent/divide. The scale 181/1024 includes the X2 input convention and 1/√2. Probability pairs sum to exactly 32768. Context uses the MXFP4 magnitude alphabet {0,1,2,3,4,6,8,12} in X2 units; ties select the smaller magnitude. Results are signed 12-bit X2 values; shared activation scale is unity for this configuration. Only control/valid state uses asynchronous reset. Data buffers are fully overwritten before consumption, reducing the reset tree load.

## Host interface

| Interface | Contract |
|---|---|
| `cfg_*` | Ready/valid weight write. Stage 0/1/2/3 = Q/K/V/O; row 0..3. Four positive and four negative column bits; overlapping signs are rejected. All 16 rows must be loaded. |
| `req_*` | Ready/valid frame input, eight signed five-bit activations. Bits `5*(4*token+channel)+:5` hold X2. Requires a calibrated available backend. |
| `rsp_*` | Two ready/valid output rows. `rsp_row_o` identifies token; four signed 12-bit X2 lanes. Data and row remain stable under backpressure. |
| `core_cfg_*` | Four weight row writes before each Q/K/V/O stage. |
| `core_eval_*` / `core_result_*` | One four-column projection per token. Completion must carry the calibrated flag; the IP never predicts completion. |
| `busy_o` / `fault_o` | Ownership lasts through both output handshakes. Timeout, backend fault, uncalibrated completion or invalid input produces a sticky fault until reset. |

The integrated `automx_cim_mixed_signal_proto` retains the existing root instances `core_i`, `condition_i`, `adc_i`, and `seq_i`. `mha_i` owns configuration/evaluation while busy. `mha_mode_i=0` selects direct CIM readout when idle. Host calibration remains available while MHA is idle and is locked while a frame is active. Changing mode during a frame cannot steal the backend. The IP does not invent a physical calibration: program the original 304 readout thresholds from the appropriate measured path.

## Calibrated decoding and ADC polarity

The readout defaults to `BINARY_DECODE=1`: an upper-bound search over the same 38 thresholds in each of eight column/row-phase banks produces the same 39 signed levels in five or six comparison clocks. `BINARY_DECODE=0` retains the 38-clock linear reference. Both paths use `captured_code >= threshold`, including equality and endpoint behavior. Exhaustive real-RTL verification covers 98,304 code/bank/table combinations in `scripts/verify_binary_decoder.py`.

Native calibration found that the original differential wiring reversed code versus signed sum. The integrated wrapper now connects conditioner `AINP` to ADC `inn_analog` and `AINN` to `inp_analog`; the application native bench uses the identical crossing. Program 304 increasing midpoint thresholds measured with this wiring. A threshold table measured with the former polarity is not interchangeable. A frame contains eight vector projections, 32 scalar dot products and 64 ADC conversions because each scalar dot uses two row phases.

## Serial digital comparison backend

`rtl/automx_ternary_projection_digital.sv` implements resident positive/negative weight masks and one conditional sign/add term per clock, with 16 term clocks per vector. `automx_mha_digital_top` connects this backend to the unchanged MHA. The FuseSoC `digital_baseline` target selects that complete digital implementation. It uses the same activation alphabet, weight masks, arithmetic, ready/valid protocol and output format as the mixed backend; ternary projections do not use general-purpose multipliers.

Application verification runs all 2,947 official UCI HAR test frames through linear mixed, binary mixed and digital paths. The nominal native profile covers two preselected frames with 128 logical ADC conversions. The electrical/service profile extends this to six fixed class-selected frames, 384 logical conversions and request-tagged replay under measured RTL control timing and ideal 50 ps input pulses. Routed pulse delivery is measured independently, including short-pulse failures; the native result does not qualify that failed interface. The laboratory notebook regenerates application vectors, native calibration, replay and routed-gate activity estimates. Shared feature extraction, embedding and classification run in software.

## Calibration-data clock gating

The adopted controller places only the 304 twelve-bit threshold data words behind `sky130_fd_sc_hd__dlclkp_1`, the characterized integrated clock gate. A level-sensitive latch holds its enable during the high clock phase. An accepted write enables that data bank; the validity bitmap, neighbor-order validation, FSM, synchronization and fault/reset state retain their regular clocks. The physical view contains the actual mapped ICG. Portable RTL simulation uses the corresponding latch-and-gate behavior. No accepted threshold write, reset invalidation or busy-frame ownership rule changes.

Power comparisons use the same native-backed frame vectors, response timing, output readiness, SKY130 TT library and OpenSTA 3.1 `read_vcd` activity. A separate checker counts actual clock edges at all 3,648 data flops. Earlier OpenSTA 2.4 gated-clock estimates are not used to decide this change. Mapped area, routed standard-cell area and macro footprint are reported separately.

## Run verification

From the containing laboratory folder, using the `env_mamba` Python environment:

```bash
python ip/automx_mha/verify.py --root . --work diagnostics/mha_ip_check
```

The test independently generates integer and floating references, checks 98 deterministic frames with random backend stalls, checks both output rows under backpressure, and exercises reset/abort, invalid activations, unavailable calibration, uncalibrated completion, timeout and backend faults. A separate test instantiates the actual mixed top and readout sequencer, programs all 304 thresholds and checks 64 ADC response transactions plus direct-mode regression. Its ADC fixture is a functional protocol model; native transistor measurements are kept as separate evidence.

`verify.synthesize(root, work)` maps the IP to the same SKY130 TT Liberty used by the controller/SAR area tables. Full cold OpenLane implementation consumes `rtl/automx_mha_ip.sv`, the existing readout RTL and the integrated top, with five hard-macro LEF/GDS views from the laboratory `inputs` folder. MHA and readout/calibration are independently routed rectangular macros; the parent routes their connections to CIM/acquisition, conditioner/mux and SAR ADC. Source-matched digital views are reused as IP inputs; changed RTL is hardened automatically. Parent timing reads both digital gate netlists and their extracted SPEFs along with the parent SPEF. The FuseSoC descriptor lists the digital and integrated RTL filesets; physical views are bound by the laboratory OpenLane configuration.

## Physical blackbox interface

For top-level physical integration, select the `physical_blackbox` fileset/target in `automx_mha.core`. `rtl/digital_blackboxes.sv` declares only the ports of MHA and readout/calibration, with the `blackbox` attribute; `rtl/wrapper_blackboxes.sv` declares CIM/acquisition, conditioner/mux and SAR ADC. Bind all five GDS/LEF views using `manifest.json` and `inputs/digital_blocks/source_library.json`. The functional verification targets continue to use the real MHA and readout RTL. Actual hierarchical timing reads routed gate netlists and SPEFs instead of these interface stubs.

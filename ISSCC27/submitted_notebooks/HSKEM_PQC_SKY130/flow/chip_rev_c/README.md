# HSKEM-2, signed-off layout (release tag hskem2-rev-c): RTL, flow and sign-off record

This folder holds what built the signed-off chip of Section 9 and Appendix C: the RTL that the published sources do not
carry, the flow scripts as they ran, and the sign-off and analysis scripts behind `results/fullchip/rev_c/`. The routed
database itself (netlist, DEF, OpenDB, SPEF, SDC and both GDS files) is attached to the release
[`hskem2-rev-c`](https://github.com/tandat08052007/sscs-ose-code-a-chip.github.io/releases/tag/hskem2-rev-c);
`results/fullchip/rev_c/release_sha256.txt` lists the SHA-256 of each compressed file and `summary.json` those of the
uncompressed database. Paths below are relative to this folder (`flow/…`, `rtl/…`) unless they start at the submission
root (`scripts/`, `results/`, `hskem_rtl/`; `flow/macros/` is the submission's OpenRAM view folder).

## Using the release

```
# from the submission root, after downloading the seven hskem2_rev_c_*.gz files of the release into rev_c/;
# hskem2_rev_c_implant_fixed.gds.gz is the layout that passes the complete DRC deck (Appendix C.3),
# hskem2_rev_c_6_final.gds.gz the router's output that LVS, timing and the other checks use
(cd rev_c && sha256sum -c ../results/fullchip/rev_c/release_sha256.txt) && gunzip -k rev_c/*.gz
# timing at one corner, as in Appendix C.1 (OpenROAD of ORFS 6101364b; the SKY130 HD Liberty of the corner)
mkdir -p rev_c/results && for f in v def odb spef sdc; do cp rev_c/hskem2_rev_c_6_final.$f rev_c/results/6_final.$f; done
PDK=/path/to/sky130A/libs.ref/sky130_fd_sc_hd/lib   # the SKY130 HD Liberty folder
RUN=rev_c/results CORNER=ss_100C_1v60 SC_LIB=$PDK/sky130_fd_sc_hd__ss_100C_1v60.lib MACRO_LIB_DIR=flow/chip_rev_c/views/ss IO_MODE=soc \
  openroad -no_splash -exit flow/chip_rev_c/flow/final_sta.tcl | grep RESULT   # setup_wns 1.395, hold_wns 0.541 (sta_corners.json)
```

`views/{ss,tt,ff}/` are the macro timing views used in sign-off: OpenRAM's views with every clock-to-output time
replaced by the value measured in SPICE at that corner (`views.log`, `flow/t3_spice_views.py`); input setup and hold
times are OpenRAM's typical-corner values. The rebuilt views also keep OpenRAM's analytical `minimum_period` on the
macro clock pins (1.62 to 1.91 ns, the largest being 1.913 ns for `24x128` and 1.899 ns for `24x256`); at the 40 ns
sign-off clock this check cannot bind, so the attribute was left unchanged. `final_sta.tcl` also takes `IO_MODE=sdc` (the constraints as written),
`DERATE=0.05`, `MACRO_HOLD=1` (hold paths into the macros) and `FMAX_SEARCH=1` (shortest period by bisection). Set
`SC_LIB` to the `sky130_fd_sc_hd` Liberty file of the corner.
`6_final_concat.cdl` (hashed in `summary.json`, the LVS netlist) is not in the release; LVS can be rerun from the GDS and
the netlist with the scripts of `signoff/`.

## The RTL

`rtl/make_root.sh <out dir>` rebuilds the synthesized RTL from the published sources: `hskem_rtl/`, the ASIC wrapper of
this folder (`rtl/asic/rtl/`, which binds the 18 SRAM macros), `scripts/make_packed_system.py` with the edits of the signed-off layout
(`scripts/t3_*_edit.py`), the two chip edits (the NTT store bound to its 24 × 128 macro, the one-round Keccak as the
core's default) and the session edits of revision C (`rtl/revc_edit.py`, with their checks in the system testbench,
`rtl/revc_tb_edit.py`). Its output is identical, file for file, to the root the chip was synthesized from: the script checks
every file against `results/fullchip/rev_c/root_sha256.txt` and prints `ROOT_MATCHES_CHIP`. The logic carries
only the public placeholder provisioning credential.

The chip was synthesized with the defines of `flow/config.mk` (the SRAM store, the streamed system of Section 8 and the first layout's
two *(chip)* defines `TRUSTEDGE_PMAC_RETIME`, `TRUSTEDGE_SO_PIPE`) plus the fourteen of the signed-off layout, each documented at the
top of its edit script:

| Define | Edit script | What it moves out of a half-cycle SRAM path |
|:---|:---|:---|
| `TRUSTEDGE_T3_MAC_DEEP` | `make_packed_system.py` | two more stages in each pipelined product |
| `TRUSTEDGE_T3_MM_PIPE` | `t3_matrix_mac_edit.py` | the key generation's serial multiplier (one cycle per pair) |
| `TRUSTEDGE_T3_CRC_SERIAL` | `t3_bridge_edit.py` | the SPI response CRC, one byte per cycle |
| `TRUSTEDGE_T3_BARRETT_1C` | `t3_barrett_edit.py` | the generic reducer keeps one conditional subtraction |
| `TRUSTEDGE_T3_SA_PIPE`, `_MUL_SEL`, `_SEL_REP` | `make_packed_system.py` | the Karatsuba sums and the operand selection of the two pair multipliers |
| `TRUSTEDGE_T3_PMAC_RAW` | `t3_pmac_raw_edit.py` | registered SRAM operands of the pipelined products |
| `TRUSTEDGE_T3_CODEC_RETIME` | `t3_codec_retime_edit.py` | the codec's reads of its coefficient RAM |
| `TRUSTEDGE_T3_MSG_PIPE`, `_PP_EARLY` | `t3_decaps_msg_edit.py` | message recovery and the product RAM's output into the NTT |
| `TRUSTEDGE_T3_LOAD_PIPE` | `t3_load_pipe_edit.py` | the encryption's coefficient stream into the codec |
| `TRUSTEDGE_T3_MARGIN` | `t3_margin_edit.py` | public-key export and the key generation's self-check |
| `TRUSTEDGE_T3_EK_PREF` | `t3_ek_pref_edit.py` | the H(ek) feed from a register |

`scripts/t3_tb_edit.py` updates the testbench's expected cycle counts; with every define off the generator builds
the streamed system of Section 8 unchanged.

`TRUSTEDGE_REVC` adds the session changes of revision C to the HSM shell and the top level (`rtl/revc_edit.py`, which
documents each one): every binding takes a fresh 64-bit epoch collected from the health-gated entropy source while the
random-bit generator is idle, the send counter of a sealed frame must advance by exactly one, a refused binding no
longer consumes its counter, and the receive path counts accepted and rejected tags per key and locks after 16
rejections until the next binding or zeroization. The ML-KEM datapath is untouched, so the cycle counts are those of
revision B. `revc/tb_revc_session.sv` exercises these rules with and without the define (16 of 16 checks pass with
it), and `revc/check_seal_log.py` recomputes every sealed tag with Python's `hmac` module:

```
flow/chip_rev_c/rtl/make_root.sh /tmp/hskem2c        # prints ROOT_MATCHES_CHIP
flow/chip_rev_c/revc/run_session_tb.sh /tmp/hskem2c/root -DTRUSTEDGE_REVC   # 16 checks; without the define: 9
```

## Parasitic corners and session checks

`revc/rc_corners.sh` re-extracts the routed database with the flow's rules and with the six OpenRCX rule sets of the PDK, scales the sign-off parasitics, and repeats the sign-off STA on every set (`revc/rc_scale.py`, `revc/rc_collect.py`; result `results/fullchip/rev_c/rc_corners.json`, Appendix C.1). It only reads the signed-off files. `formal/` holds the bounded model checks of the session logic (`formal/README.md`; result `results/fullchip/rev_c/session_formal.json`, Appendix E.3).

## Tools

OpenROAD-flow-scripts at commit `6101364b` (its Yosys 0.68+ and OpenROAD `f5522624`), with one patch to the detailed
router (`flow/openroad_drt1231_skip.diff`: after a routed design is reloaded, a pin without an access point inside one
worker's route box stopped the run with error DRT-1231; the patch leaves the pin to the worker whose box holds one); KLayout 0.30.7; Netgen
6.2; ngspice 41; Icarus Verilog 11.0 (Ubuntu 22.04) for the chip-level simulations of revision C (system simulation,
SRAM access count, gate-level run, power), and the OSS CAD Suite of 2026-09-28 (Icarus Verilog 14-devel) for
`scripts/acvp_rtl_encdec.sh` and the session testbench. SKY130 `sky130_fd_sc_hd` and the OpenRAM views and
netlists of `flow/macros/`.

## The flow, in the order it ran

`rtl/make_root.sh` and `flow/final_sta.tcl` (above) are the runnable entry points. The other scripts are a record: they carry the build machine's absolute paths (`/mnt/d/...`, `/root/t3/...`) and the work
directories of the run, and are meant to be read and adapted, not run unchanged.

Revision C reuses the scripts of revision B in `flow/`, `signoff/` and `analysis/` and adds the ones in `revc/`
(`revc/revc_env.sh` sets the root, the defines and the patched router for them).

1. `revc/revc_phase1.sh`: the RTL root (the run used a private-tree variant of `rtl/make_root.sh` with the identical
   output, `results/fullchip/rev_c/root_sha256.txt`), then synthesis to clock-tree synthesis at 40 ns with revision B's
   recipe (`flow/run_pad.sh`, `run_chip_v2.sh`, `config.mk`, `constraint.sdc`, `macros_chipv2.tcl`).
2. `revc/revc2_chain.sh`, stage by stage, each with a gate:
   * global route with revision B's recipe (`flow/grt_a3recipe.sh`, antenna jumpers of `post_grt_jumpers.tcl`) and
     routing obstructions over the frame that the SRAM macros' abstracts leave open (`revc/pre_grt_revc2.tcl`); the
     router had used that frame at the corner of one macro, the spot that revision B cleared only with post-route halos;
   * timing repair on the global-route database, setup at the slow corner and hold at the fast corner, with a ±5 %
     derate (`revc/grt_eco_revc.tcl`, `revc_grt_eco.sh`, `revc_run_chip.sh`, `revc2_gt_*.sh`), so that the routed layout
     needs no timing changes;
   * detailed route and antenna rounds (`revc/revc_ant_chain.sh`), then the final stage and timing at three corners
     (`revc/revc_final.sh`, `flow/final_sta_t3.sh`, `final_sta.tcl`, `t3_spice_views.py`).
3. Two targeted fixes of the last router markers next to that macro corner (`revc/revc2_fix1.sh`, `revc2_fix2.sh` with
   `eco_fix_revc2.tcl`): a met4 obstruction over the macro's supply-pin strip, the few nets involved ripped up and routed
   again, and a transition repair with the extracted parasitics (`revc/revc_drv_round.sh`). The result, ga1, has 0 router
   DRC and 0 antenna violations.
4. Sign-off (`revc/revc_signoff.sh`, with the scripts of `signoff/`): KLayout DRC in eight part decks
   (`signoff_drc_split.sh`, `drc_split/`), Netgen LVS (`lvs/`) and the front-end rules (`revc/feol_revc.sh`); then
   Magic's SKY130 deck (`signoff/magic_drc_boxes.sh`, `classify_magic_drc.py`; the stand-alone cell and macro check of
   `magic_cell_check.sh` applies unchanged, because the markers outside the macros lie in the same two cells).
5. Analysis (`revc/revc_extras.sh`, `revc_collect_runs.sh`): gate-level simulation over a decapsulation, energy
   (`revc/power_revc.sh`, SRAM accesses), IR drop, hold into the macros and fmax by period search, with the SPICE check of
   the macro that receives the closest hold paths (`revc/hold_8x768_corners_revc.sh`); the results files
   (`revc/collect_revc.py`), the FPGA build summary (`revc/revc_fpga_build.py`) and the release (`revc/release_revc_pack.sh`).

`scripts/acvp_rtl_encdec.sh` (Section 4) checks this RTL against the NIST ACVP vectors from the published sources.

The scripts in `revc/` ran in the author's tree with absolute paths, and some of them read revision B's record
(`results/fullchip/rev_b/`, `flow/chip_rev_b/`): `collect_revc.py` copies its stand-alone Magic cell check, which
covers the same two cells and macro, and compares its gate-level simulation. Revision C replaces revision B in this
folder; revision B's files remain in the history of this branch (commit `bd9f17a`) and its database on the release
`hskem2-rev-b`.

SPDX-License-Identifier: Apache-2.0

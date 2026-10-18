# HSKEM-2, signed-off layout (release tag rev-b): RTL, flow and sign-off record

This folder holds what built the signed-off chip of Section 9 and Appendix C: the RTL that the published sources do not
carry, the flow scripts as they ran, and the sign-off and analysis scripts behind `results/fullchip/rev_b/`. The routed
database itself (netlist, DEF, OpenDB, SPEF, SDC and both GDS files) is attached to the release
[`hskem2-rev-b`](https://github.com/tandat08052007/sscs-ose-code-a-chip.github.io/releases/tag/hskem2-rev-b);
`results/fullchip/rev_b/release_sha256.txt` lists the SHA-256 of each compressed file and `summary.json` those of the
uncompressed database. Paths below are relative to this folder (`flow/…`, `rtl/…`) unless they start at the submission
root (`scripts/`, `results/`, `hskem_rtl/`; `flow/macros/` is the submission's OpenRAM view folder).

## Using the release

```
# from the submission root, after downloading the seven hskem2_rev_b_*.gz files of the release into rev_b/
(cd rev_b && sha256sum -c ../results/fullchip/rev_b/release_sha256.txt) && gunzip -k rev_b/*.gz
# timing at one corner, as in Appendix C.1 (OpenROAD of ORFS 6101364b; the SKY130 HD Liberty of the corner)
mkdir -p rev_b/results && for f in v def odb spef sdc; do cp rev_b/hskem2_rev_b_6_final.$f rev_b/results/6_final.$f; done
RUN=rev_b/results CORNER=ss_100C_1v60 SC_LIB=$PDK/sky130_fd_sc_hd__ss_100C_1v60.lib MACRO_LIB_DIR=flow/chip_rev_b/views/ss IO_MODE=soc \
  openroad -no_splash -exit flow/chip_rev_b/flow/final_sta.tcl | grep RESULT
```

`views/{ss,tt,ff}/` are the macro timing views used in sign-off: OpenRAM's views with every clock-to-output time
replaced by the value measured in SPICE at that corner (`views.log`, `flow/t3_spice_views.py`); input setup and hold
times are OpenRAM's typical-corner values. `final_sta.tcl` also takes `IO_MODE=sdc` (the constraints as written),
`DERATE=0.05`, `MACRO_HOLD=1` (hold paths into the macros) and `FMAX_SEARCH=1` (shortest period by bisection). Set
`SC_LIB` to the `sky130_fd_sc_hd` Liberty file of the corner.
`6_final_concat.cdl` (hashed in `summary.json`, the LVS netlist) is not in the release; LVS can be rerun from the GDS and
the netlist with the scripts of `signoff/`.

## The RTL

`rtl/make_root.sh <out dir>` rebuilds the synthesized RTL from the published sources: `hskem_rtl/`, the ASIC wrapper of
this folder (`rtl/asic/rtl/`, which binds the 18 SRAM macros), `scripts/make_packed_system.py` with the edits of the signed-off layout
(`scripts/t3_*_edit.py`) and the two chip edits (the NTT store bound to its 24 × 128 macro, the one-round Keccak as the
core's default). Its output is identical, file for file, to the root the chip was synthesized from: the script checks
every file against `results/fullchip/rev_b/root_sha256.txt` and prints `ROOT_MATCHES_CHIP`. The logic carries
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

## Tools

OpenROAD-flow-scripts at commit `6101364b` (its Yosys 0.68+ and OpenROAD `f5522624`), with one patch to the detailed
router (`flow/openroad_drt1231_skip.diff`: after a routed design is reloaded, a pin without an access point inside one
worker's route box stopped the run with error DRT-1231; the patch leaves the pin to the worker whose box holds one); KLayout 0.30.7; Netgen
6.2; ngspice 41; Icarus Verilog of the OSS CAD Suite (2026-03). SKY130 `sky130_fd_sc_hd` and the OpenRAM views and
netlists of `flow/macros/`.

## The flow, in the order it ran

`rtl/make_root.sh` and `flow/final_sta.tcl` (above) are the runnable entry points. The other scripts are a record: they carry the build machine's absolute paths (`/mnt/d/...`, `/root/t3/...`) and the work
directories of the run, and are meant to be read and adapted, not run unchanged.

1. `flow/t3e_launch.sh`: the RTL root (the run used a private-tree variant of `rtl/make_root.sh` with the identical
   output, `results/fullchip/rev_b/root_sha256.txt`), then synthesis to global route at 40 ns (`flow/run_pad.sh`, `run_chip_v2.sh`,
   `config.mk`, `constraint.sdc`, `macros_chipv2.tcl`, `grt_a3recipe.sh` with the antenna jumpers of
   `post_grt_jumpers.tcl`), and timing with global-route parasitics (`t3_grt_sta.sh`, `t3_spice_sta.sh`).
2. Detailed route (`flow/drt_t3.sh`, `drt_round_t3.*`), antenna repair (`ant_chain_t3.sh`) and transition repair with
   extracted parasitics (`drv_spef_round_t3.*`).
3. Engineering changes at the macro corners, x1 to x6 (`flow/chain4_t3.sh` … `chain6_t3.sh`): routing halos inside the
   macro outline, nets ripped up and routed again (`eco_reroute_t3.tcl`), and hold repair under the I/O model of
   Appendix C.1 (`eco_hold_io_t3.tcl`). The result, w1, has 0 router DRC and 0 antenna violations.
4. Final stage, extraction and timing at three corners with SPICE macro views (`flow/final_t3.sh`, `final_sta_t3.sh`,
   `final_sta.tcl`, `t3_spice_views.py`).
5. Sign-off (`signoff/signoff_t3e.sh`, `chain_20261017.sh`): KLayout DRC in eight part decks (`signoff_drc_split.sh`,
   `drc_split/`), Netgen LVS (`lvs/`, `lvs_rest2_t3e.sh`) and the front-end rules (`feol_chipv2.sh`); then Magic's
   SKY130 deck (`magic_drc_boxes.sh`, `classify_magic_drc.py` for markers inside and outside the macros,
   `magic_cell_check.sh` for the stand-alone cell and macro checks).
6. Analysis (`analysis/`): gate-level simulation over a decapsulation (`gls_t3e.sh`), energy (`fullchip_power_t3e.sh`,
   `sram_access_t3e.sh`; `power_t3e_restretch.sh` corrected a first run that had not stretched the activity file),
   IR drop (`ir_drop.tcl`, `ir_t3e_vcd.sh`), hold into the macros (`macro_hold_t3e.sh`) and the SPICE input-timing points
   (`sram_setup/`), the results files (`collect_revb.py`, `collect_revb_extra.sh`, `stage_t3e.sh`) and the release
   (`release_revb_pack.sh`).

`scripts/acvp_rtl_encdec.sh` (Section 4) checks this RTL against the NIST ACVP vectors from the published sources.

SPDX-License-Identifier: Apache-2.0

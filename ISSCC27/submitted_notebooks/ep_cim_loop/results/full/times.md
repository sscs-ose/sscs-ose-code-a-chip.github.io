# Time table (MODE=full, TRAIN=full, WEIGHTS=out/weights/nostab_5bit.npz, NJ=16, tools on PATH (container), 2026-10-31 16:35)

| Group | Step | Time (s) | Result | Note |
|---|---|---:|---|---|
| install | fix paths | 0.2 | ok |  |
| install | install: mamba | 0.0 | skipped | tools already on PATH (container) |
| install | install: eda | 0.0 | skipped | tools already on PATH (container) |
| install | install: dig | 0.0 | skipped | tools already on PATH (container) |
| install | install: openroad | 0.0 | skipped | tools already on PATH (container) |
| install | install: xyce | 0.0 | skipped | tools already on PATH (container) |
| install | install: py | 3.1 | ok | PART py 3.0 ok |
| install | install: pdk | 0.0 | ok | PART pdk 0.0 ok |
| install | tool versions | 2.2 | ok | 8.3.685 / Netgen 1.5.324 compiled on Thu Oct 15 02:24:51 PM CEST 2026 / Warning: netgen command 'format' use fully-qualified name '::netgen::format' / 26Q4-407- |
| training | download MNIST | 1.6 | ok |  |
| training | EP: one training step, written out | 1.8 | ok | weight update: 6360 cells, SET 3138, RESET 3222, median /b/ = 0.276 mV |
| training | training (full) | 1898.5 | ok |  |
| simulation | inference: saved weights, 3 seeds (nostab_5bit.npz) | 23.2 | ok | {"5b_s0": {"test": 0.958993, "saved": 0.958993, "diff": 0.0, "p_neuron_uW": 4912.35}, "5b_s1": {"test": 0.954795, "saved": 0.954795, "diff": 0.0, "p_neuron_uW": |
| simulation | figure: test accuracy and confusion matrix | 0.2 | ok |  |
| simulation | inference: newly trained weights | 7.1 | ok | {"5b_s0": {"test": 0.958993, "test_at_best_logged": 0.958993}, "sec": 5.7} |
| simulation | Xyce: read circuit, full test set (seed 0) | 326.5 | ok | Xyce 95.90 %, same digit as Python 3097 / 3097 |
| simulation | Xyce: weight-update block | 106.7 | ok | WU block: cells 132/132, decisions match 132/132, COMP1/2 sign 132/132, /ΔV_f/ path error median 9.575 mV, power 2.8621 mW |
| simulation | figure: weight-update decisions | 0.2 | ok |  |
| simulation | Xyce: chip deck sys2 | 1776.7 | ok | chip deck: all select nodes − Python max 1086.486 µV, first stage bit [24, 24], last stage bit [24, 24], power 6.6886 mW |
| simulation | RRAM write chip deck chip_write3 | 0.0 | skipped | runs in Xyce with the RRAM Verilog-A plug-in, which is built outside the Colab setup |
| layout | block: arr_w3s_128x64 | 5.7 | ok | XOR arr_w3s_128x64: same |
| layout | block: analog (input_drive, nudge_inj, bias_beta, wbuf) | 9.3 | ok | XOR input_drive: same; XOR nudge_inj: same; XOR bias_beta: same; XOR wbuf: same |
| layout | block: tg_n2 (switch macro) | 0.2 | ok | XOR tg_n2: same |
| layout | block: HOG op-amp | 0.3 | ok | XOR hog: same |
| layout | block: wu (weight update) | 8.1 | ok | XOR wu: same |
| layout | block: test patterns (4 blocks) | 1.2 | ok | XOR tp_tl: same; XOR tp_br: same; XOR tp_bandl: same; XOR tp_bandr: same |
| layout | block: pad frame | 40.0 | ok | XOR ep_die_real: same |
| layout | figure: block GDS | 1.3 | ok |  |
| layout | digital block glob_dig (Yosys + OpenROAD) | 9.7 | ok | 113 cells incl. macros, 2436 um2; outline and pins same as saved: True; route violations 0; Magic DRC 2 (hvntm.1 2; same rules as the saved layout); LVS: Circui |
| layout | digital block data_blk (Yosys + OpenROAD) | 158.7 | ok | 327 cells incl. macros, 10200 um2; outline and pins same as saved: True; route violations 0; Magic DRC 10 (hvntm.1 10; same rules as the saved layout); LVS: Cir |
| layout | digital block col_blk (Yosys + OpenROAD) | 219.3 | ok | 1174 cells incl. macros, 37578 um2; outline and pins same as saved: True; route violations 0; Magic DRC 421 (hvntm.1 64, nwell.8 357; same rules as the saved la |
| layout | digital block row_blk (Yosys + OpenROAD) | 196.5 | ok | 2226 cells incl. macros, 61256 um2; outline and pins same as saved: True; route violations 0; Magic DRC 2396 (hvntm.1 46, nwell.8 2350; same rules as the saved  |
| layout | figure: digital block GDS (open-source) | 2.3 | ok |  |
| layout | netlist: chip deck v3 + mk_top | 2.7 | ok | deck check: boundary nodes 718, same 701, intentionally different 17, unexpected 0, wrong cell mapping 0, unclassified devices 0 / diff lines vs saved: cdl 0, v |
| layout | placement: mk_lef + place_real | 17.5 | ok | LEF files different from saved: 4, place_real.json same |
| routing | pre-wiring (Python) | 25.2 | ok |  |
| routing | OpenROAD global + detailed route | 73.9 | ok | detailed route iterations 5, last: [INFO DRT-0199]   Number of violations = 0. / ORR: route nets without wire 0 / [INFO ANT-0002] Found 0 net violations. |
| routing | DEF → GDS + check | 0.9 | ok | CHECK_GDS PASS |
| routing | figure: routed core GDS | 0.7 | ok |  |
| routing | pad ring + die | 5.7 | ok | CONN OK |
| routing | figure: die GDS | 1.0 | ok |  |
| verification | Magic RRAM tech rebuild | 0.0 | ok | diff lines vs copy in src/: 0 |
| verification | core extraction + antenna (Magic) | 606.1 | ok | antenna 266, 606.02 s, 1276.2 MB |
| verification | core LVS (Netgen) | 1.6 | ok | Circuits match uniquely. / top {'dev': [83, 83], 'nets': [1130, 1130], 'result': 'Netlists match with 32 symmetries with property errors.'} |
| verification | die extraction (Magic, LVS view) | 142.4 | ok | 142.29 s, 1367.0 MB |
| verification | die LVS (Netgen, pads as black boxes) | 1.7 | ok | Circuits match uniquely. / top {'dev': [1, 1], 'nets': [25, 25], 'result': 'Netlists match uniquely.'} |
| verification | core DRC (Magic) | 1067.4 | ok | boxes 6630 (without hvntm.1: 6170) {'hvntm.1': 460, 'LU.3': 570, 'LU.2': 600, 'rpm.1': 20, 'nwell.8': 4980} |
| verification | die DRC (Magic) | 1894.7 | ok | boxes 836294 (mostly inside the IO cells) |

| Group | Time (s) | min |
|---|---:|---:|
| install | 5.5 | 0.1 |
| training | 1901.9 | 31.7 |
| simulation | 2240.6 | 37.3 |
| layout | 672.8 | 11.2 |
| routing | 107.4 | 1.8 |
| verification | 3713.9 | 61.9 |
| **Total** | **8642.1** | **144.0** |

0 failed: none

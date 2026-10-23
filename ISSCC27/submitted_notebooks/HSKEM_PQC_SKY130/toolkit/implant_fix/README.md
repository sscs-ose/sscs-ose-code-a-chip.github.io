# implant_fix: close sub-rule implant gaps inside OpenRAM macros, and prove nothing else changed

The SKY130 front-end (FEOL) rules of the ORFS KLayout deck require 0.38 µm between nsdm shapes, 0.38 µm between
psdm shapes and 0.27 µm between npc shapes. The OpenRAM bitcell arrays and their periphery leave many gaps
narrower than that between abutted cells; the deck notes that such gaps "should be manually merged". The flow's
own DRC runs with the front-end section off, so these gaps stay invisible until the section is run alone: 163,731
markers on HSKEM-2, all inside the macros.

| File | Role |
|:---|:---|
| `implant_fix.py` | closes the gaps of each macro top cell (grow and shrink by half the rule, bridge what remains) and writes the GDS **only if** every safety check is zero: no implant change over diffusion or tap, none removed from poly, none on a poly resistor, no new nsdm/psdm overlap, no width or spacing violation left |
| `verify_untouched.py` | proves that the fixed GDS differs from the original only in nsdm, psdm and npc inside the macro subtrees (same cells, same instances, every other cell-and-layer pair identical shape for shape) |
| `count_implant_violations.py` | counts the implant spacing and width markers of each macro (a quick check, seconds, that does not need the full deck) |
| `inject_implant_gaps.py` | adds three implant gaps (psdm, nsdm, npc) to a copy of a macro GDS, away from every device |

```bash
klayout -b -rd in_gds=macro.gds -rd out_gds=fixed.gds -r implant_fix.py
klayout -b -rd a=macro.gds -rd b=fixed.gds -r verify_untouched.py        # must end with RESULT: UNTOUCHED OK
```

The macros are the top cells named `sky130_sram_*` that no other such cell instantiates; nothing outside them is
touched. The three layers are flattened into the macro top cell. Field poly (wordlines between bitcells) that
lies in a closed gap receives the implant of its neighbours; the tool reports how much.

## Evidence

- **HSKEM-2 (the design the tool was written for):** 163,731 implant markers (`n/psdm.1` 151,886, `npc.2`
  11,845) before the fix, 0 after, on the full FEOL deck; `verify_untouched.py` passes on the full chip.
- **A macro HSKEM did not generate, with the defect injected:** the public `sky130_sram_1kbyte_1rw1r_32x256_8`
  (published in `sky130_sram_macros`, 161 cells; a different OpenRAM release and configuration from HSKEM's). `inject_implant_gaps.py` adds three gaps (0.20 µm of
  psdm, 0.20 µm of nsdm, 0.15 µm of npc); the counter finds one spacing marker per layer, `implant_fix.py` adds
  exactly 0.20, 0.20 and 0.15 µm² (gap × 1 µm), the counter finds none, and `verify_untouched.py` reports
  `UNTOUCHED OK` (5,796 cell-and-layer pairs compared, 0 differences).
- **No false fixes:** on the same public macro without the injection, the tool adds and removes 0.00 µm² and
  every check is zero. This macro has no implant gap, so the tool is a no-op where there is nothing to fix.
- **It refuses unsafe fixes:** `test_implant_fix.py` (three tests, `python3 -m pytest -q`, needs `klayout`)
  builds a toy macro whose gap lies over diffusion: the tool reports the 0.12 µm² change on diffusion and writes
  no file. The same file checks that the copies of the two scripts here are byte-identical to `scripts/`.

Limits: it fixes the three implant layers only; it does not look at other front-end rules (the public macro
still shows `licon.5`, `licon.8`, `licon.15` and `poly.*` markers that belong to its own layout style and are not
implant gaps). It changes mask data, so a foundry-bound design needs the foundry's agreement on the merge.

SPDX-License-Identifier: Apache-2.0

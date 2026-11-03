# drc_split: the ORFS SKY130 back-end DRC for chips that outgrow the memory

The OpenROAD-flow-scripts SKY130HD KLayout deck (`sky130hd.lydrc`) runs in deep mode, which keeps every derived
layer alive until the end. On an 11.2 mm² chip with 18 SRAM macros one rule (`ct.1`, the edges of every
`mcon`) lifts KLayout from 6 to 21.6 GB, and the metal rules after it outgrow a 27 GB machine. `drc_split`
cuts the back-end part of the deck (BEOL and off-grid checks) into eight part decks that run one after another
in fresh processes. The rules are not touched.

| File | Role |
|:---|:---|
| `split_beol_deck.py` | writes the eight part decks from the ORFS deck (its SHA-256 is checked) and proves that every BEOL rule line is in exactly one part |
| `run_split_drc.sh <gds> <dir> [--full]` | runs the parts; with `--full` also the unsplit deck and the equivalence check |
| `compare_reports.py` | compares the markers of the unsplit report with those of all parts (rule and geometry) |
| `inject_violations.py` | adds deliberate back-end violations to a copy of a GDS, outside its die |

Each part deck is the original byte for byte, except for the three section switches and a comment line in place
of the rules that belong to other parts (every kept line keeps its line number); execution mode and rule text
are unchanged. Front-end (FEOL) checks are not part of this tool; the sign-off runs them separately.

```bash
bash run_split_drc.sh design.gds out            # parts only, merged counts in out/
bash run_split_drc.sh design.gds out --full     # plus the unsplit run and out/equivalence.txt
```

## Evidence

- Equivalence on a design that is not HSKEM, the ORFS `gcd` example (`6_final.gds`): no violations
  either way, 0 markers from the parts and from the unsplit deck.
- Equivalence with violations: `inject_violations.py` adds 17 markers (minimum width and spacing on `li1` and
  `met1`–`met5`, a `mcon` and a via without enclosure, a box off the 5 nm grid). The unsplit deck and the eight
  parts report the same 17, rule by rule and shape by shape (`EQUIVALENT: 17 markers`).
- HSKEM-2 (11.2 mm², 18 macros): the unsplit deck did not fit the memory of the build machine; the eight parts did.
- `test_drc_split.py`: four unit tests of the comparison (`python3 -m pytest -q`).

Limits: the tool is tied to one deck (hash-checked); another ORFS revision needs a new hash after a look at the
rule groups. The equivalence on `gcd` shows the split loses no marker on a design that fits the memory; for a
design that does not fit, it rests on the line-partition proof of `split_beol_deck.py`.

SPDX-License-Identifier: Apache-2.0

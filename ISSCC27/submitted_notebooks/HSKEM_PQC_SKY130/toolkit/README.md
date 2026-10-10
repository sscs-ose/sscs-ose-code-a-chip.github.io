# toolkit: measurement tools of the HSKEM submission, packaged for other designs

Each directory holds a tool that was first written to measure HSKEM, made independent of it, given tests and a README,
and run on a design that is not HSKEM.

| Tool | What it does | Run on a second design |
|:---|:---|:---|
| [`openram_energy/`](openram_energy) | transistor-level energy per idle, write and read cycle of an OpenRAM SKY130 macro (ngspice, any port layout), optionally per corner with the clock-to-output delay | an 8 x 32 macro generated with OpenRAM (not one of HSKEM's), and a second 8 x 32 configuration whose broken write the read check catches |
| [`implant_fix/`](implant_fix) | closes sub-rule implant gaps inside OpenRAM macros and proves nothing else in the GDS changed | the same public macro, with gaps injected |
| [`drc_split/`](drc_split) | runs the ORFS SKY130 back-end DRC as eight part decks, for chips whose deep-mode run outgrows the memory, and checks that the parts report what the unsplit deck reports | ORFS `gcd`, clean and with 17 injected violations |
| [`prose_coverage/`](prose_coverage) | lists which numbers in a notebook's prose are tied to its data | three notebooks accepted at ISSCC 2026 |

Every tool runs on the open tools of the submission (ngspice, KLayout, Python 3); each README states what its
evidence shows and what it does not. `python3 -m pytest -q` in a tool's directory runs its tests.

SPDX-License-Identifier: Apache-2.0

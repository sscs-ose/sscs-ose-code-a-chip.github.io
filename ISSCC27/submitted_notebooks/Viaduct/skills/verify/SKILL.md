---
name: viaduct-verify
description: Run SKY130 DRC through Viaduct on the layout open in KLayout (markers appear in its Marker Browser) or on a GDS, and know what the result does and does not mean. Read before making any claim about design-rule or LVS correctness.
---

# Verification through Viaduct

## DRC

| Task | CLI | Python |
|---|---|---|
| DRC of the open layout, markers in KLayout | `python client.py drc` | `vd.verify.drc()` |
| DRC of a file | `python client.py drc --gds /foss/designs/x.gds` | `vd.verify.drc(gds=path)` |
| deck switches | `python client.py drc --opt floating_met=true` | `vd.verify.drc(options={...})` |

Deck: `/foss/pdks/sky130A/libs.tech/klayout/drc/sky130A_mr.drc` (community SKY130
manufacturing-rules deck, release in `deck_release`). Viaduct turns on FEOL, BEOL
and offgrid groups (the deck defaults them all to **off**, which checks nothing)
and fails the run if no rule section ran. Result: `violations`, `rules_violated`,
`rules_checked` (256 for SKY130 with the default groups), `rules[]` with rule name,
count, description and example locations; `runs/drc_<id>/drc.lyrdb`.

How to report: "DRC clean against the SKY130 community deck <release>, 256 rules,
run <id>". Not: "DRC clean" or "signoff". The deck has no density rules and is not
the foundry deck.

Reference (13 Oct 2026): T-coil W=4 um, area=8000 um^2 is clean (run
20261013_145348_19a8); a 0.5 um met5 strip is caught as `m5.1` (positive control).

## Not available yet

LVS (netgen) and parasitic extraction (Magic / klayout-pex): roadmap V3, needed once a
layout contains devices. Do not claim LVS.

## Built-in PCell checks

The T-coil PCell rejects invalid parameters before drawing (layer order, crossover
metals, complete via chains, minimum width per metal, minimum turn gap, via landing
size, reference geometry limits). These are prototype constraints from
`pdk/sky130A.json`; the DRC deck is the real check.

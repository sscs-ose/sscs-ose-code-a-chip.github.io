# Bounded GDS geometry and public layer-coefficient check

This is a **geometry and selected-component calculation**, not an independent
PEX deck, full-net RC solution, signoff extraction, or silicon measurement.
It uses the existing
[MAG](../../../layout_compact_repair/evidence/attempt1/atlas.mag) and
[GDS](../../../layout_compact_repair/evidence/attempt1/atlas.gds):

| Archived input | SHA-256 |
| --- | --- |
| `atlas.mag` | `b2442585e4f9fec2be04b7dd48de4e5e1b87b8fcc375780df11a845be9a2c342` |
| `atlas.gds` | `a7d778406f5766b443eb954bfda33e56158a7604caf3ccd02d5b634d4b57d910` |

[The path-free geometry audit](reproduce_geometry.py) was replayed using
Magic 8.3.684 (recorded source revision
`4f53bb3091d1e4a9b2009a58f157a8a4331d4c84`) and open_pdks revision
`aa3fc215a80d32437b8cca1cb3fdee819d18c4c9`. From these public
inputs, it reproduced [geometry.json](geometry.json) byte for byte
(SHA-256 `724fe0f87cd76979e281cbce00b00f5354a2546a1f3a35e237d63a6bbe09d739`).
The audit matches a separate MAG export to the archived GDS at 2,867
canonical polygons and 26 TEXT records; assigns all 2,508 selected
conductor/contact polygons exactly once to 26 logical nets; and checks
the MAG's 15 ports and 27 MOS. Non-conductor device and special-purpose
GDS polygons are **not** assigned by this conductor audit.

For a new run from this directory, use WSL Ubuntu 24.04, Python 3
(replayed with 3.12.3; standard library only), the pinned Magic and
sky130A PDK/rcfile above, and fresh **nonexistent** writable output paths:

```sh
python3 reproduce_geometry.py \
  --mag ../../../layout_compact_repair/evidence/attempt1/atlas.mag \
  --gds ../../../layout_compact_repair/evidence/attempt1/atlas.gds \
  --magic "$MAGIC_BIN" --rcfile "$RCFILE" --pdk-root "$PDK_ROOT" \
  --workdir "$NEW_WORKDIR" --output "$NEW_JSON"
```

Do not use the GDS-imported RC graph as a replacement for the MAG extraction.
The first GDS-import port-restoration attempt failed; resetting the Magic
edit box restored all 15 ports and gave 26/26 logical nets and 27 MOS, but
**54/133 logical capacitor-pair values differ** and the imported RC has
**2,773 R / 462 C** rather than the MAG's **675 R / 319 C**. Exported
polygons and ports do not establish equivalence of internal contacts,
resistor segmentation, capacitive graph, or physical model fidelity.
The geometry table below comes from MAG-assigned polygons reconciled to
the archived GDS, **not** that imported RC graph.

Using the public SkyWater
[RCX resistance and capacitance tables](https://skywater-pdk.readthedocs.io/en/main/rules/rcx.html),
Table 91 gives Metal3 **47 milliohm/square**. The following calculation
is sheet resistance along the *full length of a single isolated Metal3
rectangle* at that coefficient. It does **not** solve the tapped, branched
whole-net current path or account for contact resistance:

| Named net | Metal3 rectangle (um) | Isolated end-to-end sheet component (ohm) |
| --- | ---: | ---: |
| `clk` | 48.8 x 0.34 | 6.745882 |
| `tail` | 123.6 x 0.34 | 17.085882 |
| `xp`, `xn` (each) | 53.6 x 0.34 | 7.409412 |
| `qp`, `qn` (each) | 50.8 x 0.34 | 7.022353 |

Table 95 gives adjacent-layer parallel-plate coefficients of
**0.133861 fF/um2 for M1-M2** and **0.0861861 fF/um2 for M2-M3**.
Applied solely to these named, opposite-net overlap areas:

| Opposing polygons | Overlap (um2) | Conditional plate component (fF) |
| --- | ---: | ---: |
| `clk` M2 / `tail` M3 | 0.34 | 0.029303274 |
| `tail` M1 / `clk` M2 | 0.0133 | 0.0017803513 |
| `qn` M2 / `qp` M3 | 0.34 | 0.029303274 |
| `qp` M2 / `qn` M3 | 0.27 | 0.023270247 |

These are **conditional area terms**, not extracted pair capacitances:
special-device shielding and process-corner suitability are unqualified.
Same-layer facing metal, fringe, substrate, device/junction capacitance,
via resistance and all other polygons remain outside the four terms.
The audit finds no positive *adjacent-metal area overlap* for `xp`-`xn`;
that does not imply zero mutual or total capacitance. In particular, the
48.8 um of `clk`-`tail` facing Metal3 boundary at a 0.46 um gap is **not**
converted to a lateral capacitance using the vertical-plate coefficient.
These component checks cannot calibrate the full archived RC network.

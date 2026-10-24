# Later 20 ns physical implementation evidence

This appendix preserves two independently engineering-qualified members of DAC
Round 2 `FINAL_002`, frozen at commit
`5239290e91f789d68fd8e4b282b54fdb086f6285`. It is a selected engineering subset of
an unsuccessful three-size family, **not a newly preregistered two-size study**.
The original ISSCC experiment and its unsuccessful 4x4 antenna record retain
their historical identities. The original 8x8 implementation was not completed;
the later Round 2 8x8 attempt failed bounded antenna repair and did not complete
downstream qualification. Neither family is now claimed complete.

## Recalculate the included evidence

From the submission directory, with Python 3.10 or newer:

```console
python -X utf8 supplement/physical20/verify.py --check
```

The standard-library-only verifier checks every indexed raw/layout byte hash,
binds each configuration to the frozen recipe and native run manifest, parses
the independent R2R report, checks all nine recorded hold corners, rereads
native DRC/LVS/antenna/connectivity counters, and regenerates the exact bytes of
`metrics.json` in memory. Detailed R2R path slack count/minimum must agree with
the report's scalar tokens. It also checks mapped-retention records and image/GDS
identity. No Python package installation, RTL simulator, EDA tool or network is
needed. Import interface: `verify(root=None) -> dict`.

To regenerate only this appendix's derived JSON from unchanged records:

```console
python -X utf8 supplement/physical20/verify.py --write
python -X utf8 supplement/physical20/verify.py --check
```

`--write` does not manufacture raw evidence or repair a failed record. The
Notebook displays returned values instead of embedding manually entered
performance metrics. These are checks of saved experimental records, not new
RTL simulations, physical implementations, or renewed signoff.

## What changed in the physical flow

The later common `DAC27Classic` recipe adds a generic post-detailed-route antenna
stage, checks all nets, and invokes native antenna repair only when necessary,
with at most two repair/reroute passes and the same margin for every size.
The corrected stage relies on native protected legalization; it does not call
the redundant extra detailed-placement/mirroring operation that caused an LVS
failure in rejected `FINAL_001`. Explicit two-thread detailed routing is also
part of the new recipe. The common settings, exact frozen source, and prospective
protocol are included under `raw/`.

Both retained `FINAL_002` implementations were rerun from RTL with that same
later recipe. This is not relabeling the original failed 4x4 run. The later 4x4
native repair summary documents a reduction to zero antenna violations within
the bound, followed by fresh extraction and downstream checks. The later 2x2
repair stage found no violations. These records support the usefulness of the
combined revised flow in those implementations; changing the recipe, thread
setting and run prevents attributing every original-to-later difference solely
to one repair operation. The Round 2 protocol and all failures remain visible.

## Metric definitions and limits

- `core_area_um2` is final `design__core__area`; `cell_area_um2` is final
  `design__instance__area`. Neither is a complete-system cost or a power metric.
- Internal R2R slack is parsed from the dedicated `r2r.stdout.log` token at
  `max_ss_100C_1v60`, **not** substituted from a similarly named state metric.
  The frozen derivation is `P_sta = CLOCK_PERIOD - R2R_setup_slack`, and
  `F_sta_MHz = 1000 / P_sta_ns`. This fixed-layout estimate is not measured
  silicon Fmax or complete I/O/system latency.
- All-path setup slack/count and all-corner hold are reported separately.
  Native max-slew and max-capacitance diagnostics remain nonzero; their exact
  recorded aggregate values are in `metrics.json` and the Notebook table.
  Passing the defined research qualification does not mean every electrical
  rule passed, unrestricted timing convergence, or tapeout readiness.
- The state files retain the tools' other native fields for byte integrity.
  This appendix makes no power, energy, silicon measurement, ranking-reversal,
  Pareto, or weighted-optimization claim from those fields.

## Evidence map

All source paths in `provenance.json` are relative to the research archive
`ISSCC27_Model2GDS_Codex`. Copies under `raw/` retain original bytes. The family
qualification JSON is historical parser output; `final_state.json`,
`post_route_state.json`, `r2r.stdout.log`, and `repair_summary.tsv` are the native
outputs used to independently recalculate the displayed results.

| Included path | What it supports |
| --- | --- |
| `raw/final_002_freeze.json`, `raw/recipe.json`, `raw/protocol.md` | Commit, common recipe, original three-size gate and stop condition |
| `raw/cfg_2x2/`, `raw/cfg_4x4/` | Run/config identity, native final area/check counters and compact manufacturability summary, nine-corner hold, complete dedicated R2R report, mapped-retention report and repair sequence |
| `raw/family_qualification.json`, `raw/cfg_8x8_repair_summary.tsv` | Original Round 2 FAIL status and remaining 8x8 antenna failure; no qualified 8x8 performance |
| `raw/tool_versions.json` | Captured OpenLane, Yosys, OpenROAD, OpenSTA and Magic versions |
| `raw/dac27_openlane.py`, `raw/dac27_post_drt.tcl`, `raw/phase2_r2r_sta.tcl`, `raw/timing_methodology.md` | Frozen stage integration, repair mechanism and authoritative timing query; source evidence, not portable standalone EDA entrypoints |
| `provenance.json` | Original relative paths and SHA-256; exact original OpenLane/R2R/retention/tool-version command receipts and exit status; large-archive identities checked during packaging |
| `raw/layout_manifest.json`, `raw/render_layouts_original.py`, `layouts/` | Actual final GDS image sources, hashes, render settings, original rendering source and unchanged images |

The pinned flow uses OpenLane 2.3.10, SKY130A revision
`0fe599b2afb6708d281543108caf8310912f54af`, `sky130_fd_sc_hd`, and the container
digest in `raw/recipe.json`. Source lineage and unchanged RTL hashes are recorded
by the freeze; the original submission's RTL/models and all 441 records remain
outside this appendix and are not replaced.

## Layout images and larger archives

The two images are byte-identical existing renderings of each qualified final
GDS. They show selected top-cell interconnect drawing layers (`li1`, `met1` to
`met5`), a central detail window, source run and GDS hash. Referenced library-cell
interiors, labels, cuts and unselected layers are omitted. Different overview
scales are explicitly labeled. An image is not a physical signoff check.

The original renderer and its version/layer policy are preserved for inspection;
rerendering requires the omitted GDS files, matching original dependencies and
research-archive structure. The small portable appendix can verify image hashes
and provenance but cannot regenerate layout geometry without those files.

Large GDS, maximum SPEF, final netlist, propagated SDC, saved STA environment,
mapped JSON and resolved configuration artifacts were hash-checked against the
native manifests during candidate packaging. Their original paths/sizes/hashes
are recorded in `provenance.json`; large artifacts are deliberately not copied.
Full EDA reproduction therefore requires the research archive at the freeze,
its recorded PDK/container and those artifacts. The appendix does not claim
that a reader possessing only this ZIP has rerun or independently verified
those omitted files. The integrity index itself is not a digital signature.
The DRC/LVS/antenna summary and native counters are included; the complete
per-check decks, extraction files and all detailed signoff reports are not.

Project scripts and derived illustrations retain the project's Apache-2.0
license. Captured tool-output notices remain verbatim. No PDK/library source,
cell GDS, tool executable, or font is added; see the submission `NOTICE` for
third-party attribution.

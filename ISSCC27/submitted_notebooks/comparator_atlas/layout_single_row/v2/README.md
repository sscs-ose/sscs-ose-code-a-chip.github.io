# Adopted version: single-row-local-pitch-b1

This version adopts the exact local-pitch b1 layout. Its matched control is
the previously adopted **single-row-a1**, retained byte-identically in
[`../v1/`](../v1/). The original 4.8 um compact layout is an earlier historical
control, not the control for this comparison.

The historical native measurement includes every nonempty GDS material
polygon (wells, body ties, guards and shields); only TEXT is excluded.
The bbox changes from a1's 121.8 x 17.03 um (2074.254 um2) to b1's
110 x 17.03 um (1873.3 um2): a **9.688013% incremental reduction**.
This is not die area, polygon-union area or signoff.

The fixed 13 mirror-pair radii are 3.8, 7.6, 11.4, 15.2, 19.0, 23.2,
27.4, 31.6, 35.8, 40.0, 44.2, 48.4 and 52.6 um, on the 0.005 um grid.
The 27 guarded PCells, device dimensions/flavors/junctions/bodies,
15 ordered ports, pair order/reflection/y and local relative pin/escape
geometry are retained. Horizontal endpoint updates set output halfspan
20.4 um, shield halfspan 21.4 um and M4 spines at +/-21 um; four translated
body-pad bridges and three grounded shields remain. Centerlines are not
extracted resistance.

The prior bounded trial passed 14 native gates on one actual candidate
full-style DRC attempt. This publication and the subsequent full45 campaign
**reuse both native proofs and extracts; they do not rerun native tools**.
New local intervals have at least 0.20 um additional planning safety.
Unchanged global M3 tracks have the inherited 0.16 um rule margin; this is
not a claim that all material has 0.20 um margin.
`native-b1/` contains exact PCells, routes, source freezes, negative controls,
check logs, MAG/GDS/EXT/res.ext and netlists. The archived adapter preserves
historical host paths; it is not a default executable reproduction command.
`pre-native-restoration/atlas.mag` is the exact SHA-verified recovered
historical pre-route input, **not** the final routed MAG. The recovery and
member-resolution receipts explain the normal Magic save that replaced it.

## Matched saved-data qualification

The new full45 campaign executed **1440 successful fresh transients**:
TT/SS/FF/SF/FS x 1.62/1.8/1.95 V x -40/27/125 C x signed +/-3 and
 +/-10 mV x a1/b1 x C/RC x 10/5 ps. There are **720 numerical pairs**,
720 finest 5 ps traces and 1440 two-deadline measurement rows, not 1440
finest independent experiments. Each layout/mode population has 180 keys.
The earlier 64-trace diagnostic is separate historical evidence.

| Population | 1 ns correct/wrong/unresolved | 2 ns correct/wrong/unresolved | Mean core fJ | Worst recorded 2 ns latency (ns) |
|---|---:|---:|---:|---:|
| Matched a1 C | 170/0/10 | 180/0/0 | 353.340125 | 1.389035 |
| Adopted b1 C | 170/0/10 | 180/0/0 | 346.542852 | 1.346432 |
| Matched a1 RC | 156/0/24 | 180/0/0 | 421.044730 | 1.810632 |
| Adopted b1 RC | 158/0/22 | 180/0/0 | 412.879469 | 1.760276 |

The only improved 1 ns RC keys are **SS / 1.62 V / 125 C / -10 and +10 mV**.
FS unresolved points remain; unresolved latency is null, never a zero or a
later 2 ns decision. No previously correct key is lost.
RC energy changes by -1.939286% as a ratio of totals/means and
-1.945659% as the mean per-point percentage. These estimators differ.
The observed minimum 2 ns RC margin changes from 189.368 to 239.724 ps.
All 360 primary energy and timing changes are recorded decreases, not
physically robust global PPA benefits. Numeric acceptance bands are not
physical uncertainty bounds. All 720 pairs match decisions/outcomes at
six helper deadlines; maximum energy error is 0.022142% and maximum
recorded latency error is 9.631727 ps. Fresh a1 readings agree exactly
with the archived adopted-a1 population, rather than assuming version
or model equivalence.

## Portable evidence and offline audit

`publication-provenance.json` maps every original bounded/full45 source
archive member to a lossless public ZIP part or an explicit raw-model
reference. The original nested historical packaging snapshot is retained
byte-for-byte as a public member; its 1092 constituents also resolve to
public raw/native/model identities. It is not an additional experiment.
Actual decks, startup files, consoles/logs, metadata, geometry
and TSV/NPZ traces are byte-identical. Part names, member hashes and CRC
closure are checked; no LFS or oversized Git blob is used.
`model-references.json` reuses the existing 400-file raw-model manifest:
337 Windows CRLF variants and 63 canonical-byte-identical files at revision
`f62031a1be9aefe902d6d54cddd6f59b57627436`. Canonical LF bytes are not silently
substituted. No models are downloaded or normalized by the default reader.
Historical host paths in archived code/logs are provenance, not executable
dependencies; the reader resolves portable entry-relative paths only.

From the entry directory, with the already installed review requirements:

```text
python -B single_row_evidence.py
```

This reads every part/member and remeasures all 1504 saved bounded/full45
waves using the pinned published helper, without invoking SPICE or native
tools. Default Notebook execution displays verified saved-data tables,
geometry and matched traces. `analysis/` retains all four populations,
keyed transitions/nulls, limiting keys/exact ties, both energy estimators
and observed margins. Original execution receipts retain their truthful
pre-adoption private status; adoption is recorded separately in publication
provenance rather than rewriting executed science.

**Archived RC-deck outcomes; model physical fidelity not yet qualified**

Known-nonblind nominal code-zero finite45PVT only; not calibrated49, noise,
mismatch, trim, foundry Monte Carlo, continuous yield, silicon, independently
qualified PEX or signoff. Finite-grid maxima are not silicon worst cases.

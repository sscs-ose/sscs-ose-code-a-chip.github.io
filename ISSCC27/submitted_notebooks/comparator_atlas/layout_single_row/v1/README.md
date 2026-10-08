# Adopted area version: single-row-a1

**Archived RC-deck outcomes; model physical fidelity not yet qualified.**

The exact frozen candidate uses the original selected 27 guarded native PCells,
device WL/flavors/body/junctions, 15 ordered ports, pair order/mirroring/y and local
M1/M2 escape lengths. Pitch changes 4.8 to 4.5 um; necessary horizontal
bus/output/shield endpoints and symmetric spines follow placements. No diffusion
sharing, guard removal, rule waiver, electrical retuning or matching-benefit claim.

All nonempty GDS material, including wells/body/guards/shields, bounds the area;
TEXT only is excluded. Control: `[-64.8,-4.84,64.8,12.19]`, 129.6 x 17.03 um,
2207.088 um2. Candidate: `[-60.9,-4.84,60.9,12.19]`, 121.8 x 17.03 um,
2074.254 um2: **6.0185185% less bbox area** (not polygon-union or gate area).
The widest well is 2.96 um; the recorded 1.27 um rule plus 0.20 um safety
requires 4.43 um pitch, rounded outward to 4.5 um.

Canonical candidate:
- GDS SHA256 `6e7cf5a7c3d61cd1298dc340999b01e84e5ff4ff39a6694d8070cdfeeb047fff`
- MAG SHA256 `f05c4b0b2ce0d9747cde4d2eb84d2770e37190f3543358b3fcc8165a32b47896`
- Original generator SHA256 `ffa62dc441895c2fbcf5344e65313a36a8ca078676b519e6973e5a8152bbfa5f`
- Original spacing protocol SHA256 `4d1132535a0b6b52c925cce41d8dd37a00946fff3a6062914029be3e4ceaee1c`

`native-a1/` preserves the exact generator/protocol/PCells/MAG/GDS, assembly and
route Tcl, placement/envelope/route delta, full-style DRC, spacing negative,
independent positive LVS and connection/bulk/width/flavor negatives, junction
and material/passive/DC-anchor checks. **14 checks passed on one actual candidate
DRC attempt**, before the full45 round. Native proof did not rerun for full45
or publication. The original r1 control proof/extracts were hash-verified and
**reused, not rerun**. `native/control/` and `native/candidate/` contain the exact
netlists used by the new paired simulations. A native-log private-path redaction,
if present, is explicitly hash-linked; it is not new execution.

## New paired full45, not the historical control study

TT/SS/FF/SF/FS x 1.62/1.80/1.95 V x -40/27/125 C; signed -10/-3/+3/+10 mV,
both layouts, C and RC, 10/5 ps only: **1440 new successful transients, 720
qualified numerical pairs, 180 physical keys per layout/mode**, no extra
steps/reruns/not-run points. Same nominal skew zero, code zero, 5 fF outputs,
10 ns clock, 50 ps edges, 80/20% rails and full-cycle core energy (20-30 ns).
2 ns stays primary; 1 ns is a parallel readout of the same waves.

| Version/export | 1 ns correct/wrong/unresolved | 2 ns correct/wrong/unresolved |
|---|---:|---:|
| Control C | 168/0/12 | 180/0/0 |
| Candidate C | 170/0/10 | 180/0/0 |
| Control RC | 156/0/24 | 180/0/0 |
| Candidate RC | 156/0/24 | 180/0/0 |

The only changed classification keys are C, SS/1.62 V/-40 C, +/-10 mV:
unresolved to correct at 1 ns. RC retains exactly the same 24 unresolved keys.
No formerly correct point is lost. `analysis/keyed-layout-comparisons.csv`
retains every paired key/delta; unresolved latency stays null/empty, not zero.
The 1440-row finest CSV contains two deadlines per 720 saved finest traces,
not 1440 independent finest simulations.

| Population | Mean/max core energy fJ | Worst 2 ns latency ns | Minimum observed 2 ns margin ps |
|---|---:|---:|---:|
| Control C | 356.712016 / 495.729300 | 1.413853 | 586.146694 |
| Candidate C | 353.340125 / 491.158867 | 1.389035 | 610.965055 |
| Control RC | 425.490054 / 590.364633 | 1.835032 | 164.967533 |
| Candidate RC | 421.044730 / 584.441046 | 1.810632 | 189.368192 |

All four energy maxima are FF/1.95 V/125 C/-3 mV; worst timing is
FS/1.62 V/-40 C/-3 mV. All 180 matched energies and recorded primary latencies
decrease in each mode. Ratio-of-mean energy change: -0.94527% C / -1.04475% RC;
mean per-point change differs: -0.94950% / -1.04854%.
Ranges are -1.03594 to -0.83760% C, -1.13164 to -0.94353% RC.
Recorded timing changes are about -1 to -25 ps. These small changes are
**not robust global PPA/energy benefits**.

Unchanged numerical criteria: same decisions/outcomes, <=1% energy discrepancy,
<=20 ps recorded-latency discrepancy at the six same-wave helper deadlines.
All 720 pairs passed; maxima were 0.0175381284% and 9.7550445 ps.
Numerical acceptance bands are **not physical uncertainty bounds**.
Original control versus the preserved historical RC grid was actually matched
on 180 physical keys: identical outcomes at 1/2 ns, maximum numerical differences
2.56887e-9 fJ and 8.82105e-12 ns. Historical traces are not credited as new.
C-only has no historical public population and is not independent ground truth;
RC-minus-C does not isolate resistance.

This subsequent known-nonblind nominal code-zero grid is NOT calibrated
49-condition stress, noise/mismatch/trim validation or foundry Monte Carlo.
Core energy excludes drivers/controller/calibration. No silicon, independently
qualified PEX, signoff, yield, continuous-input or matching guarantee.
Earlier rejected two-row/pre-native failures remain retained privately; they
are not silently promoted, discarded or used as public successful evidence.

## Lossless public evidence and offline audit

`raw/traces-01.zip` through `traces-12.zip` contain **all 11,520 original raw
simulation members**: every executed deck, startup file, log/console, actual
geometry, metadata, TSV and NPZ waveform. Compression/partitioning is lossless;
member hashes link to the original private 11,950-member archive
SHA256 `3154792b43ab8000985ebcd46bdce82aaaffd0b09a424519f03fcc82cf786e09`.
No 251 MB Git blob, LFS or private-only raw dependency is required.
`publication-provenance.json` records exact partition bytes/member hashes and
the original private package-manifest hash. Public raw ZIP bytes total
**243,620,890**; source bootstrap consequently fetches about 244 MB more raw
evidence. Default reading hashes the partitions but does not inflate all traces.

`frozen-execution.json`, `pre-data-deck-plan.json`, `planned-physical-keys.json`,
`execution-index.json`, `execution-key-closure.json`, `execution-receipt.json`,
`numerical-audits.json` and `analysis/` preserve the actual protocol, 1440
pre-data deck hashes, original run identities, closure, 720 numerical receipts,
keyed transitions, limiting keys/ties and comparisons.
`evidence-sha256.json` closes these recorded inputs; entry checksums also cover
the reader/docs and generated presentation outputs.

From the entry root, using the existing pinned review stack:

```text
python -B -m single_row_evidence
```

This hash-checks evidence and remeasures all 1440 saved NPZ waveforms at their
recorded deadlines; **no simulator, model installation or network is invoked**.
Notebook tables/static figures/widgets use this version explicitly. Original
public MAG/GDS/netlists, full45 records and schematic selection remain untouched,
and `original-public-control-sha256.json` checks their original byte identities.

## Tool/source identities and optional future replay

Recorded simulation: existing Windows ngspice 47, Python 3.12.10, NumPy 2.2.6,
single worker/thread. Console SHA256
`22d5cae2bd32b2e39157a8d27bf457122f68285b72a9ebefdf41551b628233ab`.
The frozen execution pins measurement/deck/numerical/runtime helpers.
Recorded native tools: Magic 8.3.684 (4f53bb3), Netgen 1.5.323 (e1528a7),
open_pdks aa3fc21/sky130A 1.0.608; exact binary/PDK hashes are retained in
`native-a1/source-tool-pins.json`. No fresh tool identity or extraction date
is fabricated.

Models are referenced, not duplicated: `model-references.json` binds all 400
original bytes to the existing public model manifest and official revision
f62031a1be9aefe902d6d54cddd6f59b57627436. That manifest explicitly records
337 Windows CRLF variants and 63 byte-identical files, with canonical Git hashes.
Already available matching files can be placed at `model-source/` alongside
`simulations/` for separately authorized optional replay of the exact raw decks.
Do not silently substitute LF bytes or call them identical runtime evidence.
No automatic downloader/installer or simulator is run by this publication.

The exact original native generator uses CLI `--entry`, `--r1`, `--out`, `--tools`
and requires the retained r1 tool/control/PCell manifests; it is archived source,
not a claim that private absolute directories exist on reviewers' machines.
Canonical public native outputs and their checks are the authority. No generator
adaptation, new geometry generation or new physical qualification was performed.

Original code: MIT. Third-party model/tool licenses retain their notices.
GitHub Copilot assisted implementation, automation, figures and documentation;
the author is responsible.

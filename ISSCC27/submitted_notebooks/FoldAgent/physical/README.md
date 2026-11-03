# Joint timing inputs and scope

This appendix contains both accepted final STA netlists, local SDCs and extracted SPEFs, the top-level wrapper, and all three vertical-link SPEFs. Copies of the final compute-tier netlist and SPEF were checked byte-for-byte against the actual final analysis inputs before packaging.

The original run used **OpenSTA 3.1.0 f89887b596**, as recorded in evidence/final-joint-nominal.log. Supply the SKY130 HD TT 25°C 1.8 V Liberty file named in library-requirement.json; verify its SHA-256 before running. The library remains under its original distribution/license.

## Explicit analysis commands

From the package root, set the library to your local copy and select a new output directory:

```sh
export SKY130_TT_LIB=/absolute/path/to/sky130_fd_sc_hd__tt_025C_1v80.lib
export STA_OUTPUT="$PWD/build/joint-review"
mkdir -p "$STA_OUTPUT"
sta -exit physical/min.tcl > "$STA_OUTPUT/min.log" 2>&1
sta -exit physical/nominal.tcl > "$STA_OUTPUT/nominal.log" 2>&1
sta -exit physical/max.tcl > "$STA_OUTPUT/max.log" 2>&1
```

Original scripts are in original/. Portable scripts change input/output paths and add environment-variable setup. Their timing, electrical, annotation and path-class commands are otherwise exact copies. Their path substitutions were reversed and compared with the originals during packaging. The scripts request full electrical reports; examine command errors and all report categories alongside the printed slack values.

These scripts build the joint clock/IO constraints directly. Included tier-local SDCs document the implementation budgets; the joint run replaces internal tier budgets with the connected circuit. Local compute-tier hold = 2.448 ps and joint hold ≈ 83.600 ps refer to their respective constraint sets. All three cases use the same typical cell-library corner.

## What this appendix supports

In v4, all three scripts ran in the independent package extraction with the recorded OpenSTA binary and exact library. Setup/hold values match the archive; full electrical reports are byte-identical. Constraint diagnostics are empty, all six path classes are present, and the 556 reported unannotated drivers exactly match unloaded drivers (zero remaining unannotated loaded drivers). Results and logs are in ../portability/joint/.

Routing-tool patches are included under tool-patches/ with original provenance. Full place-and-route regeneration additionally needs the complete original flow, tool source/build environment, PDK and physical databases. These are tracked as remaining physical-rebuild packaging work. The manuscript's accepted results remain bound to the original frozen artifacts.

Fixed public dependency sources and build instructions: [DEPENDENCIES](../DEPENDENCIES.md).

## Final GDS views

Both final-layout GDS files and their DEF source copies are included in [gds/](gds/README.md). The compute GDS was exported from the frozen final DEF; the control GDS is copied unchanged from its freeze. Readback and images were added in v5. Independent GDS DRC/LVS remains future work.

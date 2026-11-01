# Shared PE arrays and block floorplans

Latest project decision (2026-10-22): the user rejected the whitespace of the
experimental exclusive-region tiling and stopped that approach. The current
shared-array project was explicitly saved back to **Mixed placement** at
20:20:03.903 JST. Its PE definition/2×2 instances and S01–S10 evidence are
retained. S11 is Not run for the newly saved physical input; no extra EDA/model
run or automatic re-adoption was performed. The old mixed/block passes and
versioned recipes remain as history. The block controls below document that
retained experimental feature, not the active project choice.

HuLLCirq can describe a two-dimensional instance array using one shared scalar
PE definition and assign its instances to placement regions on the same chip.
The existing mixed-placement mode remains selectable. These regions constrain
standard cells; they are not independently hardened macros.

GUI end-to-end validation of the new array project, from code generation
through S11 physical layout, **completed on 2026-10-22**. The
development ledger (historical development reference; not included in this curated archive)
records actual attempts, implementation interventions and their outcomes.
Software fixtures, draft previews and saved older results are not new layout
passes.

The separate shared-array project passed fresh mixed-placement and same-chip
block-region S11 runs. GUI debugging used **12 loops and 18 implementation
intervention packages (I1–I18)**. The final block run completed at 19:42:35.223 JST and
the explicitly authorized automation policy adopted it at 19:42:38.945 JST.
At that pre-withdrawal checkpoint the array project was 11/14 stages Complete;
S12–S14 are not qualified by this exercise. The latest mixed-mode configuration
and its 10/14 state are described above.

The three earlier region attempts remain failed: Loop 8 at the original grid
check, Loop 9 at hierarchy binding, and Loop 10 at clock-tree legalization.
Loop 11 used an explicitly saved 24 µm support-spacing plan with the same
frozen v2 recipe and passed. The executed v1 and v2 flows, runtimes, profiles,
failed inputs and results remain frozen rather than being relabelled.
A saved-input read-only diagnosis (historical development reference; not included in this curated archive)
identified bracket-escaped OpenDB instance names without writing the database
or rerunning synthesis, placement or routing. This diagnosis is not a layout
pass.

The final independent saved-output check (historical development reference; not included in this curated archive)
matched all 27 retained artifacts and reconstructed ownership, capacity,
containment and final DEF binding for 5,271 original mapped cells in 11 regions,
with zero owned cells outside their regions. The 265,547 other final cells
remain explicitly outside the claimed source-block ownership. This
read-only check is not an additional EDA execution.

Loop 12 exercised the saved **Block Placement** view: all four PE regions
(741 original mapped cells per PE) could be hidden and restored independently,
visibility could be changed from 5,271 cells to zero and back, and zoom,
scrolling and **Fit view** worked. Historical mixed placement showed
**Not available** without showing another run's geometry or changing
stage completion. Returning through earlier stages reused the cached view.
The new array retained 11/14 Complete, and the original project was separately
confirmed at 14/14 Complete. This loop added no model or EDA execution.

The GUI E2E includes development-assistant-authored RTL body examples in repair
prompts (G2 guidance), followed by local-model-generated saved candidates. This
is code-assisted debugging through the GUI, not evidence of autonomous model
correction.

## Create a separate shared PE project

1. Open the supported original eleven-node explicit-PE NPU system.
2. Open **Projects**, select **Create PE array variant**, enter a new project
   name, and confirm **Create separate project**. If the browser contains a
   draft, use the explicit preservation choices before continuing.
3. Inspect the new system in **02 Graph Editor** and **03 Specifications**.
   It has eight logical definitions and eleven block instances: seven single
   instances plus four members of one shared PE definition. The original matrix
   job and expected values are retained. The original project keeps its own
   generated sources, failures, reviews and adopted results; none of its
   acceptance is transferred to the new project.
4. Configure the execution environment and review policy through the GUI.
   Saving a policy requires the applicable explicit user authorization.
5. Run and review S01–S03, then explicitly preview and start S04 generation.
   Generate the PE as one scalar element with the saved scalar interface; S08
   integrates four instances of that module. S05–S07 inspect and verify each
   definition separately. Continue through S08–S10 using their saved sources
   and the original job before starting physical execution.

Changing tabs, selecting a node, viewing a result, editing a browser draft or
validating a draft preview does not save design files or start model or EDA
execution. **Save design** records an edit. Each **Run**, generation start,
retry or review action is separate and explicit. A failed execution environment
or an attempt without saved tool checks does not establish an RTL defect; use
the GUI same-RTL synthesis retry when offered, rather than regenerating nodes.

## Edit a shared definition and member connections

The node inspector provides **Definition mode**, **Array rows**, **Array
columns**, and **Apply instance shape to draft**. Rows and columns are integers
from 1 to 16. Applying a shape changes only the draft; **Save design** records
it. Shape changes that would invalidate existing edge endpoints or physical
targets are refused instead of deleting or remapping those references.

The graph shows one definition node with indexed member ports. Connection
selectors identify the member as well as its scalar port. Indices are zero
based: `[0,0]`, `[0,1]`, `[1,0]`, and `[1,1]` for a 2 × 2 array.

The following are schema fragments, not a complete importable design:

```json
{
  "id": "npu2-pe",
  "module_name": "hullcirq_npu2_pe",
  "instance_array": { "rows": 2, "columns": 2 }
}
```

```json
{
  "node_id": "npu2-pe",
  "port_id": "npu2-pe-pair_data",
  "instance_index": [1, 0]
}
```

The latter object is an edge endpoint. A scalar endpoint omits
`instance_index`. Ports remain scalar definitions shared by the members; the
array declaration does not turn the local PE module into a wrapper containing
four MAC elements.

The current finite NPU integration and original-job checkers support the exact
2 × 2 shared-PE profile. Structural editing of other array dimensions does not
make those designs functionally verified or executable by that finite adapter.
The verifier's independent eleven-instance contract projection is not generated
hardware or a replacement for the eight saved RTL definitions.

## Select mixed placement or block regions

Open **11 Layout → Block Floorplan**. The planning preview is separate from
the selected saved physical run.

- **Mixed placement** uses the existing style of placement without fixed block
  fences. Applying and saving this choice records `{"version":"mixed-v1"}`
  and selects the fresh mixed-placement profile for new execution. An older
  design with no `physical_design` field retains its historical configuration;
  merely viewing it does not migrate it.
- **Block regions** assigns every expanded block instance to exactly one
  region on one chip. A region may contain several instances, but an instance
  cannot belong to multiple regions. Apply the mode to the draft, set the core
  rectangle, and add or edit the region rectangles and targets.

**New tiling support spacing (µm)** is a browser-only helper for the next
explicit **Tile on 0.005 µm grid** action. Its new default is 24 µm, applied to
both the outer inset and gaps between tiles. The minimum is 6 µm; the entered
value must be finite and lie on the 0.005 µm grid. Changing this helper does not
edit the plan, mark the design as an unsaved draft, save files or start tools.
Saved 6 µm plans remain unchanged and readable.

**Tile on 0.005 µm grid** explicitly replaces the draft region list using the
chosen helper spacing. It divides the available area using integer
manufacturing-grid ticks, each exactly 0.005 µm. Tile dimensions are rounded
down in integer ticks; any unused remainder stays at the top and right. A
shared 2 × 2 array occupies adjacent 2 × 2 tiles, with row 0 at the top. The
exact rectangles are visible and editable. An undersized or off-grid core, or
invalid helper spacing, is rejected without changing the existing manual
region list. Wider support channels may leave more room for inserted clock or
support cells, but a spacing choice and valid draft geometry do not prove
capacity or successful legalization.

Manual core and region coordinates must also lie on the 0.005 µm grid. They
are never silently rounded, clipped or shifted. Off-grid input produces a
planning error and is refused by the current S11 start preflight; fix the
coordinates explicitly, validate again and save the new draft before retrying.
This input correction does not alter the frozen v1 execution recipe or the
earlier failed run.

Use **Validate draft preview** to inspect geometry and target coverage. Then
select **Save design**. Neither preview nor saving starts placement. Select
**Physical Layout → Run physical layout** explicitly when the saved sources
and trusted physical runtime are ready.

## Saved physical schema

`physical_design` is separate from Graph Editor coordinates in `layout`.
Its block-mode fields are:

| Field | Meaning |
| --- | --- |
| `version` | Exactly `block-regions-v1`. |
| `core_um` | `[x_min, y_min, x_max, y_max]` in micrometres. Coordinates must be finite and the rectangle must have positive area. Core minima are at least 10 µm; the GUI retains the legacy width and height minimum of greater than 12 µm. New tiling may require more room for the chosen helper spacing. Current planning and S11 start preflight require the 0.005 µm grid. |
| `regions` | Between 1 and 128 regions with unique safe identifiers. |
| `regions[].id` | A stable region identifier. |
| `regions[].rect_um` | A positive-area rectangle inside the requested core, on the 0.005 µm grid for current planning and execution. Regions must not overlap; touching boundaries are allowed by the saved schema. |
| `regions[].targets` | One or more exact block targets. Together the regions must cover every expanded instance exactly once. |
| Target `node_id` | The saved logical definition ID. |
| Target `instance_index` | Required `[row,column]` for an array member; omitted for a scalar instance. |

Graph drawing coordinates do not specify physical placement. A physical-only
mode or region edit preserves logical S01–S10 evidence while requiring the
affected S11–S14 physical chain to be saved and rerun. A PE definition, shape,
port or connectivity edit is a logical source change and has its corresponding
broader verification requirements. Old results remain in history.

## Versioned block execution

The saved planning schema remains `block-regions-v1`. New block-region runs use
the separate `hullcirq-sky130-block-regions-v2` execution profile; historical
inspection reconstructs each run with its own saved profile, not the newest
recipe. The original v1 runtime, flow, profile, failed inputs and results are
unchanged.

V2 records both the technology-mapped source hierarchy name and its exact
OpenDB name using a reversible, bracket-only encoding. Unknown escapes,
ambiguous mappings or missing original cells fail rather than receiving a
fuzzy match. Applying regions checks the original mapped masters. Final
verification retains each owned cell's identity and exact region membership,
checks containment, and binds the actual final master, position and orientation
to the final DEF. Ordinary cell sizing remains allowed; original mapped tie
cells additionally retain their original master and explicit protection.
Inserted support cells are reported separately without invented block ownership.

Selecting v2 is not a successful execution. The GUI must start a new physical
run, retain its frozen recipe and inspect its actual checks. Earlier v1 failures
are not reinterpreted as v2 results.

## Check the actual physical result

The draft SVG is a planning preview, not a placed layout or a Passed result.
Block-mode execution derives ownership from the actual technology-mapped
hierarchy, applies physical fences, and checks final DEF cell containment and
the complete target assignment. Unassigned ownership, inadequate region
capacity, incompatible snapped geometry or a cell outside its required region
must fail rather than being waived by the preview.

Inspect **Actual physical checks**, the exact saved run, and its block artifacts:
`block-input`, `block-plan`, `block-synthesis`, `block-ownership`,
`block-capacity`, `block-placement-proof`, `block-flow`, and `block-runtime`.
These records distinguish the saved plan from actual ownership and placement
proof. S12 DRC, S13 LVS and S14 post-layout verification remain separate stages;
the new array has not completed them. The original project's acceptance is not
transferred, and S11 alone does not establish their pass or foundry qualification.

## Inspect saved block placement

1. In **11 Layout**, select the saved, completed Passed block-region run under
   **Selected physical run**, then open **Block Placement**. The first explicit
   opening reads and validates that selected run's retained proof. It does not
   start placement, save a plan or adopt a result.
2. Toggle the region checkboxes, whose labels include their assigned block or
   indexed PE targets. **Show all regions** and **Hide all regions** change only
   visibility. A region containing multiple targets is shown or hidden as one
   region; the controls do not move or reassign cells.
3. Use **Zoom**, scroll within the view, and select **Fit view** to restore
   100% zoom and the initial scroll position. The rendered rectangles are the
   original owned cells' saved placement bounding boxes, not merely the planning
   rectangles or a new placement algorithm.
4. Open **Saved source binding and view limits** to inspect the selected run,
   plan and source hashes, cell counts and limitations. The view excludes the
   unclaimed final cells rather than assigning them inferred ownership.

Visibility and zoom are local presentation controls and send no additional
view requests. Returning to the same source-bound view can reuse its browser
snapshot. **Refresh read-only snapshot** explicitly rereads and validates the
saved artifacts. A cached snapshot does not establish currentness, adoption or
new verification. Mixed, failed or incomplete runs show an unavailable/error
message inside the view; no substitute geometry is displayed and circuit-stage
status is not changed by that view error.

Portable block-region export/replay is not implemented. These results describe
execution and retained evidence on the prepared host, not a portable
fresh-install replay.

**Block Placement** is distinct from **Functional Map**. Its ownership comes
from the retained mapped hierarchy and placement proof, not inferred role
labels. The existing Functional Map generator supports the original explicit-PE
source profile, not the new shared-array source profile. Do not borrow the
original map, its inferred role labels or its geometry as evidence for a new
array layout. The source-bound block ownership and placement records are the
relevant evidence for block-region execution.

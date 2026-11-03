# Generic digital projects in the GUI

Create a new digital design with your own module names, ports and saved cycle
expectations, then run its stages through the English GUI. The generic profile
does not select an NPU example or supply an integration algorithm.

The generic GUI E2E ledger (historical development reference; not included in this curated archive) is the
authority for actual execution, debugging loops and implementation intervention
times, including the current completion or failure status. The JSON below
illustrates the input contract; it is not a verified
circuit or a successful tool run.

The actual 2026-10-23 GUI demonstration completed a two-node, non-NPU byte
transform pipeline through S01–S14. Its final chain is Completed / Passed /
Accepted / Current, with 21 saved cycles, 63 expected output-pin samples and
zero required violations across all nine STA corners. See the
execution and debugging evidence (historical development reference; not included in this curated archive).
This is finite routed-netlist functional verification plus extracted STA within
the scope below, not dynamic SDF qualification or a guarantee for every design.

## Supported digital scope

Use one clock, a synchronous active-high or active-low reset, and synthesizable
Verilog-2005 with fixed-width input and output ports. The physical flow uses the
selected SKY130A PDK and `sky130_fd_sc_hd` library. Analog circuits, multiple
clock domains, arbitrary PDKs, bidirectional interfaces and general dynamic SDF
simulation are outside this profile.

Public module and signal names are plain Verilog identifiers, not keywords.
Generic integration supports 1–256 saved node definitions with distinct module
names and safe node IDs. For the complete flow, a node ID starts with a letter
or underscore, followed by letters, digits, underscores or hyphens, up to
96 characters total. Port widths are 1–4096 bits. Declared instance arrays have
1–16 rows and 1–16 columns; each element instantiates the same scalar definition.
Local verification checks that definition. S08 and S10 separately check that
the compiled system contains the declared number of instances and satisfies
the saved external-port expectations. They do not infer internal coverage from
an array declaration.

Cycle checks use finite saved vectors, not exhaustive or formal verification.
The clock period must be 0.004–1,000,000 ns in 0.002 ns increments. The generated
testbench drives inputs while the clock is low and samples every output after
each rising edge. Its sample offset is the smaller of 1 ns and one quarter of
the period, rounded down to an integer picosecond. The saved plan records the
period, offset and testbench hash. S14 retains that cycle timing and uses the
same clock constraint for separate extracted static timing analysis.
These samples alone do not distinguish synchronous from asynchronous reset
responses between clock edges. Review the generated reset implementation too;
do not infer exhaustive reset or handshake coverage from a passing finite trace.

## Create and save the design

1. Open **Projects → New project**. Enter a project name, system name and top
   module name. Keep the new project's default manual review policy unless you
   explicitly choose another adoption policy.
2. In **Global Settings**, select the clock/reset names, reset polarity,
   synchronous reset, clock period, Verilog-2005 and the selected SKY130 library.
3. In the graph and **Specifications**, add the node definitions, ports, edges,
   required behavior, reset behavior and test expectations. Give each module a
   distinct name. Use **valid / ready** streams or the GUI's declared raw
   sideband types; raw metadata still requires its associated stream.
4. If needed, set a node's row/column instance array and connect each indexed
   element explicitly. Reusing a definition does not copy another project's
   generated RTL, execution proof or adoption.
5. Enter the node and system contracts described below. Apply each JSON editor
   explicitly, then choose **Save design**. Run S01–S03 input, connectivity and
   specification checks, inspect their findings and review the current results.

Typing, loading a template, inspecting a stage or navigating between stages does
not save a design or start a tool. **Apply verification input** changes the
browser design draft; **Save design** freezes that input for execution. Unapplied
text must be applied or explicitly discarded before saving. Invalid text is
retained with its error, not silently substituted.

## Save independent node cycle expectations

In each node's **Node cycle vectors / structured verification JSON** editor,
choose **Load unfilled generic template** or enter a contract. Replace every
template `null` with an independently specified value, then choose **Apply
verification input**. The saved field is `node.verification`.

Each of the 2–10,000 cycle rows contains exactly:

- `reset`: logical assertion, integer `1` for asserted and `0` for released.
  The testbench converts it to the reset polarity in Global Settings. The first
  row must assert reset, and at least one later row must release it.
- `drive`: every physical input except clock/reset, with no extra names.
- `expect`: every physical output, with no omissions or extra names. This
  includes data even when its valid signal is zero, and all ready/valid controls.

At least one non-clock/reset input must change when such inputs exist. Empty,
reset-only, unknown, masked and don't-care expectations cannot establish a pass.
Expected values must come from your requirements or an independent calculation,
never from generated RTL or a DUT run used as its own golden reference.

For a stream named `input_data`, the physical pins include `input_data`,
`input_data_valid` and `input_data_ready`; the ready direction is opposite to
the data direction. Use these physical names in the contract.

This illustration assumes two unsigned 8-bit valid/ready ports named
`input_data` and `output_data`. The intended behavior is a one-entry elastic
incrementer: reset clears output data/valid; an accepted input produces
`(input_data + 1) mod 256`; an accepted output clears valid unless replaced by
a simultaneous accepted input; data otherwise holds. Input ready is
`!output_valid || output_data_ready`. These are example requirements, not an
executed implementation.

```json
{
  "kind": "generic_cycle_vectors",
  "version": 1,
  "cycles": [
    {
      "reset": 1,
      "drive": {"input_data": 0, "input_data_valid": 0, "output_data_ready": 0},
      "expect": {"input_data_ready": 1, "output_data": 0, "output_data_valid": 0}
    },
    {
      "reset": 0,
      "drive": {"input_data": 5, "input_data_valid": 1, "output_data_ready": 1},
      "expect": {"input_data_ready": 1, "output_data": 6, "output_data_valid": 1}
    },
    {
      "reset": 0,
      "drive": {"input_data": 255, "input_data_valid": 1, "output_data_ready": 1},
      "expect": {"input_data_ready": 1, "output_data": 0, "output_data_valid": 1}
    }
  ]
}
```

## Preserve exact integer values

Values must fit the declared unsigned or signed width. Signed values use the
signed range, rather than an unsigned spelling of the same bit pattern.
Use ordinary JSON integers within the browser's safe integer range. For wider
values, use canonical decimal strings such as `"18446744073709551615"` for an
unsigned 64-bit value or `"-9223372036854775808"` for a signed 64-bit value.
The backend checks them as exact integers and preserves their original saved
encoding in the contract and hashes.

Decimal strings allow no leading plus, spaces, leading zeroes or `-0`.
Fractions, scientific notation, Boolean values, `null`, X/Z and masks are not
cycle values. The editor rejects unsafe numeric JSON instead of rounding it.

## Declare system integration and verification

In **Specifications → Whole-system integration and verification**, first apply
**Top public interface and integration behavior JSON**. It saves
`design.global_integration`. Declare flat physical top pins, including any
ready/valid controls. Do not list clock/reset: the application adds those from
Global Settings.

For the single-node illustration above, the top could directly connect one
adopted scalar instance to the following external interface:

```json
{
  "public_ports": [
    {"name": "input_data", "direction": "input", "width": 8, "signed": false},
    {"name": "input_data_valid", "direction": "input", "width": 1, "signed": false},
    {"name": "input_data_ready", "direction": "output", "width": 1, "signed": false},
    {"name": "output_data", "direction": "output", "width": 8, "signed": false},
    {"name": "output_data_valid", "direction": "output", "width": 1, "signed": false},
    {"name": "output_data_ready", "direction": "input", "width": 1, "signed": false}
  ],
  "behavior": "Instantiate the adopted incrementer definition once. Connect its corresponding data, valid and ready pins directly to these public pins. Share the configured clock and synchronous reset. Preserve the adopted elastic incrementer behavior without duplicating its datapath."
}
```

Then apply **System cycle-vector verification JSON**, saved as
`design.global_verification`. It has the same `kind`, `version`, `cycles`,
`reset`, `drive` and `expect` schema as the node contract, but refers to the
top's physical ports. The direct single-instance illustration can use the same
cycle JSON above. A multi-stage or array system needs its own independent
external expectations, including its actual latency and reset requirements.
Finally choose **Save design**.

## Run and review the stages

Proceed only when the required current inputs and predecessor results are
accepted. In a manual-review project, a passed run initially needs review;
inspect its evidence and use its explicit acceptance button before continuing.

1. **S04 Node RTL Generation:** preview the saved node requirements, select the
   model profile in Global Settings and test its connection before explicitly
   generating. A supported model name does not mean it is installed locally.
   The GUI blocks model actions while the connection test is pending or its
   current result explicitly says the selected model is unavailable. Inspect interface checks and review
   each candidate. S04 acceptance is not a behavioral pass.
2. **S05 Local Synthesis:** synthesize each accepted candidate. Review the
   technology-independent netlist; this is not SKY130 mapping.
3. **S06 Local Netlist Simulation:** verify each exact accepted S05 netlist
   against the node's saved cycles. Every expected output must have a known,
   matching recorded sample. Review each current result.
4. **S07 Node Implementation Specs:** derive and review each specification from
   that exact S04–S06 chain. Its asserted trace and coverage describe the saved
   finite checks, not a measured waveform or universal behavior.
5. **S08 Global RTL Generation:** preview and generate integration RTL through
   the configured model. Verification checks the saved external expectations
   and actual elaborated instance counts. Review the current result.
6. **S09 Global Synthesis**, then **S10 Global Netlist Simulation:** synthesize
   the adopted integration and all adopted definitions, then check that exact
   whole netlist with the unchanged system cycle contract. Review each result.
7. **S11 Layout:** retain **Mixed placement**. Explicitly run placement/routing
   with the pinned toolchain, inspect the physical evidence and review it. A
   Functional Map does not replace this physical run or create layout regions.
8. **S12 DRC**, then **S13 LVS:** explicitly run and review each check on the
   adopted physical chain. Missing, unsupported or failed checks cannot advance
   the design as accepted results.
9. **S14 Post-layout Verification:** choose **Prepare fixed S14 profile** for
   the current accepted S11/S12/S13 chain. Preparation checks and saves the fixed
   profile but starts no EDA job. Then choose **Run post-layout verification**.
   Review the routed-netlist functional samples, extracted parasitics,
   constraints, setup/hold and electrical checks before **Accept verified
   post-layout run** becomes applicable.

After a new physical runtime or corrective layout, an installed S14 profile
may still be available but bound to the earlier physical chain. Once the new
S11 layout, S12 DRC and S13 LVS are current and accepted, explicitly choose
**Prepare fixed S14 profile** again. Preparation independently validates that
new adopted chain and updates its source-bound profile; it does not run or
adopt S14, change original expectations or overwrite earlier attempts. The
execution button stays blocked until the current profile and sources are ready.

S14 combines the unchanged finite external cycle test on the routed circuit
with extracted static timing checks. It does not claim dynamic SDF delay
simulation, formal equivalence, foundry signoff or fabrication readiness.

## Inspect a Functional Map

For an eligible current accepted S11, open **Functional Map**, refresh generation
availability if needed, then choose **Generate Functional Map**. If a map already
exists, **Generate new Functional Map (preserve current)** creates another
attempt and publication. **Refresh generation status** reads the saved outcome;
it does not resend a generation request.

Each map is registered to the exact saved S11 record and retained source/layout
hashes. Repeated definitions can have separate instance filters when retained
evidence supports their identification. Source confirmation, named-net or
connectivity inference, shared attribution and unknown cells remain distinct.
Missing usable synthesis attribution can produce an unknown-only view of the
verified final geometry; it cannot invent functional ownership. Map generation
starts no model, synthesis, placement or circuit adoption.

## Resolve missing contracts and failures

For a new generic project, an absent cycle contract is not replaced by an NPU
template. Return to Specifications, fill the appropriate independent node or
system expectations, explicitly Apply and Save, then follow the displayed
source prerequisites. An unfilled template is not executable evidence.

For an actual failure, inspect the saved tool console and first mismatch, record
the required correction and use the stage's explicit repair/retry controls.
Keep failed attempts and generated-source history. Do not weaken expectations
to match a faulty DUT. A genuine requirements change needs an explicit saved
revision and invalidates affected downstream evidence.

For recognized S13 MOS-capacitor terminal feedback, see the
versioned LVS extraction-correction guide (historical development reference; not included in this curated archive).
Its results ledger distinguishes implementation validation from actual runs.

### Correct an electrical-only S14 failure

If the completed generic S14 passes its other required checks but fails
electrical checks, choose **Prepare fixed physical correction**. This explicit
action preserves the failed attempt, original RTL, independent cycle values,
clock/reset and signoff constraints. It prepares a separately versioned,
source-bound generic closure profile; it starts no EDA and adopts nothing.

The GUI opens **S11 Layout** with a **Prepared generic physical closure** card.
Choose **Run physical layout** separately. This is a complete fresh synthesis,
technology mapping, placement, clock-tree, routing and closure run, not reuse
of an old NPU checkpoint. All nine corners must have zero required slew,
capacitance and fanout violations. This is a bounded correction attempt, not
a promise that every circuit closes.

Review and adopt the new S11 only if its required checks pass. Then run and
review new S12 DRC and S13 LVS, prepare S14 for that new source chain and run
S14 again. Previous physical evidence becomes historical because you explicitly
changed the execution profile, not because you viewed a tab. Its original
records, warnings and failed attempts remain inspectable.

Generic closure v1 retains the exact first correction of a fresh **Mixed placement**
layout. Separately versioned v2 now supports explicitly preparing further
corrections after complete current electrical-only S11 or S14 failures. It
retains the original RTL, expectations and signoff checks, lowers recorded core
utilization by five percentage points (minimum 10%), and always performs fresh
mapping/routing. It never resumes a checkpoint or retries automatically.
See [repeated generic correction and reconnect](generic_physical_retry.md).
Block-region fences remain rejected rather than silently removed. Historical
fixed NPU correction versions remain independent. Do not substitute an NPU
retry or relax checks when a correction is ineligible or still fails.

Historical projects keep their existing versioned NPU contracts, templates and
maps unless explicitly changed. Opening an earlier result does not convert it
to this generic profile or make it current for another input. After an uncertain
request outcome, refresh saved results before retrying; do not automatically
resend execution or adoption requests.

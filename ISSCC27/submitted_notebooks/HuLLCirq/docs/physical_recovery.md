# Diagnose and correct S11–S14 through the GUI

Open the latest saved result in **Layout**, **DRC**, **LVS** or **Post-layout
Verification**. Inspect its required checks, diagnostics, source identities and
raw reports. In **Review results → Diagnose and return for correction**, select
a cause hypothesis and enter the evidence and requested correction.

| Evidence points to | Select | Next operation |
|---|---|---|
| Node behavior or implementation | **S04 node RTL**, then the definition | Prepare handoff, inspect saved instruction, Open correction target, Context Preview, explicitly request repaired RTL |
| Integration wiring | **S08 integration RTL** | Same explicit preview and model-request sequence |
| Placement, routing or electrical limits | **S11 physical implementation** | Inspect physical configuration and available source-bound physical correction profile; run separately |
| Extraction/model recognition or comparison setup | **S13 extraction / comparison setup** | Inspect the supported extraction correction profile; Prepare and Run are separate |
| Runtime, unavailable proof, unsupported check or uncertain cause | **Environment / runtime / insufficient evidence** | Inspect environment configuration and original reports before changing circuit RTL |

The cause selection is an operator hypothesis. A physical mismatch does not
automatically identify its RTL owner. **Prepare diagnostic handoff** saves only
an immutable diagnostic record. Editing fields or opening stages does not save
it. **Inspect exact saved repair instruction and source binding** shows exactly
what enters the repair instruction. **Open correction target** validates the
binding again and fills an unsent RTL repair draft where applicable. It starts
no model or EDA process and records no acceptance or rejection.

The instruction preserves original specifications, public interfaces, clock/reset,
independent expected values and history. The server checks the saved project,
system, revision, diagnostic execution and selected RTL candidate again at both
preview and start. Changed or stale inputs require a new handoff. Changes to an
instruction retaining its handoff header are rejected; prepare a new handoff
with explicit feedback. The existing independent manual-repair workflow remains
available; removing that header returns to manual instruction semantics and
does not represent a validated diagnostic handoff.
The normal preview budget still applies; exceeding it does not truncate evidence
or automatically send a request. Complete original reports remain on the source
stage. The diagnostic projection itself has a22000-byte bound and refuses larger
contexts explicitly; that is a current limitation, not universal diagnosis support.

**Load saved diagnostic handoffs** reads earlier records without updating files.
Saved records remain inspectable; opening their target still requires current
matching inputs. After any RTL repair, explicitly run and review the affected
synthesis, netlist simulation, implementation specifications, integration and
physical stages. Existing freshness rules prevent old downstream results from
becoming current evidence for changed RTL. No automatic retry or adoption is added.

For the supported SKY130 MOSCAP terminal warning, a completed Passed **never
reviewed** original v2 result may prepare direct v7 without first accepting the
warning. S11/S12 must remain accepted. A new immutable pending-source schema
preserves that unreviewed original. Historical accepted-source and failed-version
upgrade bundles keep their original interpretation. Preparation is not proof of
resolution: inspect a fresh S13 execution with zero feedback and positive model
recognition proof before review. See MOSCAP correction (historical development reference; not included in this curated archive).

S14 supports the pinned legacy and host-bound fresh public compiler installations;
the identical package checksum and full extracted inventory remain mandatory.
Its implemented method is routed-netlist functional verification plus extracted
nine-corner STA. Dynamic SDF simulation remains unsupported and is not implied
by a Passed result.

See the P1 verification ledger (historical development reference; not included in this curated archive)
for actual GUI results, loop counts, intervention times and remaining coverage.

"""Build the review notebook from these authored HTML sections; no experiments."""
from pathlib import Path
import json,re
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]
cells=[]
def prose(text):
    # Keep source paths and code identifiers stable; reader-facing names describe function.
    parts=re.split(r"(<[^>]+>)",text.strip())
    for i in range(0,len(parts),2):
        for old,new in [("L0","control & storage tier"),("L1","compute tier"),("P0","two-tier design")]:
            parts[i]=re.sub(r"\b"+old+r"\b",new,parts[i])
    cells.append(nbf.v4.new_markdown_cell("".join(parts)))
def code(text):cells.append(nbf.v4.new_code_cell(text.strip()))
def figure(name,caption):
    prose('<figure id="figure-'+str(int(name[:2]))+'"><img src="figures/'+name+'.png" alt="'+caption+'"><figcaption>'+caption+'</figcaption></figure>')
prose("""
<h1>FoldAgent: Agent-Assisted Logic Folding with Automated Verification</h1>
<p><strong>Openly licensed edition · 31 October 2026</strong><br>
Zhanchen Zhao, Wenyu Sun, Yaqing Lai, Yubo Deng<br>Tsinghua University (all authors)<br>Conference representative: Zhanchen Zhao.</p>
<p><em>An agent-assisted SKY130 design case: generate partitioned RTL, check the service contract automatically, and follow physical feedback to closure.</em></p>\n<p><strong>Reading route:</strong> <a href="#figure-1">choose the cut</a> → <a href="#connection-exercise">predict the connection budget</a> → <a href="#figure-4">understand the local repair</a> → <a href="#figure-6">trace the round trip</a>. Use <a href="#figure-5">the timing window</a> to interpret arrival margins.</p>\n<h2>Abstract</h2>
<p>FoldAgent connects agent-assisted RTL partitioning to automated circuit checks in a worked two-tier INT8 design. With projected footprint fixed at 1 mm² and a second 1 mm² logic tier added, this signed INT8 design case preserves cycle-level supply and completion throughput across 162 paired scenarios. To retain the original schedule, its chosen cut uses <strong>725 functional cross-tier connections and a same-cycle control → compute → storage round trip</strong>.</p>
<p>Preserving that schedule creates concrete physical work: protecting fixed endpoints, routing terminal access, managing antenna-diode loading and timing the connected circuit with propagated clocks. We trace these obligations through measured repairs and joint analysis at a 100 ns clock, using a TT library corner and three assumed vertical-RC models. The contribution is a reproducible engineering teaching case connecting a specific service contract to its communication and closure costs, within the stated footprint and interconnect assumptions.</p>
""")
prose("""
<h2>1. Why split the logic?</h2>
<p>The starting point is a reduced compute block attached to eight useful memory channels, with two spare interfaces for static repair. Its footprint is constrained to 1 mm². Memory-interface regions, supply structures and vertical connection keepouts consume placement and routing resources inside that footprint.
The design must retain its parallel arithmetic and buffering: reducing those resources would change the service delivered by the block.</p>
<p>Logic folding gives these resources a second 1 mm² tier. The projected footprint stays at 1 mm² and total logic silicon becomes 2 mm². This creates a useful engineering question: <strong>can we preserve the cycle-level service of the original block while closing the resulting cross-tier circuit?</strong> Here, “folding” means a structural partition of one RTL block into two physical logic dies.</p>
<p>Existing work provides open 3D backend flows, including <a href="https://github.com/lamda-bbo/Open3DBench">Open3DBench</a>. Bonding-terminal legalization is also an established physical-design problem; <a href="https://research.nvidia.com/publication/2023-03_legalization-die-bonding-bumps-and-pads-3d-ics">Pentapati et al.</a> study width and spacing constraints at these interfaces.
Our case combines an explicit memory-service contract, a fixed semantic cut and a source-bound path from functional comparison to two-tier electrical acceptance.</p>
<p>The 1 mm² footprint is an imposed design condition in this case. The comparison establishes preserved service across the chosen split and a two-tier implementation under the stated checks. A fair physical comparison would also close the same-resource single-tier design at 1 mm² and an equal-total-silicon single-tier design at 2 mm² with matching interfaces, clocks and workloads. These baselines, final ECO area and activity-based energy are the next measurements for assessing a stacking advantage.</p>
""")
prose("""
<h2>2. A circuit with an explicit service contract</h2>
<p>Each job computes eight signed outputs:
<strong>Y[j] = Σ X[i] × W[i,j]</strong>, with j = 0…7 and K = 4, 16 or 64.
Inputs and weights are signed 8-bit integers; accumulation uses signed 32-bit values.
One tile consumes four input values and an eight-lane weight row, using 32 products.
Eight independent memory interfaces may respond at different times. A four-row queue retains partial responses, while input and output ping-pong banks allow overlap between preparation, computation and consumption.</p>
<p><strong>Read by function:</strong> blue identifies the control &amp; storage tier; amber identifies the compute tier. Follow the data down to the arithmetic and back up to the output buffer in Figure 1.</p>\n<p>The L0 owns configuration, memory requests and responses, the four weight rows, input/output banks, and job/consume control. The L1 owns all products, reductions and accumulator state. The 352 bytes comprise 128 bytes of inputs, 128 bytes of weight rows, 64 bytes of output banks and 32 bytes of accumulators. Metadata and added physical buffers are accounted separately.</p>
<p>The split preserves the original external protocol. Host pins enter through the L1 and pass to the L0; the memory-side ports remain on the L0. Clock and reset follow explicit physical paths. The last tile returns the combinational next sum to the L0 in the same logical cycle, which preserves the original completion schedule and creates a real round-trip timing path.</p>
""")
figure("01-architecture","Figure 1. The actual RTL ownership and communication widths, shown schematically. The external memory service is modeled; the two logic dies are implemented.")
code("""
from pathlib import Path
import json
import review
assert Path("sources.json").is_file(), "Open this notebook from the package directory."
checks = review.verify()
print(json.dumps(checks, indent=2))
""")
prose("""

<h3>Why choose this boundary?</h3>
<p>The experiment fixes the arithmetic concurrency, payload capacity, host-facing control location and cycle-level service contract. Within those conditions, this cut keeps the state that coordinates memory responses together and moves each complete arithmetic lane with its accumulator. The following rationale follows the implemented RTL and the fixed contract; alternative partitions are design options for later measurement.</p>
<table>
<tr><th>Decision</th><th>Why it fits this circuit</th><th>Physical obligation / alternative</th></tr>
<tr><td>Keep the four-row weight queue beside memory control</td><td>Eight lanes can return independently. The queue retains partial rows; row-valid bits, outstanding requests and consume state jointly decide when all eight lanes are ready. Keeping them together retains one reservation and consumption rule.</td><td>Send the selected 256-bit weight row to computation. Moving the queue would also require distributing response identity, valid state and reservation ownership across the boundary.</td></tr>
<tr><td>Keep accumulators with the arithmetic</td><td>Each of eight 32-bit accumulators feeds the next sum on every consumed tile. Placing the state beside its adder keeps the recurrence within the compute tier.</td><td>Return eight next sums to the output banks. Keeping accumulator state on the control tier would move the recurrence feedback across the boundary and require another timing/traffic design.</td></tr>
<tr><td>Return the 256-bit next sum without another pipeline register</td><td>The last tile writes the output bank at the original completion point. This preserves the existing cycle contract and gives a direct paired comparison.</td><td>Accept a combinational round trip and verify it with propagated clocks. A registered link could ease a timing segment, while requiring a revised capture schedule, control and buffering; its throughput needs measurement.</td></tr>
<tr><td>Retain host control above package-facing ports</td><td>The pilot specification fixes host-facing command/configuration and output ordering on the control tier; package ports enter at the compute tier.</td><td>Budget 179 host feedthrough bits: 24.7% of all functional connections. Changing this ownership is a separate partition experiment.</td></tr>
</table>
<p>This choice spends <strong>725 of 784 functional sites (92.5%)</strong> to retain the original service schedule. Its value as a design example is the visible exchange: simple ownership and unchanged cycles create a wide interface and a measurable timing obligation.</p>

<h3>Count the physical cut before routing it</h3>
<p>Moving all eight output channels requires 290 forward compute bits (32 input bits, 256 weight bits and two controls), 256 return bits and 179 functional host feedthrough bits: <strong>725 functional links</strong>.
Clock and reset add two more signal terminals. Each functional link uses real SKY130 transmit and receive buffers; their area and pin capacitance enter implementation and timing.</p>
<p>The proxy geometry contains four 200 × 200 µm windows at 10 µm pitch. Of 1,600 candidate positions, 800 are allocated to supply and 16 to utility, leaving 784 functional positions. The selected cut uses about 92.5% of this capacity.
The calculation below screens connection count; the implemented and measured case is eight moved channels at 10 µm pitch.</p>
<h3 id="connection-exercise">Try a design decision: predict, run, explain</h3>
<p><strong>Before running:</strong> increase pitch from 10 to 12.5 µm while keeping the four windows and supply/utility allocation rules fixed. Predict whether the original eight-channel cut still fits. If it overflows, would moving only four channels be enough for the connection budget? Write down your prediction, then run the unchanged calculation below.</p>
<p><strong>What stays fixed?</strong> The 179 host feedthrough bits, 32 input bits and two controls remain; each moved channel adds 32 weight bits and 32 return bits. The parameter <code>moved_channels</code> counts arithmetic channels moved across the boundary.</p>
""")
code("""
import math
def connection_budget(pitch_um, moved_channels):
    assert math.isfinite(pitch_um) and pitch_um > 0
    assert isinstance(moved_channels, int) and 1 <= moved_channels <= 8
    slots = 4 * math.floor(200 / pitch_um) ** 2
    available = slots - math.ceil(slots / 2) - 16
    required = 179 + 32 + 2 + 64 * moved_channels
    return {"pitch_um": pitch_um, "channels": moved_channels,
            "available": available, "required": required, "fits": required <= available}

assert connection_budget(10, 8)["available"] == 784
assert connection_budget(10, 8)["required"] == 725
assert connection_budget(12.5, 8)["available"] == 496
assert connection_budget(12.5, 4)["required"] == 469
for pitch, channels in [(10, 8), (12.5, 8), (12.5, 4)]:
    print(connection_budget(pitch, channels))
""")
prose("""
<section class="teaching-explanation"><h3>After running: explain the design decision</h3>
<p><strong>Interface capacity:</strong> at 12.5 µm pitch, 496 functional sites remain. The eight-channel cut needs 725, exceeding capacity by 229; moving four channels needs 469 and leaves 27 spare sites.</p>
<p><strong>Compute resources:</strong> an eight-channel circuit with only four channels moved would need a location, state ownership and schedule for the other four. Reducing the whole circuit to four channels instead changes its arithmetic concurrency. The count model leaves those implementation decisions open.</p>
<p><strong>Throughput evidence:</strong> the measured 162-scenario result belongs to the implemented eight-channel cut at 10 µm pitch. A revised cut needs its own RTL, control/buffering design and the same paired performance check. The four-channel case here is an analytical budget exercise; implementation and performance measurement remain future work.</p>
<p><strong>Your conclusion:</strong> name the budget that passed and the design/measurement work still required before selecting the four-channel alternative.</p>
</section>
<h2>3. Agent assistance, automated checks and physical feedback</h2>
<p>The supplied reference RTL and fixed split specification define the design task. The recorded workflow contains a planning-agent session and one RTL implementation attempt. Automated checkers then measure the candidate against the circuit contract. Later electrical closure combines tool reports, targeted backend edits and an isolated tool repair, under the documented author approvals.</p>
<table>
<tr><th>Stage and responsibility</th><th>Input → output</th><th>Evidence in this case</th></tr>
<tr><td>Designers fix the contract</td><td>Reference circuit and footprint/interface constraints → semantic cut, resource and cycle requirements</td><td>Packaged contract, folding specification and reference RTL</td></tr>
<tr><td>Agents plan and implement</td><td>Reference RTL and split specification → a partitioned RTL candidate</td><td><a href="evidence/historical-P0-report-data.json">Historical session record</a>, <a href="evidence/agent/rtl-attempt.json">attempt and delivery identity</a>, and <a href="design/rtl/lb_feedback.sv">delivered RTL</a></td></tr>
<tr><td>Automated checkers accept or reject</td><td>Candidate, fixed stimulus and reference → arithmetic/protocol/resource checks and paired throughput records</td><td>162 matched workload pairs plus negative controls; the packaged entry reproduces the measurements</td></tr>
<tr><td>Engineering feedback closes the physical circuit</td><td>Endpoint, routing, antenna and electrical reports → targeted repairs, frozen layouts and joint analysis</td><td>The local fixes in Figure 4 and propagated-clock round trip in Figure 6</td></tr>
</table>
<h3>Follow one recorded agent decision</h3>
<p>The semantic cut was supplied by the designers. The <a href="evidence/agent/rtl-intent.txt">saved task input</a> requires “No additional pipeline, serialization or reduced MACs.” The <a href="evidence/agent/task-briefs.json">planner's nine frozen task briefs</a> carry that contract into explicit responsibilities, completion criteria and downstream checking. The <a href="evidence/agent/physical-change.md">implementation output</a> explains the resulting choice: return the combinational accumulator-plus-tile sum so that the control tier stores the last result in the original cycle.</p>
<p>The <a href="evidence/agent/recipe.yaml">historical configuration</a> selects model identifier <code>gpt-6.1-sol</code>; the RTL attempt records medium reasoning effort. Its implementation note records two local RTL revisions inside one workflow attempt: an Icarus elaboration error from unpacked-array forward references was resolved by moving the cut assignments below the declarations. The delivered RTL matches the packaged measured RTL byte for byte. The <a href="evidence/agent/README.md">agent evidence guide</a> links the inputs, saved decisions and output identities.</p>
<p><strong>What readers can rerun:</strong> the Notebook checks saved evidence, evaluates the connection budget and redraws figures; the optional entries run paired RTL measurement and joint timing. Historical generation is inspectable through configuration, task intent, frozen briefs and output records. Recreating that generation requires the original orchestration runtime, full assembled prompts/conversation and model access, which are outside this package. This single recorded design trajectory supports the case study; agent success-rate and efficiency comparisons remain future work.</p>
<table>
<tr><th>Item</th><th>Condition</th></tr>
<tr><td>Cell technology</td><td>SKY130 HD, TT, 25°C, 1.8 V</td></tr>
<tr><td>Clock</td><td>100 ns period, 1 ns uncertainty; propagated clocks in joint analysis</td></tr>
<tr><td>Physical geometry</td><td>L0 and L1 each 1 × 1 mm; fixed cross-tier endpoints</td></tr>
<tr><td>Final placement-density targets</td><td>L0: 0.40; L1: 0.55</td></tr>\n<tr><td>L0 additional MC blockages</td><td>20% cell blockage, 0% additional metal blockage, 5% necessary inner region, following the approved geometry relaxation</td></tr>
<tr><td>Routing</td><td>Seed 11, four threads; final package M4 access window 2.8 µm</td></tr>
<tr><td>Vertical link models</td><td>0.25 Ω / 15 fF; 0.5 Ω / 50 fF; 1 Ω / 100 fF</td></tr>
<tr><td>Tools</td><td>Icarus Verilog, Yosys, OpenROAD/OpenRCX and OpenSTA; exact historical identities retained with evidence</td></tr>
</table>
<p>Vertical capacitance is represented by a π model split between the two terminals. Extracted local wires and library pin capacitance are included separately. The inter-tier models and package feedthroughs are research assumptions, and the model parameters are explicit in the supplied folding specification.</p>
<p>Implementation proceeded through independent tier flows, actual endpoint comparison, extracted netlist/SPEF assembly, and joint timing and electrical checks. A local OpenROAD repair addressed BPin taper handling and cross-layer width reading; the accepted binary identity and patch provenance are retained in the original experiment archive. A future clean-room physical rebuild needs that exact tool revision and the complete flow dependencies.</p>
""")
code("""
review.architecture()
review.placement()
review.gds_layout()
print("Rebuilt Figures 1–2 from the documented split and saved GDS views; retained the DEF-derived placement map.")
print("Paired final signal pin origins:", checks["endpoint_pairs"])
print("Supply pin positions per die:", checks["power_pins_each"])
""")
figure("02-gds-layout","Figure 2. Read the top row first: final control/storage and compute GDS views share scale and orientation. The four dashed rectangles on each tier mark the 200 × 200 µm interface windows; A and B identify the magnified regions below. A shows a 50 × 50 µm part of a terminal window. B shows an 8 × 8 µm diode-access region near the compute-tier bottom edge, connecting the final geometry to the repair in Figure 4. Overview/A display metal 1–5 and vias; B adds local-interconnect and device geometry with metal 1–2. Scale bars and labels overlay unchanged KLayout pixels. Both final GDS files and readback records are included.")
prose("""
<p><strong>Two complementary views:</strong> Figure 2 shows the routed geometry. Open the <a href="figures/02-placement.png">saved placement overview (legacy Figure 2)</a> to see component origins, signal pins and supply pins with less visual clutter. It complements the functional ownership in Figure 1; the four window outlines locate the same interface regions.</p>
<h2>4. Does folding preserve the memory-fed computation?</h2>
<p>The performance comparison uses identical fixed stimulus schedules for the reference and P0. Its 162 scenarios are the Cartesian product of three K values, three repair mappings, three random seeds, three service-delay profiles and two output-backpressure settings.
Each scenario measures 1,000 steady completion/service intervals after 100 warmup jobs. We compare cases by their full scenario key, retaining the useful-byte count and both measured cycle totals.</p>
<p>For a fixed useful-byte count, the supply-throughput ratio is the reference supply-cycle count divided by the P0's count. The completion-throughput ratio uses the same relationship for completed jobs.
Fast service accepts requests continuously and responds the next cycle. Jitter uses fixed per-lane request-ready schedules and ordered response delays of 1–7 cycles. Burst service collects up to four rows before releasing responses, with a 16-cycle timeout flush. The stalled output consumer is unavailable for the first three of every eleven cycles. Figure 3 groups the same 162 paired records by these conditions.</p>
<p><strong>Why can the shorter job take longer?</strong> Under burst service, K = 4 issues one row request per lane, so a job waits for the 16-cycle timeout that releases a partial batch. K = 16 supplies four row requests per lane and triggers the batch release by occupancy. This service-policy effect yields 20 versus 10 cycles/job in both designs. The response model, rather than arithmetic work alone, determines the completion interval here.</p>
<p>All 162 ratios are exactly 1.000. The recorded maximum-latency differences are also zero in every paired scenario. This follows the intended cut: arithmetic concurrency, row buffering and the consume schedule are preserved, with no additional pipeline boundary.</p>
""")
code("""
pairs = review.compare_performance(review.read("evidence/reference-performance.json"),
                                  review.read("evidence/P0-performance.json"))
assert all(p["completion_ratio"] == p["supply_ratio"] == 1 for p in pairs)
assert all(p["latency_delta_cycles"] == 0 for p in pairs)
review.performance()
print("Matched scenarios:", len(pairs), "| completion and supply ratios: 1.000")
print("Maximum recorded latency difference: 0 cycles")
""")
figure("03-performance","Figure 3. Coverage by job length, memory service and output backpressure. Every cell summarizes nine scenario pairs (three repair mappings × three seeds): the mean completion interval and its range. Each of all 162 individual supply and completion ratios is 1.000. Both designs share the displayed interval values.")
prose("""
<p>Arithmetic and protocol acceptance also includes signed data, repair mapping, output backpressure, reset and error propagation. The final netlist evidence reuses 44 positive joint functional tasks plus an erroneous-data negative control, after checking functional-cell models and connections against the actually simulated reference. That step bridges backend changes to previously exercised behavior.</p>
<h2>5. What made physical closure difficult?</h2>
<p>A successful semantic split still leaves the physical designer with fixed terminals and real loading.
Three implementation decisions mattered in this case. Read Figure 4 from conflict to relocation, then Figure 4b for measured coordinates and Figure 2B for the resulting GDS geometry. The 200 × 200 µm cross-tier windows in Figure 2 set connection capacity; the 2.8 µm M4 access window below describes local package-pin access.</p>
<p><strong>Protect the physical interface throughout repair.</strong> The endpoint cells keep their identity, location and signal connection. Internal buffering and sizing absorb electrical changes on the logic side. Explicit location/status checks were needed because logical protection alone did not prevent an earlier placement step from moving endpoints; the affected historical candidates remain recorded as invalid.</p>
<p><strong>Treat terminal access as a route.</strong> The L1 package-pin failures concentrated near a constrained bottom-edge strip. A rule-based change increased the internal M4 access window from 2.0 to 2.8 µm while retaining the M5 pin. Local access still required routing around surrounding blocked and supply geometry. The final accepted condition keeps that 2.8 µm window.</p>
<p><strong>Repair antenna loading and geometry together.</strong> Added diodes protect routed nets but introduce terminals, capacitance and potential local conflicts. In the final local repair, two newly added diodes moved 8.16 µm upward to sites that meet existing same-net M1 routing. Their old conflicting branches were removed. The scope audit found only one signal route changed in that step; the other 18,205 signal routes and all original port definitions were preserved.</p>
""")
code("""
moves = review.read("data/diode-move.json")
for name, m in moves.items():
    assert abs(m["after_um"][1] - m["before_um"][1] - 8.16) < 1e-9
    print(name, m["before_um"], "→", m["after_um"])
review.repair()
""")
figure("04-local-repair","Figure 4. Follow the cause and repair from left to right: an added diode contact conflicts with neighboring metal; relocating the two diodes provides access to the existing signal wire. The drawing explains the mechanism at schematic scale. The measured move is +8.16 µm, and the final complete routing and antenna checks both report zero violations. Exact coordinates and the final route for link_out_data[46] are in the evidence.")
prose("""
<figure id="figure-4-detail"><img src="figures/04-route-detail.png" alt="Measured route centerlines and diode access shapes"><figcaption>Figure 4b. Actual coordinates from the accepted repair: met1/met2 centerlines on host-output net link_out_data[46] and the two diode access shapes. Old and final component origins show the +8.16 µm move. The right panel magnifies access to the same met1 route at y = 37.570 µm. This view displays the selected net and recorded diode metal; neighboring nets and the remaining mask layers are omitted.</figcaption></figure>
""")
prose("""
<p>The accepted L1 has zero complete native DRC, antenna, slew, capacitance and fanout violations. Placement legality and VDD/VSS checks pass.
Extraction preserves the routed metal geometry on all 18,206 signal nets. All SPEF resistance graphs are connected, and the final changed-net physical terminal checks pass.
A standalone exported-netlist check agrees with the database across 64,810 per-pin slew/capacitance checks, with matching violation status.</p>
<p>These results support a useful practical rule: after adding electrical fixes, revisit the local route and then recheck the complete design. The last two diode moves illustrate how a small, geometry-driven change can complete closure while retaining the interface and computation.</p>
<h2>6. Does the complete circuit meet its timing window?</h2>\n<p>A receiving register needs a stable input around its clock edge. <strong>Setup</strong> checks whether the intended value arrives before the latest allowed time. <strong>Hold</strong> checks whether the next change stays after the earliest allowed time. The distance to each boundary is the timing margin, or slack; a positive value passes that check. Figure 5 first sketches this window, then shows the measured worst margins.</p>
<p>Per-tier implementation uses temporary cross-tier I/O budgets. Joint analysis replaces those internal budgets with actual connected tier netlists, their extracted parasitics and the assumed vertical links. It retains the true external constraints, propagated clock networks and 1 ns uncertainty.
Checks include same-tier, control → compute, compute → control and existing round-trip path classes, plus parasitic annotation and constraint coverage.</p>
<p>To test sensitivity to the vertical connection, we use light, nominal and heavy link models. Resistance (R) and capacitance (C) set the modeled interconnect loading; all three use the same typical transistor library. All three joint scenarios pass setup, hold and electrical checks. From the minimum to maximum RC scenario, worst setup slack decreases by about 0.694 ns, from 53.894 to 53.200 ns.
Joint worst hold slack stays near 83.600 ps. The local hold check on the L1 has a 2.448 ps margin with its temporary implementation I/O budgets (25 ns maximum and 0 ns minimum at the internal boundary). Joint analysis removes these internal budgets and times the connected circuit and propagated clock paths, giving a different worst-path population and 83.600 ps worst hold margin. Both checks pass their own constraint sets. Process, voltage and temperature sweeps are the next robustness study; all reported results here use the typical library corner.</p>
""")
code("""
accepted = review.read("evidence/L1-acceptance.json")
for name in ["min", "nominal", "max"]:
    c = accepted["joint"]["cases"][name]
    print(f'{name:7s} setup={c["setup_ns"]:.6f} ns   hold={c["hold_ns"]*1000:.6f} ps')
print("Compute-tier local hold:", checks["hold_ps"], "ps")
review.joint()
review.path()
""")
figure("05-joint-timing","Figure 5. Green markers sit on the passing side of the zero-margin boundary for every link model. Setup margins are in nanoseconds (ns); hold margins are in picoseconds (ps), with 1,000 ps per ns. The amber callout identifies the small compute-tier local hold margin as the next robustness study. The conceptual window explains the two checks; each measured worst margin can come from a different path.")
prose("""
<p><strong>Follow the cost of keeping the schedule.</strong> Read Figure 6 along the upper arrows first, from launch register to output register; then compare the arrival and deadline in the lower bar. In Figure 6, a compute-enable register changes the input-selection logic, one input bit crosses to the arithmetic, and a result bit returns to the output bank. This same-cycle return is the physical consequence of preserving the original completion schedule. The upper diagram locates each measured segment in the circuit; the lower bar puts the complete arrival time beside its capture deadline.</p>
""")
figure("06-cross-tier-path","Figure 6. A measured control → compute → output-storage round trip in the nominal link model. The signal reaches the output register at 19.692 ns, before its 100.720 ns deadline, leaving 81.028 ns of setup margin. The five segment delays are differences between reported pin-arrival times; crossing segments include the wire and receiving buffer. The full-design nominal worst setup margin is 53.600 ns (Figure 5).")
prose("""
<h2>7. What this case teaches</h2>
<p><strong>Budget the whole boundary.</strong> Of 725 functional links, 179 carry the host interface. Including this feedthrough is essential when evaluating how much computation fits within the connection windows. The 10 µm proxy geometry leaves 59 functional sites after the chosen cut.</p>
<p><strong>Preserving a schedule creates a physical obligation.</strong> Returning the next sum without a new pipeline stage keeps the measured cycle behavior. It also places cross-tier combinational and round-trip paths in the timing graph. Their actual parasitics and clocks have to be evaluated together.</p>
<p><strong>Report the implementation cost alongside the feasibility result.</strong> Projected footprint is 1 mm²; total logic silicon is 2 mm². Historical synthesis measured 243,258 µm² for the single-tier reference and 262,841 µm² for the initial two-tier implementation, an approximately 8.1% increase before the later physical ECOs. The final design includes additional clock, buffering and antenna structures. Final activity-based energy and a fully closed equal-silicon comparison are future measurements.</p>
<p><strong>Keep the remaining engineering questions visible.</strong> The current evidence covers one physical seed, a TT library corner and three assumed interconnect RC cases. The original RTL-to-GRT SAT proof remains unproved after a stopped diagnostic; backend preservation uses the documented state/connection proofs and simulations. Independent GDS DRC/LVS, calibrated package models, thermal/IR/EM analysis and manufacturing qualification remain future work. Final L1 ODB/DEF, netlist, SDC and SPEF are frozen. The compute-tier GDS has now been exported directly from that frozen DEF, alongside the reused control-tier GDS. Readback matched per-master instance counts and all physical pin rectangles; see <a href="physical/gds/README.md">the GDS records</a>. The v5 illustration revision added format export and graphics. This editorial revision reuses those artifacts and all completed experiments.</p>

<h2>8. Reproduce the comparison, then inspect the physical analysis</h2>
<table>
<tr><th>Entry</th><th>Included inputs and action</th><th>Validation record and reuse</th></tr>
<tr><td>Default Notebook</td><td>Check source hashes, match 162 pairs, inspect endpoint positions, calculate connection capacity and redraw figures.</td><td>Executed against the included saved records.</td></tr>
<tr><td>Independent throughput comparison</td><td>Single-tier and two-tier RTL, original checker, measurement source, six fixed event schedules and nine vectors. One command runs 162 scenarios per design.</td><td>The v4 validation completed all 324 simulations from an independent package extraction; all 162 scenarios per design match the archived metrics. Those results are reused here.</td></tr>
<tr><td>Joint static timing</td><td>Both final netlists, local SDCs, extracted SPEFs, top-level wrapper, three vertical-link SPEFs and portable analysis scripts. Supply the recorded Liberty file and compatible tool separately.</td><td>The v4 validation executed all three portable scripts. Setup/hold match the archive, full electrical reports are byte-identical, and annotation/constraint checks pass. Those results are reused here.</td></tr>
<tr><td>Final GDS and report views</td><td>Both GDS layouts, frozen DEF copies, raw views, source identities and rendering script.</td><td>The v5 revision completed compute GDS format export and structural/pin readback and rendered Figure 2. Those artifacts are reused unchanged here.</td></tr>
<tr><td>Full physical implementation</td><td>The original archive retains complete flow dependencies, physical databases and routing-tool repair history.</td><td>Packaging a clean-room place-and-route rebuild remains follow-up work.</td></tr>
</table>
<p><strong>Start with input binding:</strong> from this package directory, run <code>python reproduction/reproduce_performance.py</code>. This regenerates the testbench in memory, reconstructs the nine arithmetic vectors and verifies the RTL, event schedules, checker and complete workload identities against the recorded experiment.</p>
<p><strong>Then, optionally regenerate the central comparison:</strong> with Python 3.12 and Icarus Verilog installed, run <code>python reproduction/reproduce_performance.py --run build/paired-reproduction</code>. Choose a new output directory. This compiles both designs and runs 324 simulations with the same stimulus, counts service and completion intervals, saves both new reports and checks all archived metrics. The runner uses four simulation workers and a 600-second timeout per case. The v4 portability validation executed that command in a fresh package extraction and standard-library Python environment with a minimal subprocess environment. All 324 simulations completed and reproduced the archived service cycles, completion cycles, useful bytes and maximum latency values.</p>
<p>That v4 validation used the same host and recorded installed tool binaries; source-build instructions cover obtaining those public versions on another machine. Logs and exact comparisons are included in <a href="portability/result.json">the portability result</a>.<br>See <a href="DEPENDENCIES.md">fixed public dependencies and build commands</a>, <a href="reproduction/README.md">the performance reproduction guide</a> for measurement definitions and dependencies, <a href="physical/README.md">the joint-timing guide</a> for exact inputs and commands, and <a href="sources.json">sources.json</a> for provenance. The <a href="PUBLICATION-REVIEW.md">publication checklist</a> tracks author, license and release decisions.</p>

""")
code("""
# A lightweight negative control: a slowed implementation must fail the paired throughput check.
from copy import deepcopy
reference = review.read("evidence/reference-performance.json")
slower = deepcopy(review.read("evidence/P0-performance.json"))
slower["cases"][0]["completion_cycles"] += 1
try:
    review.compare_performance(reference, slower)
except AssertionError:
    print("Deliberately slowed candidate rejected.")
else:
    raise AssertionError("Throughput checker accepted a slower candidate")
print("Final evidence check:", review.verify())
""")
prose("""
<h2>Sources and acknowledgments</h2>
<p>The circuit and experiment records are local project artifacts whose exact source identities appear in <a href="sources.json">sources.json</a>. Historical records keep their original stage-specific status; this notebook's final results use the accepted frozen evidence from both tiers.</p>
<ul>
<li><a href="https://skywater-pdk.readthedocs.io/en/main/">SkyWater SKY130 PDK documentation</a>: the open process-library context used for the per-tier implementation.</li>
<li><a href="https://openroad.readthedocs.io/en/latest/main/README.html">OpenROAD</a> and <a href="https://github.com/The-OpenROAD-Project/OpenSTA">OpenSTA</a>: the implementation and timing tools supporting the measured flow.</li>
<li><a href="https://github.com/lamda-bbo/Open3DBench">Open3DBench</a>: related open 3D backend implementation and PPA evaluation.</li>
<li><a href="https://research.nvidia.com/publication/2023-03_legalization-die-bonding-bumps-and-pads-3d-ics">S. Pentapati et al., “On Legalization of Die Bonding Bumps and Pads for 3D ICs,” ISPD 2023</a>: related interface legalization work.</li>
<li><a href="https://sscs.ieee.org/membership/awards/ieee-sscs-code-a-chip-travel-grant-awards/">IEEE SSCS Code-a-Chip</a>: current notebook submission requirements.</li>
</ul>
<p>AI assistance was used in the recorded two-tier design workflow, later engineering assistance and preparation of this manuscript. The authors are responsible for the claims and final submission. Zhanchen Zhao is the confirmed conference representative. Project materials are licensed under <a href="LICENSE">Apache-2.0</a>; OpenROAD patches retain BSD-3-Clause. See the <a href="LICENSE-SCOPE.md">license scope</a> and <a href="THIRD-PARTY-NOTICES.md">third-party notices</a>.</p>
""")
cells.append(nbf.v4.new_markdown_cell("""
<h2>Archive name key</h2>
<table><tr><th>Name used in this notebook</th><th>Original evidence identifier</th></tr>
<tr><td>Two-tier design</td><td>P0</td></tr>
<tr><td>Control &amp; storage tier (blue)</td><td>L0</td></tr>
<tr><td>Compute tier (amber)</td><td>L1</td></tr></table>
<p>Original filenames, code identifiers and reports retain these short IDs so that every result remains traceable.</p>
"""))
nb=nbf.v4.new_notebook(cells=cells,metadata={
    "kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},
    "language_info":{"name":"python","version":"3.12"},
    "release_status":"public redistribution authorized; local release package",
    "license":"Apache-2.0",
    "authors":[{"name":name,"affiliation":"Tsinghua University"} for name in ["Zhanchen Zhao","Wenyu Sun","Yaqing Lai","Yubo Deng"]]})
nbf.validate(nb)
nbf.write(nb,ROOT/"FoldAgent.ipynb")
print("Wrote",len(cells),"cells; code cells",sum(c.cell_type=="code" for c in cells))

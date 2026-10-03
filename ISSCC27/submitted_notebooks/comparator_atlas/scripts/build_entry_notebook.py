"""Generate the single public notebook, including the submitted-version Colab badge."""

from pathlib import Path
import textwrap

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]


def markdown(text: str):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(textwrap.dedent(text).strip())


def main() -> None:
    cells = [
        markdown("""
        # Comparator Atlas: SKY130 StrongARM characterization

        **Wei-Lun Hsu — National Tsing Hua University**

        **IEEE SSCS Code-a-Chip — ISSCC 2027**

        License: MIT · Tools: SKY130, ngspice, Magic, Netgen and Python

        [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WLHsu0827/sscs-ose-code-a-chip.github.io/blob/wlhsu0827-comparator-atlas-isscc27/ISSCC27/submitted_notebooks/comparator_atlas/Comparator_Atlas.ipynb)

        The badge opens the submitted fork.
        [Official-main Colab link (available only after merge)](https://colab.research.google.com/github/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/ISSCC27/submitted_notebooks/comparator_atlas/Comparator_Atlas.ipynb).

        ## Abstract

        Offset calibration alone does not ensure that a regenerative comparator
        makes a correct decision before its deadline. Comparator Atlas explores
        this tradeoff using a SKY130 StrongARM comparator with physical trim
        devices. The notebook compares nine sizing/threshold candidates,
        evaluates calibration policies across PVT conditions, and follows the
        selected design into actual layout and parasitic extraction. Interactive
        waveforms connect circuit behavior to decision time and core energy.
        Schematic and extracted results are compared under explicitly stated
        conditions. The adopted **single-row-a1 area version** reduces the
        all-material GDS bbox from 2207.088 to 2074.254 um2 (6.01852%).
        Its paired 45-PVT qualification completed 1440 transients and 720
        numerical pairs: both layouts and C/RC modes give 180/180 correct
        decisions at 2 ns. Candidate RC retains 156/180 at 1 ns
        (24 unresolved), with worst sampled delay 1.811 ns. The observed
        approximately 1% core-energy decrease does not establish a robust
        physical PPA benefit. The original studies remain separate below.
        In the original 45-condition nominal, code-zero study, archived RC
        decks give 156/180 correct decisions at 1 ns (24 unresolved) and
        180/180 at the prospectively declared 2 ns deadline; the worst sampled
        decision time is 1.835 ns. These are archived RC-deck
        outcomes; extracted-model physical fidelity is not yet qualified.
        Schematic results are unaffected by this extraction concern.
        See the model-applicability limitation in Section 8 and
        [Reproducibility](REPRODUCIBILITY.md#archived-rc-model-applicability).

        **Research question and contribution.** How do the input band and
        deadline affect calibrated decision correctness and core energy,
        and what changes between two legal layouts under matched nominal
        conditions? StrongARM operation is established (Razavi, 2015).
        Auxiliary-pair offset calibration and its timing/parasitic effects
        have also been analyzed (Li, Xu and Iizuka, 2022).
        This work contributes a finite-grid comparison and a recorded
        layout-area revision, not a new latch topology, noise theory or
        silicon benchmark. Full references appear in the discussion.

        ## Getting started

        Default execution verifies supplied data and remeasures saved waveforms;
        it does not run new simulations. For static reading, open the
        [reviewer guide](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/blob/wlhsu0827-comparator-atlas-isscc27/ISSCC27/submitted_notebooks/comparator_atlas/REVIEWER_GUIDE.md)
        or [interactive report](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/blob/wlhsu0827-comparator-atlas-isscc27/ISSCC27/submitted_notebooks/comparator_atlas/results/study/report.html).
        Download the report and open its HTML locally; GitHub's file viewer
        does not execute its JavaScript.
        Set `RUN_LIVE_SPICE` for a small fresh simulation or
        `RUN_FULL_CAMPAIGN` for the complete schematic study.
        Tool versions, full commands and evidence locations are in
        [Reproducibility](REPRODUCIBILITY.md).
        """),
        code(r"""
        from pathlib import Path
        import importlib.util
        from importlib import metadata
        import subprocess
        import sys

        parts = (
            "ISSCC27", "submitted_notebooks", "comparator_atlas"
        )
        source = Path.cwd() / "comparator-atlas-source"
        candidates = [
            Path.cwd(),
            Path.cwd().joinpath(*parts),
            source.joinpath(*parts),
        ]
        entry_root = next(
            (p for p in candidates if (p / "entry_tools.py").is_file()),
            None,
        )
        if entry_root is None:
            if source.exists():
                raise RuntimeError(
                    "An incomplete source directory already exists. "
                    "Inspect it before retrying; it was not overwritten."
                )
            repository = (
                "https://github.com/WLHsu0827/"
                "sscs-ose-code-a-chip.github.io.git"
            )
            branch = "wlhsu0827-comparator-atlas-isscc27"
            subprocess.run(
                [
                    "git", "clone", "--quiet", "--depth", "1",
                    "--filter=blob:none", "--no-checkout",
                    "--single-branch", "--branch", branch,
                    repository, str(source),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "git", "-C", str(source), "sparse-checkout",
                    "set", str(Path(*parts)),
                ],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "checkout", "--quiet", branch],
                check=True,
            )
            entry_root = source.joinpath(*parts)
            if not (entry_root / "entry_tools.py").is_file():
                raise RuntimeError("The downloaded entry is incomplete.")
        required = {
            "numpy": "2.2.6",
            "pandas": "2.2.3",
            "matplotlib": "3.10.3",
            "nbformat": "5.10.4",
            "ipywidgets": "8.1.7",
        }
        needs_setup = []
        for name, version in required.items():
            if importlib.util.find_spec(name) is None:
                needs_setup.append(name)
            elif metadata.version(name) != version:
                needs_setup.append(name)
        if needs_setup:
            subprocess.run(
                [
                    sys.executable, "-m", "pip", "install", "-q",
                    "-r", str(entry_root / "requirements-review.txt"),
                ],
                check=True,
            )
        stale = []
        for name, version in required.items():
            loaded = sys.modules.get(name)
            if loaded is not None:
                loaded_version = getattr(loaded, "__version__", version)
                if loaded_version != version:
                    stale.append(name)
        if stale:
            raise RuntimeError(
                "Dependencies were updated but older packages are loaded. "
                "Restart the kernel/runtime once, then Run all."
            )
        sys.path.insert(0, str(entry_root))
        import matplotlib.pyplot as plt
        import pandas as pd
        from IPython.display import Image, display
        import entry_tools as entry
        import layout_evidence as physical

        %matplotlib inline
        release_checksums = entry_root / "entry_checksums.json"
        if release_checksums.is_file():
            import json
            support_hashes = json.loads(
                release_checksums.read_text(encoding="utf-8")
            )
            support_hashes.pop("Comparator_Atlas.ipynb", None)
            entry.verify_files(
                entry_root,
                support_hashes,
            )
            print(
                "Public support files verified. The notebook itself "
                "remains editable for execution-mode switches."
            )
        else:
            print(
                "Development checkout: sealed experiment manifests "
                "will be verified; no release file map is present."
            )
        RUN_LIVE_SPICE = False
        RUN_FULL_CAMPAIGN = False
        print("Python:", sys.version.split()[0])
        print("Default: verified supplied evidence, not a fresh SPICE run.")
        """),
        markdown(r"""
        ## 1. Decision-time and energy measurements

        At deadline $T$ after the evaluation clock midpoint, the decision is
        valid only if **both** complementary outputs reach their assigned
        rails: one at least $0.8V_{\mathrm{DD}}$, the other at most
        $0.2V_{\mathrm{DD}}$. Its sign must equal that of the externally
        applied differential input. A resolved opposite sign is **wrong**;
        a missing complementary-rail decision is **unresolved**.
        Zero input is not counted in pass fractions.

        The sampled decision time excludes an early output glitch: it is the
        first saved valid sample after the final invalid sample, through the
        reporting deadline. A 1 ns decision deadline does not mean that a
        1 GHz clock was tested; the clock period is 10 ns.

        $$E_{\mathrm{core}}=-V_{\mathrm{DD}}
        \int_{20\,\mathrm{ns}}^{30\,\mathrm{ns}} I_{V_{\mathrm{DD}}}(t)\,dt.$$

        The full third cycle includes reset. Two previous cycles provide
        warmup. Input common mode is half the supply, clock edges are 50 ps,
        and each output carries a 5 fF ideal load unless an explicitly named
        interface stress changes that condition.

        Runs are checked for reset and complete waveform data. Pass fractions
        describe the listed test grid, not manufacturing yield.
        """),
        markdown(r"""
        ## 2. Offset calibration

        A zero-input trim scan locates candidates near a sign change. Input
        bisection then brackets confirmed opposite decisions. The score is

        $$M_T=\max(|v_-(T)|,\ |v_+(T)|).$$

        A wide unresolved interval is retained rather than replaced by its
        midpoint. The host search minimizes the larger absolute endpoint,
        with 0.2 mV input-bracket resolution and a local monotonicity assumption.

        The long-deadline policy uses 3.5 ns; a separate ablation applies the
        same procedure at 1 ns. A TT/1.8 V/27 C reference-code policy transfers
        a single code across model corners. It is **not** a per-die factory
        calibration at an unknown fixed process corner.
        """),
        markdown("""
        ## 3. Comparator circuit and design selection

        During reset, four PFETs precharge the internal and output nodes.
        When the clock rises, the tail conducts and the input pair starts
        discharging the internal nodes. Cross-coupled feedback regenerates
        the differential signal into complementary outputs. Device imbalance
        shifts the switching boundary; the auxiliary branches provide trim.

        The conventional StrongARM core has eleven transistor instances,
        including four reset PFETs. Each trim magnitude bit adds one auxiliary
        analog input NFET and its digital source-gating NFET on each side.
        The selected circuit has 27 instances and **four magnitude bits plus
        sign**, supporting codes -15 through +15. An on-chip decoder and
        calibration controller are not implemented.

        The auxiliary analog gates track their respective input. No ideal
        source simply subtracts a fitted offset. All trim devices remain
        physically present at code zero; comparison within a design therefore
        retains its trim parasitic loading.

        Nine candidates vary device threshold flavor, dimensions and trim
        range. LVT applies to the main and auxiliary analog input paths;
        latch, tail and digital switches remain standard-VT.

        Selection used three PVT conditions and six inputs, with 2x mean
        training core-energy and 4x gate-area-proxy budgets. The ranking
        maximizes worst-case training coverage, then mean coverage, followed
        by boundary magnitude, energy and gate geometry. The gate-area proxy
        is the sum of transistor W times L, not placed/routed area.
        The first prototype informed the family. All rejected candidates
        remain visible in the recorded selection.

        The schematic uses enhancement-mode MOS symbols and explicitly
        connected regenerative feedback. A reset symbol represents one
        device for each listed node; the trim pair repeats for bits 0–3
        on both sides. Identical node labels in different panels connect
        electrically. Body ties are stated beneath the drawing.
        [Vector schematic](results/presentation/circuit_guide.pdf).
        """),
        code("""
        if RUN_FULL_CAMPAIGN:
            entry.full_reproduction()
        evidence = entry.load_evidence()
        selection = evidence["selection"]
        candidates = pd.DataFrame([
            {
                "design": item["design"]["name"],
                "input_device": item["design"]["input_device"],
                "transistors": item["design"]["transistor_count"],
                "gate_area_um2": item["design"]["gate_area_proxy_um2"],
                "worst_training_coverage":
                    item["worst_case_correct_fraction"],
                "mean_training_core_fj": item["mean_core_energy_fj"],
                "eligible": item["eligible"],
            }
            for item in selection["candidates"]
        ])
        display(candidates)
        print("Frozen selected design:", selection["selected_design"])
        display(Image(filename=str(physical.circuit_guide_path())))
        """),
        markdown("""
        ## 4. Schematic results across PVT

        The complete [selected SPICE netlist](results/study/selected_circuit.spice)
        is provided with the source.

        The original comparison has 45 PVT combinations at one controlled
        main-pair width skew, plus four additional nominal skew controls:
        49 conditions per circuit. This is not every mismatch value at every
        PVT combination. With +4% skew, the two branch widths use multipliers
        1.04 and 0.96. This deliberately controlled perturbation is **not a
        foundry Monte Carlo mismatch distribution**.

        The selected/original comparison uses validation inputs distinct from
        the six current selection inputs. The three selection conditions
        remain identifiable; they are not relabeled as independent data.

        **Post-selection control.** An existing lower-energy LVT candidate,
        `lvt_base_3b`, is characterized on the same 49 conditions with code
        zero and local calibration. This addresses a stronger engineering
        question than comparison with the original circuit alone: whether
        the selected circuit's extra energy is justified by the desired
        decision band. This control was declared after viewing the original
        comparison and does not constitute a new blinded test set.

        The next tables show both average and worst-condition coverage.
        A design with a favorable average is not automatically acceptable
        if even one required condition fails.

        ### Strict sampled specification guide (schematic only)

        The saved map after the comparison requires **every included nonzero
        signed input at all 49 controlled-width-stress conditions to be
        correct**, using the existing `local_boundary` calibration. Among
        the three compared designs that qualify, it chooses the least
        measured **mean full-cycle core energy** over that sampled band.
        If none qualifies, it reports **No feasible compared design**, with
        no best-average fallback.

        At 1 ns, sampled |input| >= 1 mV has no feasible design; >= 3 mV
        selects `lvt_balanced_4b` (294/294), while >= 30 mV selects the
        lower-energy `lvt_base_3b` (98/98). The 36 cells contain 28 with
        no feasible design, five selecting `lvt_balanced_4b`, and three
        selecting `lvt_base_3b`. Baseline is never chosen **only in this
        compared calibrated sampled domain**.

        This is descriptive, post-hoc analysis of existing schematic data,
        not the nominal 45-PVT RC study or a new experiment. No interpolation,
        continuous-input guarantee or energy budget is implied. Mean core
        energy is not a maximum-cycle bound and excludes drivers and
        calibration/system energy. Exact equal means retain all tied
        designs in the JSON; display selection follows the declared order.
        The [108 per-design and 36 per-specification records](results/study/specification_map/summary.json)
        include provenance hashes. No calibration or original circuit
        selection is changed.

        ### Where do the failures remain?

        The static transition matrices match **the same sample keys**, not
        differences of aggregate totals: design, condition and signed input.
        At |input| >= 1 mV, baseline's 60 unresolved samples at 1 ns become
        29 correct, nine wrong and 22 still unresolved at 2 ns. The lower-energy
        control's nine unresolved samples become six correct and three wrong.
        A longer deadline therefore need not reduce the wrong count.
        The selected design's 20 wrong samples are **exactly the same set**
        at both deadlines, all at signed +/-1 mV; their locations and local
        calibration codes are listed below. This does not identify a physical
        cause such as trim saturation, residual offset or noise.

        The specification table also shows the **minimum observed decision
        margin** (deadline minus recorded decision time) and **maximum sampled
        full-cycle core energy**, only for strict-qualified winners. For
        selected >= 3 mV at 1 ns these are 154.52 ps and 363.22 fJ; the limiting
        timing sample is FS / 1.62 V / -40 C / +4% width stress / -3 mV.
        All qualified designs and every exact tied limiting observation are in
        the same [auditable JSON](results/study/specification_map/summary.json),
        alongside grouped failures and all 1,176 keyed deadline pairs.
        NONE retains null metrics. These finite recorded margins are not
        noise/jitter/PVT confidence bounds or timing signoff; sampled maximum
        core energy is not a worst-cycle guarantee or system-energy cap.
        The original mean-energy ranking is unchanged.
        """),
        code("""
        print("Local policy; 1 ns; sampled |input| >= 1 mV")
        display(entry.summary(evidence, minimum_mv=1.0))
        print("Same policy and deadline; sampled |input| >= 3 mV")
        display(entry.summary(evidence, minimum_mv=3.0))
        display(entry.sampled_envelope(evidence))
        figure = entry.tradeoff_figure(evidence)
        display(figure)
        plt.close(figure)

        from presentation import specification_map

        specifications = specification_map.load_checked(evidence)
        display(Image(filename=str(
            specification_map.FOLDER / "selection_map.png"
        )))
        display(specification_map.example_table(specifications))
        display(Image(filename=str(
            specification_map.FOLDER / "failure_transitions.png"
        )))
        display(specification_map.failure_table(specifications))
        display(specification_map.selected_wrong_table(specifications))
        """),
        code("""
        import ipywidgets as widgets


        def inspect_tradeoff(minimum_mv, deadline_ns):
            display(entry.summary(evidence, minimum_mv, deadline_ns))


        minimum_control = widgets.SelectionSlider(
            options=[0.25, 0.5, 1.0, 3.0, 10.0, 30.0],
            value=1.0,
            description="Min |input| (mV)",
            continuous_update=False,
            style={"description_width": "initial"},
        )
        deadline_control = widgets.SelectionSlider(
            options=[0.25, 0.35, 0.5, 0.75, 1.0, 2.0],
            value=1.0,
            description="Deadline (ns)",
            continuous_update=False,
            style={"description_width": "initial"},
        )
        interactive_table = widgets.interactive_output(
            inspect_tradeoff,
            {
                "minimum_mv": minimum_control,
                "deadline_ns": deadline_control,
            },
        )
        display(minimum_control, deadline_control, interactive_table)
        """),
        markdown("""
        ## 5. Time-step consistency

        The original 10-to-5 ps refinement exposed fourteen failed deadline
        checks across seven physical points. Refinement to 0.625 ps produced
        two consecutive passing halving comparisons under the unchanged
        limits: identical decision/outcome, at most 1% core-energy difference
        and at most 20 ps resolved-latency difference.

        The finest accepted waveform replaces **every** matching policy and
        deadline observation, including corrections that make the circuit
        look worse. Original coarse tables and the full refinement history
        remain available. No circuit, code, stimulus, deadline or frozen
        candidate choice changes during this process.

        The added energy-efficient control checks every nonzero input point
        under both policies at 10 and 5 ps, then applies the same stricter
        halving rule to sensitive points. Unresolved sensitivity blocks its
        inclusion as a completed comparison.

        These are numerical checks for declared observations, not proof of
        stability at every continuous input, random-noise immunity or
        production signoff.
        """),
        code("""
        numerical = pd.DataFrame([
            {
                "study": "original / selected",
                "initial_failed_checks":
                    evidence["stress"]["initial_numerical_failures"],
                "final_failed_checks":
                    evidence["stress"]["numerical_failures"],
                "refined_physical_points":
                    evidence["stress"]["refined_physical_points"],
            },
            {
                "study": "post-selection lower-energy control",
                "initial_failed_checks":
                    evidence["control"]["initial_failed_checks"],
                "final_failed_checks":
                    evidence["control"]["final_failed_checks"],
                "refined_physical_points":
                    evidence["control"]["refined_physical_points"],
            },
        ])
        display(numerical)
        """),
        markdown("""
        ## 6. Waveforms and decision behavior

        The following small, hash-checked waveform set is distributed with the
        entry. It is not a synthetic behavioral model. The same measurement
        function used in the campaign recomputes reset validity, rail-valid
        decisions, latency and full-cycle core energy.

        The weak SS/low-voltage/cold condition was known during selection.
        These traces illustrate mechanism; the complete condition tables
        support the finite-grid comparison.
        """),
        code("""
        measured, figure = entry.review_waveforms()
        display(measured[[
            "design", "input_mv", "deadline_ns", "outcome",
            "decision_time_ns", "core_energy_fj",
        ]])
        display(figure)
        plt.close(figure)
        if RUN_LIVE_SPICE:
            display(entry.live_spice_smoke())
        else:
            print(
                "Waveform metrics recomputed from checked saved SPICE data. "
                "Set RUN_LIVE_SPICE=True for fresh transistor simulation."
            )
        """),
        markdown("""
        ### Waveform lab: wrong, late, or correct?

        RC examples illustrate archived-deck outcomes, not a qualified
        physical model; see Section 8. Changing the display does not
        resolve the extraction-model limitation.

        The two saved figures and reading tables below compare the untrimmed
        and calibrated schematic examples at **1.0 ns**, without widget
        JavaScript. They reuse existing traces and the same measurement
        contract: no new simulations or validation coverage.

        The interactive controls follow these static examples and explore
        all eight representative saved SPICE waveforms. Compare the
        complementary output rails with the selected deadline.

        Start with the **code-zero -1 mV schematic example**: its outputs
        resolve to the wrong polarity. Switch to the same circuit and
        input with calibration enabled, then to a cold-SS extracted RC
        example. At 1 ns that RC trace is late; reading its saved 2 ns
        observation does not retroactively pass the original 1 ns gate.

        Horizontal dotted lines are the fixed 80% / 20% output rail
        thresholds. The two cursor voltages, not only their difference,
        determine whether the decision is valid. Core energy always
        covers the complete saved 10 ns cycle.
        """),
        code("""
        from presentation import waveform_lab

        lab = waveform_lab.load_lab()


        def inspect_waveform(example, deadline_ns):
            figure, reading = waveform_lab.figure(
                lab, example, deadline_ns
            )
            display(figure, pd.DataFrame([{
                key: reading[key] for key in (
                    "outcome", "deadline_ns", "Q+_at_deadline_V",
                    "Q-_at_deadline_V", "sampled_decision_time_ns",
                    "full_cycle_core_energy_fJ",
                )
            }]))
            plt.close(figure)


        for static_example in ("schematic_untrimmed", "schematic_calibrated"):
            inspect_waveform(static_example, 1.0)

        example_control = widgets.Dropdown(
            options=[
                (sample["label"], sample["id"])
                for sample in lab["samples"]
            ],
            value="schematic_untrimmed",
            description="Stored waveform",
            style={"description_width": "initial"},
            layout=widgets.Layout(width="95%"),
        )
        waveform_deadline = widgets.SelectionSlider(
            options=lab["deadlines_ns"],
            value=1.0,
            description="Deadline (ns)",
            continuous_update=False,
            style={"description_width": "initial"},
        )
        waveform_output = widgets.interactive_output(
            inspect_waveform,
            {
                "example": example_control,
                "deadline_ns": waveform_deadline,
            },
        )
        display(example_control, waveform_deadline, waveform_output)
        """),
        markdown("""
        ## 7. Input-interface sensitivity and calibration cost

        Five original/selected PVT conditions are stressed with input history,
        finite source resistance and capacitance, altered common mode, and
        increased output loading. The calibration code is frozen before the
        interface changes. Results include the unfavorable cases: the faster
        LVT path can inject larger deterministic input disturbances and does
        not necessarily improve a heavily loaded interface.

        The measured pin error includes settling and kickback, not random
        thermal noise. These interface results apply to the original and
        selected circuits; the added lower-energy control has not silently
        inherited them.

        Calibration workload below counts distinct simulated probes. Each
        probe simulates three 10 ns cycles. This is **offline experiment
        workload**, not an implemented calibration latency or total on-chip
        energy. A practical system also needs reference/input generation,
        switching, a controller and storage; those implementation costs
        remain outside the measured core-rail energy.
        """),
        code("""
        display(entry.operating_summary(evidence))
        display(entry.calibration_workload(evidence))
        """),
        markdown("""
        ## 8. Adopted single-row-a1 area version

        The adopted 27-MOS, 15-port layout has a 121.8 x 17.03 um
        all-material GDS bbox (2074.254 um2), versus the original compact
        control's 129.6 x 17.03 um (2207.088 um2): **6.01852% less area**.
        Wells, body ties, guards and shields are included; only TEXT is excluded.
        Pitch decreases from 4.8 to 4.5 um; pair order, mirroring, vertical placement, device WL/flavors,
        junctions and local M1/M2 escapes remain unchanged. Only necessary
        horizontal bus/output/shield endpoints and symmetric spines follow
        placements. There is no diffusion sharing or matching-benefit claim.

        **Archived RC-deck outcomes; model physical fidelity not yet qualified.**
        The candidate passed 14 native checks on one actual DRC attempt in its
        earlier spacing round; the unchanged original-control native proof was
        reused, not rerun. Full45 qualification and publication added no native runs.
        The subsequent nominal code-zero grid used both layouts, C and RC,
        45 PVT conditions, signed +/-3 and +/-10 mV inputs, and 10/5 ps steps:
        **1440 transients and 720 qualified pairs**, with 180 points per
        layout and mode. The conditions were known before qualification.
        All points are correct at the fixed 2 ns primary deadline.
        At 1 ns, C-only improves from 168 to 170 correct points, only at
        SS / 1.62 V / -40 C / +/-10 mV. RC retains 156 correct and the same
        24 unresolved points. No previously correct point is lost.

        All 180 matched energies and recorded 2 ns latencies decrease in
        each mode. Ratio-of-mean energy changes are -0.9453% for C-only and
        -1.0448% for RC. These decreases are numerically consistent in the
        recorded decks, but their physical accuracy is unknown.
        The declared 1% energy / 20 ps latency criteria are numerical acceptance
        bands, **not uncertainty bounds**. No robust global PPA, yield, silicon,
        independently qualified PEX or signoff conclusion follows. Core energy excludes
        drivers/controller/calibration. C-only is not independent ground truth.
        This is not the calibrated 49-condition width-stress study, nor a
        post-layout calibration, noise or mismatch qualification.

        [Versioned raw traces, native geometry, pins and audit recipe](layout_single_row/v1/README.md)
        retain all 1440 decks, logs and waveforms, 720 numerical receipts and keyed
        comparisons. Earlier studies below remain historical, not candidate data.
        """),
        code("""
        import single_row_evidence as area

        adopted = area.load()
        display(area.table(adopted))
        for factory in (area.layout_figure, area.comparison_figure):
            figure = factory(adopted)
            display(figure)
            plt.close(figure)


        def inspect_area_version(layout_version, extraction_mode):
            rows = adopted["frame"]
            display(rows[
                (rows.layout == layout_version)
                & (rows["mode"] == extraction_mode)
            ].drop(columns=["execution"]))


        area_controls = widgets.interactive(
            inspect_area_version,
            layout_version=widgets.Dropdown(
                options=["candidate", "control"], value="candidate",
                description="Area version",
            ),
            extraction_mode=widgets.Dropdown(
                options=["rc", "c"], value="rc", description="Export",
            ),
        )
        display(area_controls)
        print(area.NOTICE)
        """),
        markdown("""
        ### Original control: layout and post-layout results

        **Archived RC-deck outcomes; model physical fidelity not yet qualified.**
        In the pinned Magic/open_pdks pipeline, mutual capacitances are
        retained while grounded capacitance increases. Physical error
        magnitude and direction are unknown; no exact duplication factor,
        corrected counts or energy, or conservative bound is inferred.
        C-only is not independent ground truth, and RC-versus-C performance
        differences cannot be attributed solely to resistance.
        DRC/LVS establish their recorded structural checks, not parasitic-model
        fidelity. Schematic results are unaffected by this extraction concern.
        Numerical agreement does not establish silicon PVT performance.
        This applies to both studies below; all archived outcomes are retained.

        The layout uses the same selected 27-device circuit with nominally
        matched main inputs and code zero. It does not reproduce the
        schematic width-skew experiment as intentional geometry.
        Fifteen ordered ports, exact device flavors/dimensions/body ties,
        and actual mask geometry are checked before simulation.

        A first legal layout had positive-input failures after extraction.
        Balanced routing changed the archived-deck outcomes; a compact
        routing revision then required four real M2 bridges to eliminate
        narrow PFET body-pad notches. This final physical repair passes
        named-style DRC, independent LVS and deliberately wrong connection,
        bulk, width and SVT/LVT negative controls. It is not foundry signoff.

        **Three separate electrical exports:** connectivity-only LVS,
        C-only extraction, and distributed RC extraction. All native
        elements and their annotations remain retained. The GDS view below
        is parsed from the actual hash-checked file, not a drawn floorplan.
        """),
        code("""
        layout = physical.load_layout()
        display(physical.geometry_summary(layout))
        figure = physical.layout_figure(layout)
        display(figure)
        plt.close(figure)
        display(physical.matched_tt_comparison(layout))
        figure = physical.tt_cost_figure(layout)
        display(figure)
        plt.close(figure)
        """),
        markdown("""
        ### Historical original compact control: five-condition comparison

        At matched TT +/-3 mV points, the archived compact RC decks reduce mean
        delay from 0.843 to 0.645 ns and core energy from 521 to 425 fJ
        relative to the prior legal balanced layout. The matched schematic
        uses 244 fJ. This compares complete layouts, not the isolated effect
        of the pad repair.

        RC meets the original 1 ns deadline at 12/20 sampled points;
        eight SS points are late. The same retained traces give 20/20
        correct points at 2 ns. That is a post-hoc observation, not a
        revised 1 ns pass. This earlier ngspice-42 study covers five
        conditions and four inputs (+/-3, +/-10 mV) per mode. Its results
        remain separate from the following ngspice-47 full-grid study.
        """),
        code("""
        display(physical.deadline_summary(layout))
        figure = physical.deadline_figure(layout)
        display(figure)
        plt.close(figure)
        layout_measurements, figure = (
            physical.review_layout_waveforms(layout)
        )
        display(layout_measurements[[
            "corner", "vdd_v", "temperature_c", "input_mv",
            "deadline_ns", "outcome", "decision_time_ns", "core_energy_fj",
        ]])
        display(figure)
        plt.close(figure)
        """),
        markdown("""
        ### Historical original-control full-grid archived-deck outcomes

        This historical original compact control was evaluated over all five
        process corners, three supplies (1.62, 1.80, 1.95 V), and three
        temperatures (-40, 27, 125 C). Each of the 45 conditions uses
        differential inputs -10, -3, +3 and +10 mV: **180 points per mode**.
        Schematic and extracted RC use code zero, common mode 0.5 VDD,
        5 fF output loads, and the same 10 ns clock with 50 ps edges.

        This historical study declared **2 ns** as its primary deadline while also
        reporting 1 ns. Both modes were freshly simulated with ngspice 47
        at 10 and 5 ps; all 360 pointwise numerical comparisons meet the
        fixed decision, 1% energy and 20 ps latency criteria. The five
        earlier layout conditions are identified as previously observed;
        the other forty are new post-layout conditions, not a blinded test.

        **Archived RC decks are correct at 180/180 sampled points at 2 ns, and 156/180 at
        1 ns.** The 24 remaining 1 ns points are unresolved, not wrong-sign
        decisions. The slowest sample is FS / 1.62 V / -40 C / -3 mV at
        1.835 ns, rather than the SS corner seen in the earlier pilot.
        These finite-grid results do not establish statistical yield or
        behavior between the listed input values.

        **Where the 24 unresolved points occur.** The table below counts the
        published finest-row records, not just the ten representative traces.
        Each factor is a separate marginal partition of the same 180 RC points;
        do not add counts across factors or treat them as independent samples.

        | Factor | Level | RC correct at 1 ns | RC unresolved at 1 ns | RC correct at 2 ns |
        | --- | --- | ---: | ---: | ---: |
        | Corner | TT | 36/36 | 0/36 | 36/36 |
        | Corner | SS | 24/36 | 12/36 | 36/36 |
        | Corner | FF | 36/36 | 0/36 | 36/36 |
        | Corner | SF | 36/36 | 0/36 | 36/36 |
        | Corner | FS | 24/36 | 12/36 | 36/36 |
        | Supply (V) | 1.62 | 36/60 | 24/60 | 60/60 |
        | Supply (V) | 1.8 | 60/60 | 0/60 | 60/60 |
        | Supply (V) | 1.95 | 60/60 | 0/60 | 60/60 |
        | Temperature (C) | -40 | 52/60 | 8/60 | 60/60 |
        | Temperature (C) | 27 | 52/60 | 8/60 | 60/60 |
        | Temperature (C) | 125 | 52/60 | 8/60 | 60/60 |
        | Input (mV) | -10 | 39/45 | 6/45 | 45/45 |
        | Input (mV) | -3 | 39/45 | 6/45 | 45/45 |
        | Input (mV) | +3 | 39/45 | 6/45 | 45/45 |
        | Input (mV) | +10 | 39/45 | 6/45 | 45/45 |

        All 24 unresolved records are at 1.62 V in SS or FS; all three
        temperatures and all four signed inputs are represented. No RC point
        is wrong at either deadline; schematic is correct at 180/180 at both.
        This is a descriptive record-level audit, not a raw-waveform replay or evidence of physical causality.
        Archived RC-model physical fidelity remains unqualified.

        Reproduce this table from the [360-row CSV](results/study/postlayout_pvt45/measurements.csv)
        with `python -B -m scripts.audit_pvt_failures --format markdown`
        from the entry directory. JSON output also lists the 24 unresolved
        point/run identities; [audit details](REPRODUCIBILITY.md#full-grid-failure-distribution).
        """),
        code("""
        from presentation import pvt45_results as pvt

        full_pvt = pvt.load_results()
        display(pvt.comparison_table(full_pvt["frame"]))
        figure = pvt.timing_figure(full_pvt["frame"])
        display(figure)
        plt.close(figure)
        figure = pvt.tradeoff_figure(full_pvt["frame"])
        display(figure)
        plt.close(figure)
        """),
        markdown("""
        The PVT map shows the **maximum over the four signed input samples**
        in each cell. Black outlines identify conditions containing a missed
        1 ns decision; every point meets the primary 2 ns deadline.
        The paired plots retain all 180 schematic/RC comparisons, with
        marker shape as well as color identifying the process corner.

        Mean full-grid core energy is **245.84 fJ schematic versus
        425.49 fJ extracted RC**. The mean of the per-point energy overheads
        is 73.45%; the ratio of population means is 73.08%. These are
        different aggregations and are not interchanged.

        [Vector PVT map](results/study/postlayout_pvt45/figures/pvt45_timing.pdf)
        · [Vector paired comparison](results/study/postlayout_pvt45/figures/pvt45_comparison.pdf)

        The next plot remeasures the original saved schematic/RC pair at
        the worst sampled condition. Ten representative traces are provided
        for review; they are a subset of the 720 simulations behind the
        complete result.
        """),
        code("""
        pvt_examples = pvt.review_examples(full_pvt)
        display(pvt_examples[[
            "condition", "mode", "input_mv", "deadline_ns",
            "outcome", "decision_time_ns", "core_energy_fj",
        ]])
        figure = pvt.worst_case_figure(full_pvt)
        display(figure)
        plt.close(figure)
        """),
        markdown("""
        ## 9. Discussion and limitations

        Under the same local calibration policy, the selected circuit
        increases 1 ns correct decisions from 310/392 to 372/392 across
        the 49 listed schematic conditions, while mean core energy rises
        from 143.01 to 251.53 fJ/cycle. The post-selection lower-energy
        control reaches 351/392 at 156.65 fJ/cycle. Neither design
        dominates both measured correctness and core energy.

        The separate nominal, code-zero layout study records 156/180
        correct RC decisions at 1 ns and 180/180 at its declared 2 ns
        deadline. These are results of the archived extraction decks,
        whose physical fidelity remains unqualified; they are not
        silicon predictions or an isolated measure of resistance.

        A subsequent [two-point RC-card sensitivity check](REPRODUCIBILITY.md#bounded-rc-sensitivity-check)
        reran 28 transients with hypothetical R/C scaling. At the slowest
        archived FS point, C x 1.2 makes the 2 ns decision unresolved.
        This is neither a measured process-error bound nor a new full-grid
        pass rate. A separate [GDS geometry check](results/study/gds_geometry/README.md)
        restores the interface and measures selected conductor dimensions;
        imported RC still differs from the MAG extraction. Its isolated
        sheet/plate components are not whole-net parasitic estimates.

        - Results are deterministic SKY130 simulations. Width perturbations
          are controlled stress, not a foundry mismatch distribution or yield.
        - Candidate selection was a finite design comparison; the
          post-selection control and previously observed PVT conditions
          do not form a blinded external validation set.
        - The 49-condition calibrated schematic study, earlier five-condition
          layout experiment and full 45-condition nominal code-zero study
          have separate conditions and recorded tool identities.
        - Core-rail energy excludes input/clock drivers and calibration
          infrastructure. DRC/LVS do not establish silicon performance or
          complete foundry signoff.

        See [Reproducibility](REPRODUCIBILITY.md) for tool versions, commands,
        numerical criteria and the locations of layouts, waveforms and logs.

        ### References

        1. Behzad Razavi, “The StrongARM Latch [A Circuit for All Seasons],”
           *IEEE Solid-State Circuits Magazine*, vol. 7, no. 2, pp. 12–17,
           2015. DOI: [10.1109/MSSC.2015.2418155](https://doi.org/10.1109/MSSC.2015.2418155).
        2. Shuowei Li, Zule Xu and Tetsuya Iizuka, “Analysis of strong-arm comparator with
           auxiliary pair for offset calibration,” *Analog Integrated Circuits
           and Signal Processing*, vol. 110, no. 3, pp. 535–546, 2022.
           DOI: [10.1007/s10470-022-01992-6](https://doi.org/10.1007/s10470-022-01992-6).
        3. [Official SKY130 primitive models](https://github.com/google/skywater-pdk-libs-sky130_fd_pr),
           revision `f62031a1be9aefe902d6d54cddd6f59b57627436`.
           Original Apache-2.0 notices are retained.
        4. [Open SKY130/GF180 comparator optimization research](https://github.com/ChrisZonghaoLi/sky130_comparator_rl)
           and [an existing SKY130/LVT comparator example](https://github.com/edonD/sky130-comparator).
           Related ideas are credited; their code, figures, performance
           claims and statistical assumptions are not this study's evidence.
        5. [ngspice](https://ngspice.sourceforge.io/) and
           [Code-a-Chip rules](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io).
        6. [Magic extraction documentation](https://opencircuitdesign.com/magic/commandref/ext2spice.html),
           [distributed resistance extraction](https://opencircuitdesign.com/magic/commandref/extresist.html),
           and [open_pdks](https://github.com/RTimothyEdwards/open_pdks).

        **Acknowledgment.** GitHub Copilot assisted implementation, experiment
        automation, figures and documentation. The author is responsible for
        the work. Original code is MIT licensed; third-party models and tools
        retain their licenses.
        """),
    ]
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook.metadata.update({
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.18"},
    })
    nbf.validate(notebook)
    destination = ROOT / "Comparator_Atlas.ipynb"
    if destination.exists():
        previous = nbf.read(destination, as_version=4)
        for index, cell in enumerate(cells):
            prior_index = index if len(previous.cells) == len(cells) or index < 17 else index - 2
            if 0 <= prior_index < len(previous.cells) and (
                    len(previous.cells) == len(cells) or index not in (17, 18)):
                cell.id = previous.cells[prior_index].id
    nbf.write(notebook, destination)
    print(f"Generated {destination.name}: {len(cells)} cells")


if __name__ == "__main__":
    main()

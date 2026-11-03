"""Generate the single public notebook, including the submitted-version Colab badge."""

from pathlib import Path
import textwrap

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]


def markdown(text: str):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(textwrap.dedent(text).strip())


def main(support_digest: str | None = None) -> None:
    from presentation import release_identity

    if support_digest is None:
        support_digest = release_identity.support_digest(release_identity.release_files(ROOT))
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
        conditions. The adopted **local-pitch b1 version** reduces the
        all-material GDS bbox from matched a1's 2074.254 to 1873.3 um2 (9.688013%).
        Its paired 45-PVT qualification completed 1440 transients and 720
        numerical pairs: both layouts and C/RC modes give 180/180 correct
        decisions at 2 ns. Candidate RC gives 158/180 at 1 ns
        (22 unresolved), versus a1's 156/180 (24 unresolved), with worst
        recorded 2 ns delay 1.760276 ns. The observed
        approximately 1.94% core-energy decrease does not establish a robust
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
        import hashlib
        import importlib.util
        from importlib import metadata
        import json
        import subprocess
        import sys

        # Identity of the support files this Notebook was generated with.
        EXPECTED_SUPPORT_DIGEST = (
            "__SUPPORT_RELEASE__"
        )
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
        release_checksums = entry_root / "entry_checksums.json"
        support_hashes = None
        if release_checksums.is_file():
            support_hashes = json.loads(release_checksums.read_bytes())
            support_hashes.pop("Comparator_Atlas.ipynb", None)
            canonical = json.dumps(
                support_hashes, sort_keys=True, separators=(",", ":")
            )
            found = hashlib.sha256(canonical.encode()).hexdigest()
            if found != EXPECTED_SUPPORT_DIGEST:
                raise RuntimeError(
                    f"Release mismatch: the support files in {entry_root} "
                    f"(support digest {found[:12]}) are not the release "
                    "this Notebook was generated with "
                    f"({EXPECTED_SUPPORT_DIGEST[:12]}). A reused "
                    "'comparator-atlas-source' folder is stale, or the "
                    "submitted branch moved after this copy was saved. "
                    "Rename or delete that folder and Run all again, or "
                    "open the Notebook stored in the same folder or "
                    "commit as the support files. Nothing was overwritten."
                )
        elif entry_root == source.joinpath(*parts):
            raise RuntimeError(
                f"{release_checksums} is missing, so the downloaded "
                "source cannot be matched to this Notebook. Rename or "
                "delete 'comparator-atlas-source' and Run all again."
            )
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
            # Runtime pins only: never reinstall the pytest/nbmake/ipykernel
            # that may be executing this Notebook.
            pins_file = entry_root / "requirements-review.txt"
            pins = [
                line.strip()
                for line in pins_file.read_text().splitlines()
                if line.split("==")[0].strip() in required
            ]
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", *pins],
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
        from IPython.display import HTML, Image, display
        import entry_tools as entry
        import layout_evidence as physical

        %matplotlib inline
        if support_hashes is not None:
            entry.verify_files(
                entry_root,
                support_hashes,
            )
            print(
                "Public support files verified against release "
                f"{EXPECTED_SUPPORT_DIGEST[:12]}. The notebook itself "
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

        Start with the **code-zero -1 mV schematic example**: its outputs
        resolve to the wrong polarity. Switch to the same circuit and
        input with calibration enabled, then to a cold-SS extracted RC
        example. At 1 ns that RC trace is late; reading its saved 2 ns
        observation does not retroactively pass the original 1 ns gate.

        The two static figures and tables below show the untrimmed and
        calibrated schematic examples at **1.0 ns**; the interactive
        controls that follow explore all eight saved SPICE waveforms with
        the same measurement rules (no new simulations). Dotted lines are
        the fixed 80% / 20% output-rail thresholds: both cursor voltages,
        not only their difference, decide validity. Core energy covers the
        complete saved 10 ns cycle. RC examples come from the archived
        extraction decks (see Section 10, Limitations).
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
        ## 8. Adopted local-pitch b1 version

        **Result.** The adopted b1 layout is **9.69% smaller** than a1
        (110 x 17.03 um, 1873.3 um2, against 121.8 x 17.03 um, 2074.254 um2;
        all-material GDS bbox including wells, ties, guards and shields) and
        loses no decision. On a nominal code-zero grid of 45 PVT conditions
        and signed +/-3 and +/-10 mV inputs (180 points per layout and mode),
        every point is correct at the 2 ns primary deadline in both layouts.
        At 1 ns, C-only stays at 170 correct / 10 unresolved; RC goes from
        156 correct / 24 unresolved (a1) to 158 / 22 (b1), the gain only at
        SS / 1.62 V / 125 C / +/-10 mV. No previously correct point is lost.
        All 180 matched energies and 2 ns latencies decrease, by about 1.9%
        in both C-only and RC mean energy.

        **What changed.** The 27-MOS, 15-port b1 keeps a1's pair order,
        mirroring, vertical placement, device sizes, junctions and local
        M1/M2 escapes; only the local pitch (3.8/4.2 um) and the horizontal
        bus, output and shield endpoints that follow it change. There is no
        diffusion sharing or matching-benefit claim. Local planning margins
        are at least 0.20 um; the inherited global M3 margin is 0.16 um.

        **How it was checked.** 1440 transients (both layouts, C and RC,
        10/5 ps steps) form 720 qualified pairs; the PVT conditions were
        known before qualification. b1 passed 14 native checks on one DRC
        attempt; the a1/b1 native proofs and extracts were reused, not
        rerun. The restored pre-route MAG is not the final routed MAG. Fresh control readings match the archived a1 readings
        exactly. The 1% energy / 20 ps latency acceptance criteria are
        numerical bands, **not uncertainty bounds**, and C-only is not
        independent ground truth. Physical-fidelity limits of the RC decks
        are stated with the original control below and in Section 10.

        [Versioned raw traces, native geometry, pins and audit recipe](layout_single_row/v2/README.md)
        and the unchanged [historical a1 version](layout_single_row/v1/README.md)
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
            matched = rows.layout.eq(layout_version)
            matched &= rows["mode"].eq(extraction_mode)
            display(rows[matched])


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
        ## 9. Extension: why no design reaches 1 mV, and a design that does

        > **Scope.** Added after the main study. Later local SKY130/ngspice
        > schematic simulations (plus one extraction *estimate*) under the
        > same calibration policy and outcome rules. Nothing here changes
        > Sections 1–8 or the sealed decision record. Every number below is
        > loaded from a hash-checked archive; commands and runtimes are in
        > [Reproducibility](REPRODUCIBILITY.md#research-extension).

        **Section summary.** Each row is detailed below; r-numbers label the
        archived study runs.

        | Question | Finding | Runs |
        |---|---|---|
        | Why does the atlas return NONE at 1 mV? | Every wrong decision lies between zero and the calibration residual offset (303/303); the limit is the trim, not latch speed | law, prospective test |
        | Can a redesigned trim reach ±1 mV? | Yes: `unit6_w6` at 1 and 2 ns (760 fJ) and `u6_w12_l05` at 0.75–2 ns (623 fJ), all 49 conditions; no layout of their own | r15b, r17, r19 |
        | Does the original selection survive model and mismatch checks? | Yes; the selection is unchanged under an exact current skew | r20–r22 |
        | How large is thermal noise? | 0.71 mV input-referred at TT; ±1 mV counts are noiseless, a 10⁻⁶ error rate needs about 4 mV | r23, r24 |
        | Does the fix hold under mismatch? | Unit-cell trims pass ±1 mV at 1 ns for 978–999/1000 seeds; a segmented trim with a transistor-level decoder passes 1000/1000 | r24c–r26f |
        | What limits the segmented trim? | Clock kickback onto the decoder gates; a hold capacitor or a 4× pull-down removes it, ranking held in 40/40 seeds | r26g–r26j |

        **Question.** Section 4 finds *no feasible compared design* at
        input bands of 1 mV or below, at every deadline. Is that a latch-speed
        limit or a calibration limit?

        **A one-line law.** Calibration leaves each comparator with a static
        residual offset *m*, measured at the 3.5 ns calibration deadline.
        In this dataset, a resolved decision on input *v* is flagged when
        0 < *v*/*m* < 1, i.e. when *v* lies between zero and *m*. Over the three
        atlas designs and six deadlines this flags all 303 wrong decisions
        among 5,295 resolved ones, with no misses and four observed-correct
        false positives (all lvt_base_3b). Every observed wrong decision lies
        between zero and the residual offset, although the condition is not
        sufficient in those four cases. The selected design keeps |*m*| > 1 mV in 20 of
        49 conditions (maximum 2.58 mV), so it cannot qualify at 1 mV however
        long it is given: the limit is the trim, not regeneration speed.
        """),
        code("""
        from presentation import research_extension as ext

        extension = ext.load()
        display(ext.law_table(extension))
        display(ext.prospective_table(extension))
        display(ext.atlas_table(extension))
        """),
        markdown("""
        **Prospective test.** For six designs never simulated before, the law
        plus a decision-time model fitted only on |*v*| ≥ 3 mV issued
        predictions for all 10,584 held-out decisions (±0.25 to ±1 mV) before
        those inputs were simulated; the predictions were sealed by SHA-256.
        Of these, 10,359 (97.9%) matched, and all 108 predictive atlas-cell
        classifications agreed. None of those six
        qualifies at 1 mV either. The atlas table also lists the four later
        trim designs discussed below (r13, r15, r19).

        **Cause: the binary trim array.** Bit 0 is a single minimum-width
        (0.42 µm) device and the larger bits are wider single devices, so the
        bit weights are not exact binary ratios (we attribute this to
        narrow-width effects). The step at the 7→8 major carry reaches 11.25 mV at
        SS 1.62 V −40 °C, a DNL of +2.2 LSB (panel a). In a paired mismatch
        Monte Carlo (per-device Vth shifts from the PDK's own Pelgrom term,
        identical draws for every variant) two of 40 SS seeds land on that
        carry with |*m*| = 4.1–4.8 mV and decide ±3 mV wrongly.

        **Candidate fix.** Build each trim bit from 2<sup>k</sup> identical 0.42 µm units,
        add a fifth bit, and double the input pair (W = 6 µm) to reduce the
        offset that the trim must cover. On the same seeds, |*m*| ≤ 0.59 mV and
        ±1 mV is correct 80/80 at 0.75 ns at both TT and SS, against 70/80
        (10 wrong) at TT and 26/80 (3 wrong) at SS for the shipped design
        (table and panel b).

        **Its limit: trim range (r13).** We then ran the fix through the full
        49-condition atlas as a sealed prospective test (sha256 registered
        before the held-out inputs were simulated). The sealed prediction was
        that it would *not* qualify at 1 mV, and it does not: in 11 of 49
        conditions the calibration code saturates at ±31 and |*m*| reaches
        1.2–10.9 mV (FF and SF at 1.95 V and SF at 1.80 V with +4% width skew,
        and both ±8% skews at TT; second table below). In the other 38,
        |*m*| ≤ 0.39 mV. The sealed predictions matched 1,710 of 1,764
        held-out decisions (96.9%) and all 18 predictive atlas cells. Its
        finer step costs range (at TT 1.62 V −40 °C, +4% skew, the shipped
        design needs code −2 of ±15, the fix −12 of ±31), so across the atlas
        it qualifies only at ≥30 mV.

        **Step and range together: a design that reaches 1 mV (r15).** Two
        more sealed 49-condition tests separate the two limits (third table
        below). Keeping the 5-bit unit trim with the original W = 3 µm input
        pair (coarser step) removes saturation but leaves |*m*| up to
        1.33 mV: ≥3 mV at 1 ns at 402 fJ, no better than the shipped design.
        Keeping W = 6 µm and adding a sixth unit bit (±63 codes),
        `unit6_w6`, keeps the fine step *and* covers the skew: codes reach
        −52, |*m*| ≤ 0.55 mV in all 49 conditions, and the design qualifies
        at **±1 mV at 1 ns and 2 ns** (98 of 98 ±1 mV decisions correct at
        each), at 760 fJ mean core energy over that band. For context, the
        shipped design requires a ≥3 mV band and averages 250 fJ there; these
        are different specifications, not a same-specification energy
        comparison. It was the first tested design in this finite 49-condition
        schematic atlas to qualify at ±1 mV (r19 below adds a second). At 0.75 ns it qualifies at ±3 mV: the
        sealed ±1 mV prediction failed by one unresolved decision
        (SS 1.62 V 125 °C, +4% skew, *v* = −1 mV against *m* = −0.55 mV).
        Held-out agreement was 96.1% (5-bit) and 95.1% (6-bit). The shared
        calibration routine accepts at most ±31 codes; for the 6-bit run only
        that input check was raised to 63 in a local copy, and the search
        itself is unchanged.

        **The 6-bit design under random mismatch (r16).** On the same 40
        paired seeds as the fix (identical draws for every shared device; only
        the added bit-5 units draw new values), the 6-bit design's range
        covers every seed at TT and SS, |*m*| ≤ 0.59 mV, and ±1 mV is correct
        80/80 at both 0.75 ns and 1 ns at both conditions (first table below).
        At ±0.5 mV and 1 ns it is not reliable: 77/80 (3 wrong) at TT and
        64/80 (16 unresolved) at SS. Its nominal core energy is about 3× the
        shipped design's at all three corners (731, 460 and 1,065 fJ against
        244, 167 and 341 fJ at code 0; energy table below).

        **The 6-bit design after layout parasitics: an estimate (r17).** It
        has no drawn layout, so we reuse the archived b1 extraction with the
        input pair doubled and every trim bit split into unit copies, and
        place bits 4 and 5 on bit 3's extracted nodes with bit 3's wiring
        capacitance scaled ×2 and ×4 (no added resistance). At code 0 with
        nominal devices over the 45 PVT corners, ±1 mV is correct 90/90 at
        2 ns but only 69/90 at 1 ns (78/90 with the latch-output wiring
        halved), at 919–945 fJ; there are no wrong decisions, only
        unresolved ones, and 34 of the 37 misses at 1 ns are at 1.62 V. The
        unit-array schematic of the same design is 270/270 at 0.75 ns. So
        after estimated parasitics the 1 mV result holds at 2 ns, not at
        1 ns (post-layout table below). The same run also corrects a detail
        of r11: its schematic row used a binary-sized netlist, and the
        unit-array netlist gives the same 180/180 (worst decision 0.48 ns).
        """),
        code("""
        display(ext.mc_table(extension))
        display(ext.fix_residual_table(extension))
        display(ext.range_table(extension))
        display(ext.energy_table(extension))
        display(ext.postlayout_table(extension))
        display(ext.energy_screen_table(extension))
        display(ext.wide_rc_table(extension))
        display(ext.bin_stress_table(extension))
        display(ext.trim_range_table(extension))
        display(ext.noise_table(extension))
        figure = ext.figure(extension)
        display(figure)
        plt.close(figure)
        """),
        markdown("""
        **Cost, and what did not work.** Core energy follows total trim gate
        area (panel c): the fix uses 420 fJ against 244 fJ (TT, code 0),
        consistent with every trim channel being charged each cycle through
        its series switch, whatever the code. A gate-switched trim avoids that
        charge (188 fJ), but its transfer becomes corner-dependent and even
        non-monotonic (we attribute this to switch kickback onto the trim
        gates) and two TT seeds fall outside its range, so it is rejected. Reusing the archived b1 extraction with
        resized devices (an estimate, not a re-layout) gives 178/180 correct
        at 1 ns, and 180/180 with the latch-output wiring halved, at
        579–605 fJ.

        **Can the 6-bit design be made cheaper? The screen (r18).**
        Its energy follows the same rule: 731 fJ at TT against 244 fJ for the
        shipped design. A nominal TT screen of six variants (wider input
        pair, shorter trim L, narrower or drain-side switch; energy-screen
        table) changes energy roughly in proportion to trim range
        (input W 12 µm, L 0.5 µm: 611 fJ, range 37 mV against 44 mV). Judged
        against the code −52 of ±63 that r15b needed, we first read this as
        no margin; r19 tested that reading and it was wrong for the wider
        input pair. Moving the switch to the drain side costs more energy
        (802 fJ) and range (16 mV) and is slower.

        **A wider input pair: cheaper and faster (r19).** The wider pair also
        needs far less trim. In a sealed 49-condition test of the r18 variant
        with input W = 12 µm and 0.5 µm-long trim units (`u6_w12_l05`;
        predictions registered by SHA-256 before the held-out inputs, same
        local 63-code deviation), codes stay within −16 to +15 (r15b: −52 to
        +32), no condition reaches the range end, and |*m*| ≤ 0.39 mV. It
        qualifies at ±1 mV at 0.75, 1 and 2 ns, at ±0.5 mV at 2 ns and at
        ±3 mV at 0.5 ns, at about 623 fJ: in every atlas cell at least as good
        as `unit6_w6`, at 18% less energy. Most of the smaller offset to
        trim turned out to be a model-binning effect rather than the circuit
        (r20, next paragraph). Held-out agreement was 94.9%, and 16 of 18
        predictive atlas cells agreed; both misses predicted ±0.5 mV at
        0.75 and 1 ns, which it does not reach. In mismatch Monte Carlo
        paired with r16 (same 40 seeds per condition), the trim covers 80/80
        and ±1 mV is 80/80 correct at 0.75 and 1 ns at both conditions. The
        largest residual is higher, 0.82 mV against 0.59 mV (one SS −40 °C
        seed at code 31, where the step to code 32 measured 1.9 mV), while the
        RMS residual is similar (0.27/0.29 mV against 0.26/0.30 mV). At
        ±0.5 mV and 1 ns it is 79/80 and 78/80 correct (1 and 2 wrong)
        against 77/80 (3 wrong) and 64/80 (16 unresolved). With the r17 RC
        estimate on the same ±1 and ±3 mV inputs (fourth-to-last table), ±1 mV is
        correct 78/90 at 1 ns (`unit6_w6`: 69/90) and ±3 mV 90/90 (78/90),
        at 827 fJ against 949 fJ; all 12 misses are unresolved, at 1.62 V.
        With the latch-output wiring halved, a layout assumption rather than
        an extraction, ±1 mV is 90/90 at 1 ns.

        **Is the width-skew stress design-neutral? (r20, r21).** No. The
        SKY130 transistor models are binned by width, so a ±4% width skew
        does not give a 4% current skew: in DC at TT the low-Vt pair gives
        0.048–0.072 at W = 6 µm, 0.031–0.038 at 3 µm and 0.040 at 12 µm
        (third-to-last table). Splitting the 12 µm pair into two 6 µm fingers nearly
        triples its untrimmed offset (2.7 to 7.6 mV at TT). With an exact 4%
        current skew instead (instance multiplier *m* = 1 ± 0.04, nominal
        geometry; 45 skewed PVT conditions), the median untrimmed offset of
        `unit6_w6` falls from 16.1 to 10.2 mV while `u6_w12_l05` stays at
        6.9/6.7 mV, so the r19 gap shrinks from 2.3× to 1.5×. For the sealed
        comparison the width skew is 1.14–1.21× the exact skew for the two
        2 µm designs and 0.81× for the selected 3 µm design, whose exact-skew
        offset equals that of `lvt_base_3b` (median 11.6 mV each). We
        therefore reran the three sealed designs on all 49 conditions with
        both skews, re-simulating every ±1 mV point of every design at
        0.625 ps (the sealed record refined all ±1 mV points only for the
        selected design). The width-skew rerun matches the sealed validation
        rows exactly and the published 1 ns counts to within one decision;
        with the exact skew the counts are 310, 348 and 377 of 392, and the
        strict-map selection does not change (no design at ≥1 mV,
        `lvt_balanced_4b` at ≥3 and ≥10 mV, `lvt_base_3b` at ≥30 mV).
        Calibration removes most of the stress, so the binning changes the
        offset to be trimmed but not the comparison. One margin does shrink:
        with the exact skew the selected design reaches the end of its trim
        range (code −15 of ±15) at SF 1.95 V 125 °C, although all eight inputs
        there are still correct.

        **Does that trim range cover random mismatch at its narrowest corners?
        (r22).** The earlier Monte Carlo of the selected design covered only
        TT and SS. Without skew or mismatch, its trim range (the distance from
        the code-0 switching input to that of code ±15, at 3.5 ns) has a
        median of 37.8 mV over the 45 PVT conditions but only 18.5 mV at
        SF 1.95 V 125 °C and 19.0 mV at FF 1.95 V 125 °C, the narrowest of
        the three sealed designs (`baseline` 24.3 mV, `lvt_base_3b` 28.4 mV;
        second-to-last table): its finer step costs range where a code moves the
        offset least. On the same 40 paired seeds at those two corners, the
        untrimmed offset spreads more than at TT (standard deviation 14.2–15.1 mV
        against 11.2 mV), yet the trim covers 38/40 at each, because every
        sample's trim transfer shifts with its own mismatch (at SF, seeds with
        |offset| 20.5 and 22.4 mV, beyond the nominal 18.5 mV, are covered).
        The two uncovered seeds, 3 and 13 (untrimmed offset +38.8 to
        +42.5 mV), carry the
        largest input-pair mismatch in this seed set (about 3.3σ), and
        `lvt_base_3b` misses the same two at SF 1.95 V 125 °C. For the
        selected design every other seed decides ±3 mV correctly at 1 ns
        (78/80 at both corners; `lvt_base_3b` 76/80), and ±1 mV is 71/80 and
        69/80 against 57/80 (Monte Carlo table). So the comparison holds, but
        neither sealed trim covers about 3σ offsets at hot, high-supply
        corners; with 40 seeds the coverage is only loosely bounded (95%
        interval 84–99%).

        **How much of this is noise? Transient thermal noise (r23).** Every
        result above is noiseless: a seed counts as correct at ±1 mV when its
        residual |*m*| is below 1 mV. To turn that into an error rate we
        added the BSIM4 white (thermal) drain-current noise of every
        transistor to the transient run. A table built with ngspice `.noise`
        gives each device's noise density at its instantaneous bias (read
        back to within 0.03%), and it scales a Gaussian current sampled
        every 2 ps, switched on 2 ns before the clock edge. For 40 noise
        realizations (the same draws for every design, so comparisons are
        paired), bisection finds the input at which the 3.5 ns decision
        flips; the spread of that input is the input-referred noise σn. On
        a single switch charging a capacitor the noise is 0.97 (NMOS) and
        1.03 (PMOS) times the integrated `.noise` result at a 0.5 ps step
        (0.85 and 0.96 at 2 ps, where that faster test circuit outruns the
        grid); in the comparator a 1 ps step changes the mean-square noise by
        +1% (16 paired realizations) and 0.5 ps by −5% (4 realizations).
        For the selected design at TT, σn is 0.71 mV (95% interval
        0.55–0.87 mV; last table), the same as `lvt_base_3b` (0.72 mV; a
        paired variance test gives t = 0.4) and 1.5× the untrimmed
        `baseline` (0.46 mV; t = 3.6). It grows from 0.36 mV at
        SS 1.62 V −40 °C to 1.32 mV at SF 1.95 V 125 °C, 3.7× where
        √T alone gives 1.3×. The input pair carries 82% of
        the noise variance, the NMOS latch pair 11% and the reset switches
        7%; runs with one group noisy at a time add up, realization by
        realization, to the full run within 0.016 mV rms (24 realizations).
        With P(wrong) = Φ(−(1 mV − |*m*|)/σn) for the ±1 mV input whose sign
        opposes the residual, the Monte Carlo residuals give the selected
        design a median error probability of 0.28 at TT and 0.31 and 0.38
        at the SS and SF corners. Its ±1 mV counts are therefore
        deterministic statements about *m*, not low error rates: its
        residual (rms 0.78 mV at TT) is as large as σn. A 10⁻⁶ error rate
        needs 4.0 mV at TT (median seed; 4.4 mV at the 90th percentile) and
        6.9 mV (7.4 mV) at SF 1.95 V 125 °C. The 6-bit designs have
        residuals of 0.5–0.7σn and less noise (0.52 and 0.39 mV; the wider
        input pair lowers σn by a quarter, t = 9.6), so they need 2.6 and
        2.0 mV at TT. In the trimmed rows the switched-off trim branches are
        kept noiseless; with every device noisy the selected design gives
        0.70 mV (paired rms difference 0.05 mV), and the 6-bit designs move
        by at most 0.04 mV in 5 and 3 checked realizations.
        """),
        markdown("""
        **Noise without a noise simulation: the impulse sensitivity of the
        decision (r24).** r23 found the decision linear in the device noise,
        so σn² = Σₖ ∫ gₖ(t)² Sₖ(t)/2 dt, where gₖ(t) is the shift of the
        switching input per unit charge that device *k* injects at time *t*
        and Sₖ is its r23 noise density along the noiseless trajectory. We
        measure g directly in the r23 deck: a 2 ps, ±20 aC charge pulse into
        each internal node at time τ, with the switching input bisected for
        each sign. One condition takes 4–6 minutes against about 25 for a
        40-realization noise run, and the same formula predicts every r23
        realization from its own noise sequence (first table below:
        correlation 0.988–0.9987 on the original bench). The worst match,
        `unit6_w6` (slope 0.77), exposed a bench artifact: the bench clocks
        three cycles with the input held, and the node between each
        switched-off trim device and its open series switch floats, keeps
        charge from the earlier decisions and returns it to the input
        pair's drain node (x). This
        decision memory is 7.5 µV in the selected design and 43 µV in
        `unit6_w6`, and it vanishes when the off branches are deleted
        (second table). With the two earlier cycles pinned to a fixed input,
        the ISF reproduces every Monte Carlo realization to 6–8 µV rms, below
        the Monte Carlo's own 11.7 µV bisection step, so the remaining σn gap
        (0.640 against 0.702 mV at TT) is the sampling spread of 40
        realizations. Moving each series switch to the x side removes the
        memory in all four designs but reverses and rescales the trim step
        (shipped LSB −2.64 → +6.49 mV); a requalified fix follows below.

        On the pinned bench the selected design's σn spans 0.35 mV
        (FS 1.62 V −40 °C) to 1.21 mV (SF 1.95 V 125 °C) over the 45 PVT
        conditions (third table); noise alone then needs 5.7 mV for a 10⁻⁶
        error rate. The trend follows the classical integration-phase law
        σin² = 4kTγ(Id/gm)/Qint for the input pair (cf. Nuzzo et al.,
        TCAS-I 2008), with Qint = ∫Id dt from the clock edge until the x
        nodes reach VDD/2: with gm, Id and γ read from the same trajectory,
        the exact input-pair noise is 0.729 ± 0.037 times the closed form
        over all 45 conditions. Qint stays within 5.9–8.6 fC, so the noise is
        set by the inversion level Id/gm (and γ), not by speed: higher VDD
        and temperature push the pair deeper into strong inversion. That
        makes the input common mode a noise knob. We wrote the law's
        predictions down (constant from the first 11 atlas conditions; the
        final one moves them by 1%) before running the exact ISF at
        0.6–1.1 V (last table): within 2% at 0.6 and 0.9 V, +12% at 0.7 V and
        −17% at 1.1 V, where the latch and reset carry half the noise. At
        0.6 V a new 40-realization Monte Carlo gives 0.364 mV against
        0.344 mV from the ISF (7.0 µV rms per realization): lowering the
        common mode from VDD/2 to 0.6 V halves σn at about 6× the decision
        time, and σn² × decision time is lowest near 0.7 V (24% below
        nominal).
        """),
        code("""
        display(ext.isf_table(extension))
        display(ext.memory_table(extension))
        display(ext.isf_atlas_table(extension))
        display(ext.noise_law_table(extension))
        """),
        markdown("""
        **Closing the three gaps: a gain law for the latch noise, a causal
        memory probe and a requalified fix (r24c).** *Latch and reset noise.*
        The input pair carries 55–93% of σn² over PVT; the rest is
        latch and reset noise, suppressed by the gain the input pair gives
        before the latch takes over, Aint = (gm/Id)·VDD/2, read from the same
        noiseless trajectory. One fitted constant, σn² = σin²·[1 + (A0/Aint)²]
        with A0 = 3.13, reproduces the exact σn at all 45 PVT conditions to
        0.6% rms (1.9% max; 5.3% rms with the closed-form σin, against 16% for
        the input pair alone), and refitting A0 with each corner held out
        moves it by less than 1%. Applied unchanged to the common-mode sweep
        (first table below) it holds within 1% up to VDD/2 and
        under-predicts by 11.5% at 1.1 V, where Aint falls to 3.8. The
        ISF's reset share equals its pre-edge share on all 13 benches (within
        0.021): the reset noise is the reset-switch kT/C carried across the
        edge and suppressed by the same Aint.

        *Causal memory probe.* Deleting the off branches also deleted their
        capacitance. Here every branch stays in place and only the state of
        the floating nodes is set during the last reset, with ideal switches
        (second table; a is the memory per decision, c the fraction of the
        previous input carried over). Forcing each node to its own value
        changes a by at most 2 µV; shorting each sp⟨k⟩ to its sn⟨k⟩ erases
        both a and c in all four designs, to the 1–2 µV bisection floor; and
        forcing the node voltages of the opposite prior flips both signs. The
        memory is the differential charge on those nodes (a 1.1–2.0 mV
        split), nothing else.

        *The fix.* Shorting the pair is the fix: one minimum NMOS per bit,
        gated by the inverted clock from one minimum inverter, equalizes
        sp⟨k⟩ and sn⟨k⟩ in reset; no trim device moves. On the shipped trim
        (third table) it removes the memory (7.5 → 1.0 µV, c 0.95% → 0), keeps
        the 31-code trim monotonic at TT, SS and FS, raises the narrowest of
        the 45 half ranges from 18.7 to 27.5 mV and costs 3% energy (+1% and
        43 → 1.0 µV on `unit6_w6`). Precharging the nodes to VDD also works
        and gives more range, at 36–60% more energy; the r24 switch swap
        loses monotonicity at SS. In the paired r22 mismatch Monte Carlo at
        the two hot corners (last table) the equalized trim shrinks every
        untrimmed offset by about 10% and the two ~3σ seeds' residuals from
        16.5/14.4 to 4.8/2.7 mV (SF), but still does not cover them. Its
        hot-corner step is coarser (half range 18.5 → 29.3 mV over the same
        15 codes), so the ±1 mV count at 1 ns falls from 71/80 to 65/80 at SF
        and 69/80 to 62/80 at FF while ±3 mV stays at 78–79/80. The
        equalizer is a memory fix that makes the trim strength more uniform
        over PVT (narrowest/widest half range 0.32 → 0.49), not a ±1 mV fix;
        covering those seeds at ±1 mV needs the wider range with a finer
        step.
        """),
        code("""
        display(ext.gain_law_table(extension))
        display(ext.memory_probe_table(extension))
        display(ext.memory_fix_table(extension))
        display(ext.fix_mc_table(extension))
        """),
        markdown("""
        **One more bit with the equalizer (r25).** The shipped core gets a
        fifth binary trim bit (codes ±31) and the r24c equalizer; nothing
        else moves. *Trim length.* A longer trim device looks like a free
        finer step, but the first table shows it is not: the trim adds gm
        (∝ W/L) and capacitance on the x node (∝ W·L) in opposite
        directions, and their null moves with PVT. At L ≥ 1.25 µm the hot
        corners' trim folds back and then reverses polarity (end-point LSB
        −0.08 mV at SF for L 1.25, +0.96 mV for L 1.5) while TT still
        trims normally, so L = 1 µm is the longest usable length. Its
        63-code transfer at the hot corners has two small carry reversals
        (max |DNL| 2.2 LSB) but no fold-back. *Monte Carlo.* In the paired
        mismatch Monte Carlo (second table; the same seeds draw the same
        core and 4b trim devices as r22 and r3, the fifth bit draws its own)
        the narrowest of the 45 half ranges is 43.9 mV (median 67.1), every
        seed is covered at both hot corners, the two ~3σ seeds trim to
        within 0.82 mV, ±3 mV at 1 ns is 80/80 at all three conditions, and
        ±1 mV returns to the shipped design's level (68/80 at SF, 71/80 at
        FF, 70/80 at TT). It does not go further: every ±1 mV miss is a
        wrong decision of a covered seed, the hot-corner step is about
        2 mV, and the shipped 4b trim at TT, with every seed covered, also
        scores 70/80. All seeds at ±1 mV needs a step near 1 mV, not more
        range. *Cost.* The 5b trim with equalizer takes 460 fJ per TT
        comparison at code 0 against 296 fJ for the equalized 4b trim
        (+55%), and the gate-area proxy rises from 20.6 to 38.8 µm²; the
        decision memory stays at the bisection floor (−1.0 µV; 24.0 µV
        without the equalizer).
        """),
        code("""
        display(ext.trim_length_table(extension))
        r25 = ext.trim5_mc_table(extension)
        display(r25)
        e4, e5 = r25.attrs["energy_fj"]
        a4, a5 = r25.attrs["area_um2"]
        print(f"TT energy, code 0: 4b+eq {e4:.0f} fJ, 5b+eq {e5:.0f} fJ")
        print(f"gate-area proxy: 4b {a4:.2f} um^2, 5b {a5:.2f} um^2")
        """),
        markdown("""
        **A finer step from unit cells (r26, r26b).** r25 is limited by
        its step, not its range. *Wider input pair (r26).* Widening the
        input pair and tail by k (same current density) shrinks the step,
        since the step is set by the ratio of trim gm to input-pair gm.
        At k 1.25, ±1 mV rises from 209 to 235 of 240 decisions (SF, FF,
        TT) for +3.6% energy; six bits at k 1.5 reach 238 but cost 1.8×
        the energy. The remaining misses are carries, and the hot range
        collapses faster than 1/k. *Diagnosis (r26b, first table).* The
        width-binary trim (bit k: one W 0.42·2^k device and switch) does
        not have binary weights: w4/w0 is 30–33 at −40 °C and 7 at 125 °C,
        so its full range moves 2.4× over the five conditions. The narrow
        LSB device sits in another model bin, and its perimeter terms do
        not scale with W, so each bit has its own Vth and capacitance.
        *Unit cells.* Building bit k from 2^k identical cells (W 0.42
        trim, W 1 switch; the same total W and gate area) keeps w4/w0 at
        11.5–18.6 and the full range within 1.08× at all five conditions.
        In the second table, the unit-cell trim cuts the cold max step
        from 12 to 2.6 mV and the hot DNL from 3.0 to 1.4 LSB at the same
        k, and the 45-condition half range spreads 1.4× instead of 2.5×.
        At k 1.5 (`u5_k150`), every seed is covered and ±1 mV at 1 ns is
        240/240 over SF, FF and TT (max |m| 0.82 mV), at 482 fJ and
        39.8 µm²: +4.8% energy and +2.5% area over r25, against 818 fJ
        and 76.2 µm² for six width-binary bits. The narrow-width cause
        was seen at the cold corners in r7; new here are the hot corners,
        the equalizer and the paired Monte Carlo.
        """),
        code("""
        display(ext.bit_weight_table(extension))
        display(ext.unit_trim_table(extension))
        """),
        markdown("""
        **200 seeds and a unit-cell equalizer (r26c).** r26b's 240/240
        is 40 seeds at three conditions. At 200 seeds and five conditions
        (adding SS and FS 1.62 V −40 °C), `u5_k150` keeps every TT and hot
        seed, but at the cold corners 11 of 400 seeds leave |*m*| > 1 mV
        and ±1 mV at 1 ns passes 978 of 1000 seeds overall (95% CI
        0.967–0.986). The static misses sit at codes that switch three or
        more bits: the r24c equalizer, one minimum device per bit, was not
        converted to unit cells, so the larger bits settle less in reset,
        by an amount that changes with PVT (carry DNL up to 1.5 LSB, not
        monotonic at the hot corners). Most cold 1 ns failures are
        unresolved, not wrong: a residual near the 1 mV band edge leaves
        about 0.2 mV to regenerate, which the slow cold latch cannot do in
        1 ns. Building the equalizer from 2^k unit devices as well
        (`e5_k150`, clkb inverter m 4) makes the transfer monotonic with
        DNL ≤ 0.27 LSB at all five conditions and raises the pooled ±1 mV
        at 1 ns to 996 of 1000 (0.990–0.999), with no unresolved decision,
        for 517 fJ (+7.3%) and 2.0 µm² more equalizer gates. The cost is
        that the LSB now follows PVT (0.97 mV cold, 1.46 mV hot), so the
        hot corners lose 3 of 400 seeds (|*m*| ≤ 1.06 mV) and the
        45-condition half range spreads 1.66× instead of 1.41×. The clkb
        inverter sets the trim gain (second table): a weak edge releases
        the wide equalizer late, so it still shorts the trim nodes during
        integration; m 4 is the cheapest size with every step below
        1.8 mV.
        """),
        code("""
        eq = ext.equalizer_mc_table(extension)
        display(eq)
        e = eq.attrs["energy_fj"]
        a = eq.attrs["equalizer_area_um2"]
        for d in ("u5_k150", "e5_k150"):
            print(f"{d}: TT energy, code 0 {e[d]:.0f} fJ; "
                  f"equalizer gates {a[d]:.2f} um^2")
        print(f"core gate-area proxy {eq.attrs['core_area_um2']:.1f} um^2")
        display(ext.inverter_sweep_table(extension))
        """),
        markdown("""
        **Input-pair scale and the carry law (r26d).** The trim's PVT gain
        ratio is a property of its topology: the nominal SF/SS LSB ratio
        is 1.51 at input-pair scale k 1.5 and again at k 1.75. k only
        moves both ends together, so it sets where the design sits inside
        a window: the hot step must stay below 2 mV with margin (mean
        Monte Carlo 1-bit step ≤ 1.55 mV for 3σ at 0.15 mV), and the cold
        LSB must cover the cold offsets (≥ 0.72 mV for 3σ of b0). k 1.5
        breaks the hot bound (1.71 mV); k 1.75 meets both (1.36 mV hot,
        0.81 mV cold). On the same 200 seeds at five conditions (first
        table), k 1.75 passes ±1 mV at 1 ns for 999 of 1000 seeds
        (0.994–1.000), with one wrong and no unresolved decision, at
        533 fJ (+3.2%) and a 24.9–42.2 mV half range; the gain over 996
        is not statistically resolved. The Monte Carlo mean 1-bit step is
        10–17% above the nominal LSB at the hot corners only, so the
        window must use it. The spread of a local step follows the
        binary-DAC law √(σ0² + (2^j − 1)σu²) for j toggled bits (second
        table), with σu ≈ 0.09 LSB (0.09–0.12 mV at every condition and
        both k) and σ0 the 0.23 mV bisection grid. The nominal transfers
        have no carry excess, so the large hot steps are random: 22 of
        the 46 k 1.5 hot steps above 2 mV sit on 4-bit carries, and the
        one k 1.75 miss is a 7 → 8 carry (|*m*| 1.11 mV). Fed with the
        Monte Carlo step, the law predicts 4.6 static misses per 1000 at
        k 1.5 and 0.7 at k 1.75 (3 and 1 observed) and, for codings that
        were not simulated, 0.07 at k 1.75 with three thermometer MSBs
        (last table): segmentation, not k, is the next knob.
        """),
        code("""
        ks = ext.input_scale_table(extension)
        display(ks)
        for k, e in ks.attrs["energy_fj"].items():
            lo, mid, hi = ks.attrs["half_range_mv"][k]
            rho = ks.attrs["rho_sf_ss"][k]
            print(f"k {k}: TT energy, code 0 {e:.0f} fJ; half range "
                  f"{lo:.1f}/{mid:.1f}/{hi:.1f} mV; SF/SS LSB {rho:.2f}")
        display(ext.carry_law_table())
        display(ext.segmentation_table())
        """),
        markdown("""
        **Segmented trim (r26e).** The coding predicted above was simulated.
        The 31 unit cells per side of the k 1.75 trim are regrouped into
        seven 4-cell segments, selected by a 3-bit thermometer decoder,
        plus binary cells of 2 and 1 for the two LSBs, so one code step
        switches at most 7 cells instead of 31. The nominal transfer is
        identical to the binary one (largest boundary difference 0.00 mV)
        and monotonic at the five conditions (|DNL| ≤ 0.34 LSB). On the
        same 200 seeds at five conditions (first table) it passes ±1 mV at
        1 ns for 1000 of 1000 seeds (0.996–1.000), with no wrong or
        unresolved decision, at the same TT energy (533.08 against
        533.05 fJ) and the same rms |*m*| (0.34 mV). The step spread
        follows the binary fit for 1, 3 and 7 switched cells (second
        table), and local steps above 2 mV fall from 10 to 3 (one-sided
        sign test p = 0.046). The Gaussian law under-predicts both counts
        by about 1.8× (5.8 and 1.6) but predicts the reduction (3.6×
        against 3.3× observed); r26f below finds that the shortfall is
        counting noise plus a small carry drift, not a heavy tail.
        1000 against 999 passing seeds does not resolve the predicted
        0.07 against 0.73 static misses per 1000; that needs about 10⁴
        seeds.

        **The segmented trim as a system (r26e–r26j).** One side is shown; the
        other is identical. The decoder and its gate dip are the subject of
        r26f–r26j below.

        ```text
        trim code c, one side (sign + 5 magnitude bits, set by calibration)
          |
          +-- 2 LSBs ---------------------------------------> LSB switches (2 + 1 cells) --+
          |                                                                               |
          +-- 3 MSBs --> thermometer --> 7 segment gates --> 7 segment switches ----------+
                         decoder         (+ hold capacitor)   (4 unit cells each)         |
                         (CMOS, r26f;          ^                                          v
                         4x pull-down r26i)    |               auxiliary input NFETs (gate vinp
                                               |               or vinn, drain xp or xn) add the
             clock edge: the falling tail -----+               trim current to the core
             kicks each segment gate ("dip")
        ```

        - **Decoder:** turns the 3 MSBs into 7 equal-weight segment-gate levels,
          so a code step switches at most 7 cells instead of 31.
        - **Segment gate and hold capacitor:** the gate node holds the decoded
          level; at the clock edge the tail couples a dip onto it through the
          switch, which weakens the segment (the "loss"). A hold capacitor or a
          stronger decoder pull-down reduces the dip.
        - **Switches and auxiliary pair:** each enabled cell adds a unit of
          trim current on its side, which cancels the core's offset.
        """),
        code("""
        sg = ext.segmented_mc_table(extension)
        display(sg)
        p = sg.attrs["predicted_static_miss"]
        print(f"law, static misses per 1000: binary {p['binary']:.2f}, "
              f"segmented {p['segmented']:.2f}")
        print("steps > 2 mV, one-sided sign test p "
              f"{sg.attrs['tail_sign_test_p']:.3f}")
        display(ext.segmented_law_table())
        """),
        markdown("""
        **Step tails and a real decoder (r26f).** Two loose ends of r26e.
        First, the tail. An exact likelihood model of the observed steps
        (Gaussian; length-biased, because a seed lands in a step with
        probability proportional to its width; quantized on the bisection
        grid) finds normalized kurtosis 3.02 (binary) and 2.80 (segmented),
        Gaussian 3, and a small carry drift of 0.53% of an LSB per switched
        cell (95% CI 0.16–0.89%, likelihood-ratio p = 0.006; positive in 10
        of 10 design-condition fits). With the drift no count is rejected
        (P ≥ observed ≥ 0.15), and the law fitted on the segmented trim
        predicts the binary trim's 15- and 31-cell tail out of sample (8.1
        against 10 steps above 2 mV, first table). The tail is Gaussian.

        Second, the decoder. r26e's ideal sources are replaced by static
        CMOS gates (48 devices per side, L 0.5 µm). The decoder is logically
        correct, adds no measurable energy (533.02 against 533.08 fJ),
        leaks at most 2.93 nA, and keeps the transfer monotonic
        (|DNL| ≤ 0.39 LSB). It is not electrically neutral: at the clock
        edge the falling tail kicks each segment gate down by 113–262 mV
        through the switch's gate capacitance, which an ideal source hides,
        and the segments become 1.5–4.7% weaker than the binary cells
        (second table). The dip is a capacitive divider: one coupling
        capacitance (4.3–5.1 fF) onto one gate-node capacitance
        (11.3–12.1 fF) fits every hold-capacitor and condition point, so a
        longer decoder channel, which slows the recovery 5×, barely changes
        it, while a 4 µm square MOS capacitor on each segment gate restores
        the ideal boundaries within one 0.29 mV bisection step at TT, SS and
        SF, for 224 µm² of gate area (third table). Without the capacitor
        the weaker segments cost no decision: on the same 200 seeds at each
        of the five conditions, with every shared mismatch draw identical,
        the decoder passes static |m| ≤ 1 mV and ±1 mV at 1 ns for 1000 of
        1000 seeds, as the ideal decoder does; 797 seeds keep their code,
        200 move one code outward and 3 one code inward (max |m| 0.82 mV
        for both), and the three largest cold offsets use code 27 of 31.
        At 200 seeds per condition a one-in-1000 effect is not excluded.
        """),
        code("""
        tm = ext.tail_model_table()
        display(tm)
        j = tm.attrs["joint"]
        lo, hi = (100 * x for x in j["delta_ci95"])
        print(f"carry drift {100 * j['delta_hat']:.2f}% LSB per switched "
              f"cell (95% CI {lo:.2f}-{hi:.2f}%), LR p {j['p_delta0']:.4f}")
        dt = ext.decoder_table()
        display(dt)
        e = dt.attrs["energy_fj"]
        print(f"decoder: {dt.attrs['devices']} devices (both sides), "
              f"{dt.attrs['gate_area_um2']:.1f} um2 gate area, leakage "
              f"<= {dt.attrs['leak_worst_na']:.2f} nA ({dt.attrs['leak_cond']})"
              f"; TT energy at code 0 {e['d5_k175']:.2f} fJ "
              f"(ideal decoder {e['g5_k175']:.2f} fJ)")
        display(ext.hold_cap_table(extension))
        """),
        markdown("""
        **A dip law and the cheapest fix (r26g).** r26f left the two binary
        LSB switches on ideal sources. Buffering them with the decoder's own
        output inverter gives them dips too, but smaller ones (TT 72 and
        119 mV for the 1- and 2-cell switches, 179 mV for a 4-cell segment).
        The dip is one capacitive divider, dip = A·m/(m + m0 + c_h·a): m is
        the switch size in unit cells, m0 the driver's output capacitance in
        unit-switch couplings (3.0–4.1) and c_h·a the hold capacitor
        (4.4–6.4 units per µm²). One three-parameter fit per condition covers
        the three buffered switch sizes and the three hold capacitors within
        8%, and predicts out of sample that scaling each driver with its
        switch makes every dip the same, A/(1 + m0), within 8% (first
        table). Equal drivers therefore leave a relative segment error that
        buffering the LSBs does not remove. Scaling the drivers halves the
        range loss for 43 µm² (boundaries bisected to 0.01 mV, second
        table), but a hold capacitor is about 3× more area-efficient: 1 µm
        per segment gate (14 µm²) already loses less over the full span at
        every condition (over the segment span at four of five), because the
        loss per mV of dip grows with driver strength. Along the
        hold-capacitor family the segment loss is roughly proportional to
        the dip (0.024–0.037% per mV at TT, SS and FS), so the law sizes the
        capacitor for a target loss; 2 µm (56 µm²) leaves at most 1.25%.
        """),
        code("""
        display(ext.dip_law_table())
        display(ext.driver_fix_table())
        """),
        markdown("""
        **Why a strong driver costs more per mV (r26h).** To separate the
        gate waveform from the MOS driver, each ideal segment source is put
        behind a linear Thevenin driver: a series resistor, optionally with
        a shunt capacitor to ground, with no junction capacitance and no
        nonlinearity. Eight (R, C) points span TT dips of 41–213 mV. The
        peak dip does not set the loss: at TT a 1 kΩ resistor (64 mV dip)
        loses 4.32% of the segment span, 7 kΩ with 20 fF (68 mV) only
        1.40%. The fast dip of a resistive driver, aligned with the clock
        edge, costs 0.043–0.068% per mV at TT and 0.024–0.060 at SF and FF;
        the slower capacitive-divider dip costs 0.018–0.032 and at most
        0.009. The linear driver therefore reproduces r26g's finding that
        the stronger driver loses more per mV: it follows from the dip's
        shape, not from the MOS device, and it is why the hold capacitor,
        which slows the dip, is the cheaper fix. At SS and FS every linear
        driver costs 0.038–0.050% per mV and the scaled MOS drivers lie in
        that band; there the slow CMOS decoder, with or without hold
        capacitors, loses 8–21% less than the lowest linear driver. A 7 kΩ
        + 10 fF driver and the decoder with 1 µm hold capacitors have the
        same TT dip (103 mV) and loss within 8%, but differ by up to 2.4× at
        the hot corners, so a second-order effect remains; the next table
        locates it.
        """),
        code("""
        display(ext.thevenin_table())
        """),
        markdown("""
        **What the linear model missed: the off gates (r26h).** Matching
        the on gate is not enough: a symmetric linear driver fitted per
        corner to the MOS on-gate dip reproduces that waveform to 0.3% rms
        and still misses the loss (decoder at SS 5.78% against 4.42%,
        1 µm hold capacitors at SF 0.13% against 1.11%). The off (low)
        segment gates also dip, by 22–103 mV, and the MOS driver is not
        symmetric: its NMOS pull-down is stronger (3.0–3.4 kΩ against
        8.0–13.3 kΩ for the pull-up), and the MOS hold capacitor is
        depleted when its gate is low (4.2–4.3 fF against 10.4–11.6 fF of
        gate capacitance). A linear driver whose R and C switch with the
        gate's logic state reproduces all ten MOS losses (two designs, five
        corners) within 0.08 percentage points. Changing only the off-state
        R or only the off-state C shows that the two parts interact: the
        strong pull-down lowers the loss at TT, SS and FS, the depleted
        capacitor raises it at SF and FF. As a fix test, the decoder with an
        ideal linear 8.3 fF capacitor per segment gate (the same on-gate dip
        as the 1 µm MOS capacitor) halves the SF and FF loss (1.11 → 0.48%,
        1.10 → 0.52%) but leaves the worst corner at 2.48% against 2.50%.
        A bias-independent hold capacitor therefore helps the hot corners
        only; the larger MOS capacitors of r26g remain the way to a lower
        worst case.
        """),
        code("""
        display(ext.thevenin_state_table())
        """),
        markdown("""
        **Turning the off-gate finding into a fix (r26i).** Three PDK-only
        changes act on the off state: a 4× NMOS pull-down in the 14 segment
        output inverters (N4, +0.98 µm² gate area per segment gate), a 1 µm
        pfet hold capacitor next to the nfet one (PH1, full capacitance when
        the gate is low, so the pair is nearly state-independent without a
        MIM model), or both. On top of the 1 µm nfet capacitor, N4 lowers
        the worst corner from 2.50% to 2.09% and the SF / FF loss from
        1.11 / 1.10% to 0.32 / 0.16%; PH1 gives 2.16% worst and 0.41 /
        0.26%, better than r26h's ideal linear capacitor. A 4× pull-up
        instead (P4) lowers the dip by about 40% yet raises the hot-corner
        loss, as the dip-shape result predicts. Area-matched, however, a
        larger nfet capacitor still wins the worst corner, which is cold and
        set by the on-gate dip: at about 2 µm² a 1.4 µm capacitor reaches
        1.82% against 2.09% (N4) and 2.16% (PH1), and at about 3 µm² a
        1.72 µm capacitor 1.44% against 1.75% (N4 + PH1). The off-state
        fixes buy the hot corners instead (SF / FF at most 0.32% against
        0.76% at 2 µm²). The design rule stays r26g's: size the nfet hold
        capacitor for the worst corner, and add the cheap 4× pull-down when
        the corner spread matters. The plain 1 µm design rerun through the
        same script reproduces r26g's five losses exactly.
        """),
        code("""
        display(ext.fixes_table())
        """),
        markdown("""
        **Checking the fixes (r26j).** The r26i variants were nominal. r26j
        repeats them under Vth-mismatch Monte Carlo (40 seeds at all five
        conditions, each design paired with the ideal-decoder reference on
        the same seed), with the b1-extracted gate-net capacitance (1.22 fF
        from a segment gate to vss, s, vin, tail and x) added once and four
        times to all 14 segment gates, and with TT energy per decision and
        decoder leakage. Mismatch barely moves the segment loss (standard
        deviation at most 0.14 percentage points per condition, per-condition
        means within 0.15 of nominal, and the mean per-seed worst corner
        within 0.08 of the nominal worst corner), and without the gate net
        every area-matched ranking of r26i holds in all 40 seeds: H1.4 stays below N4 H1 by 0.27 ± 0.07 points and below
        H1 PH1 by 0.36, H1.72 below N4 + PH1 by 0.32, and N4 H1 below H1 by
        0.37. No fix changes TT energy by more than 0.18 fJ out of 451 fJ per
        decision, because the hold capacitors are charged only when a code
        changes (about 53 fJ per toggled 1.4 µm gate, during calibration);
        N4 raises the worst decoder leakage from 2.93 to 4.10 nA (SF,
        1.95 V, 125 C). Layout coupling is where the two fixes part. With the
        extracted gate net, the capacitor-only design loses ground (H1.4
        1.82% → 2.00%) while N4 H1 improves (2.09% → 2.01%), so the
        area-matched pair ties. This is consistent with the strong pull-down
        holding the off gates against the coupling, so that the capacitance
        to vss acts as extra hold; that path was not isolated. At four times the
        extracted capacitance N4 H1 reaches 1.77% against 2.20% for H1.4 and
        1.92% for H1.72. A footprint estimated from SKY130 rules (each extra
        finger or capacitor with its contacted diffusion and half spacing)
        charges N4 more than its gate area: near 5.5 µm² H1.72 gives 1.44%
        (1.55% with the extracted net) against 2.09% (2.01%) for N4 H1. The
        r26b calibration Monte Carlo, rerun for all six fixes (20 seeds at
        each condition), trims every seed and condition to ±1 mV with a
        1 ns decision (largest residual 0.82 mV), as d5 does. The
        rule therefore gains one clause: size the nfet hold capacitor for
        the worst corner with the extracted gate net included, and add the
        4× pull-down when the routed gate net couples more strongly than the
        b1 extraction or the corner spread matters.
        """),
        code("""
        display(ext.verify_table())
        """),
        markdown("""
        **Limits.**

        - **Common.** Only Vth mismatch is modelled, and |*m*| is found by
          bisection to 0.2 mV; 40 seeds per condition are not a yield estimate.
          The cost paragraph above refers to the r13 fix.
        - **6-bit designs (r15–r19).** They have no layout, DRC/LVS or extraction
          of their own; their RC numbers are estimates at code 0 without mismatch,
          their mismatch Monte Carlo covers two conditions without width skew, and
          their 49-condition tests use deterministic width skews, not random
          mismatch. The r18 screen is nominal TT only, and `u6_w12_l05` was chosen
          after seeing it; its own sealed test covers only that one design.
        - **Width skew and hot corners (r20–r22).** Under the binned models the
          atlas width skews are not design-neutral (r20); r21 reruns only the three
          sealed designs with an exact current skew, and for the 6-bit designs only
          their untrimmed offsets. The r22 Monte Carlo adds two hot corners for the
          selected design and one for `lvt_base_3b`.
        - **Noise (r23, r24).** The r23 noise model has no flicker or induced gate
          noise. σn is measured at trim code 0 on nominal devices, so noise from
          switched-on trim branches at the calibrated code is not included, and it
          is combined with the Monte Carlo residuals under a Gaussian assumption
          that 40 realizations cannot check at 10⁻⁶. The r24 ISF shares the r23
          noise model and its linearity; its atlas, common-mode and closed-form
          results use the pinned bench. The gain law's A0 is fitted on the same
          45 conditions it is scored on (held-out corners move it by <1%), and the
          common-mode sweep is one TT condition, not requalified for offset, trim
          or kickback.
        - **Memory and equalizer (r24c, r25).** The memory probe uses ideal
          switches. The equalizer and precharge devices are nominal schematic
          devices with no layout, mismatch or noise of their own in the ISF; the
          6-bit designs get only a spot check at three conditions, and the paired
          fix Monte Carlo covers the selected design at its two hot corners. The
          r25 5-bit trim is likewise schematic only; its length screen is three
          conditions, its full transfer five, and its Monte Carlo the two hot
          corners and TT.
        - **Unit-cell trims (r26–r26d).** The same holds for the r26 and r26b
          trims; the unit cells have no layout, so gradient or proximity mismatch
          among the 2^k cells of a bit is not modelled. In r26c the equalizer and
          inverter devices are nominal, the inverter size was chosen after its
          sweep on nominal transfers, the 1 ns runs use the code from a 0.2 mV
          bisection, and 200 seeds per condition bound a rate only to about 2%.
          The r26d step law is fitted on the coarse bisection candidates with few
          4-bit carries (87 and 100 seeds), assumes Gaussian steps and a residual
          uniform within a step, and its segmented codings are predictions, not
          simulations; at k 1.75 the smallest nominal half range (24.9 mV) is
          close to the largest cold |b0| at 200 seeds (25.7 mV), so a larger k
          needs a cold Monte Carlo with more seeds first.
        - **Segmented trim and decoder (r26e, r26f).** The r26e thermometer
          decoder is an ideal behavioural source with no energy, delay or
          mismatch, and each 4-cell segment is one device with the mismatch of
          four parallel cells. The r26f tail model is fitted on 13 steps above
          2 mV, its drift is a phenomenological term linear in the switched cells,
          and it assumes a residual uniform within a step. The r26f decoder has
          nominal sizing, swept only in channel length; there is no layout, so the
          gate node has no wiring capacitance; the hold capacitor's energy and
          Monte Carlo were not simulated, the divider fit assumes the oxide
          capacitance (8.4 fF/µm²), and its Monte Carlo has 200 seeds per
          condition.
        - **Kickback studies (r26g–r26i).** The r26g buffers, scaled drivers and
          hold capacitors are nominal, without Monte Carlo or energy; they are
          compared by boundaries at codes 0, ±3, ±28 and ±31, not full transfers.
          The r26h Thevenin drivers are ideal linear elements (linear within each
          gate state in the state-aware fit) at nominal conditions; the
          eight-point sweep reports one segment gate's waveform for all fourteen,
          the state-aware drivers are fitted at code −31 only, the path by which
          an off gate couples into the boundary is not isolated, and the linear
          hold capacitor is ideal because the pinned PDK checkout has no MIM
          capacitor model. The r26i variants are nominal ten-design comparisons
          with gate area only.
        - **Fix verification (r26j).** Its 40 seeds are not a yield estimate, and
          the loss is measured from the ±28 boundaries only. Each seed's worst
          corner is the maximum over five conditions, and the worst condition can
          change from seed to seed. One mismatch draw with an undivided sigma
          covers all four fingers of the N4 device, which is conservative for N4;
          the N4 and PH designs' per-condition means move most (up to 0.15
          points), but the paired H1.4 − N4 H1 difference (−0.27 points) equals
          the nominal one. Its gate net is the b1 bit-2 extraction scaled by 1 and
          4 for every segment at nominal conditions, not a routed layout, and a
          larger hold capacitor would probably add wiring capacitance of its own;
          with the net a segment can beat the ideal reference, so a negative loss
          is counted by its magnitude. Its footprint is a design-rule estimate,
          not a drawn cell; its calibration Monte Carlo has 20 seeds per
          condition; and the leakage models have no gate tunnelling.
        """),
        markdown("""
        ## 10. Discussion and limitations

        **Conclusion.** Under the same local calibration policy, the selected
        circuit increases 1 ns correct decisions from 310/392 to 372/392
        across the 49 listed schematic conditions, while mean core energy
        rises from 143.01 to 251.53 fJ/cycle. The post-selection lower-energy
        control reaches 351/392 at 156.65 fJ/cycle. Neither design
        dominates both measured correctness and core energy, which is why
        the atlas asks for an input band first and ranks energy second.

        The separate nominal, code-zero layout study records 156/180
        correct RC decisions at 1 ns and 180/180 at its declared 2 ns
        deadline. A [two-point RC-card sensitivity check](REPRODUCIBILITY.md#bounded-rc-sensitivity-check)
        (28 transients, hypothetical R/C scaling) shows the margin is thin:
        at the slowest archived FS point, C x 1.2 makes the 2 ns decision
        unresolved. A [GDS geometry check](results/study/gds_geometry/README.md)
        restores the interface and measures selected conductor dimensions.

        **What Section 9 adds.** The NONE at ±1 mV is a trim limit, not a
        speed limit; redesigned unit-cell and segmented trims pass ±1 mV in
        all 49 conditions and under mismatch Monte Carlo, the original
        selection survives an exact current-skew rerun, and the ±1 mV counts
        are noiseless (about 4 mV is needed for a 10⁻⁶ error rate at TT).

        **Limitations.**

        - *Simulation, not silicon.* Results are deterministic SKY130
          simulations. Width perturbations are controlled stress, not a
          foundry mismatch distribution or yield; Section 9's Monte Carlo
          seeds are not a yield estimate either.
        - *Archived RC decks.* Layout results come from archived extraction
          decks whose physical fidelity remains unqualified; they are not
          silicon predictions or an isolated measure of resistance. Imported
          RC still differs from the MAG extraction, and isolated sheet/plate
          components are not whole-net parasitic estimates. The sensitivity
          check is neither a measured process-error bound nor a new
          full-grid pass rate.
        - *Finite, post-hoc comparison.* Candidate selection compared a
          finite set of designs at sampled inputs; it is not continuous
          coverage or a global optimum. The post-selection control and
          previously observed PVT conditions do not form a blinded external
          validation set, and energies from different input bands are not a
          same-specification improvement.
        - *Separate populations.* The 49-condition calibrated schematic
          study, earlier five-condition layout experiment and full
          45-condition nominal code-zero study have separate conditions and
          recorded tool identities. Section 9 designs have no layout of
          their own.
        - *Energy scope.* Core-rail energy excludes input/clock drivers and
          calibration infrastructure. DRC/LVS do not establish silicon
          performance or complete foundry signoff.

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
    bootstrap = cells[1].source
    assert bootstrap.count(release_identity.PLACEHOLDER) == 1
    cells[1].source = bootstrap.replace(release_identity.PLACEHOLDER, support_digest)
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook.metadata.update({
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.18"},
    })
    nbf.validate(notebook)
    destination = ROOT / "Comparator_Atlas.ipynb"
    if destination.exists():
        import difflib

        previous = nbf.read(destination, as_version=4)
        matcher = difflib.SequenceMatcher(
            a=[c.source for c in previous.cells], b=[c.source for c in cells], autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    cells[j].id = previous.cells[i].id
    from presentation.judge_decision import integrate_notebook, validate_notebook_outputs

    integrate_notebook(notebook)
    if destination.exists():
        previous = nbf.read(destination, as_version=4)
        if [(c.id, c.source) for c in previous.cells] == [(c.id, c.source) for c in notebook.cells]:
            validate_notebook_outputs(previous)
            for cell, saved in zip(notebook.cells, previous.cells):
                if cell.cell_type == "code":
                    cell.outputs = saved.outputs
                    cell.execution_count = saved.execution_count
                    cell.metadata = saved.metadata
            if "widgets" in previous.metadata:
                notebook.metadata["widgets"] = previous.metadata["widgets"]
    nbf.validate(notebook)
    nbf.write(notebook, destination)
    print(f"Generated {destination.name}: {len(cells)} cells")


if __name__ == "__main__":
    main()

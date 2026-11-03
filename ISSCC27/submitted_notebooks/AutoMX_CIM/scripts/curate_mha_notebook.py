"""Build the evidence-led AutoMX-CIM notebook narrative without running EDA.

Original experiment cells and their historical outputs are preserved. Generated
explanations are marked so rerunning this script is idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "AutoMX_CIM_Sky130_MHA.ipynb"
MARKER = "automx_story_generated"


def lines(body: str) -> list[str]:
    return dedent(body).strip().splitlines(keepends=True)


def guide(title: str, action: str, equation: str, evidence: str) -> str:
    return (
        f"**Cell guide — {title}.** {action}\n\n"
        + "**Equation / acceptance rule:** $$" + equation + "$$\n\n"
        + f"**Readout:** {evidence}"
    )


CODE_GUIDES = {
    2: ("workspace", "Resolve the server checkout and make its packages importable.",
        r"G_{\rm root}=\bigwedge_{p\in\{\mathrm{package,requirements,scripts}\}}\mathbf{1}[p\ {\rm exists}]",
        "A valid absolute ROOT and the selected SKY130 PDK."),
    3: ("tool setup", "Inspect Python and EDA prerequisites before any long run.",
        r"G_{\rm tools}=\bigwedge_i\mathbf{1}[{\rm tool}_i\ {\rm available}]",
        "The prepared server should need no installer; the optional switches remain false."),
    8: ("frozen configuration", "Load the T=4 MHA demonstrator and print its hash.",
        r"H_{\rm cfg}={\rm SHA256}({\rm config\ bytes})",
        "Changing this hash creates a new experiment, not the same receipt chain."),
    10: ("environment receipt", "Record tool paths and PDK discovery.",
         r"G_{\rm env}=\mathbf{1}[{\rm PDK\ found}]\land\bigwedge_i\mathbf{1}[{\rm tool}_i\ {\rm found}]",
         "Missing tools are shown as pending and do not become physical PASS evidence."),
    12: ("MHA reference", "Compare FP32 attention with the quantized projection path.",
         r"Q=XW_Q,\quad K=XW_K,\quad V=XW_V,\quad O={\rm softmax}(QK^\mathsf{T}/\sqrt{d_k})V",
         "Shapes, row-normalized probabilities, error metrics, and Stage-1 receipt."),
    14: ("tile schedule", "Build the dependency graph for one reused logical 32×8 tile.",
         r"N_{\rm macro/call}=\lceil32/4\rceil\lceil8/4\rceil=16",
         "The command count and Q/K/V-to-attention dependency order."),
    16: ("vector contract", "Inspect exported MXFP4/QTEA vectors and block scales.",
         r"x_k=2^{E-128}\,a_k/2",
         "Vector-manifest presence and the encoded block shapes."),
    18: ("macro contract", "Read the shared pin and view contract before physical work.",
         r"w_{r,c}=W^+_{r,c}-W^-_{r,c}\in\{-1,0,+1\}",
         "The 4×4 passive-core contract and separate pending wrapper contract."),
    20: ("Stage 4 SPICE", "Generate and, when enabled, simulate cell-to-macro decks.",
         r"s_c=\sum_{r=0}^{3}a_r(W^+_{r,c}-W^-_{r,c})",
         "Only hash-matched ngspice PASS receipts count as Stage-4 evidence."),
    22: ("Stage 5 layout", "Run or inspect core GDS/LEF, DRC, LVS, PEX and post-layout receipts.",
         r"G_5=G_{\rm DRC}\land G_{\rm LVS}\land G_{\rm PEX}\land G_{\rm post}",
         "This gate covers the passive core; it does not certify an ADC or wrapper."),
    24: ("Stage 6 model", "Fit a TT transfer model from validated physical samples.",
         r"\widehat V_c(s)=b_c+g_cs,\qquad e_c=V_c-\widehat V_c",
         "Model and MHA extrapolation counts are architectural diagnostics."),
    26: ("PEX coverage", "Resume the TT passive-core PEX screen from validated checkpoints.",
         r"C_{\rm screen}=N_{\rm measured}/N_{\rm planned}",
         "101 completed jobs are required by the later transfer diagnostic; the 27-point PVT extension stays disabled."),
    28: ("transfer diagnosis", "Resume matched schematic/PEX samples and inspect differential-level reversals.",
         r"\Delta V_c(s)=V_{{\rm BLN},c}(s)-V_{{\rm BLP},c}(s)",
         "Overlap is a measured physical limitation; a timeout only means some of the 22 matched simulations remain incomplete."),
    29: ("diagnostic report", "Read the saved transfer findings without new SPICE.",
         r"N_{\rm overlap}=\sum_{c,s}\mathbf{1}[I_c(s)\cap I_c(s+1)\ne\varnothing]",
         "Level overlap motivates the later 2+2 read experiment."),
    31: ("schematic design space", "Sweep selected load and PWM settings.",
         r"\Delta V=f(C_{\rm BL},t_{\rm PWM},s)\big|_{\rm TT}",
         "A positive selected-case gap is a candidate, not an ADC guarantee."),
    33: ("candidate PEX", "Recheck promising settings with extracted parasitics.",
         r"\epsilon_{\rm PEX}=|\Delta V_{\rm PEX}-\Delta V_{\rm schematic}|",
         "Selected PEX comparisons do not replace the full TT screen."),
    35: ("checkpoint inventory", "Count resumable simulations before the full TT run.",
         r"C_{\rm checkpoint}=N_{\rm valid\ receipts}/N_{\rm planned}",
         "Hash validation, rather than filename alone, controls reuse."),
    36: ("101-case TT screen", "Measure all original core patterns at the candidate load.",
         r"g_{\min}=\min_{c,s}\{\min I_c(s+1)-\max I_c(s)\}",
         "A positive measured gap supports only this TT sample set."),
    38: ("independent TT holdout", "Test new MHA patterns after fitting on training data.",
         r"R_{\rm holdout}=N_{\rm decode\ errors}/N_{\rm holdout\ samples}",
         "Zero deterministic errors do not establish a silicon error rate."),
    40: ("readiness inventory", "Inspect dependencies without manufacturing receipts.",
         r"G_{\rm next}=\bigwedge_i G_i",
         "The first false prerequisite blocks the dependent stage."),
    42: ("scalar decoder", "Freeze midpoint thresholds on training levels.",
         r"\theta_{c,s}=\{\mu_c(s)+\mu_c(s+1)\}/2",
         "Evaluate the held-out data only after thresholds are frozen."),
    43: ("decoder detail", "Read per-column mismatch and margin fields.",
         r"m_{\min}=\min_i|\Delta V_i-\theta_{\rm nearest}|",
         "A margin below the target budget remains a failure."),
    44: ("training/holdout comparison", "Compare two reports without resimulation.",
         r"\Delta R=R_{\rm holdout}-R_{\rm training}",
         "A wider holdout error exposes calibration limits."),
    46: ("expanded calibration", "Add reachable signed sums to the training set.",
         r"S_c=\{\sum_{r=0}^{3}a_rw_{r,c}\mid a,w\ {\rm legal}\}",
         "The previously inspected holdout is no longer independent."),
    47: ("feature screens", "Read candidate feature-space diagnostics.",
         r"V_{\rm CM}=(V_{\rm BLP}+V_{\rm BLN})/2",
         "Common-mode dependence cannot be fixed by relabeling thresholds."),
    49: ("fresh calibration holdout", "Use a later MHA rank range after fitting.",
         r"R_{\rm fresh}=N_{\rm wrong}/N_{\rm fresh}",
         "Fresh patterns are not used to refit a reported model."),
    51: ("decoder architecture", "Compare differential and common-mode features offline.",
         r"\widehat s=f(\Delta V,V_{\rm CM},\mathrm{activity})",
         "An offline score does not prove a physical ADC transfer."),
    53: ("targeted 2+2 PEX", "Split one four-row operation into two precharged reads.",
         r"s_c=s_{A,c}+s_{B,c}",
         "Analog voltage levels of each phase still need measurement."),
    55: ("signed-level 2+2 screen", "Measure reachable partial-sum levels.",
         r"g_{\min,A/B}=\min_{c,s}\{\min I_{c,A/B}(s+1)-\max I_{c,A/B}(s)\}",
         "Training margin is checked separately for each phase."),
    57: ("frozen 2+2 holdout", "Decode two fresh phase measurements and add them digitally.",
         r"\widehat s_c=\widehat s_{A,c}+\widehat s_{B,c}",
         "Report partial and combined errors plus common-mode excursion."),
    59: ("PVT smoke", "Inspect a few selected cases across the modeled corners.",
         r"g_{\rm worst}=\min_{p\in{\cal P}_{\rm smoke}}g_{\min}(p)",
         "A smoke set is narrower than the required full PVT matrix."),
    61: ("Stage 7 RTL", "Regress the base-only controller against the fixed-point oracle.",
         r"A_{\rm next}=A_{\rm prev}+(2^{E-128}/2)s_c",
         "Simulation PASS certifies protocol/arithmetic, not analog conversion."),
    63: ("RTL stress", "Exercise reset, backpressure, and protocol corner cases.",
         r"G_{\rm RTL}=\bigwedge_{t\in{\cal T}}\mathbf{1}[t\ {\rm passes}]",
         "The stress receipt is separate from the baseline regression."),
    65: ("logical 2+2 regression", "Verify the two-read transaction count and sum.",
         r"N_{\rm reads}=N_A+N_B=16+16",
         "The Verilator macro substitutes an ideal digital model."),
    67: ("strict prototype gate", "Check whether a physical wrapper exists.",
         r"G_{\rm proto}=G_{\rm GDS}\land G_{\rm LEF}\land G_{\rm analog\ blocks}",
         "This gate remains blocked without real precharge/sample/ADC layout."),
    69: ("digital-only smoke", "Keep the synthesized 2+2 surrogate separate.",
         r"A_{\rm surrogate}=A_{\rm standard\ cells}",
         "It contains no passive CIM core and is not the core-bound GDS."),
    71: ("strict Stage 8 preflight", "Check the full clocked-wrapper requirements.",
         r"G_8=G_{\rm GDS}\land G_{\rm LEF}\land G_{\rm LIB}\land G_{\rm SPEF}\land G_{\rm ADC/PVT}",
         "Core-bound success does not make this strict gate pass."),
    73: ("evidence ledger", "Summarize only visible receipts and top-run reports.",
         r"G_{\rm claim}=\bigwedge_{i\in{\cal R}}\mathbf{1}[{\rm evidence}_i\ {\rm verified}]",
         "A claim is limited by its least complete required evidence."),
    75: ("GDS image", "Render or load the actual core-bound top layout.",
         r"A_{\rm die}=500\,\mu{\rm m}\times500\,\mu{\rm m}=0.25\,{\rm mm}^2",
         "The PNG is a visualization of the GDS, not a new DRC/LVS result."),
}


MARKDOWN_REPLACEMENTS = {
    0: r"""
        # AutoMX-CIM: from MXFP4 tiny MHA to a SKY130 core-bound GDS

        **Notebook objective.** Follow the software/hardware co-design chain from
        a numerical MHA reference through ternary CIM circuits, extracted
        characterization, RTL protocol, OpenLane physical integration, and the
        rendered top-level GDS. The presentation follows the reference SNN
        notebook's sequence: background → framework → software model → circuit
        and RTL checks → implementation → result image.

        **Verified endpoint (2026-10-08).** The GDS named
        **automx_cim_core_bound_demo** contains the real 4×4 passive CIM core
        macro and placed/routed digital two-phase control. The clean01 OpenLane
        run completed with zero route, Magic GDS DRC, KLayout DRC, LEF-macro LVS,
        and antenna violations; post-route STA still reports **57 max-fanout
        violations**. Its analog phase engine, precharge, sample/hold and ADC
        remain external. This is a core-bound prototype, not the completed
        on-chip mixed-signal wrapper.

        Existing execution outputs in earlier cells are **historical notebook
        outputs**. On the prepared Linux server, **Run All** reruns Stage 4/5 and
        RTL, then starts a new core-bound OpenLane run through Docker if its tag
        is absent, audits the final GDS, and renders it. A repeated Run All
        verifies the same tagged run. It can take hours; a failed prerequisite
        stops execution and must be fixed before a GDS claim. On this Windows
        checkout the notebook only reads an already copied run and never starts
        EDA. Set `AUTOMX_CIM_ROOT`, `AUTOMX_STAGE5_PDK_ROOT`,
        `AUTOMX_OPENLANE_SOURCE`, `AUTOMX_OPENLANE_PDK_ROOT`, and
        `AUTOMX_CORE_BOUND_TAG` when the server paths differ from defaults.
    """,
    4: r"""
        ## 1. Motivation and notebook objective

        Transformer projections repeatedly move weights between memory and
        arithmetic. AutoMX-CIM investigates a ternary differential accumulation
        close to storage, with block scaling, QTEA correction and attention
        operations in the digital path. For input matrix X and projection W,

        $$
        Q=XW_Q,\quad K=XW_K,\quad V=XW_V,\qquad
        O={\rm softmax}(QK^\mathsf{T}/\sqrt{d_k})V.
        $$

        This notebook demonstrates the **physical 4×4 CIM core** and the
        **core-bound digital top**. Their scope and remaining sign-off work are
        stated next to every result.
    """,
    6: r"""
        ## 3. Proposed framework and IP specification

        The experiment is ordered so each downstream claim can be traced to an
        input model, layout view, measurement, or regression receipt.

            tiny MHA reference + MXFP4/QTEA vectors
                       ↓
            logical 32×8 tile schedule and RTL
                       ↓
            SKY130 cell → columns → 4×4 passive CIM GDS/LEF/PEX
                       ↓
            TT decoder and 2+2 analog diagnostic
                       ↓
            2+2 digital controller + passive-core macro
                       ↓
            OpenLane core-bound GDS → DRC/LVS/STA reports → PNG

        The strict clocked mixed-signal wrapper is a separate pending branch.
        Its missing on-chip sense/ADC and sign-off views are never inferred from
        the core-bound image.

        | Boundary | Inputs | Outputs | Physical status |
        |---|---|---|---|
        | 4×4 passive CIM | ternary P/N weights, signed WLP/WLN pulses | differential BLP/BLN | GDS/LEF/PEX with core DRC/LVS |
        | 2+2 digital controller | configuration, activation, phase/ADC handshake | partial-sum accumulation, phase requests | synthesized and routed in core-bound top |
        | Analog front end | bitlines and phase timing | sampled/converted partial results | external in this prototype |
    """,
    25: r"""
        ### 4.5 Passive-core PEX coverage screen (not ADC sign-off)

        This TT screen has 85 full-code/active-row cases and 16 deterministic
        MHA-derived cases. Each ngspice job uses the Stage-5 extracted core,
        an external precharge circuit and a late 1.9 ns sample. The cell allows
        **600 s per job** because some PEX simulations exceed the former 180 s
        limit. It validates the saved receipt, deck hashes, PEX/model hashes
        and ngspice log measurements before reusing completed jobs. A failed
        job can therefore be retried without deleting prior valid results.

        $$C_{\rm screen}=N_{\rm completed}/101.$$

        `FULL_PVT_CORE_SCREEN=False` keeps this at one TT point. Its result is
        passive-core coverage only; it does not verify a physical ADC or
        full PVT wrapper.
    """,
    27: r"""
        ### 4.6 TT core transfer diagnosis (not ADC sign-off)

        The completed 101-case TT receipt identifies adjacent signed-sum
        overlaps, then selects matched schematic and PEX decks for the worst
        pairs and active-zero controls. There are 11 selected cases and two
        views each. The cell allows **600 s per simulation** and resumes only
        measurements whose deck, model/view hashes and saved ngspice log agree.
        It compares each PEX late sample with cell 4.5 again before reporting
        a completed diagnostic.

        $$N_{\rm matched}=2N_{\rm selected}=22,\qquad
        \Delta V_c=V_{{\rm BLN},c}-V_{{\rm BLP},c}.$$

        `OVERLAP_OBSERVED` is a physical transfer finding, not a script error.
        `MEASURED_DIAGNOSTIC` means all selected simulations completed; it
        does not certify a sense circuit, ADC or PVT corner.
    """,
    60: r"""
        ## 5. RTL simulation and SKY130 core-bound top implementation

        ### 5.1 Stage 7: verify the base-only 32×8 macro controller

        The controller reuses physical 4×4 tiles for a logical 32×8 operation.
        Verilator substitutes an architectural macro model, checks transaction
        order, Q24 accumulation, scaling, ready/valid backpressure, and result
        latency against the Python oracle. It does not model physical sensing.
    """,
    70: r"""
        ### 5.2 Strict Stage-8 wrapper preflight: still blocked

        The core-bound top is a useful implemented integration prototype, but
        this stricter gate needs a clocked physical wrapper with on-chip
        precharge, sample/hold, sense/ADC, GDS/LEF/LIB/SPEF and corresponding
        composite LVS/PEX, timing, ADC transfer and PVT evidence. The passive
        core GDS plus digital controller cannot satisfy those requirements.
        A BLOCKED preflight is the correct reported result.
    """,
    72: r"""
        ## 6. Results and evidence-backed claim

        The table below reads the selected tagged run. Its reported
        DRC/LVS/antenna values refer to the OpenLane **external-analog
        core-bound design**. The LVS is LEF-macro connectivity, not a
        transistor-level composite wrapper LVS. The known 57 max-fanout
        violations keep the clean01 variant below a timing-clean sign-off claim.
        The selected run's GDS and reports are inspected here; a complete
        input-snapshot audit still belongs on the server that ran OpenLane.
    """,
    74: r"""
        ### 6.1 Render the actual core-bound top GDS

        The output image follows the reference SNN notebook's final
        implementation-result section. The OpenLane die is 500 µm × 500 µm
        (0.25 mm²); the small region near the left side contains the passive CIM
        macro, while the digital cells and routes occupy the rest of the top.
        The figure is a **layout visualization**, not evidence of ADC completion.

        On the prepared Linux server, the core-bound runner creates the PNG.
        When the PNG is absent, this cell uses:

            xvfb-run -a klayout -z -x -r scripts/render_gds_klayout.py

        KLayout 0.26.2 requires the hidden-view mode **-z** and an X display
        connection; the server uses Xvfb. If xvfb-run is missing there, install
        xvfb and xauth on the server. A copied PNG is displayed directly on a
        machine without EDA tools.
    """,
    76: r"""
        ## 7. Reproduction boundary and next physical milestone

        1. Reproduce the numerical MHA, MXFP4/QTEA vectors and tile schedule.
        2. Keep Stage-4/5 PASS receipts with the passive-core GDS/LEF/PEX views.
        3. Run TT transfer, 2+2 read diagnostics and the logical RTL regression.
        4. Bind that core and digital two-phase controller in the core-bound
           OpenLane design. Preserve the run tag and input hashes. On the
           prepared server, copy the **whole updated checkout**, launch Jupyter
           from its root and use **Run All**. Cell 5.1f invokes the pinned
           OpenLane Docker image itself; it does not need `make mount`.
        5. Read route, Magic/KLayout DRC, LEF-macro LVS, antenna and STA reports;
           render the final GDS as a PNG.
        6. For a true on-chip mixed-signal top, finish the clocked analog
           wrapper, ADC transfer/noise/PVT, composite LVS/PEX, LIB/SPEF and
           timing/fanout repairs. The current image does not close these gates.

        Launch Jupyter from the Linux host, with the kernel in the same
        environment used for Stage 4/5:

        ```bash
        cd /home/nam/Vihn/interface_verify/fpga_export_18x18_mnist_softreset/test_folder/AutoMX-CIM
        export AUTOMX_CIM_ROOT="$PWD"
        export AUTOMX_STAGE5_PDK_ROOT=/home/nam/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A
        export AUTOMX_OPENLANE_SOURCE=/home/nam/dependencies/openlane_src
        export AUTOMX_OPENLANE_PDK_ROOT=/home/nam/.volare_openlane_30ee138_nam
        export AUTOMX_CORE_BOUND_TAG=core_bound_notebook_20261008_01
        jupyter lab AutoMX_CIM_Sky130_MHA.ipynb
        ```

        The Docker image must already be available locally and `xvfb-run`,
        `xauth`, `klayout`, `ngspice`, Magic, Netgen and Verilator must be in
        the server environment. The final GDS is under
        `openlane/automx_cim_core_bound_demo/runs/<tag>/results/final/gds/`;
        its PNG and receipt are under `results/sky130/` and
        `results/receipts/notebook_core_bound.json`.
    """,
}


CODE_REPLACEMENTS = {
    2: r"""
        # Find the checkout rather than assuming one absolute server path.
        from pathlib import Path
        from hashlib import sha256
        import os
        import sys

        candidates = []
        if os.environ.get("AUTOMX_CIM_ROOT"):
            candidates.append(Path(os.environ["AUTOMX_CIM_ROOT"]).expanduser())
        current = Path.cwd().resolve()
        candidates.extend([current, *current.parents])
        candidates.extend([path / "AutoMX-CIM" for path in list(candidates)])
        ROOT = next((path.resolve() for path in candidates
                     if (path / "automx_cim").is_dir()
                     and (path / "scripts/curate_mha_notebook.py").is_file()), None)
        if ROOT is None:
            raise FileNotFoundError("AutoMX-CIM checkout missing; set AUTOMX_CIM_ROOT")
        os.environ["AUTOMX_CIM_ROOT"] = str(ROOT)
        os.environ.setdefault("PDK", "sky130A")
        # Stage-5 ngspice/Magic uses the characterized PDK. The later OpenLane
        # Docker image uses AUTOMX_OPENLANE_PDK_ROOT, a separate installation.
        default_stage5 = Path(
            "/home/nam/.volare/volare/sky130/versions/"
            "bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A")
        stage5_pdk = os.environ.get("AUTOMX_STAGE5_PDK_ROOT")
        if stage5_pdk or default_stage5.is_dir():
            selected_stage5 = Path(stage5_pdk or default_stage5).expanduser()
            if selected_stage5.name != "sky130A":
                raise ValueError("AUTOMX_STAGE5_PDK_ROOT must point at sky130A")
            # Volare's .magicrc appends $PDK to $PDK_ROOT. Point PDK_ROOT at
            # the parent version directory to avoid sky130A/sky130A.
            os.environ["PDK_ROOT"] = str(selected_stage5.parent)
        os.chdir(ROOT)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        print("AutoMX-CIM root:", ROOT)
        print("Stage-5 PDK_ROOT:", os.environ.get("PDK_ROOT", "not set"))
        print("OpenLane PDK_ROOT:", os.environ.get(
            "AUTOMX_OPENLANE_PDK_ROOT", "/home/nam/.volare_openlane_30ee138_nam"))
    """,
    73: r"""
        import csv
        import json
        from pathlib import Path

        def receipt_status(relative):
            path = ROOT / relative
            if not path.is_file():
                return "NOT_COPIED"
            try:
                return json.loads(path.read_text(encoding="utf-8")).get("status", "UNKNOWN")
            except (OSError, ValueError):
                return "UNREADABLE"

        stage_labels = [
            ("Tiny MHA reference", "results/receipts/stage1_mha_tiny.json"),
            ("Passive-core Stage 5", "results/receipts/physical/stage5_summary.json"),
            ("2+2 logical RTL", "results/receipts/stage7_2p2_regression.json"),
            ("Strict wrapper preflight", "results/receipts/stage8_preflight.json"),
        ]
        for label, relative in stage_labels:
            print(f"{label:30s}: {receipt_status(relative)}")

        if CORE_BOUND_RUN is None:
            print("Core-bound run: NOT_COPIED")
        else:
            print("Core-bound run:", CORE_BOUND_RUN.relative_to(ROOT))
            print("OpenLane flow:", CORE_BOUND_METRICS.get("flow_status", "UNKNOWN"))
            for field in ("tritonRoute_violations", "Magic_violations",
                          "klayout_violations", "lvs_total_errors",
                          "pin_antenna_violations", "net_antenna_violations"):
                print(f"  {field}: {CORE_BOUND_METRICS.get(field, 'UNKNOWN')}")
            print("Top GDS:", CORE_BOUND_GDS.relative_to(ROOT))
            print("Top GDS SHA-256:", CORE_BOUND_GDS_SHA256)
            print("CIM core reachable in GDS:", CORE_REACHABLE)
            print("Post-route max fanout violations:", FANOUT_VIOLATIONS)

        print("Claim: physical passive core + digital two-phase core-bound GDS.")
        print("Excluded: on-chip sample/hold, sense/ADC, composite LVS/PEX, full PVT.")
    """,
    75: r"""
        from IPython.display import Image, display
        import os
        import shutil
        import struct
        import subprocess
        import sys

        png_path = ROOT / "results/sky130" / f"{clean_tag}_top.png"
        if (clean_tag == "core_bound_20261008_clean01"
                and not png_path.is_file()):
            old_png = ROOT / "results/sky130/core_bound_clean01_top.png"
            if old_png.is_file():
                png_path = old_png
        render_script = ROOT / "scripts/render_gds_klayout.py"
        if (not png_path.is_file() and CORE_BOUND_GDS is not None
                and sys.platform == "linux"
                and shutil.which("xvfb-run") and shutil.which("klayout")):
            render_env = os.environ.copy()
            render_env["AUTOMX_GDS"] = str(CORE_BOUND_GDS.resolve())
            render_env["AUTOMX_PNG"] = str(png_path.resolve())
            subprocess.run(
                ["xvfb-run", "-a", "klayout", "-z", "-x", "-r", str(render_script)],
                cwd=ROOT, env=render_env, check=True,
            )

        if png_path.is_file():
            with png_path.open("rb") as stream:
                header = stream.read(24)
            if len(header) < 24 or header[:8] != bytes.fromhex("89504e470d0a1a0a"):
                raise ValueError(f"Invalid PNG: {png_path}")
            width, height = struct.unpack(">II", header[16:24])
            verified_gds = (CORE_REACHABLE and CORE_BOUND_GDS is not None
                            and (clean_tag != "core_bound_20261008_clean01"
                                 or CORE_BOUND_GDS_SHA256 == expected_gds_sha256))
            print(f"Core-bound PNG: {png_path.relative_to(ROOT)}")
            print(f"Image size: {width} × {height} pixels")
            print("Matching copied GDS and reachable passive core:", verified_gds)
            print("Figure scope: passive CIM macro + routed digital controller;"
                  " analog front end external.")
            display(Image(filename=str(png_path), width=900))
        else:
            print("PNG not copied yet:", png_path)
            print("Copy the server PNG here, or on the server install xvfb/xauth and rerun this cell.")
            print("GDS:", CORE_BOUND_GDS if CORE_BOUND_GDS is not None else "NOT_COPIED")
    """,
}


EXTRA_BEFORE = {
    60: [
        (
            r"""
            ### 4.14 Loaded 2+2 TT diagnostic and common mode

            The first wrapper-load candidate allocates 800 fF to the bitline
            and 20 fF to a proposed sampling node:

            $$
            C_{\rm load}=C_{\rm BL}+C_{\rm SH}=800+20=820\ {\rm fF},
            \qquad V_{\rm CM}=(V_{\rm BLP}+V_{\rm BLN})/2.
            $$

            The server console reported 174/174 TT simulations with zero
            partial/combined decode mismatches, but **58 holdout samples
            outside the training common-mode range**. A later idle-augmented
            74/74 diagnostic still reported **91** outside-range samples.
            These are passive-core TT diagnostics, not ADC or wrapper PASS
            results. **Optional inspection cell:** skip 4.14 when running
            through to the core-bound GDS. It only reads saved JSON and does
            not supply data to later notebook cells. A missing idle report
            means only that the optional JSON is absent under `ROOT`;
            it does not invalidate the earlier 820 fF measurement.
            """,
            r"""
            import json

            load_reports = {
                "820 fF full TT": ROOT / "results/sky130/wrapper_load_full_tt/c820ff/measured.json",
                "idle-augmented TT": ROOT / "results/sky130/wrapper_idle_augmented_tt/c820ff/measured.json",
            }
            for label, path in load_reports.items():
                if not path.is_file():
                    print(label, ": MISSING_OPTIONAL_REPORT at", path.relative_to(ROOT))
                    continue
                report = json.loads(path.read_text(encoding="utf-8"))
                print(label, ":", report.get("status"), report.get("conclusion"))
                print("  simulations:", report.get("completed_sims",
                      report.get("completed_new_sims")), "/",
                      report.get("planned_sims", report.get("planned_new_sims")))
                print("  holdout:", report.get("summary", {}))
            """,
        ),
        (
            r"""
            ### 4.15 Schematic sample/hold and edge timing

            Three TT switch-level candidate cases were run with an ideal
            sampling control. The server log reported a maximum held
            differential drift of about 1 µV, but up to 24.813 mV difference
            from the original loaded bitline. The test isolates acquisition
            error from hold drift:

            $$
            e_{\rm acquire}=|V_{\rm hold}(t_s)-V_{\rm BL}(t_s)|,\qquad
            e_{\rm drift}=|V_{\rm hold}(t)-V_{\rm hold}(t_s)|.
            $$

            These candidate switches have no layout PEX, ADC/noise/PVT or
            complete wrapper sign-off. **Optional inspection cell:** skip 4.15
            when running through to the core-bound GDS. It only reads saved
            JSON and does not supply data to later notebook cells. Missing
            reports mean the three files are absent under `ROOT`, not that a
            simulation was run and failed.
            """,
            r"""
            import json

            analog_paths = {
                "sample/hold TT": ROOT / "results/sky130/wrapper_sample_hold_tt/measured.json",
                "sample/hold decomposition": ROOT / "results/sky130/wrapper_sample_hold_tt/decomposition.json",
                "sample/hold edge": ROOT / "results/sky130/wrapper_sample_hold_edge_tt/measured.json",
            }
            for label, path in analog_paths.items():
                if not path.is_file():
                    print(label, ": MISSING_OPTIONAL_REPORT at", path.relative_to(ROOT))
                    continue
                report = json.loads(path.read_text(encoding="utf-8"))
                print(label, ":", report.get("status"), report.get("conclusion", ""))
                print("  summary:", report.get("summary", {}))
            """,
        ),
    ],
    70: [
        (
            r"""
            ### 5.1e Bind the physical CIM core to two-phase digital control

            The core-bound top instantiates the real Stage-5 **passive 4×4
            macro** and the synthesized 2+2 periphery controller. Its ports
            expose WLP/WLN drives, BLP/BLN bitlines, phase handshake and
            external ADC partial results. The digital accumulation rule is

            $$
            s_c=s_{A,c}+s_{B,c},\qquad
            A_{\rm next}=A_{\rm prev}+\operatorname{scale}(s_c,E8M0).
            $$

            The external phase engine supplies pulse timing; precharge,
            sample/hold and conversion are not cells inside this GDS.
            """,
            r"""
            from pathlib import Path

            bridge_files = {
                "top RTL": ROOT / "rtl/automx_cim_core_bound_demo.sv",
                "two-phase controller": ROOT / "rtl/automx_cim_2p2_periphery_ctrl.sv",
                "core GDS": ROOT / "physical/sky130/macro/automx_ternary_cim_4x4_core.gds",
                "core LEF": ROOT / "physical/sky130/macro/automx_ternary_cim_4x4_core.lef",
                "OpenLane config": ROOT / "openlane/automx_cim_core_bound_demo/config_clean.json",
            }
            for label, path in bridge_files.items():
                print(f"{label:22s}: {'present' if path.is_file() else 'NOT_COPIED'}")
            rtl_text = bridge_files["top RTL"].read_text(encoding="utf-8")
            print("Explicit core instance:", "automx_ternary_cim_4x4_core core_i" in rtl_text)
            print("Explicit controller instance:", "automx_cim_2p2_periphery_ctrl ctrl_i" in rtl_text)
            print("Analog phase/ADC at top ports:", all(
                port in rtl_text for port in ("phase_done_i", "adc_partials_i", "BLP0", "BLN0")))
            print("Logical 2+2 receipt:",
                  json.loads((ROOT / "results/receipts/stage7_2p2_regression.json")
                             .read_text(encoding="utf-8")).get("status"))
            """,
        ),
        (
            r"""
            ### 5.1f OpenLane core-bound implementation

            OpenLane receives the controller RTL, the passive-core blackbox,
            the Stage-5 LEF/GDS pair and a fixed macro placement. It synthesizes
            and routes the digital cells around the macro. The die is fixed at
            500 µm × 500 µm:

            $$
            A_{\rm die}=500^2\ \mu{\rm m}^2=0.25\ {\rm mm}^2.
            $$

            The server uses the separate clean01 config. The pinned OpenLane
            Docker image is launched by `scripts/run_notebook_core_bound.py`.
            The equivalent command inside the container is:

                /openlane/flow.tcl -design "$PROJECT/openlane/automx_cim_core_bound_demo" \
                  -config_file "$PROJECT/openlane/automx_cim_core_bound_demo/config_clean.json" \
                  -tag "$AUTOMX_CORE_BOUND_TAG"

            The clock constraint is 20 ns, giving
            $f_{\rm clk}=1/T_{\rm clk}=50\ {\rm MHz}$ for the digital timing
            model. It does not constrain an on-chip ADC, since that circuit
            is absent.

            On Linux, the following cell builds a missing tagged run, audits
            its top GDS and renders a PNG. The default fresh tag is
            `core_bound_notebook_20261008_01`; `AUTOMX_CORE_BOUND_TAG` can
            override it. A completed run is reused only when its frozen input
            snapshot matches. Otherwise a new tag is allocated automatically.
            On Windows this
            cell only reads the copied `core_bound_20261008_clean01` run.
            `AUTOMX_RUN_OPENLANE=0` selects read-only mode on Linux.

            This produces the **external-analog core-bound** GDS. The separate
            clocked on-chip sample/hold and ADC wrapper remains unbuilt.
            """,
            r"""
            import csv
            import os
            import subprocess
            import sys
            from hashlib import sha256
            from scripts.run_stage8_core_bound_demo import _gds_hierarchy, _gds_reaches

            server_mode = sys.platform == "linux" and os.environ.get(
                "AUTOMX_RUN_OPENLANE", "1") != "0"
            default_tag = ("core_bound_notebook_20261008_01" if server_mode
                           else "core_bound_20261008_clean01")
            requested_tag = os.environ.get("AUTOMX_CORE_BOUND_TAG", default_tag)
            if server_mode:
                from scripts import run_notebook_core_bound as notebook_flow
                clean_tag = notebook_flow.select_tag(ROOT, requested_tag)
                print("Selected OpenLane tag:", clean_tag, flush=True)
            else:
                clean_tag = requested_tag
            if server_mode:
                command = [sys.executable,
                           str(ROOT / "scripts/run_notebook_core_bound.py"),
                           "--root", str(ROOT), "--tag", clean_tag]
                print("Running or auditing core-bound OpenLane tag:", clean_tag,
                      flush=True)
                subprocess.run(command, cwd=ROOT, check=True)
            design_dir = ROOT / "openlane/automx_cim_core_bound_demo"
            run_candidates = [design_dir / "runs" / clean_tag, design_dir / clean_tag]
            CORE_BOUND_RUN = next(
                (p for p in run_candidates if (p / "reports/metrics.csv").is_file()), None)
            CORE_BOUND_METRICS = {}
            CORE_BOUND_GDS = None
            CORE_BOUND_GDS_SHA256 = None
            CORE_REACHABLE = False
            expected_gds_sha256 = "9ad5eb688e16e0fa855778a5cb13a28308decc97960a96fcc99f14741bd21bfa"

            if CORE_BOUND_RUN is None:
                raise FileNotFoundError(
                    f"OpenLane run {clean_tag} is missing. On Linux check "
                    "Stage-5 PASS and the OpenLane Docker prerequisites, then "
                    "rerun this cell. On Windows copy the completed server run.")
            else:
                with (CORE_BOUND_RUN / "reports/metrics.csv").open(
                        encoding="utf-8-sig", newline="") as stream:
                    rows = list(csv.DictReader(stream))
                if len(rows) != 1:
                    raise ValueError("Expected one metrics row for clean01")
                CORE_BOUND_METRICS = rows[0]
                CORE_BOUND_GDS = CORE_BOUND_RUN / (
                    "results/final/gds/automx_cim_core_bound_demo.gds")
                if not CORE_BOUND_GDS.is_file():
                    raise FileNotFoundError(CORE_BOUND_GDS)
                CORE_BOUND_GDS_SHA256 = sha256(CORE_BOUND_GDS.read_bytes()).hexdigest()
                graph = _gds_hierarchy(CORE_BOUND_GDS)
                CORE_REACHABLE = _gds_reaches(
                    graph, "automx_cim_core_bound_demo",
                    "automx_ternary_cim_4x4_core")
                print("OpenLane:", CORE_BOUND_METRICS.get("flow_status"))
                print("Top GDS:", CORE_BOUND_GDS.relative_to(ROOT))
                print("GDS SHA-256:", CORE_BOUND_GDS_SHA256)
                if clean_tag == "core_bound_20261008_clean01":
                    print("Matches copied clean01:",
                          CORE_BOUND_GDS_SHA256 == expected_gds_sha256)
                else:
                    print("Fresh tagged run; GDS hash recorded above")
                print("Physical CIM reachable:", CORE_REACHABLE,
                      "GDS structures:", len(graph))
                print("Die area mm²:", CORE_BOUND_METRICS.get("DIEAREA_mm^2"))
                print("Digital clock period ns:", CORE_BOUND_METRICS.get("CLOCK_PERIOD"))
            """,
        ),
        (
            r"""
            ### 5.1g Read physical checks and post-route timing

            The external-analog top passes the reported routing, Magic,
            KLayout and **LEF-macro connectivity** LVS checks when their error
            counts are zero. The clean01 run also has zero final antenna
            violations. A stricter timing-clean gate additionally requires
            zero max slew, fanout and capacitance violations:

            $$
            G_{\rm timing-clean}=
            \mathbf{1}[N_{\rm slew}=N_{\rm fanout}=N_{\rm cap}=0]
            \land\mathbf{1}[{\rm slack}_{\min}\ge0].
            $$

            In the copied clean01 report, setup/hold slack are positive, but
            **57 max-fanout violations** remain. This cell reads reports by
            suffix because OpenLane step numbers moved after diode insertion.

            | Run | Route / Magic / KLayout / LVS | Final antenna | Max fanout |
            |---|---:|---:|---:|
            | lvs09 | 0 / 0 / 0 / 0 | 39 pin, 38 net | 7 |
            | clean01 | 0 / 0 / 0 / 0 | 0 pin, 0 net | 57 |

            Stage-5 and OpenLane PDK revisions differ, and this top uses
            LEF-macro connectivity LVS; a composite device-level wrapper
            sign-off remains future work.
            """,
            r"""
            import re

            FANOUT_VIOLATIONS = None
            if CORE_BOUND_RUN is None:
                print("Physical checks: run not copied")
            else:
                for key in ("tritonRoute_violations", "Magic_violations",
                            "klayout_violations", "lvs_total_errors",
                            "pin_antenna_violations", "net_antenna_violations"):
                    print(f"{key:28s}: {CORE_BOUND_METRICS.get(key, 'missing')}")
                checks = list((CORE_BOUND_RUN / "reports/signoff").glob(
                    "*-rcx_sta.checks.rpt"))
                summaries = list((CORE_BOUND_RUN / "reports/signoff").glob(
                    "*-rcx_sta.summary.rpt"))
                if len(checks) != 1 or len(summaries) != 1:
                    print("STA reports: missing or ambiguous")
                else:
                    checks_text = checks[0].read_text(encoding="utf-8", errors="replace")
                    for name in ("max slew", "max fanout", "max cap"):
                        match = re.search(rf"{name} violation count\s+(\d+)", checks_text)
                        count = int(match.group(1)) if match else None
                        print(name, "violations:", count)
                        if name == "max fanout":
                            FANOUT_VIOLATIONS = count
                    summary_text = summaries[0].read_text(
                        encoding="utf-8", errors="replace")
                    slacks = re.findall(r"(?m)^worst slack\s+(-?\d+(?:\.\d+)?)$",
                                        summary_text)
                    print("Post-route setup/hold slack ns:", slacks[:2])
                if FANOUT_VIOLATIONS == 0:
                    print("Conclusion: core-bound GDS and reported layout/timing checks pass.")
                else:
                    print("Conclusion: core-bound GDS exists and layout checks pass;"
                          " max fanout still needs repair.")
            """,
        ),
    ],
}


def generated_cell(kind: str, body: str, cell_id: str) -> dict:
    cell = {
        "cell_type": kind,
        "id": cell_id,
        "metadata": {MARKER: True},
        "source": lines(body),
    }
    if kind == "code":
        cell.update({"execution_count": None, "outputs": []})
    return cell


def improve_stage5_diagnostics(cell: dict) -> None:
    """Keep the original physical run but show Magic's actual failure lines."""
    source = "".join(cell["source"])
    old_preflight = "subprocess.run(preflight_command, cwd=ROOT, check=True)"
    if old_preflight in source:
        source = source.replace(old_preflight, """preflight_result = subprocess.run(
    preflight_command, cwd=ROOT, text=True, capture_output=True, check=True)
preflight_data = json.loads(preflight_result.stdout)
print('Stage-5 preflight:', preflight_data['status'])
print('Tools:', preflight_data['tools'])""")
    old_failure = "    if physical_result.returncode:\n"
    generator_lines = """    if physical_result.returncode:
        generator_log = ROOT / 'results/sky130/layout/magic_generate.log'
        if generator_log.is_file():
            print('Stage-5 Magic generator log tail:')
            print('\\n'.join(generator_log.read_text(
                encoding='utf-8', errors='replace').splitlines()[-80:]))
"""
    if "Stage-5 Magic generator log tail:" not in source:
        source = source.replace(old_failure, generator_lines, 1)
    else:
        # Repair the first generated notebook revision, whose inserted body
        # lacked one indentation level. Keep the original error handler after it.
        bad_lines = """    if physical_result.returncode:
    generator_log = ROOT / 'results/sky130/layout/magic_generate.log'
    if generator_log.is_file():
        print('Stage-5 Magic generator log tail:')
        print('\\n'.join(generator_log.read_text(
            encoding='utf-8', errors='replace').splitlines()[-80:]))
"""
        source = source.replace(bad_lines, generator_lines, 1)
    cell["source"] = source.splitlines(keepends=True)


def improve_core_coverage_resume(cell: dict) -> None:
    """Expose the longer timeout and checkpoint count in cell 4.5."""
    source = "".join(cell["source"])
    source = source.replace(
        "from scripts.run_core_pex_coverage import run as run_core_pex_coverage",
        "import importlib\n"
        "import scripts.run_core_pex_coverage as core_pex_coverage_module\n"
        "core_pex_coverage_module = importlib.reload(core_pex_coverage_module)\n"
        "run_core_pex_coverage = core_pex_coverage_module.run", 1)
    if "CORE_PEX_TIMEOUT_S" not in source:
        source = source.replace(
            "FULL_PVT_CORE_SCREEN = False\n",
            "FULL_PVT_CORE_SCREEN = False\nCORE_PEX_TIMEOUT_S = 600\n", 1)
        source = source.replace(
            "full_pvt=FULL_PVT_CORE_SCREEN, mha_pattern_limit=16)",
            "full_pvt=FULL_PVT_CORE_SCREEN, mha_pattern_limit=16,\n"
            "                                      timeout_s=CORE_PEX_TIMEOUT_S)", 1)
        source = source.replace(
            "print('Receipt: results/receipts/physical/core_pex_coverage.json')",
            "print('Reused valid checkpoints:', core_coverage.get('reused_checkpoints', 0))\n"
            "print('Receipt: results/receipts/physical/core_pex_coverage.json')", 1)
    cell["source"] = source.splitlines(keepends=True)


def improve_transfer_diagnostic_resume(cell: dict) -> None:
    """Reload cell 4.6's runner and show its verified resume count."""
    source = "".join(cell["source"])
    source = source.replace(
        "from scripts.run_core_transfer_diagnostics import run as run_core_transfer_diagnostics",
        "import importlib\n"
        "import scripts.run_core_transfer_diagnostics as transfer_module\n"
        "transfer_module = importlib.reload(transfer_module)\n"
        "run_core_transfer_diagnostics = transfer_module.run", 1)
    if "CORE_TRANSFER_TIMEOUT_S" not in source:
        source = source.replace(
            "RUN_CORE_TRANSFER_DIAGNOSTICS = True\n",
            "RUN_CORE_TRANSFER_DIAGNOSTICS = True\nCORE_TRANSFER_TIMEOUT_S = 600\n", 1)
        source = source.replace(
            "ROOT, execute=RUN_CORE_TRANSFER_DIAGNOSTICS, timeout_s=180)",
            "ROOT, execute=RUN_CORE_TRANSFER_DIAGNOSTICS,\n"
            "    timeout_s=CORE_TRANSFER_TIMEOUT_S)", 1)
        source = source.replace(
            "print('Matched schematic/PEX sims:', transfer_diagnostic['completed_sims'],",
            "print('Reused valid checkpoints:', transfer_diagnostic.get('reused_checkpoints', 0))\n"
            "print('Matched schematic/PEX sims:', transfer_diagnostic['completed_sims'],", 1)
    cell["source"] = source.splitlines(keepends=True)


def improve_readiness_inventory(cell: dict) -> None:
    """Show stale Stage-4.9 source hashes in the planning inventory."""
    source = "".join(cell["source"])
    source = source.replace(
        "('missing_decisions', 'missing_evidence_or_review', 'missing_views')",
        "('cell49_stale_inputs', 'missing_decisions', "
        "'missing_evidence_or_review', 'missing_views')", 1)
    cell["source"] = source.splitlines(keepends=True)


def main() -> None:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    original = [
        cell for cell in notebook["cells"]
        if not cell.get("metadata", {}).get(MARKER)
    ]
    if len(original) != 77:
        raise RuntimeError(f"Expected 77 original cells, found {len(original)}")
    actual_code_indices = {
        i for i, cell in enumerate(original) if cell["cell_type"] == "code"
    }
    if actual_code_indices != set(CODE_GUIDES):
        raise RuntimeError(
            f"Guide coverage mismatch: missing={actual_code_indices - set(CODE_GUIDES)}, "
            f"extra={set(CODE_GUIDES) - actual_code_indices}"
        )
    new_cells: list[dict] = []
    for index, cell in enumerate(original):
        for extra_index, (explanation, source) in enumerate(
            EXTRA_BEFORE.get(index, ())
        ):
            new_cells.append(generated_cell(
                "markdown", explanation, f"story-{index}-{extra_index}-intro"))
            new_cells.append(generated_cell(
                "code", source, f"story-{index}-{extra_index}-run"))
        if index in MARKDOWN_REPLACEMENTS:
            cell["source"] = lines(MARKDOWN_REPLACEMENTS[index])
        if index in CODE_REPLACEMENTS:
            cell["source"] = lines(CODE_REPLACEMENTS[index])
            cell["execution_count"] = None
            cell["outputs"] = []
        if index == 22:
            improve_stage5_diagnostics(cell)
            cell["execution_count"] = None
            cell["outputs"] = []
        if index == 26:
            improve_core_coverage_resume(cell)
            cell["execution_count"] = None
            cell["outputs"] = []
        if index == 28:
            improve_transfer_diagnostic_resume(cell)
            cell["execution_count"] = None
            cell["outputs"] = []
        if index == 40:
            improve_readiness_inventory(cell)
            cell["execution_count"] = None
            cell["outputs"] = []
        if cell["cell_type"] == "code":
            title, action, equation, evidence = CODE_GUIDES[index]
            new_cells.append(generated_cell(
                "markdown", guide(title, action, equation, evidence),
                f"story-{index}-guide"))
        cell.setdefault("id", f"original-{index:03d}")
        new_cells.append(cell)
    ids = [cell["id"] for cell in new_cells]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Notebook cell IDs are not unique")
    if not all(cell["cell_type"] != "code" or "source" in cell
               for cell in new_cells):
        raise RuntimeError("Code cell without source")
    notebook["cells"] = new_cells
    serialized = json.dumps(notebook, ensure_ascii=False, indent=1) + "\n"
    staged = NOTEBOOK.with_suffix(".ipynb.tmp")
    staged.write_text(serialized, encoding="utf-8")
    json.loads(staged.read_text(encoding="utf-8"))
    staged.replace(NOTEBOOK)
    print(f"Curated {NOTEBOOK.name}: {len(original)} original cells, "
          f"{len(new_cells) - len(original)} explanatory/new cells, "
          f"{len(new_cells)} total")


if __name__ == "__main__":
    main()
